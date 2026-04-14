const MP_BASE_URL = 'http://192.168.1.5:5000/api'
const LOCAL_BASE_URL = 'http://127.0.0.1:5000/api'

export function getApiBaseUrl() {
  // 如果用户手动在 storage 里指定了后端地址，则优先使用手动配置。
  const customBaseUrl = uni.getStorageSync('lab_api_base_url')
  if (customBaseUrl) {
    return customBaseUrl
  }

  // #ifdef H5
  // H5/PC 环境优先取当前浏览器访问的主机名，便于同一局域网设备调试。
  const { protocol, hostname } = window.location
  if (!hostname || hostname === 'localhost' || hostname === '127.0.0.1') {
    return LOCAL_BASE_URL
  }
  return `${protocol}//${hostname}:5000/api`
  // #endif

  // #ifdef MP-WEIXIN
  // 微信小程序不能直接访问 127.0.0.1，因此默认走电脑当前局域网 IP。
  return MP_BASE_URL
  // #endif

  return LOCAL_BASE_URL
}

export function getPlatformName() {
  // #ifdef H5
  return 'H5 / PC'
  // #endif

  // #ifdef MP-WEIXIN
  return '微信小程序'
  // #endif

  return '多端环境'
}

export function getBaseUrlHint() {
  // 用于登录页、首页等场景展示当前联调地址。
  return getApiBaseUrl()
}
