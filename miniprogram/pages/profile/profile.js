const { api } = require('../../utils/api')
const { getProfile, updateProfile, clearSession, isLoggedIn } = require('../../utils/session')

const ROLE_TEXT = { student:'学生', teacher:'教师', lab_admin:'实验室管理员', system_admin:'系统管理员' }

Page({
  data: {
    profile: {},
    editForm: {},
    editing: false,
    loading: false,
    globalLoading: false,
    roleText: ROLE_TEXT
  },
  onShow() {
    if (!isLoggedIn()) { wx.redirectTo({ url: '/pages/login/login' }); return }
    this.loadProfile()
  },
  async loadProfile() {
    this.setData({ globalLoading: true })
    try {
      const p = await api.profile()
      updateProfile(p)
      this.setData({ profile: p })
    } catch (err) {
      console.error('加载个人资料失败:', err)
      this.setData({ profile: getProfile() })
      wx.showToast({
        title: '加载失败',
        icon: 'none',
        duration: 2000
      })
    } finally {
      this.setData({ globalLoading: false })
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
    // 简单的输入验证
    const { editForm } = this.data
    if (editForm.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(editForm.email)) {
      wx.showToast({ title: '邮箱格式不正确', icon: 'none' })
      return
    }
    if (editForm.phone && !/^1[3-9]\d{9}$/.test(editForm.phone)) {
      wx.showToast({ title: '手机号格式不正确', icon: 'none' })
      return
    }

    this.setData({ loading: true, globalLoading: true })
    try {
      const p = await api.updateProfile(editForm)
      updateProfile(p)
      this.setData({ profile: p, editing: false })
      wx.showToast({
        title: '保存成功',
        icon: 'success',
        duration: 1500
      })
    } catch (err) {
      console.error('保存失败:', err)
      wx.showToast({
        title: '保存失败，请重试',
        icon: 'none',
        duration: 2000
      })
    } finally {
      this.setData({ loading: false, globalLoading: false })
    }
  },
  changeAvatar() {
    wx.chooseMedia({
      count: 1,
      mediaType: ['image'],
      maxDuration: 30,
      sizeType: ['compressed'],
      success: async (res) => {
        const file = res.tempFiles[0]
        // 检查文件大小 (限制为5MB)
        if (file.size > 5 * 1024 * 1024) {
          wx.showToast({
            title: '图片太大，请选择5MB以内的图片',
            icon: 'none'
          })
          return
        }

        this.setData({ globalLoading: true })
        try {
          const data = await api.uploadAvatar(file.tempFilePath)
          const profile = { ...this.data.profile, avatar_url: data.url }
          updateProfile(profile)
          this.setData({ profile })
          wx.showToast({
            title: '头像已更新',
            icon: 'success',
            duration: 1500
          })
        } catch (err) {
          console.error('头像上传失败:', err)
          wx.showToast({
            title: '上传失败，请重试',
            icon: 'none',
            duration: 2000
          })
        } finally {
          this.setData({ globalLoading: false })
        }
      },
      fail: (err) => {
        console.error('选择图片失败:', err)
        if (err.errMsg !== 'chooseMedia:fail cancel') {
          wx.showToast({
            title: '选择图片失败',
            icon: 'none'
          })
        }
      }
    })
  },
  doLogout() {
    wx.showModal({
      title: '退出登录',
      content: '确定要退出当前账号吗？',
      confirmText: '退出',
      confirmColor: '#e25454',
      cancelText: '取消',
      cancelColor: '#0071e3',
      success: (res) => {
        if (res.confirm) {
          clearSession()
          wx.reLaunch({ url: '/pages/login/login' })
        }
      }
    })
  }
})
