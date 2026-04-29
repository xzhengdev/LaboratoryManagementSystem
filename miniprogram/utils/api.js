const { request, BASE_URL } = require('./request')
const { getToken } = require('./session')
const API_ORIGIN = String(BASE_URL || '').replace(/\/api\/?$/, '')
const createIdempotencyKey = () =>
  `resv-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`
const createDailyReportIdempotencyKey = () =>
  `daily-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`

const normalizeMediaUrl = (rawUrl) => {
  const text = String(rawUrl || '').trim()
  if (!text) return ''
  if (/^https?:\/\//i.test(text)) return text
  if (text.startsWith('//')) return `https:${text}`
  if (text.startsWith('/')) return `${API_ORIGIN}${text}`
  return `${API_ORIGIN}/${text}`
}

const normalizeLabPhotos = (photos) => {
  if (!Array.isArray(photos)) return []
  return photos.map((item) => normalizeMediaUrl(item))
}

const normalizePhotoObjects = (photos) => {
  if (!Array.isArray(photos)) return []
  return photos.map((item) => ({
    ...item,
    url: normalizeMediaUrl(item && item.url)
  }))
}

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
  campuses: async () => {
    const rows = await request({ url: '/campuses' })
    if (!Array.isArray(rows)) return rows
    return rows.map((item) => ({ ...item, cover_url: normalizeMediaUrl(item && item.cover_url) }))
  },
  labs: async (params = {}) => {
    const data = await request({ url: '/labs', data: params })
    if (Array.isArray(data)) {
      return data.map((item) => ({ ...item, photos: normalizeLabPhotos(item && item.photos) }))
    }
    if (data && Array.isArray(data.items)) {
      return {
        ...data,
        items: data.items.map((item) => ({ ...item, photos: normalizeLabPhotos(item && item.photos) }))
      }
    }
    return data
  },
  labDetail: async (id) => {
    const item = await request({ url: `/labs/${id}` })
    if (!item || typeof item !== 'object') return item
    return { ...item, photos: normalizeLabPhotos(item.photos) }
  },
  labSchedule: (id, date) => request({ url: `/labs/${id}/schedule`, data: { date } }),
  equipment: (params = {}) => request({ url: '/equipment', data: params }),
  createReservation: (data, options = {}) =>
    request({
      url: '/reservations',
      method: 'POST',
      data,
      headers: {
        'Idempotency-Key': options.idempotencyKey || createIdempotencyKey()
      }
    }),
  myReservations: () => request({ url: '/reservations/my' }),
  reservationDetail: (id) => request({ url: `/reservations/${id}` }),
  cancelReservation: (id) => request({ url: `/reservations/${id}/cancel`, method: 'POST' }),
  deleteReservation: (id) => request({ url: `/reservations/${id}`, method: 'DELETE' }),
  uploadDailyReportPhoto: (filePath, data = {}) => new Promise((resolve, reject) => {
    wx.uploadFile({
      url: `${BASE_URL}/lab-reports/photos/upload`,
      filePath,
      name: 'file',
      formData: {
        lab_id: data.lab_id || '',
        campus_id: data.campus_id || ''
      },
      header: { Authorization: getToken() ? `Bearer ${getToken()}` : '' },
      success(res) {
        try {
          const payload = typeof res.data === 'string' ? JSON.parse(res.data) : res.data
          if (res.statusCode === 200 && payload.code === 0) {
            resolve({ ...payload.data, url: normalizeMediaUrl(payload.data && payload.data.url) })
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
  createDailyReport: (data, options = {}) =>
    request({
      url: '/lab-reports',
      method: 'POST',
      data,
      headers: {
        'Idempotency-Key': options.idempotencyKey || createDailyReportIdempotencyKey()
      }
    }),
  myDailyReports: async (params = {}) => {
    const rows = await request({ url: '/lab-reports', data: params })
    if (!Array.isArray(rows)) return rows
    return rows.map((item) => ({
      ...item,
      photos: normalizePhotoObjects(item && item.photos)
    }))
  },
  notifications: (params = {}) => request({ url: '/notifications', data: params }),
  unreadNotifications: () => request({ url: '/notifications/unread-count' }),
  readNotification: (id) => request({ url: `/notifications/${id}/read`, method: 'POST' }),
  readAllNotifications: () => request({ url: '/notifications/read-all', method: 'POST' }),
  agentChat: (message, options = {}) => request({
    url: '/agent/chat',
    method: 'POST',
    data: { message },
    ...options
  })
}

module.exports = { api }
