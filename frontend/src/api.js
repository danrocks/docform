import axios from 'axios'

const api = axios.create({ baseURL: '/api' })

// Add request interceptor to ensure trailing slash on pathnames
// api.interceptors.request.use(config => {
//   try {
//     // build an absolute URL using the page origin so we can safely manipulate pathname/search/hash
//     const full = new URL(config.url, window.location.origin)
//     if (!full.pathname.endsWith('/')) {
//       full.pathname = full.pathname + '/'
//       config.url = full.pathname + full.search + full.hash
//     }
//   } catch (e) {
//     // ignore malformed/absolute URLs
//   }
//   return config
// })

api.interceptors.response.use(
  r => r,
  err => {
    if (err.response?.status === 401) {
      localStorage.removeItem('token')
      window.location.href = '/login'
    }
    return Promise.reject(err)
  }
)

export default api
