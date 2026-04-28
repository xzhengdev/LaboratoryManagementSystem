# 阶段 C 实施说明（多实例 + 负载均衡 + 异步解耦）

## 1. 本阶段新增内容

1. 多实例部署骨架：`infra/docker/docker-compose.stage-c.yml`
2. 统一入口网关：`infra/nginx/lab-stage-c.conf`（Nginx upstream 到 `backend1/backend2`）
3. 异步事件总线：`backend/app/services/event_bus_service.py`
4. 异步消费 Worker：`backend/scripts/event_worker.py`
5. 健康检查接口：`GET /api/health`

## 2. 代码链路改造

预约核心链路在“写入成功后”发布异步事件（不阻塞主事务）：

1. `reservation.created`
2. `reservation.cancelled`
3. `reservation.approved`
4. `reservation.rejected`

事件生产入口：`publish_async_event(...)`  
消费端：`event_worker.py`（消费 Redis 队列并写入 `operation_logs`，用于审计与答辩演示）

## 3. 配置项（新增）

在 `backend/app/config.py` 与 `.env.example` 已增加：

1. `ENABLE_ASYNC_EVENTS`
2. `ASYNC_EVENT_QUEUE_NAME`
3. `ASYNC_EVENT_BLOCK_TIMEOUT_SECONDS`

同时补齐了数据库 URI 回退逻辑：MySQL 配置不完整时自动回退到 `sqlite:///lab_dev.db`。

## 4. 一键启动阶段 C 环境

在项目根目录执行：

```bash
docker compose -f infra/docker/docker-compose.stage-c.yml up -d --build
```

默认访问入口：

1. API 网关：`http://127.0.0.1:8080`
2. 健康检查：`http://127.0.0.1:8080/api/health`

## 5. 初始化数据（首次）

容器首次启动后，执行：

```bash
docker compose -f infra/docker/docker-compose.stage-c.yml exec backend1 python scripts/seed.py
```

## 6. 阶段 C 验证建议

1. 使用 `http://127.0.0.1:8080/api/*` 执行业务请求，观察请求可在 `backend1/backend2` 分担。
2. 提交预约后，查看 `event-worker` 日志确认异步事件被消费。
3. 复跑压测脚本，重点验证“同窗只成功 1 条”与 5xx 控制情况。
