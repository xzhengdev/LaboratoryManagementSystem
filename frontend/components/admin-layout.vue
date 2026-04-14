<template>
  <!-- 管理控制台整体工作区容器 -->
  <view class="admin-workspace">
    <!-- 主区域：采用网格布局，分为侧边栏和内容区 -->
    <view class="admin-main">
      <!-- ==================== 侧边栏区域 ==================== -->
      <view class="admin-sidebar">
        <!-- 品牌/Logo区域 -->
        <view class="admin-brand">
          <view class="admin-brand__title">管理控制台</view>
          <view class="admin-brand__sub">实验室管理系统</view>
        </view>

        <!-- 动态菜单区域：根据用户角色从配置中获取菜单项 -->
        <view class="admin-menu">
          <view
            v-for="item in sidebarItems"
            :key="item.key"
            class="admin-menu-item"
            :class="{ active: active === item.key }"
            @click="go(item.path)"
          >
            <view class="admin-menu-item__title">{{ item.title }}</view>
          </view>
        </view>

        <!-- 侧边栏底部：退出登录按钮 -->
        <view class="admin-sidebar__bottom">
          <view class="admin-head-user admin-head-user--sidebar" @click="goProfile">
            <view class="admin-head-user__avatar">{{ avatarText }}</view>
            <view class="admin-head-user__meta">
              <view class="admin-head-user__name">{{ currentUser.real_name || '管理员' }}</view>
              <view class="admin-head-user__role">{{ roleText }}</view>
            </view>
          </view>
        </view>
      </view>

      <!-- ==================== 右侧内容区域 ==================== -->
      <view class="admin-content">
        <!-- 内容头部：标题、副标题、搜索框、用户信息 -->
        <view class="admin-content-head">
          <!-- 左侧标题组 -->
          <view class="admin-content-head__left">
            <view class="admin-content-head__title">{{ title }}</view>
            <view v-if="subtitle" class="admin-content-head__sub">{{ subtitle }}</view>
          </view>

        </view>

        <!-- 插槽：用于嵌入各个管理页面的具体内容（如用户列表、设备管理等） -->
        <slot />
      </view>
    </view>
  </view>
</template>

<script>
// 导入会话管理工具：获取用户信息
import { getProfile } from '../common/session'
// 导入路由跳转工具
import { openPage } from '../common/router'
// 导入导航配置：权限校验、菜单生成、角色文本等
import {
  canAccessAdminRoute,
  getAdminMenusByRole,
  getDefaultAdminPath,
  getRoleText,
  routes
} from '../config/navigation'

export default {
  // 父组件可传入的属性
  props: {
    title: { type: String, default: '' },      // 页面主标题
    subtitle: { type: String, default: '' },   // 页面副标题
    active: { type: String, default: '' }      // 当前激活菜单项的key
  },
  data() {
    return {
      currentUser: {}  // 存储当前登录用户信息
    }
  },
  computed: {
    // 计算属性：用户角色文本（如“超级管理员”、“普通管理员”）
    roleText() {
      return getRoleText(this.currentUser.role)
    },
    // 计算属性：头像文本（取真实姓名或“Admin”的首字母大写）
    avatarText() {
      const source = this.currentUser.real_name || 'Admin'
      return source.slice(0, 1)
    },
    // 计算属性：根据用户角色动态生成侧边栏菜单项
    sidebarItems() {
      return getAdminMenusByRole(this.currentUser.role).map((item) => ({
        key: item.key,
        title: item.title,
        path: item.path
      }))
    }
  },
  // 组件实例创建完成后执行
  created() {
    this.currentUser = getProfile()   // 获取当前登录用户信息
    this.ensureRoutePermission()      // 校验当前路由权限
  },
  methods: {
    // 方法：确保用户有权限访问当前页面，若无权限则跳转至默认管理页
    ensureRoutePermission() {
      // 获取当前页面栈及当前页面路径
      const pages = getCurrentPages()
      const current = pages && pages.length ? pages[pages.length - 1] : null
      const routePath = current && current.route ? `/${current.route}` : ''
      if (!routePath) return
      // 调用权限校验函数，若无权访问
      if (canAccessAdminRoute(this.currentUser.role, routePath)) return

      // 提示无权限并跳转到该角色默认的管理页面
      uni.showToast({ title: 'No permission for this page', icon: 'none' })
      openPage(getDefaultAdminPath(this.currentUser.role), { replace: true })
    },
    // 方法：菜单点击跳转，替换当前页面历史记录
    go(path) {
      openPage(path, { replace: true })
    },
    goProfile() {
      openPage(routes.adminProfile, { replace: true })
    }
  }
}
</script>

<style lang="scss">
// 全局样式（无 scoped，影响所有子组件，作为布局基础样式）

// 工作区整体背景
.admin-workspace {
  height: 100vh;
  background: #eef2f7;
  overflow: hidden;
}

// 主区域：两栏网格布局，左侧侧边栏固定宽度，右侧自适应
.admin-main {
  height: 100vh;
  display: grid;
  grid-template-columns: 330rpx minmax(0, 1fr);
}

// ----- 侧边栏样式 -----
.admin-sidebar {
  border-right: 1rpx solid #dde5ef;
  background: #f3f6fb;
  padding: 28rpx 20rpx 26rpx;
  box-sizing: border-box;
  display: flex;
  flex-direction: column; // 垂直排列，底部利用 margin-top:auto 将退出按钮推至底部
  height: 100vh;
  overflow: hidden;
}

.admin-brand {
  margin-bottom: 30rpx;
  padding: 6rpx 10rpx;
  flex-shrink: 0;
}
.admin-brand__title {
  font-size: 42rpx;
  font-weight: 800;
  color: #182e4e;
}
.admin-brand__sub {
  margin-top: 8rpx;
  font-size: 22rpx;
  color: #6f8096;
}

.admin-menu {
  flex: 1;
  min-height: 0;
  display: grid;
  gap: 8rpx;
  align-content: start;
  overflow-y: auto;
}
.admin-menu-item {
  height: 76rpx;
  border-radius: 16rpx;
  padding: 0 18rpx;
  display: flex;
  align-items: center;
  color: #42546e;
  // 激活状态样式
  &.active {
    background: #ffffff;
    color: #0f2342;
    box-shadow: 0 8rpx 20rpx rgba(15, 35, 66, 0.08);
  }
}
.admin-menu-item__title {
  font-size: 30rpx;
  font-weight: 700;
}

// 侧边栏底部：将退出按钮推到底部
.admin-sidebar__bottom {
  margin-top: auto;
  padding: 26rpx 8rpx 8rpx;
  flex-shrink: 0;
}

// ----- 右侧内容区域样式 -----
.admin-content {
  padding: 22rpx 24rpx 28rpx;
  box-sizing: border-box;
  height: 100vh;
  overflow-y: auto;
}
.admin-content-head {
  margin-bottom: 18rpx;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 18rpx;
}
.admin-content-head__title {
  font-size: 56rpx;
  font-weight: 800;
  color: #152d4c;
}
.admin-content-head__sub {
  margin-top: 2rpx;
  font-size: 26rpx;
  color: #1ab6cc;
  font-weight: 700;
}
.admin-head-user {
  min-width: 270rpx;
  height: 74rpx;
  border-radius: 18rpx;
  padding: 5rpx 20rpx;
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #ffffff;
  border: 1rpx solid #dfe7f2;
}
.admin-head-user__meta {
  min-width: 0;
}
.admin-head-user__name {
  color: #1b2f4d;
  font-size: 24rpx;
  font-weight: 700;
}
.admin-head-user__role {
  margin-top: 2rpx;
  color: #71829a;
  font-size: 20rpx;
}
.admin-head-user__avatar {
  width: 46rpx;
  height: 46rpx;
  border-radius: 999rpx;
  background: linear-gradient(135deg, #0e2c57, #1f6ea8);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22rpx;
  font-weight: 700;
  margin-left: 10rpx;
}
.admin-head-user--sidebar {
  min-width: 0;
  width: 100%;
  box-sizing: border-box;
  min-height: 76rpx;
  border-radius: 0;
  padding: 0;
  background: transparent;
  border: none;
  box-shadow: none;
  color: #0f2342;
  justify-content: flex-start;
  gap: 14rpx;
}

.admin-head-user--sidebar .admin-head-user__name {
  font-size: 32rpx;
}

.admin-head-user--sidebar .admin-head-user__role {
  font-size: 22rpx;
  color: #6f8096;
}

.admin-head-user--sidebar .admin-head-user__avatar {
  width: 70rpx;
  height: 70rpx;
  margin-left: 0;
  margin-right: 4rpx;
  font-size: 30rpx;
}

// ----- 响应式适配：屏幕宽度小于1200px时调整布局 -----
@media screen and (max-width: 1200px) {
  .admin-main {
    grid-template-columns: 260rpx minmax(0, 1fr); // 缩小侧边栏宽度
  }
  .admin-content-head {
    flex-direction: column;   // 头部改为垂直排列
    align-items: flex-start;
  }

}
</style>
