<template>
  <view class="site-footer">
    <view class="site-footer__inner">
      <view>
        <view class="site-footer__title">中央民族大学实验室系统</view>
        <view class="site-footer__sub">© 2026 中央民族大学实验室系统</view>
      </view>
      <view class="site-footer__links">
        <view class="site-footer__link">学校信息</view>
        <view class="site-footer__link">联系我们</view>
        <view class="site-footer__link">快速链接</view>
        <view class="site-footer__link">隐私政策</view>
      </view>
    </view>
  </view>
</template>

<script>
export default {
  name: 'SiteFooter'
}
</script>

<style lang="scss">
.site-footer {
  margin-top: auto;
  padding: 18rpx 32rpx 22rpx;
}

.site-footer__inner {
  border-top: 1rpx solid rgba(197, 198, 207, 0.45);
  padding-top: 18rpx;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 20rpx;
}

.site-footer__title {
  color: #1a2b4b;
  font-size: 28rpx;
  font-weight: 800;
}

.site-footer__sub {
  margin-top: 6rpx;
  color: #7a8796;
  font-size: 22rpx;
}

.site-footer__links {
  display: flex;
  gap: 22rpx;
  color: #7a8796;
  font-size: 22rpx;
}

@media screen and (min-width: 1500px) {
  .site-footer {
    padding-left: 56rpx;
    padding-right: 56rpx;
  }
}

@media screen and (max-width: 900px) {
  .site-footer__inner {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
