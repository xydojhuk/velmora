import { api } from './client.js'

export const publicApi = {
  config: () => api.get('/public/config').then(r => r.data),
  categories: () => api.get('/public/categories').then(r => r.data),
  products: () => api.get('/public/products').then(r => r.data),
  icons: () => api.get('/public/icons').then(r => r.data),
  product: slug => api.get(`/public/products/${encodeURIComponent(slug)}`).then(r => r.data),
  order: (payload, idempotencyKey) => api.post('/public/orders', payload, { headers: { 'Idempotency-Key': idempotencyKey } }).then(r => r.data),
  visit: payload => api.post('/public/visit', payload).catch(() => null)
}

export const authApi = {
  login: payload => api.post('/auth/login', payload).then(r => r.data),
  me: () => api.get('/auth/me').then(r => r.data),
  refresh: () => api.post('/auth/refresh').then(r => r.data),
  logout: () => api.post('/auth/logout'),
  changePassword: payload => api.post('/auth/change-password', payload)
}

export const adminApi = {
  categories: () => api.get('/admin/categories').then(r => r.data),
  createCategory: payload => api.post('/admin/categories', payload).then(r => r.data),
  updateCategory: (slug, payload) => api.patch(`/admin/categories/${encodeURIComponent(slug)}`, payload).then(r => r.data),
  deleteCategory: slug => api.delete(`/admin/categories/${encodeURIComponent(slug)}`),
  icons: () => api.get('/admin/icons').then(r => r.data),
  createIcon: (label, file) => {
    const form = new FormData()
    form.append('label', label)
    form.append('file', file)
    return api.post('/admin/icons', form).then(r => r.data)
  },
  updateIcon: (id, payload) => api.patch(`/admin/icons/${id}`, payload).then(r => r.data),
  replaceIconFile: (id, file) => {
    const form = new FormData()
    form.append('file', file)
    return api.post(`/admin/icons/${id}/file`, form).then(r => r.data)
  },
  deleteIcon: id => api.delete(`/admin/icons/${id}`),
  dashboard: days => api.get('/admin/analytics/dashboard', { params: { days } }).then(r => r.data),
  orders: params => api.get('/admin/orders', { params }).then(r => r.data),
  order: id => api.get(`/admin/orders/${id}`).then(r => r.data),
  createOrder: payload => api.post('/admin/orders', payload).then(r => r.data),
  updateOrder: (id, payload) => api.patch(`/admin/orders/${id}`, payload).then(r => r.data),
  customers: params => api.get('/admin/customers', { params }).then(r => r.data),
  customer: phone => api.get(`/admin/customers/${encodeURIComponent(phone)}`).then(r => r.data),
  products: params => api.get('/admin/products', { params }).then(r => r.data),
  product: id => api.get(`/admin/products/${id}`).then(r => r.data),
  createProduct: payload => api.post('/admin/products', payload).then(r => r.data),
  updateProduct: (id, payload) => api.patch(`/admin/products/${id}`, payload).then(r => r.data),
  uploadProductImage: (id, file, altText = '') => {
    const form = new FormData()
    form.append('file', file)
    if (altText) form.append('alt_text', altText)
    return api.post(`/admin/products/${id}/images`, form).then(r => r.data)
  },
  deleteProductImage: (id, imageId) => api.delete(`/admin/products/${id}/images/${imageId}`),
  reorderProductImages: (id, imageIds) => api.patch(`/admin/products/${id}/images/order`, { image_ids: imageIds }).then(r => r.data),
  deactivateProduct: id => api.delete(`/admin/products/${id}`),
  users: params => api.get('/admin/users', { params }).then(r => r.data),
  createUser: payload => api.post('/admin/users', payload).then(r => r.data),
  updateUser: (id, payload) => api.patch(`/admin/users/${id}`, payload).then(r => r.data),
  resetPassword: (id, payload) => api.post(`/admin/users/${id}/reset-password`, payload),
  logs: params => api.get('/admin/logs', { params }).then(r => r.data),
  settings: () => api.get('/admin/settings').then(r => r.data),
  updateSettings: payload => api.patch('/admin/settings', payload).then(r => r.data),
  uploadStorefrontImage: file => {
    const form = new FormData()
    form.append('file', file)
    return api.post('/admin/settings/media', form).then(r => r.data)
  },
  deleteStorefrontImage: storageName => api.delete(`/admin/settings/media/${encodeURIComponent(storageName)}`),
  shippingMethods: () => api.get('/admin/settings/shipping').then(r => r.data),
  createShippingMethod: payload => api.post('/admin/settings/shipping', payload).then(r => r.data),
  updateShippingMethod: (id, payload) => api.patch(`/admin/settings/shipping/${id}`, payload).then(r => r.data),
  deleteShippingMethod: id => api.delete(`/admin/settings/shipping/${id}`),
  paymentMethods: () => api.get('/admin/settings/payment').then(r => r.data),
  createPaymentMethod: payload => api.post('/admin/settings/payment', payload).then(r => r.data),
  updatePaymentMethod: (id, payload) => api.patch(`/admin/settings/payment/${id}`, payload).then(r => r.data),
  deletePaymentMethod: id => api.delete(`/admin/settings/payment/${id}`)
}

function readInstallerCsrf() {
  if (typeof document === 'undefined') return ''
  const match = document.cookie.match(/(?:^|; )velmora_install_csrf=([^;]*)/)
  return match ? decodeURIComponent(match[1]) : ''
}

export const installerApi = {
  status: () => api.get('/install/status').then(r => r.data),
  unlock: payload => api.post('/install/unlock', payload).then(r => r.data),
  testDatabase: payload => api.post('/install/database/test', payload, { headers: { 'X-Install-CSRF': readInstallerCsrf() } }).then(r => r.data),
  run: payload => api.post('/install/run', payload, { headers: { 'X-Install-CSRF': readInstallerCsrf() }, timeout: 240000 }).then(r => r.data),
  ready: () => api.get('/install/ready').then(r => r.data)
}
