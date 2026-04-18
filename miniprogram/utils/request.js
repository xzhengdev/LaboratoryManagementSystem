// const BASE_URL = 'https://10.151.65.52:5000/api'
const BASE_URL = 'http://127.0.0.1:5000/api'
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
    if (loading) wx.showLoading({ title: loadingTitle, mask: true })
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
        if (loading) wx.hideLoading()
        if (res.statusCode === 401) {
          wx.removeStorageSync('lab_token')
          wx.removeStorageSync('lab_profile')
          wx.reLaunch({ url: '/pages/login/login' })
          reject(res.data)
          return
        }
        if (res.data && res.data.code === 0) {
          resolve(res.data.data)
        } else {
          const msg = (res.data && res.data.message) || '请求失败'
          wx.showToast({ title: msg, icon: 'none', duration: 2000 })
          reject(res.data)
        }
      },
      fail(err) {
        if (loading) wx.hideLoading()
        wx.showToast({ title: '网络错误，请检查连接', icon: 'none' })
        reject(err)
      }
    })
  })
}

module.exports = { request, BASE_URL }
