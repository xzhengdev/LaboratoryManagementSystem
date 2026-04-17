<template>
  
  <view class="portal-footer">
    <view class="portal-footer__inner">
      <view>
        <view class="portal-footer__title">支持跨校区协作的分布式实验室管理系统</view>
        <view class="portal-footer__sub">统一展示实验室资源、预约流程、审批链路与统计概览</view>
      </view>
      <view class="portal-footer__links">
        <view class="portal-footer__link" @click="go(routes.campuses)">校区资源</view>
        <view class="portal-footer__link" @click="go(routes.labs)">实验室预约</view>
        <view class="portal-footer__link" @click="go(routes.myReservations)">我的预约</view>
        <view class="portal-footer__link" @click="go(routes.agent)">智能助手</view>
      </view>
    </view>
  </view>
  
</template>

<script>
import { openPage } from '../common/router'
import { routes } from '../config/navigation'

export default {
  data() {
    return { routes }
  },
  methods: {
    go(path) {
      openPage(path)
    }
  }
}
</script>

<style lang="scss">
.portal-footer {
  margin-top: 48rpx;
  padding: 0 32rpx 36rpx;
}

.portal-footer__inner {
  max-width: 1440rpx;
  margin: 0 auto;
  display: flex;
  justify-content: space-between;
  gap: 28rpx;
  padding: 28rpx 30rpx;
  border-radius: 28rpx;
  background: #fff;
  border: 1rpx solid #E4EBF5;
  box-shadow: 0 12rpx 36rpx rgba(47, 128, 237, 0.06);
}

.portal-footer__title {
  font-size: 28rpx;
  font-weight: 700;
  color: #1F2D3D;
}

.portal-footer__sub {
  margin-top: 8rpx;
  font-size: 22rpx;
  color: #7A8796;
}

.portal-footer__links {
  display: flex;
  align-items: center;
  gap: 18rpx;
  flex-wrap: wrap;
}

.portal-footer__link {
  color: #2F80ED;
  font-size: 24rpx;
}
</style>
