<template>
  <view class="asset-request-page">
    <student-top-nav active="assetRequests" />

    <view class="asset-request-shell">
      <view class="page-head">
        <view>
          <view class="page-title">教师资产申报</view>
          <view class="page-subtitle">提交申报后进入审批流程，审批通过后可执行入库</view>
        </view>
        <view class="create-btn" @click="openCreateModal">+ 发起申报</view>
      </view>

      <view class="tabs">
        <view
          v-for="item in tabList"
          :key="item.key"
          class="tab-item"
          :class="{ active: activeTab === item.key }"
          @click="activeTab = item.key"
        >
          {{ item.label }}
        </view>
      </view>

      <view v-if="activeTab === 'reference'" class="card panel table-panel">
        <view class="panel-title">参考台账（本校区已入库资产）</view>
        <view class="table-scroll">
          <view class="table-head ref-grid">
            <text>资产编号</text>
            <text>资产名称</text>
            <text>类别</text>
            <text>规格型号</text>
            <text>厂家</text>
            <text>单价</text>
            <text>存放位置</text>
            <text>入库时间</text>
          </view>
          <view v-if="!referenceAssets.length" class="empty-text">暂无参考台账数据</view>
          <view v-for="item in referenceAssets" :key="item.id" class="table-row ref-grid">
            <text class="mono">{{ item.asset_code || '--' }}</text>
            <text>{{ item.asset_name || '--' }}</text>
            <text>{{ item.category || '--' }}</text>
            <text>{{ item.meta.spec_model || '--' }}</text>
            <text>{{ item.meta.manufacturer || '--' }}</text>
            <text>{{ moneyText(item.price) }}</text>
            <text>{{ item.meta.storage_location || '--' }}</text>
            <text>{{ dateText(item.created_at) }}</text>
          </view>
        </view>
      </view>

      <view v-if="activeTab === 'history'" class="card panel table-panel">
        <view class="panel-title">我的申报</view>

        <view class="toolbar">
          <picker :range="statusOptions" range-key="label" :value="statusIndex" @change="changeStatus">
            <view class="input toolbar-picker">{{ currentStatusLabel }}</view>
          </picker>
          <input v-model="keyword" class="input toolbar-search" placeholder="搜索申报单号/资产名称" />
          <view class="toolbar-btn" @click="clearFilter">清空</view>
        </view>

        <view class="table-scroll">
          <view class="table-head req-grid">
            <text>申报单号</text>
            <text>资产名称</text>
            <text>类别</text>
            <text>单价</text>
            <text>数量</text>
            <text>金额</text>
            <text>状态</text>
            <text>申报时间</text>
          </view>
          <view v-if="!filteredRequests.length" class="empty-text">暂无申报记录</view>
          <view v-for="item in filteredRequests" :key="item.id" class="table-row req-grid">
            <text class="mono">{{ item.request_no || '--' }}</text>
            <text>{{ item.asset_name || '--' }}</text>
            <text>{{ item.category || '--' }}</text>
            <text>{{ moneyText(item.unit_price) }}</text>
            <text>{{ item.quantity || 0 }}</text>
            <text>{{ moneyText(item.amount) }}</text>
            <text :class="statusClass(item.status)">{{ statusText(item.status) }}</text>
            <text>{{ timeText(item.created_at) }}</text>
          </view>
        </view>
      </view>
    </view>

    <view v-if="showCreateModal" class="modal-mask" @click="closeCreateModal">
      <view class="modal-card" @click.stop>
        <view class="modal-head">
          <view class="modal-title">发起资产申报</view>
          <view class="modal-close" @click="closeCreateModal">×</view>
        </view>

        <view class="form-grid two">
          <view class="field">
            <view class="label">所属实验室</view>
            <picker :range="labOptions" range-key="lab_name" :value="labIndex" @change="changeLab">
              <view class="input picker-like">{{ currentLabName }}</view>
            </picker>
          </view>

          <view class="field">
            <view class="label">资产名称</view>
            <input v-model="form.asset_name" class="input" placeholder="如：48口交换机" />
          </view>
        </view>

        <view class="form-grid three">
          <view class="field">
            <view class="label">资产类别</view>
            <input v-model="form.category" class="input" placeholder="如：交换设备" />
          </view>
          <view class="field">
            <view class="label">单价（元）</view>
            <input v-model="form.unit_price" type="digit" class="input" placeholder="0.00" />
          </view>
          <view class="field">
            <view class="label">数量</view>
            <input v-model="form.quantity" type="number" class="input" placeholder="1" />
          </view>
        </view>

        <view class="field">
          <view class="label">申报说明</view>
          <textarea
            v-model="form.reason"
            class="textarea"
            maxlength="300"
            placeholder="说明购置用途与使用场景"
          />
        </view>

        <view class="form-foot">
          <view class="total">预计金额：{{ moneyText(estimatedAmount) }}</view>
          <view class="actions">
            <view class="btn primary" :class="{ disabled: submitting }" @click="submitRequest">提交</view>
            <view class="btn" @click="resetForm">重置</view>
          </view>
        </view>
      </view>
    </view>
  </view>
</template>

<script>
import StudentTopNav from '../../components/student-top-nav.vue'
import { api } from '../../api/index'
import { requireLogin } from '../../common/guard'
import { getProfile } from '../../common/session'
import { openPage } from '../../common/router'
import { routes } from '../../config/navigation'

const META_FLAG = '__META__='

export default {
  components: { StudentTopNav },
  data() {
    return {
      profile: {},
      activeTab: 'reference',
      showCreateModal: false,
      submitting: false,
      tabList: [
        { key: 'reference', label: '参考台账' },
        { key: 'history', label: '我的申报' }
      ],
      labOptions: [],
      labIndex: 0,
      form: {
        campus_id: '',
        lab_id: '',
        asset_name: '',
        category: '',
        quantity: '1',
        unit_price: '',
        reason: ''
      },
      referenceAssets: [],
      requestList: [],
      statusOptions: [
        { label: '全部状态', value: '' },
        { label: '待审批', value: 'pending' },
        { label: '已通过', value: 'approved' },
        { label: '已驳回', value: 'rejected' }
      ],
      statusIndex: 0,
      keyword: ''
    }
  },
  computed: {
    currentLabName() {
      const row = this.labOptions[this.labIndex]
      return row ? row.lab_name : '请选择实验室'
    },
    estimatedAmount() {
      const quantity = Number(this.form.quantity || 0)
      const unitPrice = Number(this.form.unit_price || 0)
      if (!Number.isFinite(quantity) || !Number.isFinite(unitPrice)) return 0
      return quantity * unitPrice
    },
    currentStatusLabel() {
      return this.statusOptions[this.statusIndex]?.label || '全部状态'
    },
    currentStatusValue() {
      return this.statusOptions[this.statusIndex]?.value || ''
    },
    filteredRequests() {
      const text = String(this.keyword || '').trim().toLowerCase()
      return this.requestList.filter((item) => {
        const hitStatus = !this.currentStatusValue || item.status === this.currentStatusValue
        const hitText = !text || `${item.request_no || ''}${item.asset_name || ''}`.toLowerCase().includes(text)
        return hitStatus && hitText
      })
    }
  },
  async onShow() {
    if (!requireLogin()) return
    this.profile = getProfile()
    if (this.profile.role !== 'teacher') {
      uni.showToast({ title: '仅教师可发起资产申报', icon: 'none' })
      openPage(routes.home, { replace: true })
      return
    }
    await this.initPage()
  },
  methods: {
    openCreateModal() {
      this.showCreateModal = true
    },
    closeCreateModal() {
      if (this.submitting) return
      this.showCreateModal = false
    },
    moneyText(value) {
      const num = Number(value || 0)
      if (!Number.isFinite(num)) return '￥0.00'
      return `￥${num.toFixed(2)}`
    },
    dateText(value) {
      if (!value) return '--'
      return String(value).slice(0, 10)
    },
    timeText(value) {
      if (!value) return '--'
      return String(value).replace('T', ' ').slice(0, 19)
    },
    statusText(status) {
      const map = {
        pending: '待审批',
        approved: '已通过',
        rejected: '已驳回'
      }
      return map[status] || status
    },
    statusClass(status) {
      if (status === 'approved') return 'status approved'
      if (status === 'rejected') return 'status rejected'
      return 'status pending'
    },
    parseMeta(text) {
      const content = String(text || '')
      const idx = content.lastIndexOf(META_FLAG)
      if (idx < 0) return {}
      try {
        const row = JSON.parse(content.slice(idx + META_FLAG.length).trim())
        return row && typeof row === 'object' ? row : {}
      } catch (_error) {
        return {}
      }
    },
    withMeta(row, fieldName) {
      return {
        ...row,
        meta: this.parseMeta(row?.[fieldName])
      }
    },
    buildReason() {
      return String(this.form.reason || '').trim()
    },
    resetForm() {
      this.form.asset_name = ''
      this.form.category = ''
      this.form.quantity = '1'
      this.form.unit_price = ''
      this.form.reason = ''
    },
    changeLab(event) {
      const next = Number(event.detail.value || 0)
      this.labIndex = next
      const current = this.labOptions[next]
      this.form.lab_id = current ? current.id : ''
    },
    changeStatus(event) {
      this.statusIndex = Number(event.detail.value || 0)
    },
    clearFilter() {
      this.statusIndex = 0
      this.keyword = ''
    },
    async initPage() {
      await Promise.all([this.loadLabs(), this.loadReferenceAssets(), this.loadMyRequests()])
    },
    async loadLabs() {
      const labs = await api.labs({ campus_id: this.profile.campus_id })
      this.labOptions = Array.isArray(labs) ? labs : []
      if (this.labOptions.length) {
        this.labIndex = 0
        this.form.lab_id = this.labOptions[0].id
      }
      this.form.campus_id = this.profile.campus_id
    },
    async loadReferenceAssets() {
      const rows = await api.assets({ campus_id: this.profile.campus_id })
      const list = Array.isArray(rows) ? rows : []
      this.referenceAssets = list.map((item) => this.withMeta(item, 'description'))
    },
    async loadMyRequests() {
      const rows = await api.assetRequests()
      const list = Array.isArray(rows) ? rows : []
      this.requestList = list
    },
    async submitRequest() {
      if (this.submitting) return

      const asset_name = String(this.form.asset_name || '').trim()
      const category = String(this.form.category || '').trim()
      const quantity = Number(this.form.quantity || 0)
      const unit_price = Number(this.form.unit_price || 0)

      if (!this.form.lab_id) {
        uni.showToast({ title: '请选择实验室', icon: 'none' })
        return
      }
      if (!asset_name) {
        uni.showToast({ title: '请输入资产名称', icon: 'none' })
        return
      }
      if (!category) {
        uni.showToast({ title: '请输入资产类别', icon: 'none' })
        return
      }
      if (!Number.isFinite(quantity) || quantity <= 0) {
        uni.showToast({ title: '请输入有效数量', icon: 'none' })
        return
      }
      if (!Number.isFinite(unit_price) || unit_price <= 0) {
        uni.showToast({ title: '请输入有效单价', icon: 'none' })
        return
      }

      this.submitting = true
      try {
        await api.createAssetRequest({
          campus_id: this.profile.campus_id,
          lab_id: this.form.lab_id,
          asset_name,
          category,
          quantity,
          unit_price,
          reason: this.buildReason()
        })
        uni.showToast({ title: '申报已提交', icon: 'success' })
        this.showCreateModal = false
        this.resetForm()
        await Promise.all([this.loadReferenceAssets(), this.loadMyRequests()])
        this.activeTab = 'history'
      } finally {
        this.submitting = false
      }
    }
  }
}
</script>

<style lang="scss">
.asset-request-page {
  min-height: 100vh;
  background: #eef2f7;
}

.asset-request-shell {
  width: 100%;
  max-width: none;
  margin: 0;
  padding: 20rpx 24rpx 34rpx;
  box-sizing: border-box;
}

.page-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16rpx;
  flex-wrap: wrap;
}

.page-title {
  font-size: 36rpx;
  font-weight: 800;
  color: #163558;
}

.page-subtitle {
  margin-top: 6rpx;
  font-size: 22rpx;
  color: #5b6f87;
}

.create-btn {
  min-width: 180rpx;
  height: 68rpx;
  border-radius: 999rpx;
  background: linear-gradient(135deg, #2f6fda 0%, #4c8cf6 100%);
  color: #fff;
  font-size: 24rpx;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 8rpx 20rpx rgba(43, 96, 186, 0.22);
}

.tabs {
  margin-top: 16rpx;
  display: flex;
  align-items: center;
  gap: 10rpx;
}

.tab-item {
  min-width: 150rpx;
  height: 60rpx;
  padding: 0 22rpx;
  border: 1rpx solid #c8d2e0;
  background: #f4f7fb;
  color: #4d6480;
  font-size: 22rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 999rpx;
}

.tab-item.active {
  color: #fff;
  background: linear-gradient(135deg, #3a74d7 0%, #4d8df8 100%);
  border-color: transparent;
}

.card {
  margin-top: 16rpx;
  background: #fff;
  border-radius: 18rpx;
  box-shadow: 0 10rpx 24rpx rgba(19, 40, 82, 0.08);
}

.panel {
  padding: 20rpx;
}

.panel-title {
  font-size: 28rpx;
  color: #1b365d;
  font-weight: 700;
  margin-bottom: 14rpx;
}

.form-grid {
  display: grid;
  gap: 12rpx;
  margin-bottom: 12rpx;
}

.form-grid.two {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.form-grid.three {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.field {
  display: flex;
  flex-direction: column;
}

.label {
  font-size: 22rpx;
  color: #425a78;
  margin-bottom: 6rpx;
}

.input,
.textarea,
.picker-like,
.toolbar-picker,
.toolbar-search {
  width: 100%;
  box-sizing: border-box;
  border: 1rpx solid #d5deea;
  border-radius: 10rpx;
  background: #f9fbfd;
  color: #1f3550;
  font-size: 24rpx;
}

.input,
.picker-like,
.toolbar-picker,
.toolbar-search {
  height: 74rpx;
  line-height: 74rpx;
  padding: 0 16rpx;
}

.textarea {
  min-height: 144rpx;
  padding: 12rpx 16rpx;
}

.form-foot {
  margin-top: 8rpx;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.total {
  font-size: 24rpx;
  color: #2b5ea8;
  font-weight: 600;
}

.actions {
  display: flex;
  gap: 10rpx;
}

.btn {
  min-width: 124rpx;
  height: 64rpx;
  border-radius: 10rpx;
  background: #edf2f9;
  color: #3f5775;
  font-size: 24rpx;
  display: flex;
  align-items: center;
  justify-content: center;
}

.btn.primary {
  background: #2f6fda;
  color: #fff;
}

.btn.disabled {
  opacity: 0.65;
}

.table-panel {
  overflow: hidden;
}

.table-scroll {
  overflow-x: auto;
}

.toolbar {
  display: grid;
  grid-template-columns: 240rpx 1fr 100rpx;
  gap: 10rpx;
  margin-bottom: 12rpx;
}

.toolbar-btn {
  height: 74rpx;
  border-radius: 10rpx;
  background: #eef3fa;
  color: #456488;
  font-size: 24rpx;
  display: flex;
  align-items: center;
  justify-content: center;
}

.table-head,
.table-row {
  display: grid;
  gap: 8rpx;
  align-items: center;
}

.table-head text,
.table-row text {
  white-space: nowrap;
}

.ref-grid {
  min-width: 1520px;
  grid-template-columns: 260px 200px 150px 220px 150px 150px 220px 150px;
}

.req-grid {
  min-width: 1660px;
  grid-template-columns: 280px 220px 160px 140px 100px 140px 120px 220px;
}

.table-head {
  padding: 10rpx 12rpx;
  border-radius: 10rpx;
  background: #f0f5fb;
  color: #3f5a7a;
  font-size: 22rpx;
  font-weight: 600;
}

.table-row {
  padding: 12rpx;
  font-size: 22rpx;
  color: #294665;
  border-bottom: 1rpx solid #edf2f8;
}

.table-row:last-child {
  border-bottom: none;
}

.mono {
  font-family: 'Consolas', 'Courier New', monospace;
}

.status {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 999rpx;
  padding: 4rpx 10rpx;
  font-size: 20rpx;
}

.status.pending {
  color: #925500;
  background: #fff4df;
}

.status.approved {
  color: #0a6b3b;
  background: #e3f7ec;
}

.status.rejected {
  color: #a2291f;
  background: #fdeceb;
}

.empty-text {
  padding: 22rpx;
  text-align: center;
  font-size: 22rpx;
  color: #7b8ea8;
}

.modal-mask {
  position: fixed;
  top: 0;
  right: 0;
  bottom: 0;
  left: 0;
  background: rgba(10, 25, 47, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24rpx;
  z-index: 999;
}

.modal-card {
  width: 96vw;
  max-width: 1120px;
  max-height: 88vh;
  overflow-y: auto;
  background: #fff;
  border-radius: 18rpx;
  padding: 20rpx;
  box-shadow: 0 18rpx 48rpx rgba(16, 35, 69, 0.28);
}

.modal-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12rpx;
}

.modal-title {
  font-size: 30rpx;
  font-weight: 700;
  color: #1b365d;
}

.modal-close {
  width: 52rpx;
  height: 52rpx;
  border-radius: 50%;
  background: #f2f5fa;
  color: #4d6480;
  font-size: 34rpx;
  line-height: 52rpx;
  text-align: center;
}

.modal-card .form-foot {
  margin-top: 6rpx;
}

.modal-card .actions {
  gap: 8rpx;
}

.modal-card .btn {
  min-width: 106rpx;
  height: 28rpx;
  font-size: 22rpx;
  border-radius: 8rpx;
}

@media screen and (max-width: 768px) {
  .form-grid.two,
  .form-grid.three {
    grid-template-columns: 1fr;
  }

  .toolbar {
    grid-template-columns: 1fr;
  }

  .ref-grid {
    min-width: 1320px;
  }

  .req-grid {
    min-width: 1460px;
  }

  .modal-card {
    width: 100%;
    max-width: 100%;
  }
}
</style>
