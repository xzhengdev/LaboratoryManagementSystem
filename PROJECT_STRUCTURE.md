# 项目结构说明

> 支持跨校区协作的分布式实验室管理系统 — 完整项目文件结构与职责说明

---

## 项目总结构

```
毕设/
├── 毕业论文.md                          # 毕业论文 Markdown 源文件
├── 论文初稿.md                          # 论文早期初稿
├── 1.md                                 # 论文备份/版本文件
├── 参考文献撰写规范.md                   # 学校参考文献格式规范
│
└── lab/                                 # 主项目目录 ★
    ├── README.md                        # 项目总览、快速开始、演示账号
    │
    ├── backend/                         # Flask 后端 ★★★ 核心
    │   ├── requirements.txt             # Python 依赖清单
    │   ├── run.py                       # 开发启动入口 (debug=True 热重载)
    │   ├── start_server.py              # 生产启动入口 (无热重载)
    │   ├── debug_seed_shards.py         # 调试用分库种子数据脚本
    │   ├── .env                         # 本地实际环境变量(敏感)
    │   ├── .env.example                 # 环境变量模板
    │   │
    │   ├── app/                         # Flask 应用主包
    │   │   ├── __init__.py              # 应用工厂: 创建Flask实例、初始化扩展、注册蓝图、注册错误处理
    │   │   ├── config.py                # 全局配置: 读取环境变量、数据库URL生成、Agent/Redis/CORS配置
    │   │   ├── extensions.py            # Flask扩展声明: db/migrate/jwt/cors 对象(避免循环导入)
    │   │   │
    │   │   ├── api/                     # ★ API 路由层 (接收请求、参数校验、调用Service)
    │   │   │   ├── __init__.py          # 蓝图集中注册
    │   │   │   ├── health.py            # GET /api/health — 系统健康检查
    │   │   │   ├── auth.py              # 登录/个人资料/头像上传/修改密码
    │   │   │   ├── campuses.py          # 校区 CRUD + 校区封面上传
    │   │   │   ├── labs.py              # 实验室 CRUD + 照片 + 排期 + 删除前置校验
    │   │   │   ├── equipment.py         # 设备 CRUD (含本校区权限隔离)
    │   │   │   ├── reservations.py      # ★ 预约创建/取消/列表/详情/幂等键
    │   │   │   ├── approvals.py         # 待审批列表 + 通过/驳回
    │   │   │   ├── assets.py            # ★ 资产申报 CRUD (教师申报/管理员审批)
    │   │   │   ├── lab_reports.py       # ★ 日报提交/列表/审核/图片上传
    │   │   │   ├── notifications.py     # 消息通知列表/未读数/标记已读
    │   │   │   ├── statistics.py        # 统计总览/校区维度/实验室维度/中心汇总
    │   │   │   ├── operation_logs.py    # 操作日志查询
    │   │   │   ├── users.py             # 用户管理 CRUD (system_admin)
    │   │   │   └── agent.py             # AI 助手对话 /agent/chat
    │   │   │
    │   │   ├── services/                # ★ 业务服务层 (核心业务规则 + 分布式机制)
    │   │   │   ├── auth_service.py      # 登录逻辑: 账号密码校验、角色一致性、JWT生成
    │   │   │   ├── reservation_service.py   # ★★★ 预约核心: 参数校验、冲突检测、审批流转、操作日志
    │   │   │   ├── asset_service.py         # ★★★ 资产申报: 预算锁定、审批流转、入库登记、照片归档
    │   │   │   ├── lab_report_service.py    # ★★ 日报管理: 提交、审核、图片关联、状态流转
    │   │   │   ├── statistics_service.py    # 聚合统计查询: 总览、校区、实验室利用率
    │   │   │   ├── notification_service.py  # 消息推送: 创建通知、未读数、标记已读
    │   │   │   ├── operation_log_service.py # 操作日志写入与查询
    │   │   │   ├── summary_sync_service.py  # ★ 中心汇总同步: 校区数据→中心库异步/手动同步
    │   │   │   │
    │   │   │   ├── db_router_service.py         # ★★★ 分库路由: campus_id→目标数据库连接、引擎缓存
    │   │   │   ├── file_storage_service.py       # ★★★ 文件存储: 本地存储 + SeaweedFS分布式上传/访问
    │   │   │   ├── distributed_lock_service.py   # ★★ Redis分布式锁: 获取/释放/自旋等待
    │   │   │   ├── idempotency_service.py        # ★★ 幂等控制: 幂等键校验、记录、去重
    │   │   │   ├── event_bus_service.py          # ★ 异步事件总线: 发布事件到Redis队列
    │   │   │   ├── cache_service.py              # ★ Redis缓存: 排期/统计/列表缓存
    │   │   │   ├── rate_limit_service.py         # ★ 限流: 用户/IP/接口维度令牌桶限流
    │   │   │   │
    │   │   │   ├── agent_service.py     # Agent规则引擎: 意图识别、问答生成
    │   │   │   ├── agent_rules.py       # Agent规则定义: 意图匹配模式
    │   │   │   ├── agent_helpers.py     # Agent辅助函数: 数据查询封装
    │   │   │   ├── agent_session.py     # Agent会话管理: 上下文存储
    │   │   │   └── agent_debug.py       # Agent调试工具: 调用链追踪
    │   │   │
    │   │   ├── models/                  # 数据模型层
    │   │   │   ├── __init__.py          # 模型统一导出
    │   │   │   ├── base.py              # BaseModel基类: 时间戳、to_dict通用方法
    │   │   │   └── entities.py          # ★ 全部业务实体: Campus/User/Laboratory/Equipment/
    │   │   │                             #   Reservation/Approval/OperationLog/Asset/AssetItem/
    │   │   │                             #   LabReport/Notification/FileObject/SummarySnapshot/
    │   │   │                             #   IdempotencyRecord/GlobalBudget/...
    │   │   │
    │   │   └── utils/                   # 工具层
    │   │       ├── decorators.py        # JWT认证装饰器、角色权限装饰器get_current_user()/role_required()
    │   │       ├── validators.py        # 参数校验: require_fields、日期时间解析
    │   │       ├── response.py          # 统一响应格式: success()/fail()
    │   │       └── exceptions.py        # 自定义业务异常: AppError
    │   │
    │   ├── scripts/                     # 脚本与工具
    │   │   ├── seed_shards.py           # 分库模式种子数据: 3校区独立数据填充
    │   │   ├── seed_multi_campus_users.py # 多校区用户批量种子数据
    │   │   ├── bootstrap_shards.py      # 分库引导脚本: 建表+初始数据
    │   │   ├── full_project_test.py     # ★★★ 自动化总控测试: 16项全链路测试统一调度
    │   │   ├── check_shards.py          # 分库结构检测: 验证3校区+中心库表结构完整性
    │   │   ├── check_runtime_switches.py # 运行开关检测: 分布式锁/限流/异步/Redis状态
    │   │   ├── check_seaweedfs_routing.py # ★ SeaweedFS路由检测: 3校区文件上传访问验证
    │   │   ├── diagnose_shard_mapping.py # 分库映射诊断: 路由配置与表分布分析
    │   │   ├── smoke_shards.py          # 冒烟测试: 快速验证分库基本连通性
    │   │   ├── sync_summary.py          # 手动汇总同步: 各校区→中心库
    │   │   └── event_worker.py          # 异步事件消费者: 后台处理通知/日志/汇总
    │   │
    │   ├── migrations/                  # 数据库迁移
    │   │   ├── README.md                # Flask-Migrate 使用说明
    │   │   └── *.sql                    # SQL迁移脚本(头像/照片/封面等字段)
    │   │
    │   └── test-results/                # 测试结果输出目录
    │       └── full_project_test_*.json # 自动化测试报告JSON(16项通过)
    │
    ├── frontend/                        # uni-app Web/H5 前端 ★★
    │   ├── App.vue                      # 应用根组件
    │   ├── main.js                      # 应用入口: 挂载全局配置
    │   ├── pages.json                   # 页面注册、路由、TabBar、全局样式
    │   ├── manifest.json                # 应用清单配置
    │   │
    │   ├── api/                         # 后端接口封装
    │   │   ├── request.js               # 统一请求方法: Token注入、错误拦截、响应处理
    │   │   └── index.js                 # 业务接口汇总: 登录/预约/资产/日报/统计/Agent等
    │   │
    │   ├── common/                      # 通用逻辑
    │   │   ├── session.js               # 登录态管理: Token存储、用户资料缓存、角色判断
    │   │   ├── platform.js              # 多端适配: H5/小程序接口地址自动切换
    │   │   ├── guard.js                 # 路由守卫: 登录状态校验与跳转
    │   │   ├── router.js                # 路由策略: navigateTo/redirectTo/switchTab统一封装
    │   │   └── agent-format.js          # Agent消息格式化工具
    │   │
    │   ├── config/                      # 全局配置
    │   │   └── navigation.js            # ★ 导航配置中心: 三端路由/Tab/菜单/角色文案/快捷入口
    │   │
    │   ├── components/                  # 跨页面复用组件
    │   │   ├── admin-layout.vue         # ★ 后台管理布局壳: 顶部 + 左侧菜单 + 内容区
    │   │   ├── page-hero.vue            # 页面顶部英雄区: 标题/副标题/操作按钮
    │   │   ├── agent-chat-window.vue    # Agent 对话窗口: 气泡聊天界面
    │   │   ├── bar-chart-card.vue       # 柱状图卡片: ECharts 封装
    │   │   ├── status-tag.vue           # 状态标签: 统一颜色映射
    │   │   ├── portal-footer.vue        # 用户端页脚组件
    │   │   ├── site-footer.vue          # 管理端页脚组件
    │   │   └── student-top-nav.vue      # 学生端顶部导航
    │   │
    │   ├── pages/                       # 业务页面
    │   │   ├── login/index.vue          # 登录页
    │   │   ├── home/index.vue           # 首页: 角色差异化欢迎页
    │   │   ├── campuses/index.vue       # 校区列表浏览
    │   │   ├── labs/index.vue           # 实验室列表/筛选
    │   │   ├── lab-detail/index.vue     # 实验室详情: 设备/排期/预约入口
    │   │   ├── schedule/index.vue       # 实验室排期日历
    │   │   ├── reserve/index.vue        # ★ 预约创建表单
    │   │   ├── my-reservations/index.vue # 我的预约列表
    │   │   ├── reservation-detail/index.vue # 预约详情
    │   │   ├── profile/index.vue        # 个人资料管理
    │   │   ├── agent/index.vue          # Agent 智能助手页面
    │   │   ├── notifications/index.vue  # 消息通知列表
    │   │   ├── daily-report/index.vue   # ★ 日报上报: 拍照/文字提交
    │   │   ├── asset-requests/index.vue # ★ 资产申报: 教师端申报表单
    │   │   ├── statistics/index.vue     # ★ 统计看板: 跨校区汇总 (system_admin)
    │   │   ├── admin-campuses/index.vue # 后台校区管理
    │   │   ├── admin-labs/index.vue     # 后台实验室管理
    │   │   ├── admin-equipment/index.vue # 后台设备管理
    │   │   ├── admin-approvals/index.vue # ★ 后台审批管理: 预约审批列表
    │   │   ├── admin-asset-requests/index.vue # ★ 资产审批与入库管理
    │   │   ├── admin-daily-reports/index.vue  # ★ 日报审核管理
    │   │   ├── admin-users/index.vue    # 后台用户管理
    │   │   ├── admin-profile/index.vue  # 管理员个人资料
    │   │   └── admin-logs/index.vue     # 操作日志审计
    │   │
    │   └── ARCHITECTURE.md              # 前端架构说明文档
    │
    ├── miniprogram/                     # 微信小程序端 ★
    │   ├── app.js                       # 小程序入口: 全局生命周期
    │   ├── app.json                     # 小程序配置: 页面注册、窗口样式
    │   ├── project.config.json          # 微信开发者工具配置
    │   ├── project.private.config.json  # 个人开发配置(不提交)
    │   ├── sitemap.json                 # 站点地图(SEO索引)
    │   ├── README.md                    # 小程序说明
    │   ├── DESIGN.md                    # 小程序设计文档
    │   │
    │   ├── utils/                       # 工具库
    │   │   ├── api.js                   # 后端接口封装(同 frontend/api/index.js 并行)
    │   │   ├── request.js               # 请求封装: Token注入、wx.request封装
    │   │   └── session.js               # 登录态管理: 小程序Storage适配
    │   │
    │   └── pages/                       # 小程序页面
    │       ├── login/login.js/json       # 登录页
    │       ├── home/home.js/json         # 首页
    │       ├── campuses/campuses.js/json # 校区浏览
    │       ├── labs/labs.js/json         # 实验室列表
    │       ├── lab-detail/lab-detail.js/json # 实验室详情
    │       ├── reserve/reserve.js/json   # ★ 预约创建(移动端核心)
    │       ├── my-reservations/my-reservations.js/json # 我的预约
    │       ├── reservation-detail/reservation-detail.js/json # 预约详情
    │       ├── profile/profile.js/json   # 个人中心
    │       ├── agent/agent.js/json       # Agent 问答
    │       ├── notifications/notifications.js/json # 消息中心
    │       ├── daily-report/daily-report.js/json    # ★ 日报上报(拍照上传)
    │       ├── asset-requests/asset-requests.js/json # ★ 资产申报(教师端)
    │       └── asset-request-records/asset-request-records.js/json # ★ 申报记录查询
    │
    ├── benchmark/                       # 并发压测工具
    │   ├── README.md                    # 压测说明
    │   ├── reservation_concurrency_benchmark.py # ★★★ 预约并发压测脚本:
    │   │                                  # 同幂等键重复请求/高频不同幂等键/并发抢占同一时段
    │   └── results/                     # 压测结果目录
    │       └── reservation_*.json       # 各场景压测结果JSON(包含rps/P95/状态码分布)
    │
    ├── infra/                           # 基础设施配置
    │   └── docker/
    │       ├── docker-compose.seaweedfs-multi-campus.yml  # ★ SeaweedFS 3校区多实例编排
    │       └── docker-compose.stage-c.yml # 阶段C Docker编排(后端+Redis+SeaweedFS+Nginx)
    │
    └── 答辩PPT/                         # 答辩准备材料
        ├── 答辩PPT讲稿.md               # 答辩演讲稿
        ├── slides-work/                 # PPT 生成工具链
        │   ├── create-defense-deck.js   # ★ 答辩PPT生成脚本(pptxgenjs)
        │   ├── package.json             # Node依赖
        │   └── pptxgenjs_helpers/       # PPT生成辅助模块
        │       ├── index.js             # 入口
        │       ├── layout.js            # 布局引擎
        │       ├── layout_builders.js   # 布局构建器
        │       ├── text.js              # 文本处理
        │       ├── code.js              # 代码块渲染
        │       ├── image.js             # 图片处理
        │       ├── svg.js               # SVG渲染
        │       ├── latex.js             # LaTeX公式渲染
        │       └── util.js              # 通用工具
        └── docs/                        # 参考文档
            ├── 论文目录_三级标题版.md    # 论文大纲
            ├── 需求与改动总清单_分布式重构.md
            ├── 分库开发启动指南.md
            ├── 阶段C实施说明.md
            ├── 后期代码改动实施指南_分阶段执行.md
            ├── 后端分布式与高并发图示_论文素材.md
            ├── SeaweedFS接入实施方案_多校区资产图片存储.md
            ├── 分布式与高并发改造实施说明.md
            └── 压测报告_2026-04-27_预约并发.md
```

---

## 关键文件按论文主题对应

| 论文章节 | 论文主题 | 核心对应代码文件 |
|---|---|---|
| 第4章 校区分库 | 分库路由 | `backend/app/services/db_router_service.py`, `backend/app/config.py` |
| 第4章 中心汇总 | 异步汇总 | `backend/app/services/summary_sync_service.py`, `backend/scripts/sync_summary.py`, `backend/scripts/event_worker.py` |
| 第4章 文件存储 | SeaweedFS | `backend/app/services/file_storage_service.py`, `infra/docker/docker-compose.seaweedfs-multi-campus.yml` |
| 第4章 幂等控制 | 幂等键 | `backend/app/services/idempotency_service.py` |
| 第4章 分布式锁 | Redis锁 | `backend/app/services/distributed_lock_service.py` |
| 第4章 缓存/限流/异步 | 并发治理 | `backend/app/services/cache_service.py`, `backend/app/services/rate_limit_service.py`, `backend/app/services/event_bus_service.py` |
| 第5章 资产模块 | 申报/审批/入库 | `backend/app/services/asset_service.py`, `backend/app/api/assets.py` |
| 第5章 日报模块 | 提交/审核/图片 | `backend/app/services/lab_report_service.py`, `backend/app/api/lab_reports.py` |
| 第5章 预约模块 | 冲突检测/审批 | `backend/app/services/reservation_service.py`, `backend/app/api/reservations.py` |
| 第5章 Agent模块 | 查询问答 | `backend/app/services/agent_service.py`, `backend/app/api/agent.py` |
| 第7章 测试验证 | 自动化总控 | `backend/scripts/full_project_test.py`, `benchmark/reservation_concurrency_benchmark.py` |
| 第7章 分库测试 | 分库结构检测 | `backend/scripts/check_shards.py`, `backend/scripts/smoke_shards.py` |
| 第7章 文件存储测试 | SeaweedFS路由 | `backend/scripts/check_seaweedfs_routing.py` |
| 第7章 运行开关检测 | 分布式配置 | `backend/scripts/check_runtime_switches.py` |

---

## 技术栈总览

| 层级 | 技术 | 版本/说明 |
|---|---|---|
| 后端框架 | Flask | 3.x |
| ORM | Flask-SQLAlchemy / SQLAlchemy | — |
| 认证 | Flask-JWT-Extended | JWT 无状态认证 |
| 数据库 | MySQL (生产) / SQLite (开发) | 多实例分库 |
| 缓存与锁 | Redis | 分布式锁、幂等记录、缓存、事件队列 |
| 文件存储 | SeaweedFS | 校区级分布式文件存储 |
| Web前端 | uni-app (Vue) | H5 单页面应用 |
| 小程序 | 微信原生小程序 | 学生/教师移动端 |
| 压测工具 | Python requests + threading | 自定义并发压测脚本 |
| 容器化 | Docker + Docker Compose | SeaweedFS多实例编排 |

---

## 项目分层架构

```text
┌─────────────────────────────────────────────┐
│              前端 / 小程序端                   │
│    Web管理端 (Vue)  │  微信小程序 (原生)       │
└──────────────────┬──────────────────────────┘
                   │  RESTful API (HTTP/JSON)
┌──────────────────▼──────────────────────────┐
│              API 路由层 (app/api/)            │
│  认证/校区/实验室/预约/资产/日报/统计/Agent    │
└──────────────────┬──────────────────────────┘
                   │
┌──────────────────▼──────────────────────────┐
│          业务服务层 (app/services/)            │
│  ┌──────────┐ ┌──────────┐ ┌──────────────┐ │
│  │ 预约服务  │ │ 资产服务  │ │ 日报服务      │ │
│  └──────────┘ └──────────┘ └──────────────┘ │
│  ┌──────────┐ ┌──────────┐ ┌──────────────┐ │
│  │ 分库路由  │ │ 文件存储  │ │ 分布式锁      │ │
│  └──────────┘ └──────────┘ └──────────────┘ │
│  ┌──────────┐ ┌──────────┐ ┌──────────────┐ │
│  │ 幂等控制  │ │ 限流服务  │ │ 缓存/事件总线  │ │
│  └──────────┘ └──────────┘ └──────────────┘ │
└──────────────────┬──────────────────────────┘
                   │
┌──────────────────▼──────────────────────────┐
│           数据层 & 基础设施                    │
│  MySQL (校区5/6/7 + 中心汇总库)                │
│  Redis (分布式锁/缓存/幂等/事件队列)            │
│  SeaweedFS (校区5/6/7 文件存储)                │
└─────────────────────────────────────────────┘
```
