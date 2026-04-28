const { api } = require('../../utils/api')

const STEP_MINUTES = 30
const MIN_DURATION_MINUTES = 30
const ACTIVE_STATUSES = { pending: true, approved: true }

const STATUS_TEXT = {
  pending: '待审批',
  approved: '已通过',
  rejected: '已拒绝',
  cancelled: '已取消',
  completed: '已完成'
}

function dateToString(d) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

function today() {
  return dateToString(new Date())
}

function dateAfterDays(days) {
  const d = new Date()
  d.setDate(d.getDate() + days)
  return dateToString(d)
}

function normalizeTime(value, fallback = '09:00') {
  const text = String(value || '').trim()
  if (!text) return fallback
  const parts = text.split(':')
  const hh = String(parts[0] || '').padStart(2, '0')
  const mm = String(parts[1] || '00').padStart(2, '0')
  return `${hh}:${mm}`
}

function toMinutes(timeText) {
  const [h, m] = normalizeTime(timeText, '00:00').split(':').map((n) => Number(n || 0))
  return h * 60 + m
}

function fromMinutes(total) {
  const h = Math.floor(total / 60)
  const m = total % 60
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`
}

function combineDateTime(dateStr, timeStr) {
  const [y, m, d] = String(dateStr || '').split('-').map((n) => Number(n || 0))
  const [h, mi] = normalizeTime(timeStr, '00:00').split(':').map((n) => Number(n || 0))
  return new Date(y, (m || 1) - 1, d || 1, h || 0, mi || 0, 0)
}

function ceilToStep(total, step) {
  return Math.ceil(total / step) * step
}

function mergeIntervals(intervals) {
  if (!intervals.length) return []
  const sorted = intervals
    .map((x) => [x[0], x[1]])
    .sort((a, b) => a[0] - b[0])
  const out = [sorted[0]]
  for (let i = 1; i < sorted.length; i += 1) {
    const current = sorted[i]
    const last = out[out.length - 1]
    if (current[0] <= last[1]) {
      last[1] = Math.max(last[1], current[1])
    } else {
      out.push(current)
    }
  }
  return out
}

function formatScheduleRows(rows) {
  return (rows || []).map((item) => ({
    ...item,
    start_label: normalizeTime(item.start_time),
    end_label: normalizeTime(item.end_time),
    status_label: STATUS_TEXT[item.status] || item.status || '未知'
  }))
}

function isDateToday(dateText) {
  return dateText === today()
}

Page({
  data: {
    lab: {},
    schedule: [],
    minDate: today(),
    maxDate: dateAfterDays(7),
    form: {
      date: today(),
      start_time: '',
      end_time: '',
      participant_count: 1,
      purpose: ''
    },
    currentIdempotencyKey: '',
    loading: false,
    statusText: STATUS_TEXT,
    openTime: '08:00',
    closeTime: '22:00',
    busyIntervals: [],
    availableStartTimes: [],
    availableEndTimes: [],
    selectedTimeline: { left: 0, width: 0, visible: false },
    busyTimelineBlocks: [],
    timePanelVisible: false,
    timePanelField: '',
    timePanelTitle: '',
    timePanelOptions: []
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
      await this.loadSchedule()
    } catch (_) {}
  },
  async loadSchedule() {
    try {
      const res = await api.labSchedule(this.labId, this.data.form.date)
      const scheduleRows = res.reservations || []
      const openTime = normalizeTime(res.open_time || this.data.lab.open_time || '08:00', '08:00')
      const closeTime = normalizeTime(res.close_time || this.data.lab.close_time || '22:00', '22:00')
      this.setData(
        {
          schedule: formatScheduleRows(scheduleRows),
          openTime,
          closeTime
        },
        () => this.rebuildAvailability(true)
      )
    } catch (_) {}
  },
  onDate(e) {
    this.setData(
      {
        'form.date': e.detail.value,
        'form.start_time': '',
        'form.end_time': '',
        currentIdempotencyKey: ''
      },
      () => this.loadSchedule()
    )
  },
  onPurpose(e) {
    this.setData({ 'form.purpose': e.detail.value, currentIdempotencyKey: '' })
  },
  openTimePanel(e) {
    const field = e.currentTarget.dataset.field
    const isStart = field === 'start'
    const options = isStart ? this.data.availableStartTimes : this.data.availableEndTimes
    if (!options.length) {
      wx.showToast({ title: '当前没有可预约时间', icon: 'none' })
      return
    }
    this.setData({
      timePanelVisible: true,
      timePanelField: field,
      timePanelTitle: isStart ? '选择开始时间' : '选择结束时间',
      timePanelOptions: options
    })
  },
  closeTimePanel() {
    this.setData({
      timePanelVisible: false,
      timePanelField: '',
      timePanelTitle: '',
      timePanelOptions: []
    })
  },
  chooseTimeOption(e) {
    const value = e.currentTarget.dataset.value
    const field = this.data.timePanelField
    if (field === 'start') {
      this.setData(
        {
          'form.start_time': value,
          'form.end_time': '',
          currentIdempotencyKey: ''
        },
        () => {
          this.rebuildAvailability(false)
          const firstEnd = this.data.availableEndTimes[0] || ''
          if (firstEnd) {
            this.setData({ 'form.end_time': firstEnd }, () => this.rebuildAvailability(false))
          }
          this.closeTimePanel()
        }
      )
      return
    }
    if (field === 'end') {
      this.setData({ 'form.end_time': value, currentIdempotencyKey: '' }, () => {
        this.rebuildAvailability(false)
        this.closeTimePanel()
      })
      return
    }
    this.closeTimePanel()
  },
  rebuildAvailability(autoSelect) {
    const openMin = toMinutes(this.data.openTime)
    const closeMin = toMinutes(this.data.closeTime)
    if (closeMin <= openMin) return

    const busy = mergeIntervals(
      (this.data.schedule || [])
        .filter((item) => ACTIVE_STATUSES[item.status])
        .map((item) => [toMinutes(item.start_label), toMinutes(item.end_label)])
        .filter((seg) => seg[1] > seg[0])
        .map((seg) => [Math.max(seg[0], openMin), Math.min(seg[1], closeMin)])
        .filter((seg) => seg[1] > seg[0])
    )

    let earliestStart = openMin
    if (isDateToday(this.data.form.date)) {
      const now = new Date()
      const nowMin = now.getHours() * 60 + now.getMinutes() + 30
      earliestStart = Math.max(openMin, ceilToStep(nowMin, STEP_MINUTES))
    }

    const availableStartTimes = []
    for (let t = openMin; t + MIN_DURATION_MINUTES <= closeMin; t += STEP_MINUTES) {
      if (t < earliestStart) continue
      const end = t + MIN_DURATION_MINUTES
      const hasConflict = busy.some((seg) => !(end <= seg[0] || t >= seg[1]))
      if (!hasConflict) availableStartTimes.push(fromMinutes(t))
    }

    let startTime = this.data.form.start_time
    if (autoSelect && !availableStartTimes.includes(startTime)) {
      startTime = availableStartTimes[0] || ''
    }

    const availableEndTimes = this.buildEndOptions(startTime, openMin, closeMin, busy)
    let endTime = this.data.form.end_time
    if (startTime && (!endTime || !availableEndTimes.includes(endTime) || toMinutes(endTime) <= toMinutes(startTime))) {
      endTime = availableEndTimes[0] || ''
    }
    if (!startTime) {
      endTime = ''
    }

    const timeline = this.buildTimeline(openMin, closeMin, busy, startTime, endTime)
    this.setData({
      busyIntervals: busy,
      availableStartTimes,
      availableEndTimes,
      'form.start_time': startTime,
      'form.end_time': endTime,
      busyTimelineBlocks: timeline.busyBlocks,
      selectedTimeline: timeline.selected
    })
  },
  buildEndOptions(startTime, openMin, closeMin, busy) {
    if (!startTime) return []
    const startMin = toMinutes(startTime)
    if (startMin < openMin || startMin >= closeMin) return []

    let upper = closeMin
    for (let i = 0; i < busy.length; i += 1) {
      if (busy[i][0] >= startMin + MIN_DURATION_MINUTES) {
        upper = busy[i][0]
        break
      }
      if (startMin >= busy[i][0] && startMin < busy[i][1]) {
        return []
      }
    }

    const options = []
    for (let t = startMin + MIN_DURATION_MINUTES; t <= upper; t += STEP_MINUTES) {
      const conflict = busy.some((seg) => !(t <= seg[0] || startMin >= seg[1]))
      if (conflict) break
      options.push(fromMinutes(t))
    }
    return options
  },
  buildTimeline(openMin, closeMin, busy, startTime, endTime) {
    const span = closeMin - openMin
    const busyBlocks = busy.map((seg) => ({
      left: ((seg[0] - openMin) / span) * 100,
      width: ((seg[1] - seg[0]) / span) * 100
    }))

    const selected = { left: 0, width: 0, visible: false }
    if (startTime && endTime) {
      const s = toMinutes(startTime)
      const e = toMinutes(endTime)
      if (e > s) {
        selected.left = ((s - openMin) / span) * 100
        selected.width = ((e - s) / span) * 100
        selected.visible = true
      }
    }
    return { busyBlocks, selected }
  },
  incCount() {
    const n = this.data.form.participant_count
    if (n < (this.data.lab.capacity || 99)) {
      this.setData({ 'form.participant_count': n + 1, currentIdempotencyKey: '' })
    }
  },
  decCount() {
    const n = this.data.form.participant_count
    if (n > 1) this.setData({ 'form.participant_count': n - 1, currentIdempotencyKey: '' })
  },
  async doSubmit() {
    const { form, minDate, maxDate } = this.data
    const campusId = this.campusId || this.data.lab.campus_id

    if (!form.purpose.trim()) {
      wx.showToast({ title: '请填写使用目的', icon: 'none' })
      return
    }
    if (!form.start_time || !form.end_time) {
      wx.showToast({ title: '请选择可预约时间段', icon: 'none' })
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
    if (form.date < minDate) {
      wx.showToast({ title: '不能预约过去的日期', icon: 'none' })
      return
    }
    if (form.date > maxDate) {
      wx.showToast({ title: '预约日期不能超过未来7天', icon: 'none' })
      return
    }

    const now = new Date()
    const startAt = combineDateTime(form.date, form.start_time)
    const endAt = combineDateTime(form.date, form.end_time)

    if (form.date === minDate && endAt <= now) {
      wx.showToast({ title: '不能预约今天已过去的时间段', icon: 'none' })
      return
    }
    if (startAt.getTime() < now.getTime() + 30 * 60 * 1000) {
      wx.showToast({ title: '预约开始时间需至少提前30分钟', icon: 'none' })
      return
    }

    this.setData({ loading: true })
    try {
      const idempotencyKey =
        this.data.currentIdempotencyKey ||
        `reserve-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`
      this.setData({ currentIdempotencyKey: idempotencyKey })
      const res = await api.createReservation({
        campus_id: campusId,
        lab_id: this.labId,
        reservation_date: form.date,
        start_time: form.start_time,
        end_time: form.end_time,
        participant_count: form.participant_count,
        purpose: form.purpose
      }, { idempotencyKey })
      wx.showToast({ title: '预约成功', icon: 'success' })
      this.setData({ currentIdempotencyKey: '' })
      setTimeout(() => {
        wx.redirectTo({ url: `/pages/reservation-detail/reservation-detail?id=${res.id}` })
      }, 1200)
    } catch (_) {}
    this.setData({ loading: false })
  }
})
