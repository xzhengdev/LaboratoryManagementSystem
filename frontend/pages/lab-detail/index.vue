﻿<template>
  <view class="lab-detail-page">
    <student-top-nav active="labs" />

    <view class="lab-detail-page__hero" :style="heroStyle">
      <view class="lab-detail-page__hero-overlay">
        <view class="lab-detail-page__hero-meta">
          <view class="lab-detail-page__pill">{{ securityLabel }}</view>
          <view class="lab-detail-page__pill">{{ detail.status === 'active' ? '开放中' : '维护中' }}</view>
        </view>
        <view class="lab-detail-page__hero-path">{{ detail.campus_name || '校区待定' }} · {{ detail.location || '位置待定' }}</view>
        <view class="lab-detail-page__hero-title">{{ detail.lab_name || '实验室详情' }}</view>
        <view class="lab-detail-page__hero-sub">{{ detail.description || defaultDesc }}</view>
      </view>
      <view
        class="lab-detail-page__hero-action"
        :class="{ disabled: !canReserve }"
        @click="goReserve"
      >
        {{ canReserve ? '立即预约' : '维护中不可预约' }}
      </view>
    </view>

    <view class="lab-detail-page__tabs">
      <view class="lab-detail-page__tab" :class="{ active: activeTab === 'overview' }" @click="activeTab = 'overview'">概览</view>
      <view class="lab-detail-page__tab" :class="{ active: activeTab === 'equipment' }" @click="activeTab = 'equipment'">设备</view>
      <view class="lab-detail-page__tab" :class="{ active: activeTab === 'schedule' }" @click="activeTab = 'schedule'">排期</view>
      <view class="lab-detail-page__tab" :class="{ active: activeTab === 'rules' }" @click="activeTab = 'rules'">规则</view>
    </view>

    <view class="lab-detail-page__body" :class="{ 'is-rules': activeTab === 'rules' }">
      <view class="lab-detail-page__main" :class="{ 'is-rules': activeTab === 'rules' }">
        <view v-if="activeTab === 'overview'" class="lab-detail-page__block">
          <view class="lab-detail-page__block-title">关于实验室</view>
          <view class="lab-detail-page__intro-grid">
            <view class="lab-detail-page__intro">{{ introLeft }}</view>
            <view class="lab-detail-page__intro">{{ introRight }}</view>
          </view>
          <view class="lab-detail-page__facts">
            <view v-for="(fact, index) in labFacts" :key="index" class="lab-detail-page__fact-chip">
              {{ fact }}
            </view>
          </view>
        </view>


        <view v-if="activeTab === 'equipment'" class="lab-detail-page__block">
          <view class="lab-detail-page__block-head">
            <view class="lab-detail-page__block-title">关键设备</view>
          </view>
          <view v-if="!equipmentList.length" class="lab-detail-page__empty">当前暂无设备信息。</view>
          <view v-else class="lab-detail-page__equip-grid">
            <view v-for="(item, index) in equipmentList" :key="item.id || index" class="lab-detail-page__equip-card">
              <view class="lab-detail-page__equip-name">{{ item.equipment_name || item.name || '设备' }}</view>
              <view class="lab-detail-page__equip-desc">数量 {{ item.quantity || 0 }} · {{ item.status === 'active' ? '运行中' : '维护中' }}</view>
              <view class="lab-detail-page__equip-status" :class="item.status === 'active' ? 'active' : 'pending'">
                {{ item.status === 'active' ? '运行中' : '待维护' }}
              </view>
            </view>
          </view>
        </view>

        <view v-if="activeTab === 'schedule'" class="lab-detail-page__block">
          <view class="lab-detail-page__block-head">
            <view class="lab-detail-page__block-meta">
              <view class="lab-detail-page__block-title">日程排期</view>
              <view class="lab-detail-page__block-sub">切换日期查看预约占用、空闲时段与当前审批状态。</view>
            </view>
            <picker mode="date" :value="selectedDate" @change="changeDate">
              <view class="lab-detail-page__date-chip">{{ selectedDateLabel }}</view>
            </picker>
          </view>

          <view class="lab-detail-page__metric-grid">
            <view v-for="(item, index) in scheduleHighlights" :key="index" class="lab-detail-page__metric-card">
              <view class="lab-detail-page__metric-label">{{ item.label }}</view>
              <view class="lab-detail-page__metric-value">{{ item.value }}</view>
              <view class="lab-detail-page__metric-hint">{{ item.hint }}</view>
            </view>
          </view>

          <view class="lab-detail-page__section-head">
            <view>
              <view class="lab-detail-page__section-title">预约时段</view>
              <view class="lab-detail-page__section-sub">待审批和已通过的预约都会占用时间窗口。</view>
            </view>
            <view class="lab-detail-page__section-tag">{{ scheduleItems.length }} 条记录</view>
          </view>

          <view v-if="scheduleItems.length" class="lab-detail-page__agenda-list">
            <view v-for="item in scheduleItems" :key="item.id" class="lab-detail-page__agenda-card">
              <view class="lab-detail-page__agenda-top">
                <view class="lab-detail-page__agenda-time">{{ item.timeLabel }}</view>
                <view class="lab-detail-page__agenda-status" :class="'is-' + item.status">{{ item.statusText }}</view>
              </view>
              <view class="lab-detail-page__agenda-purpose">{{ item.purpose || '未填写用途说明' }}</view>
              <view class="lab-detail-page__agenda-meta">{{ item.ownerText }} · {{ item.participantText }}</view>
            </view>
          </view>
          <view v-else class="lab-detail-page__empty">所选日期暂无预约记录，当前时段均可申请。</view>

          <view class="lab-detail-page__section-head compact">
            <view>
              <view class="lab-detail-page__section-title">空闲窗口</view>
              <view class="lab-detail-page__section-sub">系统按当前排期自动推算可预约区间。</view>
            </view>
            <view class="lab-detail-page__section-tag">{{ fullAvailableSlots.length }} 段</view>
          </view>

          <view v-if="fullAvailableSlots.length" class="lab-detail-page__availability-list">
            <view v-for="(slot, index) in fullAvailableSlots" :key="slot + '-' + index" class="lab-detail-page__availability-item">
              <view class="lab-detail-page__availability-index">{{ String(index + 1).padStart(2, '0') }}</view>
              <view class="lab-detail-page__availability-time">{{ slot }}</view>
              <view
                class="lab-detail-page__availability-action"
                :class="{ disabled: !canReserve }"
                @click="goReserve"
              >
                {{ canReserve ? '预约此时段' : '当前不可约' }}
              </view>
            </view>
          </view>
          <view v-else class="lab-detail-page__slot-empty">该日期已无满足 30 分钟及以上的空闲时段。</view>
        </view>

        <view v-if="activeTab === 'rules'" class="lab-detail-page__block lab-detail-page__block--scroll">
          <view class="lab-detail-page__block-meta">
            <view class="lab-detail-page__block-title">预约规则</view>
            <view class="lab-detail-page__block-sub">以下说明基于当前系统已实现的预约、审批和准入逻辑整理。</view>
          </view>

          <view class="lab-detail-page__flow-grid">
            <view v-for="(item, index) in ruleSteps" :key="index" class="lab-detail-page__flow-card">
              <view class="lab-detail-page__flow-index">{{ index + 1 }}</view>
              <view class="lab-detail-page__flow-title">{{ item.title }}</view>
              <view class="lab-detail-page__flow-desc">{{ item.desc }}</view>
            </view>
          </view>

          <view class="lab-detail-page__rule-grid">
            <view v-for="(group, index) in ruleGroups" :key="index" class="lab-detail-page__rule-card">
              <view class="lab-detail-page__rule-card-title">{{ group.title }}</view>
              <view class="lab-detail-page__rule-card-list">
                <view v-for="(item, subIndex) in group.items" :key="subIndex" class="lab-detail-page__rule-card-item">
                  <view class="lab-detail-page__rule-dot"></view>
                  <view class="lab-detail-page__rule-text">{{ item }}</view>
                </view>
              </view>
            </view>
          </view>
        </view>
      </view>

      <view class="lab-detail-page__side">
        <view class="lab-detail-page__card">
          <view class="lab-detail-page__card-title">位置与访问</view>
          <view class="lab-detail-page__map">
            <image
              v-if="heroImage"
              class="lab-detail-page__map-img"
              :src="heroImage"
              mode="aspectFill"
            />
            <view class="lab-detail-page__map-mask"></view>
          </view>
          <view class="lab-detail-page__card-item">
            <view class="lab-detail-page__card-item-title">{{ detail.campus_name || '校区待定' }}</view>
            <view class="lab-detail-page__card-item-sub">{{ detail.location || '楼层与房间待补充' }}</view>
          </view>
          <view class="lab-detail-page__card-item">
            <view class="lab-detail-page__card-item-title">仅限预约访问</view>
            <view class="lab-detail-page__card-item-sub">需携带有效校园身份凭证</view>
          </view>
          <view class="lab-detail-page__checklist">
            <view v-for="(item, index) in accessChecklist" :key="index" class="lab-detail-page__check-item">
              <view class="lab-detail-page__check-dot"></view>
              <view class="lab-detail-page__check-text">{{ item }}</view>
            </view>
          </view>
        </view>
      </view>
    </view>

    <!-- <site-footer /> -->
  </view>
</template>

<script>
import SiteFooter from '../../components/site-footer.vue'
import StudentTopNav from '../../components/student-top-nav.vue'
import { api } from '../../api/index'
import { requireLogin } from '../../common/guard'
import { openPage } from '../../common/router'
import { routes } from '../../config/navigation'

const HERO_COVERS = [
  'linear-gradient(120deg, #0e3349 0%, #0e3f62 45%, #0a2146 100%)',
  'linear-gradient(120deg, #14314d 0%, #225f89 48%, #0b2144 100%)',
  'linear-gradient(120deg, #23385c 0%, #3a5d8f 46%, #162746 100%)'
]

const ACTIVE_RESERVATION_STATUSES = ['pending', 'approved']

function toMinuteValue(raw) {
  if (!raw) return 0
  const safe = String(raw).slice(0, 5)
  const parts = safe.split(':')
  const h = Number(parts[0] || 0)
  const m = Number(parts[1] || 0)
  return h * 60 + m
}

function toTimeLabel(minutes) {
  const h = Math.floor(minutes / 60)
  const m = minutes % 60
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`
}

function todayString() {
  const now = new Date()
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`
}

function formatDateLabel(raw) {
  if (!raw) return '未选择日期'
  const [year, month, day] = String(raw).split('-').map((item) => Number(item))
  if (!year || !month || !day) return String(raw)
  const date = new Date(year, month - 1, day)
  const weeks = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']
  return `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')} ${weeks[date.getDay()]}`
}

function formatDuration(minutes) {
  const safe = Math.max(0, Number(minutes) || 0)
  const hours = Math.floor(safe / 60)
  const mins = safe % 60
  if (hours && mins) return `${hours}小时${mins}分钟`
  if (hours) return `${hours}小时`
  return `${mins}分钟`
}

function getStatusText(status) {
  return {
    pending: '待审批',
    approved: '已通过',
    rejected: '已拒绝',
    cancelled: '已取消'
  }[status] || '处理中'
}

function buildAvailableSlots(openMinute, closeMinute, reservations) {
  const blocks = reservations
    .filter((item) => ACTIVE_RESERVATION_STATUSES.includes(item.status))
    .map((item) => ({
      start: toMinuteValue(item.start_time),
      end: toMinuteValue(item.end_time)
    }))
    .sort((a, b) => a.start - b.start)

  const slots = []
  let cursor = openMinute
  blocks.forEach((item) => {
    if (item.start > cursor) {
      slots.push([cursor, Math.min(item.start, closeMinute)])
    }
    cursor = Math.max(cursor, item.end)
  })
  if (cursor < closeMinute) {
    slots.push([cursor, closeMinute])
  }
  return slots.filter(([start, end]) => end - start >= 30)
}

export default {
  components: { SiteFooter, StudentTopNav },
  data() {
    return {
      id: '',
      detail: {},
      schedule: {},
      selectedDate: todayString(),
      activeTab: 'overview'
    }
  },
  computed: {
    heroImage() {
      return Array.isArray(this.detail.photos) && this.detail.photos.length ? this.detail.photos[0] : ''
    },
    heroStyle() {
      if (this.heroImage) {
        return {
          backgroundImage: `url(${this.heroImage})`,
          backgroundSize: 'cover',
          backgroundPosition: 'center',
          backgroundRepeat: 'no-repeat'
        }
      }
      return { background: this.heroCover }
    },
    heroCover() {
      const index = Number(this.id || 0) % HERO_COVERS.length
      return HERO_COVERS[index]
    },
    equipmentList() {
      return this.detail.equipment || []
    },
    canReserve() {
      return this.detail.status === 'active'
    },
    securityLabel() {
      const text = `${this.detail.lab_name || ''} ${this.detail.description || ''}`.toLowerCase()
      if (text.includes('病原') || text.includes('高危') || text.includes('病毒')) return '4级生物安全'
      if (text.includes('生物') || text.includes('基因')) return '3级生物安全'
      return '2级生物安全'
    },
    defaultDesc() {
      return '面向教学与科研开放，支持标准化预约、审批与安全准入。'
    },
    selectedDateLabel() {
      return formatDateLabel(this.selectedDate)
    },
    introLeft() {
      return `${this.detail.lab_name || '该实验室'}面向课程实验、科研训练与项目协作开放，提供稳定工位与标准化设备支持。`
    },
    introRight() {
      return `开放时间为 ${this.timeRange}，预约需经过审批并遵循准入规范，建议按可预约时段提前安排。`
    },
    labFacts() {
      return [
        `开放时段 ${this.timeRange}`,
        `容量 ${this.detail.capacity || 0} 人`,
        `${this.detail.status === 'active' ? '当前可预约' : '当前维护中'}`,
        `安全等级 ${this.securityLabel}`
      ]
    },
    scheduleOpenTime() {
      const source = this.schedule?.open_time || this.detail.open_time || '08:00'
      return String(source).slice(0, 5)
    },
    scheduleCloseTime() {
      const source = this.schedule?.close_time || this.detail.close_time || '18:00'
      return String(source).slice(0, 5)
    },
    timeRange() {
      return `${this.scheduleOpenTime} - ${this.scheduleCloseTime}`
    },
    scheduleReservations() {
      return Array.isArray(this.schedule?.reservations) ? this.schedule.reservations : []
    },
    activeScheduleReservations() {
      return this.scheduleReservations.filter((item) => ACTIVE_RESERVATION_STATUSES.includes(item.status))
    },
    totalOpenMinutes() {
      return Math.max(0, toMinuteValue(this.scheduleCloseTime) - toMinuteValue(this.scheduleOpenTime))
    },
    bookedMinutes() {
      return this.activeScheduleReservations.reduce((sum, item) => {
        const start = toMinuteValue(item.start_time)
        const end = toMinuteValue(item.end_time)
        return sum + Math.max(0, end - start)
      }, 0)
    },
    usageRate() {
      if (!this.totalOpenMinutes) return 0
      return Math.min(100, Math.round((this.bookedMinutes / this.totalOpenMinutes) * 100))
    },
    bookedCount() {
      return this.activeScheduleReservations.length
    },
    accessChecklist() {
      return [
        '需实名预约并通过审批后进入',
        '进门请出示校园证件',
        '进入前完成基础安全培训'
      ]
    },
    fullAvailableSlots() {
      return buildAvailableSlots(
        toMinuteValue(this.scheduleOpenTime),
        toMinuteValue(this.scheduleCloseTime),
        this.scheduleReservations
      ).map(([start, end]) => `${toTimeLabel(start)} - ${toTimeLabel(end)}`)
    },
    scheduleHighlights() {
      return [
        {
          label: '开放时段',
          value: this.timeRange,
          hint: this.selectedDateLabel
        },
        {
          label: '已占用时长',
          value: formatDuration(this.bookedMinutes),
          hint: `${this.bookedCount} 条有效预约`
        },
        {
          label: '空闲窗口',
          value: `${this.fullAvailableSlots.length} 段`,
          hint: this.fullAvailableSlots.length ? `最近空档 ${this.fullAvailableSlots[0]}` : '当天暂无可预约时段'
        },
        {
          label: '预计占用率',
          value: `${this.usageRate}%`,
          hint: this.bookedCount ? '待审批与已通过均占用时段' : '当前排期较为空闲'
        }
      ]
    },
    scheduleItems() {
      return this.scheduleReservations.map((item) => ({
        ...item,
        timeLabel: `${String(item.start_time || '').slice(0, 5)} - ${String(item.end_time || '').slice(0, 5)}`,
        statusText: getStatusText(item.status),
        ownerText: item.user_name || '预约人待确认',
        participantText: `${item.participant_count || 0} 人参与`
      }))
    },
    ruleSteps() {
      return [
        {
          title: '查看排期',
          desc: `先确认 ${this.selectedDateLabel} 的空闲时段，再决定预约时间。`
        },
        {
          title: '提交预约',
          desc: `填写用途、人数和所需设备，人数上限为 ${this.detail.capacity || 0} 人。`
        },
        {
          title: '等待审批',
          desc: '学生与教师预约默认进入待审批状态，管理员预约可直接通过。'
        },
        {
          title: '到场使用',
          desc: '按预约时间入场，携带有效校园身份凭证并遵守安全准入要求。'
        }
      ]
    },
    ruleGroups() {
      return [
        {
          title: '时间约束',
          items: [
            `预约时间必须落在开放时段 ${this.timeRange} 内`,
            '开始时间必须早于结束时间',
            '同一实验室同一时间段不允许存在重复预约'
          ]
        },
        {
          title: '人数与资源',
          items: [
            `参与人数不得超过实验室容量上限 ${this.detail.capacity || 0} 人`,
            '设备使用以当前库存和运行状态为准',
            '建议按空闲窗口提交申请，避免与已有预约冲突'
          ]
        },
        {
          title: '审批与权限',
          items: [
            '学生和教师预约默认需要审批',
            '实验室管理员只能审批自己校区的预约',
            '审批结果支持待审批、已通过、已拒绝和已取消等状态'
          ]
        },
        {
          title: '准入要求',
          items: [
            '停用或维护中的实验室不可预约',
            '账号被禁用的用户不能提交预约',
            '进入实验室前请完成基础安全培训并携带校园证件'
          ]
        }
      ]
    }
  },
  onLoad(options) {
    this.id = options.id || ''
    this.selectedDate = options.date || todayString()
  },
  async onShow() {
    if (!requireLogin()) return
    await this.loadData()
  },
  methods: {
    async loadData() {
      try {
        const [detailRes, scheduleRes] = await Promise.all([
          api.labDetail(this.id),
          api.labSchedule(this.id, this.selectedDate)
        ])
        this.detail = detailRes || {}
        this.schedule = scheduleRes || {}
      } catch (error) {
        this.detail = {}
        this.schedule = {}
      }
    },
    async changeDate(event) {
      this.selectedDate = event.detail.value
      try {
        this.schedule = await api.labSchedule(this.id, this.selectedDate)
      } catch (error) {
        this.schedule = {}
      }
    },
    goReserve() {
      if (!this.canReserve) {
        uni.showToast({
          title: '该实验室维护中，当前不能预约',
          icon: 'none',
          duration: 2200
        })
        return
      }
      openPage(routes.reserve, {
        query: { labId: this.id, campusId: this.detail.campus_id, date: this.selectedDate }
      })
    }
  }
}
</script>

<style lang="scss">
.lab-detail-page {
  height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background:
    radial-gradient(circle at 12% 14%, rgba(109, 179, 230, 0.25), transparent 26%),
    radial-gradient(circle at 88% 18%, rgba(173, 208, 240, 0.26), transparent 24%),
    linear-gradient(180deg, #edf5fc 0%, #dceaf7 100%);
}

.lab-detail-page__hero {
  margin: 0 32rpx;
  min-height: 600rpx;
  border-radius: 0 0 20rpx 20rpx;
  position: relative;
  overflow: hidden;
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  padding: 34rpx;
}

.lab-detail-page__hero::before {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(180deg, rgba(5, 24, 54, 0.14), rgba(5, 24, 54, 0.7));
}

.lab-detail-page__hero-overlay,
.lab-detail-page__hero-action {
  position: relative;
  z-index: 1;
}

.lab-detail-page__hero-meta {
  display: flex;
  gap: 10rpx;
}

.lab-detail-page__pill {
  height: 40rpx;
  border-radius: 999rpx;
  padding: 0 14rpx;
  display: inline-flex;
  align-items: center;
  background: rgba(255, 255, 255, 0.2);
  color: #f1f7ff;
  font-size: 20rpx;
  font-weight: 700;
}

.lab-detail-page__hero-path {
  margin-top: 16rpx;
  color: #cde0f8;
  font-size: 22rpx;
  font-weight: 700;
}

.lab-detail-page__hero-title {
  margin-top: 8rpx;
  font-size: 72rpx;
  line-height: 1.05;
  color: #ffffff;
  font-weight: 800;
  letter-spacing: -1.2rpx;
}

.lab-detail-page__hero-sub {
  margin-top: 10rpx;
  max-width: 980rpx;
  color: #d4e4f8;
  font-size: 25rpx;
  line-height: 1.5;
}

.lab-detail-page__hero-action {
  min-width: 210rpx;
  height: 76rpx;
  border-radius: 16rpx;
  padding: 0 24rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #ffffff;
  color: #092750;
  font-size: 24rpx;
  font-weight: 800;
}

.lab-detail-page__hero-action.disabled {
  background: rgba(232, 238, 247, 0.74);
  color: #64748a;
}

.lab-detail-page__tabs {
  margin: 0 32rpx;
  min-height: 86rpx;
  padding: 0 20rpx;
  display: flex;
  align-items: center;
  gap: 28rpx;
  border-bottom: 1rpx solid rgba(197, 198, 207, 0.4);
}

.lab-detail-page__tab {
  height: 84rpx;
  display: inline-flex;
  align-items: center;
  color: #4f5f79;
  font-size: 25rpx;
  font-weight: 700;
  border-bottom: 4rpx solid transparent;
}

.lab-detail-page__tab.active {
  color: #0d2548;
  border-bottom-color: #0d2548;
}

.lab-detail-page__body {
  flex: 1;
  min-height: 0;
  padding: 20rpx 32rpx 40rpx;
  display: grid;
  grid-template-columns: minmax(0, 1.9fr) minmax(300rpx, 0.9fr);
  gap: 24rpx;
  overflow: hidden;
}

.lab-detail-page__main {
  min-height: 0;
  overflow-y: auto;
}

.lab-detail-page__main.is-rules {
  overflow: hidden;
}

.lab-detail-page__block {
  background: rgba(255, 255, 255, 0.74);
  border-radius: 20rpx;
  border: 1rpx solid rgba(197, 198, 207, 0.28);
  padding: 22rpx;
  margin-bottom: 20rpx;
}

.lab-detail-page__block--scroll {
  height: 100%;
  max-height: none;
  overflow-y: auto;
  overscroll-behavior: contain;
  margin-bottom: 0;
}

.lab-detail-page__block-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.lab-detail-page__block-meta {
  display: grid;
  gap: 8rpx;
}

.lab-detail-page__block-title {
  font-size: 48rpx;
  color: #061f44;
  font-weight: 800;
}

.lab-detail-page__block-sub {
  color: #6b7f98;
  font-size: 22rpx;
  line-height: 1.6;
}


.lab-detail-page__date-chip {
  min-height: 60rpx;
  border-radius: 999rpx;
  padding: 0 18rpx;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: #eef4fb;
  border: 1rpx solid #d7e2ef;
  color: #14345c;
  font-size: 21rpx;
  font-weight: 700;
}

.lab-detail-page__intro-grid {
  margin-top: 16rpx;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 20rpx;
}

.lab-detail-page__intro {
  color: #304761;
  font-size: 25rpx;
  line-height: 1.75;
}

.lab-detail-page__facts {
  margin-top: 16rpx;
  display: flex;
  flex-wrap: wrap;
  gap: 10rpx;
}

.lab-detail-page__fact-chip {
  min-height: 42rpx;
  border-radius: 999rpx;
  padding: 0 14rpx;
  background: #edf3fa;
  border: 1rpx solid #d8e3f0;
  color: #17375e;
  font-size: 20rpx;
  font-weight: 700;
  display: inline-flex;
  align-items: center;
}

.lab-detail-page__equip-grid {
  margin-top: 16rpx;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14rpx;
}

.lab-detail-page__equip-card {
  border-radius: 16rpx;
  background: #f2f6fb;
  border-left: 6rpx solid #1ab7e6;
  padding: 16rpx;
}

.lab-detail-page__equip-name {
  color: #081e43;
  font-size: 30rpx;
  line-height: 1.25;
  font-weight: 800;
}

.lab-detail-page__equip-desc {
  margin-top: 8rpx;
  color: #5b6b82;
  font-size: 22rpx;
}

.lab-detail-page__equip-status {
  margin-top: 10rpx;
  display: inline-flex;
  min-height: 34rpx;
  border-radius: 999rpx;
  padding: 0 10rpx;
  align-items: center;
  font-size: 20rpx;
  font-weight: 700;
}

.lab-detail-page__equip-status.active {
  background: #d9f7e7;
  color: #178f5d;
}

.lab-detail-page__equip-status.pending {
  background: #ffe9c9;
  color: #b67818;
}

.lab-detail-page__empty {
  margin-top: 14rpx;
  color: #70839b;
  font-size: 23rpx;
}

.lab-detail-page__metric-grid {
  margin-top: 18rpx;
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14rpx;
}

.lab-detail-page__metric-card {
  border-radius: 18rpx;
  padding: 18rpx;
  background: #f3f7fb;
  border: 1rpx solid #dde7f2;
}

.lab-detail-page__metric-label {
  color: #70829a;
  font-size: 20rpx;
  font-weight: 700;
}

.lab-detail-page__metric-value {
  margin-top: 8rpx;
  color: #082043;
  font-size: 34rpx;
  line-height: 1.25;
  font-weight: 800;
}

.lab-detail-page__metric-hint {
  margin-top: 10rpx;
  color: #60738d;
  font-size: 20rpx;
  line-height: 1.5;
}

.lab-detail-page__section-head {
  margin-top: 24rpx;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16rpx;
}

.lab-detail-page__section-head.compact {
  margin-top: 20rpx;
}

.lab-detail-page__section-title {
  color: #09244c;
  font-size: 28rpx;
  font-weight: 800;
}

.lab-detail-page__section-sub {
  margin-top: 6rpx;
  color: #70829c;
  font-size: 20rpx;
  line-height: 1.5;
}

.lab-detail-page__section-tag {
  min-height: 42rpx;
  border-radius: 999rpx;
  padding: 0 14rpx;
  background: #edf3fa;
  color: #173b66;
  font-size: 19rpx;
  font-weight: 700;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.lab-detail-page__agenda-list {
  margin-top: 14rpx;
  display: grid;
  gap: 12rpx;
}

.lab-detail-page__agenda-card {
  border-radius: 18rpx;
  padding: 18rpx;
  background: #fbfdff;
  border: 1rpx solid #dbe6f2;
}

.lab-detail-page__agenda-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16rpx;
}

.lab-detail-page__agenda-time {
  color: #0a2348;
  font-size: 28rpx;
  font-weight: 800;
}

.lab-detail-page__agenda-status {
  min-height: 40rpx;
  border-radius: 999rpx;
  padding: 0 14rpx;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 19rpx;
  font-weight: 700;
}

.lab-detail-page__agenda-status.is-pending {
  background: rgba(242, 153, 74, 0.14);
  color: #c77b1f;
}

.lab-detail-page__agenda-status.is-approved {
  background: rgba(39, 174, 96, 0.12);
  color: #178452;
}

.lab-detail-page__agenda-status.is-rejected {
  background: rgba(235, 87, 87, 0.12);
  color: #d44f4f;
}

.lab-detail-page__agenda-status.is-cancelled {
  background: rgba(154, 160, 166, 0.14);
  color: #68717b;
}

.lab-detail-page__agenda-purpose {
  margin-top: 12rpx;
  color: #203955;
  font-size: 24rpx;
  line-height: 1.6;
}

.lab-detail-page__agenda-meta {
  margin-top: 8rpx;
  color: #70829c;
  font-size: 20rpx;
}

.lab-detail-page__availability-list {
  margin-top: 14rpx;
  display: grid;
  gap: 10rpx;
}

.lab-detail-page__availability-item {
  border-radius: 16rpx;
  padding: 16rpx 18rpx;
  background: #f4f8fb;
  border: 1rpx solid #d9e4ef;
  display: flex;
  align-items: center;
  gap: 16rpx;
}

.lab-detail-page__availability-index {
  width: 52rpx;
  height: 52rpx;
  border-radius: 14rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #0f2f5a;
  color: #f4f8ff;
  font-size: 20rpx;
  font-weight: 800;
  flex-shrink: 0;
}

.lab-detail-page__availability-time {
  color: #082043;
  font-size: 24rpx;
  font-weight: 700;
}

.lab-detail-page__availability-action {
  margin-left: auto;
  min-height: 52rpx;
  border-radius: 999rpx;
  padding: 0 16rpx;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: #e8f2fb;
  color: #0d4b78;
  font-size: 20rpx;
  font-weight: 700;
}

.lab-detail-page__availability-action.disabled {
  background: #edf2f7;
  color: #7a889c;
}

.lab-detail-page__flow-grid {
  margin-top: 18rpx;
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14rpx;
}

.lab-detail-page__flow-card {
  min-height: 210rpx;
  border-radius: 18rpx;
  padding: 18rpx;
  background: linear-gradient(180deg, #f8fbff 0%, #eef4fb 100%);
  border: 1rpx solid #d8e4f0;
}

.lab-detail-page__flow-index {
  width: 52rpx;
  height: 52rpx;
  border-radius: 14rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #0d294f;
  color: #ffffff;
  font-size: 22rpx;
  font-weight: 800;
}

.lab-detail-page__flow-title {
  margin-top: 16rpx;
  color: #071f43;
  font-size: 28rpx;
  font-weight: 800;
}

.lab-detail-page__flow-desc {
  margin-top: 10rpx;
  color: #526884;
  font-size: 21rpx;
  line-height: 1.65;
}

.lab-detail-page__rule-grid {
  margin-top: 16rpx;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14rpx;
}

.lab-detail-page__rule-card {
  border-radius: 18rpx;
  padding: 18rpx;
  background: #fbfdff;
  border: 1rpx solid #dbe6f2;
}

.lab-detail-page__rule-card-title {
  color: #072044;
  font-size: 28rpx;
  font-weight: 800;
}

.lab-detail-page__rule-card-list {
  margin-top: 14rpx;
  display: grid;
  gap: 10rpx;
}

.lab-detail-page__rule-card-item {
  display: flex;
  align-items: flex-start;
  gap: 8rpx;
}

.lab-detail-page__side {
  display: grid;
  gap: 16rpx;
  align-content: start;
  min-height: 0;
  overflow-y: auto;
}

.lab-detail-page__card {
  border-radius: 20rpx;
  background: rgba(255, 255, 255, 0.74);
  border: 1rpx solid rgba(197, 198, 207, 0.28);
  padding: 18rpx;
}

.lab-detail-page__card-title {
  color: #081f43;
  font-size: 38rpx;
  font-weight: 800;
}

.lab-detail-page__map {
  margin-top: 12rpx;
  height: 220rpx;
  border-radius: 16rpx;
  position: relative;
  overflow: hidden;
  background: linear-gradient(135deg, #737b86, #b2b7bd);
}

.lab-detail-page__map-img {
  width: 100%;
  height: 100%;
  display: block;
}

.lab-detail-page__map-mask {
  position: absolute;
  inset: 0;
  background: linear-gradient(180deg, rgba(3, 22, 53, 0.12), rgba(3, 22, 53, 0.2));
}

.lab-detail-page__card-item {
  margin-top: 14rpx;
}

.lab-detail-page__card-item-title {
  color: #0e2a4f;
  font-size: 24rpx;
  font-weight: 700;
}

.lab-detail-page__card-item-sub {
  margin-top: 4rpx;
  color: #6d7c93;
  font-size: 21rpx;
}

.lab-detail-page__checklist {
  margin-top: 14rpx;
  display: grid;
  gap: 8rpx;
}

.lab-detail-page__check-item {
  display: flex;
  align-items: flex-start;
  gap: 8rpx;
}

.lab-detail-page__check-dot {
  width: 12rpx;
  height: 12rpx;
  border-radius: 50%;
  margin-top: 9rpx;
  background: #1e8ec4;
  flex-shrink: 0;
}

.lab-detail-page__check-text {
  color: #3f5775;
  font-size: 21rpx;
  line-height: 1.5;
}

.lab-detail-page__slot-empty {
  margin-top: 10rpx;
  color: #6c7f98;
  font-size: 20rpx;
}

.lab-detail-page__rule-dot {
  width: 12rpx;
  height: 12rpx;
  border-radius: 50%;
  margin-top: 9rpx;
  background: #0f5b91;
  flex-shrink: 0;
}

.lab-detail-page__rule-text {
  color: #334d6d;
  font-size: 21rpx;
  line-height: 1.55;
}




@media screen and (min-width: 1500px) {
  .lab-detail-page__hero,
  .lab-detail-page__tabs,
  .lab-detail-page__body {
    margin-left: 56rpx;
    margin-right: 56rpx;
  }
}

@media screen and (max-width: 1100px) {
  .lab-detail-page__body,
  .lab-detail-page__intro-grid,
  .lab-detail-page__equip-grid,
  .lab-detail-page__flow-grid {
    grid-template-columns: 1fr;
  }

  .lab-detail-page__metric-grid,
  .lab-detail-page__rule-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media screen and (max-width: 760px) {
  .lab-detail-page__hero {
    padding: 20rpx;
    min-height: 340rpx;
  }

  .lab-detail-page__hero-title {
    font-size: 46rpx;
  }

  .lab-detail-page__hero-action {
    min-width: 160rpx;
    height: 66rpx;
    font-size: 22rpx;
  }

  .lab-detail-page__block-head,
  .lab-detail-page__section-head,
  .lab-detail-page__availability-item {
    display: grid;
  }

  .lab-detail-page__metric-grid,
  .lab-detail-page__rule-grid {
    grid-template-columns: 1fr;
  }

  .lab-detail-page__agenda-top {
    align-items: flex-start;
  }

  .lab-detail-page__availability-action {
    margin-left: 0;
    width: fit-content;
  }

}

</style>
