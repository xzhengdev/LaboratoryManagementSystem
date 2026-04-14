<template>
  <!-- 实验室管理主布局 -->
  <admin-layout title="实验室管理" subtitle="按校区维护实验室信息与开放状态" active="labs">
    
    <!-- ==================== 数据统计卡片区域 ==================== -->
    <view class="admin-kpi-grid">
      <view v-for="item in summaryCards" :key="item.label" class="admin-kpi-card">
        <view class="admin-kpi-card__label">{{ item.label }}</view>
        <view class="admin-kpi-card__value">{{ item.value }}</view>
      </view>
    </view>

    <!-- ==================== 工具栏区域 ==================== -->
    <view class="card admin-toolbar-lite">
      <!-- 校区筛选 - 仅系统管理员可见 -->
      <template v-if="isSystemAdmin">
        <picker :range="filterCampusOptions" range-key="campus_name" @change="selectFilterCampus">
          <view class="input toolbar-picker admin-toolbar-lite__picker">{{ filterCampusName }}</view>
        </picker>
      </template>
      <!-- 普通管理员显示固定校区 -->
      <template v-else>
        <view class="input toolbar-picker admin-toolbar-lite__picker">当前校区：{{ currentCampusName }}</view>
      </template>
      
      <!-- 搜索框 -->
      <input v-model="keyword" class="input admin-toolbar-lite__search" placeholder="搜索实验室名称或位置" />
      
      <!-- 新增实验室按钮 -->
      <view class="admin-toolbar-lite__btn" @click="openEditor()">新增实验室</view>
    </view>

    <!-- ==================== 实验室列表表格区域 ==================== -->
    <view class="card table-card">
      <!-- 表格表头 -->
      <view class="table-header lab-grid">
        <text>实验室</text>
        <text>校区</text>
        <text>容量</text>
        <text>开放时间</text>
        <text>状态</text>
        <text>操作</text>
      </view>
      
      <!-- 表格数据行 - 遍历过滤后的实验室列表 -->
      <view v-for="item in filteredList" :key="item.id" class="table-row lab-grid">
        <text class="table-strong">{{ item.lab_name }}</text>
        <text>{{ item.campus_name }}</text>
        <text>{{ item.capacity }}</text>
        <text>{{ item.open_time.slice(0, 5) }} - {{ item.close_time.slice(0, 5) }}</text>
        <status-tag :status="item.status === 'active' ? 'active' : 'disabled'" />
        <view class="actions">
          <view class="pill" @click="showDetail(item)">详情</view>
          <view class="pill" @click="openEditor(item)">编辑</view>
          <view class="pill pill-danger" @click="removeLab(item.id)">删除</view>
        </view>
      </view>
    </view>

    <!-- ==================== 实验室详情抽屉 ==================== -->
    <view v-if="drawerVisible" class="admin-drawer-mask" @click="drawerVisible = false">
      <view class="admin-drawer" @click.stop>
        <view class="title">{{ activeLab.lab_name }}</view>
        <view class="subtitle">{{ activeLab.campus_name }} · {{ activeLab.location }}</view>
        <view class="field">
          <text class="label">容量</text>
          <view class="input">{{ activeLab.capacity }}</view>
        </view>
        <view class="field">
          <text class="label">开放时间</text>
          <view class="input">{{ activeLab.open_time }} - {{ activeLab.close_time }}</view>
        </view>
        <view class="field">
          <text class="label">简介</text>
          <view class="input">{{ activeLab.description || '暂无实验室简介' }}</view>
        </view>
        <view class="actions">
          <view class="btn btn-light" @click="drawerVisible = false">关闭</view>
        </view>
      </view>
    </view>

    <!-- ==================== 新增/编辑实验室弹窗 ==================== -->
    <view v-if="editorVisible" class="admin-modal-mask" @click="closeEditor">
      <view class="admin-modal admin-modal--wide admin-lab-modal" @click.stop>
        <view class="admin-lab-modal__head">
          <view class="admin-lab-modal__title">{{ editingId ? '编辑实验室' : '新增实验室' }}</view>
          <view class="admin-lab-modal__close" @click="closeEditor">×</view>
        </view>
        
        <!-- 表单区域 - 使用网格布局 -->
        <view class="admin-form-grid">
          <!-- 校区选择 -->
          <view class="field">
            <text class="label">校区</text>
            <template v-if="isSystemAdmin">
              <picker :range="campuses" range-key="campus_name" @change="selectCampus">
                <view class="input admin-lab-input admin-lab-input--line">{{ currentEditorCampusName }}</view>
              </picker>
            </template>
            <template v-else>
              <view class="input admin-lab-input admin-lab-input--line">{{ currentCampusName }}</view>
            </template>
          </view>
          
          <!-- 实验室名称 -->
          <view class="field">
            <text class="label">实验室名称</text>
            <input v-model="form.lab_name" class="input admin-lab-input admin-lab-input--line" />
          </view>
          
          <!-- 位置 -->
          <view class="field">
            <text class="label">位置</text>
            <input v-model="form.location" class="input admin-lab-input admin-lab-input--line" />
          </view>
          
          <!-- 容量 -->
          <view class="field">
            <text class="label">容量</text>
            <input v-model="form.capacity" class="input admin-lab-input admin-lab-input--line" type="number" />
          </view>
          
          <!-- 开始时间 -->
          <view class="field">
            <text class="label">开始时间</text>
            <input v-model="form.open_time" class="input admin-lab-input admin-lab-input--line" />
          </view>
          
          <!-- 结束时间 -->
          <view class="field">
            <text class="label">结束时间</text>
            <input v-model="form.close_time" class="input admin-lab-input admin-lab-input--line" />
          </view>
        </view>
        
        <!-- 状态选择 -->
        <view class="field">
          <text class="label">状态</text>
          <picker :range="statusOptions" range-key="label" @change="selectStatus">
            <view class="input admin-lab-input admin-lab-input--line">{{ currentStatusText }}</view>
          </picker>
        </view>
        
        <!-- 简介文本框 -->
        <view class="field">
          <text class="label">简介</text>
          <textarea v-model="form.description" class="input textarea admin-lab-input admin-lab-textarea" />
        </view>
        
        <!-- 表单按钮 -->
        <view class="actions admin-lab-modal__actions">
          <view class="admin-lab-btn admin-lab-btn--ghost" @click="closeEditor">取消</view>
          <view class="admin-lab-btn admin-lab-btn--primary" @click="submitLab">{{ editingId ? '保存修改' : '创建实验室' }}</view>
        </view>
      </view>
    </view>
  </admin-layout>
</template>

<script>
// ==================== 导入依赖 ====================
import { api } from '../../api/index'           // API接口
import { requireLogin } from '../../common/guard'  // 登录验证
import { getProfile } from '../../common/session'  // 获取用户信息
import { canManageLabs, isSystemAdmin as checkSystemAdmin } from '../../config/navigation'  // 权限验证
import AdminLayout from '../../components/admin-layout.vue'     // 管理后台布局组件
import StatusTag from '../../components/status-tag.vue'         // 状态标签组件

export default {
  // 注册子组件
  components: { AdminLayout, StatusTag },
  
  data() {
    return {
      // ===== 用户数据 =====
      profile: {},           // 当前登录用户信息
      
      // ===== 基础数据 =====
      campuses: [],          // 校区列表（从API获取）
      list: [],              // 实验室列表（从API获取）
      
      // ===== UI状态 =====
      statusOptions: [
        { label: '启用', value: 'active' },
        { label: '停用', value: 'disabled' }
      ],  // 状态选项
      editingId: '',         // 正在编辑的实验室ID（空字符串表示新增模式）
      editorVisible: false,  // 编辑弹窗显示状态
      drawerVisible: false,  // 详情抽屉显示状态
      activeLab: {},         // 当前查看详情的实验室对象
      
      // ===== 筛选数据 =====
      filterCampusId: '',    // 筛选的校区ID
      keyword: '',           // 搜索关键词
      
      // ===== 表单数据 =====
      form: {
        campus_id: '',       // 所属校区ID
        lab_name: '',        // 实验室名称
        location: '',        // 实验室位置
        capacity: '30',      // 容量（默认30人）
        open_time: '08:00',  // 开放开始时间
        close_time: '21:00', // 开放结束时间
        status: 'active',    // 状态（active:启用, disabled:停用）
        description: ''      // 实验室简介
      }
    }
  },
  
  // ==================== 计算属性 ====================
  computed: {
    /**
     * 判断当前用户是否为系统管理员
     * @returns {boolean} true-系统管理员, false-普通管理员
     */
    isSystemAdmin() {
      return checkSystemAdmin(this.profile.role)
    },
    
    /**
     * 获取当前用户所在校区名称
     * @returns {string} 校区名称，未分配时显示提示
     */
    currentCampusName() {
      const item = this.campuses.find((campus) => String(campus.id) === String(this.profile.campus_id))
      return item ? item.campus_name : '未分配校区'
    },
    
    /**
     * 获取编辑表单中选中的校区名称
     * @returns {string} 校区名称，未选择时显示提示
     */
    currentEditorCampusName() {
      const item = this.campuses.find((campus) => String(campus.id) === String(this.form.campus_id))
      return item ? item.campus_name : '请选择校区'
    },
    
    /**
     * 统计数据卡片数据
     * @returns {Array} 包含总数、启用数、停用数的卡片数据
     */
    summaryCards() {
      const activeCount = this.list.filter((item) => item.status === 'active').length
      return [
        { label: '实验室总数', value: this.list.length },
        { label: '正常开放', value: activeCount },
        { label: '停用实验室', value: this.list.length - activeCount }
      ]
    },
    
    /**
     * 获取筛选器显示的校区名称
     * @returns {string} 校区名称，"全部校区"表示不过滤
     */
    filterCampusName() {
      const item = this.filterCampusOptions.find((campus) => String(campus.id) === String(this.filterCampusId))
      return item ? item.campus_name : '全部校区'
    },
    filterCampusOptions() {
      return [{ id: '', campus_name: '全部校区' }].concat(this.campuses)
    },
    
    /**
     * 过滤后的实验室列表（支持校区筛选 + 关键词搜索）
     * @returns {Array} 过滤后的实验室数组
     */
    filteredList() {
      const text = this.keyword.trim().toLowerCase()
      return this.list.filter((item) => {
        // 校区筛选条件
        const hitCampus = !this.filterCampusId || String(item.campus_id) === String(this.filterCampusId)
        // 关键词搜索条件（实验室名称、位置、校区名称）
        const hitKeyword = !text || `${item.lab_name}${item.location}${item.campus_name}`.toLowerCase().includes(text)
        return hitCampus && hitKeyword
      })
    },
    currentStatusText() {
      const item = this.statusOptions.find((option) => option.value === this.form.status)
      return item ? item.label : '请选择状态'
    }
  },
  
  // ==================== 生命周期钩子 ====================
  /**
   * 页面显示时执行
   * 1. 验证登录状态
   * 2. 验证权限
   * 3. 加载校区数据
   * 4. 加载实验室数据
   */
  async onShow() {
    // 验证是否已登录
    if (!requireLogin()) return
    
    // 获取当前用户信息
    this.profile = getProfile()
    
    // 验证是否有实验室管理权限
    if (!canManageLabs(this.profile.role)) return

    // 获取所有校区
    const allCampuses = await api.campuses()
    
    // 根据角色筛选可见校区
    this.campuses = this.isSystemAdmin
      ? allCampuses  // 系统管理员：可见所有校区
      : allCampuses.filter((item) => String(item.id) === String(this.profile.campus_id))  // 普通管理员：仅可见自己校区

    // 初始化筛选和表单的校区ID
    if (this.isSystemAdmin) {
      this.filterCampusId = ''  // 系统管理员默认显示全部校区
      if (!this.form.campus_id && this.campuses.length) {
        this.form.campus_id = this.campuses[0].id  // 默认选择第一个校区
      }
    } else {
      this.filterCampusId = this.profile.campus_id  // 普通管理员只能看自己校区
      this.form.campus_id = this.profile.campus_id
    }

    // 加载实验室数据
    await this.loadLabs()
  },
  
  // ==================== 方法定义 ====================
  methods: {
    /**
     * 从API加载实验室数据
     * 根据用户角色决定加载全部还是仅当前校区
     */
    async loadLabs() {
      const labs = await api.labs()
      this.list = this.isSystemAdmin
        ? labs  // 系统管理员：显示所有实验室
        : labs.filter((item) => String(item.campus_id) === String(this.profile.campus_id))  // 普通管理员：仅显示自己校区
    },
    
    /**
     * 编辑弹窗中 - 选择校区（仅系统管理员可见）
     * @param {Object} event - picker组件返回的事件对象
     */
    selectCampus(event) {
      this.form.campus_id = this.campuses[event.detail.value].id
    },
    
    /**
     * 工具栏 - 筛选校区（仅系统管理员可见）
     * @param {Object} event - picker组件返回的事件对象
     */
    selectFilterCampus(event) {
      this.filterCampusId = this.filterCampusOptions[event.detail.value].id
    },
    
    /**
     * 选择实验室状态
     * @param {Object} event - picker组件返回的事件对象
     */
    selectStatus(event) {
      this.form.status = this.statusOptions[event.detail.value].value
    },
    
    /**
     * 显示实验室详情抽屉
     * @param {Object} item - 实验室对象
     */
    showDetail(item) {
      this.activeLab = item
      this.drawerVisible = true
    },
    
    /**
     * 打开新增/编辑弹窗
     * @param {Object} [item] - 可选，编辑时传入实验室对象；新增时不传
     */
    openEditor(item) {
      this.editorVisible = true
      
      // 新增模式
      if (!item) {
        this.editingId = ''
        this.form = {
          campus_id: this.profile.campus_id || '',
          lab_name: '',
          location: '',
          capacity: '30',
          open_time: '08:00',
          close_time: '21:00',
          status: 'active',
          description: ''
        }
        return
      }
      
      // 编辑模式：回填数据
      this.editingId = item.id
      this.form = {
        campus_id: item.campus_id,
        lab_name: item.lab_name,
        location: item.location,
        capacity: String(item.capacity),
        open_time: item.open_time.slice(0, 5),   // 只取时:分部分
        close_time: item.close_time.slice(0, 5), // 只取时:分部分
        status: item.status,
        description: item.description || ''
      }
    },
    
    /**
     * 关闭新增/编辑弹窗
     */
    closeEditor() {
      this.editorVisible = false
      this.editingId = ''
    },
    
    /**
     * 构建提交的实验室数据对象
     * @returns {Object} 处理后的实验室数据（容量转为数字类型）
     */
    buildPayload() {
      return { ...this.form, capacity: Number(this.form.capacity) }
    },
    
    /**
     * 提交实验室数据（新增或编辑）
     * 调用API保存数据，成功后刷新列表
     */
    async submitLab() {
      // 编辑模式：调用更新接口
      if (this.editingId) {
        await api.updateLab(this.editingId, this.buildPayload())
      } 
      // 新增模式：调用创建接口
      else {
        await api.createLab(this.buildPayload())
      }
      
      // 提示成功
      uni.showToast({ title: this.editingId ? '修改成功' : '创建成功', icon: 'success' })
      
      // 关闭弹窗并刷新列表
      this.closeEditor()
      await this.loadLabs()
    },
    
    /**
     * 删除实验室
     * @param {string|number} id - 实验室ID
     */
    async removeLab(id) {
      try {
        await api.deleteLab(id)
        uni.showToast({ title: '删除成功', icon: 'success' })
        await this.loadLabs()  // 刷新列表
      } catch (error) {
        uni.showToast({ title: error?.message || '删除失败', icon: 'none' })
      }
    }
  }
}
</script>

<!-- ==================== 样式定义 ==================== -->
<style lang="scss">
// 统计卡片网格容器
.admin-kpi-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16rpx;
  margin-bottom: 18rpx;
}

// 统计卡片样式
.admin-kpi-card {
  border-radius: 20rpx;
  border: 1rpx solid #dbe4f1;
  background: #fff;
  padding: 18rpx 20rpx;
}

// 卡片标签文字
.admin-kpi-card__label {
  color: #6d7f95;
  font-size: 22rpx;
}

// 卡片数值文字
.admin-kpi-card__value {
  margin-top: 8rpx;
  font-size: 52rpx;
  font-weight: 800;
  color: #132d4d;
}

// 工具栏容器
.admin-toolbar-lite {
  margin-bottom: 18rpx;
  display: flex;
  align-items: center;
  gap: 16rpx;
  flex-wrap: nowrap;
}

.admin-toolbar-lite__search {
  flex: 1 1 420rpx;
  min-width: 320rpx;
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

// 工具栏按钮
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

// 筛选器选择框最小宽度
.toolbar-picker {
  min-width: 240rpx;
  max-width: 620rpx;
}

.admin-toolbar-lite__picker {
  flex: 0 0 auto;
  height: 64rpx;
  padding: 0 24rpx;
  border-radius: 32rpx;
  border: 1rpx solid #e4ebf5;
  background: #f5f7fa;
  display: flex;
  align-items: center;
}

// 实验室表格列宽定义
.lab-grid {
  grid-template-columns: 1.2fr 1fr 0.7fr 1fr 0.7fr 1.3fr;
}

// 表格中强调文字样式
.table-strong {
  color: #102a49;
  font-weight: 700;
}

// 表单网格布局（两列）
.admin-form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 20rpx;
}

.admin-modal-mask {
  background: rgba(10, 26, 45, 0.32);
  backdrop-filter: blur(4rpx);
}

.admin-lab-modal {
  width: 860rpx;
  max-width: calc(100vw - 64rpx);
  border-radius: 24rpx;
  padding: 28rpx 28rpx 24rpx;
  background: linear-gradient(180deg, #ffffff, #f9fbff);
  box-shadow: 0 22rpx 56rpx rgba(9, 36, 69, 0.18);
  animation: admin-lab-modal-in 180ms ease-out;
}

.admin-lab-modal__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14rpx;
}

.admin-lab-modal__title {
  font-size: 34rpx;
  font-weight: 800;
  color: #142d4e;
}

.admin-lab-modal__close {
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

.admin-lab-input {
  border-radius: 14rpx;
  background: #f4f7fc;
  border: 1rpx solid #dbe6f4;
  transition: all 150ms ease;
}

.admin-lab-input--line {
  height: 78rpx;
  line-height: 78rpx;
  padding: 0 22rpx;
}

.admin-lab-input:focus {
  border-color: #2c7da0;
  background: #ffffff;
  box-shadow: 0 0 0 4rpx rgba(44, 125, 160, 0.12);
}

.admin-lab-textarea {
  min-height: 148rpx;
  padding-top: 14rpx;
}

.admin-lab-modal__actions {
  margin-top: 20rpx;
  justify-content: flex-end;
  gap: 12rpx;
}

.admin-lab-btn {
  min-width: 160rpx;
  height: 62rpx;
  border-radius: 12rpx;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 24rpx;
  font-weight: 700;
}

.admin-lab-btn--ghost {
  background: #eef3fb;
  color: #486280;
}

.admin-lab-btn--primary {
  background: linear-gradient(135deg, #2c7da0, #276f8f);
  color: #fff;
}

@keyframes admin-lab-modal-in {
  from {
    opacity: 0;
    transform: translateY(16rpx) scale(0.98);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

// 响应式布局：小屏幕适配
@media screen and (max-width: 1200px) {
  // 统计卡片改为单列
  .admin-kpi-grid {
    grid-template-columns: 1fr;
  }

  // 表格列宽调整
  .lab-grid {
    grid-template-columns: 1.2fr 1fr 0.7fr 0.9fr 0.7fr 1fr;
  }
}
</style>
