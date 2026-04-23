<template>
  <admin-layout :title="pageTitle" :subtitle="pageSubtitle" active="logs">
    <view class="admin-kpi-grid">
      <view v-for="item in summaryCards" :key="item.label" class="admin-kpi-card">
        <view class="admin-kpi-card__label">{{ item.label }}</view>
        <view class="admin-kpi-card__value">{{ item.value }}</view>
      </view>
    </view>

    <view class="card filter-card">
      <view class="title">{{ text.filterTitle }}</view>
      <view class="filter-grid">
        <picker :range="moduleOptionLabels" :value="modulePickerIndex" @change="onModuleChange">
          <view class="filter-chip">{{ moduleChipText }}</view>
        </picker>
        <picker :range="actionOptionLabels" :value="actionPickerIndex" @change="onActionChange">
          <view class="filter-chip">{{ actionChipText }}</view>
        </picker>
        <picker mode="date" :value="filters.start_date" @change="onStartDateChange">
          <view class="filter-chip">{{ startDateChipText }}</view>
        </picker>
        <picker mode="date" :value="filters.end_date" @change="onEndDateChange">
          <view class="filter-chip">{{ endDateChipText }}</view>
        </picker>
        <picker :range="limitOptionLabels" :value="limitPickerIndex" @change="onLimitChange">
          <view class="filter-chip">{{ limitChipText }}</view>
        </picker>
      </view>
      <view class="filter-actions">
        <input
          v-model="keywordInput"
          class="input admin-toolbar-lite__search filter-search"
          confirm-type="search"
          :placeholder="text.searchPlaceholder"
          @confirm="applyFilters"
        />
        <view class="toolbar-action toolbar-action--primary" @click="applyFilters">{{ text.search }}</view>
        <view class="toolbar-action" @click="resetFilters">{{ text.reset }}</view>
      </view>
    </view>

    <view class="card">
      <view class="section-head">
        <view class="title">{{ text.listTitle }}</view>
        <view class="section-head__meta">{{ listMetaText }}</view>
      </view>
      <view v-if="list.length" class="log-list">
        <view v-for="item in list" :key="item.id" class="log-item">
          <view class="log-item__head">
            <view>
              <view class="log-item__title">{{ userDisplayName(item) }}</view>
              <view class="log-item__sub">{{ userMetaText(item) }}</view>
            </view>
            <view class="log-item__time">{{ formatDateTimeMinute(item.created_at) }}</view>
          </view>
          <view class="log-item__tags">
            <view class="pill">{{ roleLabel(item.role) }}</view>
            <view class="pill pill-soft">{{ moduleLabel(item.module) }}</view>
            <view class="pill pill-soft">{{ actionLabel(item.action) }}</view>
          </view>
          <view class="log-item__detail">{{ item.detail || text.noDetail }}</view>
          <view class="log-item__foot">{{ footText(item) }}</view>
        </view>
      </view>
      <view v-else class="empty-state">{{ text.empty }}</view>
    </view>
  </admin-layout>
</template>

<script>
import { api } from '../../api/index'
import { requireLogin } from '../../common/guard'
import { getProfile } from '../../common/session'
import { canViewOperationLogs, getRoleText, isSystemAdmin } from '../../config/navigation'
import AdminLayout from '../../components/admin-layout.vue'

const ALL_VALUE = 'all'
const LIMIT_OPTIONS = [50, 100, 200]
const MODULE_TEXT_MAP = {
  reservation: '\u9884\u7ea6',
  approval: '\u5ba1\u6279',
  auth: '\u8ba4\u8bc1',
  user: '\u7528\u6237',
  users: '\u7528\u6237',
  lab: '\u5b9e\u9a8c\u5ba4',
  labs: '\u5b9e\u9a8c\u5ba4',
  equipment: '\u8bbe\u5907',
  campus: '\u6821\u533a',
  campuses: '\u6821\u533a',
  statistics: '\u7edf\u8ba1',
  agent: 'AI \u52a9\u624b'
}
const ACTION_TEXT_MAP = {
  create: '\u521b\u5efa',
  cancel: '\u53d6\u6d88',
  update: '\u66f4\u65b0',
  delete: '\u5220\u9664',
  approved: '\u901a\u8fc7',
  rejected: '\u9a73\u56de',
  login: '\u767b\u5f55',
  logout: '\u9000\u51fa',
  reset_password: '\u91cd\u7f6e\u5bc6\u7801',
  upload: '\u4e0a\u4f20',
  view: '\u67e5\u770b'
}
const TEXT = {
  systemTitle: '\u5168\u5c40\u65e5\u5fd7\u5ba1\u8ba1',
  campusTitle: '\u672c\u6821\u533a\u65e5\u5fd7\u5ba1\u8ba1',
  systemSubtitle: '\u67e5\u770b\u7ba1\u7406\u5458\u4e0e\u7528\u6237\u7684\u5173\u952e\u4e1a\u52a1\u64cd\u4f5c\u8f68\u8ff9',
  campusSubtitle: '\u4ec5\u67e5\u770b\u5f53\u524d\u6821\u533a\u76f8\u5173\u7528\u6237\u7684\u4e1a\u52a1\u64cd\u4f5c\u8f68\u8ff9',
  filterTitle: '\u7b5b\u9009\u6761\u4ef6',
  moduleAll: '\u5168\u90e8\u6a21\u5757',
  actionAll: '\u5168\u90e8\u52a8\u4f5c',
  startAny: '\u4e0d\u9650',
  endAny: '\u4e0d\u9650',
  searchPlaceholder: '\u641c\u7d22\u7528\u6237\u3001\u6a21\u5757\u3001\u52a8\u4f5c\u6216\u8be6\u60c5',
  search: '\u67e5\u8be2',
  reset: '\u91cd\u7f6e',
  listTitle: '\u64cd\u4f5c\u65e5\u5fd7',
  listCountSuffix: '\u6761\u8bb0\u5f55',
  currentRecords: '\u5f53\u524d\u8bb0\u5f55',
  relatedUsers: '\u6d89\u53ca\u7528\u6237',
  moduleCount: '\u6a21\u5757\u6570',
  latestTime: '\u6700\u65b0\u65f6\u95f4',
  noDetail: '\u65e0\u8be6\u7ec6\u8bf4\u660e',
  empty: '\u5f53\u524d\u7b5b\u9009\u6761\u4ef6\u4e0b\u6ca1\u6709\u65e5\u5fd7\u8bb0\u5f55\u3002',
  systemScope: '\u7cfb\u7edf\u7ea7\u64cd\u4f5c',
  unassignedCampus: '\u672a\u5206\u914d\u6821\u533a',
  modulePrefix: '\u6a21\u5757',
  actionPrefix: '\u52a8\u4f5c',
  startPrefix: '\u5f00\u59cb',
  endPrefix: '\u7ed3\u675f',
  limitPrefix: '\u6570\u91cf',
  recentPrefix: '\u6700\u8fd1',
  rowSep: ' \u00b7 ',
  logIdPrefix: '\u65e5\u5fd7ID ',
  userIdPrefix: '\u7528\u6237ID '
}

export default {
  components: { AdminLayout },
  data() {
    return {
      text: TEXT,
      profile: {},
      list: [],
      keywordInput: '',
      filters: {
        module: ALL_VALUE,
        action: ALL_VALUE,
        start_date: '',
        end_date: '',
        limit: 100,
        keyword: ''
      },
      knownModules: [],
      knownActions: []
    }
  },
  computed: {
    pageTitle() {
      return isSystemAdmin(this.profile.role) ? this.text.systemTitle : this.text.campusTitle
    },
    pageSubtitle() {
      return isSystemAdmin(this.profile.role) ? this.text.systemSubtitle : this.text.campusSubtitle
    },
    summaryCards() {
      return [
        { label: this.text.currentRecords, value: this.list.length },
        { label: this.text.relatedUsers, value: new Set(this.list.map((item) => item.user_id)).size },
        { label: this.text.moduleCount, value: new Set(this.list.map((item) => item.module).filter(Boolean)).size },
        { label: this.text.latestTime, value: this.list.length ? this.formatDateTimeMinute(this.list[0].created_at) : '--' }
      ]
    },
    moduleOptions() {
      return [ALL_VALUE].concat(this.knownModules)
    },
    actionOptions() {
      return [ALL_VALUE].concat(this.knownActions)
    },
    moduleOptionLabels() {
      return this.moduleOptions.map((item) => (item === ALL_VALUE ? this.text.moduleAll : this.moduleLabel(item)))
    },
    actionOptionLabels() {
      return this.actionOptions.map((item) => (item === ALL_VALUE ? this.text.actionAll : this.actionLabel(item)))
    },
    currentModuleLabel() {
      return this.filters.module === ALL_VALUE ? this.text.moduleAll : this.moduleLabel(this.filters.module)
    },
    currentActionLabel() {
      return this.filters.action === ALL_VALUE ? this.text.actionAll : this.actionLabel(this.filters.action)
    },
    modulePickerIndex() {
      return Math.max(this.moduleOptions.indexOf(this.filters.module), 0)
    },
    actionPickerIndex() {
      return Math.max(this.actionOptions.indexOf(this.filters.action), 0)
    },
    moduleChipText() {
      return `${this.text.modulePrefix}: ${this.currentModuleLabel}`
    },
    actionChipText() {
      return `${this.text.actionPrefix}: ${this.currentActionLabel}`
    },
    startDateChipText() {
      return `${this.text.startPrefix}: ${this.filters.start_date || this.text.startAny}`
    },
    endDateChipText() {
      return `${this.text.endPrefix}: ${this.filters.end_date || this.text.endAny}`
    },
    limitChipText() {
      return `${this.text.limitPrefix}: ${this.text.recentPrefix} ${this.filters.limit} ${this.text.listCountSuffix}`
    },
    limitOptionLabels() {
      return LIMIT_OPTIONS.map((item) => `${this.text.recentPrefix} ${item} ${this.text.listCountSuffix}`)
    },
    limitPickerIndex() {
      const index = LIMIT_OPTIONS.indexOf(Number(this.filters.limit) || 100)
      return index >= 0 ? index : 1
    },
    listMetaText() {
      return `${this.list.length} ${this.text.listCountSuffix}`
    }
  },
  async onShow() {
    if (!requireLogin()) return
    this.profile = getProfile()
    if (!canViewOperationLogs(this.profile.role)) return
    await this.loadData()
  },
  methods: {
    async loadData() {
      const params = {
        limit: this.filters.limit
      }
      if (this.filters.module !== ALL_VALUE) params.module = this.filters.module
      if (this.filters.action !== ALL_VALUE) params.action = this.filters.action
      if (this.filters.start_date) params.start_date = this.filters.start_date
      if (this.filters.end_date) params.end_date = this.filters.end_date
      if (this.filters.keyword) params.keyword = this.filters.keyword

      this.list = await api.operationLogs(params)
      this.syncKnownOptions(this.list)
    },
    syncKnownOptions(items) {
      const moduleSet = new Set(this.knownModules)
      const actionSet = new Set(this.knownActions)
      items.forEach((item) => {
        if (item.module) moduleSet.add(item.module)
        if (item.action) actionSet.add(item.action)
      })
      this.knownModules = [...moduleSet].sort()
      this.knownActions = [...actionSet].sort()
    },
    onModuleChange(event) {
      const index = Number(event?.detail?.value || 0)
      this.filters.module = this.moduleOptions[index] || ALL_VALUE
      this.loadData()
    },
    onActionChange(event) {
      const index = Number(event?.detail?.value || 0)
      this.filters.action = this.actionOptions[index] || ALL_VALUE
      this.loadData()
    },
    onStartDateChange(event) {
      this.filters.start_date = event?.detail?.value || ''
      this.loadData()
    },
    onEndDateChange(event) {
      this.filters.end_date = event?.detail?.value || ''
      this.loadData()
    },
    onLimitChange(event) {
      const index = Number(event?.detail?.value || 0)
      this.filters.limit = LIMIT_OPTIONS[index] || 100
      this.loadData()
    },
    async applyFilters() {
      this.filters.keyword = this.keywordInput.trim()
      await this.loadData()
    },
    async resetFilters() {
      this.keywordInput = ''
      this.filters = {
        module: ALL_VALUE,
        action: ALL_VALUE,
        start_date: '',
        end_date: '',
        limit: 100,
        keyword: ''
      }
      await this.loadData()
    },
    parseDateTime(value) {
      const text = String(value || '').trim()
      if (!text) return null
      if (!/[zZ]|[+\-]\d{2}:\d{2}$/.test(text)) {
        const utcText = text.includes('T') ? `${text}Z` : `${text.replace(' ', 'T')}Z`
        const utcDate = new Date(utcText)
        return Number.isNaN(utcDate.getTime()) ? null : utcDate
      }
      const date = new Date(text)
      return Number.isNaN(date.getTime()) ? null : date
    },
    formatDateTimeMinute(value) {
      const date = this.parseDateTime(value)
      if (!date) return '--'
      const y = date.getFullYear()
      const m = String(date.getMonth() + 1).padStart(2, '0')
      const d = String(date.getDate()).padStart(2, '0')
      const h = String(date.getHours()).padStart(2, '0')
      const mm = String(date.getMinutes()).padStart(2, '0')
      return `${y}-${m}-${d} ${h}:${mm}`
    },
    userDisplayName(item) {
      return item.real_name || item.username || `User #${item.user_id}`
    },
    campusDisplay(item) {
      if (item.campus_name) return item.campus_name
      if (item.role === 'system_admin') return this.text.systemScope
      return this.text.unassignedCampus
    },
    userMetaText(item) {
      return `${item.username || '--'}${this.text.rowSep}${this.campusDisplay(item)}`
    },
    footText(item) {
      return `${this.text.logIdPrefix}${item.id}${this.text.rowSep}${this.text.userIdPrefix}${item.user_id}`
    },
    moduleLabel(value) {
      return this.translateLogValue(value, MODULE_TEXT_MAP)
    },
    actionLabel(value) {
      return this.translateLogValue(value, ACTION_TEXT_MAP)
    },
    translateLogValue(value, map) {
      const raw = String(value || '').trim()
      if (!raw) return '--'
      const key = raw.toLowerCase()
      return map[key] || raw
    },
    roleLabel(role) {
      return getRoleText(role)
    }
  }
}
</script>

<style lang="scss">
page {
  background: #f5f7fa;
}

.admin-workspace {
  background: #f5f7fa !important;
}

.admin-kpi-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 20rpx;
  margin-bottom: 24rpx;
}

.admin-kpi-card {
  border-radius: 22rpx;
  border: 1rpx solid #dbe4f1;
  background: #fff;
  padding: 24rpx 28rpx;
  box-shadow: 0 12rpx 32rpx rgba(16, 42, 73, 0.08);
}

.admin-kpi-card__label {
  color: #6d7f95;
  font-size: 22rpx;
  font-weight: 600;
}

.admin-kpi-card__value {
  margin-top: 10rpx;
  font-size: 36rpx;
  font-weight: 800;
  color: #132d4d;
  line-height: 1.3;
  word-break: break-word;
}

.filter-card {
  margin-bottom: 24rpx;
}

.filter-grid {
  margin-top: 18rpx;
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 14rpx;
}

.filter-chip {
  min-height: 76rpx;
  border-radius: 18rpx;
  border: 1rpx solid #d8e2f1;
  background: #f8fbff;
  padding: 0 20rpx;
  display: flex;
  align-items: center;
  color: #2d4668;
  font-size: 24rpx;
  font-weight: 600;
}

.filter-actions {
  margin-top: 16rpx;
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto auto;
  gap: 12rpx;
  align-items: center;
}

.filter-search {
  width: 100%;
  min-width: 0;
}

.admin-toolbar-lite__search {
  height: 76rpx;
  padding: 0 24rpx;
  border-radius: 18rpx;
  background: #ffffff;
  border: 1rpx solid #dce7f4;
  color: #132d4d;
  font-size: 24rpx;
  box-sizing: border-box;
}

.toolbar-action {
  height: 78rpx;
  min-width: 124rpx;
  padding: 0 24rpx;
  border-radius: 20rpx;
  border: 1rpx solid #dce7f4;
  background: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #3f5878;
  font-size: 24rpx;
  font-weight: 700;
  box-sizing: border-box;
}

.toolbar-action--primary {
  background: #e9f1fb;
  color: #1f4872;
  border-color: #d5e1f0;
}

.section-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12rpx;
}

.section-head__meta {
  font-size: 23rpx;
  color: #7a8796;
}

.log-list {
  margin-top: 18rpx;
  display: grid;
  gap: 16rpx;
}

.log-item {
  border-radius: 20rpx;
  border: 1rpx solid #e5edf7;
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  padding: 22rpx 24rpx;
}

.log-item__head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 20rpx;
}

.log-item__title {
  font-size: 30rpx;
  font-weight: 800;
  color: #173253;
}

.log-item__sub {
  margin-top: 8rpx;
  font-size: 22rpx;
  color: #72849b;
}

.log-item__time {
  font-size: 22rpx;
  color: #5d7592;
  font-weight: 700;
  white-space: nowrap;
}

.log-item__tags {
  margin-top: 14rpx;
  display: flex;
  flex-wrap: wrap;
  gap: 10rpx;
}

.log-item__detail {
  margin-top: 14rpx;
  padding: 18rpx 20rpx;
  border-radius: 16rpx;
  background: #eff5fc;
  color: #243a58;
  font-size: 24rpx;
  line-height: 1.6;
  word-break: break-word;
}

.log-item__foot {
  margin-top: 14rpx;
  font-size: 21rpx;
  color: #8a98a8;
}

@media screen and (max-width: 1200px) {
  .admin-kpi-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .filter-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media screen and (max-width: 768px) {
  .admin-kpi-grid {
    grid-template-columns: 1fr;
    gap: 12rpx;
    margin-bottom: 16rpx;
  }

  .admin-kpi-card {
    padding: 20rpx 22rpx;
  }

  .admin-kpi-card__value {
    font-size: 30rpx;
  }

  .filter-grid {
    grid-template-columns: 1fr;
    gap: 10rpx;
  }

  .filter-actions {
    grid-template-columns: 1fr;
  }

  .filter-search {
    width: 100%;
  }

  .toolbar-action {
    width: 100%;
  }

  .section-head {
    align-items: flex-start;
    flex-direction: column;
  }

  .log-item {
    padding: 18rpx 18rpx;
  }

  .log-item__head {
    flex-direction: column;
    gap: 10rpx;
  }

  .log-item__time {
    white-space: normal;
  }
}
</style>
