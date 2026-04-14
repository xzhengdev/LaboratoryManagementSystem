<template>
  <view>
    <user-top-nav active="home" />
    <view class="page">
      <view class="page-shell">

        <!-- Hero -->
        <page-hero
          :kicker="greetingKicker"
          :title="`${greeting}，${profile.real_name || '同学'}`"
          :subtitle="`${roleText} · ${profile.campus_name || '全校区'} · 分布式实验室预约管理系统`"
        >
          <template #actions>
            <view class="btn btn-light" @click="go(routes.labs)">立即预约</view>
            <view class="btn btn-light" @click="go(routes.agent)">智能助手</view>
            <view v-if="isAdmin" class="btn btn-light" @click="go(routes.adminDashboard)">进入管理端</view>
          </template>
        </page-hero>

        <!-- Quick Entries H5 -->
        <!-- #ifdef H5 -->
        <view class="home-quick-grid">
          <view
            v-for="item in quickEntries"
            :key="item.path"
            class="card home-quick-card"
            @click="go(item.path)"
          >
            <view class="home-quick-icon" :style="{ background: item.iconBg }">
              <view class="home-quick-icon__text">{{ item.iconText }}</view>
            </view>
            <view class="home-quick-card__body">
              <view class="home-quick-card__title">{{ item.title }}</view>
              <view class="subtitle">{{ item.desc }}</view>
            </view>
            <view class="home-quick-card__arrow">›</view>
          </view>
        </view>

        <!-- Main content -->
        <view class="home-content-grid">
          <!-- Recommended Labs -->
          <view class="card home-section">
            <view class="home-section__head">
              <view>
                <view class="portal-panel__kicker">推荐实验室</view>
                <view class="title" style="margin-top:14rpx;">热门开放实验室</view>
              </view>
              <view class="btn btn-light home-section__more" @click="go(routes.labs)">查看全部</view>
            </view>
            <view v-if="!featuredLabs.length" class="empty-state">暂无推荐实验室。</view>
            <view
              v-for="lab in featuredLabs"
              :key="lab.id"
              class="home-lab-item"
              @click="goLabDetail(lab.id)"
            >
              <view class="home-lab-item__accent" :style="{ background: lab.accentColor }"></view>
              <view class="home-lab-item__body">
                <view class="home-lab-item__name">{{ lab.name }}</view>
                <view class="home-lab-item__meta">{{ lab.campus_name || '未知校区' }} · 容量 {{ lab.capacity || '-' }} 人</view>
              </view>
              <status-tag :status="lab.status === 'active' ? 'active' : 'disabled'" />
            </view>
          </view>

          <!-- Right column -->
          <view>
            <!-- Recent Reservations -->
            <view class="card home-section">
              <view class="home-section__head">
                <view>
                  <view class="portal-panel__kicker">最近预约</view>
                  <view class="title" style="margin-top:14rpx;">我的预约记录</view>
                </view>
                <view class="btn btn-light home-section__more" @click="go(routes.myReservations)">全部记录</view>
              </view>
              <view v-if="!recentReservations.length" class="empty-state">暂无预约记录，快去预约吧。</view>
              <view v-for="item in recentReservations" :key="item.id" class="home-reservation-item">
                <view class="home-reservation-item__dot" :class="'dot-' + item.status"></view>
                <view class="home-reservation-item__body">
                  <view class="home-reservation-item__name">{{ item.lab_name }}</view>
                  <view class="home-reservation-item__time">{{ item.date }} {{ item.time_slot }}</view>
                </view>
                <status-tag :status="item.status" />
              </view>
            </view>

            <!-- Quick Booking Banner -->
            <view class="card home-booking-banner" @click="go(routes.labs)">
              <view>
                <view class="home-booking-banner__title">快速预约</view>
                <view class="home-booking-banner__sub">选择实验室，提交申请，等待审批</view>
              </view>
              <view class="home-booking-banner__btn">开始 →</view>
            </view>
          </view>
        </view>
        <!-- #endif -->

        <!-- Non-H5 quick entries -->
        <!-- #ifndef H5 -->
        <view class="grid">
          <view v-for="item in menus" :key="item.path" class="card quick-card" @click="go(item.path)">
            <view class="title quick-title">{{ item.title }}</view>
            <view class="subtitle">{{ item.desc }}</view>
          </view>
        </view>
        <!-- #endif -->

      </view>
      <agent-chat-window />
      <portal-footer />
    </view>
  </view>
</template>

<script>
import AgentChatWindow from '../../components/agent-chat-window.vue'
import PageHero from '../../components/page-hero.vue'
import PortalFooter from '../../components/portal-footer.vue'
import UserTopNav from '../../components/user-top-nav.vue'
import StatusTag from '../../components/status-tag.vue'
import { getProfile, isAdminRole } from '../../common/session'
import { requireLogin } from '../../common/guard'
import { openPage } from '../../common/router'
import { getRoleText, routes, userQuickEntries } from '../../config/navigation'
import { api } from '../../api/index'

const ACCENT_COLORS = ['#2F80ED', '#27AE60', '#F2994A', '#9B51E0', '#EB5757', '#56CCF2']

export default {
  components: { AgentChatWindow, PageHero, PortalFooter, UserTopNav, StatusTag },
  data() {
    return {
      profile: {},
      routes,
      featuredLabs: [],
      recentReservations: []
    }
  },
  computed: {
    greeting() {
      const h = new Date().getHours()
      if (h < 12) return '早上好'
      if (h < 18) return '下午好'
      return '晚上好'
    },
    greetingKicker() {
      const h = new Date().getHours()
      if (h < 12) return '上午好，欢迎回来'
      if (h < 18) return '下午好，欢迎回来'
      return '晚上好，欢迎回来'
    },
    roleText() {
      return getRoleText(this.profile.role)
    },
    isAdmin() {
      return isAdminRole(this.profile.role)
    },
    menus() {
      return userQuickEntries
    },
    quickEntries() {
      return [
        { title: '校区资源', desc: '查看各校区实验室分布', path: routes.campuses, iconText: '校区', iconBg: 'linear-gradient(135deg,#2F80ED,#62A2F8)' },
        { title: '实验室列表', desc: '按条件快速检索实验室', path: routes.labs, iconText: '实验室', iconBg: 'linear-gradient(135deg,#27AE60,#6FCF97)' },
        { title: '我的预约', desc: '查看待审批与已通过记录', path: routes.myReservations, iconText: '预约', iconBg: 'linear-gradient(135deg,#F2994A,#F2C94C)' },
        { title: '智能助手', desc: '智能问答与预约引导', path: routes.agent, iconText: 'AI', iconBg: 'linear-gradient(135deg,#9B51E0,#BB6BD9)' }
      ]
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
    async loadData() {
      try {
        const [labsRes, reservationsRes] = await Promise.all([
          api.labs({ page: 1, page_size: 4 }),
          api.myReservations()
        ])
        const labs = labsRes?.list || labsRes?.data || (Array.isArray(labsRes) ? labsRes : [])
        this.featuredLabs = labs.slice(0, 4).map((lab, i) => ({
          ...lab,
          accentColor: ACCENT_COLORS[i % ACCENT_COLORS.length]
        }))
        const reservations = reservationsRes?.list || reservationsRes?.data || (Array.isArray(reservationsRes) ? reservationsRes : [])
        this.recentReservations = reservations.slice(0, 3)
      } catch (e) {
        // graceful degradation
      }
    }
  }
}
</script>

<style lang="scss">
.quick-card {
  transition: transform 180ms cubic-bezier(0.16, 1, 0.3, 1);
}

.quick-title {
  font-size: 30rpx;
}

/* #ifdef H5 */
.home-quick-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 20rpx;
  margin-bottom: 24rpx;
}

.home-quick-card {
  display: flex;
  align-items: center;
  gap: 20rpx;
  cursor: pointer;
  transition: transform 180ms cubic-bezier(0.16, 1, 0.3, 1), box-shadow 180ms;
  margin-bottom: 0;
}

.home-quick-card:hover {
  transform: translateY(-4rpx);
  box-shadow: 0 20rpx 40rpx rgba(47, 128, 237, 0.14);
}

.home-quick-icon {
  width: 80rpx;
  height: 80rpx;
  border-radius: 22rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.home-quick-icon__text {
  color: #fff;
  font-size: 18rpx;
  font-weight: 700;
  text-align: center;
  line-height: 1.3;
}

.home-quick-card__body {
  flex: 1;
  min-width: 0;
}

.home-quick-card__title {
  font-size: 28rpx;
  font-weight: 700;
  color: #1F2D3D;
}

.home-quick-card__arrow {
  font-size: 40rpx;
  color: #C5D3E8;
  line-height: 1;
}

.home-content-grid {
  display: grid;
  grid-template-columns: 1.4fr 1fr;
  gap: 24rpx;
}

.home-section__head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24rpx;
}

.home-section__more {
  padding: 12rpx 20rpx !important;
  font-size: 24rpx !important;
}

.home-lab-item {
  display: flex;
  align-items: center;
  gap: 16rpx;
  padding: 18rpx 0;
  border-bottom: 1rpx solid #EEF3FB;
  cursor: pointer;
}

.home-lab-item:last-child {
  border-bottom: none;
  padding-bottom: 0;
}

.home-lab-item__accent {
  width: 8rpx;
  height: 48rpx;
  border-radius: 999rpx;
  flex-shrink: 0;
}

.home-lab-item__body {
  flex: 1;
  min-width: 0;
}

.home-lab-item__name {
  font-size: 28rpx;
  font-weight: 600;
  color: #1F2D3D;
}

.home-lab-item__meta {
  margin-top: 6rpx;
  font-size: 22rpx;
  color: #7A8796;
}

.home-reservation-item {
  display: flex;
  align-items: center;
  gap: 16rpx;
  padding: 18rpx 0;
  border-bottom: 1rpx solid #EEF3FB;
}

.home-reservation-item:last-child {
  border-bottom: none;
  padding-bottom: 0;
}

.home-reservation-item__dot {
  width: 16rpx;
  height: 16rpx;
  border-radius: 50%;
  flex-shrink: 0;
  background: #C5D3E8;
}

.dot-pending { background: #F2994A; }
.dot-approved { background: #27AE60; }
.dot-rejected { background: #EB5757; }
.dot-cancelled { background: #9AA0A6; }

.home-reservation-item__body {
  flex: 1;
  min-width: 0;
}

.home-reservation-item__name {
  font-size: 28rpx;
  font-weight: 600;
  color: #1F2D3D;
}

.home-reservation-item__time {
  margin-top: 6rpx;
  font-size: 22rpx;
  color: #7A8796;
}

.home-booking-banner {
  background: linear-gradient(135deg, #1A2B45, #2F4A6D);
  border: none;
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: pointer;
  transition: opacity 180ms;
}

.home-booking-banner:hover {
  opacity: 0.92;
}

.home-booking-banner__title {
  font-size: 32rpx;
  font-weight: 700;
  color: #fff;
}

.home-booking-banner__sub {
  margin-top: 8rpx;
  font-size: 22rpx;
  color: rgba(255, 255, 255, 0.65);
}

.home-booking-banner__btn {
  padding: 18rpx 28rpx;
  border-radius: 999rpx;
  background: rgba(255, 255, 255, 0.12);
  color: #fff;
  font-size: 26rpx;
  border: 1rpx solid rgba(255, 255, 255, 0.22);
  white-space: nowrap;
  flex-shrink: 0;
}

@media screen and (max-width: 959px) {
  .home-quick-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .home-content-grid {
    grid-template-columns: 1fr;
  }
}
/* #endif */
</style>
