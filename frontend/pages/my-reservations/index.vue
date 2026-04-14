<template>
  <view>
    <user-top-nav active="reservations" />
    <view class="page">
      <view class="page-shell">
        <page-hero
          kicker="预约管理"
          title="我的预约"
          subtitle="支持按状态筛选，PC 端可更高效地查看审批结果与预约明细"
        />

        <view class="card portal-toolbar-card">
          <view class="actions">
            <view
              v-for="item in statusFilters"
              :key="item.value"
              class="pill"
              :style="activeStatus === item.value ? 'background:#2F80ED;color:#fff;' : ''"
              @click="activeStatus = item.value"
            >
              {{ item.label }}
            </view>
          </view>
          <view class="pill">共 {{ filteredList.length }} 条</view>
        </view>

        <view v-if="!filteredList.length" class="card empty-state">当前状态下没有预约记录，去实验室列表发起一条预约吧。</view>

        <view class="grid">
          <view v-for="item in filteredList" :key="item.id" class="card">
            <view class="actions">
              <view class="title">{{ item.lab_name }}</view>
              <status-tag :status="item.status" />
            </view>
            <view class="subtitle">{{ item.reservation_date }} {{ item.start_time.slice(0, 5) }} - {{ item.end_time.slice(0, 5) }}</view>
            <view class="subtitle">{{ item.purpose }}</view>
            <view class="actions" style="margin-top:20rpx;">
              <view class="btn btn-light" @click="goDetail(item.id)">查看详情</view>
              <view v-if="['pending','approved'].includes(item.status)" class="btn btn-danger" @click="cancel(item.id)">取消预约</view>
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

export default {
  components: { PageHero, PortalFooter, StatusTag, UserTopNav },
  data() {
    return {
      list: [],
      activeStatus: ''
    }
  },
  computed: {
    statusFilters() {
      return [
        { label: '全部', value: '' },
        { label: '待审批', value: 'pending' },
        { label: '已通过', value: 'approved' },
        { label: '已拒绝', value: 'rejected' },
        { label: '已取消', value: 'cancelled' }
      ]
    },
    filteredList() {
      if (!this.activeStatus) return this.list
      return this.list.filter((item) => item.status === this.activeStatus)
    }
  },
  async onShow() {
    if (!requireLogin()) return
    // #ifdef H5
    uni.hideTabBar()
    // #endif
    this.list = await api.myReservations()
  },
  methods: {
    goDetail(id) {
      openPage(routes.reservationDetail, { query: { id } })
    },
    async cancel(id) {
      await api.cancelReservation(id)
      uni.showToast({ title: '已取消预约', icon: 'success' })
      this.list = await api.myReservations()
    }
  }
}
</script>

<style lang="scss">
/* #ifdef H5 */
.portal-toolbar-card {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 20rpx;
}
/* #endif */
</style>
