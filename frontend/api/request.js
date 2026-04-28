import { clearSession, getToken } from '../common/session'
import { getApiBaseUrl } from '../common/platform'

// 统一计算接口根地址。
// H5/PC、小程序会在 platform.js 中根据运行环境自动切换。
const BASE_URL = getApiBaseUrl()

export function request({ url, method = 'GET', data = {}, headers = {} }) {
  return new Promise((resolve, reject) => {
    uni.request({
      url: `${BASE_URL}${url}`,
      method,
      data,
      header: {
        // 所有需要鉴权的接口都通过 Authorization 头部传递 JWT。
        Authorization: getToken() ? `Bearer ${getToken()}` : '',
        ...headers
      },
      success: (res) => {
        const payload = res.data || {}
        // 约定 code === 0 为业务成功，直接返回 data 字段即可。
        if (payload.code === 0) {
          resolve(payload.data)
          return
        }
        // 401 说明登录态失效，清空本地 token 并跳回登录页。
        if (res.statusCode === 401) {
          clearSession()
          uni.redirectTo({ url: '/pages/login/index' })
        }
        uni.showToast({ title: payload.message || '请求失败', icon: 'none' })
        reject(payload)
      },
      fail: (error) => {
        // 网络层失败通常是后端没启动、地址不对，或局域网访问异常。
        uni.showToast({ title: '网络请求失败，请检查后端地址', icon: 'none' })
        reject(error)
      }
    })
  })
}
