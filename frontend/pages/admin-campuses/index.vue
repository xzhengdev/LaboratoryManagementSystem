<template>
  <!-- 使用管理后台布局组件，传入页面标题、副标题和当前激活菜单项 -->
  <admin-layout title="校区管理" subtitle="维护校区信息与运行状态" active="campuses">
    <!-- ==================== 权限检查：无管理权限时显示提示 ==================== -->
    <view v-if="!canManage" class="card empty-state">仅系统管理员可管理校区。</view>

    <!-- ==================== 有权限时显示完整管理界面 ==================== -->
    <template v-else>
      <!-- 顶部KPI指标卡片区域：展示校区总数、正常运行数、停用校区数 -->
      <view class="admin-kpi-grid">
        <view v-for="item in summaryCards" :key="item.label" class="admin-kpi-card">
          <view class="admin-kpi-card__label">{{ item.label }}</view>
          <view class="admin-kpi-card__value">{{ item.value }}</view>
        </view>
      </view>

      <!-- 工具栏：搜索框 + 新增按钮 -->
      <view class="card admin-toolbar-lite">
        <input v-model="keyword" class="input" style="flex: 1;" placeholder="搜索校区名称或地址" />
        <view class="admin-toolbar-lite__btn" @click="openCampusDialog()">新增校区</view>
      </view>

      <!-- 校区列表表格卡片 -->
      <view class="card table-card">
        <!-- 表格表头：使用grid布局对齐 -->
        <view class="table-header campus-grid">
          <text>校区名称</text>
          <text>地址</text>
          <text>实验室数量</text>
          <text>状态</text>
          <text>操作</text>
        </view>
        
        <!-- 遍历校区列表，渲染每一行数据 -->
        <view v-for="item in filteredList" :key="item.id" class="table-row campus-grid">
          <text class="table-strong">{{ item.campus_name }}</text>
          <text>{{ item.address }}</text>
          <text>{{ item.lab_count || 0 }}</text>
          <!-- 状态标签组件：根据status显示不同样式 -->
          <status-tag :status="item.status === 'active' ? 'active' : 'disabled'" />
          <view class="actions">
            <!-- 编辑按钮 -->
            <view class="pill" @click="openCampusDialog(item)">编辑</view>
            <!-- 启用/停用按钮：根据当前状态显示不同样式和文字 -->
            <view class="pill" :class="item.status === 'active' ? 'pill-danger' : 'pill-muted'" @click="toggleStatus(item)">
              {{ item.status === 'active' ? '停用' : '启用' }}
            </view>
          </view>
        </view>
        
        <!-- 无数据时的空状态提示 -->
        <view v-if="!filteredList.length" class="empty-state">没有符合条件的校区记录。</view>
      </view>

      <!-- ==================== 新增/编辑校区的模态框 ==================== -->
      <view v-if="dialogVisible" class="admin-modal-mask">
        <view class="admin-modal admin-campus-modal" @click.stop>
          <view class="admin-campus-modal__head">
            <view class="admin-campus-modal__title">{{ editingId ? '编辑校区' : '新增校区' }}</view>
            <view class="admin-campus-modal__close" @click="closeDialog">×</view>
          </view>
          
          <!-- 校区名称输入框 -->
          <view class="field admin-campus-field">
            <text class="label">校区名称</text>
            <input
              :value="form.campus_name"
              class="input admin-campus-input admin-campus-input--line"
              :disabled="false"
              placeholder="请输入校区名称"
              @input="onCampusNameInput"
            />
          </view>
          
          <!-- 校区地址输入框 -->
          <view class="field admin-campus-field">
            <text class="label">校区地址</text>
            <input
              :value="form.address"
              class="input admin-campus-input admin-campus-input--line"
              :disabled="false"
              placeholder="请输入校区地址"
              @input="onCampusAddressInput"
            />
          </view>
          
          <!-- 校区简介文本域 -->
          <view class="field admin-campus-field">
            <text class="label">校区简介</text>
            <textarea v-model="form.description" class="input textarea admin-campus-input admin-campus-textarea" placeholder="请输入校区简介（可选）" />
          </view>
          
          <!-- 模态框底部按钮 -->
          <view class="actions admin-campus-modal__actions">
            <view class="admin-campus-btn admin-campus-btn--ghost" @click="closeDialog">取消</view>
            <view class="admin-campus-btn admin-campus-btn--primary" @click="saveCampus">保存</view>
          </view>
        </view>
      </view>
    </template>
  </admin-layout>
</template>

<script>
// API接口调用模块
import { api } from '../../api/index'
// 登录状态守卫：检查用户是否已登录
import { requireLogin } from '../../common/guard'
// 会话管理：获取当前登录用户信息
import { getProfile } from '../../common/session'
// 路由跳转工具
import { openPage } from '../../common/router'
// 导航配置：校区管理权限校验、默认管理页路径
import { canManageCampuses, getDefaultAdminPath } from '../../config/navigation'
// 管理后台布局组件
import AdminLayout from '../../components/admin-layout.vue'
// 状态标签组件：用于显示校区启用/停用状态
import StatusTag from '../../components/status-tag.vue'

export default {
  // 注册子组件
  components: { AdminLayout, StatusTag },
  
  data() {
    return {
      profile: {},           // 当前登录用户信息（包含角色、权限等）
      keyword: '',          // 搜索关键词
      list: [],             // 校区列表数据
      dialogVisible: false, // 模态框显示/隐藏状态
      saving: false,
      editingId: '',        // 正在编辑的校区ID（空表示新增模式）
      form: {               // 表单数据（新增/编辑共用）
        campus_name: '',
        address: '',
        description: ''
      }
    }
  },
  
  computed: {
    /**
     * 计算属性：判断当前用户是否有校区管理权限
     * 根据用户角色调用配置中的权限校验函数
     */
    canManage() {
      return canManageCampuses(this.profile.role)
    },
    
    /**
     * 计算属性：根据搜索关键词过滤校区列表
     * 支持校区名称、地址、简介的模糊匹配
     */
    filteredList() {
      const text = this.keyword.trim().toLowerCase()
      if (!text) return this.list
      return this.list.filter((item) => 
        `${item.campus_name}${item.address}${item.description || ''}`
          .toLowerCase()
          .includes(text)
      )
    },
    
    /**
     * 计算属性：顶部KPI指标卡片数据
     * - 校区总数：列表总长度
     * - 正常运行：status为'active'的数量
     * - 停用校区：总数减去正常运行数
     */
    summaryCards() {
      const activeCount = this.list.filter((item) => item.status === 'active').length
      return [
        { label: '校区总数', value: this.list.length },
        { label: '正常运行', value: activeCount },
        { label: '停用校区', value: this.list.length - activeCount }
      ]
    }
  },
  
  /**
   * 生命周期：页面每次显示时触发
   * 1. 检查登录状态
   * 2. 获取当前用户信息
   * 3. 校验权限，无权限则跳转默认页
   * 4. 加载校区列表数据
   */
  async onShow() {
    // 未登录则跳转登录页
    if (!requireLogin()) return
    
    // 获取当前用户信息
    this.profile = getProfile()
    
    // 权限校验：无管理权限时提示并跳转
    if (!this.canManage) {
      uni.showToast({ title: '无权限访问校区管理', icon: 'none' })
      openPage(getDefaultAdminPath(this.profile.role), { replace: true })
      return
    }
    
    await this.fetchCampuses()
  },
  
  methods: {
    async fetchCampuses() {
      const campuses = await api.campuses()
      this.list = (campuses || []).map((item) => ({
        ...item,
        lab_count: item.lab_count || 0,
        description: item.description || ''
      }))
    },
    onCampusNameInput(event) {
      this.form.campus_name = event && event.detail ? event.detail.value : ''
    },
    onCampusAddressInput(event) {
      this.form.address = event && event.detail ? event.detail.value : ''
    },
    /**
     * 打开新增/编辑校区的模态框
     * @param {Object} item - 要编辑的校区对象（新增时不传）
     */
    openCampusDialog(item) {
      this.dialogVisible = true
      this.editingId = item ? item.id : ''
      // 编辑模式：回填表单数据；新增模式：清空表单
      this.form = item
        ? { 
            campus_name: item.campus_name, 
            address: item.address, 
            description: item.description || '' 
          }
        : { campus_name: '', address: '', description: '' }
    },
    
    /**
     * 关闭模态框并清空编辑状态
     */
    closeDialog() {
      this.dialogVisible = false
      this.editingId = ''
    },
    
    /**
     * 保存校区信息（新增或编辑）
     * 注意：当前实现为前端模拟，实际应调用后端API
     */
    async saveCampus() {
      if (this.saving) return
      const campus_name = (this.form.campus_name || '').trim()
      const address = (this.form.address || '').trim()
      const description = (this.form.description || '').trim()

      if (!campus_name) {
        uni.showToast({ title: '请输入校区名称', icon: 'none' })
        return
      }
      if (!address) {
        uni.showToast({ title: '请输入校区地址', icon: 'none' })
        return
      }

      this.saving = true
      try {
        if (this.editingId) {
          await api.updateCampus(this.editingId, { campus_name, address, description })
        } else {
          await api.createCampus({ campus_name, address, description, status: 'active' })
        }
        await this.fetchCampuses()
        uni.showToast({ title: '保存成功', icon: 'success' })
        this.closeDialog()
      } catch (error) {
        uni.showToast({ title: error?.message || '保存失败', icon: 'none' })
      } finally {
        this.saving = false
      }
    },
    
    /**
     * 切换校区启用/停用状态
     * @param {Object} item - 要切换状态的校区对象
     */
    async toggleStatus(item) {
      const nextStatus = item.status === 'active' ? 'disabled' : 'active'
      try {
        await api.updateCampus(item.id, { status: nextStatus })
        await this.fetchCampuses()
        uni.showToast({
          title: nextStatus === 'active' ? '已启用' : '已停用',
          icon: 'success'
        })
      } catch (error) {
        uni.showToast({ title: error?.message || '状态更新失败', icon: 'none' })
      }
    }
  }
}
</script>

<style lang="scss">
// ==================== KPI指标卡片区域样式 ====================
.admin-kpi-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));  // 三列等宽布局
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

// ==================== 工具栏样式 ====================
.admin-toolbar-lite {
  margin-bottom: 18rpx;           // 底部外边距
  display: flex;                   // flex布局实现水平排列
  align-items: center;             // 垂直居中对齐
  gap: 16rpx;                      // 搜索框和按钮之间的间距
  flex-wrap: nowrap;
}

// ==================== 搜索框样式 ====================
.admin-toolbar-lite .input {
  flex: 1;                         // 占据剩余空间，自动撑满
  height: 64rpx;                   // 高度
  padding: 0 24rpx;                // 左右内边距
  border-radius: 32rpx;            // 圆角
  background-color: #f5f7fa;       // 背景色
  border: 1rpx solid #e4ebf5;      // 边框
  font-size: 26rpx;                // 字体大小
  
  // 聚焦样式
  &:focus {
    border-color: #2c7da0;
    background-color: #ffffff;
    outline: none;
  }
}

// ==================== 新增按钮样式 ====================
.admin-toolbar-lite__btn {
  width: 190rpx;
  flex-shrink: 0;                  // 防止按钮被压缩，保持固定宽度
  height: 64rpx;                   // 与搜索框高度一致
  padding: 0 16rpx;
  border-radius: 32rpx;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background-color: #2c7da0;
  color: #ffffff;
  font-size: 26rpx;
  font-weight: 500;
  
  // 悬停效果
  &:hover {
    background-color: #1f5e7a;
  }
  
  // 点击效果
  &:active {
    transform: scale(0.98);
  }
}

// ==================== 校区模态框美化 ====================
.admin-modal-mask {
  background: rgba(10, 26, 45, 0.32);
  backdrop-filter: blur(4rpx);
}

.admin-campus-modal {
  width: 760rpx;
  max-width: calc(100vw - 64rpx);
  border-radius: 24rpx;
  padding: 28rpx 28rpx 24rpx;
  background: linear-gradient(180deg, #ffffff, #f9fbff);
  box-shadow: 0 22rpx 56rpx rgba(9, 36, 69, 0.18);
  animation: campus-modal-in 180ms ease-out;
}

.admin-campus-modal__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14rpx;
}

.admin-campus-modal__title {
  font-size: 34rpx;
  font-weight: 800;
  color: #142d4e;
}

.admin-campus-modal__close {
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
  transition: all 140ms ease;
}

.admin-campus-modal__close:hover {
  background: #e5edf8;
  color: #2f4a6a;
}

.admin-campus-field {
  margin-top: 12rpx;
}

.admin-campus-input {
  border-radius: 14rpx;
  background: #f4f7fc;
  border: 1rpx solid #dbe6f4;
  transition: all 150ms ease;
}

.admin-campus-input--line {
  height: 84rpx;
  line-height: 84rpx;
  padding: 0 22rpx;
}

.admin-campus-input:focus {
  border-color: #2c7da0;
  background: #ffffff;
  box-shadow: 0 0 0 4rpx rgba(44, 125, 160, 0.12);
}

.admin-campus-textarea {
  min-height: 148rpx;
  padding-top: 14rpx;
}

.admin-campus-modal__actions {
  margin-top: 20rpx;
  justify-content: flex-end;
  gap: 12rpx;
}

.admin-campus-btn {
  min-width: 160rpx;
  height: 62rpx;
  border-radius: 12rpx;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 24rpx;
  font-weight: 700;
  transition: transform 120ms ease, filter 120ms ease;
}

.admin-campus-btn:hover {
  filter: brightness(0.98);
}

.admin-campus-btn:active {
  transform: scale(0.98);
}

.admin-campus-btn--ghost {
  background: #eef3fb;
  color: #486280;
}

.admin-campus-btn--primary {
  background: linear-gradient(135deg, #2c7da0, #276f8f);
  color: #fff;
}

@keyframes campus-modal-in {
  from {
    opacity: 0;
    transform: translateY(16rpx) scale(0.98);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}


// ==================== 校区列表表格样式 ====================
// 使用grid布局实现表头和行内容的列对齐
.campus-grid {
  grid-template-columns: 1.2fr 1.8fr 0.9fr 0.8fr 1.1fr;
}

// 校区名称强调样式
.table-strong {
  color: #102a49;
  font-weight: 700;
}

// ==================== 响应式适配 ====================
@media screen and (max-width: 1200px) {
  // 小屏设备：KPI卡片改为单列布局
  .admin-kpi-grid {
    grid-template-columns: 1fr;
  }
  
  // 小屏设备：表格列宽适当调整
  .campus-grid {
    grid-template-columns: 1.2fr 1.2fr 0.8fr 0.8fr 1fr;
  }
}
</style>
