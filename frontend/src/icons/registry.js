const modules = import.meta.glob('../assets/icons/*.svg', { eager: true, query: '?raw', import: 'default' })

const aliases = { shieldcheck: 'shield-check' }
const labels = {
  arrow: 'Arrow', battery: 'Battery', cart: 'Cart', clock: 'Time', connection: 'Signal', notification: 'Notification',
  phone: 'Phone', plus: 'Add', pulse: 'Pulse', radar: 'Radar', resize: 'Size', shield: 'Shield', 'shield-check': 'Verified shield',
  video: 'Video', weight: 'Weight', wifi: 'Wi-Fi'
}

function keyFromPath(path) { return path.split('/').pop().replace(/\.svg$/i, '') }
function normalizeMarkup(source) {
  return String(source)
    .replace(/\swidth="[^"]*"/g, '').replace(/\sheight="[^"]*"/g, '')
    .replace(/stroke="(?:black|#000(?:000)?)"/gi, 'stroke="currentColor"')
    .replace(/fill="(?:black|#000(?:000)?)"/gi, 'fill="currentColor"')
}
const registry = Object.fromEntries(Object.entries(modules).map(([path, source]) => [keyFromPath(path), normalizeMarkup(source)]))
export function resolveIconName(name) { const value = String(name || '').trim().toLowerCase(); return aliases[value] || value }
export function iconMarkup(name, customIcons = []) { const key = resolveIconName(name); const custom = customIcons.find(item => resolveIconName(item.key) === key); if (custom?.svg_markup) return custom.svg_markup; return registry[key] || registry.pulse || '' }
export function isSystemIcon(name) { return Boolean(registry[resolveIconName(name)]) }
export const systemIconOptions = Object.keys(registry).sort((a,b)=>(labels[a]||a).localeCompare(labels[b]||b,'en')).map(name => ({ name, key:name, label:labels[name] || name.replace(/-/g,' '), markup:registry[name], system:true }))
export function mergeIconOptions(customIcons = []) { const custom = customIcons.map(item => ({ id:item.id, name:item.key, key:item.key, label:item.label, markup:item.svg_markup, system:false, original_name:item.original_name || '' })); return [...systemIconOptions,...custom].sort((a,b)=>a.label.localeCompare(b.label,'en')) }
export const iconOptions = systemIconOptions
