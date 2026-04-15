<template>
  <admin-layout :title="pageTitle" :subtitle="pageSubtitle" active="approvals">
    <view class="admin-kpi-grid">
      <view v-for="item in summaryCards" :key="item.label" class="admin-kpi-card">
        <view class="admin-kpi-card__label">{{ item.label }}</view>
        <view class="admin-kpi-card__value">{{ item.value }}</view>
      </view>
    </view>

    <view class="card admin-toolbar-lite">
      <input v-model="keyword" class="input admin-toolbar-lite__search" style="flex: 1;" placeholder="搜索实验室、申请人或用途" />
      <view class="admin-toolbar-lite__meta">{{ filteredList.length }} 条待处理</view>
    </view>

    <view class="card table-card">
      <view class="table-header approval-table-grid">
        <text>实验室</text>
        <text>申请人</text>
        <text>预约日期</text>
        <text>预约时间</text>
        <text>用途</text>
        <text>操作</text>
      </view>
      <view v-for="item in filteredList" :key="item.id" class="table-row approval-table-grid">
        <text class="table-strong">{{ item.lab_name }}</text>
        <text>{{ item.user_name }}</text>
        <text>{{ item.reservation_date || '--' }}</text>
        <text>{{ item.start_time.slice(0, 5) }} - {{ item.end_time.slice(0, 5) }}</text>
        <text class="cell-purpose">{{ item.purpose }}</text>
        <view class="actions">
          <view class="pill" @click="openDrawer(item)">查看详情</view>
        </view>
      </view>
      <view v-if="!filteredList.length" class="empty-state">当前没有待审批预约。</view>
    </view>

    <view v-if="drawerVisible" class="admin-drawer-mask" @click="drawerVisible = false">
      <view class="admin-drawer" @click.stop>
        <view class="title">{{ activeItem.lab_name }}</view>
        <view class="subtitle">{{ activeItem.user_name }} · {{ activeItem.reservation_date || '--' }}</view>
        <view class="field">
          <text class="label">预约时间</text>
          <view class="input">{{ activeItem.start_time }} - {{ activeItem.end_time }}</view>
        </view>
        <view class="field">
          <text class="label">用途</text>
          <view class="input">{{ activeItem.purpose }}</view>
        </view>
        <view class="field">
          <text class="label">审批备注</text>
          <textarea v-model="remark" class="input textarea approval-remark-input" placeholder="请输入审批意见" />
        </view>
        <view class="field">
          <text class="label">处理记录</text>
          <view class="approval-record">
            <view class="approval-record__item">
              <text class="approval-record__key">当前状态</text>
              <text class="approval-record__value approval-record__value--pending">待审批</text>
            </view>
            <view class="approval-record__item">
              <text class="approval-record__key">上次处理人</text>
              <text class="approval-record__value">{{ activeItem.approver_name || '暂无' }}</text>
            </view>
            <view class="approval-record__item">
              <text class="approval-record__key">上次处理时间</text>
              <text class="approval-record__value">{{ activeItem.approval_time || '暂无' }}</text>
            </view>
            <view class="approval-record__item">
              <text class="approval-record__key">历史备注</text>
              <text class="approval-record__value">{{ activeItem.remark || '暂无' }}</text>
            </view>
          </view>
        </view>
        <view class="actions">
          <view class="btn" @click="submit(activeItem.id, 'approved')">审批通过</view>
          <view class="btn btn-danger" @click="submit(activeItem.id, 'rejected')">驳回申请</view>
        </view>
      </view>
    </view>
  </admin-layout>
</template>

<script>
import { api } from '../../api/index'
import { requireLogin } from '../../common/guard'
import { getProfile } from '../../common/session'
import { canApproveReservations, isSystemAdmin } from '../../config/navigation'
import AdminLayout from '../../components/admin-layout.vue'

export default {
  components: { AdminLayout },
  data() {
    return {
      profile: {},
      list: [],
      keyword: '',
      drawerVisible: false,
      activeItem: {},
      remark: ''
    }
  },
  computed: {
    pageTitle() {
      return isSystemAdmin(this.profile.role) ? '全校预约审批' : '本校区预约审批'
    },
    pageSubtitle() {
      return isSystemAdmin(this.profile.role)
        ? '集中处理所有校区预约申请'
        : '仅处理当前校区的预约申请'
    },
    filteredList() {
      const text = this.keyword.trim().toLowerCase()
      if (!text) return this.list
      return this.list.filter((item) => `${item.lab_name}${item.user_name}${item.purpose}`.toLowerCase().includes(text))
    },
    summaryCards() {
      const reservationUsers = new Set(this.list.map((item) => item.user_name)).size
      return [
        { label: '待审批预约', value: this.list.length },
        { label: '涉及实验室', value: new Set(this.list.map((item) => item.lab_name)).size },
        { label: '申请人数', value: reservationUsers }
      ]
    }
  },
  async onShow() {
    if (!requireLogin()) return
    this.profile = getProfile()
    if (!canApproveReservations(this.profile.role)) return
    await this.loadData()
  },
  methods: {
    async loadData() {
      this.list = await api.pendingApprovals()
    },
    openDrawer(item) {
      this.activeItem = item
      this.remark = ''
      this.drawerVisible = true
    },
    async submit(id, approvalStatus) {
      await api.approvalAction(id, {
        approval_status: approvalStatus,
        remark: this.remark || (approvalStatus === 'approved' ? '审批通过' : '审批驳回')
      })
      uni.showToast({ title: '审批完成', icon: 'success' })
      this.drawerVisible = false
      await this.loadData()
    }
  }
}
</script>

<style lang="scss">
page {
  background: #f5f7fa;
}

.admin-workspace {
  background: #f5f7fa !important;
}

.card,
.admin-kpi-card,
.table-card,
.admin-drawer {
  border-radius: 24rpx;
  box-shadow: 0 12rpx 32rpx rgba(16, 42, 73, 0.08);
  transition: all 0.25s ease;
}

.card:hover,
.admin-kpi-card:hover,
.table-card:hover {
  transform: translateY(-4rpx);
  box-shadow: 0 20rpx 48rpx rgba(16, 42, 73, 0.12);
}

.admin-kpi-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 24rpx;
  margin-bottom: 28rpx;
}

.admin-kpi-card {
  border: 1rpx solid #dbe4f1;
  background: #fff;
  padding: 24rpx 28rpx;
}

.admin-kpi-card__label {
  color: #6d7f95;
  font-size: 22rpx;
  font-weight: 600;
}

.admin-kpi-card__value {
  margin-top: 10rpx;
  font-size: 52rpx;
  font-weight: 800;
  color: #132d4d;
  line-height: 1.1;
}

.admin-toolbar-lite {
  margin-bottom: 28rpx;
  display: flex;
  align-items: center;
  gap: 16rpx;
  flex-wrap: nowrap;
  border-radius: 24rpx;
  background: #f0f4fa;
  border: 1rpx solid #dce7f4;
  box-shadow: 0 10rpx 26rpx rgba(16, 42, 73, 0.06);
  transition: all 0.25s ease;
  padding: 24rpx !important;
}

.admin-toolbar-lite:hover {
  transform: translateY(-3rpx);
  box-shadow: 0 18rpx 44rpx rgba(16, 42, 73, 0.1);
}

.admin-toolbar-lite__search {
  flex: 1;
  height: 68rpx;
  padding: 0 24rpx;
  border-radius: 24rpx;
  background-color: #ffffff;
  border: 1rpx solid #e4ebf5;
  font-size: 24rpx;
  color: #132d4d;
  transition: all 0.2s ease;
}

.admin-toolbar-lite__search:focus {
  border-color: #2c7da0;
  background-color: #ffffff;
  outline: none;
  box-shadow: 0 0 0 4rpx rgba(44, 125, 160, 0.1);
}

.admin-toolbar-lite__meta {
  min-width: 190rpx;
  height: 68rpx;
  padding: 0 18rpx;
  border-radius: 24rpx;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: #edf3fb;
  color: #3f5878;
  font-size: 24rpx;
  font-weight: 700;
  transition: all 0.2s ease;
}

.admin-toolbar-lite__meta:hover {
  transform: translateY(-1rpx);
}

.table-card {
  border: 1rpx solid #dbe4f1;
  background: #ffffff;
  overflow: hidden;
}

.approval-table-grid {
  grid-template-columns: 1fr 0.9fr 0.9fr 1fr 1.4fr 0.8fr;
}

.table-header {
  background: #f4f7fb;
  border-bottom: 1rpx solid #e5ecf5;
  color: #6d7f95;
  font-weight: 600;
}

.table-row {
  border-bottom: 1rpx solid #edf2f7;
  padding-top: 28rpx !important;
  padding-bottom: 28rpx !important;
  transition: all 0.2s ease;
}

.table-row:hover {
  background: #f7faff;
}

.table-header.approval-table-grid text:first-child,
.table-row.approval-table-grid text:first-child {
  padding-left: 20rpx;
}

.table-strong {
  color: #0f2744;
  font-weight: 800;
}

.cell-purpose {
  color: #4d6079;
}

.pill {
  border: 1rpx solid #d9e4f2;
  background: #ffffff;
  color: #476183;
  transition: all 0.2s ease;
}

.pill:hover {
  opacity: 0.92;
  transform: translateY(-1rpx);
  background: #f6f9fd;
}

.empty-state {
  color: #6d7f95;
}

.admin-drawer-mask {
  background: rgba(10, 26, 45, 0.4);
  backdrop-filter: blur(4rpx);
}

.admin-drawer {
  background: #ffffff;
  box-shadow: 0 30rpx 80rpx rgba(9, 36, 69, 0.22);
  border-left: 1rpx solid #dbe6f4;
}

.approval-remark-input {
  min-height: 136rpx;
}

.approval-record {
  border-radius: 14rpx;
  border: 1rpx solid #dbe6f4;
  background: #f5f8fd;
  padding: 14rpx 16rpx;
}

.approval-record__item {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12rpx;
  padding: 8rpx 0;
}

.approval-record__item + .approval-record__item {
  border-top: 1rpx solid #e5edf8;
}

.approval-record__key {
  color: #6b7f99;
  font-size: 23rpx;
}

.approval-record__value {
  color: #1f3655;
  font-size: 23rpx;
  text-align: right;
  word-break: break-all;
}

.approval-record__value--pending {
  color: #2c7da0;
  font-weight: 700;
}

.btn {
  transition: all 0.2s ease;
}

.btn:hover {
  opacity: 0.92;
  transform: translateY(-1rpx);
}

@media screen and (max-width: 1200px) {
  .admin-kpi-grid {
    grid-template-columns: 1fr;
  }
}
</style>

