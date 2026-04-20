<template>
  <view class="agent-root">
    <view v-if="!visible" class="agent-toggle" @click="toggleWindow">
      智能助手
    </view>
    <view v-if="visible" class="agent-panel">
      <view class="agent-head">
        <text>实验室预约 Agent</text>
        <text class="agent-close" @click="visible = false">收起</text>
      </view>
      <scroll-view scroll-y class="agent-body">
        <view
          v-for="(item, index) in messages"
          :key="index"
          class="agent-message-wrap"
          :class="item.role"
        >
          <view class="agent-message-row">
            <view v-if="item.role === 'assistant'" class="agent-avatar agent-avatar--assistant">
              <image class="agent-avatar-img" src="/static/logo.png" mode="aspectFill" />
            </view>
            <view class="agent-message" :class="item.role">
              <text>{{ item.content }}</text>
            </view>
            <view v-if="item.role === 'user'" class="agent-avatar agent-avatar--user">
              <image v-if="userAvatar" class="agent-avatar-img" :src="userAvatar" mode="aspectFill" />
              <view v-else class="agent-avatar-fallback">{{ userInitial }}</view>
            </view>
          </view>
        </view>
      </scroll-view>
      <view class="agent-actions" v-if="lastActions.length">
        <view
          v-for="action in lastActions"
          :key="action.path"
          class="agent-action"
          @click="go(action.path)"
        >
          {{ action.label }}
        </view>
      </view>
      <view class="agent-input">
        <input v-model="draft" class="agent-text" placeholder="输入自然语言，例如：帮我看看明天可预约的实验室" confirm-type="send" @confirm="sendMessage" />
        <view class="agent-send" @click="sendMessage">发送</view>
      </view>
    </view>
  </view>
</template>

<script>
import { api } from '../api/index'
import { getProfile } from '../common/session'

export default {
  props: {
    // 某些页面需要默认展开对话窗口，例如独立的 Agent 展示页。
    defaultVisible: {
      type: Boolean,
      default: false
    }
  },
  data() {
    return {
      // visible 控制浮窗显隐；messages 保存会话上下文；lastActions 保存后端推荐跳转。
      visible: this.defaultVisible,
      draft: '',
      messages: [
        {
          role: 'assistant',
          content: '你好，我可以帮你查看实验室排期、我的预约、统计概览，也可以把你引导到对应页面。'
        }
      ],
      userAvatar: '',
      userInitial: '我',
      lastActions: []
    }
  },
  created() {
    this.loadUserIdentity()
  },
  methods: {
    loadUserIdentity() {
      const profile = getProfile() || {}
      const name = String(profile.real_name || profile.username || '我')
      this.userAvatar = profile.avatar_url || ''
      this.userInitial = name.slice(0, 1) || '我'
    },
    stripMarkdownSyntax(content) {
      const text = String(content || '')
      return text
        .replace(/```[\s\S]*?```/g, (block) => block.replace(/```/g, ''))
        .replace(/^#{1,6}\s*/gm, '')
        .replace(/\*\*(.*?)\*\*/g, '$1')
        .replace(/\*(.*?)\*/g, '$1')
        .replace(/`([^`]+)`/g, '$1')
        .replace(/^\s*([-*_])\1{2,}\s*$/gm, '')
        .replace(/^\s*[-*+]\s+/gm, '')
        .replace(/\n{3,}/g, '\n\n')
        .trim()
    },
    normalizeStatusText(content) {
      const text = String(content || '')
      return text
        .replace(/\bpending\b/gi, '待审批')
        .replace(/\bapproved\b/gi, '已通过')
        .replace(/\bcancelled\b/gi, '已取消')
        .replace(/\bcanceled\b/gi, '已取消')
    },
    normalizeAssistantText(content) {
      return this.normalizeStatusText(this.stripMarkdownSyntax(content))
    },
    toggleWindow() {
      this.visible = !this.visible
    },
    async sendMessage() {
      // 发送消息时先把用户输入写入本地消息列表，再请求后端 Agent 接口。
      if (!this.draft) {
        return
      }
      const message = this.draft
      this.messages.push({ role: 'user', content: message })
      this.draft = ''
      try {
        const res = await api.agentChat(message)
        // 后端返回 reply 文本和 actions 跳转建议，两者都展示在窗口中。
        this.messages.push({ role: 'assistant', content: this.normalizeAssistantText(res.reply) })
        this.lastActions = res.actions || []
      } catch (error) {
        this.messages.push({ role: 'assistant', content: '助手暂时不可用，请稍后再试。' })
      }
    },
    go(path) {
      // 推荐操作点击后直接跳转到系统内对应页面。
      uni.navigateTo({ url: path })
    }
  }
}
</script>

<style lang="scss">
.agent-root {
  position: fixed;
  right: 20rpx;
  bottom: 24rpx;
  z-index: 99;
}

.agent-toggle {
  background: #1c5c4c;
  color: #fff;
  border-radius: 999rpx;
  padding: 20rpx 28rpx;
  box-shadow: 0 10rpx 30rpx rgba(28, 92, 76, 0.2);
}

.agent-panel {
  width: 680rpx;
  max-width: calc(100vw - 40rpx);
  height: 760rpx;
  background: rgba(255, 255, 255, 0.98);
  border-radius: 28rpx;
  box-shadow: 0 20rpx 60rpx rgba(0, 0, 0, 0.14);
  margin-bottom: 18rpx;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.agent-head {
  padding: 24rpx;
  background: linear-gradient(135deg, #1c5c4c, #2a7b66);
  color: #fff;
  display: flex;
  justify-content: space-between;
  font-size: 28rpx;
}

.agent-close {
  opacity: 0.82;
}

.agent-body {
  flex: 1;
  padding: 20rpx;
  background: #f6f8f6;
}

.agent-message-wrap {
  margin-bottom: 16rpx;
}

.agent-message-row {
  display: flex;
  align-items: flex-start;
  gap: 12rpx;
}

.agent-message-wrap.user .agent-message-row {
  justify-content: flex-end;
}

.agent-avatar {
  width: 56rpx;
  height: 56rpx;
  border-radius: 50%;
  overflow: hidden;
  flex-shrink: 0;
  box-shadow: 0 8rpx 16rpx rgba(0, 0, 0, 0.08);
}

.agent-avatar--assistant {
  background: #ffffff;
  border: 1rpx solid rgba(28, 92, 76, 0.18);
}

.agent-avatar--user {
  background: linear-gradient(135deg, #4a90e2, #6aa8f0);
  border: 1rpx solid rgba(255, 255, 255, 0.85);
}

.agent-avatar-img {
  width: 100%;
  height: 100%;
  display: block;
}

.agent-avatar-fallback {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 24rpx;
  font-weight: 700;
}

.agent-message {
  max-width: 82%;
  padding: 18rpx 20rpx;
  border-radius: 22rpx;
  font-size: 26rpx;
  line-height: 1.6;
  white-space: pre-wrap;
}

.agent-message.assistant {
  background: #fff;
  color: #1c2520;
}

.agent-message.user {
  background: #1c5c4c;
  color: #fff;
}

.agent-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 12rpx;
  padding: 12rpx 20rpx;
  background: #fff;
}

.agent-action {
  background: #eef5f2;
  color: #1c5c4c;
  padding: 12rpx 18rpx;
  border-radius: 999rpx;
  font-size: 22rpx;
}

.agent-input {
  display: flex;
  gap: 12rpx;
  padding: 20rpx;
  background: #fff;
  border-top: 1rpx solid #eef1ee;
}

.agent-text {
  flex: 1;
  background: #f6f8f6;
  border-radius: 18rpx;
  padding: 18rpx;
}

.agent-send {
  background: #1c5c4c;
  color: #fff;
  padding: 18rpx 24rpx;
  border-radius: 18rpx;
}


@media screen and (min-width: 960px) {
  .agent-root {
    right: 32rpx;
    bottom: 32rpx;
  }

  .agent-panel {
    width: 420px;
    height: 620px;
  }
}

</style>
