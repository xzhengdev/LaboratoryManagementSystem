<template>
  <view class="reserve-page">
    <student-top-nav active="labs" />

    <view class="reserve-page__shell">
      <view class="reserve-page__head">
        <view>
          <view class="reserve-page__title">实验室预约</view>
          <view class="reserve-page__sub">精简预约流程，快速锁定研究资源。</view>
        </view>

        <view class="reserve-page__steps">
          <view class="reserve-page__step active"><text>1</text> 填写申请</view>
          <view class="reserve-page__line"></view>
          <view class="reserve-page__step"><text>2</text> 等待审核</view>
        </view>
      </view>

      <view class="reserve-page__layout">
        <view class="reserve-form">
          <view class="reserve-form__section">
            <view class="reserve-form__section-title">设施选择</view>
            <view class="reserve-form__grid two">
              <view class="reserve-form__field">
                <view class="reserve-form__label">实验室</view>
                <picker :range="labOptions" range-key="lab_name" :value="labIndex" @change="changeLab">
                  <view class="reserve-form__input reserve-form__input--picker">
                    <text>{{ currentLabName }}</text>
                    <text class="reserve-form__caret">▼</text>
                  </view>
                </picker>
              </view>

              <view class="reserve-form__field">
                <view class="reserve-form__label">参与人数</view>
                <input
                  v-model="form.participant_count"
                  class="reserve-form__input"
                  type="number"
                  :placeholder="participantPlaceholder"
                />
              </view>
            </view>
          </view>

          <view class="reserve-form__section">
            <view class="reserve-form__section-title">时间安排</view>
            <view class="reserve-form__grid three">
              <view class="reserve-form__field">
                <view class="reserve-form__label">预约日期</view>
                <picker
                  mode="date"
                  :value="form.reservation_date"
                  :start="todayDate"
                  :end="maxReserveDate"
                  @change="setField('reservation_date', $event.detail.value)"
                >
                  <view class="reserve-form__input reserve-form__input--picker">
                    <text>{{ form.reservation_date }}</text>
                    <text class="reserve-form__icon">日</text>
                  </view>
                </picker>
              </view>

              <view class="reserve-form__field">
                <view class="reserve-form__label">开始时间</view>
                <picker mode="time" :value="form.start_time" @change="setField('start_time', $event.detail.value)">
                  <view class="reserve-form__input reserve-form__input--picker">
                    <text>{{ form.start_time }}</text>
                    <text class="reserve-form__icon">时</text>
                  </view>
                </picker>
              </view>

              <view class="reserve-form__field">
                <view class="reserve-form__label">结束时间</view>
                <picker mode="time" :value="form.end_time" @change="setField('end_time', $event.detail.value)">
                  <view class="reserve-form__input reserve-form__input--picker">
                    <text>{{ form.end_time }}</text>
                    <text class="reserve-form__icon">时</text>
                  </view>
                </picker>
              </view>
            </view>

            <view class="reserve-form__occupancy">
              <view class="reserve-form__occupancy-title">当日占用情况</view>
              <view class="reserve-form__occupancy-legend">
                <view class="reserve-form__legend-item">
                  <view class="reserve-form__legend-swatch busy"></view>
                  <text>已占用</text>
                </view>
                <view class="reserve-form__legend-item">
                  <view class="reserve-form__legend-swatch idle"></view>
                  <text>空闲可用</text>
                </view>
                <view class="reserve-form__legend-item">
                  <view class="reserve-form__legend-swatch focus"></view>
                  <text>当前选择</text>
                </view>
              </view>

              <view class="reserve-form__timeline-wrap">
                <view class="reserve-form__timeline">
                  <view
                    v-for="(seg, index) in availabilitySegments"
                    :key="index"
                    class="reserve-form__timeline-seg"
                    :class="seg.type"
                    :style="{ width: seg.width }"
                  >
                    <text v-if="seg.type === 'focus'" class="reserve-form__timeline-label">选中</text>
                  </view>
                </view>

                <view class="reserve-form__timeline-ticks">
                  <view
                    v-for="(mark, index) in timeMarkItems"
                    :key="'tick-' + index"
                    class="reserve-form__timeline-tick"
                    :class="{ start: index === 0, end: index === timeMarkItems.length - 1 }"
                    :style="{ left: mark.offset + '%' }"
                  ></view>
                </view>
              </view>

              <view class="reserve-form__marks">
                <text
                  v-for="(mark, index) in timeMarkItems"
                  :key="index"
                  class="reserve-form__mark"
                  :class="{ start: index === 0, end: index === timeMarkItems.length - 1 }"
                  :style="{ left: mark.offset + '%' }"
                >{{ mark.label }}</text>
              </view>
            </view>
          </view>

          <view class="reserve-form__section">
            <view class="reserve-form__section-title">预约用途</view>
            <view class="reserve-form__field">
              <textarea
                v-model="form.purpose"
                class="reserve-form__textarea"
                maxlength="200"
                placeholder="请简述本次实验室使用的目的与研究项目名称..."
              />
            </view>
          </view>

          <view class="reserve-form__actions">
            <view class="reserve-form__btn primary" @click="submit">提交预约申请</view>
          </view>
        </view>

        <view class="reserve-side">
          <view class="reserve-side__summary">
            <view class="reserve-side__summary-title">预约摘要</view>

            <view class="reserve-side__summary-item">
              <view class="reserve-side__summary-icon">地</view>
              <view class="reserve-side__summary-content">
                <view class="reserve-side__summary-label">地点</view>
                <view class="reserve-side__summary-value">{{ summaryLocation }}</view>
              </view>
            </view>

            <view class="reserve-side__summary-item">
              <view class="reserve-side__summary-icon">时</view>
              <view class="reserve-side__summary-content">
                <view class="reserve-side__summary-label">时间</view>
                <view class="reserve-side__summary-value">{{ summaryTime }}</view>
              </view>
            </view>

            <view class="reserve-side__summary-item">
              <view class="reserve-side__summary-icon">人</view>
              <view class="reserve-side__summary-content">
                <view class="reserve-side__summary-label">资源概览</view>
                <view class="reserve-side__summary-value">{{ summaryResource }}</view>
              </view>
            </view>
          </view>

          <view class="reserve-side__notice">
            <view class="reserve-side__notice-title">预约须知</view>
            <view v-for="(item, index) in noticeItems" :key="index" class="reserve-side__notice-item">
              <view class="reserve-side__notice-dot"></view>
              <view class="reserve-side__notice-text">{{ item }}</view>
            </view>
          </view>
        </view>
      </view>
    </view>
  </view>
</template>

<script>
import StudentTopNav from '../../components/student-top-nav.vue'
import { api } from '../../api/index'
import { requireLogin } from '../../common/guard'
import { openPage } from '../../common/router'
import { routes } from '../../config/navigation'

function todayString() {
  const now = new Date()
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`
}

function addDaysString(days) {
  const now = new Date()
  now.setDate(now.getDate() + days)
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`
}

function currentMinuteValue() {
  const now = new Date()
  return now.getHours() * 60 + now.getMinutes()
}

function toDateTimeValue(dateText, timeText) {
  const [year, month, day] = String(dateText || '').split('-').map((item) => Number(item || 0))
  const [hour, minute] = String(timeText || '').split(':').map((item) => Number(item || 0))
  return new Date(year, Math.max(0, month - 1), day || 1, hour || 0, minute || 0, 0)
}

function toMinuteValue(raw) {
  if (!raw) return 0
  const safe = String(raw).slice(0, 5)
  const [h = 0, m = 0] = safe.split(':').map((item) => Number(item || 0))
  return h * 60 + m
}

function toTimeLabel(minutes) {
  const safe = Math.max(0, minutes)
  const h = Math.floor(safe / 60)
  const m = safe % 60
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`
}

function mergeBusyRanges(ranges) {
  if (!ranges.length) return []
  const sorted = ranges
    .filter((item) => item.end > item.start)
    .sort((a, b) => a.start - b.start)

  const merged = [sorted[0]]
  for (let index = 1; index < sorted.length; index += 1) {
    const current = sorted[index]
    const last = merged[merged.length - 1]
    if (current.start <= last.end) {
      last.end = Math.max(last.end, current.end)
    } else {
      merged.push({ start: current.start, end: current.end, type: 'busy' })
    }
  }
  return merged
}

function buildSegments(openMinute, closeMinute, reservations, selectedStart, selectedEnd, blockedBefore = null) {
  const total = Math.max(1, closeMinute - openMinute)
  const busyRanges = (reservations || [])
    .filter((item) => !['cancelled', 'rejected'].includes(item.status))
    .map((item) => ({
      start: Math.max(openMinute, toMinuteValue(item.start_time)),
      end: Math.min(closeMinute, toMinuteValue(item.end_time)),
      type: 'busy'
    }))

  if (typeof blockedBefore === 'number') {
    const disabledEnd = Math.min(closeMinute, Math.max(openMinute, blockedBefore))
    if (disabledEnd > openMinute) {
      busyRanges.push({ start: openMinute, end: disabledEnd, type: 'busy' })
    }
  }

  const mergedBusyRanges = mergeBusyRanges(busyRanges)
  const baseSegments = []
  let cursor = openMinute

  mergedBusyRanges.forEach((item) => {
    if (item.start > cursor) {
      baseSegments.push({ start: cursor, end: item.start, type: 'idle' })
    }
    baseSegments.push(item)
    cursor = Math.max(cursor, item.end)
  })

  if (cursor < closeMinute) {
    baseSegments.push({ start: cursor, end: closeMinute, type: 'idle' })
  }

  if (!baseSegments.length) {
    baseSegments.push({ start: openMinute, end: closeMinute, type: 'idle' })
  }

  const selectedValid = selectedEnd > selectedStart
  const result = []

  baseSegments.forEach((seg) => {
    if (!selectedValid || seg.type !== 'idle' || seg.end <= selectedStart || seg.start >= selectedEnd) {
      result.push(seg)
      return
    }

    if (seg.start < selectedStart) {
      result.push({ start: seg.start, end: selectedStart, type: 'idle' })
    }

    result.push({
      start: Math.max(seg.start, selectedStart),
      end: Math.min(seg.end, selectedEnd),
      type: 'focus'
    })

    if (seg.end > selectedEnd) {
      result.push({ start: selectedEnd, end: seg.end, type: 'idle' })
    }
  })

  return result
    .filter((seg) => seg.end > seg.start)
    .map((seg) => ({
      type: seg.type,
      width: `${((seg.end - seg.start) / total) * 100}%`
    }))
}

export default {
  components: { StudentTopNav },
  data() {
    return {
      labIndex: 0,
      labOptions: [],
      schedule: {},
      form: {
        campus_id: '',
        lab_id: '',
        reservation_date: todayString(),
        start_time: '14:00',
        end_time: '16:30',
        purpose: '',
        participant_count: '1'
      }
    }
  },
  computed: {
    currentLab() {
      return this.labOptions[this.labIndex] || {}
    },
    todayDate() {
      return todayString()
    },
    maxReserveDate() {
      return addDaysString(7)
    },
    participantPlaceholder() {
      return this.maxParticipants ? `请输入人数（上限 ${this.maxParticipants} 人）` : '请输入人数'
    },
    currentLabName() {
      return this.currentLab.lab_name || '请选择实验室'
    },
    maxParticipants() {
      return Number(this.currentLab.capacity || 0)
    },
    summaryLocation() {
      const campus = this.currentLab.campus_name || '校区待定'
      const location = this.currentLab.location || '位置待定'
      return `${campus} · ${location}`
    },
    summaryTime() {
      const start = this.form.start_time || '--:--'
      const end = this.form.end_time || '--:--'
      const duration = this.durationText ? ` (${this.durationText})` : ''
      return `${this.form.reservation_date} ${start} - ${end}${duration}`
    },
    durationText() {
      const start = toMinuteValue(this.form.start_time)
      const end = toMinuteValue(this.form.end_time)
      if (end <= start) return ''
      const total = end - start
      const hours = Math.floor(total / 60)
      const mins = total % 60
      if (hours && mins) return `${hours}小时${mins}分钟`
      if (hours) return `${hours}小时`
      return `${mins}分钟`
    },
    summaryResource() {
      return `预计参与人数：${Number(this.form.participant_count || 0)} 名`
    },
    noticeItems() {
      return [
        '预约开始时间需至少提前 30 分钟，请尽早提交申请。',
        '实验室严禁携带食物和饮料进入，请放在储物区。',
        '如需取消预约，请至少提前 2 小时通过系统撤回。',
        '使用过程中请务必穿戴好必要的防护装备。'
      ]
    },
    availabilitySegments() {
      const openMinute = toMinuteValue(this.schedule?.open_time || this.currentLab.open_time || '08:00')
      const closeMinute = toMinuteValue(this.schedule?.close_time || this.currentLab.close_time || '21:00')
      const selectedStart = toMinuteValue(this.form.start_time)
      const selectedEnd = toMinuteValue(this.form.end_time)
      const reservations = Array.isArray(this.schedule?.reservations) ? this.schedule.reservations : []
      const blockedBefore = this.form.reservation_date === todayString() ? currentMinuteValue() + 30 : null
      return buildSegments(openMinute, closeMinute, reservations, selectedStart, selectedEnd, blockedBefore)
    },
    timeMarkItems() {
      const openMinute = toMinuteValue(this.schedule?.open_time || this.currentLab.open_time || '08:00')
      const closeMinute = toMinuteValue(this.schedule?.close_time || this.currentLab.close_time || '21:00')
      const marks = [openMinute]
      let cursor = Math.ceil(openMinute / 60) * 60

      if (cursor === openMinute) {
        cursor += 60
      }

      while (cursor < closeMinute) {
        marks.push(cursor)
        cursor += 60
      }

      if (marks[marks.length - 1] !== closeMinute) {
        marks.push(closeMinute)
      }

      const total = Math.max(1, closeMinute - openMinute)
      return marks.map((value, index) => ({
        label: toTimeLabel(value),
        offset: index === 0 ? 0 : index === marks.length - 1 ? 100 : ((value - openMinute) / total) * 100
      }))
    }
  },
  onLoad(options) {
    this.form.lab_id = options.labId || ''
    this.form.campus_id = options.campusId || ''
    this.form.reservation_date = options.date || todayString()
  },
  async onShow() {
    if (!requireLogin()) return
    await this.loadLabs()
  },
  methods: {
    getTimeBounds() {
      const openMinute = toMinuteValue(this.schedule?.open_time || this.currentLab.open_time || '08:00')
      const closeMinute = toMinuteValue(this.schedule?.close_time || this.currentLab.close_time || '21:00')
      const isToday = this.form.reservation_date === todayString()
      const earliestStart = isToday ? Math.max(openMinute, currentMinuteValue() + 30) : openMinute
      return { openMinute, closeMinute, isToday, earliestStart }
    },
    ensureValidTimeRange(showMessage = false) {
      const today = todayString()
      const maxDate = addDaysString(7)
      let message = ''

      if (this.form.reservation_date < today) {
        this.form.reservation_date = today
        message = '不能选择今天之前的日期'
      }
      if (this.form.reservation_date > maxDate) {
        this.form.reservation_date = maxDate
        message = '预约日期不能超过未来7天'
      }

      const { openMinute, closeMinute, isToday, earliestStart } = this.getTimeBounds()
      const defaultDuration = 90
      const maxStart = Math.max(openMinute, closeMinute - 1)
      let start = toMinuteValue(this.form.start_time || '00:00')
      let end = toMinuteValue(this.form.end_time || '00:00')
      const originalDuration = end > start ? end - start : defaultDuration

      if (isToday && earliestStart >= closeMinute) {
        this.form.start_time = toTimeLabel(maxStart)
        this.form.end_time = toTimeLabel(closeMinute)
        if (!message) message = '当前时间之后已没有可预约时段'
        if (showMessage) {
          uni.showToast({ title: message, icon: 'none' })
        }
        return
      }

      if (isToday && start < earliestStart) {
        start = Math.min(Math.max(earliestStart, openMinute), maxStart)
        this.form.start_time = toTimeLabel(start)
        if (!message) {
          message = '预约开始时间必须至少提前30分钟'
        }
      }

      if (start < openMinute) {
        start = openMinute
        this.form.start_time = toTimeLabel(start)
      }

      if (start >= closeMinute) {
        start = Math.max(openMinute, closeMinute - Math.min(defaultDuration, Math.max(30, closeMinute - openMinute)))
        end = closeMinute
        this.form.start_time = toTimeLabel(start)
        this.form.end_time = toTimeLabel(end)
        if (!message) {
          message = '当前时间之后已没有可预约时段'
        }
      } else {
        if (end <= start) {
          end = Math.min(closeMinute, start + originalDuration)
        }
        if (end <= start) {
          end = Math.min(closeMinute, start + 30)
        }
        if (end > closeMinute) {
          end = closeMinute
        }
        if (end <= start) {
          end = Math.min(closeMinute, start + 1)
        }
        this.form.end_time = toTimeLabel(end)
      }

      if (showMessage && message) {
        uni.showToast({ title: message, icon: 'none' })
      }
    },
    async loadLabs() {
      try {
        const list = await api.labs(this.form.campus_id ? { campus_id: this.form.campus_id } : {})
        this.labOptions = Array.isArray(list) ? list : []
        if (!this.labOptions.length) return

        const targetIndex = this.form.lab_id
          ? this.labOptions.findIndex((item) => String(item.id) === String(this.form.lab_id))
          : 0

        this.labIndex = targetIndex >= 0 ? targetIndex : 0
        this.syncLabToForm()
        await this.loadSchedule()
        this.ensureValidTimeRange(false)
      } catch (_error) {
        this.labOptions = []
      }
    },
    async loadSchedule() {
      if (!this.form.lab_id) return
      try {
        this.schedule = await api.labSchedule(this.form.lab_id, this.form.reservation_date)
      } catch (_error) {
        this.schedule = {}
      }
    },
    syncLabToForm() {
      const lab = this.currentLab
      if (!lab.id) return
      this.form.lab_id = String(lab.id)
      this.form.campus_id = String(lab.campus_id || this.form.campus_id || '')
      if (!this.form.participant_count || Number(this.form.participant_count) <= 0) {
        this.form.participant_count = '1'
      }
    },
    async changeLab(event) {
      this.labIndex = Number(event.detail.value || 0)
      this.syncLabToForm()
      await this.loadSchedule()
      this.ensureValidTimeRange(true)
    },
    async setField(key, value) {
      this.form[key] = value
      if (key === 'reservation_date' && this.form.lab_id) {
        await this.loadSchedule()
      }
      this.ensureValidTimeRange(true)
    },
    async submit() {
      if (!this.form.lab_id) {
        uni.showToast({ title: '请选择实验室', icon: 'none' })
        return
      }

      if (!this.form.purpose) {
        uni.showToast({ title: '请填写预约用途', icon: 'none' })
        return
      }

      const participantCount = Number(this.form.participant_count || 0)
      if (participantCount <= 0) {
        uni.showToast({ title: '请输入有效的参与人数', icon: 'none' })
        return
      }

      if (this.maxParticipants && participantCount > this.maxParticipants) {
        uni.showToast({ title: `参与人数不能超过 ${this.maxParticipants} 人`, icon: 'none' })
        return
      }

      const today = todayString()
      const maxDate = addDaysString(7)
      const startMinute = toMinuteValue(this.form.start_time)
      const endMinute = toMinuteValue(this.form.end_time)
      const { openMinute, closeMinute, isToday, earliestStart } = this.getTimeBounds()

      if (this.form.reservation_date < today) {
        uni.showToast({ title: '不能预约今天之前的日期', icon: 'none' })
        return
      }
      if (this.form.reservation_date > maxDate) {
        uni.showToast({ title: '预约日期不能超过未来7天', icon: 'none' })
        return
      }

      if (startMinute < openMinute || endMinute > closeMinute || endMinute <= startMinute) {
        uni.showToast({ title: '请选择有效的预约时间段', icon: 'none' })
        return
      }

      if (isToday && startMinute < earliestStart) {
        uni.showToast({ title: '预约开始时间必须至少提前30分钟', icon: 'none' })
        return
      }

      const now = new Date()
      const startAt = toDateTimeValue(this.form.reservation_date, this.form.start_time)
      const endAt = toDateTimeValue(this.form.reservation_date, this.form.end_time)
      if (isToday && endAt <= now) {
        uni.showToast({ title: '不能预约今天已过去的时间段', icon: 'none' })
        return
      }
      if (startAt.getTime() < now.getTime() + 30 * 60 * 1000) {
        uni.showToast({ title: '预约开始时间必须至少提前30分钟', icon: 'none' })
        return
      }

      const createdReservation = await api.createReservation({
        ...this.form,
        participant_count: participantCount
      })

      uni.showToast({ title: '预约已提交', icon: 'success' })
      setTimeout(
        () =>
          openPage(
            createdReservation?.id ? routes.reservationDetail : routes.myReservations,
            createdReservation?.id ? { query: { id: createdReservation.id }, replace: true } : { replace: true }
          ),
        500
      )
    }
  }
}
</script>

<style lang="scss">
.reserve-page {
  min-height: 100vh;
  background:
    radial-gradient(circle at 12% 14%, rgba(109, 179, 230, 0.25), transparent 26%),
    radial-gradient(circle at 88% 18%, rgba(173, 208, 240, 0.26), transparent 24%),
    linear-gradient(180deg, #edf5fc 0%, #dceaf7 100%);
}

.reserve-page__shell {
  padding: 28rpx 32rpx 54rpx;
}

.reserve-page__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 24rpx;
}

.reserve-page__title {
  color: #082247;
  font-size: 68rpx;
  line-height: 1.04;
  font-weight: 800;
  letter-spacing: -1.2rpx;
}

.reserve-page__sub {
  margin-top: 10rpx;
  color: #5d6f88;
  font-size: 27rpx;
}

.reserve-page__steps {
  margin-top: 10rpx;
  padding: 12rpx 18rpx;
  border-radius: 22rpx;
  background: rgba(255, 255, 255, 0.62);
  border: 1rpx solid rgba(200, 210, 224, 0.55);
  display: flex;
  align-items: center;
  gap: 14rpx;
}

.reserve-page__step {
  display: inline-flex;
  align-items: center;
  gap: 10rpx;
  color: #7a8aa2;
  font-size: 24rpx;
  font-weight: 700;
}

.reserve-page__step text {
  width: 42rpx;
  height: 42rpx;
  border-radius: 50%;
  background: #eef3f9;
  color: #667a99;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 22rpx;
  font-weight: 800;
}

.reserve-page__step.active {
  color: #082247;
}

.reserve-page__step.active text {
  background: #082b63;
  color: #ffffff;
}

.reserve-page__line {
  width: 70rpx;
  height: 2rpx;
  background: #d1dae6;
}

.reserve-page__layout {
  margin-top: 28rpx;
  display: grid;
  grid-template-columns: minmax(0, 1fr) 800rpx;
  gap: 24rpx;
  align-items: start;
}

.reserve-form,
.reserve-side__summary,
.reserve-side__notice {
  border-radius: 30rpx;
  background: rgba(255, 255, 255, 0.96);
  border: 1rpx solid rgba(223, 231, 242, 0.92);
  box-shadow: 0 18rpx 42rpx rgba(16, 43, 79, 0.06);
}

.reserve-form {
  padding: 30rpx;
}

.reserve-form__section + .reserve-form__section {
  margin-top: 30rpx;
}

.reserve-form__section-title {
  color: #102b4f;
  font-size: 28rpx;
  font-weight: 800;
}

.reserve-form__grid {
  margin-top: 18rpx;
  display: grid;
  gap: 16rpx;
}

.reserve-form__grid.two {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.reserve-form__grid.three {
  grid-template-columns: 1.1fr 0.75fr 0.75fr;
}

.reserve-form__field {
  min-width: 0;
}

.reserve-form__label {
  margin-bottom: 10rpx;
  color: #667b96;
  font-size: 21rpx;
  font-weight: 700;
}

.reserve-form__input {
  width: 100%;
  height: 72rpx;
  padding: 0 18rpx;
  border-radius: 18rpx;
  background: #f1f5fa;
  color: #233857;
  font-size: 25rpx;
  box-sizing: border-box;
}

.reserve-form__input--picker {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.reserve-form__caret,
.reserve-form__icon {
  color: #6e8099;
  font-size: 22rpx;
  font-weight: 700;
}

.reserve-form__textarea {
  width: 100%;
  min-height: 180rpx;
  border-radius: 18rpx;
  padding: 20rpx;
  background: #f1f5fa;
  color: #273a57;
  font-size: 24rpx;
  box-sizing: border-box;
}

.reserve-form__occupancy {
  margin-top: 18rpx;
  border-radius: 22rpx;
  padding: 18rpx;
  background: #fbfdff;
  border: 1rpx solid #e3ebf4;
}

.reserve-form__occupancy-title {
  color: #102b4f;
  font-size: 22rpx;
  font-weight: 800;
}

.reserve-form__occupancy-legend {
  margin-top: 12rpx;
  display: flex;
  flex-wrap: wrap;
  gap: 18rpx;
}

.reserve-form__legend-item {
  display: inline-flex;
  align-items: center;
  gap: 8rpx;
  color: #60728d;
  font-size: 19rpx;
  font-weight: 700;
}

.reserve-form__legend-swatch {
  width: 22rpx;
  height: 22rpx;
  border-radius: 999rpx;
  flex-shrink: 0;
}

.reserve-form__legend-swatch.busy {
  background: #93a1b6;
}

.reserve-form__legend-swatch.idle {
  background: #e6f6ec;
}

.reserve-form__legend-swatch.focus {
  background: linear-gradient(135deg, #2f7ea5, #3f96bf);
}

.reserve-form__timeline-wrap {
  position: relative;
  margin-top: 16rpx;
}

.reserve-form__timeline {
  height: 66rpx;
  border-radius: 18rpx;
  overflow: hidden;
  display: flex;
  background: #dfe6ef;
}

.reserve-form__timeline-ticks {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.reserve-form__timeline-tick {
  position: absolute;
  top: 0;
  width: 2rpx;
  height: 66rpx;
  background: rgba(255, 255, 255, 0.72);
  transform: translateX(-50%);
}

.reserve-form__timeline-tick.start {
  transform: none;
}

.reserve-form__timeline-tick.end {
  transform: translateX(-100%);
}

.reserve-form__timeline-seg {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.reserve-form__timeline-seg.busy {
  background: #93a1b6;
}

.reserve-form__timeline-seg.idle {
  background: #e6f6ec;
}

.reserve-form__timeline-seg.focus {
  background: linear-gradient(135deg, #2f7ea5, #3f96bf);
}

.reserve-form__timeline-label {
  color: #ffffff;
  font-size: 19rpx;
  font-weight: 800;
}

.reserve-form__marks {
  position: relative;
  margin-top: 12rpx;
  min-height: 26rpx;
}

.reserve-form__mark {
  position: absolute;
  top: 0;
  color: #61738f;
  font-size: 18rpx;
  line-height: 1;
  transform: translateX(-50%);
  white-space: nowrap;
}

.reserve-form__mark.start {
  transform: none;
}

.reserve-form__mark.end {
  transform: translateX(-100%);
}

.reserve-form__actions {
  margin-top: 34rpx;
  display: flex;
  justify-content: flex-end;
}

.reserve-form__btn {
  min-width: 210rpx;
  height: 76rpx;
  border-radius: 20rpx;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 27rpx;
  font-weight: 800;
  transition: transform 0.2s ease, box-shadow 0.2s ease, opacity 0.2s ease;
}

.reserve-form__btn.primary {
  background: linear-gradient(135deg, #082b63, #123f83);
  color: #ffffff;
  box-shadow: 0 16rpx 34rpx rgba(8, 43, 99, 0.18);
}

.reserve-side {
  display: grid;
  gap: 22rpx;
}

.reserve-side__summary {
  padding: 28rpx;
  background: linear-gradient(180deg, #082555 0%, #0b2c63 100%);
  color: #ffffff;
}

.reserve-side__summary-title {
  font-size: 30rpx;
  font-weight: 800;
}

.reserve-side__summary-item {
  margin-top: 22rpx;
  display: grid;
  grid-template-columns: 52rpx minmax(0, 1fr);
  gap: 14rpx;
  align-items: start;
}

.reserve-side__summary-icon {
  width: 52rpx;
  height: 52rpx;
  border-radius: 16rpx;
  background: rgba(255, 255, 255, 0.12);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24rpx;
  font-weight: 800;
}

.reserve-side__summary-label {
  color: rgba(194, 214, 243, 0.86);
  font-size: 19rpx;
  font-weight: 700;
}

.reserve-side__summary-value {
  margin-top: 6rpx;
  font-size: 23rpx;
  line-height: 1.55;
  font-weight: 700;
}

.reserve-side__notice {
  padding: 28rpx;
}

.reserve-side__notice-title {
  color: #102b4f;
  font-size: 28rpx;
  font-weight: 800;
}

.reserve-side__notice-item {
  margin-top: 18rpx;
  display: grid;
  grid-template-columns: 12rpx minmax(0, 1fr);
  gap: 12rpx;
  align-items: start;
}

.reserve-side__notice-dot {
  width: 12rpx;
  height: 12rpx;
  border-radius: 999rpx;
  background: #3f96bf;
  margin-top: 10rpx;
}

.reserve-side__notice-text {
  color: #5d6f88;
  font-size: 22rpx;
  line-height: 1.7;
}

@media (max-width: 960px) {
  .reserve-page__head {
    flex-direction: column;
  }

  .reserve-page__layout {
    grid-template-columns: 1fr;
  }

  .reserve-form__grid.two,
  .reserve-form__grid.three {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 760px) {
  .reserve-page__shell {
    padding: 16rpx 12rpx calc(20rpx + env(safe-area-inset-bottom));
  }

  .reserve-page__title {
    font-size: 46rpx;
    line-height: 1.1;
    letter-spacing: 0;
  }

  .reserve-page__sub {
    margin-top: 8rpx;
    font-size: 22rpx;
    line-height: 1.5;
  }

  .reserve-page__steps {
    width: 100%;
    margin-top: 8rpx;
    padding: 10rpx 12rpx;
    border-radius: 14rpx;
    gap: 8rpx;
  }

  .reserve-page__step {
    font-size: 20rpx;
    gap: 6rpx;
  }

  .reserve-page__step text {
    width: 32rpx;
    height: 32rpx;
    font-size: 18rpx;
  }

  .reserve-page__line {
    width: 44rpx;
  }

  .reserve-page__layout {
    margin-top: 14rpx;
    gap: 12rpx;
  }

  .reserve-form,
  .reserve-side__summary,
  .reserve-side__notice {
    border-radius: 18rpx;
  }

  .reserve-form {
    padding: 14rpx;
  }

  .reserve-form__section + .reserve-form__section {
    margin-top: 16rpx;
  }

  .reserve-form__section-title {
    font-size: 24rpx;
  }

  .reserve-form__grid {
    margin-top: 10rpx;
    gap: 10rpx;
  }

  .reserve-form__label {
    margin-bottom: 6rpx;
    font-size: 20rpx;
  }

  .reserve-form__input {
    height: 58rpx;
    border-radius: 12rpx;
    font-size: 22rpx;
    padding: 0 12rpx;
  }

  .reserve-form__textarea {
    min-height: 132rpx;
    border-radius: 12rpx;
    padding: 12rpx;
    font-size: 22rpx;
  }

  .reserve-form__occupancy {
    margin-top: 12rpx;
    border-radius: 14rpx;
    padding: 12rpx;
  }

  .reserve-form__occupancy-title {
    font-size: 20rpx;
  }

  .reserve-form__occupancy-legend {
    margin-top: 8rpx;
    gap: 10rpx;
  }

  .reserve-form__legend-item {
    font-size: 17rpx;
  }

  .reserve-form__legend-swatch {
    width: 16rpx;
    height: 16rpx;
  }

  .reserve-form__timeline {
    height: 44rpx;
    border-radius: 12rpx;
  }

  .reserve-form__timeline-tick {
    height: 44rpx;
  }

  .reserve-form__timeline-label {
    font-size: 16rpx;
  }

  .reserve-form__marks {
    margin-top: 8rpx;
    min-height: 22rpx;
  }

  .reserve-form__mark {
    font-size: 15rpx;
  }

  .reserve-form__actions {
    margin-top: 16rpx;
    justify-content: stretch;
  }

  .reserve-form__btn {
    width: 100%;
    min-width: 0;
    height: 60rpx;
    border-radius: 12rpx;
    font-size: 23rpx;
  }

  .reserve-side {
    gap: 10rpx;
  }

  .reserve-side__summary,
  .reserve-side__notice {
    padding: 14rpx;
  }

  .reserve-side__summary-title,
  .reserve-side__notice-title {
    font-size: 24rpx;
  }

  .reserve-side__summary-item {
    margin-top: 12rpx;
    grid-template-columns: 40rpx minmax(0, 1fr);
    gap: 10rpx;
  }

  .reserve-side__summary-icon {
    width: 40rpx;
    height: 40rpx;
    border-radius: 12rpx;
    font-size: 20rpx;
  }

  .reserve-side__summary-label {
    font-size: 17rpx;
  }

  .reserve-side__summary-value {
    margin-top: 4rpx;
    font-size: 20rpx;
  }

  .reserve-side__notice-item {
    margin-top: 10rpx;
    grid-template-columns: 10rpx minmax(0, 1fr);
    gap: 10rpx;
  }

  .reserve-side__notice-dot {
    width: 10rpx;
    height: 10rpx;
    margin-top: 8rpx;
  }

  .reserve-side__notice-text {
    font-size: 20rpx;
    line-height: 1.6;
  }
}

@media (max-width: 420px) {
  .reserve-page__title {
    font-size: 40rpx;
  }

  .reserve-page__sub {
    font-size: 20rpx;
  }

  .reserve-form__section-title,
  .reserve-side__summary-title,
  .reserve-side__notice-title {
    font-size: 22rpx;
  }
}
</style>
