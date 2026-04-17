const { api } = require('../../utils/api')

const COLORS = ['#4A90E2','#27AE60','#E25454','#9B59B6','#F5A623','#1ABC9C']
const STATUS_TEXT = { pending:'待审核', approved:'已批准', rejected:'已拒绝', cancelled:'已取消', completed:'已完成' }

function today() {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`
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
    const idx = parseInt(options.id) || 0
    this.setData({ color: COLORS[idx % COLORS.length] })
    this.loadLab()
    this.loadEquipment()
  },
  async loadLab() {
    try {
      const lab = await api.labDetail(this.labId)
      this.setData({ lab })
      wx.setNavigationBarTitle({ title: lab.lab_name || '实验室详情' })
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
    wx.navigateTo({ url: `/pages/reserve/reserve?id=${this.labId}` })
  }
})
