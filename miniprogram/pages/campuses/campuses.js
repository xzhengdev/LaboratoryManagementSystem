const { api } = require('../../utils/api')
const { isLoggedIn } = require('../../utils/session')

const COLORS = ['#4A90E2','#27AE60','#E25454','#9B59B6','#F5A623','#1ABC9C']

Page({
  data: {
    list: []
  },
  onShow() {
    if (!isLoggedIn()) { wx.redirectTo({ url: '/pages/login/login' }); return }
    this.loadCampuses()
  },
  async loadCampuses() {
    try {
      const res = await api.campuses()
      const list = (res.items || res || []).map((c, i) => ({
        ...c, color: COLORS[i % COLORS.length]
      }))
      this.setData({ list })
    } catch (_) {}
  },
  goLabs(e) {
    const campusId = e.currentTarget.dataset.id
    wx.setStorageSync('campus_entry_campus_id', String(campusId || ''))
    wx.switchTab({ url: '/pages/labs/labs' })
  }
})
