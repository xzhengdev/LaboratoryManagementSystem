const { api } = require('../../utils/api')
const { getProfile, isLoggedIn } = require('../../utils/session')

function today() {
  const d = new Date()
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

const STATUS_TEXT = {
  pending: '待审核',
  approved: '已通过',
  rejected: '已驳回'
}

Page({
  data: {
    profile: {},
    labs: [],
    labIndex: -1,
    form: {
      report_date: today(),
      content: ''
    },
    photoDrafts: [],
    reports: [],
    loading: false,
    submitting: false
  },
  onShow() {
    if (!isLoggedIn()) {
      wx.redirectTo({ url: '/pages/login/login' })
      return
    }
    const profile = getProfile()
    if (String(profile.role || '') !== 'student') {
      wx.showToast({ title: '仅学生可提交日报', icon: 'none' })
      wx.navigateBack({ delta: 1 })
      return
    }
    this.setData({ profile })
    this.bootstrap()
  },
  async bootstrap() {
    this.setData({ loading: true })
    try {
      await Promise.all([this.loadLabs(), this.loadMyReports()])
    } finally {
      this.setData({ loading: false })
    }
  },
  async loadLabs() {
    const result = await api.labs({ page: 1, per_page: 100 })
    const list = result.items || result || []
    this.setData({ labs: Array.isArray(list) ? list : [] })
  },
  async loadMyReports() {
    const rows = await api.myDailyReports()
    const reports = Array.isArray(rows) ? rows : []
    this.setData({ reports })
  },
  onDateChange(e) {
    this.setData({ 'form.report_date': e.detail.value })
  },
  onContentInput(e) {
    this.setData({ 'form.content': e.detail.value })
  },
  onLabChange(e) {
    this.setData({
      labIndex: Number(e.detail.value || -1),
      photoDrafts: []
    })
  },
  getSelectedLab() {
    const index = Number(this.data.labIndex)
    if (index < 0) return null
    return this.data.labs[index] || null
  },
  async choosePhotos() {
    const selectedLab = this.getSelectedLab()
    if (!selectedLab) {
      wx.showToast({ title: '请先选择实验室', icon: 'none' })
      return
    }

    const remain = Math.max(0, 6 - this.data.photoDrafts.length)
    if (!remain) {
      wx.showToast({ title: '最多上传 6 张图片', icon: 'none' })
      return
    }

    wx.chooseImage({
      count: remain,
      sizeType: ['compressed'],
      sourceType: ['album', 'camera'],
      success: async (res) => {
        const paths = res?.tempFilePaths || []
        if (!paths.length) return

        for (let i = 0; i < paths.length; i += 1) {
          const filePath = paths[i]
          try {
            const uploaded = await api.uploadDailyReportPhoto(filePath, {
              lab_id: selectedLab.id,
              campus_id: selectedLab.campus_id
            })
            const photo = {
              localPath: filePath,
              fileId: uploaded.id,
              url: uploaded.url
            }
            this.setData({ photoDrafts: this.data.photoDrafts.concat([photo]) })
          } catch (error) {
            console.error('upload daily report photo failed', error)
          }
        }
      }
    })
  },
  removePhoto(e) {
    const index = Number(e.currentTarget.dataset.index || -1)
    if (index < 0) return
    const next = this.data.photoDrafts.filter((_, idx) => idx !== index)
    this.setData({ photoDrafts: next })
  },
  previewDraftPhotos(e) {
    const index = Number(e.currentTarget.dataset.index || 0)
    const urls = this.data.photoDrafts.map((item) => item.url || item.localPath).filter(Boolean)
    if (!urls.length) return
    wx.previewImage({ urls, current: urls[index] || urls[0] })
  },
  async submitReport() {
    if (this.data.submitting) return

    const selectedLab = this.getSelectedLab()
    if (!selectedLab) {
      wx.showToast({ title: '请选择实验室', icon: 'none' })
      return
    }

    const content = String(this.data.form.content || '').trim()
    if (!content) {
      wx.showToast({ title: '请填写日报内容', icon: 'none' })
      return
    }

    if (!this.data.photoDrafts.length) {
      wx.showToast({ title: '请至少上传 1 张现场图片', icon: 'none' })
      return
    }

    this.setData({ submitting: true })
    try {
      await api.createDailyReport({
        lab_id: selectedLab.id,
        report_date: this.data.form.report_date,
        content,
        photo_file_ids: this.data.photoDrafts.map((item) => item.fileId).filter(Boolean)
      })
      wx.showToast({ title: '提交成功', icon: 'success' })
      this.setData({
        form: {
          report_date: today(),
          content: ''
        },
        photoDrafts: []
      })
      await this.loadMyReports()
    } catch (error) {
      console.error('submit daily report failed', error)
    } finally {
      this.setData({ submitting: false })
    }
  },
  statusText(status) {
    return STATUS_TEXT[String(status || '').toLowerCase()] || status || '--'
  },
  previewReportPhotos(e) {
    const index = Number(e.currentTarget.dataset.index || 0)
    const rowIndex = Number(e.currentTarget.dataset.rowIndex || -1)
    const row = this.data.reports[rowIndex]
    if (!row || !Array.isArray(row.photos) || !row.photos.length) return
    const urls = row.photos.map((item) => item.url).filter(Boolean)
    if (!urls.length) return
    wx.previewImage({ urls, current: urls[index] || urls[0] })
  }
})
