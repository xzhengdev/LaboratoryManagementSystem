<template>
  <admin-layout title="设备管理" subtitle="按实验室筛选设备，并通过弹窗维护设备状态与数量" active="equipment">
    <view class="admin-panel-grid">
      <view v-for="item in summaryCards" :key="item.label" class="card">
        <view class="subtitle">{{ item.label }}</view>
        <view class="title">{{ item.value }}</view>
      </view>
    </view>

    <view class="card admin-toolbar">
      <picker :range="labOptions" range-key="lab_name" @change="changeLab">
        <view class="input">{{ currentLabName }}</view>
      </picker>
      <input v-model="keyword" class="input" style="flex:1;" placeholder="搜索设备名称或所属实验室" />
      <view class="btn" @click="openEditor()">新增设备</view>
      <view class="pill">表格 + 弹窗编辑</view>
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
        <text>{{ item.equipment_name }}</text>
        <text>{{ item.lab_name }}</text>
        <text>{{ item.quantity }}</text>
        <status-tag :status="item.status === 'active' ? 'active' : 'disabled'" />
        <view class="actions">
          <view class="pill" @click="openEditor(item)">编辑</view>
          <view class="pill pill-danger" @click="toggleStatus(item)">{{ item.status === 'active' ? '停用' : '启用' }}</view>
        </view>
      </view>
    </view>

    <view v-if="editorVisible" class="admin-modal-mask" @click="closeEditor">
      <view class="admin-modal" @click.stop>
        <view class="title">{{ editingId ? '编辑设备' : '新增设备' }}</view>
        <view class="field">
          <text class="label">所属实验室</text>
          <picker :range="labOptions.slice(1)" range-key="lab_name" @change="selectEditorLab">
            <view class="input">{{ editorLabName }}</view>
          </picker>
        </view>
        <view class="field">
          <text class="label">设备名称</text>
          <input v-model="form.equipment_name" class="input" />
        </view>
        <view class="field">
          <text class="label">数量</text>
          <input v-model="form.quantity" class="input" type="number" />
        </view>
        <view class="field">
          <text class="label">状态</text>
          <picker :range="statusOptions" @change="selectStatus">
            <view class="input">{{ form.status }}</view>
          </picker>
        </view>
        <view class="actions">
          <view class="btn" @click="saveEquipment">保存</view>
          <view class="btn btn-light" @click="closeEditor">取消</view>
        </view>
      </view>
    </view>
  </admin-layout>
</template>

<script>
import { api } from '../../api/index'
import { requireLogin } from '../../common/guard'
import AdminLayout from '../../components/admin-layout.vue'
import StatusTag from '../../components/status-tag.vue'

export default {
  components: { AdminLayout, StatusTag },
  data() {
    return {
      list: [],
      keyword: '',
      selectedLabId: '',
      labOptions: [{ id: '', lab_name: '全部实验室' }],
      editorVisible: false,
      editingId: '',
      statusOptions: ['active', 'disabled'],
      form: {
        lab_id: '',
        equipment_name: '',
        quantity: '1',
        status: 'active'
      }
    }
  },
  computed: {
    currentLabName() {
      const current = this.labOptions.find((item) => String(item.id) === String(this.selectedLabId))
      return current ? current.lab_name : '全部实验室'
    },
    editorLabName() {
      const current = this.labOptions.find((item) => String(item.id) === String(this.form.lab_id))
      return current ? current.lab_name : '请选择实验室'
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
    const [equipment, labs] = await Promise.all([api.equipment(), api.labs()])
    this.list = equipment
    this.labOptions = [{ id: '', lab_name: '全部实验室' }].concat(labs.map((item) => ({ id: item.id, lab_name: item.lab_name })))
  },
  methods: {
    changeLab(event) {
      this.selectedLabId = this.labOptions[event.detail.value].id
    },
    selectEditorLab(event) {
      this.form.lab_id = this.labOptions.slice(1)[event.detail.value].id
    },
    selectStatus(event) {
      this.form.status = this.statusOptions[event.detail.value]
    },
    openEditor(item) {
      this.editorVisible = true
      if (!item) {
        this.editingId = ''
        this.form = { lab_id: '', equipment_name: '', quantity: '1', status: 'active' }
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
    saveEquipment() {
      const lab = this.labOptions.find((item) => String(item.id) === String(this.form.lab_id))
      const payload = {
        id: this.editingId || Date.now(),
        lab_id: this.form.lab_id,
        lab_name: lab ? lab.lab_name : '未指定实验室',
        equipment_name: this.form.equipment_name,
        quantity: Number(this.form.quantity),
        status: this.form.status
      }
      if (this.editingId) {
        this.list = this.list.map((item) => (item.id === this.editingId ? { ...item, ...payload } : item))
      } else {
        this.list = [payload].concat(this.list)
      }
      uni.showToast({ title: '保存成功', icon: 'success' })
      this.closeEditor()
    },
    toggleStatus(item) {
      item.status = item.status === 'active' ? 'disabled' : 'active'
      uni.showToast({ title: item.status === 'active' ? '已启用' : '已停用', icon: 'success' })
    }
  }
}
</script>

<style lang="scss">
.equipment-grid {
  grid-template-columns: 1.4fr 1.2fr 0.7fr 0.7fr 1fr;
}
</style>
