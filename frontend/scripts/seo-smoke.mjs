// Runtime SEO smoke checks for a real installed shop (never assumes demo products exist).
import { hasSchemaType } from './seo-structured-data.mjs'

const base = String(process.env.SITE_URL || 'http://localhost:5173').replace(/\/$/, '')

async function read(path) {
  const response = await fetch(`${base}${path}`, { redirect: 'manual' })
  const text = await response.text()
  return { response, text }
}
function assert(value, message) { if (!value) throw new Error(message) }

const homepage = await read('/')
assert(homepage.response.ok, `Homepage HTTP ${homepage.response.status}`)
assert(homepage.text.includes('<h1'), 'Homepage SSR has no H1')
assert(homepage.text.includes('application/ld+json'), 'Missing JSON-LD')
assert(homepage.text.includes('rel="canonical"'), 'Missing canonical URL')
assert(homepage.text.includes('name="description"'), 'Missing meta description')

const robots = await read('/robots.txt')
assert(robots.response.ok && robots.text.includes('Sitemap:'), 'Missing robots sitemap reference')
assert(robots.text.includes('Disallow: /api/'), 'Robots should disallow API paths')

const sitemap = await read('/sitemap.xml')
assert(sitemap.response.ok && sitemap.text.includes('<urlset'), 'Invalid sitemap')

// A fresh shop can have zero published products. Check their SEO only if present.
const productUrl = [...sitemap.text.matchAll(/<loc>([^<]*\/product\/[^<]+)<\/loc>/g)]
  .map(([, url]) => url.replaceAll('&amp;', '&'))[0]
if (productUrl) {
  const product = await read(new URL(productUrl, base).pathname)
  assert(product.response.ok, `Product page HTTP ${product.response.status}`)
assert(hasSchemaType(product.text, 'Product'), 'Product JSON-LD missing or has invalid schema context')
  assert(hasSchemaType(product.text, 'BreadcrumbList'), 'Product breadcrumbs JSON-LD missing')
  const slug = new URL(productUrl, base).pathname.split('/').pop()
  const checkout = await read(`/checkout/${encodeURIComponent(slug)}`)
  assert(checkout.response.ok, `Checkout HTTP ${checkout.response.status}`)
  assert(String(checkout.response.headers.get('x-robots-tag') || '').includes('noindex'), 'Checkout should be noindex')
} else {
  console.log('No published product in sitemap; product/checkout SEO checks skipped')
}

const llms = await read('/llms.txt')
assert(llms.response.ok && llms.text.trim().length > 0, 'llms.txt is empty')
console.log(`SSR/SEO smoke checks passed for ${base}`)
