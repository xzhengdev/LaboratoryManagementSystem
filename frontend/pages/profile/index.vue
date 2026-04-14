<template>
  <view>
    <user-top-nav active="profile" />
    <view class="page">
      <view class="page-shell two-col">
        <view>
          <page-hero
            kicker="个人中心"
            :title="profile.real_name || '未登录用户'"
            :subtitle="`${profile.username || '未绑定账号'} · ${roleText} · ${profile.campus_name || '全校区'}`"
          />

          <!-- #ifdef H5 -->
          <view class="card">
            <view class="title">常用入口</view>
            <view class="portal-profile-links">
              <view class="pill" @click="go(routes.campuses)">查看校区资源</view>
              <view class="pill" @click="go(routes.labs)">去预约实验室</view>
              <view class="pill" @click="go(routes.agent)">打开智能助手</view>
            </view>
          </view>
          <!-- #endif -->
        </view>

        <view class="card">
          <view class="field"><text class="label">手机号</text><view class="input">{{ profile.phone || '未填写' }}</view></view>
          <view class="field"><text class="label">邮箱</text><view class="input">{{ profile.email || '未填写' }}</view></view>
          <view class="field"><text class="label">账号状态</text><status-tag :status="profile.status === 'active' ? 'active' : 'disabled'" /></view>
          <view class="actions">
            <view class="btn btn-light" @click="go(routes.myReservations)">查看我的预约</view>
            <view class="btn" @click="go(routes.agent)">打开智能助手</view>
          </view>
        </view>
      </view>

      <portal-footer />
    </view>
  </view>
</template>

<script>
import { getProfile } from '../../common/session'
import { requireLogin } from '../../common/guard'
import { openPage } from '../../common/router'
import { getRoleText, routes } from '../../config/navigation'
import PageHero from '../../components/page-hero.vue'
import PortalFooter from '../../components/portal-footer.vue'
import StatusTag from '../../components/status-tag.vue'
import UserTopNav from '../../components/user-top-nav.vue'

export default {
  components: { PageHero, PortalFooter, StatusTag, UserTopNav },
  data() {
    return {
      profile: {},
      routes
    }
  },
  computed: {
    roleText() {
      return getRoleText(this.profile.role)
    }
  },
  onShow() {
    if (!requireLogin()) return
    // #ifdef H5
    uni.hideTabBar()
    // #endif
    this.profile = getProfile()
  },
  methods: {
    go(path) {
      openPage(path)
    }
  }
}
</script>

<style lang="scss">
.portal-profile-links {
  margin-top: 20rpx;
  display: flex;
  gap: 14rpx;
  flex-wrap: wrap;
}
</style>
