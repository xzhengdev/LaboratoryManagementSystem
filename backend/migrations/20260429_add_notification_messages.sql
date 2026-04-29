-- 分布式改造阶段：站内通知表（小程序消息提醒）
-- 说明：
-- 1) 建议先备份数据库
-- 2) SQLite/MySQL 都可参考执行，MySQL 可能需将 AUTOINCREMENT 改为 AUTO_INCREMENT

CREATE TABLE IF NOT EXISTS notification_messages (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  campus_id INTEGER NOT NULL,
  user_id INTEGER NOT NULL,
  title VARCHAR(100) NOT NULL,
  content VARCHAR(500) NOT NULL,
  level VARCHAR(20) NOT NULL DEFAULT 'info',
  biz_type VARCHAR(50) NOT NULL DEFAULT 'general',
  biz_id INTEGER NULL,
  is_read BOOLEAN NOT NULL DEFAULT 0,
  read_at DATETIME NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_notification_user_read ON notification_messages(user_id, is_read);
CREATE INDEX IF NOT EXISTS idx_notification_campus_biz ON notification_messages(campus_id, biz_type, biz_id);
