-- MySQL migration: add user avatar and laboratory photos fields
-- Date: 2026-04-15

ALTER TABLE users
  ADD COLUMN IF NOT EXISTS avatar_url VARCHAR(500) NULL COMMENT '用户头像 URL' AFTER email;

ALTER TABLE laboratories
  ADD COLUMN IF NOT EXISTS photos TEXT NULL COMMENT '实验室照片 JSON 数组字符串' AFTER description;

UPDATE laboratories
SET photos = '[]'
WHERE photos IS NULL OR photos = '';
