import { computed } from 'vue'
import { useAppState } from './useAppState.js'
import { storeInfo as fallback } from '../state/fallback.js'
import { mergeStorefrontConfig } from '../state/storefrontDefaults.js'

function phoneHref(value) {
  return String(value || '').replace(/[^+\d]/g, '')
}

export function useStoreInfo() {
  const state = useAppState()
  return computed(() => {
    const config = state.pageData.storeConfig || {}
    const has = key => Object.prototype.hasOwnProperty.call(config, key)
    const phoneDisplay = has('phone') ? config.phone : fallback.phoneDisplay
    const storefront = mergeStorefrontConfig(config.storefront)
    return {
      name: has('store_name') ? config.store_name : fallback.name,
      tagline: has('brand_tagline') ? config.brand_tagline : fallback.tagline,
      footerDescription: has('footer_description') ? config.footer_description : fallback.footerDescription,
      phoneDisplay,
      phoneHref: phoneHref(phoneDisplay),
      email: has('email') ? config.email : fallback.email,
      hours: has('working_hours') ? config.working_hours : fallback.hours,
      businessHours: Array.isArray(config.business_hours) ? config.business_hours : [],
      timezone: has('timezone') ? config.timezone : fallback.timezone,
      location: has('service_region') ? config.service_region : fallback.location,
      warranty: fallback.warranty,
      warrantyNote: fallback.warrantyNote,
      storefront,
      logoUrl: storefront.branding.logo_url || '/img/logo.png',
      logoAlt: storefront.branding.logo_alt || (has('store_name') ? config.store_name : fallback.name),
      seoTitle: config.seo_title || `${has('store_name') ? config.store_name : fallback.name} — online store`,
      seoDescription: config.seo_description || (has('footer_description') ? config.footer_description : fallback.footerDescription),
      seoOgImage: config.seo_og_image || storefront.hero.image_url || '/brand/velmora-icon-512.png',
      maintenanceMode: Boolean(config.maintenance_mode),
      maintenanceTitle: config.maintenance_title || 'Scheduled maintenance',
      maintenanceMessage: config.maintenance_message || 'We are updating the store. Please try again shortly.',
      ordersEnabled: config.orders_enabled !== false,
      shippingMethods: Array.isArray(config.shipping_methods) ? config.shipping_methods : [],
      paymentMethods: Array.isArray(config.payment_methods) ? config.payment_methods : []
    }
  })
}
