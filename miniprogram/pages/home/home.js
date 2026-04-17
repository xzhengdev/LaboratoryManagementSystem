const { api } = require('../../utils/api')
const { isLoggedIn } = require('../../utils/session')

Page({
  data: {
    labs: [],
    banners: [
      { title: '智慧实验室预约', sub: '随时随地，轻松预约', bg: 'linear-gradient(135deg,#4A90E2,#2c6fbe)' },
      { title: '跨校区协作', sub: '多校区资源统一管理', bg: 'linear-gradient(135deg,#27AE60,#1e8449)' },
      { title: 'AI智能助手', sub: '自然语言查询预约信息', bg: 'linear-gradient(135deg,#9B59B6,#7d3c98)' }
    ]
  },
  onShow() {
    if (!isLoggedIn()) {
      wx.redirectTo({ url: '/pages/login/login' })
      return
    }
    this.loadLabs()
  },
  async loadLabs() {
    try {
      const res = await api.labs({ page: 1, per_page: 5 })
      const list = (res.items || res || []).slice(0, 5)
      this.setData({ labs: list })
    } catch (_) {}
  },
  goCampuses() { wx.navigateTo({ url: '/pages/campuses/campuses' }) },
  goLabs() { wx.switchTab({ url: '/pages/labs/labs' }) },
  goReservations() { wx.switchTab({ url: '/pages/my-reservations/my-reservations' }) },
  goAgent() { wx.navigateTo({ url: '/pages/agent/agent' }) },
  goLabDetail(e) {
    wx.navigateTo({ url: `/pages/lab-detail/lab-detail?id=${e.currentTarget.dataset.id}` })
  }
})
