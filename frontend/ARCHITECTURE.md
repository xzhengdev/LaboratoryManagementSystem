# 前端结构说明

本文档用于说明“支持跨校区协作的分布式实验室管理系统”前端的代码组织方式，方便毕业设计答辩、后续扩展和团队协作。

## 一、目录分层

```text
frontend
├─ api                    # 所有后端接口请求封装
├─ common                 # 会话、平台、权限、路由等通用逻辑
├─ components             # 跨页面复用组件
├─ config                 # 导航、角色、路由、信息架构配置
├─ pages                  # 业务页面
│  ├─ 用户端页面
│  └─ 管理后台页面
├─ App.vue                # 应用根组件
├─ main.js                # 应用入口
├─ pages.json             # 页面注册与全局配置
└─ uni.scss               # 全局设计令牌与通用样式
```

## 二、模块职责

### 1. `api`
- `request.js`
  负责统一请求方法、Token 注入、错误处理。
- `index.js`
  负责按业务领域暴露接口方法，页面只调用业务方法，不直接拼 URL。

### 2. `common`
- `session.js`
  管理登录态、用户资料缓存、角色判断。
- `platform.js`
  管理 H5、微信小程序等多端接口地址差异。
- `guard.js`
  管理登录校验。
- `router.js`
  管理页面跳转策略，统一处理 `navigateTo / redirectTo / switchTab`。

### 3. `config`
- `navigation.js`
  统一管理三端页面路由、Tab 结构、PC 前台导航、后台左侧菜单、角色文案、快捷入口。

### 4. `components`
- `page-hero.vue`
  页面顶部英雄区组件，用于统一标题、副标题和顶部操作区。
- `admin-layout.vue`
  后台通用布局壳，负责顶部区域、左侧菜单和内容插槽。
- `status-tag.vue`
  统一状态标签样式。
- `bar-chart-card.vue`
  简单图表卡片组件。
- `agent-chat-window.vue`
  智能助手对话窗口组件。

## 三、页面分组

### 1. 用户端页面
- `login`
- `home`
- `campuses`
- `labs`
- `lab-detail`
- `schedule`
- `reserve`
- `my-reservations`
- `reservation-detail`
- `profile`
- `agent`

### 2. 管理后台页面
- `admin-dashboard`
- `admin-campuses`
- `admin-labs`
- `admin-equipment`
- `admin-approvals`
- `admin-users`
- `statistics`

其中后台页面目前已经形成了较清晰的职责分层：

- `admin-dashboard`
  负责总览指标、图表和高频操作入口。
- `admin-campuses`
  负责校区状态、地址信息和跨校区资源概览展示。
- `admin-labs`
  负责实验室表单维护与列表展示，是当前最接近 CRUD 的后台页。
- `admin-equipment`
  负责设备筛选、库存查看与状态展示。
- `admin-approvals`
  负责待审批预约的集中处理，突出审批意见填写。
- `admin-users`
  负责用户、角色和校区归属的后台信息展示，当前为演示数据承接页。

## 四、结构设计原则

### 1. 路由与导航分离
页面内不再到处写死路径字符串，统一由 `config/navigation.js` 维护。

### 2. 页面壳与业务内容分离
将顶部 Hero 区、后台布局壳抽成组件，页面更专注于“业务数据 + 交互逻辑”。

### 3. 用户端与后台共享设计语言
虽然布局不同，但状态色、卡片、按钮、阴影、标题层级统一来自 `uni.scss`。

### 4. 多端差异集中处理
不同平台的接口地址与跳转行为尽量收口在 `common` 层，不散落到页面里。

## 五、后续建议

下一步可以继续细化以下内容：

1. 将筛选条、表格工具栏、详情信息块继续抽成复用组件。
2. 为用户端补充真正的 TabBar 图标资源并写入 `pages.json`。
3. 给后台表格页增加统一的“搜索栏 + 表格 + 弹窗表单 + 详情抽屉”模板。
4. 若后续迁移到 `uni-app cli`，可补充 `package.json` 与命令行构建脚本。

## 六、当前后台页面形态

为了保证后台体验统一，目前后台主要页面统一采用以下组合：

1. 顶部标题区
   使用 `admin-layout + page-hero` 统一呈现页面定位和管理员入口。
2. 概览统计区
   使用 3~4 个卡片快速展示该页面最重要的数量信息。
3. 工具栏区
   放置搜索、筛选、状态提示或“演示数据”等说明。
4. 内容区
   按页面性质选择卡片、表格或审批卡片列表。

这意味着后续如果继续接入真实 CRUD，只需要优先在“工具栏区”和“内容区”增加弹窗表单、抽屉详情和批量操作，而不需要重新推翻页面骨架。
