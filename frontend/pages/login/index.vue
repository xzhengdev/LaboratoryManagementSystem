<template>
  <view class="login-page" :style="pageStyle">
    <view class="login-page__overlay"></view>

    <view class="login-page__content">
      <view class="login-card">
        <view class="login-title">登录</view>
        <view class="login-subtitle">分布式实验室管理系统</view>

        <view class="field">
          <picker mode="selector" :range="roleOptions" range-key="label" :value="roleIndex" @change="changeRole">
            <view class="login-input login-input--select">
              <text class="login-input__value">{{ currentRoleLabel }}</text>
              <text class="login-input__arrow">▾</text>
            </view>
          </picker>
        </view>

        <view class="field">
          <input
            v-model="form.username"
            class="login-input"
            placeholder="用户名"
            placeholder-class="login-placeholder"
          />
        </view>

        <view class="field password-field">
          <input
            v-model="form.password"
            class="login-input"
            :password="!showPassword"
            placeholder="密码"
            placeholder-class="login-placeholder"
          />
          <text class="password-toggle" @click="togglePassword">
            {{ showPassword ? '◉' : '◎' }}
          </text>
        </view>

        <view class="login-actions">
          <text class="login-forgot">忘记密码</text>
        </view>

        <view class="login-button" :class="{ 'login-button--loading': loading }" @click="submit">
          {{ loading ? '登录中...' : '登录' }}
        </view>
      </view>
    </view>
  </view>
</template>

<script>
import { api } from '../../api/index'
import { getLoginLandingPage, setSession } from '../../common/session'
import { roleTextMap } from '../../config/navigation'

export default {
  data() {
    const roleOptions = [
      { value: 'student', label: roleTextMap.student },
      { value: 'teacher', label: roleTextMap.teacher },
      { value: 'lab_admin', label: roleTextMap.lab_admin },
      { value: 'system_admin', label: roleTextMap.system_admin }
    ]

    return {
      form: {
        role: roleOptions[0].value,
        username: '',
        password: ''
      },
      loading: false,
      showPassword: false,
      backgroundUrl: '/static/login-bg.svg',
      roleOptions,
      roleIndex: 0
    }
  },
  computed: {
    pageStyle() {
      return this.backgroundUrl
        ? {
            backgroundImage: `url(${this.backgroundUrl})`
          }
        : {}
    },
    currentRoleLabel() {
      return this.roleOptions[this.roleIndex]?.label || '请选择角色'
    }
  },
  methods: {
    togglePassword() {
      this.showPassword = !this.showPassword
    },
    changeRole(event) {
      const nextIndex = Number(event.detail.value || 0)
      this.roleIndex = nextIndex
      this.form.role = this.roleOptions[nextIndex]?.value || this.roleOptions[0].value
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
  background-color: #000000;
  background-position: center;
  background-repeat: no-repeat;
  background-size: cover;
}

.login-page__overlay {
  position: absolute;
  inset: 0;
  background:
    linear-gradient(180deg, rgba(17, 19, 24, 0.12) 0%, rgba(12, 16, 20, 0.34) 100%);
}

.login-page__content {
  position: relative;
  z-index: 1;
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 32rpx;
  box-sizing: border-box;
}

.login-card {
  width: 100%;
  max-width: 760rpx;
  padding: 70rpx 58rpx 54rpx;
  border-radius: 34rpx;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.38), rgba(255, 255, 255, 0.2));
  border: 1rpx solid rgba(255, 255, 255, 0.24);
  box-shadow: 0 28rpx 60rpx rgba(0, 0, 0, 0.2);
  backdrop-filter: blur(18px);
  box-sizing: border-box;
}

.login-title {
  text-align: center;
  color: #2c2c2c;
  font-size: 64rpx;
  font-weight: 600;
  line-height: 1.12;
  letter-spacing: 0.4rpx;
}

.login-subtitle {
  margin-top: 12rpx;
  text-align: center;
  color: rgba(29, 29, 31, 0.62);
  font-size: 24rpx;
  line-height: 1.5;
}


.field {
  margin-top: 24rpx;
}

.password-field {
  position: relative;
}

.login-input {
  width: 100%;
  min-height: 92rpx;
  padding: 0 28rpx;
  border: none;
  border-radius: 16rpx;
  background: rgba(255, 255, 255, 0.92);
  color: #1d1d1f;
  font-size: 28rpx;
  box-sizing: border-box;
  box-shadow: inset 0 1rpx 0 rgba(255, 255, 255, 0.6);
}

.login-input--select {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.login-input__value {
  color: #1d1d1f;
}

.login-input__arrow {
  color: rgba(29, 29, 31, 0.5);
  font-size: 22rpx;
}

.login-placeholder {
  color: rgba(29, 29, 31, 0.42);
}

.password-toggle {
  position: absolute;
  top: 50%;
  right: 24rpx;
  transform: translateY(-50%);
  color: rgba(29, 29, 31, 0.56);
  font-size: 28rpx;
  line-height: 1;
}

.login-actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 16rpx;
}

.login-forgot {
  color: #000000;
  font-size: 24rpx;
}

.login-button {
  width: 220rpx;
  margin: 32rpx auto 0;
  min-height: 82rpx;
  border-radius: 16rpx;
  background: linear-gradient(180deg, #39d85d 0%, #27bf48 100%);
  color: #ffffff;
  font-size: 30rpx;
  line-height: 82rpx;
  text-align: center;
  box-shadow: 0 18rpx 32rpx rgba(39, 191, 72, 0.24);
}

.login-button--loading {
  opacity: 0.82;
}

/* #ifdef H5 */
@media screen and (min-width: 1024px) {
  .login-card {
    max-width: 480px;
    padding: 52px 44px 40px;
    border-radius: 22px;
  }

  .login-title {
    font-size: 40px;
    letter-spacing: -0.2px;
  }

  .login-subtitle {
    margin-top: 10px;
    font-size: 14px;
  }

  .field {
    margin-top: 16px;
  }

  .login-input {
    min-height: 46px;
    padding: 0 14px;
    border-radius: 10px;
    font-size: 16px;
  }

  .login-input__arrow {
    font-size: 12px;
  }

  .password-toggle {
    right: 14px;
    font-size: 16px;
  }

  .login-actions {
    margin-top: 12px;
  }

  .login-forgot {
    font-size: 14px;
  }

  .login-button {
    width: 120px;
    margin-top: 2px;
    min-height: 46px;
    border-radius: 10px;
    font-size: 16px;
    line-height: 46px;
  }
}
/* #endif */
</style>
