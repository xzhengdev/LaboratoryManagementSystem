<template>
  <view class="student-top-nav">
    <view class="student-top-nav__inner">
      <view class="student-top-nav__main">
        <view class="student-top-nav__brand" @click="go(routes.home)">
          <view class="student-top-nav__brand-badge">
            <image 
              class="student-top-nav__brand-mark" 
              src="/static/logo.png" 
              mode="aspectFill"
            />
          </view>
          <view class="student-top-nav__brand-text">实验室管理系统</view>
        </view>

        <view class="student-top-nav__links">
          <view
            v-for="item in navItems"
            :key="item.key"
            class="student-top-nav__link"
            :class="{ active: item.key === active }"
            @click="go(item.path)"
          >
            {{ item.title }}
          </view>
        </view>
      </view>

      <view class="student-top-nav__actions">
        <view class="student-top-nav__profile" @click="go(routes.profile)">
          <image
            v-if="profile.avatar_url"
            class="student-top-nav__avatar student-top-nav__avatar-img"
            :src="profile.avatar_url"
            mode="aspectFill"
          />
          <view v-else class="student-top-nav__avatar">{{ avatarText }}</view>
          <view class="student-top-nav__profile-text">{{ displayName }}</view>
        </view>
      </view>
    </view>
  </view>
</template>

<script>
import { openPage } from '../common/router'
import { getProfile } from '../common/session'
import { getUserTopNavByRole, routes } from '../config/navigation'

export default {
  props: {
    active: { type: String, default: 'home' }
  },
  data() {
    return {
      routes,
      navItems: [],
      profile: {}
    }
  },
  computed: {
    avatarText() {
      return (this.profile.real_name || this.profile.username || '用户').slice(0, 1)
    },
    displayName() {
      return this.profile.real_name || this.profile.username || '用户'
    }
  },
  created() {
    this.profile = getProfile()
    this.navItems = getUserTopNavByRole(this.profile.role)
  },
  methods: {
    go(path) {
      openPage(path)
    }
  }
}
</script>

<style lang="scss">
.student-top-nav {
  position: sticky;
  top: 0;
  z-index: 50;
  padding: 0;
  background: rgba(247, 249, 252, 0.72);
  backdrop-filter: blur(18px);
  border-bottom: 1rpx solid rgba(197, 198, 207, 0.22);
  box-shadow: 0 12rpx 30rpx rgba(8, 27, 58, 0.05);
}

.student-top-nav__inner {
  width: 100%;
  min-height: 108rpx;
  margin: 0;
  padding: 0 40rpx;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 32rpx;
  box-sizing: border-box;
}

.student-top-nav__main {
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 56rpx;
  flex: 1;
}

.student-top-nav__brand {
  display: flex;
  align-items: center;
  gap: 16rpx;
  min-width: 0;
  flex-shrink: 0;
}

.student-top-nav__brand-badge {
  width: 80rpx;
  height: 80rpx;
  padding: 7rpx;
  border-radius: 20rpx;
  background: #ffffff;
  border: 1rpx solid rgba(26, 43, 75, 0.1);
  box-shadow: 0 8rpx 22rpx rgba(8, 27, 58, 0.08);
  display: flex;
  align-items: center;
  justify-content: center;
  box-sizing: border-box;
  flex-shrink: 0;
}

.student-top-nav__brand-mark {
  width: 100%;
  height: 100%;
  border-radius: 14rpx;
  display: block;
}


.student-top-nav__brand-text {
  font-size: 32rpx;
  line-height: 1.15;
  font-weight: 800;
  letter-spacing: 0;
  color: #13263a;
  white-space: nowrap;
}

.student-top-nav__links {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: 44rpx;
  min-width: 0;
  flex-wrap: nowrap;
}

.student-top-nav__link {
  padding: 8rpx 8rpx;
  border-bottom: 4rpx solid transparent;
  color: #6f7b8c;
  font-size: 24rpx;
  font-weight: 600;
  letter-spacing: 1rpx;
}

.student-top-nav__link.active {
  color: #1a2b4b;
  border-color: #41befd;
}

.student-top-nav__actions {
  display: flex;
  align-items: center;
  justify-self: end;
}

.student-top-nav__profile {
  display: flex;
  align-items: center;
  gap: 14rpx;
}

.student-top-nav__avatar {
  width: 66rpx;
  height: 66rpx;
  border-radius: 50rpx;
  display: flex;
  align-items: center;
  justify-content: center;  
}
.student-top-nav__avatar-img {
  border: 1rpx solid rgba(16, 42, 73, 0.12);
  box-shadow: 0 6rpx 16rpx rgba(19, 45, 77, 0.12);
  object-fit: cover;
}

.student-top-nav__profile-text {
  font-size: 28rpx;
  font-weight: 700;
  color: #031635;
  max-width: 160rpx;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

@media screen and (min-width: 1500px) {
  .student-top-nav__inner {
    padding-left: 56rpx;
    padding-right: 56rpx;
  }
}

@media screen and (max-width: 860px) {
  .student-top-nav__links,
  .student-top-nav__profile-text {
    display: none;
  }

  .student-top-nav__main {
    gap: 20rpx;
  }

  .student-top-nav__inner {
    min-height: 88rpx;
    padding: 0 24rpx;
  }

  .student-top-nav__brand {
    gap: 12rpx;
  }

  .student-top-nav__brand-badge {
    width: 66rpx;
    height: 66rpx;
    padding: 6rpx;
    border-radius: 16rpx;
  }

  .student-top-nav__brand-text {
    font-size: 28rpx;
  }
}
</style>
