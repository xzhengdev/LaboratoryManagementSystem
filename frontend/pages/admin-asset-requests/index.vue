<template>
  <admin-layout title="资产审批" subtitle="处理教师资产申报并执行预算流转" active="assetRequests">
    <view class="admin-kpi-grid">
      <view v-for="item in summaryCards" :key="item.label" class="admin-kpi-card">
        <view class="admin-kpi-card__label">{{ item.label }}</view>
        <view class="admin-kpi-card__value">{{ item.value }}</view>
      </view>
    </view>

    <view class="card toolbar">
      <picker :range="statusOptions" range-key="label" @change="changeStatus">
        <view class="input toolbar-picker">{{ currentStatusText }}</view>
      </picker>
      <input v-model="keyword" class="input toolbar-search" placeholder="搜索申报单号/设备名称/申请人" />
      <view class="toolbar-btn" @click="reloadAll">刷新</view>
    </view>

    <view class="card table-card">
      <view class="table-header req-grid">
        <text>申报单号</text>
        <text>设备信息</text>
        <text>申请人</text>
        <text>金额</text>
        <text>状态</text>
        <text>操作</text>
      </view>

      <view v-if="!filteredList.length" class="empty-text">暂无资产申报记录</view>

      <view v-for="item in filteredList" :key="item.id" class="table-row req-grid">
        <view>
          <view class="mono">{{ item.request_no }}</view>
          <view class="row-sub">{{ timeText(item.created_at) }}</view>
        </view>
        <view>
          <view class="strong">{{ item.asset_name }}</view>
          <view class="row-sub">{{ item.category }} · 数量{{ item.quantity }}</view>
        </view>
        <view>
          <view>{{ item.requester_name || '--' }}</view>
          <view class="row-sub">{{ item.campus_name || '--' }}</view>
        </view>
        <text>{{ moneyText(item.amount) }}</text>
        <text :class="statusClass(item.status)">{{ statusText(item.status) }}</text>
        <view class="actions">
          <view v-if="item.status === 'pending'" class="pill" @click="approve(item, 'approved')">通过</view>
          <view v-if="item.status === 'pending'" class="pill pill-danger" @click="approve(item, 'rejected')">驳回</view>
          <view v-if="item.status === 'approved'" class="pill pill-primary" @click="stockIn(item)">入库</view>
        </view>
      </view>
    </view>

    <view class="card table-card">
      <view class="table-header asset-grid">
        <text>资产编码</text>
        <text>设备名称</text>
        <text>类别</text>
        <text>金额</text>
        <text>状态</text>
        <text>图片</text>
      </view>

      <view v-if="!assetList.length" class="empty-text">暂无已入库资产</view>

      <view v-for="item in assetList" :key="item.id" class="table-row asset-grid">
        <text class="mono">{{ item.asset_code }}</text>
        <text>{{ item.asset_name }}</text>
        <text>{{ item.category }}</text>
        <text>{{ moneyText(item.price) }}</text>
        <text class="status approved">{{ item.status || 'in_use' }}</text>
        <view class="asset-photo-cell">
          <view class="asset-photo-top">
            <text class="photo-count">共 {{ photoList(item).length }} 张</text>
            <view class="pill pill-primary" @click="uploadAssetPhoto(item)">上传图片</view>
          </view>
          <view v-if="photoList(item).length" class="asset-photo-preview">
            <image
              class="asset-photo-thumb"
              :src="photoList(item)[0].url"
              mode="aspectFill"
              @click="previewPhotos(item)"
            />
          </view>
        </view>
      </view>
    </view>
  </admin-layout>
</template>

<script>
import { api } from '../../api/index'
import { requireLogin } from '../../common/guard'
import { getProfile } from '../../common/session'
import { canManageEquipment, routes } from '../../config/navigation'
import { openPage } from '../../common/router'
import AdminLayout from '../../components/admin-layout.vue'

export default {
  components: { AdminLayout },
  data() {
    return {
      profile: {},
      requestList: [],
      assetList: [],
      keyword: '',
      statusOptions: [
        { label: '全部状态', value: '' },
        { label: '待审批', value: 'pending' },
        { label: '已通过', value: 'approved' },
        { label: '已驳回', value: 'rejected' }
      ],
      selectedStatus: ''
    }
  },
  computed: {
    currentStatusText() {
      const current = this.statusOptions.find((item) => item.value === this.selectedStatus)
      return current ? current.label : '全部状态'
    },
    filteredList() {
      const text = this.keyword.trim().toLowerCase()
      return this.requestList.filter((item) => {
        const hitKeyword = !text || `${item.request_no}${item.asset_name}${item.requester_name || ''}`.toLowerCase().includes(text)
        const hitStatus = !this.selectedStatus || item.status === this.selectedStatus
        return hitKeyword && hitStatus
      })
    },
    summaryCards() {
      const pendingCount = this.requestList.filter((item) => item.status === 'pending').length
      const approvedCount = this.requestList.filter((item) => item.status === 'approved').length
      const totalAmount = this.requestList.reduce((sum, item) => sum + Number(item.amount || 0), 0)
      return [
        { label: '待审批', value: String(pendingCount) },
        { label: '已通过', value: String(approvedCount) },
        { label: '申报总额', value: this.moneyText(totalAmount) }
      ]
    }
  },
  async onShow() {
    if (!requireLogin()) return
    this.profile = getProfile()
    if (!canManageEquipment(this.profile.role)) {
      uni.showToast({ title: '当前角色无权限访问', icon: 'none' })
      openPage(routes.home, { replace: true })
      return
    }
    await this.reloadAll()
  },
  methods: {
    moneyText(value) {
      const num = Number(value || 0)
      if (!Number.isFinite(num)) return '¥0.00'
      return `¥${num.toFixed(2)}`
    },
    timeText(value) {
      if (!value) return '--'
      return String(value).replace('T', ' ').slice(0, 19)
    },
    statusText(status) {
      const map = {
        pending: '待审批',
        approved: '已通过',
        rejected: '已驳回'
      }
      return map[status] || status
    },
    statusClass(status) {
      if (status === 'approved') return 'status approved'
      if (status === 'rejected') return 'status rejected'
      return 'status pending'
    },
    photoList(item) {
      return Array.isArray(item?.photos) ? item.photos.filter((row) => row && row.url) : []
    },
    changeStatus(event) {
      this.selectedStatus = this.statusOptions[event.detail.value].value
    },
    async reloadAll() {
      const [requestList, assetList] = await Promise.all([
        api.assetRequests(),
        api.assets()
      ])
      this.requestList = Array.isArray(requestList) ? requestList : []
      this.assetList = Array.isArray(assetList) ? assetList : []
    },
    async approve(item, status) {
      await api.reviewAssetRequest(item.id, {
        approval_status: status,
        remark: status === 'approved' ? '审批通过' : '审批驳回'
      })
      uni.showToast({ title: status === 'approved' ? '已通过' : '已驳回', icon: 'success' })
      await this.reloadAll()
    },
    async stockIn(item) {
      await api.stockInAsset(item.id, {})
      uni.showToast({ title: '资产已入库', icon: 'success' })
      await this.reloadAll()
    },
    previewPhotos(item) {
      const urls = this.photoList(item).map((row) => row.url)
      if (!urls.length) return
      uni.previewImage({ urls, current: urls[0] })
    },
    uploadAssetPhoto(item) {
      uni.chooseImage({
        count: 1,
        sizeType: ['compressed'],
        sourceType: ['album', 'camera'],
        success: async (res) => {
          const filePath = res?.tempFilePaths?.[0]
          if (!filePath) return
          await api.uploadAssetPhoto(item.id, filePath)
          uni.showToast({ title: '上传成功', icon: 'success' })
          await this.reloadAll()
        },
        fail: () => {
          uni.showToast({ title: '未选择图片', icon: 'none' })
        }
      })
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

.admin-kpi-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 24rpx;
  margin-bottom: 28rpx;
}

.admin-kpi-card {
  border-radius: 22rpx;
  border: 1rpx solid #dbe4f1;
  background: #fff;
  padding: 24rpx;
}

.admin-kpi-card__label {
  color: #6d7f95;
  font-size: 22rpx;
  font-weight: 700;
}

.admin-kpi-card__value {
  margin-top: 10rpx;
  font-size: 40rpx;
  font-weight: 800;
  color: #132d4d;
}

.toolbar {
  margin-bottom: 24rpx;
  display: flex;
  align-items: center;
  gap: 14rpx;
}

.toolbar-picker {
  min-width: 220rpx;
}

.toolbar-search {
  flex: 1;
}

.toolbar-btn {
  width: 160rpx;
  height: 64rpx;
  border-radius: 18rpx;
  background: #2c7da0;
  color: #fff;
  font-size: 24rpx;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
}

.table-card {
  border: 1rpx solid #dbe4f1;
  background: #fff;
  border-radius: 22rpx;
  margin-bottom: 24rpx;
}

.req-grid {
  grid-template-columns: 1.6fr 1.3fr 1fr 0.8fr 0.8fr 1.2fr;
}

.asset-grid {
  grid-template-columns: 1.4fr 1fr 0.8fr 0.8fr 0.8fr 1.6fr;
}

.table-header {
  display: grid;
  gap: 10rpx;
  padding: 18rpx 16rpx;
  background: #f4f7fb;
  border-bottom: 1rpx solid #e5ecf5;
  color: #6d7f95;
  font-size: 22rpx;
  font-weight: 700;
}

.table-row {
  display: grid;
  gap: 10rpx;
  align-items: center;
  padding: 20rpx 16rpx;
  border-bottom: 1rpx solid #edf2f7;
  color: #173350;
  font-size: 22rpx;
}

.table-row:last-child {
  border-bottom: none;
}

.row-sub {
  margin-top: 4rpx;
  color: #73869f;
  font-size: 20rpx;
}

.strong {
  font-weight: 800;
  color: #0f2744;
}

.mono {
  font-family: Consolas, monospace;
}

.actions {
  display: flex;
  gap: 8rpx;
  flex-wrap: wrap;
}

.pill {
  padding: 0 14rpx;
  height: 46rpx;
  border-radius: 12rpx;
  border: 1rpx solid #d9e4f2;
  color: #476183;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: #fff;
}

.pill-danger {
  border-color: #efcaca;
  color: #c94747;
}

.pill-primary {
  border-color: #a9d3e5;
  color: #0d749e;
  background: #eef8fd;
}

.status {
  font-weight: 700;
}

.status.pending {
  color: #ad7a00;
}

.status.approved {
  color: #0a7a40;
}

.status.rejected {
  color: #c13333;
}

.empty-text {
  padding: 20rpx 16rpx;
  color: #7a8ca3;
  font-size: 22rpx;
}

.asset-photo-cell {
  display: flex;
  flex-direction: column;
  gap: 8rpx;
}

.asset-photo-top {
  display: flex;
  align-items: center;
  gap: 8rpx;
  flex-wrap: wrap;
}

.photo-count {
  color: #60738e;
  font-size: 20rpx;
}

.asset-photo-preview {
  display: flex;
}

.asset-photo-thumb {
  width: 72rpx;
  height: 72rpx;
  border-radius: 10rpx;
  border: 1rpx solid #d9e4f2;
}

@media screen and (max-width: 1200px) {
  .admin-kpi-grid {
    grid-template-columns: 1fr;
  }
}

@media screen and (max-width: 768px) {
  .toolbar {
    flex-direction: column;
    align-items: stretch;
  }

  .toolbar-picker,
  .toolbar-search,
  .toolbar-btn {
    width: 100%;
    min-width: 0;
  }

  .table-header {
    display: none;
  }

  .table-row {
    grid-template-columns: 1fr;
    gap: 8rpx;
  }
}
</style>
