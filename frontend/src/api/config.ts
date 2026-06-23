// 开发时用 localhost，生产时通过 .env.production 注入 VITE_API_BASE_URL
export const BASE_URL: string =
  (typeof import.meta !== 'undefined' && (import.meta as any).env?.VITE_API_BASE_URL) ||
  'http://localhost:8000'

export function request<T>(options: {
  url: string
  method: 'GET' | 'POST' | 'PUT' | 'DELETE'
  data?: any
  header?: Record<string, string>
}): Promise<T> {
  const userId = uni.getStorageSync('db_user_id') || uni.getStorageSync('device_id') || ''
  const token = uni.getStorageSync('token') || ''
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    'X-User-Id': userId,
    ...options.header,
  }
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }
  return new Promise((resolve, reject) => {
    uni.request({
      url: BASE_URL + options.url,
      method: options.method,
      data: options.data,
      header: headers,
      success: (res) => {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(res.data as T)
        } else if (res.statusCode === 401) {
          uni.removeStorageSync('token')
          uni.removeStorageSync('db_user_id')
          uni.removeStorageSync('nickname')
          uni.showToast({ title: '登录已过期，请重新登录', icon: 'none' })
          reject(res)
        } else {
          reject(res)
        }
      },
      fail: reject,
    })
  })
}
