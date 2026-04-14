<template>
  <view class="my-res-page">
    <!-- #ifdef H5 -->
    <student-top-nav active="reservations" />
    <!-- #endif -->

    <!-- #ifndef H5 -->
    <user-top-nav active="reservations" />
    <!-- #endif -->

    <view class="my-res-page__shell">
      <view class="my-res-page__head">
        <view>
          <view class="my-res-page__title">我的预约</view>
          <view class="my-res-page__sub">
            管理您在分布式校区网络中的实验室课程、设备预订和临床空间访问。
          </view>
        </view>

        <view class="my-res-page__head-actions">
          <view class="my-res-page__new-btn" @click="goNew">新建预约</view>
        </view>
      </view>

      <view class="my-res-page__layout">
        <view class="my-res-side">
          <view class="my-res-side__next-card">
            <view class="my-res-side__next-title">下一场次</view>
            <view class="my-res-side__next-time">{{ nextCountdown }}</view>
            <view class="my-res-side__next-lab">{{ nextItem.lab_name || '暂无进行中的预约' }}</view>
            <view class="my-res-side__next-loc">{{ nextItem.locationLine }}</view>
            <view class="my-res-side__next-btn" @click="goDetail(nextItem.id)">查看访问密钥</view>
          </view>

          <view class="my-res-side__status-card">
            <view class="my-res-side__status-title">快捷状态</view>
            <view
              v-for="item in statusSummary"
              :key="item.key"
              class="my-res-side__status-row"
              :class="{ active: activeStatus === item.key }"
              @click="setStatus(item.key)"
            >
              <view class="my-res-side__dot" :style="{ background: item.color }"></view>
              <view class="my-res-side__status-label">{{ item.label }}</view>
              <view class="my-res-side__status-count">{{ item.count }}</view>
            </view>
          </view>
        </view>

        <view class="my-res-main">
          <view class="my-res-main__thead">
            <text>资源与地点</text>
            <text>日期与时间</text>
            <text>状态</text>
            <text>操作</text>
          </view>

          <view v-if="!pagedList.length" class="my-res-main__empty">当前状态下没有预约记录。</view>

          <view v-for="item in pagedList" :key="item.id" class="my-res-main__row" :class="item.rowClass">
            <view class="my-res-main__resource">
              <view class="my-res-main__icon">{{ item.iconText }}</view>
              <view>
                <view class="my-res-main__name">{{ item.lab_name }}</view>
                <view class="my-res-main__loc">{{ item.locationLine }}</view>
              </view>
            </view>

            <view class="my-res-main__time">
              <view class="my-res-main__date">{{ item.dateText }}</view>
              <view class="my-res-main__range">{{ item.timeText }}</view>
            </view>

            <view class="my-res-main__status">
              <view class="my-res-main__status-pill" :class="item.statusClass">{{ item.statusText }}</view>
            </view>

            <view class="my-res-main__ops">
              <view class="my-res-main__detail" @click="goDetail(item.id)">详情</view>
              <view
                v-if="item.canCancel"
                class="my-res-main__cancel"
                @click="cancel(item.id)"
              >
                取消
              </view>
            </view>
          </view>

          <view v-if="totalPages > 1" class="my-res-main__pager">
            <view class="my-res-main__page-btn" @click="prevPage">&lt;</view>
            <view
              v-for="n in totalPages"
              :key="n"
              class="my-res-main__page-btn"
              :class="{ active: currentPage === n }"
              @click="currentPage = n"
            >
              {{ n }}
            </view>
            <view class="my-res-main__page-btn" @click="nextPage">&gt;</view>
          </view>
        </view>
      </view>

    </view>

    <site-footer />
  </view>
</template>

<script>
import SiteFooter from '../../components/site-footer.vue'
import StudentTopNav from '../../components/student-top-nav.vue'
import UserTopNav from '../../components/user-top-nav.vue'
import { api } from '../../api/index'
import { requireLogin } from '../../common/guard'
import { openPage } from '../../common/router'
import { routes } from '../../config/navigation'

function toDateObj(item) {
  const d = item.reservation_date || ''
  const t = item.start_time || '00:00'
  return new Date(`${d}T${t}`)
}

function toDateEndObj(item) {
  const d = item.reservation_date || ''
  const t = item.end_time || '00:00'
  return new Date(`${d}T${t}`)
}

function formatDateText(dateStr) {
  if (!dateStr) return '--'
  const date = new Date(`${dateStr}T00:00`)
  const m = String(date.getMonth() + 1).padStart(2, '0')
  const d = String(date.getDate()).padStart(2, '0')
  return `${m}/${d}/${date.getFullYear()}`
}

export default {
  components: { SiteFooter, StudentTopNav, UserTopNav },
  data() {
    return {
      list: [],
      activeStatus: 'all',
      currentPage: 1,
      pageSize: 4
    }
  },
  computed: {
    normalizedList() {
      const now = Date.now()
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
            statusText = '已拒绝'
            statusKey = 'rejected'
          } else if (item.status === 'cancelled') {
            statusText = '已取消'
            statusKey = 'cancelled'
          }

          const paletteMap = {
            pending: 'pending',
            approved: 'approved',
            completed: 'completed',
            rejected: 'rejected',
            cancelled: 'cancelled'
          }

          const iconPool = ['⚗', '▣', '⌬', '⚠']
          return {
            ...item,
            displayStatus: statusKey,
            statusText,
            statusClass: paletteMap[statusKey],
            canCancel: ['pending', 'approved'].includes(statusKey),
            dateText: formatDateText(item.reservation_date),
            timeText: `${(item.start_time || '--').slice(0, 5)} - ${(item.end_time || '--').slice(0, 5)}`,
            locationLine: `${item.campus_name || '校区待定'} · ${item.location || '位置待定'}`,
            rowClass: paletteMap[statusKey],
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
      const statusKeys = [
        { key: 'approved', label: '已批准', color: '#3cc6ea' },
        { key: 'pending', label: '待处理', color: '#f3be2f' },
        { key: 'completed', label: '已完成', color: '#b9c5d6' },
        { key: 'cancelled', label: '已取消', color: '#d13232' }
      ]
      return statusKeys.map((item) => ({
        ...item,
        count: this.normalizedList.filter((row) => row.displayStatus === item.key).length
      }))
    },
    nextItem() {
      const now = Date.now()
      const upcoming = this.normalizedList
        .filter((item) => item.displayStatus === 'approved' && toDateObj(item).getTime() > now)
        .sort((a, b) => toDateObj(a).getTime() - toDateObj(b).getTime())
      return upcoming[0] || {}
    },
    nextCountdown() {
      if (!this.nextItem.id) return '--'
      const diff = Math.max(0, toDateObj(this.nextItem).getTime() - Date.now())
      const h = Math.floor(diff / 3600000)
      const m = Math.floor((diff % 3600000) / 60000)
      return `${String(h).padStart(2, '0')} 小时 ${String(m).padStart(2, '0')} 分钟`
    }
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
      try {
        this.list = await api.myReservations()
      } catch (error) {
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
      await api.cancelReservation(id)
      uni.showToast({ title: '已取消预约', icon: 'success' })
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
    radial-gradient(circle at top right, rgba(65, 190, 253, 0.11), transparent 26%),
    linear-gradient(180deg, #f7f9fc 0%, #eef2f7 100%);
}

.my-res-page__shell {
  flex: 1;
  padding: 30rpx 32rpx 40rpx;
}

.my-res-page__head {
  display: flex;
  justify-content: space-between;
  gap: 20rpx;
  align-items: center;
}

.my-res-page__title {
  font-size: 76rpx;
  line-height: 1.04;
  color: #061f44;
  font-weight: 800;
  letter-spacing: -1.4rpx;
}

.my-res-page__sub {
  margin-top: 10rpx;
  color: #5d6f87;
  font-size: 28rpx;
  line-height: 1.5;
  max-width: 980rpx;
}

.my-res-page__head-actions {
  display: flex;
  align-items: center;
  gap: 12rpx;
}

.my-res-page__new-btn {
  min-width: 130rpx;
  height: 70rpx;
  border-radius: 16rpx;
  padding: 0 22rpx;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 24rpx;
  font-weight: 800;
}

.my-res-page__new-btn {
  background: #0a254c;
  color: #eef6ff;
  box-shadow: 0 10rpx 26rpx rgba(10, 37, 76, 0.2);
}

.my-res-page__layout {
  margin-top: 20rpx;
  display: grid;
  grid-template-columns: 320rpx minmax(0, 1fr);
  gap: 20rpx;
}

.my-res-side {
  display: grid;
  gap: 16rpx;
  align-content: start;
}

.my-res-side__next-card {
  background: linear-gradient(170deg, #0b2550, #081938);
  color: #d8e7ff;
  border-radius: 26rpx;
  padding: 20rpx;
}

.my-res-side__next-title {
  color: #94adcf;
  font-size: 21rpx;
}

.my-res-side__next-time {
  margin-top: 8rpx;
  color: #ffffff;
  font-size: 56rpx;
  line-height: 1.15;
  font-weight: 800;
}

.my-res-side__next-lab {
  margin-top: 10rpx;
  color: #d5e5fb;
  font-size: 24rpx;
  font-weight: 700;
}

.my-res-side__next-loc {
  margin-top: 6rpx;
  color: #9db4d4;
  font-size: 22rpx;
  line-height: 1.5;
}

.my-res-side__next-btn {
  margin-top: 20rpx;
  height: 64rpx;
  border-radius: 14rpx;
  background: #3eb4ea;
  color: #032349;
  font-size: 24rpx;
  font-weight: 800;
  display: flex;
  align-items: center;
  justify-content: center;
}

.my-res-side__status-card {
  border-radius: 24rpx;
  background: rgba(255, 255, 255, 0.72);
  border: 1rpx solid rgba(197, 198, 207, 0.28);
  padding: 16rpx;
}

.my-res-side__status-title {
  color: #0b274e;
  font-size: 32rpx;
  font-weight: 800;
}

.my-res-side__status-row {
  margin-top: 12rpx;
  min-height: 58rpx;
  border-radius: 14rpx;
  padding: 0 12rpx;
  display: flex;
  align-items: center;
  gap: 10rpx;
}

.my-res-side__status-row.active {
  background: #edf3fb;
}

.my-res-side__dot {
  width: 12rpx;
  height: 12rpx;
  border-radius: 999rpx;
}

.my-res-side__status-label {
  color: #344a65;
  font-size: 24rpx;
  font-weight: 700;
  flex: 1;
}

.my-res-side__status-count {
  color: #73849a;
  font-size: 24rpx;
  font-weight: 700;
}

.my-res-main__thead {
  min-height: 62rpx;
  padding: 0 20rpx;
  display: grid;
  grid-template-columns: 2.1fr 1fr 0.8fr 0.7fr;
  align-items: center;
  color: #5f7088;
  font-size: 22rpx;
  font-weight: 700;
}

.my-res-main__empty {
  border-radius: 18rpx;
  background: rgba(255, 255, 255, 0.75);
  border: 1rpx solid rgba(197, 198, 207, 0.28);
  padding: 22rpx;
  color: #6f8098;
  font-size: 23rpx;
}

.my-res-main__row {
  margin-bottom: 12rpx;
  border-radius: 20rpx;
  background: rgba(255, 255, 255, 0.78);
  border-left: 5rpx solid #d9e2ed;
  min-height: 124rpx;
  padding: 0 18rpx;
  display: grid;
  grid-template-columns: 2.1fr 1fr 0.8fr 0.7fr;
  align-items: center;
}

.my-res-main__row.pending {
  border-left-color: #f3be2f;
}

.my-res-main__row.approved {
  border-left-color: #3cc6ea;
}

.my-res-main__row.completed {
  border-left-color: #b9c5d6;
}

.my-res-main__row.cancelled,
.my-res-main__row.rejected {
  border-left-color: #d13232;
}

.my-res-main__resource {
  display: flex;
  align-items: center;
  gap: 14rpx;
}

.my-res-main__icon {
  width: 62rpx;
  height: 62rpx;
  border-radius: 16rpx;
  background: #edf2f8;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #253b5b;
  font-size: 28rpx;
}

.my-res-main__name {
  color: #082248;
  font-size: 34rpx;
  line-height: 1.2;
  font-weight: 800;
}

.my-res-main__loc {
  margin-top: 4rpx;
  color: #64778e;
  font-size: 22rpx;
}

.my-res-main__date {
  color: #112d53;
  font-size: 34rpx;
  font-weight: 800;
}

.my-res-main__range {
  margin-top: 4rpx;
  color: #6a7b92;
  font-size: 22rpx;
}

.my-res-main__status-pill {
  min-height: 42rpx;
  border-radius: 999rpx;
  padding: 0 14rpx;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 20rpx;
  font-weight: 800;
}

.my-res-main__status-pill.pending {
  background: #fdeac3;
  color: #a97712;
}

.my-res-main__status-pill.approved {
  background: #d8f3fb;
  color: #0a7f9e;
}

.my-res-main__status-pill.completed {
  background: #eef2f7;
  color: #73849a;
}

.my-res-main__status-pill.cancelled,
.my-res-main__status-pill.rejected {
  background: #fde0e0;
  color: #bf2a2a;
}

.my-res-main__ops {
  display: flex;
  align-items: center;
  gap: 12rpx;
}

.my-res-main__detail {
  color: #1572a8;
  font-size: 24rpx;
  font-weight: 800;
}

.my-res-main__cancel {
  color: #c43636;
  font-size: 22rpx;
  font-weight: 700;
}

.my-res-main__pager {
  margin-top: 18rpx;
  display: flex;
  justify-content: center;
  gap: 8rpx;
}

.my-res-main__page-btn {
  width: 56rpx;
  height: 56rpx;
  border-radius: 14rpx;
  background: #eef2f7;
  color: #61738b;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24rpx;
  font-weight: 700;
}

.my-res-main__page-btn.active {
  background: #0a254c;
  color: #ffffff;
}

/* #ifndef H5 */
.my-res-page__shell {
  padding-left: 24rpx;
  padding-right: 24rpx;
}

.my-res-page__head {
  flex-direction: column;
  align-items: flex-start;
}

.my-res-page__layout {
  grid-template-columns: 1fr;
}

.my-res-main__thead {
  display: none;
}

.my-res-main__row {
  grid-template-columns: 1fr;
  gap: 10rpx;
  padding: 14rpx;
}
/* #endif */

/* #ifdef H5 */
@media screen and (min-width: 1500px) {
  .my-res-page__shell {
    padding-left: 56rpx;
    padding-right: 56rpx;
  }
}

@media screen and (max-width: 1140px) {
  .my-res-page__layout {
    grid-template-columns: 1fr;
  }
}

@media screen and (max-width: 820px) {
  .my-res-page__head-actions {
    width: 100%;
  }

  .my-res-page__new-btn {
    flex: 1;
  }
}
/* #endif */
</style>
