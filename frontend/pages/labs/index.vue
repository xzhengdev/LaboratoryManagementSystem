<template>
  <view class="labs-page">
    <!-- #ifdef H5 -->
    <student-top-nav active="labs" />
    <!-- #endif -->

    <!-- #ifndef H5 -->
    <user-top-nav active="labs" />
    <!-- #endif -->

    <view class="labs-page__body">
      <view class="labs-page__shell">
        <view class="labs-page__hero">
          <view class="labs-page__title">实验室资源目录</view>
          <view class="labs-page__sub">
            Clinical Prism 分布式管理系统的资源概览。浏览、筛选并预约全国各校区的先进实验空间与尖端设备。
          </view>
        </view>

        <view class="labs-page__filters">
          <view class="labs-page__filter-block">
            <view class="labs-page__filter-label">实验类型</view>
            <view class="labs-page__chips">
              <view
                v-for="item in typeFilters"
                :key="item.key"
                class="labs-page__chip"
                :class="{ active: selectedType === item.key }"
                @click="selectedType = item.key"
              >
                {{ item.title }}
              </view>
            </view>
          </view>

          <picker class="labs-page__picker" :range="campusOptions" range-key="campus_name" @change="changeCampus">
            <view class="labs-page__map-btn">
              {{ currentCampusName }}
            </view>
          </picker>
        </view>

        <view v-if="!filteredList.length" class="labs-page__empty">
          暂无符合条件的实验室，请调整筛选后重试。
        </view>

        <view v-else class="labs-page__grid">
          <view
            v-for="(item, index) in filteredList"
            :key="item.id"
            class="labs-page__card"
            :class="{ featured: index === 3 }"
          >
            <view class="labs-page__cover" :style="{ background: item.cover }">
              <view class="labs-page__cover-tags">
                <view class="labs-page__tag status" :class="item.status === 'active' ? 'active' : 'busy'">
                  {{ item.status === 'active' ? '开放中' : '维护中' }}
                </view>
              </view>
            </view>

            <view class="labs-page__card-body">
              <view class="labs-page__card-title">{{ item.lab_name }}</view>
              <view class="labs-page__card-loc">{{ item.campus_name }} · {{ item.location || '位置待补充' }}</view>

              <view class="labs-page__tools">
                <view class="labs-page__tool">{{ item.typeText }}</view>
                <view class="labs-page__tool">容量 {{ item.capacity || 0 }}</view>
                <view class="labs-page__tool">{{ item.openText }}</view>
              </view>

              <view class="labs-page__actions">
                <view class="labs-page__btn light" @click="goDetail(item.id)">查看详情</view>
                <view
                  class="labs-page__btn primary"
                  :class="{ disabled: item.status !== 'active' }"
                  @click="goReserve(item)"
                >
                  {{ item.status === 'active' ? '立即预约' : '暂不可约' }}
                </view>
              </view>
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

const COVER_POOL = [
  'linear-gradient(135deg, #0a2e43 0%, #17618a 45%, #6ed0ff 100%)',
  'linear-gradient(135deg, #0a324f 0%, #1f7199 52%, #79d9ff 100%)',
  'linear-gradient(135deg, #15303b 0%, #2f5f7f 52%, #7fb7ce 100%)',
  'linear-gradient(135deg, #0e2d4f 0%, #174f88 50%, #6ab8ff 100%)',
  'linear-gradient(135deg, #0f2a3f 0%, #325e88 50%, #86bee6 100%)',
  'linear-gradient(135deg, #1f2f53 0%, #485f99 52%, #9ab2ef 100%)'
]

const TYPE_FILTERS = [
  { key: 'all', title: '全部' },
  { key: 'bio', title: '生物' },
  { key: 'chem', title: '化学' },
  { key: 'phy', title: '物理' },
  { key: 'ai', title: '人工智能' }
]

export default {
  components: { SiteFooter, StudentTopNav, UserTopNav },
  data() {
    return {
      selectedType: 'all',
      campusId: '',
      campusOptions: [],
      currentCampusIndex: 0,
      list: [],
      typeFilters: TYPE_FILTERS
    }
  },
  computed: {
    currentCampusName() {
      if (!this.campusOptions.length) return '全部'
      const current = this.campusOptions[this.currentCampusIndex]
      return current ? current.campus_name : '全部'
    },
    normalizedList() {
      return this.list.map((item, index) => {
        const typeText = this.resolveType(item)
        return {
          ...item,
          typeText,
          typeKey: this.resolveTypeKey(typeText),
          openText: `${(item.open_time || '00:00').slice(0, 5)} - ${(item.close_time || '00:00').slice(0, 5)}`,
          cover: COVER_POOL[index % COVER_POOL.length]
        }
      })
    },
    filteredList() {
      return this.normalizedList.filter((item) => {
        return this.selectedType === 'all' || item.typeKey === this.selectedType
      })
    }
  },
  onLoad(options) {
    this.campusId = options.campusId || ''
  },
  async onShow() {
    if (!requireLogin()) return
    // #ifdef H5
    uni.hideTabBar()
    // #endif
    await this.loadCampusOptions()
    await this.loadData()
  },
  methods: {
    async loadCampusOptions() {
      try {
        const campuses = await api.campuses()
        const all = Array.isArray(campuses) ? campuses : []
        this.campusOptions = all

        if (this.campusId) {
          const idx = all.findIndex((item) => String(item.id) === String(this.campusId))
          this.currentCampusIndex = idx >= 0 ? idx : 0
        } else {
          this.currentCampusIndex = 0
          this.campusId = all[0] ? String(all[0].id) : ''
        }
      } catch (error) {
        this.campusOptions = []
      }
    },
    async loadData() {
      try {
        this.list = await api.labs(this.campusId ? { campus_id: this.campusId } : {})
      } catch (error) {
        this.list = []
      }
    },
    resolveType(item) {
      const text = `${item.lab_name || ''} ${item.description || ''}`.toLowerCase()
      if (text.includes('生') || text.includes('基因') || text.includes('医')) return '生物'
      if (text.includes('化') || text.includes('合成')) return '化学'
      if (text.includes('物理') || text.includes('光学') || text.includes('材料')) return '物理'
      if (text.includes('ai') || text.includes('机器') || text.includes('智能')) return '人工智能'
      return '综合'
    },
    resolveTypeKey(typeText) {
      if (typeText === '生物') return 'bio'
      if (typeText === '化学') return 'chem'
      if (typeText === '物理') return 'phy'
      if (typeText === '人工智能') return 'ai'
      return 'all'
    },
    async changeCampus(event) {
      const index = Number(event.detail.value || 0)
      this.currentCampusIndex = index
      const current = this.campusOptions[index]
      this.campusId = current ? String(current.id) : ''
      await this.loadData()
    },
    goDetail(id) {
      openPage(routes.labDetail, { query: { id } })
    },
    goReserve(item) {
      if (item.status !== 'active') return
      openPage(routes.reserve, { query: { labId: item.id, campusId: item.campus_id } })
    }
  }
}
</script>

<style lang="scss">
.labs-page {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background:
    radial-gradient(circle at top right, rgba(65, 190, 253, 0.13), transparent 24%),
    linear-gradient(180deg, #f7f9fc 0%, #eef2f7 100%);
}

.labs-page__body {
  flex: 1;
  padding: 34rpx 0 60rpx;
}

.labs-page__shell {
  width: 100%;
  padding: 0 32rpx;
  box-sizing: border-box;
}

.labs-page__title {
  font-size: 74rpx;
  line-height: 1.03;
  color: #031635;
  font-weight: 800;
  letter-spacing: -1.4rpx;
}

.labs-page__sub {
  margin-top: 14rpx;
  max-width: 980rpx;
  color: #55647a;
  font-size: 30rpx;
  line-height: 1.55;
}

.labs-page__filters {
  margin-top: 26rpx;
  padding: 20rpx;
  border-radius: 24rpx;
  background: rgba(255, 255, 255, 0.72);
  border: 1rpx solid rgba(197, 198, 207, 0.2);
  display: grid;
  grid-template-columns: minmax(0, 1fr) max-content;
  gap: 18rpx;
  align-items: end;
}

.labs-page__filter-label {
  color: #3a4b63;
  font-size: 22rpx;
  font-weight: 700;
  margin-bottom: 10rpx;
}

.labs-page__chips {
  display: flex;
  align-items: center;
  gap: 10rpx;
  flex-wrap: wrap;
}

.labs-page__chip {
  min-width: 86rpx;
  height: 58rpx;
  border-radius: 999rpx;
  padding: 0 20rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #eef2f7;
  color: #3f5068;
  font-size: 22rpx;
  font-weight: 700;
}

.labs-page__chip.active {
  background: #041c42;
  color: #ecf4ff;
}

.labs-page__map-btn {
  height: 64rpx;
  border-radius: 16rpx;
  padding: 0 24rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #ffffff;
  color: #102a4c;
  font-size: 24rpx;
  font-weight: 700;
  border: 1rpx solid rgba(81, 103, 133, 0.2);
  white-space: nowrap;
}

.labs-page__picker {
  display: block;
}

.labs-page__empty {
  margin-top: 24rpx;
  border-radius: 20rpx;
  padding: 28rpx;
  background: #ffffff;
  color: #6f7f95;
  font-size: 24rpx;
}

.labs-page__grid {
  margin-top: 22rpx;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 24rpx;
}

.labs-page__card {
  overflow: hidden;
  border-radius: 26rpx;
  background: #ffffff;
  box-shadow: 0 16rpx 34rpx rgba(8, 27, 58, 0.06);
}

.labs-page__cover {
  height: 270rpx;
  position: relative;
}

.labs-page__cover-tags {
  position: absolute;
  left: 14rpx;
  top: 14rpx;
  display: flex;
  gap: 8rpx;
}

.labs-page__tag {
  height: 36rpx;
  border-radius: 999rpx;
  padding: 0 12rpx;
  display: flex;
  align-items: center;
  font-size: 18rpx;
  font-weight: 700;
}

.labs-page__tag.status {
  color: #ffffff;
}

.labs-page__tag.status.active {
  background: #2dbb73;
}

.labs-page__tag.status.busy {
  background: #f39b36;
}

.labs-page__card-body {
  padding: 24rpx;
}

.labs-page__card-title {
  color: #031635;
  font-size: 38rpx;
  line-height: 1.2;
  font-weight: 800;
}

.labs-page__card-loc {
  margin-top: 8rpx;
  color: #65768c;
  font-size: 23rpx;
}

.labs-page__tools {
  margin-top: 14rpx;
  display: flex;
  gap: 10rpx;
  flex-wrap: wrap;
}

.labs-page__tool {
  min-height: 38rpx;
  border-radius: 12rpx;
  padding: 0 12rpx;
  background: #eef2f7;
  color: #39506d;
  font-size: 20rpx;
  display: inline-flex;
  align-items: center;
}

.labs-page__actions {
  margin-top: 18rpx;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12rpx;
}

.labs-page__btn {
  height: 70rpx;
  border-radius: 16rpx;
  font-size: 24rpx;
  font-weight: 800;
  display: flex;
  align-items: center;
  justify-content: center;
}

.labs-page__btn.light {
  background: #ffffff;
  border: 2rpx solid #0b2652;
  color: #0b2652;
}

.labs-page__btn.primary {
  background: #041c42;
  color: #ecf4ff;
}

.labs-page__btn.primary.disabled {
  background: #cfd6df;
  color: #5d6c80;
}

.labs-page__card.featured {
  grid-column: span 2;
  display: grid;
  grid-template-columns: minmax(280rpx, 1fr) minmax(0, 1fr);
}

.labs-page__card.featured .labs-page__cover {
  height: 100%;
  min-height: 320rpx;
}

.labs-page__card.featured .labs-page__card-body {
  display: flex;
  flex-direction: column;
  justify-content: center;
}

/* #ifndef H5 */
.labs-page__shell {
  padding-left: 24rpx;
  padding-right: 24rpx;
}

.labs-page__title {
  font-size: 56rpx;
}

.labs-page__sub {
  font-size: 24rpx;
}

.labs-page__filters {
  grid-template-columns: 1fr;
}

.labs-page__grid {
  grid-template-columns: 1fr;
}

.labs-page__card.featured {
  grid-column: auto;
  grid-template-columns: 1fr;
}

.labs-page__card.featured .labs-page__cover {
  min-height: 270rpx;
}
/* #endif */

/* #ifdef H5 */
@media screen and (min-width: 1500px) {
  .labs-page__shell {
    padding-left: 56rpx;
    padding-right: 56rpx;
  }
}

@media screen and (max-width: 1200px) {
  .labs-page__grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .labs-page__card.featured {
    grid-column: auto;
    grid-template-columns: 1fr;
  }

  .labs-page__card.featured .labs-page__cover {
    min-height: 270rpx;
  }
}

@media screen and (max-width: 860px) {
  .labs-page__filters {
    grid-template-columns: 1fr;
  }

  .labs-page__grid {
    grid-template-columns: 1fr;
  }
}
/* #endif */
</style>
