<template>
  <admin-layout title="预约审批" subtitle="使用表格查看待审批预约，并在右侧抽屉完成审批" active="approvals">
    <view class="admin-panel-grid">
      <view v-for="item in summaryCards" :key="item.label" class="card">
        <view class="subtitle">{{ item.label }}</view>
        <view class="title">{{ item.value }}</view>
      </view>
    </view>

    <view class="card admin-toolbar">
      <input v-model="keyword" class="input" style="flex:1;" placeholder="搜索实验室、申请人或用途" />
      <view class="pill">待审批 {{ filteredList.length }} 条</view>
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
        <text>{{ item.lab_name }}</text>
        <text>{{ item.user_name }}</text>
        <text>{{ item.reservation_date || '--' }}</text>
        <text>{{ item.start_time.slice(0, 5) }} - {{ item.end_time.slice(0, 5) }}</text>
        <text>{{ item.purpose }}</text>
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
        <view class="field"><text class="label">预约时间</text><view class="input">{{ activeItem.start_time }} - {{ activeItem.end_time }}</view></view>
        <view class="field"><text class="label">用途</text><view class="input">{{ activeItem.purpose }}</view></view>
        <view class="field">
          <text class="label">审批备注</text>
          <textarea v-model="remark" class="input textarea" placeholder="请输入审批意见" />
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
import AdminLayout from '../../components/admin-layout.vue'

export default {
  components: { AdminLayout },
  data() {
    return {
      list: [],
      keyword: '',
      drawerVisible: false,
      activeItem: {},
      remark: ''
    }
  },
  computed: {
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
.approval-table-grid {
  grid-template-columns: 1fr 0.9fr 0.9fr 1fr 1.5fr 0.8fr;
}
</style>
