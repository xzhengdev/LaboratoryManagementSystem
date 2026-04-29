<template>
  <view class="daily-report-page">
    <student-top-nav active="dailyReport" />

    <view class="daily-report-shell">
      <view class="daily-report-head">
        <view class="daily-report-title">实验室日报上报</view>
        <view class="daily-report-sub">学生拍照上传实验室情况，管理员集中审核，不再依赖微信群收图。</view>
      </view>

      <view class="card report-form">
        <view class="report-form-title">提交日报</view>
        <view class="field">
          <view class="label">实验室</view>
          <picker :range="labOptions" range-key="lab_name" :value="labIndex" @change="changeLab">
            <view class="input picker-input">{{ currentLabName }}</view>
          </picker>
        </view>
        <view class="field">
          <view class="label">日期</view>
          <picker mode="date" :value="form.report_date" @change="changeDate">
            <view class="input picker-input">{{ form.report_date || '请选择日期' }}</view>
          </picker>
        </view>
        <view class="field">
          <view class="label">日报内容</view>
          <textarea
            v-model="form.content"
            class="textarea"
            maxlength="500"
            placeholder="请描述实验室当天使用情况、设备状态、卫生安全等"
          />
        </view>
        <view class="field">
          <view class="label">现场图片（最多6张）</view>
          <view class="photo-grid">
            <view
              v-for="(item, idx) in photoFiles"
              :key="item.id || idx"
              class="photo-item"
              @click="previewPhotos(idx)"
            >
              <image class="photo-img" :src="item.url" mode="aspectFill" />
              <view class="photo-remove" @click.stop="removePhoto(idx)">×</view>
            </view>
            <view v-if="photoFiles.length < 6" class="photo-add" @click="choosePhotos">+ 上传</view>
          </view>
        </view>

        <view class="form-actions">
          <view class="btn btn-primary" @click="submitReport">提交日报</view>
          <view class="btn btn-light" @click="resetForm">重置</view>
        </view>
      </view>

      <view class="card report-list">
        <view class="report-form-title">我的日报记录</view>
        <view v-if="!reportList.length" class="empty-text">暂无日报记录</view>
        <view v-for="item in reportList" :key="item.id" class="report-item">
          <view class="report-item-head">
            <view class="report-item-lab">{{ item.lab_name || '--' }}</view>
            <view :class="statusClass(item.status)">{{ statusText(item.status) }}</view>
          </view>
          <view class="report-item-time">{{ item.report_date || '--' }} · {{ timeText(item.created_at) }}</view>
          <view class="report-item-content">{{ item.content || '--' }}</view>
          <view v-if="Array.isArray(item.photos) && item.photos.length" class="report-item-photos">
            <image
              v-for="(photo, idx) in item.photos.slice(0, 4)"
              :key="photo.id || idx"
              class="report-thumb"
              :src="photo.url"
              mode="aspectFill"
              @click="previewHistoryPhotos(item, idx)"
            />
          </view>
          <view v-if="item.review_remark" class="report-item-remark">审核意见：{{ item.review_remark }}</view>
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

const todayText = () => {
  const now = new Date()
  const y = now.getFullYear()
  const m = String(now.getMonth() + 1).padStart(2, '0')
  const d = String(now.getDate()).padStart(2, '0')
  return `${y}-${m}-${d}`
}

export default {
  components: { StudentTopNav },
  data() {
    return {
      profile: {},
      labOptions: [],
      labIndex: 0,
      form: {
        lab_id: '',
        report_date: todayText(),
        content: ''
      },
      photoFiles: [],
      reportList: []
    }
  },
  computed: {
    currentLabName() {
      const item = this.labOptions[this.labIndex]
      return item ? item.lab_name : '请选择实验室'
    }
  },
  async onShow() {
    if (!requireLogin()) return
    this.profile = getProfile()
    if (this.profile.role !== 'student') {
      uni.showToast({ title: '日报提交仅支持学生端', icon: 'none' })
      openPage(routes.home, { replace: true })
      return
    }
    await this.loadPageData()
  },
  methods: {
    statusText(status) {
      const map = {
        pending: '待审核',
        approved: '已通过',
        rejected: '已驳回'
      }
      return map[status] || status || '--'
    },
    statusClass(status) {
      if (status === 'approved') return 'status approved'
      if (status === 'rejected') return 'status rejected'
      return 'status pending'
    },
    timeText(value) {
      if (!value) return '--'
      return String(value).replace('T', ' ').slice(0, 19)
    },
    async loadPageData() {
      await Promise.all([this.loadLabs(), this.loadMyReports()])
    },
    async loadLabs() {
      const rows = await api.labs({ campus_id: this.profile.campus_id })
      this.labOptions = Array.isArray(rows) ? rows : []
      if (this.labOptions.length) {
        this.labIndex = 0
        this.form.lab_id = this.labOptions[0].id
      }
    },
    async loadMyReports() {
      const rows = await api.dailyReports()
      this.reportList = Array.isArray(rows) ? rows : []
    },
    changeLab(event) {
      const next = Number(event.detail.value || 0)
      this.labIndex = next
      const row = this.labOptions[this.labIndex]
      this.form.lab_id = row ? row.id : ''
    },
    changeDate(event) {
      this.form.report_date = String(event.detail.value || '')
    },
    choosePhotos() {
      const remain = Math.max(0, 6 - this.photoFiles.length)
      if (!remain) {
        uni.showToast({ title: '最多上传6张图片', icon: 'none' })
        return
      }
      uni.chooseImage({
        count: remain,
        sizeType: ['compressed'],
        sourceType: ['album', 'camera'],
        success: async (res) => {
          const paths = Array.isArray(res?.tempFilePaths) ? res.tempFilePaths : []
          if (!paths.length) return
          await this.uploadPhotos(paths)
        }
      })
    },
    async uploadPhotos(paths) {
      uni.showLoading({ title: '上传中', mask: true })
      try {
        for (const filePath of paths) {
          const row = await api.uploadDailyReportPhoto(filePath, {
            campus_id: this.profile.campus_id,
            lab_id: this.form.lab_id || ''
          })
          this.photoFiles.push({
            id: row.id,
            url: row.url
          })
        }
        uni.showToast({ title: '图片上传成功', icon: 'success' })
      } finally {
        uni.hideLoading()
      }
    },
    removePhoto(index) {
      this.photoFiles.splice(index, 1)
    },
    previewPhotos(index = 0) {
      const urls = this.photoFiles.map((item) => item.url).filter(Boolean)
      if (!urls.length) return
      uni.previewImage({ urls, current: urls[index] || urls[0] })
    },
    previewHistoryPhotos(item, index = 0) {
      const urls = Array.isArray(item?.photos)
        ? item.photos.map((row) => row?.url).filter(Boolean)
        : []
      if (!urls.length) return
      uni.previewImage({ urls, current: urls[index] || urls[0] })
    },
    resetForm() {
      this.form.content = ''
      this.form.report_date = todayText()
      this.photoFiles = []
    },
    async submitReport() {
      if (!this.form.lab_id) {
        uni.showToast({ title: '请选择实验室', icon: 'none' })
        return
      }
      if (!String(this.form.content || '').trim()) {
        uni.showToast({ title: '请填写日报内容', icon: 'none' })
        return
      }
      const payload = {
        lab_id: this.form.lab_id,
        report_date: this.form.report_date,
        content: this.form.content,
        photo_file_ids: this.photoFiles.map((item) => item.id).filter((id) => Number(id) > 0)
      }
      await api.createDailyReport(payload)
      uni.showToast({ title: '日报提交成功', icon: 'success' })
      this.resetForm()
      await this.loadMyReports()
    }
  }
}
</script>

<style lang="scss">
.daily-report-page {
  min-height: 100vh;
  background: #eef4fb;
}

.daily-report-shell {
  padding: 24rpx 28rpx 40rpx;
}

.daily-report-head {
  margin-bottom: 16rpx;
}

.daily-report-title {
  font-size: 54rpx;
  font-weight: 800;
  color: #173252;
}

.daily-report-sub {
  margin-top: 10rpx;
  color: #60738e;
  font-size: 24rpx;
}

.card {
  background: #fff;
  border: 1rpx solid #deebf8;
  border-radius: 18rpx;
  padding: 18rpx;
  margin-bottom: 16rpx;
}

.report-form-title {
  font-size: 28rpx;
  font-weight: 800;
  color: #183654;
}

.field {
  margin-top: 12rpx;
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

.photo-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12rpx;
}

.photo-item,
.photo-add {
  position: relative;
  height: 180rpx;
  border-radius: 14rpx;
  border: 1rpx solid #dce7f5;
  background: #f6f9fe;
  overflow: hidden;
}

.photo-img {
  width: 100%;
  height: 100%;
}

.photo-add {
  display: flex;
  align-items: center;
  justify-content: center;
  color: #2c7da0;
  font-size: 28rpx;
  font-weight: 700;
}

.photo-remove {
  position: absolute;
  right: 8rpx;
  top: 8rpx;
  width: 34rpx;
  height: 34rpx;
  border-radius: 999rpx;
  background: rgba(10, 21, 35, 0.56);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22rpx;
}

.form-actions {
  margin-top: 16rpx;
  display: flex;
  gap: 12rpx;
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

.btn-light {
  background: #eaf2fb;
  color: #415b7c;
}

.empty-text {
  margin-top: 12rpx;
  color: #7a8ca3;
  font-size: 22rpx;
}

.report-item {
  margin-top: 12rpx;
  padding: 14rpx;
  border-radius: 12rpx;
  border: 1rpx solid #e3edf9;
  background: #f8fbff;
}

.report-item-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.report-item-lab {
  font-size: 25rpx;
  font-weight: 700;
  color: #163252;
}

.report-item-time {
  margin-top: 6rpx;
  color: #67809f;
  font-size: 21rpx;
}

.report-item-content {
  margin-top: 8rpx;
  color: #2f4865;
  font-size: 22rpx;
  line-height: 1.6;
}

.report-item-photos {
  margin-top: 10rpx;
  display: flex;
  gap: 8rpx;
}

.report-thumb {
  width: 88rpx;
  height: 88rpx;
  border-radius: 10rpx;
  border: 1rpx solid #d6e3f2;
}

.report-item-remark {
  margin-top: 10rpx;
  color: #9b5a00;
  font-size: 21rpx;
}

.status {
  font-size: 22rpx;
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

@media (max-width: 860px) {
  .daily-report-shell {
    padding: 14rpx 12rpx 24rpx;
  }

  .daily-report-title {
    font-size: 42rpx;
  }

  .photo-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .form-actions {
    flex-direction: column;
  }

  .btn {
    width: 100%;
  }
}
</style>
