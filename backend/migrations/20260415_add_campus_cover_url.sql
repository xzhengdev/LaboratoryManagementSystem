ALTER TABLE campuses
  ADD COLUMN cover_url VARCHAR(500) NULL COMMENT '校区封面图片URL' AFTER description;
