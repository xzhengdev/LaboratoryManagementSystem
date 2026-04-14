<template>
  <view class="reserve-page">
    <!-- #ifdef H5 -->
    <student-top-nav active="labs" />
    <!-- #endif -->

    <!-- #ifndef H5 -->
    <user-top-nav active="labs" />
    <!-- #endif -->

    <view class="reserve-page__shell">
      <view class="reserve-page__head">
        <view>
          <view class="reserve-page__title">实验室预约</view>
          <view class="reserve-page__sub">预留您的研究空间和技术资源。</view>
        </view>

        <view class="reserve-page__steps">
          <view class="reserve-page__step active"><text>1</text> 实验室与时间</view>
          <view class="reserve-page__line"></view>
          <view class="reserve-page__step"><text>2</text> 详情</view>
          <view class="reserve-page__line"></view>
          <view class="reserve-page__step"><text>3</text> 审核</view>
        </view>
      </view>

      <view class="reserve-page__layout">
        <view class="reserve-form">
          <view class="reserve-form__block">
            <view class="reserve-form__block-title">设施选择</view>
            <view class="reserve-form__grid two">
              <view class="reserve-form__field">
                <view class="reserve-form__label">选择实验室</view>
                <picker :range="labOptions" range-key="lab_name" :value="labIndex" @change="changeLab">
                  <view class="reserve-form__input">{{ currentLabName }}</view>
                </picker>
              </view>
              <view class="reserve-form__field">
                <view class="reserve-form__label">参与人数</view>
                <input
                  v-model="form.participant_count"
                  class="reserve-form__input"
                  type="number"
                  :placeholder="`最大：${maxParticipants}`"
                />
              </view>
            </view>
          </view>

          <view class="reserve-form__block">
            <view class="reserve-form__block-title">时间安排</view>
            <view class="reserve-form__grid three">
              <view class="reserve-form__field">
                <view class="reserve-form__label">预约日期</view>
                <picker mode="date" :value="form.reservation_date" @change="setField('reservation_date', $event.detail.value)">
                  <view class="reserve-form__input">{{ form.reservation_date }}</view>
                </picker>
              </view>
              <view class="reserve-form__field">
                <view class="reserve-form__label">开始时间</view>
                <picker mode="time" :value="form.start_time" @change="setField('start_time', $event.detail.value)">
                  <view class="reserve-form__input">{{ form.start_time }}</view>
                </picker>
              </view>
              <view class="reserve-form__field">
                <view class="reserve-form__label">结束时间</view>
                <picker mode="time" :value="form.end_time" @change="setField('end_time', $event.detail.value)">
                  <view class="reserve-form__input">{{ form.end_time }}</view>
                </picker>
              </view>
            </view>

            <view class="reserve-form__availability">
              <view class="reserve-form__availability-title">{{ form.reservation_date }} 的可用性</view>
              <view class="reserve-form__bar">
                <view
                  v-for="(seg, index) in availabilitySegments"
                  :key="index"
                  class="reserve-form__bar-seg"
                  :class="seg.type"
                  :style="{ width: seg.width }"
                ></view>
              </view>
              <view class="reserve-form__marks">
                <text>08:00</text><text>10:00</text><text>12:00</text><text>14:00</text><text>16:00</text><text>18:00</text><text>20:00</text>
              </view>
            </view>
          </view>

          <view class="reserve-form__block">
            <view class="reserve-form__block-title">研究目的与设备</view>
            <view class="reserve-form__field">
              <view class="reserve-form__label">用途描述</view>
              <textarea
                v-model="form.purpose"
                class="reserve-form__textarea"
                maxlength="200"
                placeholder="描述您此次实验的重点..."
              />
            </view>

            <view class="reserve-form__field">
              <view class="reserve-form__label">所需设备</view>
              <view class="reserve-form__equip-grid">
                <view
                  v-for="eq in equipmentOptions"
                  :key="eq.id"
                  class="reserve-form__equip-chip"
                  :class="{ active: selectedEquipment.includes(eq.id) }"
                  @click="toggleEquipment(eq.id)"
                >
                  {{ eq.equipment_name }}
                </view>
              </view>
            </view>
          </view>

          <view class="reserve-form__block">
            <view class="reserve-form__grid two">
              <view class="reserve-form__field">
                <view class="reserve-form__block-title">审批</view>
                <picker :range="approverOptions" @change="changeApprover">
                  <view class="reserve-form__input">{{ approverText }}</view>
                </picker>
              </view>
              <view class="reserve-form__field">
                <view class="reserve-form__block-title">文档</view>
                <view class="reserve-form__upload">上传规程 (PDF/DOC)</view>
              </view>
            </view>
          </view>

          <view class="reserve-form__actions">
            <view class="reserve-form__btn light" @click="saveDraft">保存草稿</view>
            <view class="reserve-form__btn light" @click="goBack">上一步</view>
            <view class="reserve-form__btn primary" @click="submit">提交预约</view>
          </view>
        </view>

        <view class="reserve-side">
          <view class="reserve-side__summary">
            <view class="reserve-side__title">预约摘要</view>
            <view class="reserve-side__item">
              <view class="reserve-side__label">LOCATION</view>
              <view class="reserve-side__value">{{ summaryLocation }}</view>
            </view>
            <view class="reserve-side__item">
              <view class="reserve-side__label">TIME WINDOW</view>
              <view class="reserve-side__value">{{ summaryTime }}</view>
            </view>
            <view class="reserve-side__item">
              <view class="reserve-side__label">RESOURCES</view>
              <view class="reserve-side__value">{{ summaryResource }}</view>
            </view>
            <view class="reserve-side__status">
              <text>STATUS</text>
              <text class="pill">NEW ENTRY</text>
            </view>
          </view>

          <view class="reserve-side__guide">
            <view class="reserve-side__guide-title">实验室指南</view>
            <view class="reserve-side__guide-item" v-for="(item, idx) in guideItems" :key="idx">{{ item }}</view>
            <view class="reserve-side__guide-cover"></view>
          </view>
        </view>
      </view>
    </view>

    <site-footer />
  </view>
</template>

<script>
import SiteFooter from '../../components/site-footer.vue'
import StudentTopNav from '../../components/student-top-nav.vue'
import UserTopNav from '../../components/user-top-nav.vue'
import { api } from '../../api/index'
import { requireLogin } from '../../common/guard'
import { openPage } from '../../common/router'
import { routes } from '../../config/navigation'

function todayString() {
  const now = new Date()
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`
}

export default {
  components: { SiteFooter, StudentTopNav, UserTopNav },
  data() {
    return {
      labIndex: 0,
      labOptions: [],
      selectedEquipment: [],
      approverOptions: ['系统自动分配', '实验室管理员', '系统管理员'],
      approverText: '系统自动分配',
      schedule: {},
      form: {
        campus_id: '',
        lab_id: '',
        reservation_date: todayString(),
        start_time: '14:00',
        end_time: '16:30',
        purpose: '',
        participant_count: '1'
      }
    }
  },
  computed: {
    currentLab() {
      return this.labOptions[this.labIndex] || {}
    },
    currentLabName() {
      return this.currentLab.lab_name || '请选择实验室'
    },
    maxParticipants() {
      return this.currentLab.capacity || 0
    },
    equipmentOptions() {
      return this.currentLab.equipment || []
    },
    summaryLocation() {
      return `${this.currentLab.campus_name || '校区待定'} · ${this.currentLab.location || '位置待定'}`
    },
    summaryTime() {
      return `${this.form.reservation_date} ${this.form.start_time} - ${this.form.end_time}`
    },
    summaryResource() {
      const deviceCount = this.selectedEquipment.length
      return `${Number(this.form.participant_count || 0)} 名参与者 · ${deviceCount} 台设备`
    },
    guideItems() {
      return [
        `${this.form.reservation_date} 的可用性会在提交时二次校验`,
        '请确保参与人数不超过实验室容量',
        '特殊设备请提前在用途描述中说明'
      ]
    },
    availabilitySegments() {
      const base = [
        { type: 'busy', width: '20%' },
        { type: 'idle', width: '10%' },
        { type: 'busy', width: '15%' },
        { type: 'focus', width: '15%' },
        { type: 'idle', width: '40%' }
      ]
      const list = this.schedule?.reservations || []
      if (!list.length) return base
      return base.map((item, index) => (index % 2 === 0 ? item : { ...item, type: 'idle' }))
    }
  },
  onLoad(options) {
    this.form.lab_id = options.labId || ''
    this.form.campus_id = options.campusId || ''
    this.form.reservation_date = options.date || todayString()
  },
  async onShow() {
    if (!requireLogin()) return
    // #ifdef H5
    uni.hideTabBar()
    // #endif
    await this.loadLabs()
  },
  methods: {
    async loadLabs() {
      try {
        const list = await api.labs(this.form.campus_id ? { campus_id: this.form.campus_id } : {})
        this.labOptions = Array.isArray(list) ? list : []

        if (!this.labOptions.length) return

        const targetIndex = this.form.lab_id
          ? this.labOptions.findIndex((item) => String(item.id) === String(this.form.lab_id))
          : 0

        this.labIndex = targetIndex >= 0 ? targetIndex : 0
        this.syncLabToForm()
        await this.loadSchedule()
      } catch (error) {
        this.labOptions = []
      }
    },
    async loadSchedule() {
      if (!this.form.lab_id) return
      try {
        this.schedule = await api.labSchedule(this.form.lab_id, this.form.reservation_date)
      } catch (error) {
        this.schedule = {}
      }
    },
    syncLabToForm() {
      const lab = this.currentLab
      if (!lab.id) return
      this.form.lab_id = String(lab.id)
      this.form.campus_id = String(lab.campus_id || this.form.campus_id || '')
      if (!this.form.participant_count || Number(this.form.participant_count) <= 0) {
        this.form.participant_count = '1'
      }
      this.selectedEquipment = []
    },
    async changeLab(event) {
      this.labIndex = Number(event.detail.value || 0)
      this.syncLabToForm()
      await this.loadSchedule()
    },
    async setField(key, value) {
      this.form[key] = value
      if (key === 'reservation_date' && this.form.lab_id) {
        await this.loadSchedule()
      }
    },
    toggleEquipment(id) {
      if (this.selectedEquipment.includes(id)) {
        this.selectedEquipment = this.selectedEquipment.filter((item) => item !== id)
      } else {
        this.selectedEquipment = this.selectedEquipment.concat(id)
      }
    },
    changeApprover(event) {
      this.approverText = this.approverOptions[event.detail.value] || this.approverOptions[0]
    },
    saveDraft() {
      uni.showToast({ title: '草稿已保存', icon: 'none' })
    },
    async submit() {
      if (!this.form.lab_id) {
        uni.showToast({ title: '请选择实验室', icon: 'none' })
        return
      }
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
.reserve-page {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background:
    radial-gradient(circle at top right, rgba(65, 190, 253, 0.13), transparent 24%),
    linear-gradient(180deg, #f7f9fc 0%, #eef2f7 100%);
}

.reserve-page__shell {
  flex: 1;
  padding: 30rpx 32rpx 48rpx;
}

.reserve-page__head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 20rpx;
}

.reserve-page__title {
  font-size: 68rpx;
  color: #061f44;
  font-weight: 800;
}

.reserve-page__sub {
  margin-top: 8rpx;
  color: #697a91;
  font-size: 26rpx;
}

.reserve-page__steps {
  margin-top: 8rpx;
  display: flex;
  align-items: center;
  gap: 12rpx;
}

.reserve-page__step {
  display: flex;
  align-items: center;
  gap: 10rpx;
  color: #5e6e86;
  font-size: 22rpx;
  font-weight: 700;
}

.reserve-page__step text {
  width: 42rpx;
  height: 42rpx;
  border-radius: 999rpx;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: #e3e9f2;
}

.reserve-page__step.active {
  color: #0c2851;
}

.reserve-page__step.active text {
  background: #0c2851;
  color: #fff;
}

.reserve-page__line {
  width: 52rpx;
  height: 2rpx;
  background: #ccd4e0;
}

.reserve-page__layout {
  margin-top: 20rpx;
  display: grid;
  grid-template-columns: minmax(0, 1.9fr) minmax(300rpx, 0.9fr);
  gap: 24rpx;
}

.reserve-form {
  border-radius: 28rpx;
  background: rgba(255, 255, 255, 0.8);
  border: 1rpx solid rgba(197, 198, 207, 0.3);
  padding: 22rpx;
}

.reserve-form__block {
  margin-bottom: 20rpx;
}

.reserve-form__block-title {
  color: #0b284f;
  font-size: 40rpx;
  font-weight: 800;
}

.reserve-form__grid {
  margin-top: 12rpx;
  display: grid;
  gap: 12rpx;
}

.reserve-form__grid.two {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.reserve-form__grid.three {
  grid-template-columns: 1.2fr 0.8fr 0.8fr;
}

.reserve-form__label {
  color: #6a7b92;
  font-size: 21rpx;
  margin-bottom: 8rpx;
}

.reserve-form__input {
  min-height: 68rpx;
  border-radius: 14rpx;
  background: #eff3f8;
  padding: 0 18rpx;
  display: flex;
  align-items: center;
  color: #20324e;
  font-size: 24rpx;
}

.reserve-form__textarea {
  min-height: 120rpx;
  border-radius: 14rpx;
  background: #eff3f8;
  padding: 16rpx 18rpx;
  width: 100%;
  box-sizing: border-box;
  color: #20324e;
  font-size: 24rpx;
}

.reserve-form__availability {
  margin-top: 12rpx;
  border-radius: 14rpx;
  background: #f0f4f9;
  padding: 14rpx;
}

.reserve-form__availability-title {
  color: #4d5f79;
  font-size: 22rpx;
  font-weight: 700;
}

.reserve-form__bar {
  margin-top: 10rpx;
  height: 48rpx;
  border-radius: 999rpx;
  overflow: hidden;
  display: flex;
}

.reserve-form__bar-seg {
  height: 100%;
}

.reserve-form__bar-seg.busy {
  background: #b9c1cc;
}

.reserve-form__bar-seg.idle {
  background: #d8dee7;
}

.reserve-form__bar-seg.focus {
  background: #45b3ef;
}

.reserve-form__marks {
  margin-top: 8rpx;
  display: flex;
  justify-content: space-between;
  color: #5f7088;
  font-size: 18rpx;
}

.reserve-form__equip-grid {
  margin-top: 8rpx;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10rpx;
}

.reserve-form__equip-chip {
  min-height: 58rpx;
  border-radius: 12rpx;
  border: 1rpx solid #d8e1ec;
  background: #f2f6fb;
  color: #314965;
  font-size: 22rpx;
  display: flex;
  align-items: center;
  justify-content: center;
}

.reserve-form__equip-chip.active {
  background: #dfefff;
  border-color: #90c5ef;
  color: #0f3869;
}

.reserve-form__upload {
  min-height: 110rpx;
  border-radius: 14rpx;
  border: 2rpx dashed #c8d3e2;
  color: #6d7f97;
  font-size: 23rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f5f8fc;
}

.reserve-form__actions {
  margin-top: 10rpx;
  border-top: 1rpx solid rgba(197, 198, 207, 0.35);
  padding-top: 16rpx;
  display: flex;
  justify-content: flex-end;
  gap: 12rpx;
}

.reserve-form__btn {
  min-width: 138rpx;
  height: 70rpx;
  border-radius: 16rpx;
  padding: 0 22rpx;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 24rpx;
  font-weight: 800;
}

.reserve-form__btn.light {
  background: #edf2f8;
  color: #3e4f67;
}

.reserve-form__btn.primary {
  background: #0a254c;
  color: #edf5ff;
}

.reserve-side {
  display: grid;
  gap: 16rpx;
  align-content: start;
}

.reserve-side__summary {
  border-radius: 24rpx;
  background: linear-gradient(170deg, #07214a, #041636);
  color: #d4e5ff;
  padding: 18rpx;
}

.reserve-side__title {
  font-size: 44rpx;
  color: #ffffff;
  font-weight: 800;
}

.reserve-side__item {
  margin-top: 14rpx;
}

.reserve-side__label {
  color: #46c6ff;
  font-size: 20rpx;
  letter-spacing: 1rpx;
}

.reserve-side__value {
  margin-top: 6rpx;
  color: #d7e6fb;
  font-size: 23rpx;
  line-height: 1.5;
}

.reserve-side__status {
  margin-top: 18rpx;
  padding-top: 12rpx;
  border-top: 1rpx solid rgba(108, 146, 197, 0.35);
  display: flex;
  align-items: center;
  justify-content: space-between;
  color: #8ba6ca;
  font-size: 21rpx;
}

.reserve-side__status .pill {
  min-height: 34rpx;
  border-radius: 999rpx;
  padding: 0 12rpx;
  display: inline-flex;
  align-items: center;
  background: #35c8ff;
  color: #0a254c;
  font-size: 18rpx;
  font-weight: 800;
}

.reserve-side__guide {
  border-radius: 22rpx;
  background: rgba(255, 255, 255, 0.78);
  border: 1rpx solid rgba(197, 198, 207, 0.28);
  padding: 16rpx;
}

.reserve-side__guide-title {
  color: #0b274d;
  font-size: 38rpx;
  font-weight: 800;
}

.reserve-side__guide-item {
  margin-top: 10rpx;
  color: #5d6f87;
  font-size: 22rpx;
  line-height: 1.6;
}

.reserve-side__guide-cover {
  margin-top: 14rpx;
  height: 142rpx;
  border-radius: 14rpx;
  background: linear-gradient(135deg, #74c2df, #3f6e90);
}

/* #ifndef H5 */
.reserve-page__shell {
  padding-left: 24rpx;
  padding-right: 24rpx;
}

.reserve-page__head {
  flex-direction: column;
}

.reserve-page__layout {
  grid-template-columns: 1fr;
}

.reserve-form__grid.two,
.reserve-form__grid.three,
.reserve-form__equip-grid {
  grid-template-columns: 1fr;
}

.reserve-form__actions {
  flex-wrap: wrap;
  justify-content: flex-start;
}
/* #endif */

/* #ifdef H5 */
@media screen and (min-width: 1500px) {
  .reserve-page__shell {
    padding-left: 56rpx;
    padding-right: 56rpx;
  }
}

@media screen and (max-width: 1100px) {
  .reserve-page__layout {
    grid-template-columns: 1fr;
  }
}

@media screen and (max-width: 820px) {
  .reserve-page__steps {
    display: none;
  }
}
/* #endif */
</style>
