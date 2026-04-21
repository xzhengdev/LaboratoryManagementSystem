const { api } = require('../../utils/api')
const { isLoggedIn } = require('../../utils/session')

const DELETE_WIDTH_RPX = 168
const STATUS_TEXT = {
  pending: '待审批',
  approved: '已通过',
  rejected: '已拒绝',
  cancelled: '已取消',
  completed: '已完成'
}

Page({
  data: {
    allList: [],
    list: [],
    activeFilter: '',
    statusText: STATUS_TEXT,
    overview: {
      pending: 0,
      approved: 0,
      total: 0
    },
    filters: [
      { label: '全部', value: '' },
      { label: '待审批', value: 'pending' },
      { label: '已通过', value: 'approved' },
      { label: '已拒绝', value: 'rejected' },
      { label: '已取消', value: 'cancelled' }
    ],
    deleteWidthPx: 132,
    swipingId: null,
    swipeStartX: 0,
    swipeStartOffset: 0,
    isSwiping: false
  },

  onLoad() {
    const system = wx.getSystemInfoSync()
    const rpxRatio = system.windowWidth / 750
    this.setData({ deleteWidthPx: Math.round(DELETE_WIDTH_RPX * rpxRatio) })
  },

  onShow() {
    if (!isLoggedIn()) {
      wx.redirectTo({ url: '/pages/login/login' })
      return
    }
    this.loadReservations()
  },

  async loadReservations() {
    try {
      const res = await api.myReservations()
      const list = this.normalizeList(res.items || res || [])
      this.setData({ allList: list })
      this.updateOverview(list)
      this.applyFilter()
    } catch (_) {}
  },

  normalizeList(list) {
    return (Array.isArray(list) ? list : []).map((item) => ({
      ...item,
      can_delete: item.status === 'rejected' || item.status === 'cancelled',
      _swipeX: 0,
      _open: false
    }))
  },

  updateOverview(list) {
    const pending = list.filter((item) => item.status === 'pending').length
    const approved = list.filter((item) => item.status === 'approved').length
    this.setData({
      overview: {
        pending,
        approved,
        total: list.length
      }
    })
  },

  setFilter(e) {
    this.closeAllSwipes()
    this.setData({ activeFilter: e.currentTarget.dataset.value }, () => this.applyFilter())
  },

  applyFilter() {
    const { allList, activeFilter } = this.data
    this.setData({
      list: activeFilter ? allList.filter((item) => item.status === activeFilter) : allList
    })
  },

  onPageTap() {
    this.closeAllSwipes()
  },

  getListItem(id) {
    return this.data.list.find((item) => String(item.id) === String(id))
  },

  closeAllSwipes(exceptId = null) {
    const { allList } = this.data
    const next = allList.map((item) => {
      if (exceptId && String(item.id) === String(exceptId)) return item
      if (!item._open && !item._swipeX) return item
      return { ...item, _swipeX: 0, _open: false }
    })
    this.setData({ allList: next })
    this.applyFilter()
  },

  updateSwipeForItem(id, swipeX, open = false) {
    const { allList } = this.data
    const next = allList.map((item) =>
      String(item.id) === String(id) ? { ...item, _swipeX: swipeX, _open: open } : item
    )
    this.setData({ allList: next })
    this.applyFilter()
  },

  onCardTouchStart(e) {
    const id = e?.currentTarget?.dataset?.id
    const point = e?.touches?.[0]
    if (!id || !point) return

    const item = this.getListItem(id)
    if (!item || !item.can_delete) return

    this.closeAllSwipes(id)
    this.setData({
      swipingId: id,
      swipeStartX: point.clientX,
      swipeStartOffset: Number(item._swipeX || 0),
      isSwiping: false
    })
  },

  onCardTouchMove(e) {
    const { swipingId, swipeStartX, swipeStartOffset, deleteWidthPx } = this.data
    const id = e?.currentTarget?.dataset?.id
    const point = e?.touches?.[0]
    if (!swipingId || String(swipingId) !== String(id) || !point) return

    const deltaX = point.clientX - swipeStartX
    const moved = swipeStartOffset + deltaX
    const clamped = Math.min(0, Math.max(-deleteWidthPx, moved))
    const hasMoved = Math.abs(deltaX) > 6

    if (hasMoved && !this.data.isSwiping) {
      this.setData({ isSwiping: true })
    }
    this.updateSwipeForItem(id, clamped, false)
  },

  onCardTouchEnd(e) {
    const { swipingId, deleteWidthPx } = this.data
    const id = e?.currentTarget?.dataset?.id
    if (!swipingId || String(swipingId) !== String(id)) return

    const item = this.getListItem(id)
    const current = Number(item?._swipeX || 0)
    const shouldOpen = Math.abs(current) >= deleteWidthPx * 0.45

    this.updateSwipeForItem(id, shouldOpen ? -deleteWidthPx : 0, shouldOpen)
    this.setData({
      swipingId: null,
      swipeStartX: 0,
      swipeStartOffset: 0
    })

    setTimeout(() => {
      this.setData({ isSwiping: false })
    }, 0)
  },

  deleteReservation(e) {
    const id = e?.currentTarget?.dataset?.id
    if (!id) return
    wx.showModal({
      title: '删除预约',
      content: '删除后不可恢复，确认删除该预约吗？',
      success: async (res) => {
        if (!res.confirm) return
        try {
          await api.deleteReservation(id)
          wx.showToast({ title: '删除成功', icon: 'success' })
          await this.loadReservations()
        } catch (error) {
          wx.showToast({
            title: (error && error.message) || '删除失败',
            icon: 'none'
          })
        }
      }
    })
  },

  goDetail(e) {
    if (this.data.isSwiping) return
    const id = e?.currentTarget?.dataset?.id
    const item = this.getListItem(id)
    if (item && item._open) {
      this.closeAllSwipes()
      return
    }
    wx.navigateTo({ url: `/pages/reservation-detail/reservation-detail?id=${id}` })
  }
})
