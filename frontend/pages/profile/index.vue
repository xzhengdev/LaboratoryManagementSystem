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
        <view class="profile-page__avatar">
          <image v-if="profile.avatar_url" class="profile-page__avatar-img" :src="profile.avatar_url" mode="aspectFill" />
          <view v-else class="profile-page__avatar-fallback">{{ avatarText }}</view>
        </view>
        <view class="profile-page__hero-main">
          <view class="profile-page__name">{{ profile.real_name || '未命名用户' }}</view>
          <view class="profile-page__role">{{ roleText }}</view>
          <view class="profile-page__badges">
            <view class="profile-page__badge">ID: {{ profile.username || 'N/A' }}</view>
            <view class="profile-page__badge">{{ profile.email || '未设置邮箱' }}</view>
          </view>
        </view>
      </view>

      <view class="profile-page__layout">
        <view class="profile-page__card">
          <view class="profile-page__card-head">
            <view class="profile-page__card-title">基本信息设置</view>
            <view class="profile-page__card-link" @tap="toggleEdit">{{ isEditing ? '完成编辑' : '编辑资料' }}</view>
          </view>
          <view class="profile-page__form-grid">
            <view class="profile-page__field profile-page__field--full">
              <view class="profile-page__label">头像</view>
              <view class="profile-page__avatar-row">
                <view class="profile-page__avatar profile-page__avatar--small">
                  <image v-if="form.avatar_url" class="profile-page__avatar-img" :src="form.avatar_url" mode="aspectFill" />
                  <view v-else class="profile-page__avatar-fallback">{{ avatarText }}</view>
                </view>
                <view class="profile-page__btn light" :class="{ disabled: !isEditing }" @click="pickAvatar">更换头像</view>
              </view>
            </view>
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
      isEditing: false,
      form: {
        real_name: '',
        real_name_en: '',
        email: '',
        phone: '',
        avatar_url: ''
      }
    }
  },
  computed: {
    roleText() {
      return getRoleText(this.profile.role)
    },
    avatarText() {
      const source = this.form.real_name || this.profile.real_name || this.profile.username || 'U'
      return String(source).slice(0, 1).toUpperCase()
    }
  },
  async onShow() {
    if (!requireLogin()) return
    // #ifdef H5
    uni.hideTabBar()
    // #endif
    this.profile = getProfile()
    await this.refreshProfile()
    this.syncFormFromProfile()
  },
  methods: {
    async refreshProfile() {
      try {
        const latestProfile = await api.profile()
        if (latestProfile && latestProfile.id) {
          this.profile = latestProfile
          updateProfile(latestProfile)
        }
      } catch (_error) {
        // ignore
      }
    },
    syncFormFromProfile() {
      this.form = {
        real_name: this.profile.real_name || '',
        real_name_en: this.profile.real_name_en || this.profile.real_name || '',
        email: this.profile.email || '',
        phone: this.profile.phone || '',
        avatar_url: this.profile.avatar_url || ''
      }
    },
    toggleEdit() {
      this.isEditing = !this.isEditing
      if (!this.isEditing) {
        this.syncFormFromProfile()
      }
    },
    async saveProfile() {
      if (!this.isEditing) return
      try {
        const payload = {
          real_name: this.form.real_name || this.profile.real_name,
          email: this.form.email,
          phone: this.form.phone,
          avatar_url: this.form.avatar_url || ''
        }
        const saved = await api.updateProfile(payload)
        const merged = {
          ...this.profile,
          ...saved,
          real_name_en: this.form.real_name_en || this.profile.real_name_en
        }
        updateProfile(merged)
        this.profile = merged
        this.isEditing = false
        uni.showToast({ title: '资料已保存', icon: 'success' })
      } catch (_error) {
        uni.showToast({ title: '保存失败，请稍后重试', icon: 'none' })
      }
    },
    cancelEdit() {
      this.profile = getProfile()
      this.syncFormFromProfile()
      this.isEditing = false
      uni.showToast({ title: '已恢复当前资料', icon: 'none' })
    },
    pickAvatar() {
      if (!this.isEditing) return
      uni.chooseImage({
        count: 1,
        sizeType: ['compressed'],
        sourceType: ['album', 'camera'],
        success: async (res) => {
          const list = res && res.tempFilePaths ? res.tempFilePaths : []
          const files = res && res.tempFiles ? res.tempFiles : []
          if (!list.length) return
          if (files.length && files[0].size > 10 * 1024 * 1024) {
            uni.showToast({ title: '图片不能超过10MB', icon: 'none' })
            return
          }

          let loadingShown = false
          try {
            uni.showLoading({ title: '上传中', mask: true })
            loadingShown = true
            const uploaded = await api.uploadAvatar(list[0])
            this.form.avatar_url = uploaded.url
            uni.showToast({ title: '头像已上传', icon: 'success' })
          } catch (_error) {
            // toast handled in api layer
          } finally {
            if (loadingShown) {
              uni.hideLoading()
            }
          }
        },
        fail: () => {}
      })
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
  background: linear-gradient(135deg, #eaf2ff 0%, #dfeaf9 60%, #e9f3ff 100%);
  color: #112a49;
  border: 1rpx solid #d7e4f5;
}

.profile-page__avatar {
  width: 120rpx;
  height: 120rpx;
  border-radius: 24rpx;
  background: #ffffff;
  border: 2rpx solid #c9daef;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 44rpx;
  font-weight: 800;
  overflow: hidden;
}

.profile-page__avatar-img {
  width: 100%;
  height: 100%;
  display: block;
}

.profile-page__avatar-fallback {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.profile-page__name {
  font-size: 66rpx;
  font-weight: 800;
  line-height: 1.05;
}

.profile-page__role {
  margin-top: 8rpx;
  color: #2c7da0;
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
  background: #ffffff;
  color: #33557a;
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
  display: block;
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
  padding: 6rpx 12rpx;
  border-radius: 10rpx;
  background: #edf4fb;
  transition: all 0.2s ease;
}

.profile-page__card-link:hover {
  background: #e4eef9;
}

.profile-page__card-link:active {
  transform: scale(0.98);
}

.profile-page__form-grid {
  margin-top: 14rpx;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12rpx;
}

.profile-page__field--full {
  grid-column: 1 / -1;
}

.profile-page__avatar-row {
  display: flex;
  align-items: center;
  gap: 14rpx;
}

.profile-page__avatar--small {
  width: 84rpx;
  height: 84rpx;
  border-radius: 18rpx;
  font-size: 30rpx;
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

.profile-page__btn.light.disabled {
  opacity: 0.6;
}

.profile-page__input-field {
  width: 100%;
  box-sizing: border-box;
}

/* #ifndef H5 */
.profile-page__shell {
  padding-left: 24rpx;
  padding-right: 24rpx;
}

.profile-page__layout,
.profile-page__form-grid {
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
  .profile-page__form-grid {
    grid-template-columns: 1fr;
  }
}
/* #endif */
</style>

