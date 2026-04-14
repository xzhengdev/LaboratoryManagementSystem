<template>
  <view class="card hero-card page-hero">
    <view class="page-hero__main">
      <view v-if="kicker" class="hero-kicker">{{ kicker }}</view>
      <view class="title">{{ title }}</view>
      <view v-if="subtitle" class="subtitle light-text">{{ subtitle }}</view>
    </view>
    <view v-if="$slots.actions" class="page-hero__actions">
      <slot name="actions" />
    </view>
  </view>
</template>

<script>
export default {
  props: {
    // 将页面顶部的品牌语、主标题和副标题统一成同一组件，
    // 可以让小程序/H5/PC 页面在视觉上保持一致，也便于后续整体换风格。
    kicker: { type: String, default: '' },
    title: { type: String, default: '' },
    subtitle: { type: String, default: '' }
  }
}
</script>

<style lang="scss">
.page-hero {
  display: flex;
  justify-content: space-between;
  gap: 24rpx;
  align-items: flex-start;
}

.page-hero__main {
  flex: 1;
  min-width: 0;
}

.page-hero__actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 16rpx;
}

/* #ifdef H5 */
@media screen and (max-width: 959px) {
  .page-hero {
    flex-direction: column;
  }

  .page-hero__actions {
    justify-content: flex-start;
  }
}
/* #endif */
</style>
