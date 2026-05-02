<template>
  <admin-layout title="日报审核" subtitle="审核学生提交的实验室日报" active="dailyReports">
    <view class="card toolbar">
      <picker :range="statusOptions" range-key="label" @change="changeStatus">
        <view class="input toolbar-picker">{{ currentStatusText }}</view>
      </picker>
      <input
        v-model="keyword"
        class="input toolbar-search admin-toolbar-lite__search"
        placeholder="搜索实验室/提交人/内容"
      />
    </view>
    <view class="card ai-toolbar">
      <input
        v-model="nlQuery"
        class="input ai-toolbar__input"
        placeholder="自然语言查询：例如 查今天待审核的巡查结果"
      />
      <view class="ai-toolbar__btn" :class="{ disabled: nlLoading }" @click="runNlQuery">
        {{ nlLoading ? '查询中...' : 'AI查询' }}
      </view>
      <view class="ai-toolbar__btn ai-toolbar__btn--light" @click="clearNlQuery">清空</view>
    </view>
    <view class="report-total">
      总条数：{{ reportList.length }} 条
      <text class="report-total__sub">当前显示：{{ filteredList.length }} 条</text>
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

      <view v-for="item in pagedList" :key="rowKey(item)" class="table-row report-grid">
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
              lazy-load
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

      <view v-if="filteredList.length" class="pager">
        <view class="pager-left">
          <text>第 {{ pageNo }} / {{ totalPages }} 页</text>
          <text class="pager-muted">每页 10 条</text>
        </view>
        <view class="pager-right">
          <view class="pill" :class="{ 'pill-disabled': pageNo <= 1 }" @click="goPrevPage">上一页</view>
          <view class="pill" :class="{ 'pill-disabled': pageNo >= totalPages }" @click="goNextPage">下一页</view>
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
              lazy-load
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
          <textarea
            v-model="reviewRemark"
            class="input textarea"
            placeholder="请输入审核意见（可选）"
            maxlength="255"
          />
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
      pageNo: 1,
      pageSize: 10,
      drawerVisible: false,
      activeItem: {},
      reviewRemark: '',
      nlQuery: '',
      nlLoading: false,
      nlReply: ''
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
    },
    totalPages() {
      return Math.max(1, Math.ceil(this.filteredList.length / this.pageSize))
    },
    pagedList() {
      const start = (this.pageNo - 1) * this.pageSize
      return this.filteredList.slice(start, start + this.pageSize)
    }
  },
  watch: {
    keyword() {
      this.pageNo = 1
    },
    selectedStatus() {
      this.pageNo = 1
    },
    reportList() {
      this.ensurePageInRange()
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
    ensurePageInRange() {
      if (this.pageNo < 1) this.pageNo = 1
      if (this.pageNo > this.totalPages) this.pageNo = this.totalPages
    },
    goPrevPage() {
      if (this.pageNo <= 1) return
      this.pageNo -= 1
    },
    goNextPage() {
      if (this.pageNo >= this.totalPages) return
      this.pageNo += 1
    },
    rowKey(item) {
      const campusId = item?.campus_id ?? 'x'
      const id = item?.id ?? 'x'
      return `${campusId}-${id}`
    },
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
      this.nlReply = ''
    },
    async runNlQuery() {
      const message = String(this.nlQuery || '').trim()
      if (!message || this.nlLoading) return
      this.nlLoading = true
      try {
        const result = await api.adminQuery({
          domain: 'daily_reports',
          message
        })
        if (Array.isArray(result?.items)) {
          this.reportList = result.items
        }
        if (result?.filters && typeof result.filters === 'object') {
          this.selectedStatus = String(result.filters.status || '')
          this.keyword = String(result.filters.keyword || '')
        }
        this.nlReply = String(result?.reply || '查询完成')
        uni.showToast({ title: '查询成功', icon: 'success' })
      } catch (error) {
        uni.showToast({ title: error?.message || 'AI查询失败', icon: 'none' })
      } finally {
        this.nlLoading = false
      }
    },
    async clearNlQuery() {
      this.nlQuery = ''
      this.nlReply = ''
      this.keyword = ''
      this.selectedStatus = ''
      await this.reload()
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

.toolbar,
.ai-toolbar {
  margin-bottom: 28rpx;
  display: flex;
  align-items: center;
  gap: 16rpx;
  flex-wrap: nowrap;
  border-radius: 26rpx;
  background: #f0f4fa;
  border: 1rpx solid #dce7f4;
  box-shadow: 0 12rpx 32rpx rgba(16, 42, 73, 0.08);
  transition: all 0.25s ease;
  padding: 24rpx !important;
}


.ai-toolbar__input {
  flex: 1;
  height: 64rpx;
  border-radius: 20rpx;
  border: 1rpx solid #d8e4dc;
  background: #ffffff;
  padding: 0 20rpx;
}

.ai-toolbar__btn {
  width: 120rpx;
  flex-shrink: 0;
  height: 68rpx;
  padding: 0 16rpx;
  border-radius: 24rpx;
  background: linear-gradient(180deg, #ffffff 0%, #dcf1ff 100%);
  border: 1rpx solid #c8e3f6;
  color: #2b4864;
  font-size: 24rpx;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 8rpx 20rpx rgba(77, 123, 160, 0.18);
  transition: all 0.2s ease;
}

.ai-toolbar__btn:hover {
  background: linear-gradient(180deg, #ffffff 0%, #dcf1ff 100%);
  transform: translateY(-1rpx);
  box-shadow: 0 12rpx 26rpx rgba(77, 123, 160, 0.24);
}


.ai-toolbar__btn.disabled {
  opacity: 0.65;
  pointer-events: none;
}

.report-total {
  margin: 6rpx 20rpx;
  color: #2f4f70;
  font-size: 23rpx;
  font-weight: 700;
}

.report-total__sub {
  margin-left: 16rpx;
  color: #6f8399;
  font-weight: 500;
}

.toolbar:hover {
  transform: translateY(-3rpx);
  box-shadow: 0 18rpx 44rpx rgba(16, 42, 73, 0.1);
}

.toolbar-picker {
  min-width: 220rpx;
  height: 68rpx;
  padding: 0 24rpx;
  border-radius: 24rpx;
  border: 1rpx solid #e4ebf5;
  background: #f4f7fc;
  display: flex;
  align-items: center;
  color: #486280;
  transition: all 0.2s ease;
}

.toolbar-search {
  flex: 1;
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

.toolbar .input {
  height: 68rpx;
  line-height: 68rpx;
  border-radius: 24rpx;
  font-size: 24rpx;
  margin-top: 0;
  padding: 0 24rpx;
  box-sizing: border-box;
}

.toolbar-picker:hover {
  background: #ffffff;
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
  border-radius: 18rpx;
  border: 1rpx solid #c8e3f6;
  color: #2b4864;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(180deg, #ffffff 0%, #dcf1ff 100%);
}

.empty-text {
  padding: 20rpx 16rpx;
  color: #7a8ca3;
  font-size: 22rpx;
}

.pager {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16rpx;
  padding: 18rpx 16rpx;
  border-top: 1rpx solid #e6edf7;
}

.pager-left {
  display: flex;
  align-items: center;
  gap: 10rpx;
  color: #2f4f70;
  font-size: 22rpx;
}

.pager-muted {
  color: #6f8399;
}

.pager-right {
  display: flex;
  gap: 8rpx;
}

.pill-disabled {
  opacity: 0.48;
  pointer-events: none;
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
  border-radius: 24rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1rpx solid #c8e3f6;
  background: linear-gradient(180deg, #ffffff 0%, #dcf1ff 100%);
  color: #2b4864;
  font-size: 24rpx;
  font-weight: 700;
}

.btn-reject {
  background: #fff1f1;
  border-color: #f0c9c9;
  color: #b33d3d;
}

@media screen and (max-width: 768px) {
  .toolbar {
    flex-direction: column;
    align-items: stretch;
  }

  .toolbar-picker,
  .toolbar-search{
    width: 100%;
    min-width: 0;
  }

  .ai-toolbar {
    flex-direction: column;
    align-items: stretch;
  }

  .ai-toolbar__input,
  .ai-toolbar__btn {
    width: 100%;
  }

  .table-header {
    display: none;
  }

  .table-row {
    grid-template-columns: 1fr;
  }

  .pager {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
