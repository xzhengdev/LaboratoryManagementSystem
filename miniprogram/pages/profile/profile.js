const { api } = require('../../utils/api')
const { getProfile, updateProfile, clearSession, isLoggedIn } = require('../../utils/session')

const ROLE_TEXT = { student:'学生', teacher:'教师', lab_admin:'实验室管理员', system_admin:'系统管理员' }

Page({
  data: {
    profile: {},
    editForm: {},
    editing: false,
    loading: false,
    roleText: ROLE_TEXT
  },
  onShow() {
    if (!isLoggedIn()) { wx.redirectTo({ url: '/pages/login/login' }); return }
    this.loadProfile()
  },
  async loadProfile() {
    try {
      const p = await api.profile()
      updateProfile(p)
      this.setData({ profile: p })
    } catch (_) {
      this.setData({ profile: getProfile() })
    }
  },
  startEdit() {
    const { profile } = this.data
    this.setData({
      editing: true,
      editForm: { real_name: profile.real_name || '', email: profile.email || '', phone: profile.phone || '' }
    })
  },
  cancelEdit() { this.setData({ editing: false }) },
  onRealName(e) { this.setData({ 'editForm.real_name': e.detail.value }) },
  onEmail(e)    { this.setData({ 'editForm.email': e.detail.value }) },
  onPhone(e)    { this.setData({ 'editForm.phone': e.detail.value }) },
  async saveEdit() {
    this.setData({ loading: true })
    try {
      const p = await api.updateProfile(this.data.editForm)
      updateProfile(p)
      this.setData({ profile: p, editing: false })
      wx.showToast({ title: '保存成功', icon: 'success' })
    } catch (_) {}
    this.setData({ loading: false })
  },
  changeAvatar() {
    wx.chooseMedia({
      count: 1, mediaType: ['image'],
      success: async (res) => {
        const path = res.tempFiles[0].tempFilePath
        try {
          const data = await api.uploadAvatar(path)
          const profile = { ...this.data.profile, avatar_url: data.url }
          updateProfile(profile)
          this.setData({ profile })
          wx.showToast({ title: '头像已更新', icon: 'success' })
        } catch (_) {}
      }
    })
  },
  doLogout() {
    wx.showModal({
      title: '退出登录', content: '确定要退出吗？',
      success(r) {
        if (r.confirm) {
          clearSession()
          wx.reLaunch({ url: '/pages/login/login' })
        }
      }
    })
  }
})
