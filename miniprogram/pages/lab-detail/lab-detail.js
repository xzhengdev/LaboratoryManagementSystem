const { api } = require('../../utils/api')

const COLORS = ['#4A90E2', '#27AE60', '#E25454', '#9B59B6', '#F5A623', '#1ABC9C']
const STATUS_TEXT = {
  pending: '\u5f85\u5ba1\u6279',
  approved: '\u5df2\u6279\u51c6',
  rejected: '\u5df2\u62d2\u7edd',
  cancelled: '\u5df2\u53d6\u6d88',
  completed: '\u5df2\u5b8c\u6210'
}

function today() {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

function toMinutes(raw) {
  const safe = String(raw || '').slice(0, 5)
  const [hour = 0, minute = 0] = safe.split(':').map((item) => Number(item || 0))
  return hour * 60 + minute
}

function normalizeLabStatus(lab) {
  const safeLab = lab || {}
  const openMinute = toMinutes(safeLab.open_time || '08:00')
  const closeMinute = toMinutes(safeLab.close_time || '22:00')
  const now = new Date()
  const nowMinute = now.getHours() * 60 + now.getMinutes()
  const isActive = String(safeLab.status || '') === 'active'
  const isWithinOpenHours = nowMinute >= openMinute && nowMinute < closeMinute
  const isOpen = isActive && isWithinOpenHours

  return {
    ...safeLab,
    current_status_text: isOpen ? '\u5f00\u653e' : '\u5173\u95ed',
    current_status_class: isOpen ? 'green' : 'gray'
  }
}

Page({
  data: {
    lab: {},
    equipment: [],
    schedule: [],
    activeTab: 'info',
    scheduleDate: today(),
    color: '#4A90E2',
    statusText: STATUS_TEXT
  },

  onLoad(options) {
    this.labId = options.id
    const idx = parseInt(options.id, 10) || 0
    this.setData({ color: COLORS[idx % COLORS.length] })
    this.loadLab()
    this.loadEquipment()
  },

  async loadLab() {
    try {
      const lab = normalizeLabStatus(await api.labDetail(this.labId))
      this.setData({ lab })
      wx.setNavigationBarTitle({ title: lab.lab_name || '\u5b9e\u9a8c\u5ba4\u8be6\u60c5' })
    } catch (_) {}
  },

  async loadEquipment() {
    try {
      const res = await api.equipment({ lab_id: this.labId })
      this.setData({ equipment: res.items || res || [] })
    } catch (_) {}
  },

  async loadSchedule() {
    try {
      const res = await api.labSchedule(this.labId, this.data.scheduleDate)
      this.setData({ schedule: res.reservations || res || [] })
    } catch (_) {}
  },

  switchTab(e) {
    const tab = e.currentTarget.dataset.tab
    this.setData({ activeTab: tab })
    if (tab === 'schedule') this.loadSchedule()
  },

  onDateChange(e) {
    this.setData({ scheduleDate: e.detail.value }, () => this.loadSchedule())
  },

  goReserve() {
    const campusId = (this.data.lab && this.data.lab.campus_id) || ''
    const query = campusId ? `id=${this.labId}&campus_id=${campusId}` : `id=${this.labId}`
    wx.navigateTo({ url: `/pages/reserve/reserve?${query}` })
  }
})
