<template>
  <admin-layout title="设备管理" subtitle="维护设备状态与实验室归属" active="equipment">
    <view class="admin-kpi-grid">
      <view v-for="item in summaryCards" :key="item.label" class="admin-kpi-card">
        <view class="admin-kpi-card__label">{{ item.label }}</view>
        <view class="admin-kpi-card__value">{{ item.value }}</view>
      </view>
    </view>

    <view class="card admin-toolbar-lite">
      <picker :range="labOptions" range-key="lab_name" @change="changeLab">
        <view class="input toolbar-picker admin-toolbar-lite__picker">{{ currentLabName }}</view>
      </picker>
      <input v-model="keyword" class="input admin-toolbar-lite__search" style="flex: 1;" placeholder="搜索设备名称或所属实验室" />
      <view class="admin-toolbar-lite__btn" @click="openEditor()">新增设备</view>
    </view>

    <view class="card table-card">
      <view class="table-header equipment-grid">
        <text>设备名称</text>
        <text>所属实验室</text>
        <text>数量</text>
        <text>状态</text>
        <text>操作</text>
      </view>
      <view v-for="item in filteredList" :key="item.id" class="table-row equipment-grid">
        <text class="table-strong">{{ item.equipment_name }}</text>
        <text>{{ item.lab_name }}</text>
        <text>{{ item.quantity }}</text>
        <status-tag :status="item.status === 'active' ? 'active' : 'disabled'" />
        <view class="actions">
          <view class="pill" @click="openEditor(item)">编辑</view>
          <view class="pill pill-danger" @click="toggleStatus(item)">
            {{ item.status === 'active' ? '停用' : '启用' }}
          </view>
        </view>
      </view>
    </view>

    <view v-if="editorVisible" class="admin-modal-mask" @click="closeEditor">
      <view class="admin-modal admin-equipment-modal" @click.stop>
        <view class="admin-equipment-modal__head">
          <view class="admin-equipment-modal__title">{{ editingId ? '编辑设备' : '新增设备' }}</view>
          <view class="admin-equipment-modal__close" @click="closeEditor">×</view>
        </view>
        <view class="field">
          <text class="label">所属实验室</text>
          <picker :range="editableLabOptions" range-key="lab_name" @change="selectEditorLab">
            <view class="input admin-equipment-input admin-equipment-input--line">{{ editorLabName }}</view>
          </picker>
        </view>
        <view class="field">
          <text class="label">设备名称</text>
          <input v-model="form.equipment_name" class="input admin-equipment-input admin-equipment-input--line" />
        </view>
        <view class="field">
          <text class="label">数量</text>
          <input v-model="form.quantity" class="input admin-equipment-input admin-equipment-input--line" type="number" />
        </view>
        <view class="field">
          <text class="label">状态</text>
          <picker :range="statusOptions" range-key="label" @change="selectStatus">
            <view class="input admin-equipment-input admin-equipment-input--line">{{ currentStatusText }}</view>
          </picker>
        </view>
        <view class="actions admin-equipment-modal__actions">
          <view class="admin-equipment-btn admin-equipment-btn--ghost" @click="closeEditor">取消</view>
          <view class="admin-equipment-btn admin-equipment-btn--primary" @click="saveEquipment">保存</view>
        </view>
      </view>
    </view>
  </admin-layout>
</template>

<script>
import { api } from '../../api/index'
import { requireLogin } from '../../common/guard'
import { getProfile } from '../../common/session'
import { canManageEquipment, isSystemAdmin } from '../../config/navigation'
import AdminLayout from '../../components/admin-layout.vue'
import StatusTag from '../../components/status-tag.vue'

export default {
  components: { AdminLayout, StatusTag },
  data() {
    return {
      profile: {},
      list: [],
      keyword: '',
      selectedLabId: '',
      labOptions: [{ id: '', lab_name: '全部实验室' }],
      editorVisible: false,
      editingId: '',
      saving: false,
      statusOptions: [
        { label: '启用', value: 'active' },
        { label: '停用', value: 'disabled' }
      ],
      form: {
        lab_id: '',
        equipment_name: '',
        quantity: '1',
        status: 'active'
      }
    }
  },
  computed: {
    editableLabOptions() {
      return this.labOptions.filter((item) => item.id !== '')
    },
    currentLabName() {
      const current = this.labOptions.find((item) => String(item.id) === String(this.selectedLabId))
      return current ? current.lab_name : '全部实验室'
    },
    editorLabName() {
      const current = this.editableLabOptions.find((item) => String(item.id) === String(this.form.lab_id))
      return current ? current.lab_name : '请选择实验室'
    },
    currentStatusText() {
      const current = this.statusOptions.find((item) => item.value === this.form.status)
      return current ? current.label : '请选择状态'
    },
    filteredList() {
      const text = this.keyword.trim().toLowerCase()
      return this.list.filter((item) => {
        const hitKeyword = !text || `${item.equipment_name}${item.lab_name}`.toLowerCase().includes(text)
        const hitLab = !this.selectedLabId || String(item.lab_id) === String(this.selectedLabId)
        return hitKeyword && hitLab
      })
    },
    summaryCards() {
      const total = this.list.reduce((sum, item) => sum + Number(item.quantity || 0), 0)
      const activeCount = this.list.filter((item) => item.status === 'active').length
      return [
        { label: '设备种类', value: this.list.length },
        { label: '设备总量', value: total },
        { label: '可用记录', value: activeCount }
      ]
    }
  },
  async onShow() {
    if (!requireLogin()) return
    this.profile = getProfile()
    if (!canManageEquipment(this.profile.role)) return

    await this.fetchEquipmentPageData()
  },
  methods: {
    async fetchEquipmentPageData() {
      const [equipment, labs] = await Promise.all([api.equipment(), api.labs()])
      const allowedLabs = isSystemAdmin(this.profile.role)
        ? labs
        : labs.filter((item) => String(item.campus_id) === String(this.profile.campus_id))

      const allowedLabIdSet = new Set(allowedLabs.map((item) => String(item.id)))
      this.list = equipment.filter((item) => allowedLabIdSet.has(String(item.lab_id)))

      this.labOptions = [{ id: '', lab_name: '全部实验室' }].concat(
        allowedLabs.map((item) => ({ id: item.id, lab_name: item.lab_name }))
      )

      if (!isSystemAdmin(this.profile.role) && this.labOptions.length > 1) {
        this.selectedLabId = ''
        if (!this.form.lab_id) this.form.lab_id = this.labOptions[1].id
      }
    },
    changeLab(event) {
      this.selectedLabId = this.labOptions[event.detail.value].id
    },
    selectEditorLab(event) {
      this.form.lab_id = this.editableLabOptions[event.detail.value].id
    },
    selectStatus(event) {
      this.form.status = this.statusOptions[event.detail.value].value
    },
    openEditor(item) {
      this.editorVisible = true
      if (!item) {
        this.editingId = ''
        const firstLabId = this.editableLabOptions.length ? this.editableLabOptions[0].id : ''
        this.form = { lab_id: firstLabId, equipment_name: '', quantity: '1', status: 'active' }
        return
      }
      this.editingId = item.id
      this.form = {
        lab_id: item.lab_id,
        equipment_name: item.equipment_name,
        quantity: String(item.quantity),
        status: item.status
      }
    },
    closeEditor() {
      this.editorVisible = false
      this.editingId = ''
    },
    async saveEquipment() {
      if (this.saving) return
      const lab_id = this.form.lab_id
      const equipment_name = (this.form.equipment_name || '').trim()
      const quantity = Number(this.form.quantity)
      const status = this.form.status

      if (!lab_id) {
        uni.showToast({ title: '请选择所属实验室', icon: 'none' })
        return
      }
      if (!equipment_name) {
        uni.showToast({ title: '请输入设备名称', icon: 'none' })
        return
      }
      if (!Number.isFinite(quantity) || quantity < 0) {
        uni.showToast({ title: '请输入合法数量', icon: 'none' })
        return
      }

      this.saving = true
      try {
        if (this.editingId) {
          await api.updateEquipment(this.editingId, { equipment_name, quantity, status })
        } else {
          await api.createEquipment({ lab_id, equipment_name, quantity, status })
        }
        await this.fetchEquipmentPageData()
        uni.showToast({ title: '保存成功', icon: 'success' })
        this.closeEditor()
      } catch (error) {
        uni.showToast({ title: error?.message || '保存失败', icon: 'none' })
      } finally {
        this.saving = false
      }
    },
    async toggleStatus(item) {
      const nextStatus = item.status === 'active' ? 'disabled' : 'active'
      try {
        await api.updateEquipment(item.id, { status: nextStatus })
        await this.fetchEquipmentPageData()
        uni.showToast({ title: nextStatus === 'active' ? '已启用' : '已停用', icon: 'success' })
      } catch (error) {
        uni.showToast({ title: error?.message || '状态更新失败', icon: 'none' })
      }
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

.card,
.admin-kpi-card,
.table-card {
  border-radius: 24rpx;
  box-shadow: 0 12rpx 32rpx rgba(16, 42, 73, 0.08);
  transition: all 0.25s ease;
}

.card:hover,
.admin-kpi-card:hover,
.table-card:hover {
  transform: translateY(-4rpx);
  box-shadow: 0 20rpx 48rpx rgba(16, 42, 73, 0.12);
}

.admin-kpi-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 24rpx;
  margin-bottom: 28rpx;
}

.admin-kpi-card {
  border-radius: 26rpx;
  border: 1rpx solid #dbe4f1;
  background: #fff;
  padding: 24rpx 28rpx;
}

.admin-kpi-card__label {
  color: #6d7f95;
  font-size: 22rpx;
  font-weight: 600;
}

.admin-kpi-card__value {
  margin-top: 10rpx;
  font-size: 52rpx;
  font-weight: 800;
  color: #132d4d;
  line-height: 1.1;
}

.admin-toolbar-lite {
  margin-bottom: 28rpx;
  display: flex;
  align-items: center;
  gap: 16rpx;
  flex-wrap: nowrap;
  border-radius: 24rpx;
  background: #f0f4fa;
  border: 1rpx solid #dce7f4;
  box-shadow: 0 10rpx 26rpx rgba(16, 42, 73, 0.06);
  transition: all 0.25s ease;
  padding: 24rpx !important;
}

.admin-toolbar-lite:hover {
  transform: translateY(-3rpx);
  box-shadow: 0 18rpx 44rpx rgba(16, 42, 73, 0.1);
}

.admin-toolbar-lite__btn {
  width: 190rpx;
  flex-shrink: 0;
  height: 68rpx;
  padding: 0 16rpx;
  border-radius: 24rpx;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background-color: #2c7da0;
  color: #ffffff;
  font-size: 24rpx;
  font-weight: 700;
  box-shadow: 0 8rpx 20rpx rgba(44, 125, 160, 0.25);
  transition: all 0.2s ease;
}

.admin-toolbar-lite__btn:hover {
  background-color: #256a86;
  transform: translateY(-2rpx);
  box-shadow: 0 12rpx 28rpx rgba(44, 125, 160, 0.35);
}

.admin-toolbar-lite__btn:active {
  transform: scale(0.96);
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
  box-shadow: 0 0 0 4rpx rgba(44, 125, 160, 0.1);
  outline: none;
}

.toolbar-picker {
  min-width: 240rpx;
}

.admin-toolbar-lite__picker {
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

.admin-toolbar-lite__picker:hover {
  background: #ffffff;
}

.table-card {
  border: 1rpx solid #dbe4f1;
  background: #ffffff;
  overflow: hidden;
}

.equipment-grid {
  grid-template-columns: 1.4fr 1.2fr 0.7fr 0.7fr 1fr;
}

.table-header {
  background: #f4f7fb;
  border-bottom: 1rpx solid #e5ecf5;
  color: #6d7f95;
  font-weight: 600;
}

.table-row {
  border-bottom: 1rpx solid #edf2f7;
  padding-top: 28rpx !important;
  padding-bottom: 28rpx !important;
  transition: all 0.2s ease;
}

.table-row:hover {
  background: #f7faff;
}

.table-header.equipment-grid text:first-child,
.table-row.equipment-grid text:first-child {
  padding-left: 20rpx;
}

.table-strong {
  color: #0f2744;
  font-weight: 800;
}

.table-row .tag {
  position: relative;
  display: inline-flex;
  align-items: center;
  width: fit-content;
  padding: 0 0 0 24rpx;
  border: none;
  border-radius: 0;
  background: transparent !important;
  font-size: 24rpx;
  font-weight: 800;
}

.table-row .tag::before {
  content: '';
  position: absolute;
  left: 0;
  top: 50%;
  width: 16rpx;
  height: 16rpx;
  border-radius: 999rpx;
  transform: translateY(-50%);
  background: currentColor;
}

.table-row .tag-active {
  color: #0d749e !important;
}

.table-row .tag-disabled {
  color: #c81e1e !important;
}

.pill {
  border: 1rpx solid #d9e4f2;
  background: #ffffff;
  color: #476183;
  transition: all 0.2s ease;
}

.pill:hover {
  opacity: 0.92;
  transform: translateY(-1rpx);
  background: #f6f9fd;
}

.pill-danger {
  border-color: #efcaca;
  color: #c94747;
}

.admin-modal-mask {
  background: rgba(10, 26, 45, 0.4);
  backdrop-filter: blur(4rpx);
}

.admin-equipment-modal {
  width: 760rpx;
  max-width: calc(100vw - 64rpx);
  border-radius: 28rpx;
  padding: 28rpx 28rpx 24rpx;
  background: #ffffff;
  box-shadow: 0 30rpx 80rpx rgba(9, 36, 69, 0.22);
  animation: equipment-modal-in 180ms ease-out;
}

.admin-equipment-modal__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14rpx;
}

.admin-equipment-modal__title {
  font-size: 34rpx;
  font-weight: 800;
  color: #142d4e;
}

.admin-equipment-modal__close {
  width: 56rpx;
  height: 56rpx;
  border-radius: 999rpx;
  background: #edf3fb;
  color: #476183;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 34rpx;
  line-height: 1;
  transition: all 0.2s ease;
}

.admin-equipment-modal__close:hover {
  opacity: 0.92;
  transform: translateY(-1rpx);
}

.admin-equipment-input {
  border-radius: 14rpx;
  background: #ffffff;
  border: 1rpx solid #dbe6f4;
  transition: all 0.2s ease;
}

.admin-equipment-input--line {
  height: 78rpx;
  line-height: 78rpx;
  padding: 0 22rpx;
}

.admin-equipment-input:focus {
  border-color: #2c7da0;
  background: #ffffff;
  box-shadow: 0 0 0 4rpx rgba(44, 125, 160, 0.1);
}

.admin-equipment-modal__actions {
  margin-top: 20rpx;
  justify-content: flex-end;
  gap: 12rpx;
}

.admin-equipment-btn {
  min-width: 160rpx;
  height: 62rpx;
  border-radius: 12rpx;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 24rpx;
  font-weight: 700;
  transition: all 0.2s ease;
}

.admin-equipment-btn:hover {
  opacity: 0.92;
  transform: translateY(-1rpx);
}

.admin-equipment-btn--ghost {
  background: #eef3fb;
  color: #486280;
}

.admin-equipment-btn--primary {
  background: linear-gradient(135deg, #2c7da0, #276f8f);
  color: #fff;
  box-shadow: 0 8rpx 20rpx rgba(44, 125, 160, 0.28);
}

@keyframes equipment-modal-in {
  from {
    opacity: 0;
    transform: translateY(16rpx) scale(0.98);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

@media screen and (max-width: 1200px) {
  .admin-kpi-grid {
    grid-template-columns: 1fr;
  }
}

@media screen and (max-width: 768px) {
  .admin-kpi-grid {
    gap: 16rpx;
    margin-bottom: 20rpx;
  }

  .admin-kpi-card {
    padding: 20rpx 22rpx;
  }

  .admin-kpi-card__value {
    font-size: 44rpx;
  }

  .admin-toolbar-lite {
    flex-direction: column;
    align-items: stretch;
    gap: 14rpx;
    padding: 18rpx !important;
    margin-bottom: 20rpx;
  }

  .toolbar-picker,
  .admin-toolbar-lite__picker,
  .admin-toolbar-lite__search,
  .admin-toolbar-lite__btn {
    width: 100%;
    min-width: 0;
    max-width: none;
    height: 64rpx;
  }

  .table-header {
    display: none !important;
  }

  .table-row.equipment-grid {
    display: flex;
    flex-direction: column;
    gap: 10rpx;
    padding: 20rpx !important;
    border-bottom: 1rpx solid #e6edf7;
  }

  .table-row.equipment-grid > text,
  .table-row.equipment-grid > view {
    width: 100%;
    font-size: 24rpx;
    line-height: 1.5;
  }

  .actions {
    justify-content: flex-start;
    flex-wrap: wrap;
    gap: 10rpx;
  }

  .admin-equipment-modal {
    width: calc(100vw - 32rpx);
    max-width: calc(100vw - 32rpx);
    padding: 22rpx 20rpx 20rpx;
    border-radius: 22rpx;
  }

  .admin-equipment-modal__title {
    font-size: 30rpx;
  }

  .admin-equipment-modal__actions {
    flex-direction: column;
    gap: 10rpx;
  }

  .admin-equipment-btn {
    width: 100%;
    min-width: 0;
    height: 64rpx;
  }
}
</style>

