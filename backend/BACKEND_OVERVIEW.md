# 实验室预约系统后端说明文档

## 1. 后端目标与需求分析

### 1.1 业务目标
本后端服务用于支撑「多校区实验室预约」系统的核心业务，提供统一 API 给小程序端和 Web 端调用，负责：
- 用户认证与鉴权
- 校区、实验室、设备的维护
- 预约提交、冲突校验、审批流
- 统计分析
- AI 助手问答（规则引擎/LLM）

### 1.2 角色与权限需求
系统主要角色：
- `student`：学生，发起预约、查看自己的预约
- `teacher`：教师，发起预约、查看自己的预约
- `lab_admin`：实验室管理员，管理本校区实验室/设备，审批本校区预约
- `system_admin`：系统管理员，跨校区管理用户/校区/实验室并可审批

权限核心要求：
- 所有敏感接口需登录（JWT）
- 管理端接口按角色限制
- `lab_admin` 仅限本校区数据范围

### 1.3 核心业务规则需求
预约创建需满足：
- 必填参数齐全（`campus_id, lab_id, reservation_date, start_time, end_time, purpose`）
- 实验室存在且状态可用
- 预约校区与实验室所属校区一致
- 预约时段在实验室开放时间内
- 人数不超过容量
- 时段不与已有有效预约冲突
- 学生/教师默认走审批，管理员可自动通过

### 1.4 非功能需求
- 响应格式统一，便于前端统一处理
- 错误码可读、可追踪
- 支持图片上传（头像/校区封面/实验室照片）
- 支持 SQLite（开发）与 MySQL（生产）
- 具备基础统计能力与操作日志能力

---

## 2. 技术栈与分层架构

### 2.1 技术栈
- 框架：Flask
- ORM：Flask-SQLAlchemy / SQLAlchemy
- 迁移：Flask-Migrate
- 认证：Flask-JWT-Extended
- 跨域：Flask-CORS
- 配置：python-dotenv
- HTTP 调用（AI）：requests

依赖见 [requirements.txt](./requirements.txt)

### 2.2 分层结构
- API 层（`app/api`）：路由定义、参数接收、调用服务层
- Service 层（`app/services`）：业务规则与事务逻辑
- Model 层（`app/models`）：数据模型与关系映射
- Utils 层（`app/utils`）：校验器、统一响应、权限装饰器、异常类型
- App 工厂层（`app/__init__.py`）：初始化 Flask 与扩展、注册蓝图与错误处理

---

## 3. backend 目录逐项说明

> 以下按“源码与业务相关文件”优先说明；运行产物与第三方环境单独说明。

### 3.1 入口与运行文件
- [run.py](./run.py)
  - 开发启动入口（`debug=True`），便于调试
- [start_server.py](./start_server.py)
  - 非热重载启动入口（`debug=False, use_reloader=False`），适合稳定联调/后台运行
- [.env.example](./.env.example)
  - 环境变量模板（密钥、数据库、Agent 配置）
- [.env](./.env)
  - 本地实际配置（敏感，不应外泄）

### 3.2 应用工厂与全局配置
- [app/__init__.py](./app/__init__.py)
  - 创建 Flask app
  - 初始化扩展（db/migrate/jwt/cors）
  - 注册蓝图（统一挂载 `/api`）
  - 注册异常处理（`AppError`、404、500、413）
  - 初始化上传目录并提供静态访问 `/uploads/<path>`
  - 注册 CLI 命令 `flask seed-data`

- [app/config.py](./app/config.py)
  - 读取环境变量
  - 动态生成数据库连接（`DATABASE_URL` 优先，否则 MySQL，否则 SQLite）
  - Agent provider/model/base_url/key 配置

- [app/extensions.py](./app/extensions.py)
  - 声明 Flask 扩展对象，避免循环导入

### 3.3 API 路由层（`app/api`）
- [api/__init__.py](./app/api/__init__.py)
  - 集中注册蓝图：`auth/campuses/labs/equipment/reservations/approvals/statistics/users/agent`

- [api/auth.py](./app/api/auth.py)
  - 登录、获取/更新个人资料、头像上传

- [api/campuses.py](./app/api/campuses.py)
  - 校区 CRUD、校区封面上传
  - 写接口仅 `system_admin`

- [api/labs.py](./app/api/labs.py)
  - 实验室列表/详情/排期
  - 实验室 CRUD、照片上传、删除（含预约阻塞校验）

- [api/equipment.py](./app/api/equipment.py)
  - 设备列表与 CRUD
  - `lab_admin` 仅能管理本校区实验室设备

- [api/reservations.py](./app/api/reservations.py)
  - 创建预约、取消预约、我的预约、预约详情、通用预约列表

- [api/approvals.py](./app/api/approvals.py)
  - 待审批列表、审批通过/拒绝

- [api/statistics.py](./app/api/statistics.py)
  - 总览、校区统计、实验室利用率

- [api/users.py](./app/api/users.py)
  - 用户列表、创建、更新、重置密码
  - 仅 `system_admin`

- [api/agent.py](./app/api/agent.py)
  - AI 助手对话入口 `/agent/chat`

### 3.4 服务层（`app/services`）
- [services/auth_service.py](./app/services/auth_service.py)
  - 登录主逻辑：账号密码、角色一致性、状态校验、JWT 生成

- [services/reservation_service.py](./app/services/reservation_service.py)
  - 预约核心规则集中地：
    - 必填参数校验
    - 校区与实验室一致性
    - 时间冲突检测
    - 审批逻辑与日志记录

- [services/statistics_service.py](./app/services/statistics_service.py)
  - 聚合统计查询（总览、校区维度、实验室维度）

- [services/agent_service.py](./app/services/agent_service.py)
  - 规则型问答 + 可选 LLM 回答
  - 识别“我的预约/统计/可预约实验室/指定实验室排期”等意图

### 3.5 数据模型层（`app/models`）
- [models/base.py](./app/models/base.py)
  - `BaseModel` + 时间戳 + 通用 `to_dict`

- [models/entities.py](./app/models/entities.py)
  - 业务实体：
    - `Campus` 校区
    - `User` 用户
    - `Laboratory` 实验室
    - `Equipment` 设备
    - `Reservation` 预约
    - `Approval` 审批
    - `OperationLog` 操作日志
  - 含模型关系与序列化增强字段（如 `campus_name`, `photos`）

- [models/__init__.py](./app/models/__init__.py)
  - 统一导出模型

### 3.6 工具层（`app/utils`）
- [utils/decorators.py](./app/utils/decorators.py)
  - `get_current_user()`、`role_required()`

- [utils/validators.py](./app/utils/validators.py)
  - `require_fields`、日期时间解析

- [utils/response.py](./app/utils/response.py)
  - 统一成功/失败响应结构

- [utils/exceptions.py](./app/utils/exceptions.py)
  - 业务异常 `AppError`

### 3.7 数据初始化与迁移
- [scripts/seed.py](./scripts/seed.py)
  - 一键生成演示数据（校区、实验室、设备、角色账号、示例预约）

- [migrations/README.md](./migrations/README.md)
  - Flask-Migrate 使用说明

- [migrations/20260415_add_user_avatar_and_lab_photos.sql](./migrations/20260415_add_user_avatar_and_lab_photos.sql)
  - 用户头像字段 + 实验室照片字段

- [migrations/20260415_add_campus_cover_url.sql](./migrations/20260415_add_campus_cover_url.sql)
  - 校区封面字段

### 3.8 运行时目录/文件（非业务源码）
- `backend/.venv/`：Python 虚拟环境（第三方依赖，不属于业务代码）
- `backend/uploads/`：上传文件目录（头像/校区封面/实验室图）
- `backend/instance/lab_dev.db`：本地 SQLite 数据库文件
- `backend/server.out.log`, `backend/server.err.log`：服务日志
- `__pycache__/`：Python 缓存目录

---

## 4. 请求处理主链路（从小程序到后端）

1. 客户端调用 `/api/...` 接口
2. API 层做参数接收、权限装饰器校验
3. Service 层执行业务规则与事务
4. Model 层读写数据库
5. `response.success/fail` 返回统一 JSON

统一成功返回：
```json
{ "code": 0, "message": "success", "data": {...} }
```

统一失败返回：
```json
{ "code": 40000, "message": "错误信息", "data": null }
```
并带对应 HTTP 状态码。

---

## 5. 权限与数据范围控制

控制方式：
- `@jwt_required()`：必须登录
- `@role_required(...)`：角色限制
- Service 内二次校验“数据归属”

典型场景：
- `lab_admin` 更新实验室时，必须是本校区实验室
- `student/teacher` 只能查看自己的预约详情
- 审批操作仅管理员角色可执行

---

## 6. 预约模块关键规则（最核心）

在 [reservation_service.py](./app/services/reservation_service.py) 实现：
- 参数完整性
- 用户状态可用性
- 实验室状态、校区匹配
- 时间段合法性（开始 < 结束）
- 开放时间边界
- 人数上限
- 时段冲突（`start < existing_end && end > existing_start`）
- 审批状态流转
- 操作日志记录

这部分是系统正确性的核心，也是答辩重点。

---

## 7. AI 助手模块说明

入口：[api/agent.py](./app/api/agent.py) -> [services/agent_service.py](./app/services/agent_service.py)

支持两种模式：
- 规则模式（默认可工作）
- LLM 模式（配置 `AGENT_PROVIDER` + `LLM_API_KEY`）

规则模式可处理：
- 我的预约
- 指定日期可预约实验室
- 指定实验室排期
- 统计概况

说明：目前 `actions` 里有部分 Web 路径（如 `/pages/labs/index`）与小程序路径不完全一致，前端需做映射或后端返回小程序专用路径。

---

## 8. 配置与环境变量

关键变量（见 [.env.example](./.env.example)）：
- `SECRET_KEY`, `JWT_SECRET_KEY`
- `DATABASE_URL` 或 MySQL 组合配置
- `AGENT_PROVIDER`, `AGENT_MODEL`, `LLM_API_KEY`, `LLM_BASE_URL`
- `UPLOAD_DIRNAME`

数据库选择优先级：
1. `DATABASE_URL`
2. MySQL 配置齐全时走 MySQL
3. 否则回退 SQLite `sqlite:///lab_dev.db`

---

## 9. 运行与初始化建议

### 9.1 本地开发
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

### 9.2 初始化演示数据
```bash
flask --app run.py seed-data
```
或
```bash
python scripts/seed.py
```

### 9.3 迁移流程
```bash
flask db init
flask db migrate -m "message"
flask db upgrade
```

---

## 10. 当前设计优点与改进建议

### 10.1 优点
- 分层清晰（API/Service/Model/Utils）
- 核心业务规则集中在 Service 层
- 权限控制与数据范围控制完整
- 响应结构统一，前端易接入
- 支持上传与多种数据库方案

### 10.2 建议改进
- 字符编码：源码注释/部分文案存在乱码，建议统一 UTF-8 无 BOM
- 安全：开发默认密钥需在生产替换
- CORS：当前 `/api/*` 允许所有来源，生产应按域名白名单
- Agent 路径：统一小程序与 Web 跳转路径协议
- 测试：补充预约冲突、审批流、权限边界的自动化测试
- 观测：可加入结构化日志与请求追踪 ID

---

## 11. 一句话总结

这个后端是一个以“预约规则正确性 + 多角色权限控制”为核心的 Flask 服务，已具备从认证、资源管理、预约审批到统计与 AI 助手的完整闭环，适合作为毕业设计演示与后续工程化扩展基础。
