const { api } = require('../../utils/api')
const { setSession, isLoggedIn } = require('../../utils/session')

const REMEMBER_KEY = 'login_remember_credentials'

Page({
  data: {
    form: { username: '', password: '' },
    loading: false,
    rememberPassword: false,
    ui: {
      brandTitle: '\u5b9e\u9a8c\u5ba4\u7ba1\u7406\u7cfb\u7edf',
      brandSubtitle: '\u7edf\u4e00\u8eab\u4efd\u8ba4\u8bc1\u00b7\u5b89\u5168\u8bbf\u95ee\u5b9e\u9a8c\u8d44\u6e90',
      accountLabel: '\u5b66\u53f7/\u6559\u5de5\u53f7',
      accountPlaceholder: '\u5b66\u53f7/\u6559\u5de5\u53f7',
      passwordLabel: '\u5bc6\u7801',
      passwordPlaceholder: '\u5bc6\u7801',
      remember: '\u8bb0\u4f4f\u5bc6\u7801',
      forgot: '\u5fd8\u8bb0\u5bc6\u7801\uff1f',
      login: '\u767b\u5f55',
      loggingIn: '\u767b\u5f55\u4e2d...',
      secureText: '\u4ec5\u9650\u6821\u5185\u8bbf\u95ee \u00b7 \u5185\u7f51\u5b89\u5168\u533a\u57df',
      platformText: 'LABORATORY MANAGEMENT PLATFORM',
      idIcon: '\u8d26\u53f7',
      pwdIcon: '\u5bc6\u7801'
    }
  },

  onLoad() {
    if (isLoggedIn()) {
      wx.switchTab({ url: '/pages/home/home' })
      return
    }

    const remembered = wx.getStorageSync(REMEMBER_KEY)
    if (remembered && remembered.username && remembered.password) {
      this.setData({
        'form.username': remembered.username,
        'form.password': remembered.password,
        rememberPassword: true
      })
    }
  },

  onUsername(e) {
    this.setData({ 'form.username': e.detail.value.trim() })
  },

  onPassword(e) {
    this.setData({ 'form.password': e.detail.value })
  },

  toggleRemember() {
    const next = !this.data.rememberPassword
    this.setData({ rememberPassword: next })
    if (!next) {
      wx.removeStorageSync(REMEMBER_KEY)
    }
  },

  onForgotPassword() {
    wx.showModal({
      title: '\u5fd8\u8bb0\u5bc6\u7801',
      content: '\u8bf7\u8054\u7cfb\u5b9e\u9a8c\u5ba4\u7ba1\u7406\u5458\u6216\u6559\u52a1\u7cfb\u7edf\u7ba1\u7406\u5458\u91cd\u7f6e\u5bc6\u7801\u3002',
      confirmText: '\u6211\u77e5\u9053\u4e86',
      showCancel: false
    })
  },

  async doLogin() {
    const { username, password } = this.data.form
    if (!username || !password) {
      wx.showToast({ title: '\u8bf7\u586b\u5199\u7528\u6237\u540d\u548c\u5bc6\u7801', icon: 'none' })
      return
    }

    this.setData({ loading: true })
    try {
      const res = await api.login({ username, password })
      setSession(res.token, res.user)

      if (this.data.rememberPassword) {
        wx.setStorageSync(REMEMBER_KEY, { username, password })
      } else {
        wx.removeStorageSync(REMEMBER_KEY)
      }

      wx.showToast({ title: '\u767b\u5f55\u6210\u529f', icon: 'success' })
      wx.switchTab({ url: '/pages/home/home' })
    } catch (_) {
      wx.showToast({ title: '\u767b\u5f55\u5931\u8d25\uff0c\u8bf7\u68c0\u67e5\u8d26\u53f7\u6216\u7f51\u7edc', icon: 'none' })
    }
    this.setData({ loading: false })
  }
})