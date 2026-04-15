<template>
  <view class="tag" :class="tagClass">
    {{ textMap[status] || label || status }}
  </view>
</template>

<script>
export default {
  props: {
    status: {
      type: String,
      default: ''
    },
    label: {
      type: String,
      default: ''
    }
  },
  computed: {
    textMap() {
      return {
        pending: '待审批',
        approved: '已通过',
        rejected: '已拒绝',
        cancelled: '已取消',
        active: '可用',
        disabled: '停用'
      }
    },
    tagClass() {
      return `tag-${this.status || 'default'}`
    }
  }
}
</script>

<style lang="scss">
.tag {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 999rpx;
  padding: 8rpx 18rpx;
  font-size: 22rpx;
  border: 1rpx solid transparent;
  max-width: 120rpx;
}

.tag-pending {
  background: rgba(242, 153, 74, 0.12);
  color: #f2994a;
}

.tag-approved {
  background: rgba(39, 174, 96, 0.12);
  color: #27ae60;
}

.tag-rejected {
  background: rgba(235, 87, 87, 0.12);
  color: #eb5757;
}

.tag-cancelled,
.tag-disabled {
  background: rgba(154, 160, 166, 0.14);
  color: #6f7780;
}

.tag-active {
  background: rgba(47, 128, 237, 0.12);
  color: #2f80ed;
}

.tag-default {
  background: #eef5ff;
  color: #2f80ed;
}
</style>
