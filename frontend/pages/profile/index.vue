﻿<template>
  <view class="profile-page">
    <student-top-nav active="profile" />

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
            <view class="profile-page__btn light" @click="openPasswordDialog">修改密码</view>
            <view class="profile-page__btn danger" @click="logout">退出登录</view>
          </view>
        </view>
      </view>
    </view>

    <view v-if="passwordDialogVisible" class="profile-page__modal-mask" @click="closePasswordDialog">
      <view class="profile-page__password-modal" @click.stop>
        <view class="profile-page__password-head">
          <view>
            <view class="profile-page__password-title">修改密码</view>
            <view class="profile-page__password-sub">验证原密码后更新登录密码</view>
          </view>
          <view class="profile-page__password-close" @click="closePasswordDialog">×</view>
        </view>
        <view class="profile-page__password-fields">
          <view class="profile-page__field">
            <view class="profile-page__label">原密码</view>
            <input v-model.trim="passwordForm.old_password" class="profile-page__input profile-page__input-field" password placeholder="请输入当前密码" />
          </view>
          <view class="profile-page__field">
            <view class="profile-page__label">新密码</view>
            <input v-model.trim="passwordForm.new_password" class="profile-page__input profile-page__input-field" password placeholder="至少 6 位" />
          </view>
          <view class="profile-page__field">
            <view class="profile-page__label">确认新密码</view>
            <input v-model.trim="passwordForm.confirm_password" class="profile-page__input profile-page__input-field" password placeholder="再次输入新密码" />
          </view>
        </view>
        <view class="profile-page__form-actions profile-page__password-actions">
          <view class="profile-page__btn light" @click="closePasswordDialog">取消</view>
          <view class="profile-page__btn primary" :class="{ disabled: changingPassword }" @click="changePassword">确认修改</view>
        </view>
      </view>
    </view>

    <site-footer />
  </view>
</template>

<script>
import SiteFooter from '../../components/site-footer.vue'
import StudentTopNav from '../../components/student-top-nav.vue'
import { api } from '../../api/index'
import { requireLogin } from '../../common/guard'
import { openPage } from '../../common/router'
import { clearSession, getProfile, updateProfile } from '../../common/session'
import { getRoleText, routes } from '../../config/navigation'

export default {
  components: { SiteFooter, StudentTopNav },
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
      },
      passwordDialogVisible: false,
      changingPassword: false,
      passwordForm: {
        old_password: '',
        new_password: '',
        confirm_password: ''
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
    },
    resetPasswordForm() {
      this.passwordForm = {
        old_password: '',
        new_password: '',
        confirm_password: ''
      }
    },
    openPasswordDialog() {
      this.passwordDialogVisible = true
    },
    closePasswordDialog() {
      if (this.changingPassword) return
      this.passwordDialogVisible = false
      this.resetPasswordForm()
    },
    async changePassword() {
      if (this.changingPassword) return
      const oldPassword = this.passwordForm.old_password
      const newPassword = this.passwordForm.new_password
      const confirmPassword = this.passwordForm.confirm_password

      if (!oldPassword) {
        uni.showToast({ title: '请输入原密码', icon: 'none' })
        return
      }
      if (!newPassword || newPassword.length < 6) {
        uni.showToast({ title: '新密码至少 6 位', icon: 'none' })
        return
      }
      if (newPassword !== confirmPassword) {
        uni.showToast({ title: '两次输入的新密码不一致', icon: 'none' })
        return
      }

      this.changingPassword = true
      try {
        await api.changePassword({
          old_password: oldPassword,
          new_password: newPassword,
          confirm_password: confirmPassword
        })
        this.resetPasswordForm()
        this.passwordDialogVisible = false
        uni.showToast({ title: '密码修改成功', icon: 'success' })
      } catch (error) {
        uni.showToast({ title: error?.message || '密码修改失败', icon: 'none' })
      } finally {
        this.changingPassword = false
      }
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

.profile-page__modal-mask {
  position: fixed;
  inset: 0;
  z-index: 1000;
  background: rgba(10, 26, 45, 0.42);
  backdrop-filter: blur(4rpx);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 32rpx;
  box-sizing: border-box;
}

.profile-page__password-modal {
  width: 720rpx;
  max-width: calc(100vw - 64rpx);
  border-radius: 26rpx;
  background: #ffffff;
  padding: 28rpx;
  box-shadow: 0 30rpx 80rpx rgba(9, 36, 69, 0.22);
}

.profile-page__password-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20rpx;
  margin-bottom: 20rpx;
}

.profile-page__password-title {
  color: #082248;
  font-size: 34rpx;
  font-weight: 800;
}

.profile-page__password-sub {
  margin-top: 6rpx;
  color: #60738c;
  font-size: 22rpx;
  font-weight: 700;
}

.profile-page__password-close {
  width: 54rpx;
  height: 54rpx;
  border-radius: 999rpx;
  background: #edf3fb;
  color: #476183;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 34rpx;
  line-height: 1;
}

.profile-page__password-fields {
  display: grid;
  grid-template-columns: 1fr;
  gap: 14rpx;
}

.profile-page__password-actions {
  justify-content: flex-end;
}




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
  .profile-page__shell {
    padding: 16rpx 12rpx calc(16rpx + env(safe-area-inset-bottom));
  }

  .profile-page__hero {
    border-radius: 20rpx;
    padding: 14rpx;
    gap: 12rpx;
    align-items: flex-start;
  }

  .profile-page__avatar {
    width: 88rpx;
    height: 88rpx;
    border-radius: 16rpx;
    font-size: 34rpx;
  }

  .profile-page__name {
    font-size: 42rpx;
    line-height: 1.12;
  }

  .profile-page__role {
    margin-top: 6rpx;
    font-size: 24rpx;
  }

  .profile-page__badges {
    margin-top: 8rpx;
    gap: 6rpx;
  }

  .profile-page__badge {
    min-height: 32rpx;
    font-size: 18rpx;
    padding: 0 10rpx;
  }

  .profile-page__layout {
    margin-top: 12rpx;
  }

  .profile-page__card {
    border-radius: 18rpx;
    padding: 14rpx;
    margin-bottom: 12rpx;
  }

  .profile-page__card-title {
    font-size: 30rpx;
  }

  .profile-page__card-link {
    font-size: 20rpx;
    padding: 4rpx 10rpx;
    border-radius: 8rpx;
  }

  .profile-page__form-grid {
    margin-top: 10rpx;
    gap: 10rpx;
  }

  .profile-page__avatar-row {
    gap: 10rpx;
    flex-wrap: wrap;
  }

  .profile-page__avatar--small {
    width: 68rpx;
    height: 68rpx;
    border-radius: 14rpx;
    font-size: 24rpx;
  }

  .profile-page__label {
    font-size: 20rpx;
    margin-bottom: 5rpx;
  }

  .profile-page__input {
    min-height: 56rpx;
    font-size: 22rpx;
    border-radius: 10rpx;
    padding: 0 12rpx;
  }

  .profile-page__form-actions {
    margin-top: 12rpx;
    gap: 8rpx;
    flex-wrap: wrap;
  }

  .profile-page__btn {
    flex: 1 1 auto;
    min-width: 0;
    height: 54rpx;
    border-radius: 10rpx;
    font-size: 21rpx;
    padding: 0 12rpx;
  }

  .profile-page__stats,
  .profile-page__form-grid {
    grid-template-columns: 1fr;
  }
}

@media screen and (max-width: 420px) {
  .profile-page__name {
    font-size: 38rpx;
  }

  .profile-page__card-title {
    font-size: 28rpx;
  }
}

</style>

