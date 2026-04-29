<template>
  <view class="asset-request-page">
    <student-top-nav active="assetRequests" />

    <view class="asset-request-shell">
      <view class="asset-request-head">
        <view class="asset-request-title">教师资产申报</view>
        <view class="asset-request-sub">申报购置将自动锁定校区预算，等待管理员审批。</view>
      </view>

      <view class="asset-request-kpi">
        <view class="asset-kpi-card">
          <view class="asset-kpi-label">预算总额</view>
          <view class="asset-kpi-value">{{ moneyText(budget.total_amount) }}</view>
        </view>
        <view class="asset-kpi-card">
          <view class="asset-kpi-label">已锁定</view>
          <view class="asset-kpi-value">{{ moneyText(budget.locked_amount) }}</view>
        </view>
        <view class="asset-kpi-card">
          <view class="asset-kpi-label">可用额度</view>
          <view class="asset-kpi-value">{{ moneyText(budget.available_amount) }}</view>
        </view>
      </view>

      <view class="asset-request-form card">
        <view class="asset-form-title">发起申报</view>
        <view class="asset-form-grid two">
          <view class="field">
            <view class="label">实验室</view>
            <picker :range="labOptions" range-key="lab_name" :value="labIndex" @change="changeLab">
              <view class="input picker-input">{{ currentLabName }}</view>
            </picker>
          </view>

          <view class="field">
            <view class="label">设备名称</view>
            <input v-model="form.asset_name" class="input" placeholder="如：高性能图形工作站" />
          </view>
        </view>

        <view class="asset-form-grid three">
          <view class="field">
            <view class="label">类别</view>
            <input v-model="form.category" class="input" placeholder="如：教学设备" />
          </view>
          <view class="field">
            <view class="label">数量</view>
            <input v-model="form.quantity" type="number" class="input" placeholder="1" />
          </view>
          <view class="field">
            <view class="label">单价（元）</view>
            <input v-model="form.unit_price" type="digit" class="input" placeholder="1000" />
          </view>
        </view>

        <view class="field">
          <view class="label">申报说明</view>
          <textarea v-model="form.reason" class="textarea" maxlength="200" placeholder="说明购置用途与课程/课题背景" />
        </view>

        <view class="asset-form-foot">
          <view class="asset-form-total">预计金额：<text>{{ moneyText(estimatedAmount) }}</text></view>
          <view class="btn btn-primary" @click="submitRequest">提交申报</view>
        </view>
      </view>

      <view class="asset-request-list card">
        <view class="asset-form-title">我的申报</view>

        <view class="list-header">
          <text>申报单号</text>
          <text>设备</text>
          <text>金额</text>
          <text>状态</text>
          <text>时间</text>
        </view>

        <view v-if="!requestList.length" class="empty-text">暂无资产申报记录</view>

        <view v-for="item in requestList" :key="item.id" class="list-row">
          <text class="mono">{{ item.request_no }}</text>
          <text>{{ item.asset_name }}</text>
          <text>{{ moneyText(item.amount) }}</text>
          <text :class="statusClass(item.status)">{{ statusText(item.status) }}</text>
          <text>{{ timeText(item.created_at) }}</text>
        </view>
      </view>
    </view>
  </view>
</template>

<script>
import StudentTopNav from '../../components/student-top-nav.vue'
import { api } from '../../api/index'
import { requireLogin } from '../../common/guard'
import { getProfile } from '../../common/session'
import { openPage } from '../../common/router'
import { routes } from '../../config/navigation'

export default {
  components: { StudentTopNav },
  data() {
    return {
      profile: {},
      budget: {
        total_amount: 0,
        locked_amount: 0,
        available_amount: 0
      },
      labOptions: [],
      labIndex: 0,
      form: {
        campus_id: '',
        lab_id: '',
        asset_name: '',
        category: '',
        quantity: '1',
        unit_price: '',
        reason: ''
      },
      requestList: []
    }
  },
  computed: {
    currentLabName() {
      const item = this.labOptions[this.labIndex]
      return item ? item.lab_name : '请选择实验室'
    },
    estimatedAmount() {
      const quantity = Number(this.form.quantity || 0)
      const unitPrice = Number(this.form.unit_price || 0)
      if (!Number.isFinite(quantity) || !Number.isFinite(unitPrice)) return 0
      return quantity * unitPrice
    }
  },
  async onShow() {
    if (!requireLogin()) return
    this.profile = getProfile()
    if (this.profile.role !== 'teacher') {
      uni.showToast({ title: '仅教师可发起资产申报', icon: 'none' })
      openPage(routes.home, { replace: true })
      return
    }
    await this.initPage()
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
    async initPage() {
      await Promise.all([this.loadBudget(), this.loadLabs(), this.loadMyRequests()])
    },
    async loadBudget() {
      this.budget = await api.currentAssetBudget({ campus_id: this.profile.campus_id })
    },
    async loadLabs() {
      const labs = await api.labs({ campus_id: this.profile.campus_id })
      this.labOptions = Array.isArray(labs) ? labs : []
      if (this.labOptions.length) {
        this.labIndex = 0
        this.form.lab_id = this.labOptions[0].id
        this.form.campus_id = this.profile.campus_id
      }
    },
    async loadMyRequests() {
      const list = await api.assetRequests()
      this.requestList = Array.isArray(list) ? list : []
    },
    changeLab(event) {
      const next = Number(event.detail.value || 0)
      this.labIndex = next
      const current = this.labOptions[this.labIndex]
      this.form.lab_id = current ? current.id : ''
    },
    async submitRequest() {
      const asset_name = String(this.form.asset_name || '').trim()
      const category = String(this.form.category || '').trim()
      const reason = String(this.form.reason || '').trim()
      const quantity = Number(this.form.quantity || 0)
      const unit_price = Number(this.form.unit_price || 0)

      if (!this.form.lab_id) {
        uni.showToast({ title: '请选择实验室', icon: 'none' })
        return
      }
      if (!asset_name) {
        uni.showToast({ title: '请输入设备名称', icon: 'none' })
        return
      }
      if (!category) {
        uni.showToast({ title: '请输入设备类别', icon: 'none' })
        return
      }
      if (!Number.isFinite(quantity) || quantity <= 0) {
        uni.showToast({ title: '请输入有效数量', icon: 'none' })
        return
      }
      if (!Number.isFinite(unit_price) || unit_price <= 0) {
        uni.showToast({ title: '请输入有效单价', icon: 'none' })
        return
      }

      await api.createAssetRequest({
        campus_id: this.profile.campus_id,
        lab_id: this.form.lab_id,
        asset_name,
        category,
        quantity,
        unit_price,
        reason
      })
      uni.showToast({ title: '申报已提交', icon: 'success' })
      this.form.asset_name = ''
      this.form.category = ''
      this.form.quantity = '1'
      this.form.unit_price = ''
      this.form.reason = ''
      await Promise.all([this.loadBudget(), this.loadMyRequests()])
    }
  }
}
</script>

<style lang="scss">
.asset-request-page {
  min-height: 100vh;
  background: #edf3fa;
}

.asset-request-shell {
  padding: 24rpx 28rpx 40rpx;
}

.asset-request-head {
  margin-bottom: 18rpx;
}

.asset-request-title {
  font-size: 56rpx;
  font-weight: 800;
  color: #163252;
}

.asset-request-sub {
  margin-top: 8rpx;
  color: #60738e;
  font-size: 24rpx;
}

.asset-request-kpi {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16rpx;
  margin-bottom: 18rpx;
}

.asset-kpi-card {
  background: #fff;
  border: 1rpx solid #deebf8;
  border-radius: 18rpx;
  padding: 18rpx;
}

.asset-kpi-label {
  color: #637890;
  font-size: 22rpx;
}

.asset-kpi-value {
  margin-top: 8rpx;
  font-size: 36rpx;
  font-weight: 800;
  color: #102d4b;
}

.card {
  background: #fff;
  border: 1rpx solid #deebf8;
  border-radius: 18rpx;
  padding: 18rpx;
  margin-bottom: 16rpx;
}

.asset-form-title {
  font-size: 28rpx;
  color: #183654;
  font-weight: 800;
}

.asset-form-grid {
  display: grid;
  gap: 14rpx;
  margin-top: 14rpx;
}

.asset-form-grid.two {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.asset-form-grid.three {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.label {
  margin-bottom: 8rpx;
  color: #60738e;
  font-size: 22rpx;
}

.input {
  height: 70rpx;
  border-radius: 14rpx;
  background: #f2f6fb;
  padding: 0 16rpx;
  font-size: 24rpx;
  color: #173350;
}

.picker-input {
  display: flex;
  align-items: center;
}

.textarea {
  width: 100%;
  min-height: 140rpx;
  border-radius: 14rpx;
  background: #f2f6fb;
  padding: 16rpx;
  box-sizing: border-box;
  font-size: 24rpx;
  color: #173350;
}

.asset-form-foot {
  margin-top: 16rpx;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.asset-form-total {
  color: #506684;
  font-size: 24rpx;
}

.asset-form-total text {
  color: #0f2d4f;
  font-weight: 800;
}

.btn {
  height: 66rpx;
  padding: 0 30rpx;
  border-radius: 14rpx;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 24rpx;
  font-weight: 700;
}

.btn-primary {
  background: #2f7ea5;
  color: #fff;
}

.list-header,
.list-row {
  margin-top: 12rpx;
  display: grid;
  grid-template-columns: 1.6fr 1fr 0.8fr 0.8fr 1.2fr;
  gap: 10rpx;
  align-items: center;
}

.list-header {
  color: #6b7f97;
  font-size: 22rpx;
  font-weight: 700;
}

.list-row {
  background: #f8fbff;
  border: 1rpx solid #e4edf7;
  border-radius: 12rpx;
  padding: 14rpx;
  color: #183654;
  font-size: 22rpx;
}

.mono {
  font-family: Consolas, monospace;
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
  margin-top: 14rpx;
  color: #7a8ca3;
  font-size: 22rpx;
}

@media (max-width: 860px) {
  .asset-request-shell {
    padding: 14rpx 12rpx 24rpx;
  }

  .asset-request-title {
    font-size: 40rpx;
  }

  .asset-request-kpi,
  .asset-form-grid.two,
  .asset-form-grid.three {
    grid-template-columns: 1fr;
  }

  .asset-form-foot {
    flex-direction: column;
    align-items: stretch;
    gap: 10rpx;
  }

  .btn {
    width: 100%;
  }

  .list-header {
    display: none;
  }

  .list-row {
    grid-template-columns: 1fr;
    gap: 6rpx;
  }
}
</style>
