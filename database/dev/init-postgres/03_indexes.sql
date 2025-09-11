SET search_path = content, public;

CREATE INDEX IF NOT EXISTS idx_topic_slug ON topic(slug);
CREATE INDEX IF NOT EXISTS idx_content_plan_schedule ON content_plan(planned_at, status);
CREATE INDEX IF NOT EXISTS idx_generation_job_status_time ON generation_job(status, scheduled_at NULLS LAST);
CREATE INDEX IF NOT EXISTS idx_publish_job_status_time ON publish_job(status, scheduled_at NULLS LAST);
CREATE INDEX IF NOT EXISTS idx_post_status_time ON post(status, updated_at DESC);
