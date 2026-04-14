<template>
  <admin-layout title="控制台首页" subtitle="查看核心统计、待办审批、资源分布与高频操作" active="dashboard">

    <!-- Metric Cards -->
    <view class="admin-dashboard-grid">
      <view v-for="item in cards" :key="item.label" class="card admin-metric-card" :style="{ '--accent': item.accent }">
        <view class="admin-metric-card__accent"></view>
        <view class="admin-metric-card__body">
          <view class="admin-metric-card__label">{{ item.label }}</view>
          <view class="admin-metric-card__value">{{ item.value }}</view>
          <view class="admin-metric-card__tip">{{ item.tip }}</view>
        </view>
        <view class="admin-metric-card__badge" :style="{ background: item.badgeBg, color: item.accent }">
          {{ item.badge }}
        </view>
      </view>
    </view>

    <!-- Charts Row -->
    <view class="admin-dashboard-panels">
      <bar-chart-card title="校区预约统计" subtitle="按校区查看预约活跃度" :data="campusChart" />

      <!-- Lab Utilization -->
      <view class="card">
        <view class="title">实验室使用率</view>
        <view class="subtitle" style="margin-bottom:24rpx;">各实验室当前开放与使用情况</view>
        <view v-if="!usageStats.length" class="empty-state">暂无使用率数据。</view>
        <view v-for="item in usageStats" :key="item.lab_name" class="usage-item">
          <view class="usage-item__head">
            <view class="usage-item__name">{{ item.lab_name }}</view>
            <view class="usage-item__pct">{{ item.pct }}%</view>
          </view>
          <view class="usage-bar">
            <view class="usage-bar__fill" :style="{ width: item.pct + '%', background: item.color }"></view>
          </view>
        </view>
      </view>
    </view>

    <!-- Bottom Row -->
    <view class="admin-dashboard-panels">
      <!-- Recent Activity -->
      <view class="card">
        <view class="title">最近审批动态</view>
        <view v-if="!recentActivities.length" class="empty-state">当前暂无审批动态。</view>
        <view v-for="item in recentActivities" :key="item.title" class="admin-activity-item">
          <view class="admin-activity-item__dot" :class="'activity-dot-' + item.type"></view>
          <view style="flex:1;min-width:0;">
            <view class="admin-activity-item__title">{{ item.title }}</view>
            <view class="admin-activity-item__sub">{{ item.sub }}</view>
          </view>
          <view class="pill">{{ item.time }}</view>
        </view>
      </view>

      <!-- Right: shortcuts + tips -->
      <view>
        <!-- Quick Entries -->
        <view class="card" style="margin-bottom:24rpx;">
          <view class="title" style="margin-bottom:20rpx;">快捷入口</view>
          <view class="admin-shortcut-grid">
            <view
              v-for="item in shortcuts"
              :key="item.path"
              class="admin-shortcut-card"
              :style="{ '--sc': item.color }"
              @click="go(item.path)"
            >
              <view class="admin-shortcut-card__icon">{{ item.icon }}</view>
              <view class="admin-shortcut-card__title">{{ item.title }}</view>
            </view>
          </view>
        </view>

        <!-- Tips -->
        <view class="card">
          <view class="title" style="margin-bottom:16rpx;">管理视角提示</view>
          <view class="admin-tip-list">
            <view class="admin-tip-item">优先处理待审批预约，减少用户等待时间。</view>
            <view class="admin-tip-item">关注实验室使用率高的校区，及时调配资源。</view>
            <view class="admin-tip-item">定期检查设备状态与停用实验室，保证预约质量。</view>
          </view>
        </view>
      </view>
    </view>

  </admin-layout>
</template>

<script>
import { api } from '../../api/index'
import { requireLogin } from '../../common/guard'
import { openPage } from '../../common/router'
import AdminLayout from '../../components/admin-layout.vue'
import BarChartCard from '../../components/bar-chart-card.vue'

const USAGE_COLORS = ['#2F80ED', '#27AE60', '#F2994A', '#9B51E0', '#EB5757', '#56CCF2']

export default {
  components: { AdminLayout, BarChartCard },
  data() {
    return {
      overview: {},
      campusStats: [],
      usageData: []
    }
  },
  computed: {
    cards() {
      return [
        {
          label: '校区数量',
          value: this.overview.campus_count || 0,
          tip: '跨校区资源协作',
          accent: '#2F80ED',
          badgeBg: '#EEF5FF',
          badge: '校区'
        },
        {
          label: '实验室总数',
          value: this.overview.lab_count || 0,
          tip: '覆盖全部校区',
          accent: '#27AE60',
          badgeBg: '#EDFAF3',
          badge: '实验室'
        },
        {
          label: '预约总数',
          value: this.overview.reservation_count || 0,
          tip: '累计预约记录',
          accent: '#F2994A',
          badgeBg: '#FFF5EC',
          badge: '预约'
        },
        {
          label: '待审批数量',
          value: this.overview.pending_count || 0,
          tip: '建议优先处理',
          accent: '#EB5757',
          badgeBg: '#FDECEC',
          badge: '待办'
        }
      ]
    },
    campusChart() {
      return this.campusStats.map((item) => ({ label: item.campus_name, value: item.reservation_count }))
    },
    usageStats() {
      const source = this.usageData.length ? this.usageData : this.campusStats
      const max = Math.max(...source.map((i) => Number(i.reservation_count || i.usage_count || 0)), 1)
      return source.slice(0, 5).map((item, i) => ({
        lab_name: item.lab_name || item.campus_name || `实验室 ${i + 1}`,
        pct: Math.round(((Number(item.reservation_count || item.usage_count || 0)) / max) * 100),
        color: USAGE_COLORS[i % USAGE_COLORS.length]
      }))
    },
    shortcuts() {
      return [
        { title: '预约审批', path: '/pages/admin-approvals/index', icon: '审批', color: '#2F80ED' },
        { title: '实验室管理', path: '/pages/admin-labs/index', icon: '实验室', color: '#27AE60' },
        { title: '设备管理', path: '/pages/admin-equipment/index', icon: '设备', color: '#F2994A' },
        { title: '统计分析', path: '/pages/statistics/index', icon: '统计', color: '#9B51E0' }
      ]
    },
    recentActivities() {
      return this.campusStats.slice(0, 4).map((item, index) => ({
        title: `${item.campus_name} 有 ${item.reservation_count} 条预约记录`,
        sub: index === 0 ? '当前最活跃校区，建议优先关注资源负载。' : '可继续查看实验室使用情况与审批进度。',
        time: `${index + 1} 分钟前`,
        type: index === 0 ? 'hot' : 'normal'
      }))
    }
  },
  async onShow() {
    if (!requireLogin()) return
    const [overview, campusStats, usageData] = await Promise.all([
      api.statisticsOverview(),
      api.statisticsCampus(),
      api.statisticsUsage().catch(() => [])
    ])
    this.overview = overview
    this.campusStats = campusStats
    this.usageData = Array.isArray(usageData) ? usageData : []
  },
  methods: {
    go(path) {
      openPage(path, { replace: true })
    }
  }
}
</script>

<style lang="scss">
/* Metric cards */
.admin-dashboard-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 20rpx;
  margin-bottom: 24rpx;
}

.admin-metric-card {
  position: relative;
  display: flex;
  align-items: center;
  gap: 20rpx;
  overflow: hidden;
  margin-bottom: 0;
}

.admin-metric-card__accent {
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 8rpx;
  background: var(--accent, #2F80ED);
  border-radius: 24rpx 0 0 24rpx;
}

.admin-metric-card__body {
  flex: 1;
  min-width: 0;
  padding-left: 8rpx;
}

.admin-metric-card__label {
  font-size: 24rpx;
  color: #7A8796;
}

.admin-metric-card__value {
  font-size: 52rpx;
  font-weight: 700;
  color: #1F2D3D;
  line-height: 1.2;
  margin-top: 6rpx;
}

.admin-metric-card__tip {
  margin-top: 8rpx;
  font-size: 22rpx;
  color: #9AA0A6;
}

.admin-metric-card__badge {
  padding: 10rpx 16rpx;
  border-radius: 14rpx;
  font-size: 22rpx;
  font-weight: 600;
  flex-shrink: 0;
}

/* Charts row */
.admin-dashboard-panels {
  display: grid;
  grid-template-columns: 1.2fr 0.8fr;
  gap: 24rpx;
  margin-bottom: 24rpx;
}

/* Usage bars */
.usage-item {
  margin-bottom: 20rpx;
}

.usage-item:last-child {
  margin-bottom: 0;
}

.usage-item__head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10rpx;
}

.usage-item__name {
  font-size: 26rpx;
  font-weight: 600;
  color: #1F2D3D;
}

.usage-item__pct {
  font-size: 24rpx;
  font-weight: 700;
  color: #5B6B7F;
}

.usage-bar {
  height: 14rpx;
  border-radius: 999rpx;
  background: #EEF3FB;
  overflow: hidden;
}

.usage-bar__fill {
  height: 100%;
  border-radius: 999rpx;
  transition: width 600ms cubic-bezier(0.16, 1, 0.3, 1);
}

/* Activity list */
.admin-activity-item {
  display: flex;
  align-items: center;
  gap: 16rpx;
  padding: 18rpx 0;
  border-bottom: 1rpx solid #EEF3FB;
}

.admin-activity-item:last-child {
  border-bottom: none;
  padding-bottom: 0;
}

.admin-activity-item__dot {
  width: 16rpx;
  height: 16rpx;
  border-radius: 50%;
  flex-shrink: 0;
  background: #C5D3E8;
}

.activity-dot-hot { background: #EB5757; }
.activity-dot-normal { background: #2F80ED; }

.admin-activity-item__title {
  font-size: 26rpx;
  font-weight: 600;
  color: #1F2D3D;
}

.admin-activity-item__sub {
  margin-top: 6rpx;
  font-size: 22rpx;
  color: #7A8796;
  line-height: 1.6;
}

/* Shortcut cards */
.admin-shortcut-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16rpx;
}

.admin-shortcut-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12rpx;
  padding: 24rpx 16rpx;
  border-radius: 20rpx;
  background: #F8FBFF;
  border: 1rpx solid #E8F0FC;
  cursor: pointer;
  transition: all 180ms cubic-bezier(0.16, 1, 0.3, 1);
}

.admin-shortcut-card:hover {
  background: #EEF5FF;
  border-color: var(--sc, #2F80ED);
  transform: translateY(-2rpx);
}

.admin-shortcut-card__icon {
  width: 72rpx;
  height: 72rpx;
  border-radius: 20rpx;
  background: var(--sc, #2F80ED);
  color: #fff;
  font-size: 18rpx;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
  line-height: 1.3;
}

.admin-shortcut-card__title {
  font-size: 26rpx;
  font-weight: 600;
  color: #1F2D3D;
}

/* Tips */
.admin-tip-list {
  display: grid;
  gap: 14rpx;
}

.admin-tip-item {
  padding: 18rpx 20rpx;
  border-radius: 18rpx;
  background: #F8FBFF;
  border: 1rpx solid #E8F0FC;
  font-size: 24rpx;
  color: #41556F;
  line-height: 1.7;
}
</style>
