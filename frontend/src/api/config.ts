const BASE_URL = 'http://localhost:8000'

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
        } else {
          reject(res)
        }
      },
      fail: reject,
    })
  })
}
