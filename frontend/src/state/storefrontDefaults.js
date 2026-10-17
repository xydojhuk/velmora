import legacyCopy from './legacyStorefrontCopy.json'
import canonicalStorefront from './storefrontDefaults.json'

export const defaultStorefront = canonicalStorefront

function mergeValue(base, override) {
  if (Array.isArray(base)) return Array.isArray(override) ? override : base
  if (base && typeof base === 'object') {
    const source = override && typeof override === 'object' && !Array.isArray(override) ? override : {}
    return Object.fromEntries(Object.keys(base).map(key => [key, mergeValue(base[key], source[key])]).concat(
      Object.keys(source).filter(key => !(key in base)).map(key => [key, source[key]])
    ))
  }
  return override === undefined || override === null ? base : override
}

// Upgrade ONLY unchanged old placeholder copy; retain user-authored content.
// Existing database values are not overwritten until the shop owner saves the editor.
function replaceLegacyCopy(current, legacy, modern) {
  if (Array.isArray(legacy)) {
    if (!Array.isArray(current)) return current
    return current.map((item, index) => index < legacy.length && index < modern.length
      ? replaceLegacyCopy(item, legacy[index], modern[index]) : item)
  }
  if (legacy && typeof legacy === 'object' && current && typeof current === 'object') {
    return Object.fromEntries(Object.entries(current).map(([key, item]) => [key,
      Object.prototype.hasOwnProperty.call(legacy, key) && Object.prototype.hasOwnProperty.call(modern, key)
        ? replaceLegacyCopy(item, legacy[key], modern[key]) : item]))
  }
  return current === legacy ? modern : current
}

export function mergeStorefrontConfig(value) {
  const merged = mergeValue(defaultStorefront, value || {})
  for (const key of ['modals', 'platform']) {
    merged[key] = replaceLegacyCopy(merged[key], legacyCopy[key], defaultStorefront[key])
  }
  // Platform attribution belongs to the software, not to an individual store.
  merged.platform.enabled = true
  merged.platform.repository_url ||= 'https://github.com/xydojhuk/velmora'
  return merged
}
