# 实验室预约管理系统（毕业设计）

支持多校区协作的实验室预约系统，包含：
- 后端 API（Flask）
- Web 管理端 / H5（uni-app）
- 微信小程序端
- Agent 智能助手（规则模式 + 可选 LLM 模式）

## 功能概览

- 用户与权限：学生、教师、实验室管理员、系统管理员
- 校区/实验室/设备管理
- 预约创建、冲突校验、审批流
- 统计分析（总览、校区、实验室利用率）
- Agent 自然语言问答（我的预约、可预约实验室、排期、统计）

## 技术栈

- 后端：Flask, SQLAlchemy, Flask-Migrate, Flask-JWT-Extended, Flask-CORS
- 数据库：MySQL（生产）/ SQLite（开发）
- 前端：uni-app（H5）
- 小程序：微信原生小程序

## 目录结构

```text
lab/
├─ backend/                # Flask 后端
│  ├─ app/
│  │  ├─ api/
│  │  ├─ models/
│  │  ├─ services/
│  │  └─ utils/
│  ├─ migrations/
│  ├─ scripts/
│  ├─ run.py
│  └─ requirements.txt
├─ frontend/               # uni-app H5/Web 端
├─ miniprogram/            # 微信小程序端
└─ README.md
```

## 快速开始（本地开发）

### 1) 后端启动

```bash
cd backend
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS / Linux:
# source .venv/bin/activate

pip install -r requirements.txt
copy .env.example .env
python scripts/seed.py
python run.py
```

默认启动地址：`http://127.0.0.1:5000`

### 2) 前端运行

推荐使用 HBuilderX 打开 `frontend/`：
- 运行到浏览器（H5）
- 或打包后发布

### 3) 小程序运行

使用微信开发者工具打开 `miniprogram/` 并配置合法请求域名。

## 环境变量说明（后端）

使用 `backend/.env.example` 作为模板，关键变量如下：

- `SECRET_KEY`, `JWT_SECRET_KEY`
- `DATABASE_URL`（优先）  
  或 MySQL 组合：`MYSQL_HOST / MYSQL_PORT / MYSQL_USER / MYSQL_PASSWORD / MYSQL_DB`
- `AGENT_PROVIDER`：`rule` / `openai` / `deepseek`
- `AGENT_MODEL`
- `LLM_API_KEY`
- `LLM_BASE_URL`

## 默认演示账号

- 学生：`student1 / 123456`
- 教师：`teacher1 / 123456`
- 实验室管理员：`labadmin1 / 123456`
- 系统管理员：`admin1 / 123456`

## 主要接口

- 认证：`/api/auth/*`
- 校区：`/api/campuses*`
- 实验室：`/api/labs*`
- 设备：`/api/equipment*`
- 预约：`/api/reservations*`
- 审批：`/api/approvals*`
- 统计：`/api/statistics*`
- Agent：`POST /api/agent/chat`

## 部署建议（生产）

- 后端：`gunicorn + nginx`
- 数据库：MySQL
- 前端：构建后静态托管到 nginx
- 接口代理：前端走同域 `/api`，由 nginx 反代到后端
- 安全：务必替换所有密钥，不要提交 `.env`、上传目录和缓存日志

## 许可证

仅用于毕业设计学习与演示。
