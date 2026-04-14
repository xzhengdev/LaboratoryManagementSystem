<template>
  <view>
    <user-top-nav active="labs" />
    <view class="page">
      <view class="page-shell">
        <page-hero
          kicker="便捷预约"
          title="实验室列表"
          subtitle="支持按关键词和校区筛选，快速进入详情、时段查询与预约流程"
        />

        <view class="portal-search-layout">
          <view class="card portal-filter-card">
            <view class="title portal-filter-title">筛选条件</view>
            <view class="field">
              <text class="label">关键词</text>
              <input v-model="keyword" class="input" placeholder="搜索实验室名称或地点" />
            </view>
            <view class="field">
              <text class="label">校区</text>
              <picker :range="campusOptions" range-key="campus_name" @change="changeCampus">
                <view class="input">{{ currentCampusName }}</view>
              </picker>
            </view>
            <view class="actions">
              <view class="btn" @click="loadData">应用筛选</view>
              <view class="btn btn-light" @click="resetFilter">重置</view>
            </view>
          </view>

          <view>
            <!-- #ifdef H5 -->
            <view class="card portal-toolbar-card">
              <view>
                <view class="portal-toolbar__title">实验室资源检索</view>
                <view class="portal-toolbar__sub">桌面端采用左侧筛选 + 右侧结果区，更适合连续对比与浏览。</view>
              </view>
              <view class="pill">结果 {{ filteredList.length }} 条</view>
            </view>
            <!-- #endif -->

            <view v-if="!filteredList.length" class="card empty-state">没有找到符合条件的实验室，请尝试调整搜索词或筛选条件。</view>

            <view class="grid">
              <view v-for="item in filteredList" :key="item.id" class="card">
                <view class="actions">
                  <view class="title">{{ item.lab_name }}</view>
                  <status-tag :status="item.status === 'active' ? 'active' : 'disabled'" />
                </view>
                <view class="subtitle">{{ item.campus_name }} · {{ item.location }}</view>
                <view class="subtitle">容纳 {{ item.capacity }} 人 · {{ item.open_time.slice(0, 5) }} - {{ item.close_time.slice(0, 5) }}</view>
                <view class="actions" style="margin-top: 20rpx;">
                  <view class="btn btn-light" @click="goDetail(item.id)">查看详情</view>
                  <view class="btn" @click="goReserve(item)">立即预约</view>
                </view>
              </view>
            </view>
          </view>
        </view>
      </view>

      <portal-footer />
    </view>
  </view>
</template>

<script>
import { api } from '../../api/index'
import { requireLogin } from '../../common/guard'
import { openPage } from '../../common/router'
import { routes } from '../../config/navigation'
import PageHero from '../../components/page-hero.vue'
import PortalFooter from '../../components/portal-footer.vue'
import StatusTag from '../../components/status-tag.vue'
import UserTopNav from '../../components/user-top-nav.vue'

export default {
  components: { StatusTag, PageHero, PortalFooter, UserTopNav },
  data() {
    return {
      campusId: '',
      keyword: '',
      campusOptions: [{ id: '', campus_name: '全部校区' }],
      list: []
    }
  },
  computed: {
    currentCampusName() {
      const target = this.campusOptions.find((item) => String(item.id) === String(this.campusId))
      return target ? target.campus_name : '全部校区'
    },
    filteredList() {
      const text = this.keyword.trim().toLowerCase()
      if (!text) return this.list
      return this.list.filter((item) => (
        `${item.lab_name}${item.location}${item.campus_name}`.toLowerCase().includes(text)
      ))
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
    const campuses = await api.campuses()
    this.campusOptions = [{ id: '', campus_name: '全部校区' }].concat(campuses)
    await this.loadData()
  },
  methods: {
    async loadData() {
      this.list = await api.labs(this.campusId ? { campus_id: this.campusId } : {})
    },
    changeCampus(event) {
      this.campusId = this.campusOptions[event.detail.value].id
      this.loadData()
    },
    resetFilter() {
      this.keyword = ''
      this.campusId = ''
      this.loadData()
    },
    goDetail(id) {
      openPage(routes.labDetail, { query: { id } })
    },
    goReserve(item) {
      openPage(routes.reserve, { query: { labId: item.id, campusId: item.campus_id } })
    }
  }
}
</script>

<style lang="scss">
.portal-filter-title {
  margin-bottom: 18rpx;
}

/* #ifdef H5 */
.portal-search-layout {
  display: grid;
  grid-template-columns: 320rpx minmax(0, 1fr);
  gap: 24rpx;
}

.portal-filter-card {
  position: sticky;
  top: 132rpx;
  align-self: start;
}

.portal-toolbar-card {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 20rpx;
}

.portal-toolbar__title {
  font-size: 28rpx;
  font-weight: 700;
  color: #1F2D3D;
}

.portal-toolbar__sub {
  margin-top: 8rpx;
  font-size: 22rpx;
  color: #7A8796;
}
/* #endif */
</style>
