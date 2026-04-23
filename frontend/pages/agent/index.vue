<template>
  <view class="agent-page">
    <student-top-nav active="agent" />

    <view class="agent-page__shell">
      <view class="agent-page__head">
        <view class="agent-page__title">AI 助手</view>
        <view class="agent-page__sub">支持查询可预约实验室、我的预约、实验室排期与统计概览。</view>
      </view>

      <view class="agent-page__chat">
        <scroll-view
          scroll-y
          scroll-with-animation
          class="agent-page__messages"
          :scroll-into-view="scrollIntoView"
        >
          <view
            v-for="(item, index) in messages"
            :id="messageDomId(index)"
            :key="item.id || index"
            class="agent-page__row"
            :class="item.role"
          >
            <view class="agent-page__avatar" :class="item.role === 'assistant' ? 'assistant' : 'user'">
              <image
                v-if="item.role === 'assistant'"
                class="agent-page__avatar-img"
                src="/static/logo.png"
                mode="aspectFill"
              />
              <image
                v-else-if="userAvatar"
                class="agent-page__avatar-img"
                :src="userAvatar"
                mode="aspectFill"
              />
              <view v-else class="agent-page__avatar-fallback">{{ userInitial }}</view>
            </view>
            <view class="agent-page__bubble">
              <view class="agent-page__text">{{ item.content }}</view>
              <view v-if="item.role === 'assistant' && item.actions && item.actions.length" class="agent-page__actions">
                <view
                  v-for="(action, i) in item.actions"
                  :key="index + '-' + i"
                  class="agent-page__action"
                  @click="go(action.path)"
                >
                  {{ action.label }}
                </view>
              </view>
            </view>
          </view>
        </scroll-view>

        <view class="agent-page__quick">
          <view class="agent-page__quick-title">常用提问</view>
          <view class="agent-page__quick-list">
            <view
              v-for="(item, idx) in quickPrompts"
              :key="'prompt-' + idx"
              class="agent-page__quick-item"
              @click="usePrompt(item)"
            >
              {{ item }}
            </view>
          </view>
        </view>

        <view class="agent-page__input-bar">
          <input
            v-model.trim="draft"
            class="agent-page__input"
            placeholder="输入您的指令或查询..."
            confirm-type="send"
            @confirm="sendMessage"
          />
          <view class="agent-page__send" @click="sendMessage">发送</view>
        </view>
      </view>
    </view>

    <!-- <site-footer /> -->
  </view>
</template>

<script>
import SiteFooter from '../../components/site-footer.vue'
import StudentTopNav from '../../components/student-top-nav.vue'
import { api } from '../../api/index'
import { formatAgentReply, normalizeAgentActions, normalizeAgentPath } from '../../common/agent-format'
import { requireLogin } from '../../common/guard'
import { openPage } from '../../common/router'
import { getProfile } from '../../common/session'

export default {
  components: { SiteFooter, StudentTopNav },
  data() {
    return {
      draft: '',
      messageSeq: 1,
      scrollIntoView: '',
      userAvatar: '',
      userInitial: '我',
      quickPrompts: [
        '显示我的预约状态',
        '总结本月实验室使用情况',
        '明天下午可预约的实验室',
        '查询实验室列表',
        '帮我查看实验室详情',
        '推荐一个可预约实验室'
      ],
      messages: [
        {
          id: 'msg-0',
          role: 'assistant',
          content: '你好，我可以帮你查可预约实验室、我的预约状态、审批进度和统计概览。'
        }
      ]
    }
  },
  onShow() {
    if (!requireLogin()) return
    const profile = getProfile() || {}
    const name = String(profile.real_name || profile.username || '我')
    this.userAvatar = profile.avatar_url || ''
    this.userInitial = name.slice(0, 1) || '我'
    this.scrollToBottom()
  },
  methods: {
    createMessage(role, content, extra = {}) {
      const id = `msg-${this.messageSeq++}`
      return {
        id,
        role,
        content,
        ...extra
      }
    },
    messageDomId(index) {
      return `agent-page-msg-${index}`
    },
    scrollToBottom() {
      this.$nextTick(() => {
        const target = this.messageDomId(this.messages.length - 1)
        this.scrollIntoView = ''
        this.$nextTick(() => {
          this.scrollIntoView = target
        })
      })
    },
    normalizeAssistantText(content) {
      return formatAgentReply(content)
    },
    normalizeActions(actions) {
      return normalizeAgentActions(actions)
    },
    usePrompt(text) {
      this.draft = text
      this.sendMessage()
    },
    async sendMessage() {
      if (!this.draft) return
      const message = this.draft
      this.messages.push(this.createMessage('user', message))
      this.draft = ''
      this.scrollToBottom()
      try {
        const res = await api.agentChat(message)
        this.messages.push({
          ...this.createMessage(
            'assistant',
            this.normalizeAssistantText(res.reply || '已收到，请稍后再试。')
          ),
          content: this.normalizeAssistantText(res.reply || '已收到，请稍后再试。'),
          actions: this.normalizeActions(res.actions)
        })
        this.scrollToBottom()
      } catch (error) {
        this.messages.push(
          this.createMessage('assistant', '助手暂时不可用，请稍后再试。', {
            actions: []
          })
        )
        this.scrollToBottom()
      }
    },
    go(path) {
      openPage(normalizeAgentPath(path))
    }
  }
}
</script>

<style lang="scss">
.agent-page {
  height: 100vh;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background:
    radial-gradient(circle at 12% 14%, rgba(109, 179, 230, 0.25), transparent 26%),
    radial-gradient(circle at 88% 18%, rgba(173, 208, 240, 0.26), transparent 24%),
    linear-gradient(180deg, #edf5fc 0%, #dceaf7 100%);
}

.agent-page__shell {
  flex: 1;
  padding: 28rpx 32rpx 22rpx;
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
}

.agent-page__title {
  color: #061f44;
  font-size: 64rpx;
  line-height: 1.06;
  font-weight: 800;
}

.agent-page__sub {
  margin-top: 8rpx;
  color: #5f7188;
  font-size: 26rpx;
}

.agent-page__chat {
  margin-top: 18rpx;
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-rows: minmax(0, 1fr) auto auto;
  gap: 10rpx;
  overflow: hidden;
  border-radius: 24rpx;
  border: 1rpx solid rgba(197, 198, 207, 0.28);
  background: rgba(255, 255, 255, 0.78);
  padding: 14rpx;
}

.agent-page__messages {
  height: 100%;
  min-height: 0;
  padding: 6rpx;
  overflow: hidden;
}

.agent-page__row {
  display: flex;
  gap: 10rpx;
  margin-bottom: 14rpx;
}

.agent-page__row.user {
  flex-direction: row-reverse;
}

.agent-page__avatar {
  width: 52rpx;
  height: 52rpx;
  border-radius: 999rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #0b2750;
  color: #d9eeff;
  font-size: 22rpx;
  font-weight: 800;
  flex-shrink: 0;
  overflow: hidden;
  box-shadow: 0 8rpx 18rpx rgba(0, 0, 0, 0.08);
}

.agent-page__avatar.assistant {
  background: #ffffff;
  border: 2rpx solid rgba(255, 255, 255, 0.75);
}

.agent-page__avatar.user {
  background: linear-gradient(135deg, #4a90e2, #6aa8f0);
  border: 2rpx solid rgba(255, 255, 255, 0.82);
}

.agent-page__avatar-img {
  width: 100%;
  height: 100%;
  display: block;
}

.agent-page__avatar-fallback {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #ffffff;
  font-size: 22rpx;
  font-weight: 700;
}

.agent-page__bubble {
  max-width: 75%;
  border-radius: 18rpx;
  padding: 14rpx;
  background: #ffffff;
}

.agent-page__row.user .agent-page__bubble {
  background: #0b2550;
  color: #e9f2ff;
}

.agent-page__text {
  font-size: 25rpx;
  line-height: 1.6;
  color: #1f334f;
  white-space: pre-wrap;
}

.agent-page__row.user .agent-page__text {
  color: #eef5ff;
}

.agent-page__actions {
  margin-top: 10rpx;
  display: flex;
  flex-wrap: wrap;
  gap: 8rpx;
}

.agent-page__action {
  min-height: 44rpx;
  border-radius: 999rpx;
  padding: 0 14rpx;
  background: #e9f4ff;
  color: #0d3b69;
  display: inline-flex;
  align-items: center;
  font-size: 21rpx;
  font-weight: 700;
}

.agent-page__quick {
  display: flex;
  flex-direction: column;
  gap: 8rpx;
  flex-shrink: 0;
  overflow: hidden;
}

.agent-page__quick-title {
  font-size: 22rpx;
  color: #5b6f8a;
  font-weight: 700;
  padding: 0 4rpx;
}

.agent-page__quick-list {
  display: flex;
  gap: 10rpx;
  flex-wrap: wrap;
}

.agent-page__quick-item {
  min-height: 54rpx;
  border-radius: 999rpx;
  padding: 0 16rpx;
  background: #edf2f8;
  color: #4c5f79;
  display: inline-flex;
  align-items: center;
  font-size: 22rpx;
  font-weight: 700;
}

.agent-page__input-bar {
  margin-bottom: 6rpx;
  flex-shrink: 0;
  border-radius: 18rpx;
  background: #ffffff;
  border: 1rpx solid rgba(197, 198, 207, 0.34);
  padding: 10rpx;
  display: flex;
  gap: 10rpx;
}

.agent-page__input {
  flex: 1;
  min-height: 62rpx;
  border-radius: 14rpx;
  background: #f2f6fb;
  padding: 0 14rpx;
  color: #223853;
  font-size: 24rpx;
}

.agent-page__send {
  min-width: 100rpx;
  height: 62rpx;
  border-radius: 14rpx;
  background: #0a254c;
  color: #eef6ff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24rpx;
  font-weight: 800;
}




@media screen and (min-width: 1500px) {
  .agent-page__shell {
    padding-left: 56rpx;
    padding-right: 56rpx;
  }
}

@media screen and (max-width: 860px) {
  .agent-page__messages {
    min-height: 520rpx;
  }

  .agent-page__bubble {
    max-width: 86%;
  }
}

@media screen and (max-width: 760px) {
  .agent-page__shell {
    padding: 16rpx 12rpx calc(16rpx + env(safe-area-inset-bottom));
    min-height: 0;
  }

  .agent-page__title {
    font-size: 48rpx;
    line-height: 1.08;
  }

  .agent-page__sub {
    margin-top: 6rpx;
    font-size: 22rpx;
    line-height: 1.5;
  }

  .agent-page__chat {
    margin-top: 12rpx;
    border-radius: 18rpx;
    padding: 10rpx;
    min-height: 0;
    gap: 6rpx;
  }

  .agent-page__messages {
    height: 100%;
    min-height: 0;
  }

  .agent-page__row {
    gap: 8rpx;
    margin-bottom: 10rpx;
  }

  .agent-page__avatar {
    width: 44rpx;
    height: 44rpx;
  }

  .agent-page__bubble {
    max-width: 88%;
    border-radius: 14rpx;
    padding: 10rpx 12rpx;
  }

  .agent-page__text {
    font-size: 22rpx;
    line-height: 1.55;
  }

  .agent-page__actions {
    margin-top: 8rpx;
    gap: 6rpx;
  }

  .agent-page__action {
    min-height: 38rpx;
    padding: 0 10rpx;
    font-size: 19rpx;
  }

  .agent-page__quick {
    gap: 6rpx;
  }

  .agent-page__quick-title {
    font-size: 20rpx;
  }

  .agent-page__quick-list {
    gap: 8rpx;
  }

  .agent-page__quick-item {
    min-height: 46rpx;
    padding: 0 12rpx;
    font-size: 20rpx;
  }

  .agent-page__input-bar {
    margin-top: 8rpx;
    margin-bottom: 2rpx;
    border-radius: 14rpx;
    padding: 8rpx;
    gap: 8rpx;
  }

  .agent-page__input {
    min-height: 54rpx;
    border-radius: 10rpx;
    font-size: 22rpx;
    padding: 0 10rpx;
  }

  .agent-page__send {
    min-width: 82rpx;
    height: 54rpx;
    border-radius: 10rpx;
    font-size: 21rpx;
  }
}

@media screen and (max-width: 420px) {
  .agent-page__title {
    font-size: 42rpx;
  }

  .agent-page__sub {
    font-size: 20rpx;
  }

  .agent-page__bubble {
    max-width: 90%;
  }
}

</style>
