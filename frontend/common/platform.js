const LOCAL_BASE_URL = 'http://127.0.0.1:5000/api'

export function getApiBaseUrl() {
  const customBaseUrl = uni.getStorageSync('lab_api_base_url')
  if (customBaseUrl) return customBaseUrl

  const { protocol, hostname } = window.location
  if (!hostname || hostname === 'localhost' || hostname === '127.0.0.1') {
    return LOCAL_BASE_URL
  }
  return `${protocol}//${hostname}:5000/api`
}

export function getPlatformName() {
  return 'H5 / PC'
}

export function getBaseUrlHint() {
  return getApiBaseUrl()
}
