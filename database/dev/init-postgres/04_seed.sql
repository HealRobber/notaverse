SET search_path = content, public;

INSERT INTO kv_store (k, v) VALUES
 ('daily_quota_per_channel', '{"WORDPRESS":3}'),
 ('publish_window', '{"start_hour":9,"end_hour":21}'),
 ('retry_max', '3'),
 ('max_parallel_jobs', '4'),
 ('min_series_gap_days', '2'),
 ('require_manual_review', 'false')
ON CONFLICT (k) DO NOTHING;

INSERT INTO channel(type, name, credentials, enabled) VALUES
 ('WORDPRESS','My WP Blog','{"base_url":"http://wordpress","username":"itengz","app_password":"ciAE 7Zb5 NeMJ QNbC vSo6 dqAC"}', true)
ON CONFLICT DO NOTHING;
