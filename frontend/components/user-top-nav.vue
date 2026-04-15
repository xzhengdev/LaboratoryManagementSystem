<template>
  <!-- #ifdef H5 -->
  <view class="portal-nav">
    <view class="portal-nav__inner">
      <view class="portal-brand" @click="go(routes.home)">
        <view class="portal-brand__mark">LAB</view>
        <view>
          <view class="portal-brand__title">璺ㄦ牎鍖哄疄楠屽棰勭害骞冲彴</view>
          <view class="portal-brand__sub">PC 鐢ㄦ埛鍓嶅彴</view>
        </view>
      </view>

      <view class="portal-links">
        <view
          v-for="item in navs"
          :key="item.key"
          class="portal-link"
          :class="{ active: item.key === active }"
          @click="go(item.path)"
        >
          {{ item.title }}
        </view>
      </view>

      <view class="portal-actions">
        <view class="portal-user" @click="go(routes.profile)">
          <image
            v-if="profile.avatar_url"
            class="portal-user__avatar portal-user__avatar-img"
            :src="profile.avatar_url"
            mode="aspectFill"
          />
          <view v-else class="portal-user__avatar">{{ avatarText }}</view>
          <view class="portal-user__name">{{ profile.real_name || profile.username || '访客' }}</view>
        </view>
        <view v-if="isAdmin" class="btn btn-light portal-admin" @click="goAdminWorkspace">绠＄悊鍚庡彴</view>
      </view>
    </view>
  </view>
  <!-- #endif -->
</template>

<script>
import { getProfile, isAdminRole } from '../common/session'
import { openPage } from '../common/router'
import { getDefaultAdminPath, getUserTopNavByRole, routes } from '../config/navigation'

export default {
  props: {
    active: { type: String, default: 'home' }
  },
  data() {
    return {
      navs: [],
      routes,
      profile: {}
    }
  },
  computed: {
    avatarText() {
      return (this.profile.real_name || this.profile.username || '访客').slice(0, 1)
    },
    isAdmin() {
      return isAdminRole(this.profile.role)
    }
  },
  created() {
    this.profile = getProfile()
    this.navs = getUserTopNavByRole(this.profile.role)
  },
  methods: {
    go(path) {
      openPage(path)
    },
    goAdminWorkspace() {
      openPage(getDefaultAdminPath(this.profile.role), { replace: true })
    }
  }
}
</script>

<style lang="scss">
.portal-nav {
  position: sticky;
  top: 0;
  z-index: 40;
  padding: 20rpx 32rpx 0;
  background: linear-gradient(180deg, rgba(247, 249, 252, 0.96), rgba(247, 249, 252, 0.72));
  backdrop-filter: blur(10px);
}

.portal-nav__inner {
  max-width: 1440rpx;
  margin: 0 auto;
  display: grid;
  grid-template-columns: auto 1fr auto;
  align-items: center;
  gap: 28rpx;
  padding: 18rpx 26rpx;
  border-radius: 28rpx;
  background: rgba(255, 255, 255, 0.92);
  border: 1rpx solid #E4EBF5;
  box-shadow: 0 14rpx 44rpx rgba(47, 128, 237, 0.08);
}

.portal-brand {
  display: flex;
  align-items: center;
  gap: 18rpx;
}

.portal-brand__mark {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 82rpx;
  height: 82rpx;
  border-radius: 24rpx;
  background: linear-gradient(135deg, #2F80ED, #6AA9FF);
  color: #fff;
  font-weight: 700;
  letter-spacing: 2rpx;
}

.portal-brand__title {
  font-size: 30rpx;
  font-weight: 700;
  color: #1F2D3D;
}

.portal-brand__sub {
  margin-top: 6rpx;
  font-size: 22rpx;
  color: #7A8796;
}

.portal-links {
  display: flex;
  justify-content: center;
  gap: 16rpx;
}

.portal-link {
  padding: 14rpx 22rpx;
  border-radius: 999rpx;
  color: #5B6B7F;
  font-size: 25rpx;
}

.portal-link.active {
  background: #EEF5FF;
  color: #2F80ED;
  font-weight: 600;
}

.portal-actions {
  display: flex;
  align-items: center;
  gap: 16rpx;
}
.portal-user {
  display: flex;
  align-items: center;
  gap: 12rpx;
}
.portal-user__avatar {
  width: 58rpx;
  height: 58rpx;
  border-radius: 16rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #1a2b4b, #2c7da0);
  color: #ffffff;
  font-weight: 700;
  font-size: 24rpx;
}
.portal-user__avatar-img {
  border: 1rpx solid rgba(19, 45, 77, 0.12);
  box-shadow: 0 6rpx 16rpx rgba(19, 45, 77, 0.12);
  object-fit: cover;
}
.portal-user__name {
  max-width: 160rpx;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: #132d4d;
  font-size: 24rpx;
  font-weight: 700;
}

.portal-admin {
  padding-left: 24rpx;
  padding-right: 24rpx;
}
</style>


