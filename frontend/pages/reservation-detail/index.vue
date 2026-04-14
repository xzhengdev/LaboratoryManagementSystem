<template>
  <view>
    <user-top-nav active="reservations" />
    <view class="page">
      <view class="page-shell two-col">
        <view>
          <page-hero
            kicker="预约详情"
            :title="detail.lab_name || '预约详情'"
            :subtitle="`${detail.campus_name || '未分配校区'} · ${detail.user_name || '当前用户'}`"
          />

          <view class="card">
            <view class="table-row detail-grid">
              <text>预约日期</text>
              <text>{{ detail.reservation_date }}</text>
            </view>
            <view class="table-row detail-grid">
              <text>预约时间</text>
              <text>{{ detail.start_time && detail.start_time.slice(0, 5) }} - {{ detail.end_time && detail.end_time.slice(0, 5) }}</text>
            </view>
            <view class="table-row detail-grid">
              <text>参与人数</text>
              <text>{{ detail.participant_count }}</text>
            </view>
            <view class="table-row detail-grid">
              <text>用途说明</text>
              <text>{{ detail.purpose }}</text>
            </view>
          </view>
        </view>

        <view class="card">
          <view class="actions">
            <view class="title">审批记录</view>
            <status-tag v-if="detail.status" :status="detail.status" />
          </view>
          <view v-if="!(detail.approvals || []).length" class="empty-state">当前还没有审批记录，请耐心等待管理员处理。</view>
          <view v-for="item in detail.approvals || []" :key="item.id" class="table-row approval-grid">
            <status-tag :status="item.approval_status" />
            <text>{{ item.approval_time && item.approval_time.slice(0, 16).replace('T', ' ') }}</text>
            <text>{{ item.remark || '无备注' }}</text>
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
import PageHero from '../../components/page-hero.vue'
import PortalFooter from '../../components/portal-footer.vue'
import StatusTag from '../../components/status-tag.vue'
import UserTopNav from '../../components/user-top-nav.vue'

export default {
  components: { PageHero, PortalFooter, StatusTag, UserTopNav },
  data() {
    return {
      id: '',
      detail: {}
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
    this.detail = await api.reservationDetail(this.id)
  }
}
</script>

<style lang="scss">
.detail-grid {
  grid-template-columns: 1fr 2fr;
}

.approval-grid {
  grid-template-columns: 1fr 1fr 2fr;
}
</style>
