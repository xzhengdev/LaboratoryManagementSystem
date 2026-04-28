-- 说明：
-- 1) 建议在备份数据库后执行
-- 2) SQLite 可直接执行（CREATE INDEX IF NOT EXISTS 生效）
-- 3) MySQL 若不支持 IF NOT EXISTS，请改为手工判断后执行 ALTER TABLE ... ADD INDEX

-- 幂等记录表
CREATE TABLE IF NOT EXISTS idempotency_records (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  endpoint VARCHAR(64) NOT NULL,
  idempotency_key VARCHAR(128) NOT NULL,
  request_hash VARCHAR(64) NOT NULL,
  status VARCHAR(20) NOT NULL DEFAULT 'processing',
  response_payload TEXT NULL,
  reservation_id INTEGER NULL,
  http_status INTEGER NOT NULL DEFAULT 200,
  error_message VARCHAR(255) NULL,
  expires_at DATETIME NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT uq_idempotency_user_endpoint_key UNIQUE (user_id, endpoint, idempotency_key)
);

CREATE INDEX IF NOT EXISTS idx_idempotency_expires_at
  ON idempotency_records(expires_at);

-- 预约表高频查询索引
CREATE INDEX IF NOT EXISTS idx_reservation_lab_date_status
  ON reservations(lab_id, reservation_date, status);

CREATE INDEX IF NOT EXISTS idx_reservation_user_created_at
  ON reservations(user_id, created_at);

