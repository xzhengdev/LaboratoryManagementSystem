<template>
  <admin-layout title="资产审批" subtitle="处理教师资产申报并执行预算流转" active="assetRequests">
    <view class="admin-kpi-grid">
      <view v-for="item in summaryCards" :key="item.label" class="admin-kpi-card">
        <view class="admin-kpi-card__label">{{ item.label }}</view>
        <view class="admin-kpi-card__value">{{ item.value }}</view>
      </view>
    </view>
    <view v-if="isSystemAdmin" class="card global-budget-card">
      <view class="global-budget-card__head">
        <view class="global-budget-card__title">全校共享预算</view>
        <view class="global-budget-card__sub">三个校区共用一个总额度（锁定/已用统一计算）</view>
      </view>
      <view class="global-budget-grid">
        <view class="global-budget-item">
          <view class="global-budget-item__label">总额度</view>
          <view class="global-budget-item__value">{{ moneyText(globalBudget.total_amount) }}</view>
        </view>
        <view class="global-budget-item">
          <view class="global-budget-item__label">已锁定</view>
          <view class="global-budget-item__value">{{ moneyText(globalBudget.locked_amount) }}</view>
        </view>
        <view class="global-budget-item">
          <view class="global-budget-item__label">已使用</view>
          <view class="global-budget-item__value">{{ moneyText(globalBudget.used_amount) }}</view>
        </view>
        <view class="global-budget-item">
          <view class="global-budget-item__label">可用额度</view>
          <view class="global-budget-item__value">{{ moneyText(globalBudget.available_amount) }}</view>
        </view>
      </view>
      <view class="global-budget-form">
        <input v-model="globalBudgetInput" class="input global-budget-input" type="digit" placeholder="输入新的全校总额度，如 600000.00" />
        <view class="toolbar-btn" :class="{ disabled: globalBudgetSaving }" @click="saveGlobalBudget">
          {{ globalBudgetSaving ? '保存中...' : '更新总额度' }}
        </view>
      </view>
    </view>

    <view class="card toolbar">
      <view class="asset-mode-switch">
        <view class="asset-mode-pill" :class="{ active: panelMode === 'requests' }" @click="panelMode = 'requests'">
          申报记录
        </view>
        <view class="asset-mode-pill" :class="{ active: panelMode === 'assets' }" @click="panelMode = 'assets'">
          已入库资产
        </view>
      </view>
      <picker v-if="panelMode === 'requests'" :range="statusOptions" range-key="label" @change="changeStatus">
        <view class="input toolbar-picker">{{ currentStatusText }}</view>
      </picker>
      <input v-model="keyword" class="input toolbar-search admin-toolbar-lite__search" :placeholder="searchPlaceholder" />
      <view class="toolbar-btn" @click="reloadAll">刷新</view>
    </view>
    <view class="card ai-toolbar">
      <input
        v-model="nlQuery"
        class="input ai-toolbar__input"
        placeholder="自然语言查询：例如 查已入库的交换机资产"
      />
      <view class="ai-toolbar__btn" :class="{ disabled: nlLoading }" @click="runNlQuery">
        {{ nlLoading ? '查询中...' : 'AI查询' }}
      </view>
      <view class="ai-toolbar__btn ai-toolbar__btn--light" @click="clearNlQuery">清空</view>
    </view>
    <view v-if="nlReply" class="ai-reply">{{ nlReply }}</view>

    <view v-if="panelMode === 'requests'" class="card table-card">
        <view class="table-header req-grid">
          <text>申报单号</text>
          <text>设备信息</text>
          <text>申请人</text>
          <text>金额</text>
          <text>状态</text>
          <text>操作</text>
        </view>

        <view v-if="!filteredList.length" class="empty-text">暂无资产申报记录</view>

        <view v-for="item in filteredList" :key="rowKey(item)" class="table-row req-grid">
          <view>
            <view class="mono">{{ item.request_no }}</view>
            <view class="row-sub">{{ timeText(item.created_at) }}</view>
          </view>
          <view>
            <view class="strong">{{ item.asset_name }}</view>
            <view class="row-sub">{{ item.category }} · 数量{{ item.quantity }}</view>
          </view>
          <view>
            <view>{{ item.requester_name || '--' }}</view>
            <view class="row-sub">{{ item.campus_name || '--' }}</view>
          </view>
          <text>{{ moneyText(item.amount) }}</text>
          <text :class="statusClass(item.status)">{{ statusText(item.status) }}</text>
          <view class="actions">
            <view v-if="item.status === 'pending'" class="pill" @click="approve(item, 'approved')">通过</view>
            <view v-if="item.status === 'pending'" class="pill pill-danger" @click="approve(item, 'rejected')">驳回</view>
            <view v-if="item.status === 'approved' && !isRequestStocked(item)" class="pill pill-primary" @click="openStockInModal(item)">入库登记</view>
            <view v-if="item.status === 'approved' && isRequestStocked(item)" class="pill">已入库</view>
          </view>
        </view>
    </view>

    <view v-if="panelMode === 'assets'" class="card table-card">
        <view class="table-header asset-grid">
          <text>资产编码</text>
          <text>设备名称</text>
          <text>类别</text>
          <text>规格型号</text>
          <text>厂家</text>
          <text>存放位置</text>
          <text>金额</text>
          <text>图片</text>
        </view>

        <view v-if="!filteredAssetRows.length" class="empty-text">暂无已入库资产</view>

        <view v-for="item in filteredAssetRows" :key="rowKey(item)" class="table-row asset-grid">
          <text class="mono">{{ item.asset_code }}</text>
          <text>{{ item.asset_name }}</text>
          <text>{{ item.category }}</text>
          <text>{{ item.meta.spec_model || '--' }}</text>
          <text>{{ item.meta.manufacturer || '--' }}</text>
          <text>{{ item.meta.storage_location || '--' }}</text>
          <text>{{ moneyText(item.price) }}</text>
          <view class="asset-photo-cell">
            <view class="asset-photo-top">
              <text class="photo-count">共 {{ photoList(item).length }} 张</text>
              <text
                v-if="photoList(item).length > 3"
                class="asset-photo-more"
                @click="previewPhotos(item, 0)"
              >
                查看全部
              </text>
            </view>
            <view v-if="photoList(item).length" class="asset-photo-preview">
              <image
                v-for="(photo, idx) in photoList(item).slice(0, 3)"
                :key="photo.id || idx"
                class="asset-photo-thumb"
                :src="photo.url"
                mode="aspectFill"
                @click="previewPhotos(item, idx)"
              />
            </view>
            <view v-else class="row-sub">暂无图片</view>
          </view>
        </view>
    </view>

    <view v-if="showStockInModal" class="stock-modal-mask" @click="closeStockInModal">
      <view class="stock-modal" @click.stop>
        <view class="stock-modal__head">
          <view class="stock-modal__title">资产入库登记</view>
          <view class="stock-modal__close" @click="closeStockInModal">×</view>
        </view>

        <view class="stock-modal__hint">
          申报单：{{ currentRequest.request_no || '--' }} · {{ currentRequest.asset_name || '--' }}
        </view>

        <view class="stock-form-grid two">
          <view class="field">
            <view class="label">资产编号（可选）</view>
            <input v-model="stockInForm.asset_code" class="input" placeholder="不填则系统自动生成" />
          </view>
          <view class="field">
            <view class="label">资产状态</view>
            <picker :range="stockStatusOptions" range-key="label" :value="stockStatusIndex" @change="changeStockStatus">
              <view class="input">{{ currentStockStatusLabel }}</view>
            </picker>
          </view>
        </view>

        <view class="stock-form-grid three">
          <view class="field">
            <view class="label">规格型号</view>
            <input v-model="stockInForm.spec_model" class="input" placeholder="如：H3C S5120V3" />
          </view>
          <view class="field">
            <view class="label">厂家</view>
            <input v-model="stockInForm.manufacturer" class="input" placeholder="如：H3C" />
          </view>
          <view class="field">
            <view class="label">存放位置</view>
            <input v-model="stockInForm.storage_location" class="input" placeholder="如：理工楼508" />
          </view>
        </view>

        <view class="field">
          <view class="label">入库备注（可选）</view>
          <textarea v-model="stockInForm.description" class="input textarea" maxlength="200" placeholder="可填写采购批次、保修信息等" />
        </view>

        <view class="field">
          <view class="label">设备照片</view>
          <view class="stock-photo-wrap">
            <view class="pill pill-primary" @click="uploadStockInPhoto">上传设备照片</view>
            <text class="stock-photo-count">待上传 {{ stockInPendingPhotoPaths.length }} 张</text>
          </view>
          <view v-if="stockInPendingPhotoPaths.length" class="stock-photo-list">
            <image
              v-for="(path, idx) in stockInPendingPhotoPaths"
              :key="path || idx"
              class="stock-photo-thumb"
              :src="path"
              mode="aspectFill"
              @click="previewStockInPhotos(idx)"
            />
          </view>
        </view>

        <view class="stock-modal__foot">
          <view class="stock-btn stock-btn--primary" :class="{ disabled: stockInSubmitting }" @click="submitStockIn">
            确认入库
          </view>
          <view class="stock-btn" @click="closeStockInModal">取消</view>
        </view>
      </view>
    </view>
  </admin-layout>
</template>

<script>
import { api } from '../../api/index'
import { requireLogin } from '../../common/guard'
import { getProfile } from '../../common/session'
import { canManageEquipment, routes } from '../../config/navigation'
import { openPage } from '../../common/router'
import AdminLayout from '../../components/admin-layout.vue'

const META_FLAG = '__META__='

export default {
  components: { AdminLayout },
  data() {
    return {
      profile: {},
      requestList: [],
      assetList: [],
      globalBudget: {
        total_amount: 0,
        locked_amount: 0,
        used_amount: 0,
        available_amount: 0
      },
      globalBudgetInput: '',
      globalBudgetSaving: false,
      keyword: '',
      panelMode: 'requests',
      statusOptions: [
        { label: '全部状态', value: '' },
        { label: '待审批', value: 'pending' },
        { label: '已通过', value: 'approved' },
        { label: '已驳回', value: 'rejected' }
      ],
      selectedStatus: '',
      showStockInModal: false,
      stockInSubmitting: false,
      currentRequest: {},
      stockInPendingPhotoPaths: [],
      stockStatusOptions: [
        { label: '在用', value: 'in_use' },
        { label: '备用', value: 'spare' },
        { label: '维修中', value: 'repair' }
      ],
      nlQuery: '',
      nlLoading: false,
      nlReply: '',
      stockStatusIndex: 0,
      stockInForm: {
        asset_code: '',
        spec_model: '',
        manufacturer: '',
        storage_location: '',
        status: 'in_use',
        description: ''
      }
    }
  },
  computed: {
    isSystemAdmin() {
      return String(this.profile?.role || '') === 'system_admin'
    },
    currentStatusText() {
      const current = this.statusOptions.find((item) => item.value === this.selectedStatus)
      return current ? current.label : '全部状态'
    },
    currentStockStatusLabel() {
      return this.stockStatusOptions[this.stockStatusIndex]?.label || '在用'
    },
    searchPlaceholder() {
      if (this.panelMode === 'assets') return '搜索资产编码/名称/类别/规格/厂家/存放位置'
      return '搜索申报单号/设备名称/申请人'
    },
    filteredList() {
      const text = this.keyword.trim().toLowerCase()
      return this.requestList.filter((item) => {
        if (this.isRequestStocked(item)) return false
        const hitKeyword = !text || `${item.request_no}${item.asset_name}${item.requester_name || ''}`.toLowerCase().includes(text)
        const hitStatus = !this.selectedStatus || item.status === this.selectedStatus
        return hitKeyword && hitStatus
      })
    },
    summaryCards() {
      const pendingCount = this.requestList.filter((item) => item.status === 'pending').length
      const approvedCount = this.requestList.filter((item) => item.status === 'approved' && !this.isRequestStocked(item)).length
      const totalAmount = this.requestList.reduce((sum, item) => sum + Number(item.amount || 0), 0)
      return [
        { label: '待审批', value: String(pendingCount) },
        { label: '已通过', value: String(approvedCount) },
        { label: '申报总额', value: this.moneyText(totalAmount) }
      ]
    },
    assetRows() {
      return this.assetList.map((item) => ({
        ...item,
        meta: this.parseMeta(item?.description)
      }))
    },
    stockedRequestIdSet() {
      const set = new Set()
      this.assetList.forEach((item) => {
        const requestId = item?.request_id
        const campusId = item?.campus_id
        if (
          requestId !== undefined && requestId !== null && requestId !== '' &&
          campusId !== undefined && campusId !== null && campusId !== ''
        ) {
          set.add(`${campusId}:${requestId}`)
        }
      })
      return set
    },
    filteredAssetRows() {
      const text = this.keyword.trim().toLowerCase()
      if (!text) return this.assetRows
      return this.assetRows.filter((item) => {
        const meta = item?.meta || {}
        const fields = [
          item?.asset_code,
          item?.asset_name,
          item?.category,
          meta?.spec_model,
          meta?.manufacturer,
          meta?.storage_location
        ]
        return fields.some((field) => String(field || '').toLowerCase().includes(text))
      })
    }
  },
  async onShow() {
    if (!requireLogin()) return
    this.profile = getProfile()
    if (!canManageEquipment(this.profile.role)) {
      uni.showToast({ title: '当前角色无权限访问', icon: 'none' })
      openPage(routes.home, { replace: true })
      return
    }
    await this.reloadAll()
  },
  methods: {
    moneyText(value) {
      const num = Number(value || 0)
      if (!Number.isFinite(num)) return '¥0.00'
      return `¥${num.toFixed(2)}`
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
    photoList(item) {
      return Array.isArray(item?.photos) ? item.photos.filter((row) => row && row.url) : []
    },
    changeStatus(event) {
      this.selectedStatus = this.statusOptions[event.detail.value].value
    },
    changeStockStatus(event) {
      const idx = Number(event.detail.value || 0)
      this.stockStatusIndex = idx
      this.stockInForm.status = this.stockStatusOptions[idx]?.value || 'in_use'
    },
    rowKey(item) {
      const campusId = item?.campus_id ?? 'x'
      const id = item?.id ?? 'x'
      return `${campusId}-${id}`
    },
    isRequestStocked(item) {
      const requestId = item?.id
      const campusId = item?.campus_id
      if (
        requestId === undefined || requestId === null || requestId === '' ||
        campusId === undefined || campusId === null || campusId === ''
      ) {
        return false
      }
      return this.stockedRequestIdSet.has(`${campusId}:${requestId}`)
    },
    async reloadAll() {
      const [requestList, assetList] = await Promise.all([
        api.assetRequests(),
        api.assets()
      ])
      this.requestList = Array.isArray(requestList) ? requestList : []
      this.assetList = Array.isArray(assetList) ? assetList : []
      this.nlReply = ''
      if (this.isSystemAdmin) {
        await this.loadGlobalBudget()
      }
    },
    async runNlQuery() {
      const message = String(this.nlQuery || '').trim()
      if (!message || this.nlLoading) return
      this.nlLoading = true
      try {
        const result = await api.adminQuery({
          domain: 'assets',
          message,
          context: { mode: this.panelMode }
        })
        const filters = result?.filters && typeof result.filters === 'object' ? result.filters : {}
        const panelMode = String(filters.panel_mode || this.panelMode || '').toLowerCase()
        if (panelMode === 'assets' || panelMode === 'requests') {
          this.panelMode = panelMode
        }
        if (Array.isArray(result?.items)) {
          if (this.panelMode === 'assets') {
            this.assetList = result.items
          } else {
            this.requestList = result.items
          }
        }
        this.keyword = String(filters.keyword || '')
        if (this.panelMode === 'requests') {
          this.selectedStatus = String(filters.status || '')
        } else {
          this.selectedStatus = ''
        }
        this.nlReply = String(result?.reply || '查询完成')
      } catch (error) {
        uni.showToast({ title: error?.message || 'AI查询失败', icon: 'none' })
      } finally {
        this.nlLoading = false
      }
    },
    async clearNlQuery() {
      this.nlQuery = ''
      this.nlReply = ''
      this.keyword = ''
      this.selectedStatus = ''
      await this.reloadAll()
    },
    async loadGlobalBudget() {
      const row = await api.globalAssetBudget()
      this.globalBudget = {
        total_amount: Number(row?.total_amount || 0),
        locked_amount: Number(row?.locked_amount || 0),
        used_amount: Number(row?.used_amount || 0),
        available_amount: Number(row?.available_amount || 0)
      }
      this.globalBudgetInput = String(this.globalBudget.total_amount || '')
    },
    async saveGlobalBudget() {
      if (this.globalBudgetSaving) return
      const amount = Number(this.globalBudgetInput || 0)
      if (!Number.isFinite(amount) || amount <= 0) {
        uni.showToast({ title: '请输入有效总额度', icon: 'none' })
        return
      }
      this.globalBudgetSaving = true
      try {
        await api.updateGlobalAssetBudget({
          total_amount: amount,
          remark: '全校共享预算总额'
        })
        uni.showToast({ title: '总额度已更新', icon: 'success' })
        await this.loadGlobalBudget()
      } finally {
        this.globalBudgetSaving = false
      }
    },
    async approve(item, status) {
      await api.reviewAssetRequest(item.id, {
        campus_id: item.campus_id,
        approval_status: status,
        remark: status === 'approved' ? '审批通过' : '审批驳回'
      })
      uni.showToast({ title: status === 'approved' ? '已通过' : '已驳回', icon: 'success' })
      await this.reloadAll()
    },
    openStockInModal(item) {
      this.currentRequest = item || {}
      this.stockInPendingPhotoPaths = []
      this.stockStatusIndex = 0
      this.stockInForm = {
        asset_code: '',
        spec_model: '',
        manufacturer: '',
        storage_location: '',
        status: 'in_use',
        description: ''
      }
      this.showStockInModal = true
    },
    closeStockInModal() {
      if (this.stockInSubmitting) return
      this.showStockInModal = false
    },
    async submitStockIn() {
      if (this.stockInSubmitting) return
      const spec_model = String(this.stockInForm.spec_model || '').trim()
      const manufacturer = String(this.stockInForm.manufacturer || '').trim()
      const storage_location = String(this.stockInForm.storage_location || '').trim()

      if (!spec_model) {
        uni.showToast({ title: '请填写规格型号', icon: 'none' })
        return
      }
      if (!manufacturer) {
        uni.showToast({ title: '请填写厂家', icon: 'none' })
        return
      }
      if (!storage_location) {
        uni.showToast({ title: '请填写存放位置', icon: 'none' })
        return
      }

      this.stockInSubmitting = true
      try {
        const createdAsset = await api.stockInAsset(this.currentRequest.id, {
          campus_id: this.currentRequest.campus_id,
          asset_code: String(this.stockInForm.asset_code || '').trim(),
          status: this.stockInForm.status || 'in_use',
          spec_model,
          manufacturer,
          storage_location,
          description: String(this.stockInForm.description || '').trim()
        })

        this.showStockInModal = false
        this.panelMode = 'assets'
        this.keyword = ''
        const optimisticAsset = createdAsset
          ? {
              ...createdAsset,
              photos: Array.isArray(createdAsset.photos) ? createdAsset.photos : []
            }
          : null
        if (optimisticAsset) {
          this.assetList = [optimisticAsset, ...this.assetList]
        }

        let uploadSuccess = 0
        let uploadFailed = 0
        const filePaths = Array.isArray(this.stockInPendingPhotoPaths) ? this.stockInPendingPhotoPaths : []
        if (createdAsset?.id && filePaths.length) {
          for (const filePath of filePaths) {
            try {
              await api.uploadAssetPhoto(createdAsset.id, filePath, { campus_id: createdAsset.campus_id })
              uploadSuccess += 1
            } catch (_error) {
              uploadFailed += 1
            }
          }
        }

        if (uploadFailed > 0) {
          uni.showToast({ title: `入库成功，图片成功${uploadSuccess}张，失败${uploadFailed}张`, icon: 'none' })
        } else if (uploadSuccess > 0) {
          uni.showToast({ title: `入库成功，已上传${uploadSuccess}张图片`, icon: 'success' })
        } else {
          uni.showToast({ title: '入库成功', icon: 'success' })
        }
        await this.reloadAll()
      } finally {
        this.stockInSubmitting = false
      }
    },
    previewPhotos(item, index = 0) {
      const urls = this.photoList(item).map((row) => row.url)
      if (!urls.length) return
      uni.previewImage({ urls, current: urls[index] || urls[0] })
    },
    previewStockInPhotos(index = 0) {
      const urls = this.stockInPendingPhotoPaths.filter(Boolean)
      if (!urls.length) return
      uni.previewImage({ urls, current: urls[index] || urls[0] })
    },
    uploadStockInPhoto() {
      uni.chooseImage({
        count: 6,
        sizeType: ['compressed'],
        sourceType: ['album', 'camera'],
        success: async (res) => {
          const selected = Array.isArray(res?.tempFilePaths) ? res.tempFilePaths : []
          if (!selected.length) return
          const merged = [...this.stockInPendingPhotoPaths, ...selected]
          const dedup = [...new Set(merged)].slice(0, 9)
          this.stockInPendingPhotoPaths = dedup
        },
        fail: () => {
          uni.showToast({ title: '未选择图片', icon: 'none' })
        }
      })
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
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 24rpx;
  margin-bottom: 28rpx;
}

.admin-kpi-card {
  border-radius: 22rpx;
  border: 1rpx solid #dbe4f1;
  background: #fff;
  padding: 24rpx;
}

.admin-kpi-card__label {
  color: #6d7f95;
  font-size: 22rpx;
  font-weight: 700;
}

.admin-kpi-card__value {
  margin-top: 10rpx;
  font-size: 40rpx;
  font-weight: 800;
  color: #132d4d;
}

.global-budget-card {
  margin-bottom: 24rpx;
  border-radius: 22rpx;
  border: 1rpx solid #dbe4f1;
  background: #fff;
}

.global-budget-card__head {
  margin-bottom: 14rpx;
}

.global-budget-card__title {
  font-size: 30rpx;
  font-weight: 800;
  color: #133254;
}

.global-budget-card__sub {
  margin-top: 4rpx;
  font-size: 22rpx;
  color: #6e829d;
}

.global-budget-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12rpx;
}

.global-budget-item {
  border: 1rpx solid #e4ecf6;
  border-radius: 16rpx;
  background: #f7faff;
  padding: 14rpx 16rpx;
}

.global-budget-item__label {
  font-size: 20rpx;
  color: #667d99;
}

.global-budget-item__value {
  margin-top: 6rpx;
  font-size: 30rpx;
  font-weight: 800;
  color: #183a60;
}

.global-budget-form {
  margin-top: 14rpx;
  display: flex;
  gap: 12rpx;
  align-items: center;
}

.global-budget-input {
  flex: 1;
  height: 68rpx;
  border-radius: 24rpx;
  background: #fff;
  border: 1rpx solid #e4ebf5;
  padding: 0 24rpx;
}

.toolbar {
  margin-bottom: 28rpx;
  display: flex;
  align-items: center;
  gap: 16rpx;
  flex-wrap: nowrap;
  border-radius: 26rpx;
  background: #f0f4fa;
  border: 1rpx solid #dce7f4;
  box-shadow: 0 12rpx 32rpx rgba(16, 42, 73, 0.08);
  transition: all 0.25s ease;
  padding: 24rpx !important;
}

.ai-toolbar {
  margin-bottom: 20rpx;
  display: flex;
  align-items: center;
  gap: 12rpx;
  padding: 20rpx !important;
  border-radius: 22rpx;
  background: #f6faf6;
  border: 1rpx solid #d7e7da;
}

.ai-toolbar__input {
  flex: 1;
  height: 64rpx;
  border-radius: 20rpx;
  border: 1rpx solid #d8e4dc;
  background: #ffffff;
  padding: 0 20rpx;
}

.ai-toolbar__btn {
  min-width: 140rpx;
  height: 64rpx;
  border-radius: 20rpx;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: #1f6f54;
  color: #fff;
  font-size: 22rpx;
  font-weight: 700;
}

.ai-toolbar__btn--light {
  background: #eef4f0;
  color: #2b4d3f;
}

.ai-toolbar__btn.disabled {
  opacity: 0.65;
  pointer-events: none;
}

.ai-reply {
  margin: -6rpx 0 18rpx;
  padding: 12rpx 16rpx;
  border-radius: 14rpx;
  background: #f1f8f2;
  color: #2a5a47;
  font-size: 22rpx;
  border: 1rpx solid #d6e9db;
}

.toolbar:hover {
  transform: translateY(-3rpx);
  box-shadow: 0 18rpx 44rpx rgba(16, 42, 73, 0.1);
}

.toolbar-picker {
  min-width: 220rpx;
  height: 68rpx;
  padding: 0 24rpx;
  border-radius: 24rpx;
  border: 1rpx solid #e4ebf5;
  background: #f4f7fc;
  display: flex;
  align-items: center;
  color: #486280;
  transition: all 0.2s ease;
}

.toolbar-search {
  flex: 1;
}

.admin-toolbar-lite__search {
  flex: 1;
  height: 68rpx;
  padding: 0 24rpx;
  border-radius: 24rpx;
  background-color: #ffffff;
  border: 1rpx solid #e4ebf5;
  font-size: 24rpx;
  color: #132d4d;
  transition: all 0.2s ease;
}

.admin-toolbar-lite__search:focus {
  border-color: #2c7da0;
  background-color: #ffffff;
  outline: none;
  box-shadow: 0 0 0 4rpx rgba(44, 125, 160, 0.1);
}

.toolbar-btn {
  width: 190rpx;
  flex-shrink: 0;
  height: 68rpx;
  padding: 0 16rpx;
  border-radius: 24rpx;
  background: linear-gradient(180deg, #ffffff 0%, #dcf1ff 100%);
  border: 1rpx solid #c8e3f6;
  color: #2b4864;
  font-size: 24rpx;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 8rpx 20rpx rgba(77, 123, 160, 0.18);
  transition: all 0.2s ease;
}

.toolbar-btn:hover {
  background: linear-gradient(180deg, #ffffff 0%, #dcf1ff 100%);
  transform: translateY(-1rpx);
  box-shadow: 0 12rpx 26rpx rgba(77, 123, 160, 0.24);
}

.toolbar-btn.disabled {
  opacity: 0.65;
  pointer-events: none;
}

.toolbar .input {
  height: 68rpx;
  line-height: 68rpx;
  border-radius: 24rpx;
  font-size: 24rpx;
  margin-top: 0;
  padding: 0 24rpx;
  box-sizing: border-box;
}

.toolbar-picker {
  display: flex;
  align-items: center;
}

.toolbar-picker:hover {
  background: #ffffff;
}

.toolbar .toolbar-search {
  height: 68rpx;
  line-height: 68rpx;
  padding: 0 24rpx;
  border-radius: 24rpx;
  font-size: 24rpx;
}
.asset-mode-switch {
  height: 68rpx;
  padding: 0 8rpx;
  border-radius: 24rpx;
  border: 1rpx solid #e4ebf5;
  background: #ffffff;
  display: inline-flex;
  align-items: center;
  gap: 8rpx;
}

.asset-mode-pill {
  min-width: 150rpx;
  height: 52rpx;
  padding: 0 16rpx;
  border-radius: 14rpx;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: #5a6e88;
  font-size: 22rpx;
  font-weight: 700;
}

.asset-mode-pill.active {
  background: #e9f1fb;
  color: #1f4872;
}

.table-card {
  border: 1rpx solid #dbe4f1;
  background: #fff;
  border-radius: 22rpx;
  margin-bottom: 0;
}

.req-grid {
  grid-template-columns: 1.6fr 1.3fr 1fr 0.8fr 0.8fr 1.2fr;
}

.asset-grid {
  grid-template-columns: 1.6fr 1.1fr 0.9fr 1.2fr 0.9fr 1.2fr 0.8fr 1.6fr;
}

.table-header {
  display: grid;
  gap: 10rpx;
  padding: 18rpx 16rpx;
  background: #f4f7fb;
  border-bottom: 1rpx solid #e5ecf5;
  color: #6d7f95;
  font-size: 22rpx;
  font-weight: 700;
}

.table-row {
  display: grid;
  gap: 10rpx;
  align-items: center;
  padding: 20rpx 16rpx;
  border-bottom: 1rpx solid #edf2f7;
  color: #173350;
  font-size: 22rpx;
}

.table-row:last-child {
  border-bottom: none;
}

.row-sub {
  margin-top: 4rpx;
  color: #73869f;
  font-size: 20rpx;
}

.strong {
  font-weight: 800;
  color: #0f2744;
}

.mono {
  font-family: Consolas, monospace;
}

.actions {
  display: flex;
  gap: 8rpx;
  flex-wrap: wrap;
}

.pill {
  padding: 0 14rpx;
  height: 46rpx;
  border-radius: 18rpx;
  border: 1rpx solid #c8e3f6;
  color: #2b4864;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(180deg, #ffffff 0%, #dcf1ff 100%);
}

.pill-danger {
  border-color: #f0c9c9;
  color: #b33d3d;
  background: #fff1f1;
}

.pill-primary {
  border-color: #b8d9f2;
  color: #2b4864;
  background: linear-gradient(180deg, #ffffff 0%, #dcf1ff 100%);
}

.status {
  font-weight: 700;
}

.status.pending {
  color: #ad7a00;
}

.status.approved {
  color: #0a7a40;
}

.status.rejected {
  color: #c13333;
}

.empty-text {
  padding: 20rpx 16rpx;
  color: #7a8ca3;
  font-size: 22rpx;
}

.asset-photo-cell {
  display: flex;
  flex-direction: column;
  gap: 8rpx;
  padding-left: 20rpx;
}

.asset-photo-top {
  display: flex;
  align-items: center;
  gap: 8rpx;
  flex-wrap: wrap;
}

.photo-count {
  color: #60738e;
  font-size: 20rpx;
}

.asset-photo-preview {
  display: flex;
  align-items: center;
  gap: 8rpx;
  flex-wrap: wrap;
}

.asset-photo-thumb {
  width: 72rpx;
  height: 72rpx;
  border-radius: 10rpx;
  border: 1rpx solid #d9e4f2;
}

.asset-photo-more {
  color: #2c7da0;
  font-size: 20rpx;
}

.stock-modal-mask {
  position: fixed;
  top: 0;
  right: 0;
  bottom: 0;
  left: 0;
  background: rgba(14, 30, 52, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24rpx;
  z-index: 999;
}

.stock-modal {
  width: 96vw;
  max-width: 980px;
  max-height: 88vh;
  overflow-y: auto;
  background: #fff;
  border-radius: 18rpx;
  padding: 20rpx;
  box-shadow: 0 18rpx 48rpx rgba(16, 35, 69, 0.28);
}

.stock-modal__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10rpx;
}

.stock-modal__title {
  font-size: 30rpx;
  font-weight: 700;
  color: #1b365d;
}

.stock-modal__close {
  width: 52rpx;
  height: 52rpx;
  border-radius: 50%;
  background: #f2f5fa;
  color: #4d6480;
  font-size: 34rpx;
  line-height: 52rpx;
  text-align: center;
}

.stock-modal__hint {
  font-size: 22rpx;
  color: #60738e;
  margin-bottom: 12rpx;
}

.stock-modal .input {
  margin-top: 6rpx;
  border-radius: 10rpx;
  font-size: 22rpx;
}

.stock-modal input.input,
.stock-modal .stock-form-grid .input {
  height: 56rpx;
  line-height: 56rpx;
  padding: 0 14rpx;
}

.stock-form-grid {
  display: grid;
  gap: 12rpx;
  margin-bottom: 12rpx;
}

.stock-form-grid.two {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.stock-form-grid.three {
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

.textarea {
  min-height: 96rpx;
  padding: 10rpx 14rpx;
  line-height: 1.5;
}

.stock-photo-wrap {
  display: flex;
  align-items: center;
  gap: 12rpx;
  flex-wrap: wrap;
}

.stock-photo-count {
  color: #60738e;
  font-size: 20rpx;
}

.stock-photo-list {
  margin-top: 10rpx;
  display: flex;
  align-items: center;
  gap: 10rpx;
  flex-wrap: wrap;
}

.stock-photo-thumb {
  width: 84rpx;
  height: 84rpx;
  border-radius: 10rpx;
  border: 1rpx solid #d9e4f2;
}

.stock-modal__foot {
  margin-top: 6rpx;
  display: flex;
  justify-content: flex-end;
  gap: 8rpx;
}

.stock-btn {
  min-width: 110rpx;
  height: 52rpx;
  border-radius: 20rpx;
  background: linear-gradient(180deg, #ffffff 0%, #dcf1ff 100%);
  border: 1rpx solid #c8e3f6;
  color: #2b4864;
  font-size: 22rpx;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.stock-btn--primary {
  background: linear-gradient(180deg, #ffffff 0%, #dcf1ff 100%);
  color: #2b4864;
}

.stock-btn.disabled {
  opacity: 0.65;
}

@media screen and (max-width: 1200px) {
  .admin-kpi-grid {
    grid-template-columns: 1fr;
  }

  .global-budget-grid {
    grid-template-columns: 1fr 1fr;
  }
}

@media screen and (max-width: 768px) {
  .global-budget-form {
    flex-direction: column;
    align-items: stretch;
  }

  .global-budget-grid {
    grid-template-columns: 1fr;
  }

  .toolbar {
    flex-direction: column;
    align-items: stretch;
  }

  .toolbar-picker,
  .asset-mode-switch,
  .toolbar-search,
  .toolbar-btn {
    width: 100%;
    min-width: 0;
  }

  .ai-toolbar {
    flex-direction: column;
    align-items: stretch;
  }

  .ai-toolbar__input,
  .ai-toolbar__btn {
    width: 100%;
  }

  .table-header {
    display: none;
  }

  .table-row {
    grid-template-columns: 1fr;
    gap: 8rpx;
  }

  .stock-form-grid.two,
  .stock-form-grid.three {
    grid-template-columns: 1fr;
  }
}
</style>

