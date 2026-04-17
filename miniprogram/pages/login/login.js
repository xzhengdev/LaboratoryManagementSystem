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
    // 已登录直接跳转
    if (isLoggedIn()) {
      wx.switchTab({ url: '/pages/home/home' })
      return
    }

    // 读取记住密码
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

  /* ===== 输入处理（关键：保证浮动 label 正常） ===== */
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

  /* ===== 记住密码 ===== */
  toggleRemember() {
    const next = !this.data.rememberPassword
    this.setData({ rememberPassword: next })

    if (!next) {
      wx.removeStorageSync(REMEMBER_KEY)
    }
  },

  /* ===== 忘记密码 ===== */
  onForgotPassword() {
    wx.showModal({
      title: '忘记密码',
      content: '请联系实验室管理员或教务系统管理员重置密码。',
      confirmText: '我知道了',
      showCancel: false
    })
  },

  /* ===== 登录（带 loading 动效） ===== */
  async doLogin() {
    if (this.data.loading) return   // 防重复点击

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

      // 记住密码
      if (this.data.rememberPassword) {
        wx.setStorageSync(REMEMBER_KEY, { username, password })
      } else {
        wx.removeStorageSync(REMEMBER_KEY)
      }

      wx.showToast({
        title: '登录成功',
        icon: 'success'
      })

      // 延迟一点更有“产品感”
      setTimeout(() => {
        wx.switchTab({ url: '/pages/home/home' })
      }, 500)

    } catch (err) {
      wx.showToast({
        title: '登录失败，请检查账号或网络',
        icon: 'none'
      })
    }

    this.setData({ loading: false })
  }
})