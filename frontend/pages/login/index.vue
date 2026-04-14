<template>
  <view class="login-page" :style="pageStyle">
    <view class="login-page__overlay"></view>

    <view class="login-page__content">
      <view class="login-card">
        <view class="login-hero">
         <view class="login-hero__badge">
          <image 
            class="login-hero__badge-img" 
            src="/static/logo.png" 
            mode="aspectFill"
          />
        </view>
          <view class="login-title">登录</view>
          <view class="login-subtitle">分布式实验室预约管理系统</view>
        </view>

        <view class="login-section">
          <view class="login-section__label">身份角色选择</view>
          <view class="role-grid">
            <view
              v-for="(item, index) in roleOptions"
              :key="item.value"
              class="role-card"
              :class="{ 'role-card--active': roleIndex === index }"
              @click="selectRole(index)"
            >
              <view class="role-card__icon">
                <image class="role-card__icon-image" :src="item.icon" mode="aspectFit" />
              </view>
              <text class="role-card__text">{{ item.label }}</text>
            </view>
          </view>
        </view>

        <view class="login-form">
          <view class="input-wrap">
            <text class="input-wrap__icon">👤</text>
            <input
              v-model="form.username"
              class="login-input"
              placeholder="用户名 / 学工号"
              placeholder-class="login-placeholder"
            />
          </view>

          <view class="input-wrap">
            <text class="input-wrap__icon">🔒</text>
            <input
              v-model="form.password"
              class="login-input login-input--password"
              :password="!showPassword"
              placeholder="请输入密码"
              placeholder-class="login-placeholder"
            />
            <text class="password-toggle" @click="togglePassword">
              {{ showPassword ? '◉' : '◎' }}
            </text>
          </view>
        </view>

        <view class="login-tools">
          <view class="remember-box" @click="rememberMe = !rememberMe">
            <view class="remember-box__check" :class="{ 'remember-box__check--active': rememberMe }">
              <text v-if="rememberMe" class="remember-box__tick">✓</text>
            </view>
            <text class="remember-box__label">记住我</text>
          </view>
          <text class="forgot-link">忘记密码？</text>
        </view>

        <view class="login-button" :class="{ 'login-button--loading': loading }" @click="submit">
          {{ loading ? '登录中...' : '立即登录' }}
        </view>

        <view class="login-footer">
          <view class="login-footer__line"></view>
          <text class="login-footer__text">仅限校内访问 · 内网安全区域</text>
          <view class="login-footer__badge-row">
            <view class="login-footer__badge">校</view>
          </view>
        </view>
      </view>

      <view class="page-footer">LABORATORY MANAGEMENT PLATFORM</view>
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
      { value: 'student', label: roleTextMap.student, icon: studentIcon },
      { value: 'teacher', label: roleTextMap.teacher, icon: teacherIcon },
      { value: 'lab_admin', label: roleTextMap.lab_admin, icon: labAdminIcon },
      { value: 'system_admin', label: roleTextMap.system_admin, icon: systemAdminIcon }
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
      loading: false,
      backgroundUrl: '/static/login-bg.svg'
    }
  },
  computed: {
    pageStyle() {
      return this.backgroundUrl
        ? {
            backgroundImage: `url(${this.backgroundUrl})`
          }
        : {}
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
  background-color: #031635;
  background-position: center;
  background-repeat: no-repeat;
  background-size: cover;
}

.login-page__overlay {
  position: absolute;
  inset: 0;
  background:
    linear-gradient(135deg, rgba(3, 22, 53, 0.9) 0%, rgba(26, 43, 75, 0.68) 44%, rgba(0, 101, 141, 0.24) 100%);
}

.login-page__content {
  position: relative;
  z-index: 1;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 28rpx 24rpx 40rpx;
  box-sizing: border-box;
}

.login-card {
  width: 48%;
  max-width: 720rpx;
  padding: 44rpx 34rpx 32rpx;
  border-radius: 32rpx;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.78), rgba(247, 249, 252, 0.68));
  border: 1rpx solid rgba(255, 255, 255, 0.34);
  backdrop-filter: blur(28rpx);
  box-shadow: 0 30rpx 80rpx rgba(0, 0, 0, 0.26);
  box-sizing: border-box;
}

.login-hero {
  text-align: center;
  margin-bottom: 30rpx;
}

.login-hero__badge-img {
  width: 100%;
  height: 100%;
  border-radius: 50%;
  /* 外阴影 + 内阴影 = 凸起感 */
  box-shadow: 0 10rpx 20rpx rgba(0, 0, 0, 0.5),
              inset 0 2rpx 4rpx rgba(255, 255, 255, 0.4),
              inset 0 -2rpx 2rpx rgba(0, 0, 0, 0.3);
}

.login-title {
  color: #031635;
  font-size: 54rpx;
  line-height: 1.1;
  font-weight: 800;
  letter-spacing: 0.6rpx;
}

.login-subtitle {
  margin-top: 10rpx;
  color: #44474e;
  font-size: 24rpx;
  font-weight: 600;
  letter-spacing: 0.4rpx;
}

.login-section__label {
  margin-bottom: 14rpx;
  padding-left: 6rpx;
  color: #44474e;
  font-size: 20rpx;
  font-weight: 700;
  letter-spacing: 2rpx;
}

.role-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14rpx;
  padding: 12rpx;
  border-radius: 24rpx;
  background: rgba(236, 238, 241, 0.9);
  box-shadow: inset 0 1rpx 0 rgba(255, 255, 255, 0.56);
}

.role-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8rpx;
  min-height: 108rpx;
  border-radius: 18rpx;
  color: #44474e;
  border: 1rpx solid transparent;
  transition: all 180ms cubic-bezier(0.16, 1, 0.3, 1);
}

.role-card--active {
  background: rgba(255, 255, 255, 0.96);
  color: #031635;
  border-color: rgba(182, 198, 239, 0.8);
  box-shadow: 0 10rpx 24rpx rgba(0, 0, 0, 0.08);
}

.role-card__icon {
  width: 44rpx;
  height: 44rpx;
  border-radius: 14rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  overflow: hidden;
}

.role-card__icon-image {
  width: 28rpx;
  height: 28rpx;
}

.role-card__text {
  font-size: 20rpx;
  font-weight: 700;
  text-align: center;
  line-height: 1.35;
}

.login-form {
  display: grid;
  gap: 14rpx;
  margin-top: 22rpx;
}

.input-wrap {
  position: relative;
}

.input-wrap__icon {
  position: absolute;
  top: 50%;
  left: 22rpx;
  transform: translateY(-50%);
  color: #44474e;
  font-size: 26rpx;
  font-weight: 700;
}

.login-input {
  width: 100%;
  min-height: 82rpx;
  padding: 0 22rpx 0 66rpx;
  border: none;
  border-radius: 20rpx;
  background: rgba(236, 238, 241, 0.92);
  color: #031635;
  font-size: 26rpx;
  box-sizing: border-box;
  border: 1rpx solid rgba(197, 198, 207, 0.5);
  box-shadow: inset 0 1rpx 0 rgba(255, 255, 255, 0.54);
}

.login-input--password {
  padding-right: 66rpx;
}

.login-placeholder {
  color: rgba(117, 119, 127, 0.88);
}

.password-toggle {
  position: absolute;
  top: 50%;
  right: 24rpx;
  transform: translateY(-50%);
  color: #4e5e81;
  font-size: 24rpx;
  line-height: 1;
}

.login-tools {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 18rpx;
  padding: 0 6rpx;
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
  border: 2rpx solid #c5c6cf;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 2rpx solid #ccc;
  background-color: #f5f7fa;
  transition: all 0.3s ease;
}

.remember-box__check--active {
  background: #00658d;
  border-color: #00658d;
}

.remember-box__tick {
  color: #ffffff;
  font-size: 18rpx;
  font-weight: 700;
}

.remember-box__label {
  color: #44474e;
  font-size: 22rpx;
  font-weight: 600;
}

.forgot-link {
  color: #00658d;
  font-size: 22rpx;
  font-weight: 600;
}

.login-button {
  margin-top: 22rpx;
  min-height: 78rpx;
  border-radius: 20rpx;
  background: linear-gradient(135deg, #031635 0%, #1a2b4b 100%);
  color: #ffffff;
  font-size: 28rpx;
  font-weight: 800;
  line-height: 78rpx;
  text-align: center;
  box-shadow: 0 24rpx 44rpx rgba(3, 22, 53, 0.24);
  border: 1rpx solid rgba(255, 255, 255, 0.14);
}

.login-button--loading {
  opacity: 0.84;
}

.login-footer {
  margin-top: 24rpx;
  padding-top: 20rpx;
  border-top: 1rpx solid rgba(0, 0, 0, 0.06);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 14rpx;
}

.login-footer__line {
  width: 64rpx;
  height: 6rpx;
  border-radius: 999rpx;
  background: rgba(3, 22, 53, 0.12);
}

.login-footer__text {
  color: #44474e;
  font-size: 18rpx;
  font-weight: 700;
  letter-spacing: 2rpx;
}

.login-footer__badge-row {
  display: flex;
  align-items: center;
  justify-content: center;
}

.login-footer__badge {
  width: 48rpx;
  height: 48rpx;
  border-radius: 999rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.5);
  border: 1rpx solid rgba(255, 255, 255, 0.36);
  color: rgba(68, 71, 78, 0.72);
  font-size: 20rpx;
  font-weight: 700;
}

.page-footer {
  margin-top: 18rpx;
  color: rgba(255, 255, 255, 0.56);
  font-size: 16rpx;
  letter-spacing: 3rpx;
}

/* #ifdef H5 */
@media screen and (min-width: 1024px) {
  .login-page__content {
    padding: 20px 24px 28px;
  }

  .login-card {
    max-width: 840px;
    padding: 38px 32px 24px;
    border-radius: 28px;
  }

  .login-hero {
    margin-bottom: 22px;
  }

  .login-hero__badge {
    width: 72px;
    height: 72px;
    margin-bottom: 16px;
    border-radius: 22px;
  }

  .login-hero__badge-ring {
    inset: 7px;
    border-radius: 16px;
  }

  .login-hero__badge-icon {
    font-size: 34px;
  }

  .login-title {
    font-size: 34px;
    letter-spacing: -0.4px;
  }

  .login-subtitle {
    margin-top: 8px;
    font-size: 14px;
  }

  .login-section__label {
    margin-bottom: 8px;
    font-size: 10px;
    letter-spacing: 2px;
  }

  .role-grid {
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 8px;
    padding: 10px;
    border-radius: 18px;
  }

  .role-card {
    min-height: 78px;
    border-radius: 14px;
  }

  .role-card__icon {
    width: 30px;
    height: 30px;
    border-radius: 10px;
  }

  .role-card__icon-image {
    width: 18px;
    height: 18px;
  }

  .role-card__text {
    font-size: 11px;
  }

  .login-form {
    gap: 12px;
    margin-top: 16px;
  }

  .input-wrap__icon {
    left: 16px;
    font-size: 16px;
  }

  .login-input {
    min-height: 44px;
    padding: 0 16px 0 46px;
    border-radius: 14px;
    font-size: 15px;
  }

  .login-input--password {
    padding-right: 46px;
  }

  .password-toggle {
    right: 16px;
    font-size: 14px;
  }

  .login-tools {
    margin-top: 14px;
    padding: 0 2px;
  }

  .remember-box {
    gap: 8px;
  }

  .remember-box__check {
    width: 16px;
    height: 16px;
    border-radius: 5px;
    border-width: 1.5px;
  }

  .remember-box__tick {
    font-size: 10px;
  }

  .remember-box__label,
  .forgot-link {
    font-size: 12px;
  }

  .login-button {
    margin-top: 16px;
    min-height: 52px;
    border-radius: 16px;
    font-size: 16px;
    line-height: 52px;
  }

  .login-footer {
    margin-top: 18px;
    padding-top: 16px;
    gap: 10px;
  }

  .login-footer__line {
    width: 36px;
    height: 4px;
  }

  .login-footer__text {
    font-size: 10px;
    letter-spacing: 1.8px;
  }

  .login-footer__badge {
    width: 30px;
    height: 30px;
    font-size: 12px;
  }

  .page-footer {
    margin-top: 14px;
    font-size: 10px;
    letter-spacing: 3px;
  }
}
/* #endif */
</style>
