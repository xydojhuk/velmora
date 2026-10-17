export function formatMoney(minor = 0, currency = 'USD') {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency, maximumFractionDigits: 2 }).format(Number(minor) / 100)
}

export function formatDateTime(value) {
  if (!value) return '—'
  return new Intl.DateTimeFormat('en-US', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value))
}

export function formatDate(value) {
  if (!value) return '—'
  return new Intl.DateTimeFormat('en-US', { dateStyle: 'medium' }).format(new Date(value))
}

export function normalizeImage(path) {
  if (!path) return '/img/product-handle.png'
  if (/^https?:\/\//i.test(path)) return path
  return path.startsWith('/') ? path : `/${path}`
}

export function orderStatusLabel(status) {
  return { new: 'New', confirmed: 'Confirmed', processing: 'Processing', shipped: 'Shipped', completed: 'Completed', cancelled: 'Cancelled', returned: 'Returned' }[status] || status || '—'
}

export function paymentStatusLabel(status) {
  return { unpaid: 'Unpaid', pending: 'Pending', paid: 'Paid', refunded: 'Refunded' }[status] || status || '—'
}

export function orderSourceLabel(source) {
  return { website: 'Website', manual: 'Manual', phone: 'Phone', telegram: 'Telegram', viber: 'Viber', instagram: 'Instagram', other: 'Other' }[source] || source || '—'
}

export function auditActionLabel(action) {
  return {
    'auth.login': 'Sign in', 'auth.login.failed': 'Failed sign-in attempt', 'auth.login.locked': 'Sign-in blocked',
    'auth.login.success': 'Successful sign-in', 'auth.logout': 'Signed out', 'auth.password_change.failed': 'Password change failed',
    'auth.password_change.success': 'Password changed', 'auth.refresh.csrf_failed': 'CSRF validation failed',
    'auth.refresh.reuse_detected': 'Refresh token reuse detected', 'auth.refresh.success': 'Session refreshed',
    'order.admin.created': 'Order created in admin', 'order.admin.updated': 'Order updated', 'order.public': 'Checkout request',
    'order.public.bot_rejected': 'Automated order rejected', 'order.public.created': 'Website order created',
    'product.created': 'Product created', 'product.updated': 'Product updated', 'product.deactivated': 'Product deactivated',
    'product.image_uploaded': 'Product image uploaded', 'product.image_deleted': 'Product image deleted', 'product.images_reordered': 'Product images reordered',
    'public.page_visit': 'Page visit', 'security.request_denied': 'Request blocked by security policy', 'settings.updated': 'Store settings updated',
    'settings.shipping_created': 'Shipping method created', 'settings.shipping_updated': 'Shipping method updated', 'settings.shipping_deleted': 'Shipping method deleted',
    'settings.payment_created': 'Payment method created', 'settings.payment_updated': 'Payment method updated', 'settings.payment_deleted': 'Payment method deleted',
    'user.bootstrap_admin.created': 'Initial administrator created', 'user.created': 'User created', 'user.updated': 'User updated', 'user.password_reset': 'User password reset',
    'icon.created': 'Icon added', 'icon.updated': 'Icon renamed', 'icon.file_replaced': 'Icon file replaced', 'icon.deleted': 'Icon deleted'
  }[action] || action || '—'
}

export function auditResourceLabel(resource) {
  return { icon: 'Icon', order: 'Order', page: 'Page', payment_method: 'Payment method', product: 'Product', session: 'Session', settings: 'Settings', shipping_method: 'Shipping method', user: 'User' }[resource] || resource || '—'
}
