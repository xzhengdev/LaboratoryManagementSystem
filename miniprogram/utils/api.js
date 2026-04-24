const { request, BASE_URL } = require('./request')
const { getToken } = require('./session')

const api = {
  login: (data) => request({ url: '/auth/login', method: 'POST', data }),
  profile: () => request({ url: '/auth/profile' }),
  updateProfile: (data) => request({ url: '/auth/profile', method: 'PUT', data }),
  changePassword: (data) => request({ url: '/auth/change-password', method: 'POST', data }),
  uploadAvatar: (filePath) => new Promise((resolve, reject) => {
    wx.uploadFile({
      url: `${BASE_URL}/auth/upload-avatar`,
      filePath,
      name: 'file',
      header: { Authorization: getToken() ? `Bearer ${getToken()}` : '' },
      success(res) {
        try {
          const payload = typeof res.data === 'string' ? JSON.parse(res.data) : res.data
          if (res.statusCode === 200 && payload.code === 0) {
            resolve(payload.data)
          } else {
            wx.showToast({ title: payload.message || '上传失败', icon: 'none' })
            reject(payload)
          }
        } catch (e) {
          reject(e)
        }
      },
      fail(err) {
        wx.showToast({ title: '上传失败', icon: 'none' })
        reject(err)
      }
    })
  }),
  campuses: () => request({ url: '/campuses' }),
  labs: (params = {}) => request({ url: '/labs', data: params }),
  labDetail: (id) => request({ url: `/labs/${id}` }),
  labSchedule: (id, date) => request({ url: `/labs/${id}/schedule`, data: { date } }),
  equipment: (params = {}) => request({ url: '/equipment', data: params }),
  createReservation: (data) => request({ url: '/reservations', method: 'POST', data }),
  myReservations: () => request({ url: '/reservations/my' }),
  reservationDetail: (id) => request({ url: `/reservations/${id}` }),
  cancelReservation: (id) => request({ url: `/reservations/${id}/cancel`, method: 'POST' }),
  deleteReservation: (id) => request({ url: `/reservations/${id}`, method: 'DELETE' }),
  agentChat: (message, options = {}) => request({
    url: '/agent/chat',
    method: 'POST',
    data: { message },
    ...options
  })
}

module.exports = { api }
