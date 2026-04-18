const { api } = require('../../utils/api')
const { isLoggedIn } = require('../../utils/session')

const COLORS = ['#4A90E2', '#27AE60', '#E25454', '#9B59B6', '#F5A623', '#1ABC9C']

Page({
  data: {
    campusOptions: [{ id: '', campus_name: '全部校区' }],
    labs: [],
    allLabs: [],
    selectedCampusId: '',
    selectedCampusIndex: 0,
    selectedCampusName: '',
    selectedType: '',
    keyword: '',
    entryCampusId: '',
    types: [
      { label: '全部', value: '' },
      { label: '生物', value: 'bio' },
      { label: '化学', value: 'chem' },
      { label: '物理', value: 'phy' },
      { label: 'AI', value: 'ai' }
    ]
  },
  onLoad(options) {
    this.setData({ entryCampusId: options && options.campus ? String(options.campus) : '' })
  },
  onShow() {
    if (!isLoggedIn()) {
      wx.redirectTo({ url: '/pages/login/login' })
      return
    }
    this.loadData()
  },
  async loadData() {
    try {
      const [campusesRes, labsRes] = await Promise.all([api.campuses(), api.labs()])
      const campuses = this.normalizeList(campusesRes)
      const campusOptions = [{ id: '', campus_name: '全部校区' }, ...campuses]

      const selectedId = this.data.entryCampusId || this.data.selectedCampusId
      const selectedCampusIndex = selectedId
        ? Math.max(campusOptions.findIndex((item) => String(item.id) === String(selectedId)), 0)
        : 0
      const selectedCampus = campusOptions[selectedCampusIndex] || campusOptions[0]

      const labs = this.normalizeList(labsRes).map((item, index) => {
        const typeKey = this.resolveTypeKey(item)
        return {
          ...item,
          color: COLORS[index % COLORS.length],
          typeKey,
          openText: `${(item.open_time || '--:--').slice(0, 5)}-${(item.close_time || '--:--').slice(0, 5)}`,
          statusText: item.status === 'active' ? '开放中' : '维护中',
          statusClass: item.status === 'active' ? 'active' : 'inactive'
        }
      })

      this.setData(
        {
          campusOptions,
          selectedCampusId: String(selectedCampus.id || ''),
          selectedCampusIndex,
          selectedCampusName: selectedCampus.id ? selectedCampus.campus_name : '',
          allLabs: labs,
          entryCampusId: ''
        },
        () => this.filterLabs()
      )
    } catch (_) {}
  },
  normalizeList(res) {
    if (Array.isArray(res)) return res
    if (res && Array.isArray(res.items)) return res.items
    return []
  },
  resolveTypeKey(item) {
    const direct = String(item.lab_type || '').toLowerCase()
    if (['bio', 'chem', 'phy', 'ai'].includes(direct)) return direct

    const text = `${item.lab_name || ''} ${item.description || ''}`.toLowerCase()
    if (text.includes('bio') || text.includes('biology') || text.includes('gene') || text.includes('medical')) return 'bio'
    if (text.includes('chem') || text.includes('chemical') || text.includes('synthesis')) return 'chem'
    if (text.includes('physics') || text.includes('optics') || text.includes('material')) return 'phy'
    if (text.includes('ai') || text.includes('machine') || text.includes('intelligent')) return 'ai'
    return ''
  },
  onCampusChange(e) {
    const selectedCampusIndex = Number(e.detail.value || 0)
    const selectedCampus = this.data.campusOptions[selectedCampusIndex] || this.data.campusOptions[0]
    this.setData(
      {
        selectedCampusIndex,
        selectedCampusId: String(selectedCampus.id || ''),
        selectedCampusName: selectedCampus.id ? selectedCampus.campus_name : ''
      },
      () => this.filterLabs()
    )
  },
  onSearch(e) {
    this.setData({ keyword: (e.detail.value || '').trim() }, () => this.filterLabs())
  },
  selectType(e) {
    this.setData({ selectedType: e.currentTarget.dataset.value }, () => this.filterLabs())
  },
  filterLabs() {
    const { allLabs, selectedCampusId, selectedType, keyword } = this.data
    let list = allLabs

    if (selectedCampusId) {
      list = list.filter((item) => String(item.campus_id) === String(selectedCampusId))
    }
    if (selectedType) {
      list = list.filter((item) => item.typeKey === selectedType)
    }
    if (keyword) {
      const lowerKeyword = keyword.toLowerCase()
      list = list.filter((item) => {
        const text = `${item.lab_name || ''} ${item.location || ''} ${item.campus_name || ''} ${item.description || ''}`.toLowerCase()
        return text.includes(lowerKeyword)
      })
    }

    this.setData({ labs: list })
  },
  goDetail(e) {
    wx.navigateTo({ url: `/pages/lab-detail/lab-detail?id=${e.currentTarget.dataset.id}` })
  }
})
