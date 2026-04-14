<template>
  <view>
    <user-top-nav active="campuses" />
    <view class="page">
      <view class="page-shell">
        <page-hero
          kicker="校区资源"
          title="校区列表"
          subtitle="统一展示各校区的实验室资源分布、地址信息与预约入口"
        />

        <view class="grid">
          <view v-for="item in list" :key="item.id" class="card">
            <view class="actions">
              <view class="title">{{ item.campus_name }}</view>
              <status-tag :status="item.status === 'active' ? 'active' : 'disabled'" />
            </view>
            <view class="subtitle">{{ item.address }}</view>
            <view class="subtitle">{{ item.description || '暂无校区简介' }}</view>
            <view class="actions" style="margin-top: 20rpx;">
              <view class="btn btn-light" @click="goLabs(item.id)">查看实验室</view>
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
  components: { PageHero, PortalFooter, StatusTag, UserTopNav },
  data() {
    return { list: [] }
  },
  async onShow() {
    if (!requireLogin()) return
    // #ifdef H5
    uni.hideTabBar()
    // #endif
    this.list = await api.campuses()
  },
  methods: {
    goLabs(campusId) {
      openPage(routes.labs, { query: { campusId } })
    }
  }
}
</script>
