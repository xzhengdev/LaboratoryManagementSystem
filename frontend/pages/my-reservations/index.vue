<template>
  <view class="my-res-page">
    <student-top-nav active="reservations" />

    <view class="my-res-page__shell">
      <view class="my-res-page__head">
        <view class="my-res-page__head-copy">
          <view class="my-res-page__title">我的预约</view>
          <view class="my-res-page__sub">集中查看实验室预约记录、当前状态与最近一场预约安排。</view>
        </view>

        <view class="my-res-page__head-actions">
          <view class="my-res-page__new-btn" @click="goNew">新建预约</view>
        </view>
      </view>

      <view class="my-res-page__layout">
        <view class="my-res-side">
          <view class="my-res-side__next-card">
            <view class="my-res-side__eyebrow">最近一场</view>
            <view class="my-res-side__countdown">{{ nextCountdown }}</view>
            <view class="my-res-side__next-lab">{{ nextItem.lab_name || '暂无即将开始的预约' }}</view>
            <view class="my-res-side__next-loc">{{ nextItem.locationLine || '请选择实验室并提交新的预约申请。' }}</view>
            <view
              class="my-res-side__next-btn"
              :class="{ disabled: !nextItem.id }"
              @click="goDetail(nextItem.id)"
            >
              查看预约详情
            </view>
          </view>

          <view class="card my-res-side__status-card">
            <view class="my-res-side__status-title">状态概览</view>
            <view
              v-for="item in statusSummary"
              :key="item.key"
              class="my-res-side__status-row"
              :class="{ active: activeStatus === item.key }"
              @click="setStatus(item.key)"
            >
              <view class="my-res-side__status-dot" :style="{ background: item.color }"></view>
              <view class="my-res-side__status-label">{{ item.label }}</view>
              <view class="my-res-side__status-count">{{ item.count }}</view>
            </view>
          </view>
        </view>

        <view class="my-res-main">
          <view class="card my-res-toolbar">
            <view class="my-res-toolbar__chips">
              <view
                v-for="item in filterTabs"
                :key="item.key"
                class="my-res-toolbar__chip"
                :class="{ active: activeStatus === item.key }"
                @click="setStatus(item.key)"
              >
                {{ item.label }}
                <text>{{ item.count }}</text>
              </view>
            </view>
            <view class="my-res-toolbar__meta">{{ filteredList.length }} 条记录</view>
          </view>

          <view class="card table-card">
            <view class="table-header my-res-table-grid">
              <text>资源与地点</text>
              <text>预约日期</text>
              <text>预约时间</text>
              <text>状态</text>
              <text>操作</text>
            </view>

            <view v-if="!pagedList.length" class="empty-state my-res-main__empty">
              当前筛选条件下没有预约记录，试试切换状态或新建一条预约。
            </view>

            <view v-for="item in pagedList" :key="item.id" class="table-row my-res-table-grid">
              <view class="my-res-resource">
                <view class="my-res-resource__icon">{{ item.iconText }}</view>
                <view class="my-res-resource__content">
                  <view class="table-strong my-res-resource__name">{{ item.lab_name || '未命名实验室' }}</view>
                  <view class="my-res-resource__meta">{{ item.locationLine }}</view>
                  <view class="my-res-resource__purpose">{{ item.purpose || '未填写预约用途' }}</view>
                </view>
              </view>

              <view class="my-res-time">
                <view class="my-res-time__date">{{ item.dateText }}</view>
                <view class="my-res-time__weekday">{{ item.weekdayText }}</view>
              </view>

              <view class="my-res-time">
                <view class="my-res-time__date">{{ item.timeText }}</view>
                <view class="my-res-time__weekday">{{ item.durationText }}</view>
              </view>

              <view class="my-res-status">
                <view class="my-res-status__pill" :class="item.statusClass">{{ item.statusText }}</view>
              </view>

              <view class="actions my-res-actions">
                <view class="pill" @click="goDetail(item.id)">查看详情</view>
                <view v-if="item.canCancel" class="pill pill-danger" @click="cancel(item.id)">取消预约</view>
                <view v-else class="my-res-actions__mute">不可取消</view>
              </view>
            </view>
          </view>

          <view v-if="totalPages > 1" class="my-res-main__pager">
            <view class="my-res-main__page-btn" :class="{ disabled: currentPage === 1 }" @click="prevPage">上一页</view>
            <view
              v-for="n in totalPages"
              :key="n"
              class="my-res-main__page-btn"
              :class="{ active: currentPage === n }"
              @click="currentPage = n"
            >
              {{ n }}
            </view>
            <view class="my-res-main__page-btn" :class="{ disabled: currentPage === totalPages }" @click="nextPage">下一页</view>
          </view>
        </view>
      </view>
    </view>
  </view>
</template>

<script>
import StudentTopNav from '../../components/student-top-nav.vue'
import { api } from '../../api/index'
import { requireLogin } from '../../common/guard'
import { openPage } from '../../common/router'
import { routes } from '../../config/navigation'

function toDateObj(item) {
  const date = item.reservation_date || ''
  const time = item.start_time || '00:00'
  return new Date(`${date}T${time}`)
}

function toDateEndObj(item) {
  const date = item.reservation_date || ''
  const time = item.end_time || '00:00'
  return new Date(`${date}T${time}`)
}

function toMinuteValue(raw) {
  if (!raw) return 0
  const safe = String(raw).slice(0, 5)
  const [hour = 0, minute = 0] = safe.split(':').map((item) => Number(item || 0))
  return hour * 60 + minute
}

function formatDateText(dateStr) {
  if (!dateStr) return '--'
  const date = new Date(`${dateStr}T00:00`)
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${month}/${day}/${date.getFullYear()}`
}

function formatWeekday(dateStr) {
  if (!dateStr) return '日期待定'
  const weekMap = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']
  const date = new Date(`${dateStr}T00:00`)
  return weekMap[date.getDay()] || '日期待定'
}

function formatDuration(startTime, endTime) {
  const start = toMinuteValue(startTime)
  const end = toMinuteValue(endTime)
  if (end <= start) return '时长待定'
  const total = end - start
  const hours = Math.floor(total / 60)
  const minutes = total % 60
  if (hours && minutes) return `${hours}小时${minutes}分钟`
  if (hours) return `${hours}小时`
  return `${minutes}分钟`
}

export default {
  components: { StudentTopNav },
  data() {
    return {
      list: [],
      activeStatus: 'all',
      currentPage: 1,
      pageSize: 6
    }
  },
  computed: {
    normalizedList() {
      const now = Date.now()
      const iconPool = ['实', '约', '研', '课']
      return this.list
        .map((item, index) => {
          const endAt = toDateEndObj(item).getTime()
          let statusText = '待处理'
          let statusKey = 'pending'

          if (item.status === 'approved') {
            if (endAt < now) {
              statusText = '已完成'
              statusKey = 'completed'
            } else {
              statusText = '已批准'
              statusKey = 'approved'
            }
          } else if (item.status === 'rejected') {
            statusText = '已驳回'
            statusKey = 'rejected'
          } else if (item.status === 'cancelled') {
            statusText = '已取消'
            statusKey = 'cancelled'
          }

          return {
            ...item,
            displayStatus: statusKey,
            statusText,
            statusClass: statusKey,
            canCancel: ['pending', 'approved'].includes(statusKey),
            dateText: formatDateText(item.reservation_date),
            weekdayText: formatWeekday(item.reservation_date),
            timeText: `${(item.start_time || '--:--').slice(0, 5)} - ${(item.end_time || '--:--').slice(0, 5)}`,
            durationText: formatDuration(item.start_time, item.end_time),
            locationLine: `${item.campus_name || '校区待定'} · ${item.location || '位置待定'}`,
            iconText: iconPool[index % iconPool.length]
          }
        })
        .sort((a, b) => toDateObj(b).getTime() - toDateObj(a).getTime())
    },
    filteredList() {
      if (this.activeStatus === 'all') return this.normalizedList
      return this.normalizedList.filter((item) => item.displayStatus === this.activeStatus)
    },
    totalPages() {
      return Math.max(1, Math.ceil(this.filteredList.length / this.pageSize))
    },
    pagedList() {
      const start = (this.currentPage - 1) * this.pageSize
      return this.filteredList.slice(start, start + this.pageSize)
    },
    statusSummary() {
      const items = [
        { key: 'approved', label: '已批准', color: '#3cc6ea' },
        { key: 'pending', label: '待处理', color: '#f3be2f' },
        { key: 'completed', label: '已完成', color: '#b9c5d6' },
        { key: 'cancelled', label: '已取消', color: '#d13232' },
        { key: 'rejected', label: '已驳回', color: '#c75c5c' }
      ]
      return items.map((item) => ({
        ...item,
        count: this.normalizedList.filter((row) => row.displayStatus === item.key).length
      }))
    },
    filterTabs() {
      return [
        { key: 'all', label: '全部', count: this.normalizedList.length },
        ...this.statusSummary
      ]
    },
    nextItem() {
      const now = Date.now()
      const upcoming = this.normalizedList
        .filter((item) => item.displayStatus === 'approved' && toDateObj(item).getTime() > now)
        .sort((a, b) => toDateObj(a).getTime() - toDateObj(b).getTime())
      return upcoming[0] || {}
    },
    nextCountdown() {
      if (!this.nextItem.id) return '暂无'
      const diff = Math.max(0, toDateObj(this.nextItem).getTime() - Date.now())
      const hours = Math.floor(diff / 3600000)
      const minutes = Math.floor((diff % 3600000) / 60000)
      return `${String(hours).padStart(2, '0')} 小时 ${String(minutes).padStart(2, '0')} 分钟`
    }
  },
  async onShow() {
    if (!requireLogin()) return
    await this.loadData()
  },
  methods: {
    async loadData() {
      try {
        this.list = await api.myReservations()
      } catch (_error) {
        this.list = []
      }
      this.currentPage = 1
    },
    setStatus(key) {
      this.activeStatus = key
      this.currentPage = 1
    },
    goNew() {
      openPage(routes.reserve)
    },
    goDetail(id) {
      if (!id) return
      openPage(routes.reservationDetail, { query: { id } })
    },
    async cancel(id) {
      if (!id) return
      await api.cancelReservation(id)
      uni.showToast({ title: '预约已取消', icon: 'success' })
      await this.loadData()
    },
    prevPage() {
      this.currentPage = Math.max(1, this.currentPage - 1)
    },
    nextPage() {
      this.currentPage = Math.min(this.totalPages, this.currentPage + 1)
    }
  }
}
</script>

<style lang="scss">
.my-res-page {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background:
    radial-gradient(circle at 12% 14%, rgba(109, 179, 230, 0.25), transparent 26%),
    radial-gradient(circle at 88% 18%, rgba(173, 208, 240, 0.26), transparent 24%),
    linear-gradient(180deg, #edf5fc 0%, #dceaf7 100%);
}

.my-res-page__shell {
  flex: 1;
  padding: 30rpx 32rpx 44rpx;
}

.my-res-page__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 24rpx;
}

.my-res-page__head-copy {
  max-width: 980rpx;
}

.my-res-page__title {
  color: #061f44;
  font-size: 76rpx;
  line-height: 1.04;
  font-weight: 800;
  letter-spacing: -1.4rpx;
}

.my-res-page__sub {
  margin-top: 12rpx;
  color: #5d6f87;
  font-size: 28rpx;
  line-height: 1.6;
}

.my-res-page__head-actions {
  display: flex;
  align-items: center;
}

.my-res-page__new-btn {
  min-width: 148rpx;
  height: 72rpx;
  border-radius: 18rpx;
  padding: 0 24rpx;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #6ea7f2 0%, #3d78d4 55%, #295cab 100%);
  color: #f7fbff;
  font-size: 24rpx;
  font-weight: 800;
  box-shadow: 0 12rpx 28rpx rgba(41, 92, 171, 0.24);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.my-res-page__new-btn:hover {
  transform: translateY(-2rpx);
  box-shadow: 0 20rpx 40rpx rgba(41, 92, 171, 0.28);
}

.my-res-page__layout {
  margin-top: 24rpx;
  display: grid;
  grid-template-columns: 320rpx minmax(0, 1fr);
  gap: 24rpx;
  align-items: start;
}

.card,
.table-card,
.my-res-side__next-card {
  border-radius: 24rpx;
  box-shadow: 0 12rpx 32rpx rgba(18, 200, 167, 0.08);
  transition: transform 0.25s ease, box-shadow 0.25s ease;
}

.card:hover,
.table-card:hover,
.my-res-side__next-card:hover {
  transform: translateY(-4rpx);
  box-shadow: 0 20rpx 48rpx rgba(16, 42, 73, 0.12);
}

.card {
  border: 1rpx solid #dbe4f1;
  background: #ffffff;
}

.my-res-side {
  display: grid;
  gap: 18rpx;
  align-content: start;
}

.my-res-side__next-card {
  padding: 24rpx;
  background:
    radial-gradient(circle at top right, rgba(255, 255, 255, 0.22), transparent 32%),
    linear-gradient(160deg, #8fb7e8 0%, #4f78b8 52%, #274a7d 100%);
  color: #eaf4ff;
}

.my-res-side__eyebrow {
  color: #96afd2;
  font-size: 21rpx;
  font-weight: 700;
}

.my-res-side__countdown {
  margin-top: 10rpx;
  color: #ffffff;
  font-size: 56rpx;
  line-height: 1.12;
  font-weight: 800;
  letter-spacing: -1rpx;
}

.my-res-side__next-lab {
  margin-top: 14rpx;
  color: #e6efff;
  font-size: 27rpx;
  line-height: 1.4;
  font-weight: 800;
}

.my-res-side__next-loc {
  margin-top: 8rpx;
  color: #a7bbd7;
  font-size: 22rpx;
  line-height: 1.65;
}

.my-res-side__next-btn {
  margin-top: 22rpx;
  height: 64rpx;
  border-radius: 16rpx;
  background: #3eb4ea;
  color: #032349;
  font-size: 24rpx;
  font-weight: 800;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: transform 0.2s ease, box-shadow 0.2s ease, opacity 0.2s ease;
}

.my-res-side__next-btn:hover {
  transform: translateY(-2rpx);
  box-shadow: 0 16rpx 28rpx rgba(62, 180, 234, 0.22);
}

.my-res-side__next-btn.disabled {
  opacity: 0.58;
  pointer-events: none;
  box-shadow: none;
}

.my-res-side__status-card {
  padding: 18rpx;
}

.my-res-side__status-title {
  color: #0b274e;
  font-size: 32rpx;
  font-weight: 800;
}

.my-res-side__status-row {
  margin-top: 12rpx;
  min-height: 60rpx;
  border-radius: 16rpx;
  padding: 0 14rpx;
  display: flex;
  align-items: center;
  gap: 12rpx;
  transition: background 0.2s ease, transform 0.2s ease;
}

.my-res-side__status-row.active {
  background: #edf3fb;
}

.my-res-side__status-row:hover {
  transform: translateX(2rpx);
}

.my-res-side__status-dot {
  width: 12rpx;
  height: 12rpx;
  border-radius: 999rpx;
  flex-shrink: 0;
}

.my-res-side__status-label {
  flex: 1;
  color: #344a65;
  font-size: 24rpx;
  font-weight: 700;
}

.my-res-side__status-count {
  color: #73849a;
  font-size: 24rpx;
  font-weight: 800;
}

.my-res-main {
  min-width: 0;
}

.my-res-toolbar {
  margin-bottom: 20rpx;
  padding: 20rpx 24rpx;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16rpx;
  flex-wrap: wrap;
  border-radius: 24rpx;
  background: #f0f4fa;
  border: 1rpx solid #dce7f4;
  box-shadow: 0 10rpx 26rpx rgba(16, 42, 73, 0.06);
}

.my-res-toolbar__chips {
  display: flex;
  flex-wrap: wrap;
  gap: 10rpx;
}

.my-res-toolbar__chip {
  min-height: 58rpx;
  padding: 0 16rpx;
  border-radius: 999rpx;
  background: #ffffff;
  border: 1rpx solid #dbe5f1;
  color: #546982;
  display: inline-flex;
  align-items: center;
  gap: 8rpx;
  font-size: 22rpx;
  font-weight: 700;
  transition: all 0.2s ease;
}

.my-res-toolbar__chip text {
  min-width: 30rpx;
  height: 30rpx;
  border-radius: 999rpx;
  background: #edf3fb;
  color: #5b6e86;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 18rpx;
  font-weight: 800;
}

.my-res-toolbar__chip.active {
  background: linear-gradient(135deg, #5d93e8 0%, #346ec7 100%);
  border-color: #346ec7;
  color: #f8fbff;
}

.my-res-toolbar__chip.active text {
  background: rgba(255, 255, 255, 0.2);
  color: #ffffff;
}

.my-res-toolbar__meta {
  min-height: 58rpx;
  padding: 0 18rpx;
  border-radius: 18rpx;
  background: #edf3fb;
  color: #46607f;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 23rpx;
  font-weight: 800;
}

.table-card {
  border: 1rpx solid #dbe4f1;
  background: #ffffff;
  overflow: hidden;
}

.my-res-table-grid {
  display: grid;
  grid-template-columns: minmax(0, 2.2fr) 0.9fr 1fr 0.8fr 1fr;
  gap: 20rpx;
  align-items: center;
}

.table-header {
  padding: 24rpx 28rpx;
  background: #f4f7fb;
  border-bottom: 1rpx solid #e5ecf5;
  color: #6d7f95;
  font-size: 22rpx;
  font-weight: 700;
}

.table-row {
  padding: 26rpx 28rpx;
  border-bottom: 1rpx solid #edf2f7;
  transition: background 0.2s ease;
}

.table-row:last-of-type {
  border-bottom: none;
}

.table-row:hover {
  background: #f7faff;
}

.table-strong {
  color: #0f2744;
  font-weight: 800;
}

.empty-state {
  padding: 32rpx 28rpx;
  color: #6d7f95;
  font-size: 24rpx;
}

.my-res-resource {
  display: flex;
  align-items: flex-start;
  gap: 16rpx;
  min-width: 0;
}

.my-res-resource__icon {
  width: 64rpx;
  height: 64rpx;
  border-radius: 18rpx;
  background: linear-gradient(135deg, #edf2f8, #f9fbff);
  color: #213a5d;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28rpx;
  font-weight: 800;
  flex-shrink: 0;
}

.my-res-resource__content {
  min-width: 0;
}

.my-res-resource__name {
  font-size: 32rpx;
  line-height: 1.24;
}

.my-res-resource__meta {
  margin-top: 6rpx;
  color: #64778e;
  font-size: 22rpx;
  line-height: 1.55;
}

.my-res-resource__purpose {
  margin-top: 6rpx;
  color: #8a9aaf;
  font-size: 21rpx;
  line-height: 1.55;
}

.my-res-time__date {
  color: #112d53;
  font-size: 30rpx;
  font-weight: 800;
  line-height: 1.2;
}

.my-res-time__weekday {
  margin-top: 6rpx;
  color: #6a7b92;
  font-size: 22rpx;
  line-height: 1.5;
}

.my-res-status__pill {
  min-height: 44rpx;
  border-radius: 999rpx;
  padding: 0 16rpx;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 20rpx;
  font-weight: 800;
}

.my-res-status__pill.pending {
  background: #fdeac3;
  color: #a97712;
}

.my-res-status__pill.approved {
  background: #d8f3fb;
  color: #0a7f9e;
}

.my-res-status__pill.completed {
  background: #eef2f7;
  color: #73849a;
}

.my-res-status__pill.cancelled,
.my-res-status__pill.rejected {
  background: #fde0e0;
  color: #bf2a2a;
}

.actions {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10rpx;
}

.pill {
  min-height: 52rpx;
  padding: 0 16rpx;
  border-radius: 16rpx;
  border: 1rpx solid #d9e4f2;
  background: #ffffff;
  color: #476183;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 22rpx;
  font-weight: 700;
  transition: all 0.2s ease;
}

.pill:hover {
  opacity: 0.92;
  transform: translateY(-1rpx);
  background: #f6f9fd;
}

.pill-danger {
  border-color: #f1d3d3;
  color: #c43636;
  background: #fff9f9;
}

.pill-danger:hover {
  background: #fff1f1;
}

.my-res-actions__mute {
  color: #97a6b9;
  font-size: 22rpx;
  font-weight: 700;
}

.my-res-main__pager {
  margin-top: 20rpx;
  display: flex;
  justify-content: center;
  gap: 8rpx;
  flex-wrap: wrap;
}

.my-res-main__page-btn {
  min-width: 60rpx;
  height: 56rpx;
  padding: 0 18rpx;
  border-radius: 14rpx;
  background: #eef2f7;
  color: #61738b;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22rpx;
  font-weight: 700;
}

.my-res-main__page-btn.active {
  background: #0a254c;
  color: #ffffff;
}

.my-res-main__page-btn.disabled {
  opacity: 0.45;
}




@media screen and (min-width: 1500px) {
  .my-res-page__shell {
    padding-left: 56rpx;
    padding-right: 56rpx;
  }
}

@media screen and (max-width: 1180px) {
  .my-res-page__layout {
    grid-template-columns: 1fr;
  }
}

@media screen and (max-width: 920px) {
  .my-res-page__head {
    flex-direction: column;
    align-items: flex-start;
  }

  .my-res-page__head-actions {
    width: 100%;
  }

  .my-res-page__new-btn {
    width: 100%;
  }

  .my-res-table-grid {
    grid-template-columns: 1fr;
    gap: 12rpx;
  }

  .table-header {
    display: none;
  }
}

@media screen and (max-width: 760px) {
  .my-res-page__shell {
    padding: 18rpx 14rpx calc(34rpx + env(safe-area-inset-bottom));
  }

  .my-res-page__title {
    font-size: 50rpx;
    letter-spacing: 0;
  }

  .my-res-page__sub {
    margin-top: 8rpx;
    font-size: 23rpx;
    line-height: 1.55;
  }

  .my-res-page__new-btn {
    min-width: 0;
    height: 64rpx;
    border-radius: 14rpx;
    font-size: 22rpx;
  }

  .my-res-page__layout {
    margin-top: 14rpx;
    gap: 14rpx;
  }

  .my-res-side {
    gap: 12rpx;
  }

  .my-res-side__next-card {
    padding: 18rpx;
    border-radius: 18rpx;
  }

  .my-res-side__countdown {
    font-size: 44rpx;
  }

  .my-res-side__next-lab {
    font-size: 24rpx;
  }

  .my-res-side__next-loc {
    font-size: 20rpx;
  }

  .my-res-side__next-btn {
    margin-top: 14rpx;
    height: 56rpx;
    border-radius: 12rpx;
    font-size: 22rpx;
  }

  .my-res-side__status-card {
    padding: 14rpx;
    border-radius: 18rpx;
  }

  .my-res-side__status-title {
    font-size: 28rpx;
  }

  .my-res-side__status-row {
    min-height: 52rpx;
    margin-top: 8rpx;
    border-radius: 12rpx;
  }

  .my-res-side__status-label,
  .my-res-side__status-count {
    font-size: 22rpx;
  }

  .my-res-toolbar {
    margin-bottom: 12rpx;
    padding: 14rpx;
    border-radius: 18rpx;
  }

  .my-res-toolbar__chip {
    min-height: 50rpx;
    font-size: 20rpx;
    padding: 0 12rpx;
  }

  .my-res-toolbar__meta {
    min-height: 50rpx;
    font-size: 21rpx;
  }

  .table-row {
    padding: 16rpx 14rpx;
    border-radius: 14rpx;
    margin-bottom: 10rpx;
    border: 1rpx solid #e7edf5;
    background: #fff;
  }

  .table-row:last-of-type {
    border-bottom: 1rpx solid #e7edf5;
  }

  .my-res-resource {
    gap: 12rpx;
  }

  .my-res-resource__icon {
    width: 52rpx;
    height: 52rpx;
    border-radius: 14rpx;
    font-size: 22rpx;
  }

  .my-res-resource__name {
    font-size: 28rpx;
  }

  .my-res-resource__meta,
  .my-res-resource__purpose,
  .my-res-time__weekday {
    font-size: 20rpx;
  }

  .my-res-time__date {
    font-size: 26rpx;
  }

  .my-res-status__pill {
    min-height: 40rpx;
    font-size: 19rpx;
    padding: 0 12rpx;
  }

  .pill {
    min-height: 46rpx;
    border-radius: 12rpx;
    font-size: 20rpx;
  }

  .my-res-main__pager {
    margin-top: 14rpx;
    justify-content: flex-start;
  }

  .my-res-main__page-btn {
    min-width: 52rpx;
    height: 48rpx;
    font-size: 20rpx;
    border-radius: 12rpx;
  }
}

@media screen and (max-width: 420px) {
  .my-res-page__title {
    font-size: 44rpx;
  }

  .my-res-page__sub {
    font-size: 22rpx;
  }

  .my-res-resource__name {
    font-size: 26rpx;
  }
}

</style>
