<template>
  <view class="student-home">
    <!-- #ifdef H5 -->
    <student-top-nav active="home" />
    <!-- #endif -->

    <!-- #ifndef H5 -->
    <user-top-nav active="home" />
    <!-- #endif -->

    <view class="student-home__body">
      <view class="student-home__shell">
        <view class="student-home__welcome">
          <view class="student-home__welcome-copy">
            <view class="student-home__welcome-title">欢迎回来，{{ displayName }}</view>
            <view class="student-home__welcome-sub">
              {{ currentDateText }} · {{ timeText }}
              <text class="student-home__welcome-highlight">{{ roleFocusText }}</text>
            </view>
          </view>

          <view class="student-home__welcome-badges">
            <view class="student-home__metric-badge">
              <text class="student-home__metric-icon">T</text>
              <text>22C</text>
            </view>
            <view class="student-home__metric-badge">
              <text class="student-home__metric-icon">NW</text>
              <text>High</text>
            </view>
          </view>
        </view>

        <view class="student-home__hero-grid">
          <view class="student-home__quick-grid">
            <view
              v-for="item in quickCards"
              :key="item.path"
              class="student-home__quick-card"
              @click="go(item.path)"
            >
              <view class="student-home__quick-icon">{{ item.icon }}</view>
              <view class="student-home__quick-title">{{ item.title }}</view>
            </view>
          </view>

          <view class="student-home__countdown">
            <view class="student-home__countdown-orb"></view>
            <view class="student-home__countdown-top">
              <text class="student-home__eyebrow">Upcoming</text>
              <text class="student-home__bell">Reminder</text>
            </view>

            <view>
              <view class="student-home__countdown-name">
                {{ upcomingReservation.lab_name || '当前没有即将开始的预约' }}
              </view>
              <view class="student-home__countdown-meta">
                {{ upcomingMeta }}
              </view>
            </view>

            <view class="student-home__countdown-bottom">
              <view>
                <view class="student-home__countdown-label">距离开始还有</view>
                <view class="student-home__countdown-value">{{ countdownText }}</view>
              </view>
              <view class="student-home__countdown-btn" @click="go(routes.myReservations)">查看预约</view>
            </view>
          </view>
        </view>

        <view class="student-home__section-head">
          <view class="student-home__section-title">推荐设施</view>
          <view class="student-home__section-link" @click="go(routes.labs)">查看所有实验室</view>
        </view>

        <view class="student-home__lab-grid">
          <view
            v-for="lab in featuredLabs"
            :key="lab.id"
            class="student-home__lab-card"
          >
            <view class="student-home__lab-cover" :style="{ background: lab.cover }">
              <image
                v-if="lab.coverImage"
                class="student-home__lab-cover-img"
                :src="lab.coverImage"
                mode="aspectFill"
              />
              <view class="student-home__lab-cover-mask"></view>
              <view class="student-home__lab-status" :class="lab.statusClass">
                <view class="student-home__lab-status-dot"></view>
                <text>{{ lab.statusText }}</text>
              </view>
            </view>

            <view class="student-home__lab-body">
              <view class="student-home__lab-name">{{ lab.lab_name }}</view>
              <view class="student-home__lab-location">
                {{ lab.campus_name || '校区待补充' }} · {{ lab.location || '位置待补充' }}
              </view>

              <view class="student-home__lab-tools">
                <view class="student-home__lab-tool">{{ lab.typeText }}</view>
                <view class="student-home__lab-tool">容量 {{ lab.capacity || 0 }}</view>
                <view class="student-home__lab-tool">{{ lab.openText }}</view>
              </view>

              <view class="student-home__lab-actions">
                <view class="student-home__lab-btn light" @click="goLabDetail(lab.id)">查看详情</view>
                <view
                  class="student-home__lab-btn primary"
                  :class="{ disabled: lab.status !== 'active' }"
                  @click="goReserveFromHome(lab)"
                >
                  {{ lab.status === 'active' ? '立即预约' : '暂不可约' }}
                </view>
              </view>
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
import UserTopNav from '../../components/user-top-nav.vue'
import { api } from '../../api/index'
import { requireLogin } from '../../common/guard'
import { openPage } from '../../common/router'
import { getProfile } from '../../common/session'
import { routes } from '../../config/navigation'

const LAB_COVERS = [
  'linear-gradient(135deg, #0c284e 0%, #1b4f82 55%, #48b7f4 100%)',
  'linear-gradient(135deg, #1a2744 0%, #3e6f8f 52%, #d3ecff 100%)',
  'linear-gradient(135deg, #214235 0%, #3f7f68 48%, #b8e9d2 100%)',
  'linear-gradient(135deg, #32231f 0%, #725043 50%, #f3d2b1 100%)'
]

export default {
  components: { SiteFooter, StudentTopNav, UserTopNav },
  data() {
    return {
      routes,
      profile: {},
      featuredLabs: [],
      reservations: []
    }
  },
  computed: {
    displayName() {
      return this.profile.real_name || this.profile.username || '同学'
    },
    currentDateText() {
      const now = new Date()
      return `${now.getMonth() + 1}/${now.getDate()}`
    },
    timeText() {
      const now = new Date()
      return `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`
    },
    quickCards() {
      if (this.profile.role === 'teacher') {
        return [
          { title: '校区资源', path: routes.campuses, icon: '校' },
          { title: '实验室列表', path: routes.labs, icon: '实' },
          { title: '教学预约', path: routes.reserve, icon: '约' },
          { title: '我的预约', path: routes.myReservations, icon: '单' }
        ]
      }
      return [
        { title: '校区资源', path: routes.campuses, icon: '校' },
        { title: '实验室列表', path: routes.labs, icon: '实' },
        { title: '我的预约', path: routes.myReservations, icon: '单' },
        { title: 'AI 助手', path: routes.agent, icon: 'AI' }
      ]
    },
    roleFocusText() {
      return this.profile.role === 'teacher' ? '教学预约优先通道' : '校园活跃中'
    },
    upcomingReservation() {
      const sorted = [...this.reservations].sort((a, b) => {
        const left = `${a.reservation_date || ''} ${a.start_time || ''}`
        const right = `${b.reservation_date || ''} ${b.start_time || ''}`
        return left.localeCompare(right)
      })
      return sorted.find((item) => item.status === 'approved') || sorted[0] || {}
    },
    upcomingMeta() {
      const item = this.upcomingReservation
      if (!item.lab_name) return '去实验室列表看看今天有哪些空闲资源。'
      return `${item.campus_name || '校区待定'} · ${item.purpose || '用途待补充'}`
    },
    countdownText() {
      const item = this.upcomingReservation
      if (!item.reservation_date || !item.start_time) return '--'
      const target = new Date(`${item.reservation_date}T${item.start_time}`)
      const diff = Math.max(0, target.getTime() - Date.now())
      const totalMinutes = Math.floor(diff / 60000)
      const hours = Math.floor(totalMinutes / 60)
      const minutes = totalMinutes % 60
      return `${hours}h ${minutes}m`
    }
  },
  async onShow() {
    if (!requireLogin()) return
    // #ifdef H5
    uni.hideTabBar()
    // #endif
    this.profile = getProfile()
    await this.loadData()
  },
  methods: {
    go(path) {
      openPage(path)
    },
    goLabDetail(id) {
      openPage(routes.labDetail, { query: { id } })
    },
    goReserveFromHome(lab) {
      if (!lab || lab.status !== 'active') return
      openPage(routes.reserve, { query: { labId: lab.id, campusId: lab.campus_id } })
    },
    resolveType(item) {
      const text = `${item.lab_name || ''} ${item.description || ''}`.toLowerCase()
      if (text.includes('生物') || text.includes('基因') || text.includes('医学')) return '生物'
      if (text.includes('化学') || text.includes('合成')) return '化学'
      if (text.includes('物理') || text.includes('光学') || text.includes('材料')) return '物理'
      if (text.includes('ai') || text.includes('机器') || text.includes('智能')) return '人工智能'
      return '综合'
    },
    async loadData() {
      try {
        const [labsRes, reservationsRes] = await Promise.all([
          api.labs({ page: 1, page_size: 6 }),
          api.myReservations()
        ])

        const labs = labsRes?.list || labsRes?.data || (Array.isArray(labsRes) ? labsRes : [])
        this.featuredLabs = labs.slice(0, 3).map((lab, index) => ({
          ...lab,
          cover: LAB_COVERS[index % LAB_COVERS.length],
          coverImage: Array.isArray(lab.photos) && lab.photos.length ? lab.photos[0] : '',
          typeText: this.resolveType(lab),
          openText: `${(lab.open_time || '00:00').slice(0, 5)} - ${(lab.close_time || '00:00').slice(0, 5)}`,
          statusText: lab.status === 'active' ? (index === 1 ? '紧张' : '空闲') : '停用',
          statusClass: lab.status === 'active' ? (index === 1 ? 'demand' : 'active') : 'disabled'
        }))

        const reservations =
          reservationsRes?.list || reservationsRes?.data || (Array.isArray(reservationsRes) ? reservationsRes : [])
        this.reservations = reservations.slice(0, 5)
      } catch (error) {
        this.featuredLabs = []
        this.reservations = []
      }
    }
  }
}
</script>

<style lang="scss">
.student-home {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background:
    radial-gradient(circle at top right, rgba(65, 190, 253, 0.14), transparent 26%),
    linear-gradient(180deg, #f7f9fc 0%, #eef2f7 100%);
}

.student-home__nav {
  position: sticky;
  top: 0;
  z-index: 50;
  padding: 0;
  background: rgba(247, 249, 252, 0.72);
  backdrop-filter: blur(18px);
  border-bottom: 1rpx solid rgba(197, 198, 207, 0.22);
  box-shadow: 0 12rpx 30rpx rgba(8, 27, 58, 0.05);
}

.student-home__nav-inner {
  width: 100%;
  min-height: 108rpx;
  margin: 0;
  padding: 0 40rpx;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 32rpx;
  box-sizing: border-box;
}

.student-home__nav-main {
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 56rpx;
  flex: 1;
}

.student-home__brand {
  display: flex;
  align-items: center;
  gap: 18rpx;
}

.student-home__brand-mark {
  width: 78rpx;
  height: 78rpx;
  border-radius: 24rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #031635, #1a2b4b);
  color: #41befd;
  font-size: 30rpx;
  font-weight: 800;
}

.student-home__brand-text {
  font-size: 30rpx;
  font-weight: 800;
  letter-spacing: -0.5rpx;
  color: #1a2b4b;
   margin-left: 30rpx;  /* 鍙宠竟璺?80rpx */
   margin-right: 80rpx;  /* 鍙宠竟璺?80rpx */
}

.student-home__nav-links {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: 40rpx;
  min-width: 0;
  flex-wrap: nowrap;
}

.student-home__nav-link {
  padding: 8rpx 4rpx;
  border-bottom: 4rpx solid transparent;
  color: #6f7b8c;
  font-size: 24rpx;
  font-weight: 600;
  letter-spacing: 1rpx;
  transition: color 180ms ease;
}

.student-home__nav-link.active {
  color: #1a2b4b;
  border-color: #41befd;
}

.student-home__nav-actions {
  display: flex;
  align-items: center;
  gap: 18rpx;
  justify-self: end;
}


.student-home__profile {
  display: flex;
  align-items: center;
  gap: 14rpx;
  padding-left: 22rpx;
  border-left: 1rpx solid rgba(117, 119, 127, 0.18);
}

.student-home__avatar {
  width: 66rpx;
  height: 66rpx;
  border-radius: 999rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #1a2b4b, #7ecfff);
  color: #ffffff;
  font-size: 26rpx;
  font-weight: 700;
}

.student-home__profile-text {
  font-size: 22rpx;
  font-weight: 600;
  color: #031635;
}

.student-home__body {
  flex: 1;
  padding: 36rpx 0 88rpx;
}

.student-home__shell {
  width: 100%;
  padding: 0 32rpx;
  box-sizing: border-box;
}

.student-home__welcome {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 24rpx;
  margin-bottom: 42rpx;
}

.student-home__welcome-title {
  font-size: 58rpx;
  line-height: 1.08;
  font-weight: 800;
  color: #031635;
}

.student-home__welcome-sub {
  margin-top: 12rpx;
  font-size: 24rpx;
  color: #5d6879;
  font-weight: 500;
}

.student-home__welcome-highlight {
  margin-left: 10rpx;
  color: #00658d;
  font-weight: 700;
}

.student-home__welcome-badges {
  display: flex;
  gap: 16rpx;
}

.student-home__metric-badge {
  display: flex;
  align-items: center;
  gap: 10rpx;
  padding: 18rpx 24rpx;
  border-radius: 24rpx;
  background: rgba(255, 255, 255, 0.72);
  border: 1rpx solid rgba(197, 198, 207, 0.16);
  backdrop-filter: blur(18px);
  color: #031635;
  font-size: 24rpx;
  font-weight: 700;
}

.student-home__metric-icon {
  color: #00658d;
}

.student-home__hero-grid {
  display: grid;
  grid-template-columns: minmax(0, 2.2fr) minmax(420rpx, 1fr);
  gap: 24rpx;
  margin-bottom: 56rpx;
}

.student-home__quick-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 18rpx;
}

.student-home__quick-card {
  min-height: 186rpx;
  padding: 28rpx;
  border-radius: 28rpx;
  background: #ffffff;
  box-shadow: 0 18rpx 36rpx rgba(8, 27, 58, 0.05);
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 22rpx;
  transition: all 180ms cubic-bezier(0.16, 1, 0.3, 1);
}

.student-home__quick-card:hover {
  transform: translateY(-4rpx);
  background: #031635;
}

.student-home__quick-card:hover .student-home__quick-title {
  color: #ffffff;
}

.student-home__quick-card:hover .student-home__quick-icon {
  background: #1a2b4b;
  color: #41befd;
}

.student-home__quick-icon {
  width: 92rpx;
  height: 92rpx;
  border-radius: 24rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #e7ebf0;
  color: #031635;
  font-size: 28rpx;
  font-weight: 800;
}

.student-home__quick-title {
  font-size: 30rpx;
  line-height: 1.2;
  color: #031635;
  font-weight: 800;
}

.student-home__countdown {
  position: relative;
  overflow: hidden;
  min-height: 390rpx;
  padding: 32rpx;
  border-radius: 28rpx;
  background: linear-gradient(180deg, #031635 0%, #1a2b4b 100%);
  color: #ffffff;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.student-home__countdown-orb {
  position: absolute;
  top: -80rpx;
  right: -76rpx;
  width: 230rpx;
  height: 230rpx;
  border-radius: 999rpx;
  background: rgba(65, 190, 253, 0.18);
  filter: blur(28rpx);
}

.student-home__countdown-top,
.student-home__countdown-bottom {
  position: relative;
  z-index: 1;
}

.student-home__countdown-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.student-home__eyebrow {
  font-size: 20rpx;
  letter-spacing: 4rpx;
  color: #41befd;
  font-weight: 800;
}

.student-home__bell {
  color: #41befd;
  font-size: 20rpx;
  font-weight: 700;
}

.student-home__countdown-name {
  position: relative;
  z-index: 1;
  margin-top: 66rpx;
  font-size: 38rpx;
  line-height: 1.2;
  font-weight: 800;
}

.student-home__countdown-meta {
  position: relative;
  z-index: 1;
  margin-top: 10rpx;
  color: rgba(182, 198, 239, 0.88);
  font-size: 22rpx;
  line-height: 1.5;
}

.student-home__countdown-bottom {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20rpx;
}

.student-home__countdown-label {
  font-size: 20rpx;
  color: rgba(182, 198, 239, 0.84);
}

.student-home__countdown-value {
  margin-top: 8rpx;
  font-size: 42rpx;
  font-weight: 800;
}

.student-home__countdown-btn {
  padding: 18rpx 28rpx;
  border-radius: 20rpx;
  background: #41befd;
  color: #031635;
  font-size: 24rpx;
  font-weight: 800;
  white-space: nowrap;
}

.student-home__section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20rpx;
  margin-bottom: 28rpx;
}

.student-home__section-title {
  font-size: 38rpx;
  font-weight: 800;
  color: #031635;
}

.student-home__section-link {
  color: #00658d;
  font-size: 24rpx;
  font-weight: 800;
}

.student-home__lab-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 24rpx;
}

.student-home__lab-card {
  overflow: hidden;
  border-radius: 26rpx;
  background: #ffffff;
  box-shadow: 0 16rpx 34rpx rgba(8, 27, 58, 0.06);
}

.student-home__lab-cover {
  position: relative;
  height: 340rpx;
  overflow: hidden;
}

.student-home__lab-cover-img {
  width: 100%;
  height: 100%;
  display: block;
}

.student-home__lab-cover-mask {
  position: absolute;
  inset: 0;
  background: linear-gradient(180deg, rgba(7, 22, 43, 0.16) 0%, rgba(7, 22, 43, 0.06) 100%);
}

.student-home__lab-status {
  position: absolute;
  top: 16rpx;
  left: 16rpx;
  display: flex;
  align-items: center;
  gap: 8rpx;
  padding: 8rpx 14rpx;
  border-radius: 999rpx;
  background: rgba(255, 255, 255, 0.88);
  color: #0b2652;
  font-size: 18rpx;
  font-weight: 800;
}

.student-home__lab-status-dot {
  width: 12rpx;
  height: 12rpx;
  border-radius: 999rpx;
  background: #27ae60;
}

.student-home__lab-status.demand .student-home__lab-status-dot {
  background: #f2994a;
}

.student-home__lab-status.disabled .student-home__lab-status-dot {
  background: #ba1a1a;
}

.student-home__lab-body {
  padding: 24rpx;
}

.student-home__lab-name {
  color: #031635;
  font-size: 38rpx;
  line-height: 1.2;
  font-weight: 800;
}

.student-home__lab-location {
  margin-top: 8rpx;
  color: #65768c;
  font-size: 23rpx;
}

.student-home__lab-tools {
  margin-top: 14rpx;
  display: flex;
  gap: 10rpx;
  flex-wrap: wrap;
}

.student-home__lab-tool {
  min-height: 38rpx;
  border-radius: 12rpx;
  padding: 0 12rpx;
  background: #eef2f7;
  color: #39506d;
  font-size: 20rpx;
  display: inline-flex;
  align-items: center;
}

.student-home__lab-actions {
  margin-top: 18rpx;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12rpx;
}

.student-home__lab-btn {
  height: 70rpx;
  border-radius: 16rpx;
  font-size: 24rpx;
  font-weight: 800;
  display: flex;
  align-items: center;
  justify-content: center;
}

.student-home__lab-btn.light {
  background: #ffffff;
  border: 2rpx solid #0b2652;
  color: #0b2652;
}

.student-home__lab-btn.primary {
  background: #041c42;
  color: #ecf4ff;
}

.student-home__lab-btn.primary.disabled {
  background: #cfd6df;
  color: #5d6c80;
}

.student-home__lab-btn:active {
  transform: scale(0.98);
}

.student-home__lab-location,
.student-home__lab-name,
.student-home__lab-tools,
.student-home__lab-actions {
  position: relative;
}

.student-home__lab-location {
  font-size: 20rpx;
  color: #65768c;
}

.student-home__timeline-card {
  margin-top: 60rpx;
  padding: 34rpx;
  border-radius: 30rpx;
  background: #f2f4f7;
  border: 1rpx solid rgba(197, 198, 207, 0.16);
}

.student-home__timeline-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20rpx;
  margin-bottom: 34rpx;
}

.student-home__timeline-sub {
  margin-top: 10rpx;
  color: #75777f;
  font-size: 20rpx;
}

.student-home__timeline-tabs {
  display: flex;
  align-items: center;
  gap: 10rpx;
}

.student-home__timeline-tab {
  padding: 14rpx 24rpx;
  border-radius: 16rpx;
  color: #6a7483;
  font-size: 22rpx;
  font-weight: 800;
}

.student-home__timeline-tab.active {
  background: #ffffff;
  border: 1rpx solid rgba(197, 198, 207, 0.24);
  color: #031635;
}

.student-home__timeline-list {
  display: grid;
  gap: 24rpx;
}

.student-home__timeline-row {
  display: grid;
  grid-template-columns: 180rpx 1fr 120rpx;
  gap: 20rpx;
  align-items: center;
}

.student-home__timeline-name {
  color: #031635;
  font-size: 22rpx;
  font-weight: 800;
}

.student-home__timeline-track {
  position: relative;
  height: 34rpx;
}

.student-home__timeline-base {
  position: absolute;
  inset: 0;
  border-radius: 999rpx;
  background: #ffffff;
}

.student-home__timeline-segment {
  position: absolute;
  top: 0;
  height: 100%;
  border-radius: 999rpx;
}

.student-home__timeline-now {
  position: absolute;
  left: 36%;
  top: -8rpx;
  width: 3rpx;
  height: 50rpx;
  background: #00658d;
}

.student-home__timeline-state {
  text-align: right;
  font-size: 20rpx;
  font-weight: 800;
}

.student-home__timeline-state.busy {
  color: #031635;
}

.student-home__timeline-state.open {
  color: #27ae60;
}

.student-home__timeline-state.partial {
  color: #1a2b4b;
}

.student-home__footer {
  padding: 48rpx 32rpx 12rpx;
}

.student-home__footer-inner {
  width: 100%;
  margin: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 28rpx;
  padding: 32rpx;
  border-radius: 28rpx;
  background: #ffffff;
  border: 1rpx solid rgba(228, 235, 245, 0.92);
  box-shadow: 0 12rpx 36rpx rgba(47, 128, 237, 0.06);
}

.student-home__footer-title {
  color: #1a2b4b;
  font-size: 30rpx;
  font-weight: 800;
}

.student-home__footer-sub {
  margin-top: 10rpx;
  color: #7a8796;
  font-size: 22rpx;
}

.student-home__footer-links {
  display: flex;
  align-items: center;
  gap: 18rpx;
  flex-wrap: wrap;
}

.student-home__footer-link {
  color: #00658d;
  font-size: 24rpx;
  font-weight: 700;
}

/* #ifndef H5 */
.student-home__hero-grid,
.student-home__lab-grid,
.student-home__footer-inner {
  grid-template-columns: 1fr;
  flex-direction: column;
}

.student-home__body {
  padding-top: 24rpx;
}

.student-home__shell,
.student-home__footer {
  padding-left: 24rpx;
  padding-right: 24rpx;
}

.student-home__welcome,
.student-home__timeline-head {
  flex-direction: column;
  align-items: flex-start;
}

.student-home__quick-grid,
.student-home__lab-grid {
  grid-template-columns: 1fr;
}

.student-home__timeline-row {
  grid-template-columns: 1fr;
}

.student-home__timeline-state {
  text-align: left;
}
/* #endif */

/* #ifdef H5 */
@media screen and (min-width: 1500px) {
  .student-home__nav-inner {
    padding-left: 56rpx;
    padding-right: 56rpx;
  }

  .student-home__shell,
  .student-home__footer {
    padding-left: 56rpx;
    padding-right: 56rpx;
  }

  .student-home__hero-grid {
    grid-template-columns: minmax(0, 2.4fr) minmax(460rpx, 1fr);
  }

  .student-home__quick-grid {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }

  .student-home__lab-grid {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }
}

@media screen and (max-width: 1180px) {
  .student-home__hero-grid {
    grid-template-columns: 1fr;
  }

  .student-home__lab-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .student-home__footer-inner {
    flex-direction: column;
    align-items: flex-start;
  }
}

@media screen and (max-width: 860px) {
  .student-home__nav-links,
  .student-home__profile-text {
    display: none;
  }

  .student-home__nav-main {
    gap: 20rpx;
  }

  .student-home__welcome,
  .student-home__timeline-head {
    flex-direction: column;
    align-items: flex-start;
  }

  .student-home__quick-grid,
  .student-home__lab-grid {
    grid-template-columns: 1fr;
  }

  .student-home__timeline-row {
    grid-template-columns: 1fr;
  }

  .student-home__timeline-state {
    text-align: left;
  }
}
/* #endif */
</style>


