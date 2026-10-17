import { fallbackProduct, fallbackProducts, storeInfo } from './state/fallback.js'
import { defaultStorefront } from './state/storefrontDefaults.js'

const fallbackConfig = {
  store_name: storeInfo.name,
  brand_tagline: storeInfo.tagline,
  footer_description: storeInfo.footerDescription,
  phone: storeInfo.phoneDisplay,
  email: storeInfo.email,
  working_hours: storeInfo.hours,
  business_hours: [],
  timezone: storeInfo.timezone,
  service_region: storeInfo.location,
  storefront: defaultStorefront,
  seo_title: 'Velmora — online store',
  seo_description: storeInfo.footerDescription,
  seo_og_image: '/brand/velmora-icon-512.png',
  maintenance_mode: false,
  maintenance_title: 'Scheduled maintenance',
  maintenance_message: '',
  orders_enabled: false,
  shipping_methods: [],
  payment_methods: [],
  icons: []
}

async function safeConfig(api) {
  try {
    const response = await api.get('/public/config')
    return { data: response.data, online: true }
  } catch {
    return { data: fallbackConfig, online: false }
  }
}

async function safeProducts(api) {
  try {
    const response = await api.get('/public/products')
    return { data: response.data, online: true }
  } catch {
    return { data: fallbackProducts, online: false }
  }
}

async function safeProduct(api, slug) {
  try {
    const response = await api.get(`/public/products/${encodeURIComponent(slug)}`)
    return { data: response.data, online: true, missing: false }
  } catch (error) {
    if (error.response?.status === 404) return { data: null, online: true, missing: true }
    return { data: fallbackProduct(slug), online: false, missing: false }
  }
}

export async function loadSsrState(route, api) {
  if (route.name === 'install') return { pageData: {}, apiOnline: true, status: 200 }
  const isStore = route.meta.layout === 'store'
  const config = isStore ? await safeConfig(api) : { data: null, online: true }
  if (route.name === 'home') {
    const products = await safeProducts(api)
    const online = products.online && config.online
    return { pageData: { products: products.data, storeConfig: config.data }, apiOnline: online, status: config.data?.maintenance_mode || !online ? 503 : 200 }
  }
  if (route.name === 'product' || route.name === 'checkout') {
    const product = await safeProduct(api, route.params.slug)
    const products = await safeProducts(api)
    const online = product.online && products.online && config.online
    let status = 200
    if (config.data?.maintenance_mode || !online) status = 503
    else if (product.missing) status = 404
    return {
      pageData: { product: product.data, productMissing: product.missing, products: products.data, storeConfig: config.data },
      apiOnline: online,
      status
    }
  }
  if (route.name === 'not-found') return { pageData: { storeConfig: config.data }, apiOnline: config.online, status: 404 }
  return { pageData: {}, apiOnline: true, status: 200 }
}
