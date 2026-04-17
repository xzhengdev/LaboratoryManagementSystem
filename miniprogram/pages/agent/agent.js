const { api } = require('../../utils/api')

Page({
  data: {
    messages: [
      { role: 'assistant', content: '你好！我是实验室预约助手，可以帮你查询实验室排期、我的预约，或引导你到对应页面。', actions: [] }
    ],
    draft: '',
    scrollId: 'msg-bottom',
    quickPrompts: ['今天有哪些实验室可预约', '查看我的预约', '明天的排期']
  },
  onDraft(e) { this.setData({ draft: e.detail.value }) },
  sendQuick(e) {
    this.setData({ draft: e.currentTarget.dataset.text }, () => this.sendMessage())
  },
  async sendMessage() {
    const msg = this.data.draft.trim()
    if (!msg) return
    const messages = [...this.data.messages, { role: 'user', content: msg, actions: [] }]
    this.setData({ messages, draft: '', scrollId: 'msg-bottom' })
    try {
      const res = await api.agentChat(msg)
      this.setData({
        messages: [...this.data.messages, { role: 'assistant', content: res.reply, actions: res.actions || [] }],
        scrollId: 'msg-bottom'
      })
    } catch (_) {
      this.setData({
        messages: [...this.data.messages, { role: 'assistant', content: '助手暂时不可用，请稍后再试。', actions: [] }]
      })
    }
  },
  goAction(e) {
    wx.navigateTo({ url: e.currentTarget.dataset.path })
  }
})
