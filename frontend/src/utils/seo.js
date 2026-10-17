export function safeJsonLd(value) {
  return JSON.stringify(value)
    .replace(/</g, '\\u003c')
    .replace(/\u2028/g, '\\u2028')
    .replace(/\u2029/g, '\\u2029')
}

export function compactMetaText(value, maxLength = 180) {
  const normalized = String(value || '').replace(/\s+/g, ' ').trim()
  if (normalized.length <= maxLength) return normalized
  const slice = normalized.slice(0, maxLength + 1)
  const boundary = slice.lastIndexOf(' ')
  return `${slice.slice(0, boundary > maxLength * 0.7 ? boundary : maxLength).trim()}…`
}

export function validGoogleAnalyticsId(value) {
  const id = String(value || '').trim()
  return /^G-[A-Z0-9]{4,20}$/i.test(id) ? id : ''
}

export function validGoogleTagManagerId(value) {
  const id = String(value || '').trim()
  return /^GTM-[A-Z0-9]{4,20}$/i.test(id) ? id : ''
}

export function validVerificationToken(value) {
  const token = String(value || '').trim()
  return /^[A-Za-z0-9._~=-]{6,200}$/.test(token) ? token : ''
}
