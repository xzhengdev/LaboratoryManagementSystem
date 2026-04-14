<template>
  <view class="tag" :class="tagClass">
    {{ textMap[status] || label || status }}
  </view>
</template>

<script>
export default {
  props: {
    // status 使用后端原始状态值，如 pending / approved / disabled。
    status: {
      type: String,
      default: ''
    },
    // 某些场景允许自定义显示文案。
    label: {
      type: String,
      default: ''
    }
  },
  computed: {
    textMap() {
      // 统一状态文案，保证用户端和管理端含义一致。
      return {
        pending: '待审批',
        approved: '已通过',
        rejected: '已拒绝',
        cancelled: '已取消',
        active: '可预约',
        disabled: '停用'
      }
    },
    tagClass() {
      // 按状态拼接 class，交给样式层决定颜色。
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
}

.tag-pending {
  background: rgba(242, 153, 74, 0.12);
  color: #F2994A;
}

.tag-approved {
  background: rgba(39, 174, 96, 0.12);
  color: #27AE60;
}

.tag-rejected {
  background: rgba(235, 87, 87, 0.12);
  color: #EB5757;
}

.tag-cancelled,
.tag-disabled {
  background: rgba(154, 160, 166, 0.14);
  color: #6f7780;
}

.tag-active {
  background: rgba(47, 128, 237, 0.12);
  color: #2F80ED;
}

.tag-default {
  background: #EEF5FF;
  color: #2F80ED;
}
</style>
