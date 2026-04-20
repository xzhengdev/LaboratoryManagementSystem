<template>
  <view class="card">
    <view class="title">{{ title }}</view>
    <view class="subtitle">{{ subtitle }}</view>
    <view class="chart-bars">
      <view v-for="item in normalizedData" :key="item.label" class="chart-item">
        <view class="chart-bar" :style="{ height: item.height + 'rpx' }"></view>
        <view class="chart-label">{{ item.label }}</view>
        <view class="chart-label">{{ item.value }}</view>
      </view>
    </view>
  </view>
</template>

<script>
export default {
  props: {
    // 图表标题与说明通常出现在管理端统计、控制台页面。
    title: { type: String, default: '' },
    subtitle: { type: String, default: '' },
    // data format example: [{ label: '海淀校区', value: 12 }]
    data: { type: Array, default: () => [] }
  },
  computed: {
    normalizedData() {
      // 根据最大值动态计算柱高，避免数值较小时图表完全看不见。
      const max = Math.max(...this.data.map((item) => Number(item.value) || 0), 1)
      return this.data.map((item) => ({
        ...item,
        height: Math.max(36, Math.round(((Number(item.value) || 0) / max) * 220))
      }))
    }
  }
}
</script>

<style scoped lang="scss">
.chart-bars {
  overflow-x: auto;
}

.chart-item {
  min-width: 88rpx;
}

.chart-bar {
  background: linear-gradient(180deg, #bee5ff 0%, #f0feff 100%);
}

.chart-label {
  word-break: break-all;
}

@media screen and (max-width: 768px) {
  .chart-item {
    min-width: 78rpx;
  }

  .chart-label {
    font-size: 20rpx;
    line-height: 1.35;
  }
}
</style>
