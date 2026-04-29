const { api } = require('../../utils/api')
const { getProfile, isLoggedIn } = require('../../utils/session')

Page({
  data: {
    profile: {},
    summary: {
      pending: 0,
      approved: 0,
      rejected: 0
    },
    labs: [],
    labIndex: -1,
    selectedLabName: '请选择实验室',
    form: {
      asset_name: '',
      category: '',
      quantity: 1,
      unit_price: '',
      reason: ''
    },
    amountText: '0.00',
    submitting: false
  },

  onShow() {
    if (!isLoggedIn()) {
      wx.redirectTo({ url: '/pages/login/login' })
      return
    }
    const profile = getProfile() || {}
    if (String(profile.role || '') !== 'teacher') {
      wx.showToast({ title: '仅教师可使用资产申报', icon: 'none' })
      setTimeout(() => wx.navigateBack({ delta: 1 }), 600)
      return
    }
    this.setData({ profile })
    this.loadLabs()
    this.loadSummary()
  },

  async loadLabs() {
    try {
      const res = await api.labs({ page: 1, per_page: 100, campus_id: this.data.profile.campus_id })
      const list = (res.items || res || []).map((row) => ({
        id: row.id,
        name: row.lab_name || `实验室${row.id}`
      }))
      if (!list.length) {
        this.setData({
          labs: [],
          labIndex: -1,
          selectedLabName: '请先创建实验室'
        })
        return
      }
      this.setData({
        labs: list,
        labIndex: 0,
        selectedLabName: list[0].name
      })
    } catch (_) {}
  },

  async loadSummary() {
    try {
      const rows = await api.myAssetRequests()
      const list = Array.isArray(rows) ? rows : []
      const summary = { pending: 0, approved: 0, rejected: 0 }
      list.forEach((item) => {
        const key = String(item.status || '').toLowerCase()
        if (key === 'pending') summary.pending += 1
        if (key === 'approved') summary.approved += 1
        if (key === 'rejected') summary.rejected += 1
      })
      this.setData({ summary })
    } catch (_) {
      this.setData({ summary: { pending: 0, approved: 0, rejected: 0 } })
    }
  },

  onLabChange(e) {
    const nextIndex = Number(e.detail.value || 0)
    const selected = this.data.labs[nextIndex] || { name: '不指定实验室' }
    this.setData({ labIndex: nextIndex, selectedLabName: selected.name || '不指定实验室' })
  },

  onInput(e) {
    const field = e.currentTarget.dataset.field
    const value = e.detail.value
    this.setData({ [`form.${field}`]: value }, () => {
      this.refreshAmountText()
    })
  },

  resetForm() {
    const selected = this.data.labs[0]
    this.setData({
      form: { asset_name: '', category: '', quantity: 1, unit_price: '', reason: '' },
      labIndex: selected ? 0 : -1,
      selectedLabName: selected ? selected.name : '请选择实验室',
      amountText: '0.00'
    })
  },

  goRecords() {
    wx.navigateTo({ url: '/pages/asset-request-records/asset-request-records' })
  },

  normalizePayload() {
    const selectedLab = this.data.labs[this.data.labIndex] || { id: '' }
    return {
      lab_id: selectedLab.id || '',
      asset_name: String(this.data.form.asset_name || '').trim(),
      category: String(this.data.form.category || '').trim(),
      quantity: Number(this.data.form.quantity || 0),
      unit_price: Number(this.data.form.unit_price || 0),
      reason: String(this.data.form.reason || '').trim()
    }
  },

  validate(payload) {
    if (!payload.lab_id) return '请选择实验室'
    if (!payload.asset_name) return '请填写资产名称'
    if (!payload.category) return '请填写资产类别'
    if (!Number.isFinite(payload.quantity) || payload.quantity <= 0) return '数量必须大于 0'
    if (!Number.isFinite(payload.unit_price) || payload.unit_price <= 0) return '单价必须大于 0'
    return ''
  },

  async submitRequest() {
    if (this.data.submitting) return
    const payload = this.normalizePayload()
    if (!this.data.labs.length) {
      wx.showToast({ title: '当前校区暂无实验室，请先创建', icon: 'none' })
      return
    }
    const error = this.validate(payload)
    if (error) {
      wx.showToast({ title: error, icon: 'none' })
      return
    }

    this.setData({ submitting: true })
    try {
      await api.createAssetRequest(payload)
      wx.showToast({ title: '申报成功', icon: 'success' })
      this.resetForm()
      this.loadSummary()
      setTimeout(() => {
        wx.navigateTo({ url: '/pages/asset-request-records/asset-request-records' })
      }, 250)
    } catch (_) {
    } finally {
      this.setData({ submitting: false })
    }
  },

  refreshAmountText() {
    const qty = Number(this.data.form.quantity || 0)
    const unit = Number(this.data.form.unit_price || 0)
    if (!Number.isFinite(qty) || !Number.isFinite(unit)) {
      this.setData({ amountText: '0.00' })
      return
    }
    this.setData({ amountText: (qty * unit).toFixed(2) })
  }
})
