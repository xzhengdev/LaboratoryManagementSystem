<template>
  <view>
    <user-top-nav active="labs" />
    <view class="page">
      <view class="page-shell two-col">
        <view>
          <page-hero
            kicker="预约提交"
            title="填写实验室预约申请"
            subtitle="PC 前台支持更完整地填写预约时间、用途和参与人数，提交后等待管理员审批。"
          />

          <!-- #ifdef H5 -->
          <view class="card">
            <view class="title">填写建议</view>
            <view class="portal-tips">
              <view class="portal-tip">优先填写明确的使用目的，便于管理员快速审批。</view>
              <view class="portal-tip">开始和结束时间建议与实验室开放时段保持一致。</view>
              <view class="portal-tip">提交后可在“我的预约”里查看审批状态与处理意见。</view>
            </view>
          </view>
          <!-- #endif -->
        </view>

        <view class="card">
          <view class="field">
            <text class="label">预约日期</text>
            <picker mode="date" :value="form.reservation_date" @change="setField('reservation_date', $event.detail.value)">
              <view class="input">{{ form.reservation_date }}</view>
            </picker>
          </view>
          <view class="field">
            <text class="label">开始时间</text>
            <picker mode="time" :value="form.start_time" @change="setField('start_time', $event.detail.value)">
              <view class="input">{{ form.start_time }}</view>
            </picker>
          </view>
          <view class="field">
            <text class="label">结束时间</text>
            <picker mode="time" :value="form.end_time" @change="setField('end_time', $event.detail.value)">
              <view class="input">{{ form.end_time }}</view>
            </picker>
          </view>
          <view class="field">
            <text class="label">用途说明</text>
            <textarea v-model="form.purpose" class="input textarea" maxlength="120" placeholder="请输入课程实验、项目答辩、科研测试等用途" />
          </view>
          <view class="field">
            <text class="label">参与人数</text>
            <input v-model="form.participant_count" class="input" type="number" placeholder="请输入参与人数" />
          </view>
          <view class="actions">
            <view class="btn" @click="submit">提交预约</view>
            <view class="btn btn-light" @click="goBack">返回上一页</view>
          </view>
        </view>
      </view>

      <portal-footer />
    </view>
  </view>
</template>

<script>
import { api } from '../../api/index'
import { requireLogin } from '../../common/guard'
import { openPage } from '../../common/router'
import { routes } from '../../config/navigation'
import PageHero from '../../components/page-hero.vue'
import PortalFooter from '../../components/portal-footer.vue'
import UserTopNav from '../../components/user-top-nav.vue'

function todayString() {
  const now = new Date()
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`
}

export default {
  components: { PageHero, PortalFooter, UserTopNav },
  data() {
    return {
      form: {
        campus_id: '',
        lab_id: '',
        reservation_date: todayString(),
        start_time: '09:00',
        end_time: '11:00',
        purpose: '',
        participant_count: '1'
      }
    }
  },
  onLoad(options) {
    this.form.lab_id = options.labId || ''
    this.form.campus_id = options.campusId || ''
    this.form.reservation_date = options.date || todayString()
  },
  onShow() {
    if (!requireLogin()) return
    // #ifdef H5
    uni.hideTabBar()
    // #endif
  },
  methods: {
    setField(key, value) {
      this.form[key] = value
    },
    async submit() {
      if (!this.form.purpose) {
        uni.showToast({ title: '请填写预约用途', icon: 'none' })
        return
      }
      await api.createReservation({
        ...this.form,
        participant_count: Number(this.form.participant_count)
      })
      uni.showToast({ title: '预约已提交', icon: 'success' })
      setTimeout(() => openPage(routes.myReservations, { replace: true }), 500)
    },
    goBack() {
      uni.navigateBack()
    }
  }
}
</script>

<style lang="scss">
.portal-tips {
  margin-top: 20rpx;
  display: grid;
  gap: 14rpx;
}

.portal-tip {
  padding: 18rpx 20rpx;
  border-radius: 18rpx;
  background: #F8FBFF;
  border: 1rpx solid #E8F0FC;
  color: #4B5D73;
  font-size: 24rpx;
  line-height: 1.7;
}
</style>
