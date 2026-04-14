<template>
  <view class="admin-workspace">
    <view class="admin-topbar">
      <view class="admin-topbar__left">
        <view class="admin-brand">
          <view class="admin-brand__mark">LAB</view>
          <view>
            <view class="admin-brand__title">分布式实验室管理后台</view>
            <view class="admin-brand__sub">支持跨校区协作的统一管理工作台</view>
          </view>
        </view>
      </view>

      <view class="admin-topbar__center">
        <view class="admin-pill">{{ currentCampusName }}</view>
        <view class="admin-pill">通知 {{ noticeCount }}</view>
      </view>

      <view class="admin-topbar__right">
        <view class="admin-user">
          <view class="admin-user__name">{{ currentUser.real_name || '管理员' }}</view>
          <view class="admin-user__role">{{ roleText }}</view>
        </view>
        <view class="btn btn-light admin-topbar__btn" @click="goUserHome">前台首页</view>
        <view class="btn btn-light admin-topbar__btn" @click="logout">退出登录</view>
      </view>
    </view>

    <view class="admin-main">
      <view class="admin-sidebar">
        <view class="admin-sidebar__scroll">
          <view v-for="group in menuGroups" :key="group.group" class="admin-menu-group">
            <view class="admin-menu-group__title">{{ group.group }}</view>
            <view
              v-for="item in group.items"
              :key="item.path"
              class="admin-menu-item"
              :class="{ active: active === item.key }"
              @click="go(item.path)"
            >
              <view class="admin-menu-item__title">{{ item.title }}</view>
              <view class="admin-menu-item__sub">{{ item.desc }}</view>
            </view>
          </view>
        </view>
      </view>

      <view class="admin-content">
        <view class="admin-page-head">
          <view>
            <view class="admin-page-head__kicker">后台工作区</view>
            <view class="admin-page-head__title">{{ title }}</view>
            <view class="admin-page-head__sub">{{ subtitle }}</view>
          </view>
        </view>

        <slot />
      </view>
    </view>
  </view>
</template>

<script>
import { clearSession, getProfile } from '../common/session'
import { openPage } from '../common/router'
import { getAdminMenuGroups, getRoleText, routes } from '../config/navigation'

export default {
  props: {
    title: { type: String, default: '' },
    subtitle: { type: String, default: '' },
    active: { type: String, default: '' }
  },
  data() {
    return {
      currentUser: {}
    }
  },
  computed: {
    menuGroups() {
      return getAdminMenuGroups()
    },
    currentCampusName() {
      return this.currentUser.campus_name || '全局视角'
    },
    roleText() {
      return getRoleText(this.currentUser.role)
    },
    noticeCount() {
      return this.active === 'approvals' ? 3 : 2
    }
  },
  created() {
    this.currentUser = getProfile()
  },
  methods: {
    go(path) {
      openPage(path, { replace: true })
    },
    goUserHome() {
      openPage(routes.home)
    },
    logout() {
      clearSession()
      openPage(routes.login, { replace: true })
    }
  }
}
</script>

<style lang="scss">
.admin-workspace {
  min-height: 100vh;
  background: #F4F7FB;
}

.admin-topbar {
  position: sticky;
  top: 0;
  z-index: 60;
  height: 96rpx;
  padding: 0 28rpx;
  display: grid;
  grid-template-columns: auto 1fr auto;
  align-items: center;
  gap: 24rpx;
  background: rgba(255, 255, 255, 0.96);
  border-bottom: 1rpx solid #E4EBF5;
  backdrop-filter: blur(10px);
}

.admin-topbar__left,
.admin-topbar__center,
.admin-topbar__right {
  display: flex;
  align-items: center;
  gap: 16rpx;
}

.admin-topbar__center {
  justify-content: center;
}

.admin-topbar__right {
  justify-content: flex-end;
}

.admin-brand {
  display: flex;
  align-items: center;
  gap: 16rpx;
}

.admin-brand__mark {
  width: 64rpx;
  height: 64rpx;
  border-radius: 18rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #2F80ED, #6AA9FF);
  color: #fff;
  font-weight: 700;
}

.admin-brand__title {
  font-size: 28rpx;
  font-weight: 700;
  color: #1F2D3D;
}

.admin-brand__sub {
  margin-top: 4rpx;
  font-size: 20rpx;
  color: #7A8796;
}

.admin-pill {
  padding: 10rpx 18rpx;
  border-radius: 999rpx;
  background: #EEF5FF;
  color: #2F80ED;
  font-size: 22rpx;
}

.admin-user {
  text-align: right;
}

.admin-user__name {
  font-size: 24rpx;
  font-weight: 600;
  color: #1F2D3D;
}

.admin-user__role {
  margin-top: 4rpx;
  font-size: 20rpx;
  color: #7A8796;
}

.admin-topbar__btn {
  padding-left: 22rpx;
  padding-right: 22rpx;
}

.admin-main {
  min-height: calc(100vh - 96rpx);
  display: grid;
  grid-template-columns: 280rpx minmax(0, 1fr);
}

.admin-sidebar {
  background: #FFFFFF;
  border-right: 1rpx solid #E4EBF5;
}

.admin-sidebar__scroll {
  position: sticky;
  top: 96rpx;
  height: calc(100vh - 96rpx);
  overflow-y: auto;
  padding: 24rpx 20rpx 28rpx;
  box-sizing: border-box;
}

.admin-menu-group + .admin-menu-group {
  margin-top: 24rpx;
}

.admin-menu-group__title {
  margin-bottom: 12rpx;
  padding: 0 12rpx;
  font-size: 20rpx;
  color: #7A8796;
}

.admin-menu-item {
  padding: 18rpx 16rpx;
  border-radius: 18rpx;
  transition: all 180ms cubic-bezier(0.16, 1, 0.3, 1);
}

.admin-menu-item + .admin-menu-item {
  margin-top: 8rpx;
}

.admin-menu-item.active {
  background: #EEF5FF;
}

.admin-menu-item.active .admin-menu-item__title,
.admin-menu-item.active .admin-menu-item__sub {
  color: #2F80ED;
}

.admin-menu-item__title {
  font-size: 26rpx;
  font-weight: 600;
  color: #1F2D3D;
}

.admin-menu-item__sub {
  margin-top: 8rpx;
  font-size: 22rpx;
  color: #7A8796;
  line-height: 1.6;
}

.admin-content {
  padding: 28rpx;
  box-sizing: border-box;
}

.admin-page-head {
  margin-bottom: 24rpx;
  padding: 26rpx 28rpx;
  border-radius: 24rpx;
  background: linear-gradient(135deg, #FFFFFF, #F7FAFF);
  border: 1rpx solid #E4EBF5;
}

.admin-page-head__kicker {
  display: inline-flex;
  padding: 8rpx 14rpx;
  border-radius: 999rpx;
  background: #EEF5FF;
  color: #2F80ED;
  font-size: 20rpx;
}

.admin-page-head__title {
  margin-top: 14rpx;
  font-size: 40rpx;
  font-weight: 700;
  color: #1F2D3D;
}

.admin-page-head__sub {
  margin-top: 8rpx;
  font-size: 24rpx;
  color: #6A7A90;
}
</style>
