// Validate JSON-LD as structured data rather than searching HTML for a URL substring.
export function hasSchemaType(html, expectedType) {
  const scripts = String(html).matchAll(/<script\b[^>]*\btype\s*=\s*["']application\/ld\+json["'][^>]*>([\s\S]*?)<\/script\s*>/gi)
  for (const [, contents] of scripts) {
    let parsed
    try { parsed = JSON.parse(contents) } catch { continue }
    const queue = Array.isArray(parsed) ? parsed : [parsed]
    while (queue.length) {
      const value = queue.pop()
      if (!value || typeof value !== 'object') continue
      if (value['@context'] === 'https://schema.org' && value['@type'] === expectedType) return true
      if (Array.isArray(value['@graph'])) queue.push(...value['@graph'])
    }
  }
  return false
}
