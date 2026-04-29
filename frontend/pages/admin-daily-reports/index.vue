<template>
  <admin-layout title="日报审核" subtitle="审核学生提交的实验室日报" active="dailyReports">
    <view class="card toolbar">
      <picker :range="statusOptions" range-key="label" @change="changeStatus">
        <view class="input toolbar-picker">{{ currentStatusText }}</view>
      </picker>
      <input v-model="keyword" class="input toolbar-search" placeholder="搜索实验室/提交人/内容" />
      <view class="toolbar-btn" @click="reload">刷新</view>
    </view>

    <view class="card table-card">
      <view class="table-header report-grid">
        <text>提交日期</text>
        <text>实验室</text>
        <text>提交人</text>
        <text>内容</text>
        <text>图片</text>
        <text>状态</text>
        <text>操作</text>
      </view>

      <view v-if="!filteredList.length" class="empty-text">暂无日报记录</view>

      <view v-for="item in filteredList" :key="item.id" class="table-row report-grid">
        <view>
          <view>{{ item.report_date || '--' }}</view>
          <view class="row-sub">{{ timeText(item.created_at) }}</view>
        </view>
        <view>
          <view class="strong">{{ item.lab_name || '--' }}</view>
          <view class="row-sub">{{ item.campus_name || '--' }}</view>
        </view>
        <view>{{ item.reporter_name || '--' }}</view>
        <view class="content-cell">{{ item.content || '--' }}</view>
        <view>
          <view class="photo-count">共 {{ photoList(item).length }} 张</view>
          <view v-if="photoList(item).length" class="photo-thumb-list">
            <image
              v-for="(photo, idx) in photoList(item).slice(0, 3)"
              :key="photo.id || idx"
              class="photo-thumb"
              :src="photo.url"
              mode="aspectFill"
              @click="previewPhotos(item, idx)"
            />
          </view>
        </view>
        <text :class="statusClass(item.status)">{{ statusText(item.status) }}</text>
        <view class="actions">
          <view class="pill" @click="openDrawer(item)">详情</view>
        </view>
      </view>
    </view>

    <view v-if="drawerVisible" class="drawer-mask" @click="closeDrawer">
      <view class="drawer" @click.stop>
        <view class="drawer-title">日报详情</view>
        <view class="drawer-sub">{{ activeItem.lab_name || '--' }} · {{ activeItem.report_date || '--' }}</view>

        <view class="field">
          <text class="label">提交人</text>
          <view class="input">{{ activeItem.reporter_name || '--' }}</view>
        </view>
        <view class="field">
          <text class="label">提交内容</text>
          <view class="input textarea-view">{{ activeItem.content || '--' }}</view>
        </view>
        <view class="field">
          <text class="label">图片</text>
          <view class="drawer-photos">
            <image
              v-for="(photo, idx) in photoList(activeItem)"
              :key="photo.id || idx"
              class="drawer-photo"
              :src="photo.url"
              mode="aspectFill"
              @click="previewPhotos(activeItem, idx)"
            />
            <view v-if="!photoList(activeItem).length" class="empty-mini">暂无图片</view>
          </view>
        </view>

        <view class="field">
          <text class="label">当前状态</text>
          <view class="input">{{ statusText(activeItem.status) }}</view>
        </view>

        <view v-if="canReview(activeItem)" class="field">
          <text class="label">审核意见</text>
          <textarea v-model="reviewRemark" class="input textarea" placeholder="请输入审核意见（可选）" maxlength="255" />
        </view>

        <view class="drawer-actions" v-if="canReview(activeItem)">
          <view class="btn btn-approve" @click="review('approved')">审核通过</view>
          <view class="btn btn-reject" @click="review('rejected')">驳回</view>
        </view>
      </view>
    </view>
  </admin-layout>
</template>

<script>
import { api } from '../../api/index'
import { requireLogin } from '../../common/guard'
import { getProfile } from '../../common/session'
import { canApproveReservations, routes } from '../../config/navigation'
import { openPage } from '../../common/router'
import AdminLayout from '../../components/admin-layout.vue'

export default {
  components: { AdminLayout },
  data() {
    return {
      profile: {},
      reportList: [],
      keyword: '',
      statusOptions: [
        { label: '全部状态', value: '' },
        { label: '待审核', value: 'pending' },
        { label: '已通过', value: 'approved' },
        { label: '已驳回', value: 'rejected' }
      ],
      selectedStatus: '',
      drawerVisible: false,
      activeItem: {},
      reviewRemark: ''
    }
  },
  computed: {
    currentStatusText() {
      const current = this.statusOptions.find((item) => item.value === this.selectedStatus)
      return current ? current.label : '全部状态'
    },
    filteredList() {
      const text = this.keyword.trim().toLowerCase()
      return this.reportList.filter((item) => {
        const hitKeyword = !text || `${item.lab_name || ''}${item.reporter_name || ''}${item.content || ''}`.toLowerCase().includes(text)
        const hitStatus = !this.selectedStatus || item.status === this.selectedStatus
        return hitKeyword && hitStatus
      })
    }
  },
  async onShow() {
    if (!requireLogin()) return
    this.profile = getProfile()
    if (!canApproveReservations(this.profile.role)) {
      uni.showToast({ title: '当前角色无权限访问', icon: 'none' })
      openPage(routes.home, { replace: true })
      return
    }
    await this.reload()
  },
  methods: {
    photoList(item) {
      return Array.isArray(item?.photos) ? item.photos.filter((row) => row && row.url) : []
    },
    timeText(value) {
      if (!value) return '--'
      return String(value).replace('T', ' ').slice(0, 19)
    },
    statusText(status) {
      const map = {
        pending: '待审核',
        approved: '已通过',
        rejected: '已驳回'
      }
      return map[status] || status || '--'
    },
    statusClass(status) {
      if (status === 'approved') return 'status approved'
      if (status === 'rejected') return 'status rejected'
      return 'status pending'
    },
    changeStatus(event) {
      this.selectedStatus = this.statusOptions[event.detail.value].value
    },
    async reload() {
      this.reportList = await api.dailyReports()
    },
    previewPhotos(item, index = 0) {
      const urls = this.photoList(item).map((row) => row.url)
      if (!urls.length) return
      uni.previewImage({ urls, current: urls[index] || urls[0] })
    },
    canReview(item) {
      return String(item?.status || '').toLowerCase() === 'pending'
    },
    openDrawer(item) {
      this.activeItem = item
      this.reviewRemark = ''
      this.drawerVisible = true
    },
    closeDrawer() {
      this.drawerVisible = false
    },
    async review(reviewStatus) {
      if (!this.activeItem?.id) return
      await api.reviewDailyReport(this.activeItem.id, {
        review_status: reviewStatus,
        review_remark: this.reviewRemark || (reviewStatus === 'approved' ? '审核通过' : '审核驳回')
      })
      uni.showToast({ title: '审核完成', icon: 'success' })
      this.closeDrawer()
      await this.reload()
    }
  }
}
</script>

<style lang="scss">
page {
  background: #f5f7fa;
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
}

.report-grid {
  grid-template-columns: 1fr 1fr 0.8fr 1.2fr 1fr 0.7fr 0.8fr;
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

.content-cell {
  display: -webkit-box;
  overflow: hidden;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.photo-count {
  color: #60738e;
  font-size: 20rpx;
}

.photo-thumb-list {
  margin-top: 6rpx;
  display: flex;
  gap: 6rpx;
}

.photo-thumb {
  width: 62rpx;
  height: 62rpx;
  border-radius: 10rpx;
  border: 1rpx solid #d9e4f2;
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

.actions {
  display: flex;
  gap: 8rpx;
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

.empty-text {
  padding: 20rpx 16rpx;
  color: #7a8ca3;
  font-size: 22rpx;
}

.drawer-mask {
  position: fixed;
  inset: 0;
  background: rgba(10, 26, 45, 0.4);
  display: flex;
  justify-content: flex-end;
  z-index: 999;
}

.drawer {
  width: 92vw;
  max-width: 720rpx;
  height: 100%;
  background: #fff;
  padding: 26rpx 24rpx;
  box-sizing: border-box;
  overflow-y: auto;
}

.drawer-title {
  font-size: 36rpx;
  font-weight: 800;
  color: #102f50;
}

.drawer-sub {
  margin-top: 8rpx;
  color: #6d7f95;
  font-size: 23rpx;
}

.field {
  margin-top: 16rpx;
}

.label {
  color: #5f7592;
  font-size: 22rpx;
  font-weight: 700;
}

.input {
  margin-top: 8rpx;
  border: 1rpx solid #d7e3f1;
  border-radius: 14rpx;
  background: #f8fbff;
  padding: 14rpx;
  color: #1a3553;
  font-size: 23rpx;
}

.textarea {
  width: 100%;
  min-height: 120rpx;
}

.textarea-view {
  white-space: pre-wrap;
}

.drawer-photos {
  margin-top: 8rpx;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10rpx;
}

.drawer-photo {
  width: 100%;
  height: 160rpx;
  border-radius: 12rpx;
  border: 1rpx solid #d8e3f0;
}

.empty-mini {
  color: #7b8ba1;
  font-size: 22rpx;
}

.drawer-actions {
  margin-top: 24rpx;
  display: flex;
  gap: 12rpx;
}

.btn {
  flex: 1;
  height: 70rpx;
  border-radius: 16rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 24rpx;
  font-weight: 700;
}

.btn-approve {
  background: #0f9d58;
}

.btn-reject {
  background: #d64545;
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
  }
}
</style>
