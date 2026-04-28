-- 分布式改造阶段：资产管理、日报、文件元数据基础表
-- 说明：
-- 1) 建议先备份数据库
-- 2) SQLite/MySQL 都可参考执行，MySQL 可能需将 AUTOINCREMENT 改为 AUTO_INCREMENT

CREATE TABLE IF NOT EXISTS file_objects (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  campus_id INTEGER NOT NULL,
  biz_type VARCHAR(50) NOT NULL,
  biz_id INTEGER NULL,
  file_id VARCHAR(255) NOT NULL,
  original_name VARCHAR(255) NOT NULL,
  storage_backend VARCHAR(30) NOT NULL DEFAULT 'local',
  url VARCHAR(500) NOT NULL,
  mime_type VARCHAR(100) NULL,
  size INTEGER NOT NULL DEFAULT 0,
  sha256 VARCHAR(64) NOT NULL,
  created_by INTEGER NOT NULL,
  status VARCHAR(20) NOT NULL DEFAULT 'active',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_file_object_campus_biz ON file_objects(campus_id, biz_type, biz_id);
CREATE INDEX IF NOT EXISTS idx_file_object_file_id ON file_objects(file_id);

CREATE TABLE IF NOT EXISTS asset_budgets (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  campus_id INTEGER NOT NULL,
  total_amount DECIMAL(12,2) NOT NULL DEFAULT 0,
  locked_amount DECIMAL(12,2) NOT NULL DEFAULT 0,
  used_amount DECIMAL(12,2) NOT NULL DEFAULT 0,
  remark VARCHAR(255) NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT uq_asset_budget_campus UNIQUE (campus_id)
);

CREATE TABLE IF NOT EXISTS asset_purchase_requests (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  request_no VARCHAR(40) NOT NULL,
  campus_id INTEGER NOT NULL,
  lab_id INTEGER NULL,
  requester_id INTEGER NOT NULL,
  asset_name VARCHAR(100) NOT NULL,
  category VARCHAR(50) NOT NULL,
  quantity INTEGER NOT NULL DEFAULT 1,
  unit_price DECIMAL(12,2) NOT NULL,
  amount DECIMAL(12,2) NOT NULL,
  reason TEXT NULL,
  status VARCHAR(20) NOT NULL DEFAULT 'pending',
  reviewer_id INTEGER NULL,
  review_remark VARCHAR(255) NULL,
  reviewed_at DATETIME NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT uq_asset_request_no UNIQUE (request_no)
);
CREATE INDEX IF NOT EXISTS idx_asset_request_campus_status ON asset_purchase_requests(campus_id, status);

CREATE TABLE IF NOT EXISTS asset_budget_ledgers (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  campus_id INTEGER NOT NULL,
  request_id INTEGER NULL,
  op_type VARCHAR(30) NOT NULL,
  amount DECIMAL(12,2) NOT NULL,
  before_locked DECIMAL(12,2) NOT NULL,
  after_locked DECIMAL(12,2) NOT NULL,
  before_used DECIMAL(12,2) NOT NULL,
  after_used DECIMAL(12,2) NOT NULL,
  operator_id INTEGER NOT NULL,
  remark VARCHAR(255) NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_asset_budget_ledger_request ON asset_budget_ledgers(request_id);

CREATE TABLE IF NOT EXISTS asset_items (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  asset_code VARCHAR(40) NOT NULL,
  campus_id INTEGER NOT NULL,
  lab_id INTEGER NULL,
  request_id INTEGER NULL,
  asset_name VARCHAR(100) NOT NULL,
  category VARCHAR(50) NOT NULL,
  price DECIMAL(12,2) NOT NULL,
  status VARCHAR(20) NOT NULL DEFAULT 'in_use',
  description TEXT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT uq_asset_code UNIQUE (asset_code)
);
CREATE INDEX IF NOT EXISTS idx_asset_item_campus_status ON asset_items(campus_id, status);

CREATE TABLE IF NOT EXISTS lab_daily_reports (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  campus_id INTEGER NOT NULL,
  lab_id INTEGER NOT NULL,
  reporter_id INTEGER NOT NULL,
  report_date DATE NOT NULL,
  content TEXT NULL,
  status VARCHAR(20) NOT NULL DEFAULT 'pending',
  reviewer_id INTEGER NULL,
  review_remark VARCHAR(255) NULL,
  reviewed_at DATETIME NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_daily_report_campus_status ON lab_daily_reports(campus_id, status);
CREATE INDEX IF NOT EXISTS idx_daily_report_lab_date ON lab_daily_reports(lab_id, report_date);
