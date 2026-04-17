<template>
  <view class="campus-page">
    <!-- #ifdef H5 -->
    <student-top-nav active="campuses" />
    <!-- #endif -->

    <!-- #ifndef H5 -->
    <user-top-nav active="campuses" />
    <!-- #endif -->

    <view class="campus-page__shell">
      <view class="campus-page__hero">
        <view class="campus-page__hero-glow campus-page__hero-glow--left"></view>
        <view class="campus-page__hero-glow campus-page__hero-glow--right"></view>
        <view class="campus-page__hero-title">探索我们的校区</view>
        <view class="campus-page__hero-sub">
          浏览各校区实验室资源与开放状态，选择目标校区快速进入预约流程
        </view>
      </view>

      <view class="campus-page__grid">
        <view
          v-for="(item, index) in campuses"
          :key="item.id || item.name"
          class="campus-page__card"
          :class="'campus-page__card--' + (index + 1)"
        >
          <view class="campus-page__cover" :style="{ background: item.cover }">
            <image v-if="item.cover_url" class="campus-page__cover-img" :src="item.cover_url" mode="widthFix" />
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
    radial-gradient(circle at 12% 14%, rgba(109, 179, 230, 0.25), transparent 26%),
    radial-gradient(circle at 88% 18%, rgba(173, 208, 240, 0.26), transparent 24%),
    linear-gradient(180deg, #edf5fc 0%, #dceaf7 100%);
}


.campus-page__shell {
  width: 100%;
  box-sizing: border-box;
}

.campus-page__hero {
  position: relative;
  overflow: hidden;
  text-align: center;
  border-radius: 24rpx;
  padding: 100rpx 24rpx 32rpx;
  background: linear-gradient(180deg, rgba(229, 240, 250, 0.85), rgba(226, 238, 250, 0.58));
}

.campus-page__hero-glow {
  position: absolute;
  width: 140rpx;
  height: 140rpx;
  border-radius: 999rpx;
  filter: blur(18rpx);
  pointer-events: none;
}

.campus-page__hero-glow--left {
  left: 180rpx;
  top: 42rpx;
  background: rgba(150, 206, 244, 0.56);
}

.campus-page__hero-glow--right {
  right: 180rpx;
  top: 40rpx;
  background: rgba(184, 199, 236, 0.5);
}

.campus-page__hero-title {
  position: relative;
  z-index: 1;
  font-size: 72rpx;
  line-height: 1.02;
  font-weight: 800;
  letter-spacing: -1rpx;
  color: #020b1a;
}

.campus-page__hero-sub {
  position: relative;
  z-index: 1;
  margin-top: 16rpx;
  max-width: 1140rpx;
  margin-left: auto;
  margin-right: auto;
  color: #4b4949;
  font-size: 35rpx;
  line-height: 1.5;
  font-weight: bold; /* 加粗 */
}

.campus-page__grid {
  margin-top: 70rpx;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 28rpx;
}

.campus-page__card {
  overflow: hidden;
  position: relative;
  min-height: 1100rpx;
  border-radius: 24rpx;
  background: rgba(255, 255, 255, 0.06);
  border: 1rpx solid rgba(255, 255, 255, 0.5);
  box-shadow: 0 16rpx 42rpx rgba(22, 49, 86, 0.16);
  transition: all 0.28s ease;
}

.campus-page__card:hover {
  transform: translateY(-4rpx);
  box-shadow: 0 22rpx 56rpx rgba(22, 49, 86, 0.18);
}

.campus-page__card--1 {
  min-height: 1100rpx;
}

.campus-page__card--2 {
  min-height: 1100rpx;
}

.campus-page__card--3 {
  min-height: 1100rpx;
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
  background: linear-gradient(180deg, rgba(6, 18, 38, 0.06) 0%, rgba(9, 25, 49, 0.42) 78%, rgba(9, 25, 49, 0.48) 100%);
}

.campus-page__card-body {
  position: absolute;
  left: 30rpx;
  right: 30rpx;
  bottom: 30rpx;
  padding: 30rpx 30rpx 24rpx;
  border-radius: 18rpx;
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.83), rgba(246, 248, 252, 0.7));
  border: 1rpx solid rgba(0, 0, 0, 0.58);
  backdrop-filter: blur(8rpx);
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
  min-height: 40rpx;
  padding: 0 14rpx;
  border-radius: 999rpx;
  background: rgba(94, 162, 205, 0.2);
  color: #2f6f95;
  font-size: 20rpx;
  font-weight: 800;
  display: inline-flex;
  align-items: center;
}

.campus-page__card-title {
  margin-top: 16rpx;
  font-size: 38rpx;
  line-height: 1.22;
  font-weight: 800;
  color: #000000;
}

.campus-page__card-right {
  width: 140rpx;
  border-left: 1rpx solid rgba(0, 0, 0, 0.2);
  padding-left: 24rpx;
  flex-shrink: 0;
  text-align: center;
  align-self: center;
}

.campus-page__count {
  color: #080d18;
  font-size: 68rpx;
  font-weight: 800;
  line-height: 1;
}

.campus-page__count-label {
  margin-top: 6rpx;
  color: #26384f;
  font-size: 21rpx;
  font-weight: 600;
}

.campus-page__card-desc {
  margin-top: 10rpx;
  min-height: 128rpx;
  color: #24344a;
  font-size: 23rpx;
  line-height: 1.52;
}

.campus-page__card-actions {
  margin-top: 12rpx;
  display: flex;
  gap: 14rpx;
  align-items: center;
}

.campus-page__enter-btn {
  width: 170rpx;
  height: 66rpx;
  border-radius: 16rpx;
  background: linear-gradient(180deg, #eaf4ff 0%, #d9e9fa 100%);
  border: 1rpx solid rgba(130, 176, 215, 0.7);
  color: #3f6d96;
  font-size: 26rpx;
  font-weight: 800;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
  box-shadow: 0 4rpx 12rpx rgba(66, 104, 145, 0.15);
}


.campus-page__enter-btn:hover {
  transform: translateY(-1rpx);
  opacity: 0.92;
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
    gap: 24rpx;
  }

  .campus-page__card-body,
  .campus-page__card--3 .campus-page__card-body {
    left: 14rpx;
    right: 14rpx;
    bottom: 14rpx;
  }
}

@media screen and (max-width: 860px) {
  .campus-page__hero {
    text-align: left;
    padding: 26rpx 22rpx 18rpx;
  }

  .campus-page__hero-title {
    font-size: 52rpx;
  }

  .campus-page__hero-sub {
    font-size: 26rpx;
  }

  .campus-page__card,
  .campus-page__card--1,
  .campus-page__card--2,
  .campus-page__card--3 {
    min-height: 620rpx;
  }

  .campus-page__card-title {
    font-size: 32rpx;
  }

  .campus-page__card-desc {
    font-size: 23rpx;
    min-height: 92rpx;
  }

  .campus-page__count-label {
    font-size: 21rpx;
  }

  .campus-page__pill {
    font-size: 20rpx;
  }

  .campus-page__enter-btn {
    width: 160rpx;
    font-size: 24rpx;
  }

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
