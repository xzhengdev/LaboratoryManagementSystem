const TOKEN_KEY = 'lab_token'
const PROFILE_KEY = 'lab_profile'

function getToken() {
  return wx.getStorageSync(TOKEN_KEY) || ''
}

function setSession(token, profile) {
  wx.setStorageSync(TOKEN_KEY, token)
  wx.setStorageSync(PROFILE_KEY, profile || {})
}

function clearSession() {
  wx.removeStorageSync(TOKEN_KEY)
  wx.removeStorageSync(PROFILE_KEY)
}

function getProfile() {
  return wx.getStorageSync(PROFILE_KEY) || {}
}

function updateProfile(profile) {
  wx.setStorageSync(PROFILE_KEY, profile || {})
}

function isLoggedIn() {
  return !!getToken()
}

module.exports = { getToken, setSession, clearSession, getProfile, updateProfile, isLoggedIn }
