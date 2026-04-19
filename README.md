# 实验室预约开发说明

本项目是一个前后端分离的毕业设计 MVP，主题为“支持跨校区协作的实验室预约管理系统”。系统包含用户登录、校区与实验室查询、预约提交、审批管理、统计概览，以及新增的 `Agent` 自然语言助手窗口。

## 项目结构

```text
lab
├─ backend
│  ├─ app
│  │  ├─ api
│  │  ├─ models
│  │  ├─ services
│  │  └─ utils
│  ├─ migrations
│  ├─ scripts
│  ├─ .env.example
│  ├─ requirements.txt
│  └─ run.py
├─ frontend
│  ├─ api
│  ├─ common
│  ├─ components
│  ├─ pages
│  ├─ App.vue
│  ├─ main.js
│  ├─ manifest.json
│  ├─ pages.json
│  └─ uni.scss
└─ README.md
```

## 后端说明

- 技术栈：`Flask + Flask-SQLAlchemy + Flask-JWT-Extended + Flask-Migrate + Flask-CORS`
- 数据库：
  - 优先读取 `DATABASE_URL`
  - 如果配置了 `MYSQL_HOST / MYSQL_USER / MYSQL_PASSWORD / MYSQL_DB`，则走 MySQL
  - 如果都没配，会回退到本地 `sqlite:///lab_dev.db`，便于直接演示
- 统一返回结构：

```json
{
  "code": 0,
  "message": "success",
  "data": {}
}
```

### 后端安装与运行

```bash
cd lab/backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn
copy .env.example .env
python scripts/seed.py
python run.py
```

如果你要严格使用 MySQL，请先建库 `lab_reservation`，然后在 `.env` 中填写数据库连接信息。

### 迁移命令

```bash
cd lab/backend
flask --app run.py db init
flask --app run.py db migrate -m "init"
flask --app run.py db upgrade
```

### Seed 数据

初始化脚本：`lab/backend/scripts/seed.py`

默认测试账号：

- 学生：`student1 / 123456`
- 教师：`teacher1 / 123456`
- 实验室管理员：`labadmin1 / 123456`
- 系统管理员：`admin1 / 123456`

## 已实现 API

### 认证

- `POST /api/auth/login`
- `GET /api/auth/profile`

### 校区

- `GET /api/campuses`
- `GET /api/campuses/<id>`
- `POST /api/campuses`
- `PUT /api/campuses/<id>`
- `DELETE /api/campuses/<id>`

### 实验室

- `GET /api/labs`
- `GET /api/labs/<id>`
- `GET /api/labs/<id>/schedule`
- `POST /api/labs`
- `PUT /api/labs/<id>`
- `DELETE /api/labs/<id>`

### 设备

- `GET /api/equipment`
- `POST /api/equipment`
- `PUT /api/equipment/<id>`
- `DELETE /api/equipment/<id>`

### 预约

- `POST /api/reservations`
- `GET /api/reservations/my`
- `GET /api/reservations/<id>`
- `POST /api/reservations/<id>/cancel`
- `GET /api/reservations`

### 审批

- `GET /api/approvals/pending`
- `POST /api/approvals/<reservation_id>`

### 统计

- `GET /api/statistics/overview`
- `GET /api/statistics/campus`
- `GET /api/statistics/lab_usage`

### Agent

- `POST /api/agent/chat`

## Agent 助手说明

系统新增了一个前端悬浮窗口组件 `frontend/components/agent-chat-window.vue`，用户可以直接输入自然语言，例如：

- “帮我看看今天有哪些实验室还能预约”
- “查看我的预约”
- “共享基础虚拟仿真实验室明天的排期”
- “给我看统计概览”

后端 `app/services/agent_service.py` 支持两种模式：

- `rule`：默认模式，不依赖外部模型，基于业务关键词返回预约建议、排期摘要和统计信息
- `openai`：如果配置了 `OPENAI_API_KEY` 和兼容接口地址，会自动调用外部对话模型

## 前端说明

- 技术栈：`uni-app`
- 支持页面：
  - 登录页
  - 首页
  - 校区列表页
  - 实验室列表页
  - 实验室详情页
  - 排期页
  - 预约提交页
  - 我的预约页
  - 预约详情页
  - 审批管理页
  - 实验室管理页
  - 统计页
  - Agent 页

### 前端运行

建议用 `HBuilderX` 导入 `lab/frontend`：

1. 选择“运行到浏览器”测试 H5
2. 选择“运行到小程序模拟器”测试微信小程序
3. 后端接口地址默认写在 `frontend/api/request.js` 中，当前为 `http://127.0.0.1:5000/api`

前端多端地址策略现在由 `frontend/common/platform.js` 统一控制：

- `H5 / PC 浏览器`：默认优先使用当前页面主机名，并拼接为 `:5000/api`
- `本机开发`：自动回退到 `http://127.0.0.1:5000/api`
- `微信小程序`：默认使用 `http://192.168.1.6:5000/api`

如果你的电脑局域网地址变化了，只需要改 `frontend/common/platform.js` 里的 `MP_BASE_URL` 即可。

## 已实现的业务规则

- 同一实验室同一时间段不允许重复预约
- 预约必须在实验室开放时间内
- 开始时间必须早于结束时间
- 停用实验室不可预约
- 禁用用户不可预约
- 普通用户只能查看自己的预约
- 实验室管理员只能审批自己校区的预约
- 审批状态支持 `approved / rejected / cancelled`

## 当前说明

这版优先保证毕业设计演示所需的 MVP 闭环完整，重点是：

- 后端接口结构清晰，能直接扩展
- 前端页面足够覆盖演示路径
- Agent 已经以“自然语言窗口”的形式接入业务系统

如果你下一步要继续，我建议直接做这三件事：

1. 把实验室管理页继续补成完整 CRUD
2. 将 Agent 从规则模式切到真实大模型
3. 增加操作日志、图表组件和审批备注输入框
