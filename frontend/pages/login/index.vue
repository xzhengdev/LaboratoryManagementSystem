<template>
  <view class="login-page">
    <view class="login-page__glow login-page__glow--left"></view>
    <view class="login-page__glow login-page__glow--right"></view>

    <view class="login-page__content">
      <view class="login-page__main">
        <view class="login-card">
          <view class="login-hero">
            <view class="login-hero__badge">
              <image class="login-hero__badge-img" src="/static/logo.png" mode="aspectFill" />
            </view>
            <view class="login-title">实验室管理系统</view>
            <view class="login-subtitle">统一身份认证·安全访问实验资源</view>
          </view>

          <view class="login-section">
            <view class="role-grid">
              <view
                v-for="(item, index) in roleOptions"
                :key="item.value"
                class="role-card"
                :class="{ 'role-card--active': roleIndex === index }"
                @click="selectRole(index)"
              >
                <view class="role-card__icon" :class="item.tone">
                  <image class="role-card__icon-image" :src="item.icon" mode="aspectFit" />
                </view>
                <text class="role-card__text">{{ item.label }}</text>
              </view>
            </view>
          </view>

          <view class="login-form">
            <view class="input-wrap">
              <text class="input-wrap__icon">账号</text>
              <input
                v-model="form.username"
                class="login-input"
                placeholder="用户名/工号"
                placeholder-class="login-placeholder"
              />
            </view>

            <view class="input-wrap">
              <text class="input-wrap__icon">密码</text>
              <input
                v-model="form.password"
                class="login-input login-input--password"
                :password="!showPassword"
                placeholder="密码"
                placeholder-class="login-placeholder"
              />
              <text class="password-toggle" @click="togglePassword">{{ showPassword ? '隐藏' : '显示' }}</text>
            </view>
          </view>

          <view class="login-tools">
            <view class="remember-box" @click="rememberMe = !rememberMe">
              <view class="remember-box__check" :class="{ 'remember-box__check--active': rememberMe }">
                <text v-if="rememberMe" class="remember-box__tick">√</text>
              </view>
              <text class="remember-box__label">记住账号</text>
            </view>
            <text class="forgot-link">忘记密码</text>
          </view>

          <view class="login-button" :class="{ 'login-button--loading': loading }" @click="submit">
            {{ loading ? '登录中...' : '立即登录' }}
          </view>
        </view>
      </view>

      <view class="login-page__bottom">
        <view class="login-footer">
          <view class="login-footer__line"></view>
          <text class="login-footer__text">仅限校内访问 · 内网安全区域</text>
        </view>
        <view class="page-footer">LABORATORY MANAGEMENT PLATFORM</view>
      </view>
    </view>
  </view>
</template>

<script>
import { api } from '../../api/index'
import { getLoginLandingPage, setSession } from '../../common/session'
import { roleTextMap } from '../../config/navigation'
import studentIcon from '../../static/icons/student.png'
import teacherIcon from '../../static/icons/teacher.png'
import labAdminIcon from '../../static/icons/lab-admin.png'
import systemAdminIcon from '../../static/icons/system-admin.png'

export default {
  data() {
    const roleOptions = [
      { value: 'student', label: roleTextMap.student, icon: studentIcon, tone: 'role-card__icon--tone-1' },
      { value: 'teacher', label: roleTextMap.teacher, icon: teacherIcon, tone: 'role-card__icon--tone-2' },
      { value: 'lab_admin', label: roleTextMap.lab_admin, icon: labAdminIcon, tone: 'role-card__icon--tone-3' },
      { value: 'system_admin', label: roleTextMap.system_admin, icon: systemAdminIcon, tone: 'role-card__icon--tone-4' }
    ]

    return {
      form: {
        role: roleOptions[0].value,
        username: '',
        password: ''
      },
      roleOptions,
      roleIndex: 0,
      rememberMe: true,
      showPassword: false,
      loading: false
    }
  },
  methods: {
    selectRole(index) {
      this.roleIndex = index
      this.form.role = this.roleOptions[index].value
    },
    togglePassword() {
      this.showPassword = !this.showPassword
    },
    async submit() {
      if (this.loading) return
      if (!this.form.username || !this.form.password) {
        uni.showToast({ title: '请输入用户名和密码', icon: 'none' })
        return
      }

      this.loading = true
      try {
        const res = await api.login(this.form)
        setSession(res.token, res.user)
        uni.reLaunch({ url: getLoginLandingPage(res.user?.role) })
      } finally {
        this.loading = false
      }
    }
  }
}
</script>

<style lang="scss">
.login-page {
  position: relative;
  min-height: 100vh;
  overflow: hidden;
  background:
    radial-gradient(circle at 12% 14%, rgba(109, 179, 230, 0.24), transparent 28%),
    radial-gradient(circle at 88% 18%, rgba(173, 208, 240, 0.24), transparent 24%),
    linear-gradient(180deg, #edf5fc 0%, #dceaf7 100%);
}

.login-page__glow {
  position: absolute;
  width: 320rpx;
  height: 320rpx;
  border-radius: 999rpx;
  filter: blur(18rpx);
  pointer-events: none;
}

.login-page__glow--left {
  left: -80rpx;
  top: 120rpx;
  background: rgba(150, 206, 244, 0.36);
}

.login-page__glow--right {
  right: -70rpx;
  top: 260rpx;
  background: rgba(184, 199, 236, 0.32);
}

.login-page__content {
  position: relative;
  z-index: 1;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  padding: 36rpx 24rpx 24rpx;
  box-sizing: border-box;
}

.login-page__main {
  flex: 1;
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.login-page__bottom {
  width: 100%;
  text-align: center
}

.login-card {
  width: 30%;
  max-width: 720rpx;
  border-radius: 28rpx;
  background: linear-gradient(180deg, rgba(249, 254, 255, 0.92), rgba(239, 252, 255, 0.86));
  border: 1rpx solid rgba(169, 198, 225, 0.55);
  box-shadow: 0 26rpx 60rpx rgba(0, 0, 0, 0.26);
  box-sizing: border-box;
}

.login-hero {
  text-align: center;
  margin-bottom: 34rpx;
}

.login-section {
  margin-bottom: 14rpx;
}

.login-hero__badge {
  width: 112rpx;
  height: 112rpx;
  margin: 0 auto 14rpx;
  border-radius: 28rpx;
  padding: 10rpx;
  // border: 1rpx solid rgba(0, 0, 0, 0.15);
  box-sizing: border-box;
}

.login-hero__badge-img {
  width: 100%;
  height: 100%;
  border-radius: 20rpx;
}

.login-title {
  color: #12243d;
  font-size: 56rpx;
  line-height: 1.1;
  font-weight: 800;
}

.login-subtitle {
  margin-top: 10rpx;
  color: #3a5674;
  font-size: 24rpx;
  font-weight: 600;
}

.role-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12rpx;
  padding: 12rpx;
  border-radius: 20rpx;
}

.role-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8rpx;
  min-height: 98rpx;
  border-radius: 16rpx;
  color: #385673;
  border: 1rpx solid transparent;
  transition: all 180ms cubic-bezier(0.16, 1, 0.3, 1);
}

.role-card--active {
  background: rgba(241, 252, 255, 0.96);
  box-shadow: 0 10rpx 20rpx rgba(117, 117, 117, 0.3);
}

.role-card__icon {
  width: 48rpx;
  height: 48rpx;
  border-radius: 14rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1rpx solid rgba(0, 0, 0, 0.18);
}


.role-card__icon-image {
  width: 28rpx;
  height: 28rpx;
}

.role-card__text {
  font-size: 18rpx;
  font-weight: 700;
}

.login-form {
  display: grid;
  gap: 18rpx;
  margin-top: 0;
}

.input-wrap {
  position: relative;
}

.input-wrap__icon {
  position: absolute;
  top: 50%;
  left: 22rpx;
  transform: translateY(-50%);
  color: #000000;
  font-size: 22rpx;
  font-weight: 700;
}

.login-input {
  width: 100%;
  min-height: 84rpx;
  padding: 0 22rpx 0 86rpx;
  border-radius: 18rpx;
  // background: rgba(255, 255, 255, 0.96);
  // color: #15314f;
  font-size: 22rpx;
  box-sizing: border-box;
  border: 1rpx solid rgba(0, 0, 0, 0.38);
}

.login-input--password {
  padding-right: 88rpx;
}

// .login-placeholder {
//   color: rgba(92, 121, 148, 0.8);
// }

.password-toggle {
  position: absolute;
  top: 50%;
  right: 24rpx;
  transform: translateY(-50%);
  color: #3d6690;
  font-size: 22rpx;
  font-weight: 700;
}

.login-tools {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 22rpx;
}

.remember-box {
  display: flex;
  align-items: center;
  gap: 10rpx;
}

.remember-box__check {
  width: 32rpx;
  height: 32rpx;
  border-radius: 8rpx;
  border: 2rpx solid rgba(124, 169, 208, 0.82);
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: #eff6fd;
  transition: all 0.2s ease;
}

.remember-box__check--active {
  background: #2f6f95;
  border-color: #2f6f95;
}

.remember-box__tick {
  color: #ffffff;
  font-size: 18rpx;
  font-weight: 800;
}

.remember-box__label,
.forgot-link {
  color: #3e5d7c;
  font-size: 22rpx;
  font-weight: 600;
}

.login-button {
  margin-top: 30rpx;
  min-height: 80rpx;
  border-radius: 20rpx;
  background: linear-gradient(135deg, #8fb4e5 0%, #38a3e7 52%, #79c2d4 100%);
  color: #ffffff;
  font-size: 28rpx;
  font-weight: 800;
  line-height: 80rpx;
  text-align: center;
  box-shadow: 0 18rpx 34rpx rgba(41, 97, 146, 0.24);
}

.login-button--loading {
  opacity: 0.84;
}

.login-footer {
  margin-top: 0;
  text-align: center;
}

.login-footer__line {
  width: 64rpx;
  height: 6rpx;
  border-radius: 999rpx;
  margin: 0 auto 12rpx;
  background: rgba(78, 125, 167, 0.22);
}

.login-footer__text {
  color: #4f7092;
  font-size: 19rpx;
  font-weight: 700;
  letter-spacing: 1rpx;
}

.page-footer {
  margin-top: 16rpx;
  color: rgba(53, 87, 121, 0.66);
  font-size: 16rpx;
  letter-spacing: 2rpx;
}

@media screen and (max-width: 768px) {
  .login-page__content {
    padding: 28rpx 18rpx calc(18rpx + env(safe-area-inset-bottom));
  }

  .login-page__main {
    align-items: flex-start;
    padding-top: 24rpx;
  }

  .login-card {
    width: 100%;
    max-width: none;
    border-radius: 24rpx;
    padding: 30rpx 22rpx 24rpx;
    box-shadow: 0 16rpx 36rpx rgba(0, 0, 0, 0.18);
  }

  .login-hero {
    margin-bottom: 24rpx;
  }

  .login-title {
    font-size: 48rpx;
  }

  .login-subtitle {
    font-size: 22rpx;
    line-height: 1.5;
  }

  .role-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 10rpx;
    padding: 10rpx;
  }

  .role-card {
    min-height: 92rpx;
  }

  .role-card__text {
    font-size: 22rpx;
  }

  .login-input {
    min-height: 82rpx;
    font-size: 28rpx;
  }

  .input-wrap__icon,
  .password-toggle,
  .remember-box__label,
  .forgot-link {
    font-size: 24rpx;
  }

  .login-button {
    min-height: 82rpx;
    line-height: 82rpx;
    font-size: 30rpx;
  }

  .login-page__bottom {
    margin-top: 12rpx;
  }
}


@media screen and (min-width: 1024px) {
  .login-page__content {
    padding: 24px 24px 18px;
  }

  .login-card {
    max-width: 560px;
    // min-height: 560px;
    padding: 34px 24px 24px;
    border-radius: 20px;
  }

  .login-hero {
    margin-bottom: 18px;
  }

  .login-section {
    margin-bottom: 8px;
  }

  .login-hero__badge {
    width: 64px;
    height: 64px;
    margin-bottom: 10px;
    border-radius: 16px;
    padding: 7px;
  }

  .login-hero__badge-img {
    border-radius: 11px;
  }

  .login-title {
    font-size: 32px;
  }

  .login-subtitle {
    margin-top: 6px;
    font-size: 13px;
  }

  .role-grid {
    gap: 8px;
    padding: 8px;
    border-radius: 14px;
  }

  .role-card {
    min-height: 62px;
    border-radius: 11px;
    gap: 6px;
  }

  .role-card__icon {
    width: 24px;
    height: 24px;
    border-radius: 8px;
  }

  .role-card__icon-image {
    width: 14px;
    height: 14px;
  }

  .role-card__text {
    font-size: 10px;
  }

  .login-form {
    gap: 11px;
    margin-top: 0;
  }

  .input-wrap__icon {
    left: 14px;
    font-size: 12px;
  }

  .login-input {
    min-height: 42px;
    padding: 0 14px 0 52px;
    border-radius: 12px;
    font-size: 14px;
  }

  .login-input--password {
    padding-right: 56px;
  }

  .password-toggle {
    right: 14px;
    font-size: 12px;
  }

  .login-tools {
    margin-top: 12px;
  }

  .remember-box__check {
    width: 14px;
    height: 14px;
    border-radius: 4px;
    border-width: 1.5px;
  }

  .remember-box__tick {
    font-size: 9px;
  }

  .remember-box__label,
  .forgot-link {
    font-size: 12px;
  }

  .login-button {
    margin-top: 18px;
    min-height: 44px;
    border-radius: 12px;
    font-size: 15px;
    line-height: 44px;
  }

  .login-footer {
    margin-top: 0;
  }

  .login-footer__line {
    width: 32px;
    height: 4px;
    margin-bottom: 8px;
  }

  .login-footer__text {
    font-size: 11px;
  }

  .page-footer {
    margin-top: 8px;
    font-size: 10px;
    letter-spacing: 2px;
  }
}

</style>
