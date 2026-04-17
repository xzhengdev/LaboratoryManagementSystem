const { api } = require('../../utils/api')

const STATUS_TEXT = { pending:'待审核', approved:'已批准', rejected:'已拒绝', cancelled:'已取消', completed:'已完成' }
const STATUS_SUB  = { pending:'等待管理员审核', approved:'预约已通过，请按时使用', rejected:'预约未通过审核', cancelled:'预约已取消', completed:'使用已完成' }

Page({
  data: {
    reservation: {},
    approvals: [],
    loading: false,
    statusText: STATUS_TEXT,
    statusSub: STATUS_SUB
  },
  onLoad(options) {
    this.resId = options.id
    this.loadDetail()
  },
  async loadDetail() {
    try {
      const res = await api.reservationDetail(this.resId)
      this.setData({
        reservation: res,
        approvals: res.approvals || []
      })
    } catch (_) {}
  },
  doCancel() {
    wx.showModal({
      title: '确认取消',
      content: '确定要取消这条预约吗？',
      success: async (r) => {
        if (!r.confirm) return
        this.setData({ loading: true })
        try {
          await api.cancelReservation(this.resId)
          wx.showToast({ title: '已取消', icon: 'success' })
          setTimeout(() => this.loadDetail(), 1000)
        } catch (_) {}
        this.setData({ loading: false })
      }
    })
  }
})
