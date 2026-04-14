import { getDefaultAdminPath, routes } from '../config/navigation'

const TOKEN_KEY = 'lab_token'
const PROFILE_KEY = 'lab_profile'

const ADMIN_ROLES = ['lab_admin', 'system_admin']

export function getToken() {
  return uni.getStorageSync(TOKEN_KEY) || ''
}

export function setSession(token, profile) {
  uni.setStorageSync(TOKEN_KEY, token)
  uni.setStorageSync(PROFILE_KEY, profile || {})
}

export function clearSession() {
  uni.removeStorageSync(TOKEN_KEY)
  uni.removeStorageSync(PROFILE_KEY)
}

export function updateProfile(profile) {
  uni.setStorageSync(PROFILE_KEY, profile || {})
}

export function getProfile() {
  return uni.getStorageSync(PROFILE_KEY) || {}
}

export function isAdminRole(role) {
  return ADMIN_ROLES.includes(role)
}

export function getLoginLandingPage(role) {
  return isAdminRole(role) ? getDefaultAdminPath(role) : routes.home
}
