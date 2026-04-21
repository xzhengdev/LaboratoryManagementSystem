const { api } = require('../../utils/api')
const { setSession, isLoggedIn } = require('../../utils/session')

const REMEMBER_KEY = 'login_remember_credentials'

Page({
  data: {
    form: {
      username: '',
      password: ''
    },
    loading: false,
    rememberPassword: false,
    ui: {
      brandTitle: '实验室管理系统',
      brandSubtitle: '统一身份认证 · 安全访问实验资源',
      accountPlaceholder: '学号/学工号',
      passwordPlaceholder: '请输入密码',
      remember: '记住密码',
      forgot: '忘记密码？',
      login: '登录',
      loggingIn: '登录中...',
      secureText: '仅限校内访问 · 内网安全区域'
    }
  },

  onLoad() {
    if (isLoggedIn()) {
      wx.switchTab({ url: '/pages/home/home' })
      return
    }

    const remembered = wx.getStorageSync(REMEMBER_KEY)
    if (remembered?.username && remembered?.password) {
      this.setData({
        form: {
          username: remembered.username,
          password: remembered.password
        },
        rememberPassword: true
      })
    }
  },

  onUsername(e) {
    this.setData({
      'form.username': e.detail.value.trim()
    })
  },

  onPassword(e) {
    this.setData({
      'form.password': e.detail.value
    })
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
      title: '忘记密码',
      content: '请联系实验室管理员或系统管理员重置密码。',
      confirmText: '我知道了',
      showCancel: false
    })
  },

  async doLogin() {
    if (this.data.loading) return
    const { username, password } = this.data.form

    if (!username || !password) {
      wx.showToast({
        title: '请输入账号和密码',
        icon: 'none'
      })
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

      wx.showToast({
        title: '登录成功',
        icon: 'success'
      })

      setTimeout(() => {
        wx.switchTab({ url: '/pages/home/home' })
      }, 500)
    } catch (err) {
      console.error('[MP][LOGIN][ERROR]', err)
      const message = (err && err.message) || (err && err.msg) || '登录失败，请检查账号或密码'
      wx.showToast({
        title: message,
        icon: 'none'
      })
    }

    this.setData({ loading: false })
  }
})
