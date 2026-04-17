const { api } = require('../../utils/api')
const { setSession, isLoggedIn } = require('../../utils/session')

Page({
  data: {
    form: { username: '', password: '' },
    loading: false,
    ui: {
      brandTitle: '实验室管理系统',
      brandSubtitle: '统一身份认证·安全访问实验资源',
      accountLabel: '学号/教工号',
      accountPlaceholder: '学号/教工号',
      passwordLabel: '密码',
      passwordPlaceholder: '密码',
      remember: '记住密码',
      forgot: '忘记密码？',
      login: '登录',
      loggingIn: '登录中...',
      secureText: '仅限校内访问 · 内网安全区域',
      platformText: 'LABORATORY MANAGEMENT PLATFORM',
      idIcon: '账号',
      pwdIcon: '密码'
    }
  },

  onLoad() {
    if (isLoggedIn()) {
      wx.switchTab({ url: '/pages/home/home' })
    }
  },

  onUsername(e) {
    this.setData({ 'form.username': e.detail.value.trim() })
  },

  onPassword(e) {
    this.setData({ 'form.password': e.detail.value })
  },

  async doLogin() {
    const { username, password } = this.data.form
    if (!username || !password) {
      wx.showToast({ title: '请填写用户名和密码', icon: 'none' })
      return
    }

    this.setData({ loading: true })
    try {
      const res = await api.login({ username, password })
      setSession(res.token, res.user)
      wx.showToast({ title: '登录成功', icon: 'success' })
      wx.switchTab({ url: '/pages/home/home' })
    } catch (_) {
      wx.showToast({ title: '登录失败，请检查账号或网络', icon: 'none' })
    }
    this.setData({ loading: false })
  }
})