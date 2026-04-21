const { api } = require('../../utils/api')
const { isLoggedIn } = require('../../utils/session')

Page({
  data: {
    labs: [],
    banners: [
      { title: '智慧实验室预约', sub: '随时随地，快速锁定实验资源', image: '/assets/logo.png' },
      { title: '跨校区协同', sub: '多校区资源统一查看与调度', image: '/assets/logo.png' },
      { title: 'AI 智能助手', sub: '自然语言查询预约和排期信息', image: '/assets/logo.png' }
    ]
  },
  onShow() {
    if (!isLoggedIn()) {
      wx.redirectTo({ url: '/pages/login/login' })
      return
    }
    this.loadBanners()
    this.loadLabs()
  },
  async loadBanners() {
    try {
      const campuses = await api.campuses()
      const list = Array.isArray(campuses) ? campuses : []
      const imageBanners = list
        .filter((item) => item && item.cover_url)
        .slice(0, 5)
        .map((item) => ({
          title: item.campus_name || '校区实验室资源',
          sub: item.description || item.address || '查看该校区可预约实验室与开放时段',
          image: item.cover_url
        }))

      if (imageBanners.length) {
        this.setData({ banners: imageBanners })
      }
    } catch (_) {}
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
