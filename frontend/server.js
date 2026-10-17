import crypto from 'node:crypto'
import fs from 'node:fs/promises'
import path from 'node:path'
import process from 'node:process'
import { fileURLToPath } from 'node:url'
import express from 'express'
import { rateLimit } from 'express-rate-limit'
import axios from 'axios'

const root = path.dirname(fileURLToPath(import.meta.url))

async function loadEnv() {
  try {
    const raw = await fs.readFile(path.join(root, '.env'), 'utf8')
    for (const line of raw.split(/\r?\n/)) {
      const value = line.trim()
      if (!value || value.startsWith('#') || !value.includes('=')) continue
      const index = value.indexOf('=')
      const key = value.slice(0, index).trim()
      const val = value.slice(index + 1).trim().replace(/^['"]|['"]$/g, '')
      if (!(key in process.env)) process.env[key] = val
    }
  } catch {}
}

await loadEnv()

const isProd = process.env.NODE_ENV === 'production'
const host = process.env.HOST || '127.0.0.1'
const port = Number(process.env.PORT || 5173)
const configuredSiteUrl = String(process.env.SITE_URL || '').trim()
if (isProd && !configuredSiteUrl) throw new Error('SITE_URL must be configured in production')
const siteUrl = String(configuredSiteUrl || `http://localhost:${port}`).replace(/\/$/, '')
let siteProtocol
try {
  const parsedSiteUrl = new URL(siteUrl)
  siteProtocol = parsedSiteUrl.protocol
  if (!['http:', 'https:'].includes(parsedSiteUrl.protocol)) throw new Error('unsupported protocol')
} catch {
  throw new Error('SITE_URL must be an absolute http(s) URL')
}

const apiBaseURL = process.env.API_SERVER_BASE_URL || 'http://127.0.0.1:8000/api/v1'
const apiProxyTarget = process.env.API_PROXY_TARGET || 'http://127.0.0.1:8000'
const installStateFile = process.env.INSTALL_STATE_FILE || '/run/velmora/config/installed.json'
async function installationComplete() {
  try { await fs.access(installStateFile); return true } catch { return false }
}
const runtimeConfig = {
  googleSiteVerification: String(process.env.GOOGLE_SITE_VERIFICATION || '').trim(),
  bingSiteVerification: String(process.env.BING_SITE_VERIFICATION || '').trim(),
  yandexSiteVerification: String(process.env.YANDEX_SITE_VERIFICATION || '').trim(),
  googleAnalyticsId: String(process.env.GOOGLE_ANALYTICS_ID || '').trim(),
  googleTagManagerId: String(process.env.GOOGLE_TAG_MANAGER_ID || '').trim()
}

const app = express()
app.disable('x-powered-by')
// In Docker, Caddy is the only public-facing hop. Do not trust forwarded IPs
// for direct/local Node development unless explicitly configured.
const proxyHops = Number(process.env.SSR_TRUST_PROXY_HOPS || 0)
if (!Number.isInteger(proxyHops) || proxyHops < 0 || proxyHops > 1) throw new Error('Invalid SSR_TRUST_PROXY_HOPS')
app.set('trust proxy', proxyHops)

const ssrLimitPerMinute = Number(process.env.SSR_RATE_LIMIT_PER_MINUTE || 240)
if (!Number.isSafeInteger(ssrLimitPerMinute) || ssrLimitPerMinute < 1 || ssrLimitPerMinute > 5000) {
  throw new Error('Invalid SSR_RATE_LIMIT_PER_MINUTE')
}
const ssrRateLimiter = rateLimit({
  windowMs: 60_000,
  limit: ssrLimitPerMinute,
  standardHeaders: 'draft-8',
  legacyHeaders: false,
  skip: req => !['GET', 'HEAD'].includes(req.method),
  message: 'Too many page requests. Please try again later.'
})

function buildContentSecurityPolicy(nonce) {
  const usesGoogle = Boolean(runtimeConfig.googleAnalyticsId || runtimeConfig.googleTagManagerId)
  const scriptSources = ["'self'", `'nonce-${nonce}'`]
  const connectSources = ["'self'"]
  if (usesGoogle) {
    scriptSources.push('https://www.googletagmanager.com', 'https://www.google-analytics.com')
    connectSources.push('https://www.googletagmanager.com', 'https://www.google-analytics.com', 'https://*.google-analytics.com')
  }
  return [
    "default-src 'self'",
    "base-uri 'self'",
    "object-src 'none'",
    "frame-ancestors 'none'",
    "form-action 'self'",
    `script-src ${scriptSources.join(' ')}`,
    "script-src-attr 'none'",
    "style-src 'self' https://fonts.googleapis.com",
    `style-src-elem 'self' 'nonce-${nonce}' https://fonts.googleapis.com`,
    "style-src-attr 'unsafe-inline'",
    "font-src 'self' data: https://fonts.gstatic.com",
    "img-src 'self' data: blob: https:",
    "frame-src 'none'",
    `connect-src ${connectSources.join(' ')}`,
    "media-src 'self'",
    "manifest-src 'self'",
    "worker-src 'self' blob:",
    ...(isProd && siteProtocol === 'https:' ? ['upgrade-insecure-requests'] : [])
  ].join('; ')
}

app.use((req, res, next) => {
  res.set('X-Content-Type-Options', 'nosniff')
  res.set('X-Frame-Options', 'DENY')
  res.set('Referrer-Policy', 'strict-origin-when-cross-origin')
  res.set('Permissions-Policy', 'camera=(), microphone=(), geolocation=(), payment=(), usb=()')
  res.set('Cross-Origin-Opener-Policy', 'same-origin')
  res.set('X-Permitted-Cross-Domain-Policies', 'none')
  if (isProd && siteProtocol === 'https:') res.set('Strict-Transport-Security', 'max-age=31536000; includeSubDomains')
  next()
})

app.get('/healthz', (req, res) => {
  res.set('Cache-Control', 'no-store')
  res.set('X-Robots-Tag', 'noindex, nofollow, noarchive')
  res.json({ status: 'ok' })
})

app.use(async (req, res, next) => {
  if (!['GET', 'HEAD'].includes(req.method)) return next()
  const installed = await installationComplete()
  if (installed && req.path === '/install') return res.redirect(302, '/')
  if (!installed && req.path !== '/install' && !req.path.startsWith('/assets/') && !req.path.startsWith('/img/') && !req.path.startsWith('/brand/') && req.path !== '/favicon.ico') {
    res.set('Cache-Control', 'no-store')
    res.set('X-Robots-Tag', 'noindex, nofollow, noarchive')
    return res.redirect(302, '/install')
  }
  next()
})

let vite

function xmlEscape(value) {
  return String(value).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&apos;')
}

async function publicProducts() {
  try {
    const response = await axios.get(`${apiBaseURL}/public/products`, { timeout: 6000 })
    return { products: response.data.filter(item => item.is_active), online: true }
  } catch {
    return { products: [], online: false }
  }
}

if (!isProd) {
  const { createServer } = await import('vite')
  vite = await createServer({
    root,
    server: {
      middlewareMode: true,
      proxy: {
        '/api': { target: apiProxyTarget, changeOrigin: true },
        '/media': { target: apiProxyTarget, changeOrigin: true }
      }
    },
    appType: 'custom'
  })
  app.use(vite.middlewares)
} else {
  app.use('/assets', express.static(path.join(root, 'dist/client/assets'), { maxAge: '1y', immutable: true }))
  app.use(express.static(path.join(root, 'dist/client'), { index: false, maxAge: '1h' }))
}

app.get('/robots.txt', async (req, res) => {
  if (!(await installationComplete())) { res.set('Cache-Control','no-store'); return res.type('text/plain').send('User-agent: *\nDisallow: /') }
  res.set('Cache-Control', 'public, max-age=300')
  res.type('text/plain').send([
    'User-agent: *',
    'Allow: /',
    'Disallow: /api/',
    `Sitemap: ${siteUrl}/sitemap.xml`
  ].join('\n'))
})

app.get('/sitemap.xml', async (req, res) => {
  const result = await publicProducts()
  if (!result.online) {
    res.set('Retry-After', '300')
    res.set('Cache-Control', 'no-store')
    return res.status(503).type('text/plain').send('Sitemap is temporarily unavailable')
  }
  const urls = [
    `<url><loc>${xmlEscape(`${siteUrl}/`)}</loc></url>`,
    ...result.products.map(product => {
      const lastmod = product.updated_at ? `<lastmod>${xmlEscape(String(product.updated_at).slice(0, 10))}</lastmod>` : ''
      return `<url><loc>${xmlEscape(`${siteUrl}/product/${encodeURIComponent(product.slug)}`)}</loc>${lastmod}</url>`
    })
  ]
  res.set('Cache-Control', 'public, max-age=300, stale-while-revalidate=600')
  res.type('application/xml').send(`<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">${urls.join('')}</urlset>`)
})

app.get('/llms.txt', async (req, res) => {
  const result = await publicProducts()
  if (!result.online) {
    res.set('Retry-After', '300')
    res.set('Cache-Control', 'no-store')
    return res.status(503).type('text/plain').send('Catalog data is temporarily unavailable')
  }
  let storeName = 'Online store'
  let storeDescription = 'Browse our product catalog.'
  try {
    const { data } = await axios.get(`${apiBaseURL}/public/config`, { timeout: 6000 })
    storeName = String(data.store_name || storeName).replace(/[\r\n#]/g, ' ').trim()
    storeDescription = String(data.seo_description || data.footer_description || storeDescription).replace(/[\r\n]/g, ' ').trim()
  } catch {
    res.set('Retry-After', '300')
    res.set('Cache-Control', 'no-store')
    return res.status(503).type('text/plain').send('Store information is temporarily unavailable')
  }
  const lines = [
    `# ${storeName}`,
    '',
    storeDescription,
    'Primary language: English.',
    '',
    '## Public pages',
    `- ${siteUrl}/ — catalog, product overview, FAQ and contacts`,
    ...result.products.map(product => `- ${siteUrl}/product/${encodeURIComponent(product.slug)} — ${product.title}`),
    '',
    '## Indexing',
    `- Sitemap: ${siteUrl}/sitemap.xml`,
    `- Robots: ${siteUrl}/robots.txt`,
    '',
    'The admin panel, authentication and checkout pages are not intended for indexing.'
  ]
  res.set('Cache-Control', 'public, max-age=300')
  res.type('text/plain').send(lines.join('\n'))
})

app.use(ssrRateLimiter, async (req, res, next) => {
  if (!['GET', 'HEAD'].includes(req.method) || req.path.startsWith('/api/') || req.path.startsWith('/media/')) return next()
  const privatePage = req.path === '/login' || req.path.startsWith('/admin') || req.path.startsWith('/checkout')
  if (privatePage) {
    res.set('X-Robots-Tag', 'noindex, nofollow, noarchive')
    res.set('Cache-Control', 'no-store')
  } else {
    res.set('Cache-Control', 'public, max-age=0, s-maxage=60, stale-while-revalidate=300')
  }

  const cspNonce = crypto.randomBytes(18).toString('base64')
  if (isProd) res.set('Content-Security-Policy', buildContentSecurityPolicy(cspNonce))

  try {
    let template
    let render
    if (!isProd) {
      template = await fs.readFile(path.join(root, 'index.html'), 'utf8')
      template = await vite.transformIndexHtml(req.originalUrl, template)
      render = (await vite.ssrLoadModule('/src/entry-server.js')).render
    } else {
      template = await fs.readFile(path.join(root, 'dist/client/index.html'), 'utf8')
      render = (await import('./dist/server/entry-server.js')).render
    }

    const result = await render(req.originalUrl, {
      apiBaseURL,
      cookie: req.headers.cookie || '',
      siteUrl,
      runtimeConfig,
      cspNonce
    })

    if ((result.status || 200) >= 400) res.set('X-Robots-Tag', 'noindex, nofollow, noarchive')
    if (result.status === 503) {
      res.set('Retry-After', '3600')
      res.set('Cache-Control', 'no-store')
    }

    const state = JSON.stringify(result.state).replace(/</g, '\\u003c').replace(/\u2028/g, '\\u2028').replace(/\u2029/g, '\\u2029')
    const html = template
      .replaceAll('__CSP_NONCE__', cspNonce)
      .replace('__APP_HEAD__', result.head || '')
      .replace('__APP_HTML__', result.html || '')
      .replace('__APP_STATE__', state)

    res.set('Content-Language', 'en')
    res.status(result.status || 200).type('text/html').send(html)
  } catch (error) {
    if (vite) vite.ssrFixStacktrace(error)
    console.error(error)
    res.set('X-Robots-Tag', 'noindex, nofollow, noarchive')
    res.set('Cache-Control', 'no-store')
    res.status(500).type('text/plain').send('Internal server error')
  }
})

app.listen(port, host, () => {
  console.log(`VELMORA Vue SSR: ${siteUrl} (${host}:${port})`)
})
