<template>
  <admin-layout title="用户管理" subtitle="按角色筛选并维护用户状态" active="users">
    <view v-if="!canManage" class="card empty-state">仅系统管理员可管理用户。</view>

    <template v-else>
      <view class="admin-kpi-grid">
        <view v-for="item in summaryCards" :key="item.label" class="admin-kpi-card">
          <view class="admin-kpi-card__label">{{ item.label }}</view>
          <view class="admin-kpi-card__value">{{ item.value }}</view>
        </view>
      </view>

      <view class="card admin-toolbar-lite">
        <input v-model="keyword" class="input admin-toolbar-lite__search" style="flex: 1;" placeholder="搜索姓名、角色或校区" />
        <picker :range="roleFilterOptions" range-key="label" @change="changeRole">
          <view class="input toolbar-picker admin-toolbar-lite__picker">{{ currentRoleName }}</view>
        </picker>
        <view class="admin-toolbar-lite__btn" @click="openUserDialog()">新增用户</view>
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
          <text class="table-strong">{{ item.real_name }}</text>
          <text>{{ item.role_name }}</text>
          <text>{{ item.campus_name || '全校区' }}</text>
          <status-tag :status="item.status === 'active' ? 'active' : 'disabled'" />
          <view class="actions">
            <view class="pill" @click="openUserDialog(item)">编辑</view>
            <view class="pill" @click="toggleStatus(item)">{{ item.status === 'active' ? '停用' : '启用' }}</view>
            <view class="pill pill-danger" @click="resetPassword(item)">重置密码</view>
          </view>
        </view>
        <view v-if="!filteredUsers.length" class="empty-state">暂无用户数据</view>
      </view>

      <view v-if="dialogVisible" class="admin-modal-mask" @click="closeDialog">
        <view class="admin-modal admin-user-modal" @click.stop>
          <view class="admin-user-modal__head">
            <view class="admin-user-modal__title">{{ editingId ? '编辑用户' : '新增用户' }}</view>
            <view class="admin-user-modal__close" @click="closeDialog">×</view>
          </view>
          <view class="field">
            <text class="label">用户名</text>
            <input v-model="form.username" class="input admin-user-input admin-user-input--line" placeholder="请输入用户名（登录账号）" />
          </view>
          <view class="field">
            <text class="label">姓名</text>
            <input v-model="form.real_name" class="input admin-user-input admin-user-input--line" placeholder="请输入真实姓名" />
          </view>
          <view class="field">
            <text class="label">角色</text>
            <picker :range="roleFormOptions" range-key="label" @change="selectRole">
              <view class="input admin-user-input admin-user-input--line">{{ currentFormRoleName }}</view>
            </picker>
          </view>
          <view class="field">
            <text class="label">所属校区</text>
            <template v-if="form.role === 'system_admin'">
              <view class="input admin-user-input admin-user-input--line">全校区（系统管理员）</view>
            </template>
            <template v-else>
              <picker :range="campuses" range-key="campus_name" @change="selectCampus">
                <view class="input admin-user-input admin-user-input--line">{{ currentFormCampusName }}</view>
              </picker>
            </template>
          </view>
          <view v-if="!editingId" class="field">
            <text class="label">初始密码</text>
            <input v-model="form.password" class="input admin-user-input admin-user-input--line" placeholder="默认 123456，可自行设置" password />
          </view>
          <view class="actions admin-user-modal__actions">
            <view class="admin-user-btn admin-user-btn--ghost" @click="closeDialog">取消</view>
            <view class="admin-user-btn admin-user-btn--primary" @click="saveUser">保存</view>
          </view>
        </view>
      </view>
    </template>
  </admin-layout>
</template>

<script>
import { api } from '../../api/index'
import { requireLogin } from '../../common/guard'
import { getProfile } from '../../common/session'
import { openPage } from '../../common/router'
import { canManageUsers, getDefaultAdminPath, getRoleText } from '../../config/navigation'
import AdminLayout from '../../components/admin-layout.vue'
import StatusTag from '../../components/status-tag.vue'

export default {
  components: { AdminLayout, StatusTag },
  data() {
    return {
      profile: {},
      keyword: '',
      selectedRole: '',
      dialogVisible: false,
      editingId: '',
      saving: false,
      campuses: [],
      users: [],
      roleFilterOptions: [
        { label: '全部角色', value: '' },
        { label: '学生', value: 'student' },
        { label: '老师', value: 'teacher' },
        { label: '实验室管理员', value: 'lab_admin' },
        { label: '系统管理员', value: 'system_admin' }
      ],
      form: {
        username: '',
        real_name: '',
        role: 'student',
        campus_id: '',
        password: ''
      }
    }
  },
  computed: {
    canManage() {
      return canManageUsers(this.profile.role)
    },
    roleFormOptions() {
      return this.roleFilterOptions.filter((item) => item.value)
    },
    currentRoleName() {
      const current = this.roleFilterOptions.find((item) => item.value === this.selectedRole)
      return current ? current.label : '全部角色'
    },
    currentFormRoleName() {
      const current = this.roleFormOptions.find((item) => item.value === this.form.role)
      return current ? current.label : '请选择角色'
    },
    currentFormCampusName() {
      const current = this.campuses.find((item) => String(item.id) === String(this.form.campus_id))
      return current ? current.campus_name : '请选择校区'
    },
    filteredUsers() {
      const text = this.keyword.trim().toLowerCase()
      return this.users.filter((item) => {
        const hitKeyword = !text || `${item.username}${item.real_name}${item.role_name}${item.campus_name || ''}`.toLowerCase().includes(text)
        const hitRole = !this.selectedRole || item.role === this.selectedRole
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
  async onShow() {
    if (!requireLogin()) return
    this.profile = getProfile()
    if (!this.canManage) {
      uni.showToast({ title: '无权限访问用户管理', icon: 'none' })
      openPage(getDefaultAdminPath(this.profile.role), { replace: true })
      return
    }
    try {
      await this.loadData()
    } catch (error) {
      uni.showToast({ title: error?.message || '用户请求失败，请检查后端服务', icon: 'none' })
    }
  },
  methods: {
    async loadData() {
      const [users, campuses] = await Promise.all([api.users(), api.campuses()])
      this.campuses = (Array.isArray(campuses) ? campuses : []).map((item) => ({ id: item.id, campus_name: item.campus_name }))
      this.users = (Array.isArray(users) ? users : []).map((item) => ({
        ...item,
        role_name: item.role_name || getRoleText(item.role),
        campus_name: item.campus_name || '全校区'
      }))
    },
    changeRole(event) {
      this.selectedRole = this.roleFilterOptions[event.detail.value].value
    },
    selectRole(event) {
      this.form.role = this.roleFormOptions[event.detail.value].value
      if (this.form.role === 'system_admin') this.form.campus_id = ''
    },
    selectCampus(event) {
      this.form.campus_id = this.campuses[event.detail.value].id
    },
    openUserDialog(item) {
      this.dialogVisible = true
      this.editingId = item ? item.id : ''
      if (item) {
        this.form = {
          username: item.username,
          real_name: item.real_name,
          role: item.role,
          campus_id: item.campus_id || '',
          password: ''
        }
        return
      }
      this.form = {
        username: '',
        real_name: '',
        role: 'student',
        campus_id: this.campuses.length ? this.campuses[0].id : '',
        password: ''
      }
    },
    closeDialog() {
      this.dialogVisible = false
      this.editingId = ''
    },
    async saveUser() {
      if (this.saving) return
      const username = (this.form.username || '').trim()
      const real_name = (this.form.real_name || '').trim()
      const role = this.form.role
      const campus_id = role === 'system_admin' ? null : this.form.campus_id
      const password = (this.form.password || '').trim()

      if (!username) {
        uni.showToast({ title: '请输入用户名', icon: 'none' })
        return
      }
      if (!real_name) {
        uni.showToast({ title: '请输入姓名', icon: 'none' })
        return
      }
      if (!role) {
        uni.showToast({ title: '请选择角色', icon: 'none' })
        return
      }
      if (role !== 'system_admin' && !campus_id) {
        uni.showToast({ title: '请选择所属校区', icon: 'none' })
        return
      }

      this.saving = true
      try {
        const payload = { username, real_name, role, campus_id }
        if (this.editingId) {
          await api.updateUser(this.editingId, payload)
        } else {
          await api.createUser({ ...payload, password: password || '123456', status: 'active' })
        }
        await this.loadData()
        uni.showToast({ title: '保存成功', icon: 'success' })
        this.closeDialog()
      } catch (error) {
        uni.showToast({ title: error?.message || '保存失败', icon: 'none' })
      } finally {
        this.saving = false
      }
    },
    async toggleStatus(item) {
      const nextStatus = item.status === 'active' ? 'disabled' : 'active'
      try {
        await api.updateUser(item.id, { status: nextStatus })
        await this.loadData()
        uni.showToast({ title: nextStatus === 'active' ? '已启用' : '已停用', icon: 'success' })
      } catch (error) {
        uni.showToast({ title: error?.message || '状态更新失败', icon: 'none' })
      }
    },
    async resetPassword(item) {
      try {
        await api.resetUserPassword(item.id, { password: '123456' })
        uni.showToast({ title: `已重置 ${item.real_name} 密码为 123456`, icon: 'none' })
      } catch (error) {
        uni.showToast({ title: error?.message || '重置密码失败', icon: 'none' })
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
  min-width: 220rpx;
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

.user-grid {
  grid-template-columns: 1fr 1fr 1.2fr 0.8fr 1.4fr;
}

.table-strong {
  color: #102a49;
  font-weight: 700;
}

.admin-modal-mask {
  background: rgba(10, 26, 45, 0.32);
  backdrop-filter: blur(4rpx);
}

.admin-user-modal {
  width: 760rpx;
  max-width: calc(100vw - 64rpx);
  border-radius: 24rpx;
  padding: 28rpx 28rpx 24rpx;
  background: linear-gradient(180deg, #ffffff, #f9fbff);
  box-shadow: 0 22rpx 56rpx rgba(9, 36, 69, 0.18);
  animation: user-modal-in 180ms ease-out;
}

.admin-user-modal__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14rpx;
}

.admin-user-modal__title {
  font-size: 34rpx;
  font-weight: 800;
  color: #142d4e;
}

.admin-user-modal__close {
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

.admin-user-input {
  border-radius: 14rpx;
  background: #f4f7fc;
  border: 1rpx solid #dbe6f4;
  transition: all 150ms ease;
}

.admin-user-input--line {
  height: 78rpx;
  line-height: 78rpx;
  padding: 0 22rpx;
}

.admin-user-input:focus {
  border-color: #2c7da0;
  background: #ffffff;
  box-shadow: 0 0 0 4rpx rgba(44, 125, 160, 0.12);
}

.admin-user-modal__actions {
  margin-top: 20rpx;
  justify-content: flex-end;
  gap: 12rpx;
}

.admin-user-btn {
  min-width: 160rpx;
  height: 62rpx;
  border-radius: 12rpx;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 24rpx;
  font-weight: 700;
}

.admin-user-btn--ghost {
  background: #eef3fb;
  color: #486280;
}

.admin-user-btn--primary {
  background: linear-gradient(135deg, #2c7da0, #276f8f);
  color: #fff;
}

@keyframes user-modal-in {
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
