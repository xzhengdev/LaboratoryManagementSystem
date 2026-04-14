<template>
  <admin-layout title="统计分析" subtitle="通过图表查看校区预约量、实验室使用率与热门资源排行" active="statistics">
    <view class="admin-panel-grid">
      <view class="card" v-for="item in overviewCards" :key="item.label">
        <view class="subtitle">{{ item.label }}</view>
        <view class="title">{{ item.value }}</view>
      </view>
    </view>

    <view class="admin-dashboard-panels">
      <bar-chart-card title="校区预约统计" subtitle="按校区展示预约总量" :data="campusChart" />
      <bar-chart-card title="实验室使用率" subtitle="按实验室展示已通过预约量" :data="labChart" />
    </view>

    <view class="admin-dashboard-panels">
      <view class="card">
        <view class="title">热门实验室排行</view>
        <view v-for="(item, index) in rankingList" :key="item.lab_name" class="ranking-item">
          <view class="ranking-item__left">
            <view class="ranking-item__index">{{ index + 1 }}</view>
            <view>
              <view class="ranking-item__title">{{ item.lab_name }}</view>
              <view class="ranking-item__sub">已通过预约 {{ item.approved_count }} 次</view>
            </view>
          </view>
          <view class="pill">{{ item.campus_name || '未分配校区' }}</view>
        </view>
      </view>

      <view class="card">
        <view class="title">分析说明</view>
        <view class="admin-tip-list">
          <view class="admin-tip-item">校区预约量可反映不同校区资源活跃度。</view>
          <view class="admin-tip-item">实验室使用率适合辅助管理员做开放时段调整。</view>
          <view class="admin-tip-item">热门实验室排行适合用于设备投入与资源扩容决策。</view>
        </view>
      </view>
    </view>
  </admin-layout>
</template>

<script>
import { api } from '../../api/index'
import { requireLogin } from '../../common/guard'
import AdminLayout from '../../components/admin-layout.vue'
import BarChartCard from '../../components/bar-chart-card.vue'

export default {
  components: { AdminLayout, BarChartCard },
  data() {
    return {
      overview: {},
      campusStats: [],
      usageStats: []
    }
  },
  computed: {
    overviewCards() {
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
    labChart() {
      return this.usageStats.slice(0, 6).map((item) => ({ label: item.lab_name, value: item.approved_count }))
    },
    rankingList() {
      return this.usageStats.slice(0, 5)
    }
  },
  async onShow() {
    if (!requireLogin()) return
    this.overview = await api.statisticsOverview()
    this.campusStats = await api.statisticsCampus()
    this.usageStats = await api.statisticsUsage()
  }
}
</script>

<style lang="scss">
.ranking-item + .ranking-item {
  margin-top: 14rpx;
}

.ranking-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 20rpx;
  padding: 18rpx 0;
  border-bottom: 1rpx solid #EEF3FB;
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
  background: #EEF5FF;
  color: #2F80ED;
  font-size: 22rpx;
  font-weight: 700;
}

.ranking-item__title {
  font-size: 26rpx;
  font-weight: 600;
  color: #1F2D3D;
}

.ranking-item__sub {
  margin-top: 6rpx;
  font-size: 22rpx;
  color: #7A8796;
}
</style>
