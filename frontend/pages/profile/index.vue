<template>
  <view class="profile-page">
    <!-- #ifdef H5 -->
    <student-top-nav active="profile" />
    <!-- #endif -->

    <!-- #ifndef H5 -->
    <user-top-nav active="profile" />
    <!-- #endif -->

    <view class="profile-page__shell">
      <view class="profile-page__hero">
        <view class="profile-page__avatar">博</view>
        <view class="profile-page__hero-main">
          <view class="profile-page__name">{{ profile.real_name || '未命名用户' }}</view>
          <view class="profile-page__role">{{ roleText }}</view>
          <view class="profile-page__badges">
            <view class="profile-page__badge">ID：{{ profile.username || 'N/A' }}</view>
            <view class="profile-page__badge">实验室协作成员</view>
            <view class="profile-page__badge blue">核心团队</view>
          </view>
        </view>
      </view>

      <view class="profile-page__stats">
        <view class="profile-page__stat-card">
          <view class="profile-page__stat-label">总预约次数</view>
          <view class="profile-page__stat-value">{{ stats.total }}</view>
          <view class="profile-page__stat-sub positive">较上月增长 {{ stats.growth }}%</view>
        </view>
        <view class="profile-page__stat-card">
          <view class="profile-page__stat-label">实验室内累计时长</view>
          <view class="profile-page__stat-value">{{ stats.hours }}h</view>
          <view class="profile-page__progress">
            <view class="profile-page__progress-in" :style="{ width: `${stats.progress}%` }"></view>
          </view>
          <view class="profile-page__stat-sub">年度目标：1200h</view>
        </view>
        <view class="profile-page__stat-card">
          <view class="profile-page__stat-label">当前活跃预订</view>
          <view class="profile-page__stat-value">{{ stats.active }}</view>
          <view class="profile-page__stat-sub">审批中 {{ stats.pending }} 项</view>
        </view>
        <view class="profile-page__stat-card">
          <view class="profile-page__stat-label">合规性评分</view>
          <view class="profile-page__stat-value">{{ stats.score }}%</view>
          <view class="profile-page__stat-sub">评级：优秀</view>
        </view>
      </view>

      <view class="profile-page__layout">
        <view>
          <view class="profile-page__card">
          <view class="profile-page__card-head">
            <view class="profile-page__card-title">基本信息设置</view>
              <view class="profile-page__card-link" @click="toggleEdit">{{ isEditing ? '完成编辑' : '编辑所有' }}</view>
            </view>
            <view class="profile-page__form-grid">
              <view class="profile-page__field">
                <view class="profile-page__label">中文姓名</view>
                <input v-model.trim="form.real_name" class="profile-page__input profile-page__input-field" :disabled="!isEditing" />
              </view>
              <view class="profile-page__field">
                <view class="profile-page__label">英文姓名</view>
                <input v-model.trim="form.real_name_en" class="profile-page__input profile-page__input-field" :disabled="!isEditing" />
              </view>
              <view class="profile-page__field">
                <view class="profile-page__label">电子邮件</view>
                <input v-model.trim="form.email" class="profile-page__input profile-page__input-field" :disabled="!isEditing" />
              </view>
              <view class="profile-page__field">
                <view class="profile-page__label">联系电话</view>
                <input v-model.trim="form.phone" class="profile-page__input profile-page__input-field" :disabled="!isEditing" />
              </view>
            </view>
            <view class="profile-page__form-actions">
              <view class="profile-page__btn primary" :class="{ disabled: !isEditing }" @click="saveProfile">保存更改</view>
              <view class="profile-page__btn light" @click="cancelEdit">取消</view>
              <view class="profile-page__btn danger" @click="logout">退出登录</view>
            </view>
          </view>

          <view class="profile-page__card">
            <view class="profile-page__card-title">实验室准入状态</view>
            <view class="profile-page__access-grid">
              <view v-for="(item, index) in accessList" :key="index" class="profile-page__access-item" :class="item.state">
                <view class="profile-page__access-icon">{{ item.icon }}</view>
                <view>
                  <view class="profile-page__access-name">{{ item.name }}</view>
                  <view class="profile-page__access-sub">{{ item.sub }}</view>
                </view>
              </view>
            </view>
          </view>
        </view>

        <view class="profile-page__card profile-page__timeline-card">
          <view class="profile-page__card-title">最近活动记录</view>
          <view class="profile-page__timeline">
            <view v-for="(item, idx) in timeline" :key="idx" class="profile-page__timeline-item">
              <view class="profile-page__timeline-dot" :class="item.type"></view>
              <view class="profile-page__timeline-main">
                <view class="profile-page__timeline-title">{{ item.title }}</view>
                <view class="profile-page__timeline-desc">{{ item.desc }}</view>
                <view class="profile-page__timeline-time">{{ item.time }}</view>
              </view>
            </view>
          </view>
          <view class="profile-page__timeline-btn">查看完整历史</view>
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
import { clearSession, getProfile, updateProfile } from '../../common/session'
import { getRoleText, routes } from '../../config/navigation'

export default {
  components: { SiteFooter, StudentTopNav, UserTopNav },
  data() {
    return {
      routes,
      profile: {},
      reservations: [],
      isEditing: false,
      form: {
        real_name: '',
        real_name_en: '',
        email: '',
        phone: ''
      }
    }
  },
  computed: {
    roleText() {
      return getRoleText(this.profile.role)
    },
    stats() {
      const list = this.reservations
      const total = list.length
      const active = list.filter((item) => item.status === 'approved').length
      const pending = list.filter((item) => item.status === 'pending').length
      const minutes = list.reduce((sum, item) => {
        const start = (item.start_time || '00:00').split(':').map(Number)
        const end = (item.end_time || '00:00').split(':').map(Number)
        return sum + Math.max(0, end[0] * 60 + end[1] - (start[0] * 60 + start[1]))
      }, 0)
      const hours = Math.round((minutes / 60) * 10) / 10
      const progress = Math.min(100, Math.round((hours / 1200) * 100))
      return {
        total,
        active,
        pending,
        hours,
        progress,
        growth: Math.min(99, 8 + pending),
        score: Math.max(80, 98 - Math.min(8, list.filter((i) => i.status === 'cancelled').length))
      }
    },
    accessList() {
      const campus = this.profile.campus_name || '主校区'
      return [
        { icon: '⎈', name: `${campus} · 生物安全二级实验室`, sub: '有效期至 2025-12-31', state: 'ok' },
        { icon: '⚗', name: `${campus} · 化学分析中心`, sub: '有效期至 2025-06-15', state: 'ok' },
        { icon: '⚙', name: `${campus} · 纳米技术净室`, sub: '资质审核中...', state: 'warn' },
        { icon: '⌫', name: `${campus} · 同位素研究室`, sub: '未授权（需完成安全培训）', state: 'lock' }
      ]
    },
    timeline() {
      const latest = this.reservations.slice(0, 3)
      const items = latest.map((item) => ({
        type: item.status === 'approved' ? 'ok' : item.status === 'pending' ? 'warn' : 'normal',
        title: item.status === 'approved' ? '实验预约确认' : item.status === 'pending' ? '审批处理中' : '预约状态更新',
        desc: `${item.lab_name || '实验室'} · ${item.reservation_date || ''} ${(item.start_time || '').slice(0, 5)}-${(item.end_time || '').slice(0, 5)}`,
        time: '刚刚'
      }))
      if (!items.length) {
        return [
          { type: 'ok', title: '账户已激活', desc: '欢迎使用分布式实验室预约系统。', time: '今天' }
        ]
      }
      return items
    }
  },
  async onShow() {
    if (!requireLogin()) return
    // #ifdef H5
    uni.hideTabBar()
    // #endif
    this.profile = getProfile()
    this.syncFormFromProfile()
    await this.loadReservations()
  },
  methods: {
    async loadReservations() {
      try {
        this.reservations = await api.myReservations()
      } catch (error) {
        this.reservations = []
      }
    },
    syncFormFromProfile() {
      this.form = {
        real_name: this.profile.real_name || '',
        real_name_en: this.profile.real_name_en || this.profile.real_name || '',
        email: this.profile.email || '',
        phone: this.profile.phone || ''
      }
    },
    toggleEdit() {
      this.isEditing = !this.isEditing
      if (!this.isEditing) {
        this.syncFormFromProfile()
      }
    },
    saveProfile() {
      if (!this.isEditing) return
      const merged = {
        ...this.profile,
        real_name: this.form.real_name || this.profile.real_name,
        real_name_en: this.form.real_name_en || this.profile.real_name_en,
        email: this.form.email,
        phone: this.form.phone
      }
      updateProfile(merged)
      this.profile = merged
      this.isEditing = false
      uni.showToast({ title: '资料已保存', icon: 'success' })
    },
    cancelEdit() {
      this.profile = getProfile()
      this.syncFormFromProfile()
      this.isEditing = false
      uni.showToast({ title: '已恢复当前资料', icon: 'none' })
    },
    logout() {
      clearSession()
      openPage(routes.login, { replace: true })
    }
  }
}
</script>

<style lang="scss">
.profile-page {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background:
    radial-gradient(circle at top right, rgba(65, 190, 253, 0.11), transparent 26%),
    linear-gradient(180deg, #f7f9fc 0%, #eef2f7 100%);
}

.profile-page__shell {
  flex: 1;
  padding: 28rpx 32rpx 24rpx;
}

.profile-page__hero {
  border-radius: 28rpx;
  padding: 20rpx;
  display: flex;
  gap: 18rpx;
  align-items: center;
  background: linear-gradient(130deg, #1a2d54, #244c7a 62%, #1e3f68);
  color: #e8f3ff;
}

.profile-page__avatar {
  width: 120rpx;
  height: 120rpx;
  border-radius: 24rpx;
  background: rgba(4, 20, 40, 0.48);
  border: 2rpx solid rgba(133, 183, 227, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 44rpx;
  font-weight: 800;
}

.profile-page__name {
  font-size: 66rpx;
  font-weight: 800;
  line-height: 1.05;
}

.profile-page__role {
  margin-top: 8rpx;
  color: #4fc5ff;
  font-size: 36rpx;
  font-weight: 700;
}

.profile-page__badges {
  margin-top: 10rpx;
  display: flex;
  gap: 8rpx;
  flex-wrap: wrap;
}

.profile-page__badge {
  min-height: 36rpx;
  border-radius: 999rpx;
  padding: 0 12rpx;
  display: inline-flex;
  align-items: center;
  background: rgba(255, 255, 255, 0.18);
  color: #e7f3ff;
  font-size: 20rpx;
  font-weight: 700;
}

.profile-page__badge.blue {
  background: rgba(79, 197, 255, 0.24);
  color: #86deff;
}

.profile-page__stats {
  margin-top: 16rpx;
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14rpx;
}

.profile-page__stat-card {
  border-radius: 20rpx;
  background: rgba(255, 255, 255, 0.8);
  border: 1rpx solid rgba(197, 198, 207, 0.3);
  padding: 16rpx;
}

.profile-page__stat-label {
  color: #5e7088;
  font-size: 22rpx;
}

.profile-page__stat-value {
  margin-top: 6rpx;
  color: #0a244a;
  font-size: 56rpx;
  font-weight: 800;
}

.profile-page__stat-sub {
  margin-top: 8rpx;
  color: #77879c;
  font-size: 20rpx;
}

.profile-page__stat-sub.positive {
  color: #1e9b60;
  font-weight: 700;
}

.profile-page__progress {
  margin-top: 8rpx;
  height: 8rpx;
  border-radius: 999rpx;
  background: #e2e8f0;
  overflow: hidden;
}

.profile-page__progress-in {
  height: 100%;
  background: #41befd;
}

.profile-page__layout {
  margin-top: 16rpx;
  display: grid;
  grid-template-columns: minmax(0, 1.7fr) minmax(280rpx, 0.8fr);
  gap: 16rpx;
}

.profile-page__card {
  border-radius: 24rpx;
  background: rgba(255, 255, 255, 0.8);
  border: 1rpx solid rgba(197, 198, 207, 0.3);
  padding: 18rpx;
  margin-bottom: 16rpx;
}

.profile-page__card-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.profile-page__card-title {
  color: #082248;
  font-size: 42rpx;
  font-weight: 800;
}

.profile-page__card-link {
  color: #0f5b8e;
  font-size: 24rpx;
  font-weight: 700;
}

.profile-page__form-grid {
  margin-top: 14rpx;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12rpx;
}

.profile-page__label {
  color: #60738c;
  font-size: 21rpx;
  margin-bottom: 6rpx;
}

.profile-page__input {
  min-height: 64rpx;
  border-radius: 12rpx;
  background: #eef3f9;
  display: flex;
  align-items: center;
  padding: 0 14rpx;
  color: #1f3450;
  font-size: 24rpx;
}

.profile-page__form-actions {
  margin-top: 14rpx;
  display: flex;
  gap: 10rpx;
}

.profile-page__btn {
  min-width: 140rpx;
  height: 62rpx;
  border-radius: 14rpx;
  padding: 0 20rpx;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 24rpx;
  font-weight: 800;
}

.profile-page__btn.primary {
  background: #0a254c;
  color: #edf6ff;
}

.profile-page__btn.light {
  background: #eef2f7;
  color: #465974;
}

.profile-page__btn.danger {
  background: #d93434;
  color: #fff;
}

.profile-page__btn.primary.disabled {
  background: #b7c3d4;
  color: #f2f7ff;
}

.profile-page__input-field {
  width: 100%;
  box-sizing: border-box;
}

.profile-page__access-grid {
  margin-top: 12rpx;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10rpx;
}

.profile-page__access-item {
  border-radius: 14rpx;
  border-left: 5rpx solid #d3dce8;
  background: #f3f7fc;
  padding: 12rpx;
  display: grid;
  grid-template-columns: 40rpx 1fr;
  gap: 10rpx;
}

.profile-page__access-item.ok {
  border-left-color: #2ebf71;
}

.profile-page__access-item.warn {
  border-left-color: #f3a51d;
}

.profile-page__access-item.lock {
  border-left-color: #b5c0cf;
}

.profile-page__access-icon {
  width: 40rpx;
  height: 40rpx;
  border-radius: 10rpx;
  background: #e5edf8;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #29517f;
  font-size: 20rpx;
}

.profile-page__access-name {
  color: #112f53;
  font-size: 23rpx;
  font-weight: 700;
}

.profile-page__access-sub {
  margin-top: 4rpx;
  color: #6f8097;
  font-size: 20rpx;
}

.profile-page__timeline-card {
  height: 100%;
}

.profile-page__timeline {
  margin-top: 12rpx;
  display: grid;
  gap: 10rpx;
}

.profile-page__timeline-item {
  display: grid;
  grid-template-columns: 24rpx 1fr;
  gap: 10rpx;
}

.profile-page__timeline-dot {
  width: 20rpx;
  height: 20rpx;
  border-radius: 999rpx;
  margin-top: 4rpx;
  background: #c9d4e3;
}

.profile-page__timeline-dot.ok {
  background: #3eb4ea;
}

.profile-page__timeline-dot.warn {
  background: #f3be2f;
}

.profile-page__timeline-title {
  color: #0d294f;
  font-size: 24rpx;
  font-weight: 700;
}

.profile-page__timeline-desc {
  margin-top: 2rpx;
  color: #63768f;
  font-size: 21rpx;
  line-height: 1.5;
}

.profile-page__timeline-time {
  margin-top: 4rpx;
  color: #8a99ae;
  font-size: 19rpx;
}

.profile-page__timeline-btn {
  margin-top: 14rpx;
  height: 56rpx;
  border-radius: 12rpx;
  border: 1rpx solid rgba(132, 147, 168, 0.35);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #455973;
  font-size: 22rpx;
  font-weight: 700;
}

/* #ifndef H5 */
.profile-page__shell {
  padding-left: 24rpx;
  padding-right: 24rpx;
}

.profile-page__stats {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.profile-page__layout,
.profile-page__form-grid,
.profile-page__access-grid {
  grid-template-columns: 1fr;
}

.profile-page__name {
  font-size: 48rpx;
}
/* #endif */

/* #ifdef H5 */
@media screen and (min-width: 1500px) {
  .profile-page__shell {
    padding-left: 56rpx;
    padding-right: 56rpx;
  }
}

@media screen and (max-width: 1120px) {
  .profile-page__stats {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .profile-page__layout {
    grid-template-columns: 1fr;
  }
}

@media screen and (max-width: 760px) {
  .profile-page__stats,
  .profile-page__form-grid,
  .profile-page__access-grid {
    grid-template-columns: 1fr;
  }
}
/* #endif */
</style>
