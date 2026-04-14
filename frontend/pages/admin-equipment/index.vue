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
.admin-kpi-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16rpx;
  margin-bottom: 18rpx;
}

.admin-kpi-card {
  border-radius: 20rpx;
  border: 1rpx solid #dbe4f1;
  background: #fff;
  padding: 18rpx 20rpx;
}

.admin-kpi-card__label {
  color: #6d7f95;
  font-size: 22rpx;
}

.admin-kpi-card__value {
  margin-top: 8rpx;
  font-size: 52rpx;
  font-weight: 800;
  color: #132d4d;
}

.admin-toolbar-lite {
  margin-bottom: 18rpx;
  display: flex;
  align-items: center;
  gap: 16rpx;
  flex-wrap: nowrap;
}

.admin-toolbar-lite__btn {
  width: 190rpx;
  flex-shrink: 0;
  height: 64rpx;
  padding: 0 16rpx;
  border-radius: 32rpx;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background-color: #2c7da0;
  color: #ffffff;
  font-size: 26rpx;
  font-weight: 500;
}

.admin-toolbar-lite__btn:hover {
  background-color: #1f5e7a;
}

.admin-toolbar-lite__btn:active {
  transform: scale(0.98);
}

.admin-toolbar-lite__search {
  flex: 1;
  height: 64rpx;
  padding: 0 24rpx;
  border-radius: 32rpx;
  background-color: #f5f7fa;
  border: 1rpx solid #e4ebf5;
  font-size: 26rpx;
}

.admin-toolbar-lite__search:focus {
  border-color: #2c7da0;
  background-color: #ffffff;
  outline: none;
}

.toolbar-picker {
  min-width: 240rpx;
}

.admin-toolbar-lite__picker {
  height: 64rpx;
  padding: 0 24rpx;
  border-radius: 32rpx;
  border: 1rpx solid #e4ebf5;
  background: #f5f7fa;
  display: flex;
  align-items: center;
}

.equipment-grid {
  grid-template-columns: 1.4fr 1.2fr 0.7fr 0.7fr 1fr;
}

.table-strong {
  color: #102a49;
  font-weight: 700;
}

.admin-modal-mask {
  background: rgba(10, 26, 45, 0.32);
  backdrop-filter: blur(4rpx);
}

.admin-equipment-modal {
  width: 760rpx;
  max-width: calc(100vw - 64rpx);
  border-radius: 24rpx;
  padding: 28rpx 28rpx 24rpx;
  background: linear-gradient(180deg, #ffffff, #f9fbff);
  box-shadow: 0 22rpx 56rpx rgba(9, 36, 69, 0.18);
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
}

.admin-equipment-input {
  border-radius: 14rpx;
  background: #f4f7fc;
  border: 1rpx solid #dbe6f4;
  transition: all 150ms ease;
}

.admin-equipment-input--line {
  height: 78rpx;
  line-height: 78rpx;
  padding: 0 22rpx;
}

.admin-equipment-input:focus {
  border-color: #2c7da0;
  background: #ffffff;
  box-shadow: 0 0 0 4rpx rgba(44, 125, 160, 0.12);
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
}

.admin-equipment-btn--ghost {
  background: #eef3fb;
  color: #486280;
}

.admin-equipment-btn--primary {
  background: linear-gradient(135deg, #2c7da0, #276f8f);
  color: #fff;
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
</style>
