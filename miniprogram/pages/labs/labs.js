const { api } = require('../../utils/api')
const { isLoggedIn } = require('../../utils/session')

const COLORS = ['#4A90E2','#27AE60','#E25454','#9B59B6','#F5A623','#1ABC9C']

Page({
  data: {
    campuses: [],
    labs: [],
    allLabs: [],
    selectedCampus: '',
    selectedType: '',
    types: [
      { label: '全部', value: '' },
      { label: '生物', value: 'bio' },
      { label: '化学', value: 'chem' },
      { label: '物理', value: 'phy' },
      { label: 'AI', value: 'ai' }
    ]
  },
  onShow() {
    if (!isLoggedIn()) { wx.redirectTo({ url: '/pages/login/login' }); return }
    this.loadData()
  },
  async loadData() {
    try {
      const [campuses, labsRes] = await Promise.all([api.campuses(), api.labs()])
      const labs = (labsRes.items || labsRes || []).map((l, i) => ({
        ...l, color: COLORS[i % COLORS.length]
      }))
      this.setData({ campuses, allLabs: labs, labs })
    } catch (_) {}
  },
  selectCampus(e) {
    this.setData({ selectedCampus: e.currentTarget.dataset.id }, () => this.filterLabs())
  },
  selectType(e) {
    this.setData({ selectedType: e.currentTarget.dataset.value }, () => this.filterLabs())
  },
  filterLabs() {
    const { allLabs, selectedCampus, selectedType } = this.data
    let list = allLabs
    if (selectedCampus) list = list.filter(l => l.campus_id === selectedCampus)
    if (selectedType) list = list.filter(l => (l.lab_type || '') === selectedType)
    this.setData({ labs: list })
  },
  goDetail(e) {
    wx.navigateTo({ url: `/pages/lab-detail/lab-detail?id=${e.currentTarget.dataset.id}` })
  }
})
