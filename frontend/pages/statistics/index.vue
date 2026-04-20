<template>
  <admin-layout :title="pageTitle" :subtitle="pageSubtitle" active="statistics">
    <view class="admin-kpi-grid">
      <view class="admin-kpi-card" v-for="item in overviewCards" :key="item.label">
        <view class="admin-kpi-card__label">{{ item.label }}</view>
        <view class="admin-kpi-card__value">{{ item.value }}</view>
      </view>
    </view>

    <view v-if="isSystemView" class="admin-panels-grid">
      <bar-chart-card title="校区预约统计" subtitle="按校区展示预约总量" :data="campusChart" />
      <bar-chart-card title="实验室使用率" subtitle="按实验室展示已通过预约量" :data="labChart" />
    </view>

    <view v-else class="admin-panels-grid">
      <bar-chart-card title="本校区实验室预约量" subtitle="按实验室展示预约总量" :data="localReservationChart" />
      <bar-chart-card title="本校区实验室通过量" subtitle="按实验室展示已通过预约量" :data="localApprovedChart" />
    </view>

    <view class="admin-panels-grid">
      <view class="card">
        <view class="title">{{ rankingTitle }}</view>
        <view v-for="(item, index) in rankingList" :key="item.lab_name" class="ranking-item">
          <view class="ranking-item__left">
            <view class="ranking-item__index">{{ index + 1 }}</view>
            <view>
              <view class="ranking-item__title">{{ item.lab_name }}</view>
              <view class="ranking-item__sub">已通过预约 {{ item.approved_count }} 次 / 总预约 {{ item.reservation_count }} 次</view>
            </view>
          </view>
          <view class="pill">{{ pillText(item) }}</view>
        </view>
      </view>

      <view class="card">
        <view class="title">分析说明</view>
        <view class="admin-tip-list">
          <view class="admin-tip-item">{{ tipList[0] }}</view>
          <view class="admin-tip-item">{{ tipList[1] }}</view>
          <view class="admin-tip-item">{{ tipList[2] }}</view>
        </view>
      </view>
    </view>
  </admin-layout>
</template>

<script>
import { api } from '../../api/index'
import { requireLogin } from '../../common/guard'
import { getProfile } from '../../common/session'
import { canViewStatistics, isSystemAdmin } from '../../config/navigation'
import AdminLayout from '../../components/admin-layout.vue'
import BarChartCard from '../../components/bar-chart-card.vue'

export default {
  components: { AdminLayout, BarChartCard },
  data() {
    return {
      profile: {},
      overview: {},
      campusStats: [],
      usageStats: []
    }
  },
  computed: {
    isSystemView() {
      return isSystemAdmin(this.profile.role)
    },
    pageTitle() {
      return this.isSystemView ? '全局统计分析' : '本校区统计分析'
    },
    pageSubtitle() {
      return this.isSystemView ? '查看跨校区资源使用趋势' : '查看本校区资源使用趋势'
    },
    overviewCards() {
      if (!this.isSystemView) {
        const campusName = this.campusStats.length ? this.campusStats[0].campus_name : '--'
        return [
          { label: '当前校区', value: campusName },
          { label: '实验室数', value: this.overview.lab_count || 0 },
          { label: '预约总数', value: this.overview.reservation_count || 0 },
          { label: '待审批', value: this.overview.pending_count || 0 }
        ]
      }

      return [
        { label: '校区数', value: this.overview.campus_count || 0 },
        { label: '实验室数', value: this.overview.lab_count || 0 },
        { label: '预约总数', value: this.overview.reservation_count || 0 },
        { label: '待审批', value: this.overview.pending_count || 0 }
      ]
    },
    campusChart() {
      return this.campusStats.map((item) => ({ label: item.campus_name, value: item.reservation_count }))
    },
    sortedUsageStats() {
      return [...this.usageStats].sort((a, b) => {
        const reservationDiff = (Number(b.reservation_count) || 0) - (Number(a.reservation_count) || 0)
        if (reservationDiff !== 0) return reservationDiff
        const approvedDiff = (Number(b.approved_count) || 0) - (Number(a.approved_count) || 0)
        if (approvedDiff !== 0) return approvedDiff
        return (Number(a.lab_id) || 0) - (Number(b.lab_id) || 0)
      })
    },
    labChart() {
      return this.sortedUsageStats.slice(0, 6).map((item) => ({ label: item.lab_name, value: item.approved_count }))
    },
    localReservationChart() {
      return this.sortedUsageStats.slice(0, 6).map((item) => ({ label: item.lab_name, value: item.reservation_count || 0 }))
    },
    localApprovedChart() {
      return this.sortedUsageStats.slice(0, 6).map((item) => ({ label: item.lab_name, value: item.approved_count || 0 }))
    },
    rankingTitle() {
      return this.isSystemView ? '热门实验室排行（全校）' : '热门实验室排行（本校区）'
    },
    rankingList() {
      return this.sortedUsageStats.slice(0, 5)
    },
    campusNameMap() {
      const map = {}
      this.campusStats.forEach((item) => {
        map[String(item.campus_id)] = item.campus_name
      })
      return map
    },
    tipList() {
      if (this.isSystemView) {
        return [
          '校区预约量可反映不同校区资源活跃度。',
          '实验室使用率可辅助调整开放时段。',
          '热门实验室排行可用于设备投入与扩容决策。'
        ]
      }

      return [
        '本校区实验室预约总量可反映近期教学/科研负载。',
        '通过量与待审批量可辅助安排管理员排班。',
        '高负载实验室可优先延长开放时段或增加设备。'
      ]
    }
  },
  async onShow() {
    if (!requireLogin()) return
    this.profile = getProfile()
    if (!canViewStatistics(this.profile.role)) return

    this.overview = await api.statisticsOverview()
    this.campusStats = await api.statisticsCampus()
    this.usageStats = await api.statisticsUsage()
  },
  methods: {
    pillText(item) {
      const campusName = this.campusStats.length ? this.campusStats[0].campus_name : '当前校区'
      if (!this.isSystemView) return campusName
      const key = String(item.campus_id || '')
      return this.campusNameMap[key] || item.campus_name || '未分配校区'
    }
  }
}
</script>

<style lang="scss">
.admin-kpi-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16rpx;
  margin-bottom: 18rpx;
}

.admin-kpi-card {
  border-radius: 20rpx;
  border: 1rpx solid #dbe4f1;
  background: #fff;
  padding: 18rpx 20rpx;
}

.admin-kpi-card__label {
  color: #6d7f95;
  font-size: 22rpx;
}

.admin-kpi-card__value {
  margin-top: 8rpx;
  font-size: 52rpx;
  font-weight: 800;
  color: #132d4d;
}

.admin-panels-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16rpx;
  margin-bottom: 18rpx;
}

.ranking-item + .ranking-item {
  margin-top: 14rpx;
}

.ranking-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 20rpx;
  padding: 18rpx 0;
  border-bottom: 1rpx solid #eef3fb;
}

.ranking-item__left {
  display: flex;
  align-items: center;
  gap: 16rpx;
}

.ranking-item__index {
  width: 44rpx;
  height: 44rpx;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #eef5ff;
  color: #2f80ed;
  font-size: 22rpx;
  font-weight: 700;
}

.ranking-item__title {
  font-size: 26rpx;
  font-weight: 700;
  color: #1f2d3d;
}

.ranking-item__sub {
  margin-top: 6rpx;
  font-size: 22rpx;
  color: #7a8796;
}

.admin-tip-list {
  margin-top: 16rpx;
  display: grid;
  gap: 12rpx;
}

.admin-tip-item {
  padding: 16rpx 18rpx;
  border-radius: 14rpx;
  background: #f3f7fd;
  color: #4f6178;
  font-size: 23rpx;
}

@media screen and (max-width: 1200px) {
  .admin-kpi-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .admin-panels-grid {
    grid-template-columns: 1fr;
  }
}

@media screen and (max-width: 768px) {
  .admin-kpi-grid {
    grid-template-columns: 1fr;
    gap: 12rpx;
    margin-bottom: 14rpx;
  }

  .admin-kpi-card {
    padding: 16rpx 18rpx;
  }

  .admin-kpi-card__label {
    font-size: 21rpx;
  }

  .admin-kpi-card__value {
    font-size: 42rpx;
  }

  .admin-panels-grid {
    gap: 12rpx;
    margin-bottom: 14rpx;
  }

  .ranking-item {
    flex-direction: column;
    align-items: flex-start;
    gap: 10rpx;
    padding: 14rpx 0;
  }

  .ranking-item__left {
    width: 100%;
    align-items: flex-start;
  }

  .ranking-item__title {
    font-size: 24rpx;
    line-height: 1.45;
    word-break: break-all;
  }

  .ranking-item__sub {
    font-size: 21rpx;
    line-height: 1.5;
  }

  .ranking-item .pill {
    align-self: flex-start;
    max-width: 100%;
    white-space: normal;
    line-height: 1.4;
  }

  .admin-tip-list {
    gap: 10rpx;
    margin-top: 12rpx;
  }

  .admin-tip-item {
    padding: 14rpx 14rpx;
    font-size: 22rpx;
    line-height: 1.55;
  }
}
</style>
