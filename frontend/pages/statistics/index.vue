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

    <view class="admin-kpi-grid daily-kpi-grid">
      <view class="admin-kpi-card" v-for="item in dailyOverviewCards" :key="item.label">
        <view class="admin-kpi-card__label">{{ item.label }}</view>
        <view class="admin-kpi-card__value">{{ item.value }}</view>
      </view>
    </view>

    <view class="admin-panels-grid">
      <bar-chart-card title="日报按校区统计" subtitle="对比各校区日报上报总量" :data="dailyCampusChart" />
      <bar-chart-card title="日报按实验室统计" subtitle="对比实验室日报上报总量" :data="dailyLabChart" />
    </view>

    <view v-if="isSystemView" class="card summary-card">
      <view class="summary-card__head">
        <view>
          <view class="title">中心汇总总表（按日快照）</view>
          <view class="summary-card__sub">快照日期：{{ summaryLatest.snapshot_date || '--' }}</view>
        </view>
        <view class="summary-card__actions">
          <view class="pill" @click="reloadSummary">刷新快照</view>
          <view class="pill" :class="{ disabled: syncingSummary }" @click="syncSummary">
            {{ syncingSummary ? '同步中...' : '立即同步' }}
          </view>
        </view>
      </view>
      <view v-if="!summaryRows.length" class="empty-text">暂无汇总快照，请先点击“立即同步”。</view>
      <view v-else class="summary-table">
        <view class="summary-row summary-row--head">
          <text>校区</text>
          <text>预约</text>
          <text>资产申报</text>
          <text>资产数</text>
          <text>日报</text>
          <text>资产总额</text>
        </view>
        <view class="summary-row" v-for="item in summaryRows" :key="item.id">
          <text>{{ item.campus_name }}</text>
          <text>{{ item.reservation_count || 0 }}</text>
          <text>{{ item.asset_request_count || 0 }}</text>
          <text>{{ item.asset_item_count || 0 }}</text>
          <text>{{ item.daily_report_count || 0 }}</text>
          <text>¥{{ moneyText(item.asset_budget_total_amount) }}</text>
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
      usageStats: [],
      dailyOverview: {},
      dailyCampusStats: [],
      dailyLabStats: [],
      summaryLatest: {},
      syncingSummary: false
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
        { label: '待审批', value: this.overview.pending_count || 0 },
        { label: '总资产额度', value: `¥${this.moneyText(this.summaryLatest?.totals?.asset_budget_total_amount)}` }
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
    },
    dailyOverviewCards() {
      return [
        { label: '日报总数', value: this.dailyOverview.daily_report_count || 0 },
        { label: '待审核日报', value: this.dailyOverview.daily_report_pending_count || 0 },
        { label: '已通过日报', value: this.dailyOverview.daily_report_approved_count || 0 },
        { label: '已驳回日报', value: this.dailyOverview.daily_report_rejected_count || 0 }
      ]
    },
    dailyCampusChart() {
      return this.dailyCampusStats.map((item) => ({
        label: item.campus_name,
        value: item.daily_report_count || 0
      }))
    },
    dailyLabChart() {
      const sorted = [...this.dailyLabStats].sort(
        (a, b) => (Number(b.daily_report_count) || 0) - (Number(a.daily_report_count) || 0)
      )
      return sorted.slice(0, 8).map((item) => ({
        label: item.lab_name,
        value: item.daily_report_count || 0
      }))
    },
    summaryRows() {
      return Array.isArray(this.summaryLatest?.rows) ? this.summaryLatest.rows : []
    }
  },
  async onShow() {
    if (!requireLogin()) return
    this.profile = getProfile()
    if (!canViewStatistics(this.profile.role)) return

    const [
      overview,
      campusStats,
      usageStats,
      dailyOverview,
      dailyCampusStats,
      dailyLabStats
    ] = await Promise.all([
      api.statisticsOverview(),
      api.statisticsCampus(),
      api.statisticsUsage(),
      api.statisticsDailyReportOverview(),
      api.statisticsDailyReportCampus(),
      api.statisticsDailyReportLab()
    ])
    this.overview = overview
    this.campusStats = campusStats
    this.usageStats = usageStats
    this.dailyOverview = dailyOverview
    this.dailyCampusStats = dailyCampusStats
    this.dailyLabStats = dailyLabStats
    if (this.isSystemView) {
      await this.reloadSummary()
    }
  },
  methods: {
    moneyText(value) {
      const num = Number(value || 0)
      if (!Number.isFinite(num)) return '0.00'
      return num.toFixed(2)
    },
    pillText(item) {
      const campusName = this.campusStats.length ? this.campusStats[0].campus_name : '当前校区'
      if (!this.isSystemView) return campusName
      const key = String(item.campus_id || '')
      return this.campusNameMap[key] || item.campus_name || '未分配校区'
    },
    async reloadSummary() {
      this.summaryLatest = await api.latestSummary()
    },
    async syncSummary() {
      if (this.syncingSummary) return
      this.syncingSummary = true
      try {
        await api.syncSummary()
        uni.showToast({ title: '汇总同步完成', icon: 'success' })
        await this.reloadSummary()
      } finally {
        this.syncingSummary = false
      }
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

.daily-kpi-grid {
  margin-top: 6rpx;
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

.summary-card {
  margin-top: 2rpx;
}

.summary-card__head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 14rpx;
}

.summary-card__sub {
  margin-top: 6rpx;
  font-size: 22rpx;
  color: #6c7f96;
}

.summary-card__actions {
  display: flex;
  gap: 10rpx;
}

.summary-card__actions .pill {
  height: 46rpx;
  padding: 0 14rpx;
  border-radius: 12rpx;
  border: 1rpx solid #d9e4f2;
  color: #476183;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: #fff;
}

.pill.disabled {
  opacity: 0.6;
}

.summary-table {
  margin-top: 14rpx;
}

.summary-row {
  display: grid;
  grid-template-columns: 1.2fr .7fr .9fr .8fr .7fr 1fr;
  gap: 10rpx;
  padding: 14rpx 10rpx;
  border-bottom: 1rpx solid #edf3fb;
  color: #223b58;
  font-size: 22rpx;
}

.summary-row--head {
  font-weight: 700;
  color: #5f7390;
  background: #f4f8fd;
  border-radius: 10rpx;
  border-bottom: none;
}

.empty-text {
  margin-top: 12rpx;
  color: #7a8ca3;
  font-size: 22rpx;
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
