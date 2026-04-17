const BASE_URL = 'https://6a9d-61-50-133-187.ngrok-free.app/api'

function getToken() {
  return wx.getStorageSync('lab_token') || ''
}

function request({ url, method = 'GET', data = {} }) {
  return new Promise((resolve, reject) => {
    wx.showLoading({ title: '加载中', mask: true })
    wx.request({
      url: BASE_URL + url,
      method,
      data,
      header: {
        'Content-Type': 'application/json',
        Authorization: getToken() ? `Bearer ${getToken()}` : ''
      },
      success(res) {
        wx.hideLoading()
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
        wx.hideLoading()
        wx.showToast({ title: '网络错误，请检查连接', icon: 'none' })
        reject(err)
      }
    })
  })
}

module.exports = { request, BASE_URL }
