const { api } = require('../../utils/api')

const TAB_PATHS = [
  '/pages/home/home',
  '/pages/labs/labs',
  '/pages/my-reservations/my-reservations',
  '/pages/profile/profile'
]

let uid = Date.now()
function nextId() {
  uid += 1
  return uid
}

Page({
  data: {
    messages: [],
    draft: '',
    sending: false,
    canSend: false,
    typing: false,
    scrollAnchor: '',
    userAvatar: '',
    userName: '我',
    userInitial: '我',
    quickPrompts: [
      '今天有哪些实验室可预约？',
      '帮我查看我的预约记录',
      '明天下午空闲时段有哪些？'
    ]
  },

  onLoad() {
    this.bootstrap()
  },

  onShow() {
    this.loadUserProfile()
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

  bootstrap() {
    this.setData({
      messages: [
        {
          id: nextId(),
          role: 'assistant',
          content: '你好，我是实验室预约助手。你可以问我实验室空闲时段、预约状态，或直接点下面的快捷问题。',
          actions: []
        }
      ]
    }, () => this.scrollToBottom())
  },

  loadUserProfile() {
    const profile = wx.getStorageSync('lab_profile') || {}
    const name = profile.real_name || profile.username || '我'
    this.setData({
      userAvatar: profile.avatar_url || '',
      userName: name,
      userInitial: String(name).slice(0, 1) || '我'
    })
  },

  onDraft(e) {
    const draft = e.detail.value || ''
    this.setData({
      draft,
      canSend: !!draft.trim() && !this.data.sending
    })
  },

  sendQuick(e) {
    if (this.data.sending) return
    const text = e.currentTarget.dataset.text || ''
    this.setData({ draft: text, canSend: !!text.trim() }, () => this.sendMessage())
  },

  appendMessage(message, callback) {
    const messages = [...this.data.messages, message]
    this.setData({ messages }, () => {
      this.scrollToBottom()
      if (typeof callback === 'function') callback()
    })
  },

  scrollToBottom() {
    const anchor = this.data.typing
      ? 'typing-bubble'
      : (this.data.messages.length ? `msg-${this.data.messages[this.data.messages.length - 1].id}` : '')
    if (!anchor) return
    setTimeout(() => {
      this.setData({ scrollAnchor: anchor })
    }, 20)
  },

  async sendMessage() {
    if (this.data.sending) return

    const msg = (this.data.draft || '').trim()
    if (!msg) return

    const userMessage = {
      id: nextId(),
      role: 'user',
      content: msg,
      actions: []
    }

    this.setData({
      sending: true,
      typing: true,
      canSend: false,
      draft: ''
    }, () => this.scrollToBottom())

    this.appendMessage(userMessage)

    try {
      const res = await api.agentChat(msg, { loading: false, timeout: 25000 })
      const assistantMessage = {
        id: nextId(),
        role: 'assistant',
        content: (res && res.reply) || '已收到你的问题。',
        actions: (res && res.actions) || []
      }
      assistantMessage.content = this.normalizeAssistantText(assistantMessage.content)
      this.appendMessage(assistantMessage)
    } catch (err) {
      const fallbackMessage = {
        id: nextId(),
        role: 'assistant',
        content: '助手暂时不可用，请稍后再试。',
        actions: []
      }
      this.appendMessage(fallbackMessage)
      console.error('agentChat error:', err)
    } finally {
      this.setData({
        sending: false,
        typing: false,
        canSend: !!(this.data.draft || '').trim()
      }, () => this.scrollToBottom())
    }
  },

  goAction(e) {
    const path = e.currentTarget.dataset.path
    if (!path) return

    const isTab = TAB_PATHS.includes(path)
    if (isTab) {
      wx.switchTab({ url: path })
      return
    }

    wx.navigateTo({
      url: path,
      fail() {
        wx.showToast({ title: '暂不支持跳转该页面', icon: 'none' })
      }
    })
  }
})
