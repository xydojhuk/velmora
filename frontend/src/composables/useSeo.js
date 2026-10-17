import { useHead } from '@unhead/vue'
import { useAppState } from './useAppState.js'
import { compactMetaText, safeJsonLd } from '../utils/seo.js'

const defaultImage = '/img/herobg.png'

function absoluteUrl(value, siteUrl) {
  if (!value) return siteUrl || '/'
  try {
    return siteUrl ? new URL(value, siteUrl).toString() : value
  } catch {
    return value
  }
}

export function useSeo({ title, description, path = '/', image = defaultImage, imageAlt = '', type = 'website', noindex = false, jsonLd = null }) {
  const state = useAppState()
  const siteUrl = String(state.siteUrl || '').replace(/\/$/, '')
  const metaTitle = compactMetaText(title, 80)
  const metaDescription = compactMetaText(description, 200)
  const siteName = state.pageData?.storeConfig?.store_name || 'Velmora'
  const canonical = absoluteUrl(path, siteUrl)
  const imageUrl = absoluteUrl(image, siteUrl)
  const robots = noindex ? 'noindex,nofollow,noarchive' : 'index,follow,max-image-preview:large,max-snippet:-1,max-video-preview:-1'
  const head = {
    title: metaTitle,
    link: [{ rel: 'canonical', href: canonical }],
    meta: [
      { name: 'description', content: metaDescription },
      { name: 'robots', content: robots },
      { property: 'og:locale', content: 'en_US' },
      { property: 'og:type', content: type },
      { property: 'og:site_name', content: siteName },
      { property: 'og:title', content: metaTitle },
      { property: 'og:description', content: metaDescription },
      { property: 'og:url', content: canonical },
      { property: 'og:image', content: imageUrl },
      { property: 'og:image:alt', content: imageAlt || metaTitle },
      { name: 'twitter:card', content: 'summary_large_image' },
      { name: 'twitter:title', content: metaTitle },
      { name: 'twitter:description', content: metaDescription },
      { name: 'twitter:image', content: imageUrl },
      { name: 'twitter:image:alt', content: imageAlt || metaTitle }
    ]
  }
  if (jsonLd) {
    const items = Array.isArray(jsonLd) ? jsonLd : [jsonLd]
    head.script = items.map(item => ({ type: 'application/ld+json', nonce: state.cspNonce || undefined, innerHTML: safeJsonLd(item) }))
  }
  useHead(head)
}
