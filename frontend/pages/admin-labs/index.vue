<template>
  <admin-layout title="实验室管理" subtitle="按校区维护实验室信息，并通过抽屉查看详情" active="labs">
    <view class="admin-panel-grid">
      <view v-for="item in summaryCards" :key="item.label" class="card">
        <view class="subtitle">{{ item.label }}</view>
        <view class="title">{{ item.value }}</view>
      </view>
    </view>

    <view class="card admin-toolbar">
      <picker :range="campuses" range-key="campus_name" @change="selectFilterCampus">
        <view class="input">{{ filterCampusName }}</view>
      </picker>
      <input v-model="keyword" class="input" style="flex:1;" placeholder="搜索实验室名称或地点" />
      <view class="btn" @click="openEditor()">新增实验室</view>
      <view class="pill">表格 + 抽屉详情 + 弹窗编辑</view>
    </view>

    <view class="card table-card">
      <view class="table-header lab-grid">
        <text>实验室</text>
        <text>校区</text>
        <text>容量</text>
        <text>开放时间</text>
        <text>状态</text>
        <text>操作</text>
      </view>
      <view v-for="item in filteredList" :key="item.id" class="table-row lab-grid">
        <text>{{ item.lab_name }}</text>
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

    <view v-if="drawerVisible" class="admin-drawer-mask" @click="drawerVisible = false">
      <view class="admin-drawer" @click.stop>
        <view class="title">{{ activeLab.lab_name }}</view>
        <view class="subtitle">{{ activeLab.campus_name }} · {{ activeLab.location }}</view>
        <view class="field"><text class="label">容量</text><view class="input">{{ activeLab.capacity }}</view></view>
        <view class="field"><text class="label">开放时间</text><view class="input">{{ activeLab.open_time }} - {{ activeLab.close_time }}</view></view>
        <view class="field"><text class="label">简介</text><view class="input">{{ activeLab.description || '暂无实验室简介' }}</view></view>
        <view class="actions">
          <view class="btn btn-light" @click="drawerVisible = false">关闭</view>
        </view>
      </view>
    </view>

    <view v-if="editorVisible" class="admin-modal-mask" @click="closeEditor">
      <view class="admin-modal admin-modal--wide" @click.stop>
        <view class="title">{{ editingId ? '编辑实验室' : '新增实验室' }}</view>
        <view class="admin-form-grid">
          <view class="field">
            <text class="label">校区</text>
            <picker :range="campuses" range-key="campus_name" @change="selectCampus">
              <view class="input">{{ currentCampusName }}</view>
            </picker>
          </view>
          <view class="field">
            <text class="label">实验室名称</text>
            <input v-model="form.lab_name" class="input" />
          </view>
          <view class="field">
            <text class="label">地点</text>
            <input v-model="form.location" class="input" />
          </view>
          <view class="field">
            <text class="label">容量</text>
            <input v-model="form.capacity" class="input" type="number" />
          </view>
          <view class="field">
            <text class="label">开放时间</text>
            <input v-model="form.open_time" class="input" />
          </view>
          <view class="field">
            <text class="label">关闭时间</text>
            <input v-model="form.close_time" class="input" />
          </view>
        </view>
        <view class="field">
          <text class="label">状态</text>
          <picker :range="statusOptions" @change="selectStatus">
            <view class="input">{{ form.status }}</view>
          </picker>
        </view>
        <view class="field">
          <text class="label">简介</text>
          <textarea v-model="form.description" class="input textarea" />
        </view>
        <view class="actions">
          <view class="btn" @click="submitLab">{{ editingId ? '保存修改' : '创建实验室' }}</view>
          <view class="btn btn-light" @click="closeEditor">取消</view>
        </view>
      </view>
    </view>
  </admin-layout>
</template>

<script>
import { api } from '../../api/index'
import { requireLogin } from '../../common/guard'
import { getProfile } from '../../common/session'
import AdminLayout from '../../components/admin-layout.vue'
import StatusTag from '../../components/status-tag.vue'

export default {
  components: { AdminLayout, StatusTag },
  data() {
    return {
      campuses: [],
      list: [],
      statusOptions: ['active', 'disabled'],
      editingId: '',
      editorVisible: false,
      drawerVisible: false,
      activeLab: {},
      filterCampusId: '',
      keyword: '',
      form: {
        campus_id: '',
        lab_name: '',
        location: '',
        capacity: '30',
        open_time: '08:00',
        close_time: '21:00',
        status: 'active',
        description: ''
      }
    }
  },
  computed: {
    summaryCards() {
      const activeCount = this.list.filter((item) => item.status === 'active').length
      return [
        { label: '实验室总数', value: this.list.length },
        { label: '正常开放', value: activeCount },
        { label: '停用实验室', value: this.list.length - activeCount }
      ]
    },
    currentCampusName() {
      const item = this.campuses.find((campus) => String(campus.id) === String(this.form.campus_id))
      return item ? item.campus_name : '请选择校区'
    },
    filterCampusName() {
      const item = this.campuses.find((campus) => String(campus.id) === String(this.filterCampusId))
      return item ? item.campus_name : '全部校区'
    },
    filteredList() {
      const text = this.keyword.trim().toLowerCase()
      return this.list.filter((item) => {
        const hitCampus = !this.filterCampusId || String(item.campus_id) === String(this.filterCampusId)
        const hitKeyword = !text || `${item.lab_name}${item.location}${item.campus_name}`.toLowerCase().includes(text)
        return hitCampus && hitKeyword
      })
    }
  },
  async onShow() {
    if (!requireLogin()) return
    this.campuses = await api.campuses()
    const profile = getProfile()
    if (profile.campus_id && !this.form.campus_id) this.form.campus_id = profile.campus_id
    await this.loadLabs()
  },
  methods: {
    async loadLabs() {
      this.list = await api.labs()
    },
    selectCampus(event) {
      this.form.campus_id = this.campuses[event.detail.value].id
    },
    selectFilterCampus(event) {
      this.filterCampusId = this.campuses[event.detail.value].id
    },
    selectStatus(event) {
      this.form.status = this.statusOptions[event.detail.value]
    },
    showDetail(item) {
      this.activeLab = item
      this.drawerVisible = true
    },
    openEditor(item) {
      this.editorVisible = true
      if (!item) {
        this.editingId = ''
        this.form = {
          campus_id: getProfile().campus_id || '',
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
      this.editingId = item.id
      this.form = {
        campus_id: item.campus_id,
        lab_name: item.lab_name,
        location: item.location,
        capacity: String(item.capacity),
        open_time: item.open_time.slice(0, 5),
        close_time: item.close_time.slice(0, 5),
        status: item.status,
        description: item.description || ''
      }
    },
    closeEditor() {
      this.editorVisible = false
      this.editingId = ''
    },
    buildPayload() {
      return { ...this.form, capacity: Number(this.form.capacity) }
    },
    async submitLab() {
      if (this.editingId) {
        await api.updateLab(this.editingId, this.buildPayload())
      } else {
        await api.createLab(this.buildPayload())
      }
      uni.showToast({ title: this.editingId ? '修改成功' : '创建成功', icon: 'success' })
      this.closeEditor()
      await this.loadLabs()
    },
    async removeLab(id) {
      await api.deleteLab(id)
      uni.showToast({ title: '删除成功', icon: 'success' })
      await this.loadLabs()
    }
  }
}
</script>

<style lang="scss">
.lab-grid {
  grid-template-columns: 1.2fr 1fr 0.7fr 1fr 0.7fr 1.3fr;
}

.admin-form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 20rpx;
}
</style>
