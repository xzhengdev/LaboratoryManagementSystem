<template>
  <view>
    <user-top-nav active="agent" />
    <view class="page">
      <view class="page-shell two-col">
        <page-hero
          kicker="自然语言助手"
          title="Agent 智能问答窗口"
          subtitle="支持查询可预约实验室、我的预约、实验室排期以及统计概览，适合演示系统中的智能交互能力。"
        />

        <view class="card">
          <view class="title">演示说明</view>
          <view class="subtitle">右下角浮窗已经加载，你也可以在当前页面直接打开并输入自然语言。</view>
          <view class="subtitle">推荐问题：帮我看看今天可预约的实验室 / 查看我的预约 / 给我看统计概览</view>
          <view class="actions" style="margin-top:20rpx;">
            <view class="btn btn-light" @click="go(routes.labs)">去看实验室</view>
            <view class="btn btn-light" @click="go(routes.myReservations)">查看我的预约</view>
          </view>
        </view>
      </view>

      <agent-chat-window :default-visible="true" />
      <portal-footer />
    </view>
  </view>
</template>

<script>
import AgentChatWindow from '../../components/agent-chat-window.vue'
import PageHero from '../../components/page-hero.vue'
import PortalFooter from '../../components/portal-footer.vue'
import UserTopNav from '../../components/user-top-nav.vue'
import { requireLogin } from '../../common/guard'
import { openPage } from '../../common/router'
import { routes } from '../../config/navigation'

export default {
  components: { AgentChatWindow, PageHero, PortalFooter, UserTopNav },
  data() {
    return { routes }
  },
  onShow() {
    if (!requireLogin()) return
    // #ifdef H5
    uni.hideTabBar()
    // #endif
  },
  methods: {
    go(path) {
      openPage(path)
    }
  }
}
</script>
