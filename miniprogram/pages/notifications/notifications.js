const { api } = require('../../utils/api')
const { isLoggedIn } = require('../../utils/session')

Page({
  data: {
    list: [],
    loading: false
  },
  onShow() {
    if (!isLoggedIn()) {
      wx.redirectTo({ url: '/pages/login/login' })
      return
    }
    this.loadData()
  },
  async loadData() {
    this.setData({ loading: true })
    try {
      const rows = await api.notifications()
      this.setData({ list: Array.isArray(rows) ? rows : [] })
      const unread = (rows || []).filter((item) => !item.is_read).length
      wx.setStorageSync('last_notice_count', unread)
    } catch (_) {
    } finally {
      this.setData({ loading: false })
    }
  },
  async markAllRead() {
    await api.readAllNotifications()
    wx.showToast({ title: '已全部标记已读', icon: 'success' })
    await this.loadData()
  },
  async openItem(e) {
    const id = Number(e.currentTarget.dataset.id || 0)
    if (!id) return
    const row = this.data.list.find((item) => Number(item.id) === id)
    if (!row) return
    if (!row.is_read) {
      await api.readNotification(id)
    }
    await this.loadData()
    const bizType = String(row.biz_type || '')
    if (bizType === 'daily_report_review' && row.biz_id) {
      wx.navigateTo({ url: `/pages/daily-report/daily-report` })
    }
  }
})
