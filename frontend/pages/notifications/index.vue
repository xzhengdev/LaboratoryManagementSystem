<template>
  <view class="notifications-page">
    <student-top-nav active="notifications" />

    <view class="notifications-shell">
      <view class="notifications-head">
        <view class="notifications-title">消息提醒</view>
        <view class="notifications-sub">查看日报审核结果等业务消息，避免遗漏管理员反馈。</view>
      </view>

      <view class="card toolbar">
        <view class="toolbar-left">
          <view class="badge">未读 {{ unreadCount }}</view>
        </view>
        <view class="toolbar-right">
          <view class="pill" @click="toggleUnreadOnly">{{ unreadOnly ? '显示全部' : '仅看未读' }}</view>
          <view class="pill pill-primary" @click="markAllRead">全部已读</view>
          <view class="pill" @click="reload">刷新</view>
        </view>
      </view>

      <view class="card">
        <view v-if="!list.length" class="empty-text">暂无消息</view>
        <view
          v-for="item in list"
          :key="item.id"
          class="notify-item"
          :class="{ unread: !item.is_read }"
          @click="openDetail(item)"
        >
          <view class="notify-head">
            <view class="notify-title">{{ item.title || '系统消息' }}</view>
            <view class="notify-time">{{ timeText(item.created_at) }}</view>
          </view>
          <view class="notify-content">{{ item.content || '--' }}</view>
          <view class="notify-foot">
            <view :class="levelClass(item.level)">{{ levelText(item.level) }}</view>
            <view v-if="!item.is_read" class="notify-dot"></view>
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

export default {
  components: { StudentTopNav },
  data() {
    return {
      list: [],
      unreadCount: 0,
      unreadOnly: false
    }
  },
  async onShow() {
    if (!requireLogin()) return
    await this.reload()
  },
  methods: {
    timeText(value) {
      if (!value) return '--'
      return String(value).replace('T', ' ').slice(0, 19)
    },
    levelText(level) {
      const map = {
        success: '通过',
        warning: '驳回',
        info: '通知'
      }
      return map[level] || '通知'
    },
    levelClass(level) {
      if (level === 'success') return 'tag success'
      if (level === 'warning') return 'tag warning'
      return 'tag'
    },
    async reload() {
      const params = this.unreadOnly ? { unread_only: 1 } : {}
      const [rows, unread] = await Promise.all([
        api.notifications(params),
        api.notificationUnreadCount()
      ])
      this.list = Array.isArray(rows) ? rows : []
      this.unreadCount = Number(unread?.unread_count || 0)
    },
    toggleUnreadOnly() {
      this.unreadOnly = !this.unreadOnly
      this.reload()
    },
    async markAllRead() {
      await api.markAllNotificationsRead()
      uni.showToast({ title: '已全部标记为已读', icon: 'success' })
      await this.reload()
    },
    async openDetail(item) {
      if (!item || !item.id) return
      if (!item.is_read) {
        await api.markNotificationRead(item.id)
        item.is_read = true
        this.unreadCount = Math.max(0, Number(this.unreadCount || 0) - 1)
      }
      uni.showModal({
        title: item.title || '消息详情',
        content: item.content || '--',
        showCancel: false
      })
    }
  }
}
</script>

<style lang="scss">
.notifications-page {
  min-height: 100vh;
  background: #eef4fb;
}

.notifications-shell {
  padding: 24rpx 28rpx 40rpx;
}

.notifications-head {
  margin-bottom: 16rpx;
}

.notifications-title {
  font-size: 54rpx;
  font-weight: 800;
  color: #173252;
}

.notifications-sub {
  margin-top: 10rpx;
  color: #60738e;
  font-size: 24rpx;
}

.card {
  background: #fff;
  border: 1rpx solid #deebf8;
  border-radius: 18rpx;
  padding: 18rpx;
  margin-bottom: 16rpx;
}

.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12rpx;
}

.toolbar-right {
  display: flex;
  align-items: center;
  gap: 8rpx;
}

.badge {
  min-height: 42rpx;
  border-radius: 999rpx;
  padding: 0 16rpx;
  display: inline-flex;
  align-items: center;
  background: #e8f3ff;
  color: #265986;
  font-size: 22rpx;
  font-weight: 700;
}

.pill {
  padding: 0 12rpx;
  height: 44rpx;
  border-radius: 12rpx;
  border: 1rpx solid #d9e4f2;
  color: #476183;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: #fff;
  font-size: 22rpx;
}

.pill-primary {
  border-color: #a9d3e5;
  color: #0d749e;
  background: #eef8fd;
}

.empty-text {
  color: #7a8ca3;
  font-size: 22rpx;
}

.notify-item {
  margin-top: 12rpx;
  padding: 14rpx;
  border-radius: 12rpx;
  border: 1rpx solid #e3edf9;
  background: #f8fbff;
}

.notify-item.unread {
  border-color: #b8daf2;
  background: #f0f8ff;
}

.notify-head {
  display: flex;
  justify-content: space-between;
  gap: 12rpx;
}

.notify-title {
  color: #163252;
  font-size: 25rpx;
  font-weight: 700;
}

.notify-time {
  color: #67809f;
  font-size: 20rpx;
}

.notify-content {
  margin-top: 8rpx;
  color: #2f4865;
  font-size: 22rpx;
  line-height: 1.6;
}

.notify-foot {
  margin-top: 10rpx;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.tag {
  min-height: 36rpx;
  padding: 0 10rpx;
  border-radius: 999rpx;
  background: #ecf1f8;
  color: #566f8f;
  font-size: 20rpx;
  display: inline-flex;
  align-items: center;
}

.tag.success {
  background: #e8fbf1;
  color: #0e8a4f;
}

.tag.warning {
  background: #fff2df;
  color: #ad6f00;
}

.notify-dot {
  width: 16rpx;
  height: 16rpx;
  border-radius: 999rpx;
  background: #3f92c7;
}

@media (max-width: 860px) {
  .notifications-shell {
    padding: 14rpx 12rpx 24rpx;
  }

  .notifications-title {
    font-size: 42rpx;
  }

  .toolbar {
    flex-direction: column;
    align-items: stretch;
  }

  .toolbar-right {
    flex-wrap: wrap;
  }
}
</style>
