<template>
  <view class="lab-detail-page">
    <!-- #ifdef H5 -->
    <student-top-nav active="labs" />
    <!-- #endif -->

    <!-- #ifndef H5 -->
    <user-top-nav active="labs" />
    <!-- #endif -->

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
      <view class="lab-detail-page__hero-action" @click="goReserve">立即预约</view>
    </view>

    <view class="lab-detail-page__tabs">
      <view class="lab-detail-page__tab active">概览</view>
      <view class="lab-detail-page__tab">设备</view>
      <view class="lab-detail-page__tab">排期</view>
      <view class="lab-detail-page__tab">规则</view>
    </view>

    <view class="lab-detail-page__body">
      <view class="lab-detail-page__main">
        <view class="lab-detail-page__block">
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

        <view class="lab-detail-page__block">
          <view class="lab-detail-page__block-head">
            <view class="lab-detail-page__block-title">关键设备</view>
            <view class="lab-detail-page__link">查看完整库存</view>
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

        <view class="lab-detail-page__card">
          <view class="lab-detail-page__card-title">今日可用性</view>
          <view class="lab-detail-page__time-strip">
            <view class="lab-detail-page__time-seg">{{ timeRange }}</view>
            <view class="lab-detail-page__time-seg active">已预约 {{ bookedCount }} 段</view>
            <view class="lab-detail-page__time-seg">可约 {{ availableSlots.length }} 段</view>
          </view>
          <view class="lab-detail-page__book-btn" @click="goReserve">新预约</view>
          <view class="lab-detail-page__slot-head">
            <view class="lab-detail-page__slot-title">可预约时段</view>
            <view class="lab-detail-page__slot-count">{{ availableSlots.length }} 段</view>
          </view>
          <view v-if="availableSlots.length" class="lab-detail-page__slot-list">
            <view v-for="(slot, index) in availableSlots" :key="index" class="lab-detail-page__slot-chip">
              {{ slot }}
            </view>
          </view>
          <view v-else class="lab-detail-page__slot-empty">今日可预约时段已满，请改约其他日期。</view>
          <view class="lab-detail-page__next-time">下一个可用时段：{{ nextAvailableText }}</view>
        </view>

        <view class="lab-detail-page__card">
          <view class="lab-detail-page__card-title">预约规则</view>
          <view class="lab-detail-page__rule-list">
            <view v-for="(item, index) in bookingRules" :key="index" class="lab-detail-page__rule-item">
              <view class="lab-detail-page__rule-dot"></view>
              <view class="lab-detail-page__rule-text">{{ item }}</view>
            </view>
          </view>
        </view>

        <view class="lab-detail-page__owner">
          <view class="lab-detail-page__owner-avatar">管</view>
          <view class="lab-detail-page__owner-info">
            <view class="lab-detail-page__owner-role">实验室管理员</view>
            <view class="lab-detail-page__owner-name">{{ contactName }}</view>
          </view>
          <view class="lab-detail-page__owner-action" @click="showAccessGuide">准入说明</view>
        </view>
      </view>
    </view>

    <site-footer />
  </view>
</template>

<script>
import SiteFooter from '../../components/site-footer.vue'
import StudentTopNav from '../../components/student-top-nav.vue'
import UserTopNav from '../../components/user-top-nav.vue'
import { api } from '../../api/index'
import { requireLogin } from '../../common/guard'
import { openPage } from '../../common/router'
import { routes } from '../../config/navigation'

const HERO_COVERS = [
  'linear-gradient(120deg, #0e3349 0%, #0e3f62 45%, #0a2146 100%)',
  'linear-gradient(120deg, #14314d 0%, #225f89 48%, #0b2144 100%)',
  'linear-gradient(120deg, #23385c 0%, #3a5d8f 46%, #162746 100%)'
]

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

export default {
  components: { SiteFooter, StudentTopNav, UserTopNav },
  data() {
    return {
      id: '',
      detail: {},
      schedule: {},
      selectedDate: todayString()
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
    securityLabel() {
      const text = `${this.detail.lab_name || ''} ${this.detail.description || ''}`.toLowerCase()
      if (text.includes('病原') || text.includes('高危') || text.includes('病毒')) return '4级生物安全'
      if (text.includes('生物') || text.includes('基因')) return '3级生物安全'
      return '2级生物安全'
    },
    defaultDesc() {
      return '面向教学与科研开放，支持标准化预约、审批与安全准入。'
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
    timeRange() {
      if (!this.detail.open_time || !this.detail.close_time) return '08:00 - 18:00'
      return `${this.detail.open_time.slice(0, 5)} - ${this.detail.close_time.slice(0, 5)}`
    },
    bookedCount() {
      const reservations = Array.isArray(this.schedule?.reservations) ? this.schedule.reservations : []
      return reservations.filter((item) => !['cancelled', 'rejected'].includes(item.status)).length
    },
    accessChecklist() {
      return [
        '需实名预约并通过审批后进入',
        '进门请出示校园证件',
        '进入前完成基础安全培训'
      ]
    },
    availableSlots() {
      const sourceOpen = this.schedule?.open_time || this.detail.open_time
      const sourceClose = this.schedule?.close_time || this.detail.close_time
      const openMinute = toMinuteValue(sourceOpen || '08:00')
      const closeMinute = toMinuteValue(sourceClose || '18:00')
      const reservations = Array.isArray(this.schedule?.reservations) ? this.schedule.reservations : []
      const blocks = reservations
        .filter((item) => !['cancelled', 'rejected'].includes(item.status))
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
      if (cursor < closeMinute) slots.push([cursor, closeMinute])

      return slots
        .filter(([start, end]) => end - start >= 30)
        .slice(0, 5)
        .map(([start, end]) => `${toTimeLabel(start)} - ${toTimeLabel(end)}`)
    },
    bookingRules() {
      return [
        '最短预约 30 分钟，最长预约 4 小时',
        '仅支持开放时段内预约',
        '开始前 15 分钟可取消，不计违约',
        '学生与教师预约默认需要审批'
      ]
    },
    contactName() {
      return `${this.detail.campus_name || '本校区'} 管理员`
    },
    nextAvailableText() {
      const list = this.availableSlots
      if (!list.length) return '今日已约满'
      return list[0]
    }
  },
  onLoad(options) {
    this.id = options.id || ''
  },
  async onShow() {
    if (!requireLogin()) return
    // #ifdef H5
    uni.hideTabBar()
    // #endif
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
    goReserve() {
      openPage(routes.reserve, {
        query: { labId: this.id, campusId: this.detail.campus_id, date: this.selectedDate }
      })
    },
    showAccessGuide() {
      uni.showToast({
        title: '请先完成预约审批并携带有效校园证件',
        icon: 'none',
        duration: 2200
      })
    }
  }
}
</script>

<style lang="scss">
.lab-detail-page {
  min-height: 100vh;
  background:
    radial-gradient(circle at top right, rgba(65, 190, 253, 0.11), transparent 24%),
    linear-gradient(180deg, #f7f9fc 0%, #eef2f7 100%);
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
  padding: 20rpx 32rpx 40rpx;
  display: grid;
  grid-template-columns: minmax(0, 1.9fr) minmax(300rpx, 0.9fr);
  gap: 24rpx;
}

.lab-detail-page__block {
  background: rgba(255, 255, 255, 0.74);
  border-radius: 20rpx;
  border: 1rpx solid rgba(197, 198, 207, 0.28);
  padding: 22rpx;
  margin-bottom: 20rpx;
}

.lab-detail-page__block-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.lab-detail-page__block-title {
  font-size: 48rpx;
  color: #061f44;
  font-weight: 800;
}

.lab-detail-page__link {
  color: #0d5a8f;
  font-size: 23rpx;
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

.lab-detail-page__side {
  display: grid;
  gap: 16rpx;
  align-content: start;
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

.lab-detail-page__time-strip {
  margin-top: 14rpx;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  border-radius: 12rpx;
  overflow: hidden;
}

.lab-detail-page__time-seg {
  min-height: 58rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #dfe4eb;
  color: #4e5f78;
  font-size: 19rpx;
  font-weight: 700;
}

.lab-detail-page__time-seg.active {
  background: #0c2a52;
  color: #f2f8ff;
}

.lab-detail-page__book-btn {
  margin-top: 14rpx;
  height: 74rpx;
  border-radius: 16rpx;
  background: #0a254c;
  color: #ecf4ff;
  font-size: 24rpx;
  font-weight: 800;
  display: flex;
  align-items: center;
  justify-content: center;
}

.lab-detail-page__slot-head {
  margin-top: 14rpx;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.lab-detail-page__slot-title {
  color: #09264e;
  font-size: 22rpx;
  font-weight: 800;
}

.lab-detail-page__slot-count {
  color: #5f7492;
  font-size: 20rpx;
  font-weight: 700;
}

.lab-detail-page__slot-list {
  margin-top: 10rpx;
  display: flex;
  flex-wrap: wrap;
  gap: 8rpx;
}

.lab-detail-page__slot-chip {
  min-height: 40rpx;
  border-radius: 999rpx;
  padding: 0 12rpx;
  background: #eff4fb;
  color: #1b3d67;
  border: 1rpx solid #d7e2ef;
  font-size: 19rpx;
  font-weight: 700;
  display: inline-flex;
  align-items: center;
}

.lab-detail-page__slot-empty {
  margin-top: 10rpx;
  color: #6c7f98;
  font-size: 20rpx;
}

.lab-detail-page__next-time {
  margin-top: 10rpx;
  color: #6f8098;
  font-size: 20rpx;
}

.lab-detail-page__owner {
  border-radius: 16rpx;
  background: rgba(255, 255, 255, 0.74);
  border: 1rpx solid rgba(197, 198, 207, 0.28);
  padding: 12rpx 16rpx;
  display: flex;
  align-items: center;
  gap: 12rpx;
}

.lab-detail-page__owner-avatar {
  width: 64rpx;
  height: 64rpx;
  border-radius: 999rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #1d3868, #72c6ff);
  color: #ffffff;
  font-weight: 800;
}

.lab-detail-page__owner-role {
  color: #70829c;
  font-size: 20rpx;
}

.lab-detail-page__owner-name {
  color: #0e2b51;
  font-size: 23rpx;
  font-weight: 700;
}

.lab-detail-page__owner-action {
  margin-left: auto;
  min-height: 56rpx;
  border-radius: 999rpx;
  padding: 0 18rpx;
  background: #edf3fa;
  color: #1c446f;
  font-size: 21rpx;
  font-weight: 700;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.lab-detail-page__rule-list {
  margin-top: 14rpx;
  display: grid;
  gap: 10rpx;
}

.lab-detail-page__rule-item {
  display: flex;
  align-items: flex-start;
  gap: 8rpx;
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

/* #ifndef H5 */
.lab-detail-page__hero,
.lab-detail-page__tabs,
.lab-detail-page__body {
  margin-left: 24rpx;
  margin-right: 24rpx;
}

.lab-detail-page__hero-title {
  font-size: 52rpx;
}

.lab-detail-page__body,
.lab-detail-page__intro-grid,
.lab-detail-page__equip-grid {
  grid-template-columns: 1fr;
}
/* #endif */

/* #ifdef H5 */
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
  .lab-detail-page__equip-grid {
    grid-template-columns: 1fr;
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
}
/* #endif */
</style>
