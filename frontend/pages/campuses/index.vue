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
            探索三个校区的实验室资源与开放状态，选择目标校区后可快速进入预约流程。
          </view>
        </view>

        <view class="campus-page__grid">
          <view
            v-for="(item, index) in campuses"
            :key="item.id || item.name"
            class="campus-page__card"
            :class="`campus-page__card--${index + 1}`"
          >
            <view class="campus-page__cover" :style="{ background: item.cover }">
              <image v-if="item.cover_url" class="campus-page__cover-img" :src="item.cover_url" mode="aspectFill" />
              <view class="campus-page__cover-mask"></view>
            </view>

            <view class="campus-page__card-body">
              <view class="campus-page__card-main">
                <view class="campus-page__card-left">
                  <view class="campus-page__pill">{{ item.badge }}</view>
                  <view class="campus-page__card-title">{{ item.name }}</view>
                  <view class="campus-page__card-desc">{{ item.desc }}</view>
                </view>
                <view class="campus-page__card-right">
                  <view class="campus-page__count">{{ item.labCount }}</view>
                  <view class="campus-page__count-label">可用实验室</view>
                </view>
              </view>
              <view class="campus-page__card-actions">
                <view class="campus-page__enter-btn" @tap="enterCampus(item)">进入此校区</view>

              </view>
            </view>
          </view>
        </view>
      </view>
    </view>

    <!-- <site-footer /> -->
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

const COVER_THEMES = [
  'linear-gradient(135deg, #0f2b52 0%, #2e5f9e 52%, #7ec2ff 100%)',
  'linear-gradient(135deg, #1a3150 0%, #2c6f9a 50%, #6ec3d8 100%)',
  'linear-gradient(135deg, #1e2a4f 0%, #4f5ea7 50%, #9ab0ff 100%)'
]

function getCampusBadge(name) {
  const text = String(name || '')
  const match = text.match(/（(.+?)）/)
  if (match && match[1]) return `${match[1]}校区`
  return '校区'
}

export default {
  components: { SiteFooter, StudentTopNav, UserTopNav },
  data() {
    return {
      routes,
      campusList: [],
      labMap: {}
    }
  },
  computed: {
    campuses() {
      return this.campusList.slice(0, 3).map((item, index) => {
        const matchedLabs = this.labMap[String(item.id)] || 0
        return {
          id: item.id,
          name: item.campus_name,
          badge: getCampusBadge(item.campus_name),
          desc: item.description || item.address || '暂无校区简介',
          cover: COVER_THEMES[index % COVER_THEMES.length],
          cover_url: item.cover_url || '',
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
    enterCampus(item) {
      if (item.id) {
        uni.setStorageSync('campus_entry_campus_id', String(item.id))
      } else {
        uni.removeStorageSync('campus_entry_campus_id')
      }
      if (item.id) {
        openPage(routes.labs)
      } else {
        openPage(routes.labs)
      }
    },
    async loadData() {
      try {
        const [campusesRes, labsRes] = await Promise.all([api.campuses(), api.labs({ page: 1, page_size: 500 })])
        const list = Array.isArray(campusesRes) ? campusesRes : []
        this.campusList = list
        const labs = labsRes?.list || labsRes?.data || (Array.isArray(labsRes) ? labsRes : [])

        const labCountMap = {}
        labs.forEach((lab) => {
          const key = String(lab.campus_id)
          labCountMap[key] = (labCountMap[key] || 0) + 1
        })
        this.labMap = labCountMap
      } catch (_error) {
        this.campusList = []
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
  grid-template-columns: 1.3fr 1fr;
  grid-template-rows: 520rpx 520rpx;
  gap: 24rpx;
}

.campus-page__card {
  overflow: hidden;
  position: relative;
  min-height: 420rpx;
  border-radius: 36rpx;
  background: rgba(255, 255, 255, 0.06);
  border: 1rpx solid rgba(255, 255, 255, 0.35);
  box-shadow: 0 24rpx 64rpx rgba(8, 27, 58, 0.1);
  transition: all 0.28s ease;
}

.campus-page__card:hover {
  transform: translateY(-6rpx);
  box-shadow: 0 30rpx 72rpx rgba(8, 27, 58, 0.15);
}

.campus-page__card--1 {
  grid-column: 1 / span 1;
  grid-row: 1 / span 2;
  min-height: 864rpx;
}

.campus-page__card--2 {
  grid-column: 2 / span 1;
  grid-row: 1 / span 1;
  min-height: 420rpx;
}

.campus-page__card--3 {
  grid-column: 2 / span 1;
  grid-row: 2 / span 1;
  min-height: 420rpx;
}

.campus-page__cover {
  position: absolute;
  inset: 0;
  height: 100%;
  overflow: hidden;
}

.campus-page__cover-img {
  width: 100%;
  height: 100%;
  display: block;
}

.campus-page__cover-mask {
  position: absolute;
  inset: 0;
  background: linear-gradient(180deg, rgba(8, 20, 40, 0.1) 0%, rgba(8, 20, 40, 0.55) 100%);
}

.campus-page__card-body {
  position: absolute;
  left: 40rpx;
  right: 40rpx;
  bottom: 30rpx;
  padding: 26rpx;
  border-radius: 20rpx;
  /* 使用更透明的背景 + 白色/浅色底色 */
  background: rgba(255, 255, 255, 0.7);
  border: 1rpx solid rgba(255, 255, 255, 0.4);
}

.campus-page__card-main {
  display: flex;
  align-items: stretch;
  justify-content: space-between;
  gap: 24rpx;
}

.campus-page__card-left {
  flex: 1;
  min-width: 0;
}

.campus-page__pill {
  width: fit-content;
  min-height: 42rpx;
  padding: 0 18rpx;
  border-radius: 999rpx;
  background: rgba(44, 125, 160, 0.16);
  color: #0f4b6f;
  font-size: 20rpx;
  font-weight: 800;
  display: inline-flex;
  align-items: center;
}

.campus-page__card-title {
  margin-top: 14rpx;
  font-size: 34rpx;
  line-height: 1.22;
  font-weight: 800;
  color: #031635;
}

.campus-page__card-right {
  width: 132rpx;
  flex-shrink: 0;
  text-align: right;
}

.campus-page__count {
  color: #031635;
  font-size: 64rpx;
  font-weight: 800;
  line-height: 1;
}

.campus-page__count-label {
  margin-top: 6rpx;
  color: #55647a;
  font-size: 21rpx;
  font-weight: 700;
}

.campus-page__card-desc {
  margin-top: 12rpx;
  min-height: 92rpx;
  color: #66758a;
  font-size: 23rpx;
  line-height: 1.55;
}

.campus-page__card-actions {
  margin-top: 14rpx;
  display: flex;
  gap: 14rpx;
  align-items: center;
}

.campus-page__enter-btn {
  flex: 1;
  height: 74rpx;
  border-radius: 20rpx;
  background: #041c42;
  color: #eaf3ff;
  font-size: 26rpx;
  font-weight: 800;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
}


.campus-page__enter-btn:hover {
  transform: translateY(-1rpx);
  opacity: 0.95;
}


/* #ifndef H5 */
.campus-page__body {
  padding-top: 24rpx;
}

.campus-page__shell {
  padding-left: 24rpx;
  padding-right: 24rpx;
}

.campus-page__grid {
  grid-template-columns: 1fr;
}

.campus-page__card,
.campus-page__card--1,
.campus-page__card--2,
.campus-page__card--3 {
  grid-column: auto;
}

.campus-page__card--3 {
  display: block;
}

.campus-page__card--3 .campus-page__cover,
.campus-page__card--1 .campus-page__cover,
.campus-page__card--2 .campus-page__cover {
  height: 100%;
}

.campus-page__card-body,
.campus-page__card--3 .campus-page__card-body {
  left: 14rpx;
  right: 14rpx;
  bottom: 14rpx;
}
/* #endif */

/* #ifdef H5 */
@media screen and (min-width: 1500px) {
  .campus-page__shell {
    padding-left: 56rpx;
    padding-right: 56rpx;
  }
}

@media screen and (max-width: 1180px) {
  .campus-page__grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    grid-template-rows: auto;
  }

  .campus-page__card--1 {
    grid-column: 1 / span 2;
    grid-row: auto;
    min-height: 560rpx;
  }

  .campus-page__card--2,
  .campus-page__card--3 {
    grid-column: auto;
    grid-row: auto;
    min-height: 420rpx;
  }

  .campus-page__card-body,
  .campus-page__card--3 .campus-page__card-body {
    left: 14rpx;
    right: 14rpx;
    bottom: 14rpx;
  }
}

@media screen and (max-width: 860px) {
  .campus-page__grid {
    grid-template-columns: 1fr;
  }

  .campus-page__card--1,
  .campus-page__card--2,
  .campus-page__card--3 {
    grid-column: auto;
  }
}
/* #endif */
</style>
