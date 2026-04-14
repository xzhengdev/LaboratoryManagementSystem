const TOKEN_KEY = 'lab_token'
const PROFILE_KEY = 'lab_profile'

const ADMIN_ROLES = ['lab_admin', 'system_admin']

export function getToken() {
  // 读取本地缓存中的登录令牌。
  return uni.getStorageSync(TOKEN_KEY) || ''
}

export function setSession(token, profile) {
  // 登录成功后同时写入 token 与用户信息，减少页面重复请求。
  uni.setStorageSync(TOKEN_KEY, token)
  uni.setStorageSync(PROFILE_KEY, profile || {})
}

export function clearSession() {
  // 退出登录或 token 失效时统一清空会话信息。
  uni.removeStorageSync(TOKEN_KEY)
  uni.removeStorageSync(PROFILE_KEY)
}

export function updateProfile(profile) {
  // 某些页面会重新拉取最新个人信息，这里只更新 profile，不改 token。
  uni.setStorageSync(PROFILE_KEY, profile || {})
}

export function getProfile() {
  // 返回当前已缓存的用户信息。
  return uni.getStorageSync(PROFILE_KEY) || {}
}

export function isAdminRole(role) {
  // 管理端页面仅允许实验室管理员和系统管理员进入。
  return ADMIN_ROLES.includes(role)
}

export function getLoginLandingPage(role) {
  return isAdminRole(role) ? '/pages/admin-dashboard/index' : '/pages/home/index'
}
