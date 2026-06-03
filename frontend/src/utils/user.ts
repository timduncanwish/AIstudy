export function getUserId(): string {
  let id = uni.getStorageSync('device_id')
  if (!id) {
    id = 'device_' + Date.now() + '_' + Math.random().toString(36).slice(2, 8)
    uni.setStorageSync('device_id', id)
  }
  return id
}
