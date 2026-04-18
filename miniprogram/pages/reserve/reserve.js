const { api } = require('../../utils/api')

const STATUS_TEXT = {
  pending: '待审核',
  approved: '已通过',
  rejected: '已拒绝',
  cancelled: '已取消',
  completed: '已完成'
}

function today() {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

Page({
  data: {
    lab: {},
    schedule: [],
    form: {
      date: today(),
      start_time: '09:00',
      end_time: '11:00',
      participant_count: 1,
      purpose: ''
    },
    loading: false,
    statusText: STATUS_TEXT
  },
  onLoad(options) {
    this.labId = options.id
    this.campusId = options.campus_id || ''
    this.loadLab()
  },
  async loadLab() {
    try {
      const lab = await api.labDetail(this.labId)
      this.campusId = lab.campus_id || this.campusId
      this.setData({ lab })
      this.loadSchedule()
    } catch (_) {}
  },
  async loadSchedule() {
    try {
      const res = await api.labSchedule(this.labId, this.data.form.date)
      this.setData({ schedule: res.reservations || res || [] })
    } catch (_) {}
  },
  onDate(e) {
    this.setData({ 'form.date': e.detail.value }, () => this.loadSchedule())
  },
  onStartTime(e) {
    this.setData({ 'form.start_time': e.detail.value })
  },
  onEndTime(e) {
    this.setData({ 'form.end_time': e.detail.value })
  },
  onPurpose(e) {
    this.setData({ 'form.purpose': e.detail.value })
  },
  incCount() {
    const n = this.data.form.participant_count
    if (n < (this.data.lab.capacity || 99)) this.setData({ 'form.participant_count': n + 1 })
  },
  decCount() {
    const n = this.data.form.participant_count
    if (n > 1) this.setData({ 'form.participant_count': n - 1 })
  },
  async doSubmit() {
    const { form } = this.data
    const campusId = this.campusId || this.data.lab.campus_id

    if (!form.purpose.trim()) {
      wx.showToast({ title: '请填写使用目的', icon: 'none' })
      return
    }
    if (form.start_time >= form.end_time) {
      wx.showToast({ title: '结束时间需晚于开始时间', icon: 'none' })
      return
    }
    if (!campusId) {
      wx.showToast({ title: '缺少必要参数: campus_id', icon: 'none' })
      return
    }

    this.setData({ loading: true })
    try {
      const res = await api.createReservation({
        campus_id: campusId,
        lab_id: this.labId,
        reservation_date: form.date,
        start_time: form.start_time,
        end_time: form.end_time,
        participant_count: form.participant_count,
        purpose: form.purpose
      })
      wx.showToast({ title: '预约成功', icon: 'success' })
      setTimeout(() => {
        wx.redirectTo({ url: `/pages/reservation-detail/reservation-detail?id=${res.id}` })
      }, 1200)
    } catch (_) {}
    this.setData({ loading: false })
  }
})
