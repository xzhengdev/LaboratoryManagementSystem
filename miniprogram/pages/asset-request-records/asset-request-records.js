const { api } = require('../../utils/api')
const { getProfile, isLoggedIn } = require('../../utils/session')

Page({
  data: {
    profile: {},
    allRequests: [],
    list: [],
    activeStatus: 'all',
    keyword: '',
    summary: {
      total: 0,
      pending: 0,
      approved: 0,
      rejected: 0
    }
  },

  onShow() {
    if (!isLoggedIn()) {
      wx.redirectTo({ url: '/pages/login/login' })
      return
    }
    const profile = getProfile() || {}
    if (String(profile.role || '') !== 'teacher') {
      wx.showToast({ title: '仅教师可查看', icon: 'none' })
      setTimeout(() => wx.navigateBack({ delta: 1 }), 600)
      return
    }
    this.setData({ profile })
    this.loadRequests()
  },

  async loadRequests() {
    try {
      const rows = await api.myAssetRequests()
      const list = Array.isArray(rows) ? rows : []
      const normalized = list.map((item) => ({
        ...item,
        status_text: this.statusText(item.status),
        created_text: this.formatTime(item.created_at),
        unit_price_text: this.moneyText(item.unit_price),
        amount_text: this.moneyText(item.amount)
      }))
      this.setData({
        allRequests: normalized,
        summary: this.buildSummary(normalized)
      })
      this.applyFilter()
    } catch (_) {
      this.setData({
        allRequests: [],
        list: [],
        summary: { total: 0, pending: 0, approved: 0, rejected: 0 }
      })
    }
  },

  buildSummary(list) {
    const summary = { total: list.length, pending: 0, approved: 0, rejected: 0 }
    list.forEach((item) => {
      const key = String(item.status || '').toLowerCase()
      if (key === 'pending') summary.pending += 1
      if (key === 'approved') summary.approved += 1
      if (key === 'rejected') summary.rejected += 1
    })
    return summary
  },

  setStatus(e) {
    const activeStatus = e.currentTarget.dataset.status || 'all'
    this.setData({ activeStatus }, () => this.applyFilter())
  },

  onKeywordInput(e) {
    this.setData({ keyword: e.detail.value || '' })
  },

  applyFilter() {
    const text = String(this.data.keyword || '').trim().toLowerCase()
    const active = this.data.activeStatus
    const list = this.data.allRequests.filter((item) => {
      const statusOK = active === 'all' || String(item.status || '').toLowerCase() === active
      const keywordOK = !text || `${item.request_no || ''}${item.asset_name || ''}`.toLowerCase().includes(text)
      return statusOK && keywordOK
    })
    this.setData({ list })
  },

  statusText(status) {
    const map = {
      pending: '待审批',
      approved: '已通过',
      rejected: '已驳回'
    }
    return map[String(status || '').toLowerCase()] || String(status || '--')
  },

  formatTime(value) {
    const text = String(value || '').trim()
    if (!text) return '--'
    return text.replace('T', ' ').slice(0, 19)
  },

  moneyText(value) {
    const num = Number(value || 0)
    if (!Number.isFinite(num)) return '0.00'
    return num.toFixed(2)
  }
})