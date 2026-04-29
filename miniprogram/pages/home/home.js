const { api } = require('../../utils/api')
const { getProfile, isLoggedIn } = require('../../utils/session')

Page({
  data: {
    profileRole: '',
    isTeacher: false,
    labs: [],
    unreadNoticeCount: 0,
    banners: [
      { title: '智慧实验室预约', sub: '随时随地，快速锁定实验资源', image: '/assets/logo.png' },
      { title: '跨校区协作', sub: '多校区资源统一查看与调度', image: '/assets/logo.png' },
      { title: 'AI 智能助手', sub: '自然语言查询预约和排期信息', image: '/assets/logo.png' }
    ]
  },
  onShow() {
    if (!isLoggedIn()) {
      wx.redirectTo({ url: '/pages/login/login' })
      return
    }
    const profile = getProfile() || {}
    const role = String(profile.role || '')
    const isTeacher = role === 'teacher'
    this.setData({
      profileRole: role,
      isTeacher
    })

    this.loadBanners()
    this.loadLabs()
    this.loadUnreadNotifications()
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
  async loadUnreadNotifications() {
    try {
      const result = await api.unreadNotifications()
      const unreadCount = Number(result && result.unread_count ? result.unread_count : 0)
      this.setData({ unreadNoticeCount: unreadCount })
    } catch (_) {
      this.setData({ unreadNoticeCount: 0 })
    }
  },
  goCampuses() { wx.navigateTo({ url: '/pages/campuses/campuses' }) },
  goLabs() { wx.switchTab({ url: '/pages/labs/labs' }) },
  goReservations() { wx.switchTab({ url: '/pages/my-reservations/my-reservations' }) },
  goDailyReport() { wx.navigateTo({ url: '/pages/daily-report/daily-report' }) },
  goAssetRequests() { wx.navigateTo({ url: '/pages/asset-requests/asset-requests' }) },
  goNotifications() { wx.navigateTo({ url: '/pages/notifications/notifications' }) },
  goAgent() { wx.navigateTo({ url: '/pages/agent/agent' }) },
  goLabDetail(e) {
    wx.navigateTo({ url: `/pages/lab-detail/lab-detail?id=${e.currentTarget.dataset.id}` })
  }
})
