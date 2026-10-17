export function readCookie(name) {
  if (typeof document === 'undefined') return ''
  const prefix = `${encodeURIComponent(name)}=`
  const item = document.cookie.split('; ').find(row => row.startsWith(prefix))
  return item ? decodeURIComponent(item.slice(prefix.length)) : ''
}
