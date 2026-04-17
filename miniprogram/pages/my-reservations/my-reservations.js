const { api } = require('../../utils/api')
const { isLoggedIn } = require('../../utils/session')

const STATUS_TEXT = { pending:'待审核', approved:'已批准', rejected:'已拒绝', cancelled:'已取消', completed:'已完成' }

Page({
  data: {
    allList: [],
    list: [],
    activeFilter: '',
    statusText: STATUS_TEXT,
    filters: [
      { label: '全部', value: '' },
      { label: '待审核', value: 'pending' },
      { label: '已批准', value: 'approved' },
      { label: '已拒绝', value: 'rejected' },
      { label: '已取消', value: 'cancelled' }
    ]
  },
  onShow() {
    if (!isLoggedIn()) { wx.redirectTo({ url: '/pages/login/login' }); return }
    this.loadReservations()
  },
  async loadReservations() {
    try {
      const res = await api.myReservations()
      const list = res.items || res || []
      this.setData({ allList: list })
      this.applyFilter()
    } catch (_) {}
  },
  setFilter(e) {
    this.setData({ activeFilter: e.currentTarget.dataset.value }, () => this.applyFilter())
  },
  applyFilter() {
    const { allList, activeFilter } = this.data
    this.setData({ list: activeFilter ? allList.filter(r => r.status === activeFilter) : allList })
  },
  goDetail(e) {
    wx.navigateTo({ url: `/pages/reservation-detail/reservation-detail?id=${e.currentTarget.dataset.id}` })
  }
})
