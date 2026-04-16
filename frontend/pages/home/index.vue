<template>
  <view class="student-home">
    <!-- #ifdef H5 -->
    <student-top-nav active="home" />
    <!-- #endif -->

    <!-- #ifndef H5 -->
    <user-top-nav active="home" />
    <!-- #endif -->

    <view class="student-home__body">
      <view class="student-home__shell">
        <view class="student-home__hero">
          <view class="student-home__hero-title">
            欢迎回来，<text class="student-home__hero-title-accent">{{ displayName }}</text>
          </view>
          <view class="student-home__hero-sub">
            今天想预约哪间实验室？我们已为您准备好最新的科研资源。
          </view>
          <view class="student-home__hero-btn" @click="go(routes.labs)">
            <text>立即开始预约</text>
            <text class="student-home__hero-arrow">→</text>
          </view>
        </view>

        <view class="student-home__entry-grid">
          <view
            v-for="entry in homeEntries"
            :key="entry.path"
            class="student-home__entry-card"
            @click="go(entry.path)"
          >
            <view class="student-home__entry-icon" :class="entry.iconClass">{{ entry.icon }}</view>
            <view class="student-home__entry-title">{{ entry.title }}</view>
            <view class="student-home__entry-desc">{{ entry.desc }}</view>
          </view>
        </view>

        <view class="student-home__section-head">
          <view class="student-home__section-title">热门实验室推荐</view>
          <view class="student-home__section-controls">
            <view class="student-home__section-dot">‹</view>
            <view class="student-home__section-dot">›</view>
          </view>
        </view>

        <view class="student-home__list">
          <view
            v-for="lab in featuredLabs"
            :key="lab.id"
            class="student-home__list-item"
          >
            <view class="student-home__list-cover" :style="{ background: lab.cover }">
              <image
                v-if="lab.coverImage"
                class="student-home__list-cover-img"
                :src="lab.coverImage"
                mode="aspectFill"
              />
              <view class="student-home__list-cover-mask"></view>
            </view>

            <view class="student-home__list-main">
              <view class="student-home__list-name">{{ lab.lab_name }}</view>
              <view class="student-home__list-tags">
                <text class="student-home__list-tag">{{ lab.typeText }}</text>
                <text class="student-home__list-tag">容量 {{ lab.capacity || 0 }}</text>
              </view>
              <view class="student-home__list-meta">
                {{ lab.campus_name || '校区待补充' }} · {{ lab.location || '位置待补充' }}
              </view>
            </view>

            <view class="student-home__list-side">
              <view class="student-home__list-status" :class="lab.statusClass">{{ lab.statusText }}</view>
              <view
                class="student-home__list-action"
                :class="{ disabled: lab.status !== 'active' }"
                @click="goReserveFromHome(lab)"
              >
                {{ lab.status === 'active' ? '立即预约' : '暂不可约' }}
              </view>
              <view class="student-home__list-detail" @click="goLabDetail(lab.id)">查看详情</view>
            </view>
          </view>
        </view>
      </view>
    </view>
  </view>
</template>

<script>
import StudentTopNav from '../../components/student-top-nav.vue'
import UserTopNav from '../../components/user-top-nav.vue'
import { api } from '../../api/index'
import { requireLogin } from '../../common/guard'
import { openPage } from '../../common/router'
import { getProfile } from '../../common/session'
import { routes } from '../../config/navigation'

const LAB_COVERS = [
  'linear-gradient(135deg, #0c284e 0%, #1b4f82 55%, #48b7f4 100%)',
  'linear-gradient(135deg, #1a2744 0%, #3e6f8f 52%, #d3ecff 100%)',
  'linear-gradient(135deg, #214235 0%, #3f7f68 48%, #b8e9d2 100%)',
  'linear-gradient(135deg, #32231f 0%, #725043 50%, #f3d2b1 100%)'
]

export default {
  components: { StudentTopNav, UserTopNav },
  data() {
    return {
      routes,
      profile: {},
      featuredLabs: []
    }
  },
  computed: {
    displayName() {
      return this.profile.real_name || this.profile.username || '同学'
    },
    homeEntries() {
      return [
        {
          title: '校区资源',
          desc: '探索不同校区的尖端设施与空间布局',
          path: routes.campuses,
          icon: '◧',
          iconClass: 'blue'
        },
        {
          title: '实验室列表',
          desc: '精准查找并一键预约最理想的实验空间',
          path: routes.labs,
          icon: '⌬',
          iconClass: 'cyan'
        },
        {
          title: '我的预约',
          desc: '全方位管理您的实验行程与历史记录',
          path: routes.myReservations,
          icon: '☑',
          iconClass: 'indigo'
        },
        {
          title: '智能助手',
          desc: '利用 AI 快速查询状态或解答系统疑问',
          path: routes.agent,
          icon: '✦',
          iconClass: 'gold'
        }
      ]
    }
  },
  async onShow() {
    if (!requireLogin()) return
    // #ifdef H5
    uni.hideTabBar()
    // #endif
    this.profile = getProfile()
    await this.loadData()
  },
  methods: {
    go(path) {
      openPage(path)
    },
    goLabDetail(id) {
      openPage(routes.labDetail, { query: { id } })
    },
    goReserveFromHome(lab) {
      if (!lab || lab.status !== 'active') return
      openPage(routes.reserve, { query: { labId: lab.id, campusId: lab.campus_id } })
    },
    resolveType(item) {
      const text = `${item.lab_name || ''} ${item.description || ''}`.toLowerCase()
      if (text.includes('生物') || text.includes('基因') || text.includes('医学')) return '生物实验'
      if (text.includes('化学') || text.includes('合成')) return '化学实验'
      if (text.includes('物理') || text.includes('光学') || text.includes('材料')) return '材料实验'
      if (text.includes('ai') || text.includes('机器') || text.includes('智能')) return '智能计算'
      return '综合实验'
    },
    async loadData() {
      try {
        const labsRes = await api.labs({ page: 1, page_size: 6 })
        const labs = labsRes?.list || labsRes?.data || (Array.isArray(labsRes) ? labsRes : [])
        this.featuredLabs = labs.slice(0, 3).map((lab, index) => ({
          ...lab,
          cover: LAB_COVERS[index % LAB_COVERS.length],
          coverImage: Array.isArray(lab.photos) && lab.photos.length ? lab.photos[0] : '',
          typeText: this.resolveType(lab),
          statusText: lab.status === 'active' ? (index % 2 === 0 ? '空闲' : '需预约') : '停用',
          statusClass: lab.status === 'active' ? (index % 2 === 0 ? 'active' : 'demand') : 'disabled'
        }))
      } catch (error) {
        this.featuredLabs = []
      }
    }
  }
}
</script>

<style lang="scss">
.student-home {
  min-height: 100vh;
  background: #eef2f7;
}

.student-home__body {
  padding: 22rpx 0 88rpx;
}

.student-home__shell {
  width: 100%;
  padding: 0 36rpx;
  box-sizing: border-box;
}

.student-home__hero {
  position: relative;
  overflow: hidden;
  padding: 58rpx 60rpx;
  border-radius: 32rpx;
  background: linear-gradient(112deg, #021b4c 0%, #052f72 56%, #1362a6 100%);
  box-shadow: 0 22rpx 52rpx rgba(5, 36, 83, 0.26);
}

.student-home__hero::after {
  content: '';
  position: absolute;
  right: -110rpx;
  top: -90rpx;
  width: 380rpx;
  height: 380rpx;
  border-radius: 999rpx;
  background: radial-gradient(circle, rgba(95, 192, 255, 0.42), rgba(95, 192, 255, 0));
}

.student-home__hero-title {
  position: relative;
  z-index: 1;
  font-size: 68rpx;
  line-height: 1.1;
  font-weight: 800;
  color: #f7fbff;
}

.student-home__hero-title-accent {
  color: #4cc8ff;
}

.student-home__hero-sub {
  position: relative;
  z-index: 1;
  margin-top: 20rpx;
  font-size: 30rpx;
  color: rgba(221, 236, 255, 0.92);
}

.student-home__hero-btn {
  position: relative;
  z-index: 1;
  margin-top: 34rpx;
  width: 260rpx;
  height: 84rpx;
  border-radius: 22rpx;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 10rpx;
  font-size: 28rpx;
  font-weight: 700;
  color: #f5f9ff;
  background: linear-gradient(90deg, #163f87 0%, #45bfff 100%);
  transition:
    transform 180ms ease,
    box-shadow 180ms ease,
    filter 180ms ease;
}

.student-home__hero-btn:hover {
  transform: translateY(-3rpx);
  filter: brightness(1.05);
  box-shadow: 0 14rpx 28rpx rgba(68, 186, 255, 0.3);
}

.student-home__hero-btn:active {
  transform: translateY(0);
  box-shadow: none;
}

.student-home__hero-arrow {
  font-size: 30rpx;
}

.student-home__entry-grid {
  margin-top: 34rpx;
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 22rpx;
}

.student-home__entry-card {
  min-height: 212rpx;
  padding: 28rpx 24rpx;
  border-radius: 24rpx;
  background: #ffffff;
  border: 1rpx solid rgba(197, 207, 220, 0.55);
  box-shadow: 0 12rpx 28rpx rgba(22, 44, 79, 0.05);
  transition:
    transform 180ms ease,
    box-shadow 180ms ease,
    border-color 180ms ease;
}

.student-home__entry-card:hover {
  transform: translateY(-4rpx);
  border-color: rgba(74, 165, 242, 0.36);
  box-shadow: 0 20rpx 40rpx rgba(22, 44, 79, 0.1);
}

.student-home__entry-icon {
  width: 74rpx;
  height: 74rpx;
  border-radius: 18rpx;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 34rpx;
  font-weight: 700;
  color: #1f3a65;
  background: #ecf1f8;
}

.student-home__entry-icon.blue { background: #e9f1ff; color: #18498b; }
.student-home__entry-icon.cyan { background: #e7f8ff; color: #0e6f99; }
.student-home__entry-icon.indigo { background: #edf0ff; color: #3d4f9b; }
.student-home__entry-icon.gold { background: #fff5df; color: #b97702; }

.student-home__entry-title {
  margin-top: 20rpx;
  font-size: 40rpx;
  font-weight: 800;
  color: #0d2b55;
}

.student-home__entry-desc {
  margin-top: 10rpx;
  font-size: 24rpx;
  line-height: 1.58;
  color: #5e718b;
}

.student-home__section-head {
  margin-top: 44rpx;
  margin-bottom: 22rpx;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.student-home__section-title {
  font-size: 48rpx;
  font-weight: 800;
  color: #0b2a53;
}

.student-home__section-controls {
  display: inline-flex;
  gap: 10rpx;
}

.student-home__section-dot {
  width: 52rpx;
  height: 52rpx;
  border-radius: 999rpx;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 24rpx;
  color: #8fa1b8;
  border: 1rpx solid #d7dfea;
  background: #f8fbff;
}

.student-home__list {
  display: grid;
  gap: 18rpx;
}

.student-home__list-item {
  min-height: 176rpx;
  padding: 18rpx;
  border-radius: 24rpx;
  background: #ffffff;
  border: 1rpx solid #e1e7f0;
  display: grid;
  grid-template-columns: 170rpx minmax(0, 1fr) 180rpx;
  align-items: center;
  gap: 22rpx;
  transition:
    transform 180ms ease,
    box-shadow 180ms ease;
}

.student-home__list-item:hover {
  transform: translateY(-3rpx);
  box-shadow: 0 18rpx 36rpx rgba(16, 41, 79, 0.09);
}

.student-home__list-cover {
  position: relative;
  height: 140rpx;
  border-radius: 16rpx;
  overflow: hidden;
}

.student-home__list-cover-img {
  width: 100%;
  height: 100%;
  display: block;
  transform: scale(1);
  transition: transform 220ms ease;
}

.student-home__list-item:hover .student-home__list-cover-img {
  transform: scale(1.04);
}

.student-home__list-cover-mask {
  position: absolute;
  inset: 0;
  background: linear-gradient(180deg, rgba(8, 26, 51, 0.08), rgba(8, 26, 51, 0.22));
}

.student-home__list-main {
  min-width: 0;
}

.student-home__list-name {
  font-size: 42rpx;
  line-height: 1.2;
  font-weight: 800;
  color: #0c2b56;
}

.student-home__list-tags {
  margin-top: 12rpx;
  display: flex;
  flex-wrap: wrap;
  gap: 8rpx;
}

.student-home__list-tag {
  min-height: 36rpx;
  padding: 0 10rpx;
  border-radius: 999rpx;
  background: #f0f4fa;
  color: #5a6f8d;
  font-size: 20rpx;
  display: inline-flex;
  align-items: center;
}

.student-home__list-meta {
  margin-top: 14rpx;
  font-size: 22rpx;
  color: #6f7f95;
}

.student-home__list-side {
  justify-self: end;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 14rpx;
}

.student-home__list-status {
  min-height: 40rpx;
  padding: 0 14rpx;
  border-radius: 999rpx;
  font-size: 20rpx;
  font-weight: 700;
  display: inline-flex;
  align-items: center;
}

.student-home__list-status.active {
  color: #0e8a4f;
  background: #e8fbf1;
}

.student-home__list-status.demand {
  color: #ab6f00;
  background: #fff3dd;
}

.student-home__list-status.disabled {
  color: #a83f3f;
  background: #ffe9e9;
}

.student-home__list-action {
  min-width: 138rpx;
  height: 64rpx;
  padding: 0 18rpx;
  border-radius: 16rpx;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 24rpx;
  font-weight: 700;
  color: #ffffff;
  background: #0c2a5a;
  transition:
    transform 160ms ease,
    background-color 160ms ease,
    box-shadow 160ms ease;
}

.student-home__list-action:hover {
  transform: translateY(-2rpx);
  background: #143d7d;
  box-shadow: 0 12rpx 24rpx rgba(9, 34, 73, 0.2);
}

.student-home__list-action.disabled {
  color: #6b7d94;
  background: #d7dee8;
}

.student-home__list-action.disabled:hover {
  transform: none;
  box-shadow: none;
}

.student-home__list-detail {
  font-size: 22rpx;
  font-weight: 700;
  color: #2c4f84;
}

.student-home__list-detail:hover {
  color: #0d3a77;
}

/* #ifndef H5 */
.student-home__shell {
  padding: 0 24rpx;
}

.student-home__hero {
  padding: 44rpx 34rpx;
}

.student-home__hero-title {
  font-size: 52rpx;
}

.student-home__hero-sub {
  font-size: 26rpx;
}

.student-home__entry-grid {
  grid-template-columns: 1fr;
}

.student-home__list-item {
  grid-template-columns: 1fr;
  justify-items: stretch;
}

.student-home__list-cover {
  height: 220rpx;
}

.student-home__list-side {
  justify-self: start;
  align-items: flex-start;
}
/* #endif */

/* #ifdef H5 */
@media screen and (max-width: 1120px) {
  .student-home__entry-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .student-home__list-item {
    grid-template-columns: 170rpx minmax(0, 1fr);
  }

  .student-home__list-side {
    grid-column: 1 / -1;
    flex-direction: row;
    justify-content: flex-end;
    align-items: center;
  }
}

@media screen and (max-width: 760px) {
  .student-home__shell {
    padding: 0 20rpx;
  }

  .student-home__entry-grid {
    grid-template-columns: 1fr;
  }

  .student-home__list-item {
    grid-template-columns: 1fr;
  }

  .student-home__list-cover {
    height: 210rpx;
  }

  .student-home__list-side {
    justify-content: flex-start;
  }
}
/* #endif */
</style>
