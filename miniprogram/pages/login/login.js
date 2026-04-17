const { api } = require('../../utils/api')
const { setSession, isLoggedIn } = require('../../utils/session')

Page({
  data: {
    form: { username: '', password: '', role: 'student' },
    loading: false,
    roles: [
      { label: '学生', value: 'student' },
      { label: '教师', value: 'teacher' },
      { label: '实验室管理员', value: 'lab_admin' },
      { label: '系统管理员', value: 'system_admin' }
    ]
  },
  onLoad() {
    if (isLoggedIn()) {
      wx.switchTab({ url: '/pages/home/home' })
    }
  },
  selectRole(e) {
    this.setData({ 'form.role': e.currentTarget.dataset.value })
  },
  onUsername(e) { this.setData({ 'form.username': e.detail.value }) },
  onPassword(e) { this.setData({ 'form.password': e.detail.value }) },
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
      wx.switchTab({ url: '/pages/home/home' })
    } catch (_) {}
    this.setData({ loading: false })
  }
})
