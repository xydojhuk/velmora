import axios from 'axios'
import { readCookie } from '../utils/cookies.js'

const clientBaseURL = import.meta.env.VITE_API_BASE_URL || '/api/v1'

export const api = axios.create({
  baseURL: clientBaseURL,
  withCredentials: true,
  timeout: 15000,
  headers: {
    Accept: 'application/json'
  }
})

api.interceptors.request.use(config => {
  const method = String(config.method || 'get').toLowerCase()
  if (['post', 'put', 'patch', 'delete'].includes(method)) {
    const token = readCookie('velmora_csrf')
    if (token) config.headers['X-CSRF-Token'] = token
  }
  return config
})

let refreshing = null

api.interceptors.response.use(
  response => response,
  async error => {
    const original = error.config
    const status = error.response?.status
    const refreshRequest = String(original?.url || '').includes('/auth/refresh')
    const loginRequest = String(original?.url || '').includes('/auth/login')
    const installerRequest = String(original?.url || '').includes('/install/') || String(original?.url || '').endsWith('/install')
    if (status !== 401 || !original || original.__retried || refreshRequest || loginRequest || installerRequest) {
      return Promise.reject(error)
    }
    original.__retried = true
    try {
      if (!refreshing) {
        refreshing = api.post('/auth/refresh').finally(() => {
          refreshing = null
        })
      }
      await refreshing
      return api(original)
    } catch {
      if (typeof window !== 'undefined') window.dispatchEvent(new CustomEvent('velmora:auth-expired'))
      return Promise.reject(error)
    }
  }
)

export function createServerApi(baseURL, cookie = '') {
  return axios.create({
    baseURL,
    timeout: 10000,
    headers: {
      Accept: 'application/json',
      ...(cookie ? { Cookie: cookie } : {})
    }
  })
}
