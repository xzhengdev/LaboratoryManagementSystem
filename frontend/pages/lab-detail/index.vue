<template>
  <view>
    <user-top-nav active="labs" />
    <view class="page">
      <view class="page-shell two-col">
        <view>
          <page-hero
            kicker="实验室详情"
            :title="detail.lab_name || '实验室详情'"
            :subtitle="`${detail.campus_name || '未分配校区'} · ${detail.location || '未填写位置'}`"
          />

          <view class="card">
            <view class="subtitle">{{ detail.description || '暂无实验室介绍' }}</view>
            <view class="grid" style="margin-top: 24rpx;">
              <view class="card">
                <view class="label">容纳人数</view>
                <view class="title">{{ detail.capacity || 0 }}</view>
              </view>
              <view class="card">
                <view class="label">开放时间</view>
                <view class="title">{{ timeRange }}</view>
              </view>
            </view>
          </view>

          <view class="card">
            <view class="title">设备清单</view>
            <view v-if="!(detail.equipment || []).length" class="empty-state">当前暂无设备信息</view>
            <view v-for="item in detail.equipment || []" :key="item.id" class="table-row" style="grid-template-columns: 2fr 1fr 1fr;">
              <text>{{ item.equipment_name }}</text>
              <text>{{ item.quantity }}</text>
              <status-tag :status="item.status === 'active' ? 'active' : 'disabled'" />
            </view>
          </view>
        </view>

        <view>
          <view class="card portal-schedule-card">
            <view class="title">可预约时间段</view>
            <view class="subtitle">{{ selectedDate }}</view>
            <picker mode="date" :value="selectedDate" @change="changeDate">
              <view class="input" style="margin-top: 16rpx;">{{ selectedDate }}</view>
            </picker>
            <view v-if="!schedule.reservations || !schedule.reservations.length" class="empty-state">当天暂无已占用时段，可直接发起预约。</view>
            <view v-for="item in schedule.reservations || []" :key="item.id" class="table-row" style="grid-template-columns: 1.3fr 1fr 1.7fr;">
              <text>{{ item.start_time.slice(0, 5) }} - {{ item.end_time.slice(0, 5) }}</text>
              <status-tag :status="item.status" />
              <text>{{ item.purpose }}</text>
            </view>
            <view class="actions" style="margin-top: 20rpx;">
              <view class="btn" @click="goReserve">提交预约</view>
            </view>
          </view>
        </view>
      </view>

      <portal-footer />
    </view>
  </view>
</template>

<script>
import { api } from '../../api/index'
import { requireLogin } from '../../common/guard'
import { openPage } from '../../common/router'
import { routes } from '../../config/navigation'
import PageHero from '../../components/page-hero.vue'
import PortalFooter from '../../components/portal-footer.vue'
import StatusTag from '../../components/status-tag.vue'
import UserTopNav from '../../components/user-top-nav.vue'

function todayString() {
  const date = new Date()
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
}

export default {
  components: { PageHero, PortalFooter, StatusTag, UserTopNav },
  data() {
    return {
      id: '',
      detail: {},
      schedule: {},
      selectedDate: todayString()
    }
  },
  computed: {
    timeRange() {
      if (!this.detail.open_time) return '--'
      return `${this.detail.open_time.slice(0, 5)} - ${this.detail.close_time.slice(0, 5)}`
    }
  },
  onLoad(options) {
    this.id = options.id
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
      this.detail = await api.labDetail(this.id)
      this.schedule = await api.labSchedule(this.id, this.selectedDate)
    },
    async changeDate(event) {
      this.selectedDate = event.detail.value
      this.schedule = await api.labSchedule(this.id, this.selectedDate)
    },
    goReserve() {
      openPage(routes.reserve, { query: { labId: this.id, campusId: this.detail.campus_id, date: this.selectedDate } })
    }
  }
}
</script>
