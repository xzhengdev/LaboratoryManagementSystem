<template>
  <admin-layout title="校区管理" subtitle="查看校区列表、状态启停与关联实验室数量" active="campuses">
    <view class="admin-panel-grid">
      <view v-for="item in summaryCards" :key="item.label" class="card">
        <view class="subtitle">{{ item.label }}</view>
        <view class="title">{{ item.value }}</view>
      </view>
    </view>

    <view class="card admin-toolbar">
      <input v-model="keyword" class="input" style="flex:1;" placeholder="搜索校区名称或地址" />
      <view class="btn" @click="openCampusDialog()">新增校区</view>
      <view class="pill">表格 + 弹窗表单</view>
    </view>

    <view class="card table-card">
      <view class="table-header campus-grid">
        <text>校区名称</text>
        <text>地址</text>
        <text>实验室数量</text>
        <text>状态</text>
        <text>操作</text>
      </view>
      <view v-for="item in filteredList" :key="item.id" class="table-row campus-grid">
        <text>{{ item.campus_name }}</text>
        <text>{{ item.address }}</text>
        <text>{{ item.lab_count || 0 }}</text>
        <status-tag :status="item.status === 'active' ? 'active' : 'disabled'" />
        <view class="actions">
          <view class="pill" @click="openCampusDialog(item)">编辑</view>
          <view class="pill" :class="item.status === 'active' ? 'pill-danger' : 'pill-muted'" @click="toggleStatus(item)">
            {{ item.status === 'active' ? '停用' : '启用' }}
          </view>
        </view>
      </view>
      <view v-if="!filteredList.length" class="empty-state">没有符合条件的校区记录。</view>
    </view>

    <view v-if="dialogVisible" class="admin-modal-mask" @click="closeDialog">
      <view class="admin-modal" @click.stop>
        <view class="title">{{ editingId ? '编辑校区' : '新增校区' }}</view>
        <view class="field">
          <text class="label">校区名称</text>
          <input v-model="form.campus_name" class="input" />
        </view>
        <view class="field">
          <text class="label">校区地址</text>
          <input v-model="form.address" class="input" />
        </view>
        <view class="field">
          <text class="label">校区简介</text>
          <textarea v-model="form.description" class="input textarea" />
        </view>
        <view class="actions">
          <view class="btn" @click="saveCampus">保存</view>
          <view class="btn btn-light" @click="closeDialog">取消</view>
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
      keyword: '',
      list: [],
      dialogVisible: false,
      editingId: '',
      form: {
        campus_name: '',
        address: '',
        description: ''
      }
    }
  },
  computed: {
    filteredList() {
      const text = this.keyword.trim().toLowerCase()
      if (!text) return this.list
      return this.list.filter((item) => `${item.campus_name}${item.address}${item.description || ''}`.toLowerCase().includes(text))
    },
    summaryCards() {
      const activeCount = this.list.filter((item) => item.status === 'active').length
      return [
        { label: '校区总数', value: this.list.length },
        { label: '正常开放', value: activeCount },
        { label: '停用校区', value: this.list.length - activeCount }
      ]
    }
  },
  async onShow() {
    if (!requireLogin()) return
    const campuses = await api.campuses()
    this.list = campuses.map((item, index) => ({
      ...item,
      lab_count: item.lab_count || 0,
      description: item.description || ['主教学与实验中心', '跨校区联合实验基地', '综合开放实验平台'][index % 3]
    }))
  },
  methods: {
    openCampusDialog(item) {
      this.dialogVisible = true
      this.editingId = item ? item.id : ''
      this.form = item ? {
        campus_name: item.campus_name,
        address: item.address,
        description: item.description || ''
      } : {
        campus_name: '',
        address: '',
        description: ''
      }
    },
    closeDialog() {
      this.dialogVisible = false
      this.editingId = ''
    },
    saveCampus() {
      const payload = {
        id: this.editingId || Date.now(),
        campus_name: this.form.campus_name,
        address: this.form.address,
        description: this.form.description,
        lab_count: 0,
        status: 'active'
      }
      if (this.editingId) {
        this.list = this.list.map((item) => (item.id === this.editingId ? { ...item, ...payload } : item))
      } else {
        this.list = [payload].concat(this.list)
      }
      uni.showToast({ title: '保存成功', icon: 'success' })
      this.closeDialog()
    },
    toggleStatus(item) {
      item.status = item.status === 'active' ? 'disabled' : 'active'
      uni.showToast({ title: item.status === 'active' ? '已启用' : '已停用', icon: 'success' })
    }
  }
}
</script>

<style lang="scss">
.campus-grid {
  grid-template-columns: 1fr 1.8fr 0.8fr 0.8fr 1fr;
}
</style>
