import test from 'node:test'
import assert from 'node:assert/strict'
import { hasSchemaType } from './seo-structured-data.mjs'

test('recognizes correct Product and BreadcrumbList JSON-LD', () => {
  const html = `<script nonce="abc" type="application/ld+json">{"@context":"https://schema.org","@type":"Product"}</script><script type='application/ld+json'>{"@context":"https://schema.org","@type":"BreadcrumbList"}</script>`
  assert.equal(hasSchemaType(html, 'Product'), true)
  assert.equal(hasSchemaType(html, 'BreadcrumbList'), true)
})

test('rejects malicious lookalike schema URLs and non-JSON text', () => {
  const html = `<script type="application/ld+json">{"@context":"https://schema.org.evil.example","@type":"Product"}</script><p>https://schema.org</p>`
  assert.equal(hasSchemaType(html, 'Product'), false)
  assert.equal(hasSchemaType('<script type="application/ld+json">broken</script>', 'Product'), false)
})
