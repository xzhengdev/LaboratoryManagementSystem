const { api } = require('../../utils/api')
const { getProfile, isLoggedIn } = require('../../utils/session')

Page({
  data: {
    profile: {},
    budget: null,
    requests: [],
    labs: [],
    labIndex: 0,
    selectedLabName: '不指定实验室',
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
    this.loadBudget()
    this.loadRequests()
  },

  async loadLabs() {
    try {
      const res = await api.labs({ page: 1, per_page: 100, campus_id: this.data.profile.campus_id })
      const list = (res.items || res || []).map((row) => ({
        id: row.id,
        name: row.lab_name || `实验室${row.id}`
      }))
      this.setData({
        labs: [{ id: '', name: '不指定实验室' }, ...list],
        labIndex: 0,
        selectedLabName: '不指定实验室'
      })
    } catch (_) {}
  },

  async loadBudget() {
    try {
      const budget = await api.assetCurrentBudget()
      this.setData({ budget: budget || null })
    } catch (_) {
      this.setData({ budget: null })
    }
  },

  async loadRequests() {
    try {
      const rows = await api.myAssetRequests()
      const list = Array.isArray(rows) ? rows : []
      this.setData({
        requests: list.map((item) => ({
          ...item,
          status_text: this.statusText(item.status)
        }))
      })
    } catch (_) {
      this.setData({ requests: [] })
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

  normalizePayload() {
    const selectedLab = this.data.labs[this.data.labIndex] || { id: '' }
    return {
      lab_id: selectedLab.id || null,
      asset_name: String(this.data.form.asset_name || '').trim(),
      category: String(this.data.form.category || '').trim(),
      quantity: Number(this.data.form.quantity || 0),
      unit_price: Number(this.data.form.unit_price || 0),
      reason: String(this.data.form.reason || '').trim()
    }
  },

  validate(payload) {
    if (!payload.asset_name) return '请填写资产名称'
    if (!payload.category) return '请填写资产类别'
    if (!Number.isFinite(payload.quantity) || payload.quantity <= 0) return '数量必须大于 0'
    if (!Number.isFinite(payload.unit_price) || payload.unit_price <= 0) return '单价必须大于 0'
    return ''
  },

  async submitRequest() {
    if (this.data.submitting) return
    const payload = this.normalizePayload()
    const error = this.validate(payload)
    if (error) {
      wx.showToast({ title: error, icon: 'none' })
      return
    }

    this.setData({ submitting: true })
    try {
      await api.createAssetRequest(payload)
      wx.showToast({ title: '申报成功', icon: 'success' })
      this.setData({
        form: { asset_name: '', category: '', quantity: 1, unit_price: '', reason: '' },
        labIndex: 0,
        selectedLabName: '不指定实验室',
        amountText: '0.00'
      })
      this.loadBudget()
      this.loadRequests()
    } catch (_) {
    } finally {
      this.setData({ submitting: false })
    }
  },

  statusText(status) {
    const map = {
      pending: '待审批',
      approved: '已通过',
      rejected: '已驳回'
    }
    return map[String(status || '').toLowerCase()] || String(status || '-')
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
