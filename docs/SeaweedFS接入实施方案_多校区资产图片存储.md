# SeaweedFS 接入实施方案（多校区资产图片存储）

## 1. 目标
1. 将资产图片从本地裸目录升级为对象存储。  
2. 每个校区独立部署 SeaweedFS，满足“本地存储、分布式自治”。  
3. 中心侧仅汇总图片元数据，不汇聚原始图片文件。  

---

## 2. 推荐部署拓扑
1. 校区A：`master-a + volume-a + filer-a`。  
2. 校区B：`master-b + volume-b + filer-b`。  
3. 校区C：`master-c + volume-c + filer-c`。  
4. 中心服务不存图，只保存各校区图片元数据与访问地址。  

> 毕设阶段可先每校区单机部署一套，后续再扩展 volume 节点。

---

## 3. 数据模型改造建议
现有 `asset_photo`（或新增表）建议字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | bigint | 主键 |
| `asset_id` | bigint | 资产ID |
| `campus_id` | bigint | 校区ID |
| `storage_provider` | varchar(32) | 固定 `seaweedfs` |
| `bucket` | varchar(64) | 逻辑桶，如 `assets-a` |
| `file_id` | varchar(128) | SeaweedFS 文件标识 |
| `filer_url` | varchar(512) | 文件访问URL |
| `sha256` | varchar(64) | 去重与校验 |
| `file_size` | bigint | 文件大小 |
| `mime_type` | varchar(64) | 文件类型 |
| `created_at` | datetime | 创建时间 |

---

## 4. 接口改造建议
## 4.1 上传接口
`POST /api/assets/photos/upload`
1. 参数：`asset_id` + `file`。  
2. 流程：鉴权 -> 校验图片 -> 上传到本校区 SeaweedFS -> 保存元数据 -> 返回 URL。  

## 4.2 查询接口
`GET /api/assets/{asset_id}/photos`
1. 返回图片元数据列表。  
2. 可返回签名URL或受控代理URL。  

## 4.3 删除接口（可选）
`DELETE /api/assets/photos/{photo_id}`
1. 逻辑删除元数据。  
2. 异步清理 SeaweedFS 文件。  

---

## 5. 后端实现落点（按你当前 Flask 项目）
1. 新增服务：`backend/app/services/storage_service.py`（封装 SeaweedFS 上传/删除）。  
2. 新增配置：`backend/app/config.py` 增加校区级 `SEAWEEDFS_FILER_URL`。  
3. 资产接口层调用 `storage_service`，不直接写磁盘。  
4. 原 `/uploads/*` 可保留兼容期，逐步迁移。  

---

## 6. 配置示例（环境变量）
```env
SEAWEEDFS_ENABLED=1
SEAWEEDFS_TIMEOUT_SECONDS=10

# 校区A
SEAWEEDFS_CAMPUS_1_FILER_URL=http://campus-a-filer:8888
SEAWEEDFS_CAMPUS_1_COLLECTION=assets-a

# 校区B
SEAWEEDFS_CAMPUS_2_FILER_URL=http://campus-b-filer:8888
SEAWEEDFS_CAMPUS_2_COLLECTION=assets-b
```

---

## 7. 上传流程（事务边界建议）
1. 先上传图片到 SeaweedFS，拿到 `file_id/url/hash`。  
2. 再写数据库元数据（与资产入库事务可同事务或补偿事务）。  
3. 数据库写失败时，触发异步补偿删除孤儿文件。  

---

## 8. 并发与可靠性建议
1. 上传接口加幂等键，避免重复上传落多份。  
2. 对同一资产可做 `sha256` 去重。  
3. 失败重试与超时控制要分层：客户端重试 + 服务端重试。  
4. 建议记录 `trace_id`，用于答辩演示链路追踪。  

---

## 9. 渐进迁移步骤（建议一周内完成）
1. 第1步：落地 SeaweedFS 环境并联通测试。  
2. 第2步：新增 `storage_service` 和配置开关。  
3. 第3步：资产图片上传接口切到 SeaweedFS。  
4. 第4步：补充迁移脚本，把历史 `/uploads/assets` 元数据迁移到新表。  
5. 第5步：压测上传并验证故障恢复与元数据一致性。  

---

## 10. 论文写作可直接引用的一句话
本文采用校区级 SeaweedFS 对象存储实现设备影像本地化自治，中心节点仅汇总图片元数据与统计信息，从而在满足分布式资源治理的同时降低跨校区存储耦合与带宽成本。

