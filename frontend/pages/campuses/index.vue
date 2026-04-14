<template>
  <view class="campus-page">
    <!-- #ifdef H5 -->
    <student-top-nav active="campuses" />
    <!-- #endif -->

    <!-- #ifndef H5 -->
    <user-top-nav active="campuses" />
    <!-- #endif -->

    <view class="campus-page__body">
      <view class="campus-page__shell">
        <view class="campus-page__hero">
          <view class="campus-page__hero-title">我们的校区</view>
          <view class="campus-page__hero-sub">
            请选择当前所在校区，快速查看对应实验室资源并进入预约流程。
          </view>
        </view>

        <view class="campus-page__grid">
          <view v-for="item in campuses" :key="item.name" class="campus-page__card">
            <view class="campus-page__cover" :style="{ background: item.cover }">
              <view class="campus-page__cover-badge">{{ item.badge }}</view>
            </view>

            <view class="campus-page__card-body">
              <view class="campus-page__card-title">{{ item.name }}</view>
              <view class="campus-page__card-desc">{{ item.desc }}</view>

              <view class="campus-page__card-meta">
                <view class="campus-page__meta-item">
                  <text class="campus-page__meta-label">实验室数量</text>
                  <text class="campus-page__meta-value">{{ item.labCount }} 个</text>
                </view>
                <view class="campus-page__meta-item">
                  <text class="campus-page__meta-label">状态</text>
                  <text class="campus-page__meta-value">{{ item.statusText }}</text>
                </view>
              </view>

              <view class="campus-page__enter-btn" @click="enterCampus(item)">进入此校区</view>
            </view>
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

const CAMPUS_PRESETS = [
  {
    name: '中央民族大学（主校区）',
    badge: '主校区',
    desc: '覆盖基础教学与综合科研的核心实验资源，支持全天候预约与审批流转。',
    cover: 'linear-gradient(135deg, #12345b 0%, #3f6ea1 45%, #88c4ff 100%)',
    statusText: '运行中'
  },
  {
    name: '中央民族大学（丰台校区）',
    badge: '丰台校区',
    desc: '聚焦工程实践与交叉学科实验，配备标准化仪器设备与开放实验工位。',
    cover: 'linear-gradient(135deg, #0f2d2f 0%, #2f7a68 52%, #99d7c7 100%)',
    statusText: '运行中'
  },
  {
    name: '中央民族大学（海南校区）',
    badge: '海南校区',
    desc: '面向海洋与热带方向研究，提供区域特色实验室与项目协同能力。',
    cover: 'linear-gradient(135deg, #2f254d 0%, #5e4ea0 52%, #bfb3ff 100%)',
    statusText: '运行中'
  }
]

export default {
  components: { SiteFooter, StudentTopNav, UserTopNav },
  data() {
    return {
      routes,
      campusMap: {},
      labMap: {}
    }
  },
  computed: {
    campuses() {
      return CAMPUS_PRESETS.map((item) => {
        const matched = this.findCampus(item.name)
        const matchedLabs = matched ? (this.labMap[String(matched.id)] || 0) : 0
        return {
          ...item,
          id: matched ? matched.id : '',
          labCount: matchedLabs
        }
      })
    }
  },
  async onShow() {
    if (!requireLogin()) return
    // #ifdef H5
    uni.hideTabBar()
    // #endif
    await this.loadData()
  },
  methods: {
    go(path) {
      openPage(path)
    },
    findCampus(name) {
      return Object.values(this.campusMap).find((item) => item.campus_name === name)
    },
    enterCampus(item) {
      if (item.id) {
        openPage(routes.labs, { query: { campusId: item.id } })
      } else {
        openPage(routes.labs)
      }
    },
    async loadData() {
      try {
        const [campusesRes, labsRes] = await Promise.all([api.campuses(), api.labs({ page: 1, page_size: 500 })])
        const list = Array.isArray(campusesRes) ? campusesRes : []
        const labs = labsRes?.list || labsRes?.data || (Array.isArray(labsRes) ? labsRes : [])

        const campusMap = {}
        list.forEach((item) => {
          campusMap[String(item.id)] = item
        })
        this.campusMap = campusMap

        const labCountMap = {}
        labs.forEach((lab) => {
          const key = String(lab.campus_id)
          labCountMap[key] = (labCountMap[key] || 0) + 1
        })
        this.labMap = labCountMap
      } catch (error) {
        this.campusMap = {}
        this.labMap = {}
      }
    }
  }
}
</script>

<style lang="scss">
.campus-page {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background:
    radial-gradient(circle at top right, rgba(65, 190, 253, 0.14), transparent 26%),
    linear-gradient(180deg, #f7f9fc 0%, #eef2f7 100%);
}

.campus-page__nav {
  position: sticky;
  top: 0;
  z-index: 50;
  padding: 0;
  background: rgba(247, 249, 252, 0.72);
  backdrop-filter: blur(18px);
  border-bottom: 1rpx solid rgba(197, 198, 207, 0.22);
  box-shadow: 0 12rpx 30rpx rgba(8, 27, 58, 0.05);
}

.campus-page__nav-inner {
  width: 100%;
  min-height: 108rpx;
  margin: 0;
  padding: 0 40rpx;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 32rpx;
  box-sizing: border-box;
}

.campus-page__nav-main {
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 56rpx;
  flex: 1;
}

.campus-page__brand {
  display: flex;
  align-items: center;
  gap: 18rpx;
}

.campus-page__brand-mark {
  width: 78rpx;
  height: 78rpx;
  border-radius: 24rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #031635, #1a2b4b);
  color: #41befd;
  font-size: 30rpx;
  font-weight: 800;
}

.campus-page__brand-text {
  font-size: 30rpx;
  font-weight: 800;
  letter-spacing: -0.5rpx;
  color: #1a2b4b;
}

.campus-page__nav-links {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: 44rpx;
  min-width: 0;
  flex-wrap: nowrap;
}

.campus-page__nav-link {
  padding: 8rpx 8rpx;
  border-bottom: 4rpx solid transparent;
  color: #6f7b8c;
  font-size: 24rpx;
  font-weight: 600;
  letter-spacing: 1rpx;
}

.campus-page__nav-link.active {
  color: #1a2b4b;
  border-color: #41befd;
}

.campus-page__nav-actions {
  display: flex;
  align-items: center;
  justify-self: end;
}

.campus-page__profile {
  display: flex;
  align-items: center;
  gap: 14rpx;
}

.campus-page__avatar {
  width: 66rpx;
  height: 66rpx;
  border-radius: 999rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #1a2b4b, #7ecfff);
  color: #ffffff;
  font-size: 26rpx;
  font-weight: 700;
}

.campus-page__profile-text {
  font-size: 22rpx;
  font-weight: 600;
  color: #031635;
}

.campus-page__body {
  flex: 1;
  padding: 36rpx 0 80rpx;
}

.campus-page__shell {
  width: 100%;
  padding: 0 32rpx;
  box-sizing: border-box;
}

.campus-page__hero-title {
  font-size: 74rpx;
  line-height: 1.02;
  font-weight: 800;
  letter-spacing: -1.4rpx;
  color: #031635;
}

.campus-page__hero-sub {
  margin-top: 14rpx;
  max-width: 980rpx;
  color: #55647a;
  font-size: 30rpx;
  line-height: 1.55;
}

.campus-page__grid {
  margin-top: 34rpx;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 24rpx;
}

.campus-page__card {
  overflow: hidden;
  border-radius: 28rpx;
  background: #ffffff;
  box-shadow: 0 18rpx 36rpx rgba(8, 27, 58, 0.06);
}

.campus-page__cover {
  height: 220rpx;
  position: relative;
}

.campus-page__cover-badge {
  position: absolute;
  left: 20rpx;
  bottom: 20rpx;
  padding: 8rpx 16rpx;
  border-radius: 999rpx;
  background: rgba(255, 255, 255, 0.2);
  border: 1rpx solid rgba(255, 255, 255, 0.38);
  color: #f8fcff;
  font-size: 20rpx;
  font-weight: 700;
}

.campus-page__card-body {
  padding: 24rpx;
}

.campus-page__card-title {
  font-size: 34rpx;
  line-height: 1.22;
  font-weight: 800;
  color: #031635;
}

.campus-page__card-desc {
  margin-top: 10rpx;
  min-height: 90rpx;
  color: #66758a;
  font-size: 23rpx;
  line-height: 1.55;
}

.campus-page__card-meta {
  margin-top: 14rpx;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12rpx;
}

.campus-page__meta-item {
  padding: 16rpx 14rpx;
  border-radius: 16rpx;
  background: #f1f5fb;
}

.campus-page__meta-label {
  display: block;
  color: #7a889e;
  font-size: 20rpx;
}

.campus-page__meta-value {
  display: block;
  margin-top: 4rpx;
  color: #0f2a4a;
  font-size: 24rpx;
  font-weight: 700;
}

.campus-page__enter-btn {
  margin-top: 16rpx;
  height: 74rpx;
  border-radius: 16rpx;
  background: #041c42;
  color: #eaf3ff;
  font-size: 24rpx;
  font-weight: 800;
  display: flex;
  align-items: center;
  justify-content: center;
}

.campus-page__footer {
  padding: 48rpx 32rpx 12rpx;
}

.campus-page__footer-inner {
  width: 100%;
  margin: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 28rpx;
  padding: 32rpx;
  border-radius: 28rpx;
  background: #ffffff;
  border: 1rpx solid rgba(228, 235, 245, 0.92);
  box-shadow: 0 12rpx 36rpx rgba(47, 128, 237, 0.06);
}

.campus-page__footer-title {
  color: #1a2b4b;
  font-size: 30rpx;
  font-weight: 800;
}

.campus-page__footer-sub {
  margin-top: 10rpx;
  color: #7a8796;
  font-size: 22rpx;
}

.campus-page__footer-links {
  display: flex;
  align-items: center;
  gap: 18rpx;
  flex-wrap: wrap;
}

.campus-page__footer-link {
  color: #7a8796;
  font-size: 23rpx;
}

/* #ifndef H5 */
.campus-page__body {
  padding-top: 24rpx;
}

.campus-page__shell,
.campus-page__footer {
  padding-left: 24rpx;
  padding-right: 24rpx;
}

.campus-page__grid {
  grid-template-columns: 1fr;
}

.campus-page__footer-inner {
  flex-direction: column;
  align-items: flex-start;
}
/* #endif */

/* #ifdef H5 */
@media screen and (min-width: 1500px) {
  .campus-page__nav-inner {
    padding-left: 56rpx;
    padding-right: 56rpx;
  }

  .campus-page__shell,
  .campus-page__footer {
    padding-left: 56rpx;
    padding-right: 56rpx;
  }
}

@media screen and (max-width: 1180px) {
  .campus-page__grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .campus-page__footer-inner {
    flex-direction: column;
    align-items: flex-start;
  }
}

@media screen and (max-width: 860px) {
  .campus-page__nav-links,
  .campus-page__profile-text {
    display: none;
  }

  .campus-page__nav-main {
    gap: 20rpx;
  }

  .campus-page__grid {
    grid-template-columns: 1fr;
  }
}
/* #endif */
</style>
