<template>
  <admin-layout title="个人资料" subtitle="管理账户信息与登录状态" active="">
    <view class="admin-profile-grid">
      <view class="card">
        <view class="admin-profile-head">
          <view class="admin-profile-avatar">{{ avatarText }}</view>
          <view>
            <view class="admin-profile-name">{{ profile.real_name || profile.username || '管理员' }}</view>
            <view class="admin-profile-role">{{ roleText }}</view>
          </view>
        </view>

        <view class="admin-profile-fields">
          <view class="admin-profile-row">
            <text class="admin-profile-label">用户名</text>
            <text class="admin-profile-value">{{ profile.username || '--' }}</text>
          </view>
          <view class="admin-profile-row">
            <text class="admin-profile-label">所属校区</text>
            <text class="admin-profile-value">{{ profile.campus_name || '全校区' }}</text>
          </view>
          <view class="admin-profile-row">
            <text class="admin-profile-label">账号状态</text>
            <text class="admin-profile-value">{{ statusText }}</text>
          </view>
        </view>
      </view>

      <view class="card">
        <view class="admin-profile-card-title">账户操作</view>
        <view class="admin-profile-actions">
          <view class="admin-btn admin-btn-primary" @click="goDashboard">返回管理工作台</view>
          <view class="admin-btn admin-btn-danger" @click="logout">退出登录</view>
        </view>
      </view>
    </view>
  </admin-layout>
</template>

<script>
import AdminLayout from '../../components/admin-layout.vue'
import { clearSession, getProfile } from '../../common/session'
import { requireLogin } from '../../common/guard'
import { openPage } from '../../common/router'
import { getDefaultAdminPath, getRoleText, routes } from '../../config/navigation'

export default {
  components: { AdminLayout },
  data() {
    return {
      profile: {}
    }
  },
  computed: {
    roleText() {
      return getRoleText(this.profile.role)
    },
    statusText() {
      const map = {
        active: '正常',
        disabled: '停用',
        pending: '待处理',
        approved: '已通过',
        rejected: '已驳回'
      }
      const key = String(this.profile.status || '').trim().toLowerCase()
      return map[key] || '未知'
    },
    avatarText() {
      const source = this.profile.real_name || this.profile.username || '管理员'
      return source.slice(0, 1)
    }
  },
  onShow() {
    if (!requireLogin()) return
    this.profile = getProfile()
  },
  methods: {
    goDashboard() {
      openPage(getDefaultAdminPath(this.profile.role), { replace: true })
    },
    logout() {
      clearSession()
      openPage(routes.login, { replace: true })
    }
  }
}
</script>

<style lang="scss">
.admin-profile-grid {
  display: grid;
  grid-template-columns: 1.3fr 0.7fr;
  gap: 16rpx;
}

.admin-profile-head {
  display: flex;
  align-items: center;
  gap: 16rpx;
}

.admin-profile-avatar {
  width: 84rpx;
  height: 84rpx;
  border-radius: 999rpx;
  background: linear-gradient(135deg, #0e2c57, #1f6ea8);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 32rpx;
  font-weight: 700;
}

.admin-profile-name {
  font-size: 34rpx;
  color: #112b4d;
  font-weight: 800;
}

.admin-profile-role {
  margin-top: 4rpx;
  font-size: 22rpx;
  color: #667a93;
}

.admin-profile-fields {
  margin-top: 18rpx;
  display: grid;
  gap: 10rpx;
}

.admin-profile-row {
  min-height: 64rpx;
  border-radius: 14rpx;
  border: 1rpx solid #e4ebf5;
  padding: 0 16rpx;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.admin-profile-label {
  font-size: 22rpx;
  color: #6c7f95;
}

.admin-profile-value {
  font-size: 23rpx;
  color: #1b2f4d;
  font-weight: 700;
}

.admin-profile-card-title {
  font-size: 28rpx;
  font-weight: 800;
  color: #142d4e;
}

.admin-profile-actions {
  margin-top: 16rpx;
  display: grid;
  gap: 12rpx;
}

.admin-btn {
  height: 68rpx;
  border-radius: 14rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24rpx;
  font-weight: 700;
}

.admin-btn-primary {
  background: #edf3fb;
  color: #14335b;
}

.admin-btn-danger {
  background: linear-gradient(135deg, #fff1f1, #ffdede);
  border: 1rpx solid #f4baba;
  color: #b43333;
}

@media screen and (max-width: 1200px) {
  .admin-profile-grid {
    grid-template-columns: 1fr;
  }
}
</style>
