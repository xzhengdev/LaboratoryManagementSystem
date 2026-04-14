<template>
  <admin-layout title="用户管理" subtitle="按姓名、角色与校区筛选用户，并通过弹窗完成状态管理" active="users">
    <view class="admin-panel-grid">
      <view v-for="item in summaryCards" :key="item.label" class="card">
        <view class="subtitle">{{ item.label }}</view>
        <view class="title">{{ item.value }}</view>
      </view>
    </view>

    <view class="card admin-toolbar">
      <input v-model="keyword" class="input" style="flex:1;" placeholder="搜索姓名、角色或校区" />
      <picker :range="roleOptions" @change="changeRole">
        <view class="input">{{ currentRoleName }}</view>
      </picker>
      <view class="btn" @click="openUserDialog()">新增用户</view>
      <view class="pill">演示数据</view>
    </view>

    <view class="card table-card">
      <view class="table-header user-grid">
        <text>姓名</text>
        <text>角色</text>
        <text>所属校区</text>
        <text>状态</text>
        <text>操作</text>
      </view>
      <view v-for="item in filteredUsers" :key="item.id" class="table-row user-grid">
        <text>{{ item.real_name }}</text>
        <text>{{ item.role_name }}</text>
        <text>{{ item.campus_name }}</text>
        <status-tag :status="item.status === 'active' ? 'active' : 'disabled'" />
        <view class="actions">
          <view class="pill" @click="openUserDialog(item)">编辑</view>
          <view class="pill" @click="toggleStatus(item)">{{ item.status === 'active' ? '停用' : '启用' }}</view>
          <view class="pill pill-danger" @click="resetPassword">重置密码</view>
        </view>
      </view>
    </view>

    <view v-if="dialogVisible" class="admin-modal-mask" @click="closeDialog">
      <view class="admin-modal" @click.stop>
        <view class="title">{{ editingId ? '编辑用户' : '新增用户' }}</view>
        <view class="field">
          <text class="label">姓名</text>
          <input v-model="form.real_name" class="input" />
        </view>
        <view class="field">
          <text class="label">角色</text>
          <picker :range="roleOptions.slice(1)" @change="selectRole">
            <view class="input">{{ form.role_name || '请选择角色' }}</view>
          </picker>
        </view>
        <view class="field">
          <text class="label">所属校区</text>
          <input v-model="form.campus_name" class="input" />
        </view>
        <view class="actions">
          <view class="btn" @click="saveUser">保存</view>
          <view class="btn btn-light" @click="closeDialog">取消</view>
        </view>
      </view>
    </view>
  </admin-layout>
</template>

<script>
import { requireLogin } from '../../common/guard'
import AdminLayout from '../../components/admin-layout.vue'
import StatusTag from '../../components/status-tag.vue'

export default {
  components: { AdminLayout, StatusTag },
  data() {
    return {
      keyword: '',
      selectedRole: '',
      roleOptions: ['全部角色', '学生', '教师', '实验室管理员', '系统管理员'],
      dialogVisible: false,
      editingId: '',
      form: {
        real_name: '',
        role_name: '',
        campus_name: ''
      },
      users: [
        { id: 1, real_name: '张同学', role_name: '学生', campus_name: '主校区', status: 'active' },
        { id: 2, real_name: '李老师', role_name: '教师', campus_name: '主校区', status: 'active' },
        { id: 3, real_name: '王管理员', role_name: '实验室管理员', campus_name: '东校区', status: 'active' },
        { id: 4, real_name: '系统管理员', role_name: '系统管理员', campus_name: '全校区', status: 'active' },
        { id: 5, real_name: '赵同学', role_name: '学生', campus_name: '西校区', status: 'disabled' }
      ]
    }
  },
  computed: {
    currentRoleName() {
      return this.selectedRole || '全部角色'
    },
    filteredUsers() {
      const text = this.keyword.trim().toLowerCase()
      return this.users.filter((item) => {
        const hitKeyword = !text || `${item.real_name}${item.role_name}${item.campus_name}`.toLowerCase().includes(text)
        const hitRole = !this.selectedRole || item.role_name === this.selectedRole
        return hitKeyword && hitRole
      })
    },
    summaryCards() {
      const activeCount = this.users.filter((item) => item.status === 'active').length
      return [
        { label: '用户总数', value: this.users.length },
        { label: '正常账号', value: activeCount },
        { label: '停用账号', value: this.users.length - activeCount }
      ]
    }
  },
  onShow() {
    requireLogin()
  },
  methods: {
    changeRole(event) {
      const value = this.roleOptions[event.detail.value]
      this.selectedRole = value === '全部角色' ? '' : value
    },
    selectRole(event) {
      this.form.role_name = this.roleOptions.slice(1)[event.detail.value]
    },
    openUserDialog(item) {
      this.dialogVisible = true
      this.editingId = item ? item.id : ''
      this.form = item ? {
        real_name: item.real_name,
        role_name: item.role_name,
        campus_name: item.campus_name
      } : {
        real_name: '',
        role_name: '',
        campus_name: ''
      }
    },
    closeDialog() {
      this.dialogVisible = false
      this.editingId = ''
    },
    saveUser() {
      const payload = {
        id: this.editingId || Date.now(),
        real_name: this.form.real_name,
        role_name: this.form.role_name,
        campus_name: this.form.campus_name,
        status: 'active'
      }
      if (this.editingId) {
        this.users = this.users.map((item) => (item.id === this.editingId ? { ...item, ...payload } : item))
      } else {
        this.users = [payload].concat(this.users)
      }
      uni.showToast({ title: '保存成功', icon: 'success' })
      this.closeDialog()
    },
    toggleStatus(item) {
      item.status = item.status === 'active' ? 'disabled' : 'active'
      uni.showToast({ title: item.status === 'active' ? '已启用' : '已停用', icon: 'success' })
    },
    resetPassword() {
      uni.showToast({ title: '密码已重置为 123456', icon: 'none' })
    }
  }
}
</script>

<style lang="scss">
.user-grid {
  grid-template-columns: 1fr 1fr 1fr 0.8fr 1.4fr;
}
</style>
