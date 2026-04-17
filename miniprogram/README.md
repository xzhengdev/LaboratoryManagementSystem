# 实验室预约系统 - 微信小程序

基于原有 Flask 后端 API 的微信小程序前端。

## 功能模块

- 用户登录（学生/教师/实验室管理员/系统管理员）
- 校区列表浏览
- 实验室列表（按校区、类型筛选）
- 实验室详情（概览、设备、排期）
- 实验室预约（选择时间、人数、目的）
- 我的预约（按状态筛选、取消预约）
- 预约详情（审批记录）
- 个人资料（头像、信息修改）
- AI 助手（自然语言查询、页面引导）

## 目录结构

```
miniprogram/
├── app.js / app.json / app.wxss
├── utils/
│   ├── request.js      # 网络请求封装
│   ├── session.js      # 会话管理
│   └── api.js          # API 接口集合
├── pages/
│   ├── login/          # 登录页
│   ├── home/           # 首页（入口卡片、推荐实验室）
│   ├── campuses/       # 校区列表
│   ├── labs/           # 实验室列表（筛选）
│   ├── lab-detail/     # 实验室详情（标签页）
│   ├── reserve/        # 预约表单
│   ├── my-reservations/# 我的预约列表
│   ├── reservation-detail/ # 预约详情
│   ├── profile/        # 个人资料
│   └── agent/          # AI 助手聊天页
├── sitemap.json
└── project.config.json
```

## 运行要求

1. **后端服务**：Flask 后端需在 `http://127.0.0.1:5000` 运行（可在 `utils/request.js` 修改 `BASE_URL`）
2. **微信开发者工具**：导入本目录为小程序项目
3. **AppID**：已配置为 `wxb3d15e0804a6f2c3`（测试号），可替换为自己的 AppID

## 页面流程

1. 登录 → 选择角色（student/teacher/lab_admin/system_admin）
2. 首页 → 校区 / 实验室 / 我的预约 / AI 助手入口
3. 实验室列表 → 筛选（校区、类型）→ 详情页 → 预约
4. 我的预约 → 状态筛选 → 详情页 → 取消（如可取消）
5. 个人资料 → 编辑信息 / 更换头像 / 退出登录

## API 兼容性

- 使用 JWT token（`Authorization: Bearer <token>`）
- 状态码 401 自动跳转登录页
- 上传头像/封面使用 `wx.uploadFile`
- 其他请求使用 `wx.request`

## 样式规范

- 主色 `#4A90E2`（按钮、选中态）
- 背景 `#F7F9FC`
- 卡片圆角 `16rpx`
- 状态色：
  - 待审核 `#F5A623`
  - 已批准 `#27AE60`
  - 已拒绝 `#E25454`
  - 已取消 `#999`
  - 已完成 `#4A90E2`

## 适配说明

- 基于 uni-app 风格转写为原生小程序
- 保留原有业务逻辑与 API 调用方式
- 简化了管理端页面（仅学生/教师常用功能）
- 添加微信小程序特有交互（picker、uploadFile 等）

## 下一步

1. 在微信开发者工具中导入项目
2. 启动 Flask 后端（`python backend/run.py`）
3. 使用测试账号登录（如 `student1` / `123456`）
4. 体验完整预约流程