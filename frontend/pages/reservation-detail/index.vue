<template>
  <view class="reservation-detail-page">
    <!-- #ifdef H5 -->
    <student-top-nav active="reservations" />
    <!-- #endif -->

    <!-- #ifndef H5 -->
    <user-top-nav active="reservations" />
    <!-- #endif -->

    <view class="reservation-detail-page__shell">
      <view class="reservation-detail-page__head">
        <view>
          <view class="reservation-detail-page__id">预约 ID: #{{ detail.reservation_code || ('LBS-' + (id || '--')) }}</view>
          <view class="reservation-detail-page__title">{{ detail.lab_name || '预约详情' }}</view>
          <view class="reservation-detail-page__sub">{{ detail.campus_name || '校区待定' }} · {{ detail.location || '楼宇待补充' }}</view>
        </view>

        <view class="reservation-detail-page__actions">
          <view class="reservation-detail-page__btn light" @click="downloadCert">下载证书</view>
          <view
            class="reservation-detail-page__btn danger"
            :class="{ disabled: !canCancel }"
            @click="cancelCurrent"
          >
            取消预约
          </view>
        </view>
      </view>

      <view class="reservation-detail-page__layout">
        <view class="reservation-detail-page__timeline-card">
          <view class="reservation-detail-page__card-head">
            <view class="reservation-detail-page__card-title">审批流程</view>
            <view class="reservation-detail-page__status-pill" :class="statusClass">{{ statusText }}</view>
          </view>

          <view class="reservation-detail-page__timeline">
            <view v-for="(node, idx) in timelineNodes" :key="idx" class="reservation-detail-page__node" :class="node.state">
              <view class="reservation-detail-page__node-mark"></view>
              <view class="reservation-detail-page__node-body">
                <view class="reservation-detail-page__node-title">{{ node.title }}</view>
                <view class="reservation-detail-page__node-time">{{ node.timeText }}</view>
                <view class="reservation-detail-page__node-desc">{{ node.desc }}</view>
                <view v-if="node.reviewer" class="reservation-detail-page__node-reviewer">
                  {{ node.reviewer }}
                </view>
              </view>
            </view>
          </view>
        </view>

        <view class="reservation-detail-page__side">
          <view class="reservation-detail-page__side-card schedule">
            <view class="reservation-detail-page__side-title">日程安排</view>
            <view class="reservation-detail-page__line">
              <text>预约日期</text>
              <text>{{ dateText }}</text>
            </view>
            <view class="reservation-detail-page__line two">
              <view>
                <view class="k">开始时间</view>
                <view class="v">{{ startText }}</view>
              </view>
              <view>
                <view class="k">结束时间</view>
                <view class="v">{{ endText }}</view>
              </view>
            </view>
            <view class="reservation-detail-page__line">
              <text>总时长</text>
              <text>{{ durationText }}</text>
            </view>
          </view>

          <view class="reservation-detail-page__side-card">
            <view class="reservation-detail-page__side-title">实验室环境</view>
            <view class="reservation-detail-page__line"><text>设备配置</text><text>{{ envConfig }}</text></view>
            <view class="reservation-detail-page__line"><text>生物安全等级</text><text>{{ envLevel }}</text></view>
            <view class="reservation-detail-page__line"><text>共享空间</text><text>{{ envSpace }}</text></view>
          </view>

          <view class="reservation-detail-page__purpose-card">
            <view class="reservation-detail-page__side-title light">研究目的</view>
            <view class="reservation-detail-page__purpose-text">{{ detail.purpose || '暂未填写用途说明。' }}</view>
            <view class="reservation-detail-page__purpose-id">机构研究查验项目 #{{ detail.id || '--' }}</view>
          </view>
        </view>
      </view>

      <view class="reservation-detail-page__tips">
        <view class="reservation-detail-page__tip-card">
          <view class="reservation-detail-page__tip-title">进入说明</view>
          <view class="reservation-detail-page__tip-text">请携带校园身份凭证，访问密钥将在预约开始前 15 分钟生效。</view>
        </view>
        <view class="reservation-detail-page__tip-card">
          <view class="reservation-detail-page__tip-title">安全规程</view>
          <view class="reservation-detail-page__tip-text">需佩戴实验护目镜，遵循实验楼安全指引后进入指定工位。</view>
        </view>
        <view class="reservation-detail-page__tip-card">
          <view class="reservation-detail-page__tip-title">实验室助手</view>
          <view class="reservation-detail-page__tip-text">值班实验员会在预约时段内提供设备校准与异常协助。</view>
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

function formatDateText(input) {
  if (!input) return '--'
  const date = new Date(`${input}T00:00`)
  if (Number.isNaN(date.getTime())) return input
  const y = date.getFullYear()
  const m = date.getMonth() + 1
  const d = date.getDate()
  const week = ['星期日', '星期一', '星期二', '星期三', '星期四', '星期五', '星期六']
  return `${y}年${m}月${d}日，${week[date.getDay()]}`
}

function hoursBetween(start, end) {
  if (!start || !end) return '--'
  const [sh, sm] = start.split(':').map(Number)
  const [eh, em] = end.split(':').map(Number)
  const mins = (eh * 60 + em) - (sh * 60 + sm)
  if (mins <= 0) return '--'
  return `${(mins / 60).toFixed(1)} 小时`
}

export default {
  components: { SiteFooter, StudentTopNav, UserTopNav },
  data() {
    return {
      id: '',
      detail: {}
    }
  },
  computed: {
    canCancel() {
      return ['pending', 'approved'].includes(this.detail.status)
    },
    statusText() {
      const map = {
        pending: '进行中',
        approved: '已批准',
        rejected: '已拒绝',
        cancelled: '已取消'
      }
      return map[this.detail.status] || '待处理'
    },
    statusClass() {
      return this.detail.status || 'pending'
    },
    dateText() {
      return formatDateText(this.detail.reservation_date)
    },
    startText() {
      return (this.detail.start_time || '--').slice(0, 5)
    },
    endText() {
      return (this.detail.end_time || '--').slice(0, 5)
    },
    durationText() {
      return hoursBetween(this.detail.start_time, this.detail.end_time)
    },
    envConfig() {
      return (this.detail.equipment && this.detail.equipment[0] && this.detail.equipment[0].equipment_name) || '标准配置'
    },
    envLevel() {
      const text = `${this.detail.lab_name || ''} ${this.detail.purpose || ''}`.toLowerCase()
      if (text.includes('病原') || text.includes('基因')) return 'BSL-2'
      return 'BSL-1'
    },
    envSpace() {
      return this.detail.participant_count > 1 ? '共享实验位' : '独立隔间'
    },
    timelineNodes() {
      const approvals = this.detail.approvals || []
      const createdNode = {
        state: 'done',
        title: '申请已提交',
        timeText: this.detail.created_at ? this.detail.created_at.replace('T', ' ').slice(0, 16) : '已提交',
        desc: '系统已接收预约申请并完成基础规则校验。'
      }

      const approvalNodes = approvals.map((item) => ({
        state: item.approval_status === 'approved' ? 'done' : item.approval_status === 'rejected' ? 'warn' : 'active',
        title: item.approval_status === 'approved' ? '审批通过' : item.approval_status === 'rejected' ? '审批驳回' : '等待审批',
        timeText: item.approval_time ? item.approval_time.replace('T', ' ').slice(0, 16) : '等待处理',
        desc: item.remark || '管理员正在处理当前预约申请。',
        reviewer: item.reviewer_name ? `审批人：${item.reviewer_name}` : ''
      }))

      if (!approvalNodes.length) {
        approvalNodes.push({
          state: this.detail.status === 'pending' ? 'active' : 'done',
          title: this.detail.status === 'pending' ? '待最终确认' : '审批结果已同步',
          timeText: '处理中',
          desc: '等待管理员完成最终库存与冲突校验。'
        })
      }

      return [createdNode].concat(approvalNodes)
    }
  },
  onLoad(options) {
    this.id = options.id || ''
  },
  async onShow() {
    if (!requireLogin()) return
    // #ifdef H5
    uni.hideTabBar()
    // #endif
    await this.loadData()
  },
  methods: {
    async loadData() {
      try {
        this.detail = await api.reservationDetail(this.id)
      } catch (error) {
        this.detail = {}
      }
    },
    async cancelCurrent() {
      if (!this.canCancel || !this.detail.id) return
      await api.cancelReservation(this.detail.id)
      uni.showToast({ title: '已取消预约', icon: 'success' })
      await this.loadData()
    },
    downloadCert() {
      uni.showToast({ title: '证书生成功能开发中', icon: 'none' })
    },
    goBack() {
      openPage(routes.myReservations, { replace: true })
    }
  }
}
</script>

<style lang="scss">
.reservation-detail-page {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background:
    radial-gradient(circle at 12% 14%, rgba(109, 179, 230, 0.25), transparent 26%),
    radial-gradient(circle at 88% 18%, rgba(173, 208, 240, 0.26), transparent 24%),
    linear-gradient(180deg, #edf5fc 0%, #dceaf7 100%);
}

.reservation-detail-page__shell {
  flex: 1;
  padding: 30rpx 32rpx 40rpx;
}

.reservation-detail-page__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20rpx;
}

.reservation-detail-page__id {
  color: #3f5878;
  font-size: 22rpx;
  font-weight: 700;
}

.reservation-detail-page__title {
  margin-top: 8rpx;
  color: #061f44;
  font-size: 76rpx;
  line-height: 1.04;
  font-weight: 800;
  letter-spacing: -1.4rpx;
}

.reservation-detail-page__sub {
  margin-top: 10rpx;
  color: #5d6f87;
  font-size: 27rpx;
}

.reservation-detail-page__actions {
  display: flex;
  gap: 12rpx;
}

.reservation-detail-page__btn {
  min-width: 150rpx;
  height: 66rpx;
  border-radius: 14rpx;
  padding: 0 20rpx;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 23rpx;
  font-weight: 800;
}

.reservation-detail-page__btn.light {
  background: #ffffff;
  color: #20354f;
  border: 1rpx solid rgba(120, 137, 160, 0.28);
}

.reservation-detail-page__btn.danger {
  background: #d93434;
  color: #fff;
}

.reservation-detail-page__btn.danger.disabled {
  background: #e6b4b4;
}

.reservation-detail-page__layout {
  margin-top: 20rpx;
  display: grid;
  grid-template-columns: minmax(0, 1.9fr) minmax(300rpx, 0.9fr);
  gap: 20rpx;
}

.reservation-detail-page__timeline-card {
  border-radius: 24rpx;
  background: rgba(255, 255, 255, 0.78);
  border: 1rpx solid rgba(197, 198, 207, 0.28);
  padding: 18rpx;
}

.reservation-detail-page__card-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.reservation-detail-page__card-title {
  color: #082248;
  font-size: 40rpx;
  font-weight: 800;
}

.reservation-detail-page__status-pill {
  min-height: 38rpx;
  border-radius: 999rpx;
  padding: 0 12rpx;
  display: inline-flex;
  align-items: center;
  font-size: 20rpx;
  font-weight: 800;
}

.reservation-detail-page__status-pill.pending {
  background: #d7eef9;
  color: #0a7c9b;
}

.reservation-detail-page__status-pill.approved {
  background: #d9f7e7;
  color: #178f5d;
}

.reservation-detail-page__status-pill.rejected,
.reservation-detail-page__status-pill.cancelled {
  background: #fde0e0;
  color: #bf2a2a;
}

.reservation-detail-page__timeline {
  margin-top: 14rpx;
  display: grid;
  gap: 10rpx;
}

.reservation-detail-page__node {
  display: grid;
  grid-template-columns: 28rpx 1fr;
  gap: 12rpx;
}

.reservation-detail-page__node-mark {
  width: 24rpx;
  height: 24rpx;
  border-radius: 999rpx;
  margin-top: 4rpx;
  background: #c8d2df;
  border: 3rpx solid #e8eef6;
}

.reservation-detail-page__node.done .reservation-detail-page__node-mark {
  background: #0a7fa4;
}

.reservation-detail-page__node.active .reservation-detail-page__node-mark {
  background: #2ab0df;
}

.reservation-detail-page__node.warn .reservation-detail-page__node-mark {
  background: #d93434;
}

.reservation-detail-page__node-body {
  padding-bottom: 12rpx;
  border-left: 1rpx solid #d6deea;
  padding-left: 12rpx;
}

.reservation-detail-page__node:last-child .reservation-detail-page__node-body {
  border-left-color: transparent;
}

.reservation-detail-page__node-title {
  color: #0c2a50;
  font-size: 30rpx;
  font-weight: 800;
}

.reservation-detail-page__node-time {
  margin-top: 4rpx;
  color: #5f7189;
  font-size: 22rpx;
}

.reservation-detail-page__node-desc {
  margin-top: 6rpx;
  color: #6c7f98;
  font-size: 23rpx;
  line-height: 1.55;
}

.reservation-detail-page__node-reviewer {
  margin-top: 8rpx;
  border-radius: 12rpx;
  background: #eef3fa;
  padding: 10rpx 12rpx;
  color: #2f4867;
  font-size: 22rpx;
  font-weight: 700;
}

.reservation-detail-page__side {
  display: grid;
  gap: 14rpx;
  align-content: start;
}

.reservation-detail-page__side-card {
  border-radius: 22rpx;
  background: rgba(255, 255, 255, 0.78);
  border: 1rpx solid rgba(197, 198, 207, 0.28);
  padding: 16rpx;
}

.reservation-detail-page__side-card.schedule {
  border-left: 6rpx solid #1098c8;
}

.reservation-detail-page__side-title {
  color: #082248;
  font-size: 34rpx;
  font-weight: 800;
}

.reservation-detail-page__side-title.light {
  color: #ecf4ff;
}

.reservation-detail-page__line {
  margin-top: 10rpx;
  display: flex;
  justify-content: space-between;
  align-items: center;
  color: #52647e;
  font-size: 22rpx;
}

.reservation-detail-page__line.two {
  gap: 18rpx;
  justify-content: flex-start;
}

.reservation-detail-page__line .k {
  color: #66788f;
  font-size: 20rpx;
}

.reservation-detail-page__line .v {
  margin-top: 2rpx;
  color: #0b294f;
  font-size: 34rpx;
  font-weight: 800;
}

.reservation-detail-page__purpose-card {
  border-radius: 22rpx;
  background: linear-gradient(160deg, #081f46, #061634);
  padding: 16rpx;
  color: #d6e6fb;
}

.reservation-detail-page__purpose-text {
  margin-top: 10rpx;
  font-size: 23rpx;
  line-height: 1.6;
}

.reservation-detail-page__purpose-id {
  margin-top: 12rpx;
  color: #34c6ff;
  font-size: 21rpx;
  font-weight: 700;
}

.reservation-detail-page__tips {
  margin-top: 16rpx;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14rpx;
}

.reservation-detail-page__tip-card {
  border-radius: 18rpx;
  background: rgba(255, 255, 255, 0.74);
  border: 1rpx solid rgba(197, 198, 207, 0.28);
  padding: 14rpx;
}

.reservation-detail-page__tip-title {
  color: #0b294f;
  font-size: 29rpx;
  font-weight: 800;
}

.reservation-detail-page__tip-text {
  margin-top: 8rpx;
  color: #5d718a;
  font-size: 22rpx;
  line-height: 1.6;
}

/* #ifndef H5 */
.reservation-detail-page__shell {
  padding-left: 24rpx;
  padding-right: 24rpx;
}

.reservation-detail-page__head {
  flex-direction: column;
  align-items: flex-start;
}

.reservation-detail-page__layout,
.reservation-detail-page__tips {
  grid-template-columns: 1fr;
}
/* #endif */

/* #ifdef H5 */
@media screen and (min-width: 1500px) {
  .reservation-detail-page__shell {
    padding-left: 56rpx;
    padding-right: 56rpx;
  }
}

@media screen and (max-width: 1140px) {
  .reservation-detail-page__layout,
  .reservation-detail-page__tips {
    grid-template-columns: 1fr;
  }
}
/* #endif */
</style>
