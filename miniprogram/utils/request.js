// const BASE_URL = 'http://60.205.216.140/api'
const BASE_URL = 'http://127.0.0.1:5000/api'
// const BASE_URL = 'http://172.20.10.7:5000/api'
// const BASE_URL = 'http://10.151.102.78:5000/api'
function getToken() {
  return wx.getStorageSync('lab_token') || ''
}

function request({
  url,
  method = 'GET',
  data = {},
  loading = true,
  loadingTitle = '加载中',
  timeout = 15000
}) {
  return new Promise((resolve, reject) => {
    if (loading) wx.showLoading({
      title: loadingTitle,
      mask: true
    })

    const isLoginApi = String(url || '').includes('/auth/login')

    wx.request({
      url: BASE_URL + url,
      method,
      data,
      timeout,
      header: {
        'Content-Type': 'application/json',
        Authorization: getToken() ? `Bearer ${getToken()}` : ''
      },
      success(res) {
        console.log('[MP][REQUEST]', method, url, 'status=', res.statusCode, 'payload=', res.data)
        if (loading) wx.hideLoading()

        if (res.statusCode === 401) {
          // 登录接口 401 代表账号/密码错误，不强制跳转，交由页面展示提示。
          if (!isLoginApi) {
            wx.removeStorageSync('lab_token')
            wx.removeStorageSync('lab_profile')
            wx.reLaunch({
              url: '/pages/login/login'
            })
          }
          reject(res.data)
          return
        }

        if (res.data && res.data.code === 0) {
          resolve(res.data.data)
          return
        }

        const msg = (res.data && res.data.message) || '请求失败'
        wx.showToast({
          title: msg,
          icon: 'none',
          duration: 2000
        })
        reject(res.data)
      },
      fail(err) {
        console.error('[MP][REQUEST][FAIL]', method, url, err)
        if (loading) wx.hideLoading()
        wx.showToast({
          title: '网络错误，请检查连接',
          icon: 'none'
        })
        reject(err)
      }
    })
  })
}

module.exports = {
  request,
  BASE_URL
}