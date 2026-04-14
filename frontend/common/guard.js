import { getToken } from './session'

export function requireLogin() {
  // 页面级登录守卫：
  // 若本地没有 token，则直接跳回登录页，并阻止当前页面继续执行。
  const token = getToken()
  if (!token) {
    uni.redirectTo({ url: '/pages/login/index' })
    return false
  }
  return true
}
