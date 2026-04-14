<template>
  <view class="page">
    <view class="page-shell two-col">
      <view class="card hero-card">
        <view class="hero-kicker">可预约时段</view>
        <view class="title">{{ schedule.lab && schedule.lab.lab_name }}</view>
        <view class="subtitle light-text">查看当日排期，快速判断可预约时间段</view>
      </view>

      <view class="card">
        <view class="field">
          <text class="label">预约日期</text>
          <picker mode="date" :value="date" @change="changeDate">
            <view class="input">{{ date }}</view>
          </picker>
        </view>
        <view class="subtitle">开放时间：{{ schedule.open_time }} - {{ schedule.close_time }}</view>
        <view v-if="!(schedule.reservations || []).length" class="empty-state">当天暂无预约，可直接发起新的预约申请。</view>
        <view v-for="item in schedule.reservations || []" :key="item.id" class="table-row" style="grid-template-columns: 1.2fr 1fr 1.6fr;">
          <text>{{ item.start_time.slice(0, 5) }} - {{ item.end_time.slice(0, 5) }}</text>
          <status-tag :status="item.status" />
          <text>{{ item.purpose }}</text>
        </view>
        <view class="actions" style="margin-top:20rpx;">
          <view class="btn" @click="goReserve">前往预约</view>
        </view>
      </view>
    </view>
  </view>
</template>

<script>
import { api } from '../../api/index'
import { requireLogin } from '../../common/guard'
import StatusTag from '../../components/status-tag.vue'

function todayString() {
  const now = new Date()
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`
}

export default {
  components: { StatusTag },
  data() {
    return {
      // 该页专注“查看排期”，便于详情页之外的独立演示。
      labId: '',
      date: todayString(),
      schedule: {}
    }
  },
  onLoad(options) {
    this.labId = options.labId
    this.date = options.date || todayString()
  },
  async onShow() {
    if (!requireLogin()) return
    await this.loadData()
  },
  methods: {
    async loadData() {
      this.schedule = await api.labSchedule(this.labId, this.date)
    },
    async changeDate(event) {
      // 日期变化后立即重新请求当天排期。
      this.date = event.detail.value
      await this.loadData()
    },
    goReserve() {
      const campusId = this.schedule.lab ? this.schedule.lab.campus_id : ''
      uni.navigateTo({ url: `/pages/reserve/index?labId=${this.labId}&campusId=${campusId}&date=${this.date}` })
    }
  }
}
</script>
