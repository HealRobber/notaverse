-- 사용할 데이터베이스를 선택
USE wordpress_manager;

-- images 테이블 생성
CREATE TABLE IF NOT EXISTS images (
    id INT AUTO_INCREMENT PRIMARY KEY,
    image_url VARCHAR(255) NOT NULL, 
    image_id INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- posts 테이블 생성
CREATE TABLE IF NOT EXISTS posts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    category_ids VARCHAR(255) NOT NULL,
    tag_ids VARCHAR(255) NOT NULL,
    featured_media_id INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- prompts 테이블 생성
CREATE TABLE IF NOT EXISTS prompts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    prompt TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- parameters 테이블 생성
CREATE TABLE IF NOT EXISTS parameters (
    id INT AUTO_INCREMENT PRIMARY KEY,
    parameter TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- pipelines 테이블 생성
CREATE TABLE IF NOT EXISTS pipelines (
    id INT AUTO_INCREMENT PRIMARY KEY,
    prompt_array TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- description 컬럼 추가
ALTER TABLE pipelines
  ADD COLUMN description TEXT NOT NULL DEFAULT '';

-- 4) 잡 큐(스케줄러가 넣고, 워커가 가져가서 실행)
CREATE TABLE IF NOT EXISTS content_jobs (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    job_type ENUM('PLAN_NEXT','WRITE_AND_POST') NOT NULL,
    payload JSON NOT NULL,                       -- { "series_id": 1, "episode_no": 3, ... }
    scheduled_at DATETIME NOT NULL,
    available_at DATETIME NOT NULL,              -- 락/재시도 backoff 후 재가용 시간
    started_at DATETIME NULL,
    finished_at DATETIME NULL,
    status ENUM('queued','running','done','failed') DEFAULT 'queued',
    attempts INT NOT NULL DEFAULT 0,
    max_attempts INT NOT NULL DEFAULT 3,
    last_error TEXT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    KEY idx_status_time (status, available_at, scheduled_at)
) ENGINE=InnoDB;

-- 5) posts <-> series 연결(선택): 편의 인덱스
ALTER TABLE posts
    ADD COLUMN series_id INT NULL,
    ADD COLUMN episode_no INT NULL,
    ADD KEY idx_posts_series (series_id, episode_no);

CREATE TABLE jobs (
  id            VARCHAR(64) PRIMARY KEY,
  name          VARCHAR(128) NOT NULL,
  func_key      VARCHAR(128) NOT NULL,   -- job_registry의 키
  cron_expr     VARCHAR(64)  NOT NULL,   -- crontab
  params_json   JSON         NULL,       -- MariaDB면 LONGTEXT JSON alias 허용
  enabled       TINYINT(1)   NOT NULL DEFAULT 1,
  coalesce      TINYINT(1)   NOT NULL DEFAULT 1,
  max_instances INT          NOT NULL DEFAULT 1,
  misfire_grace INT          NOT NULL DEFAULT 300,
  lock_key      VARCHAR(128) NULL,       -- 없으면 "lock:{id}" 사용
  version       BIGINT       NOT NULL DEFAULT 1,  -- 변경 시 +1
  updated_at    TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  created_at    TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE job_runs (
  id             BIGINT AUTO_INCREMENT PRIMARY KEY,
  job_id         VARCHAR(64) NOT NULL,
  scheduled_time DATETIME(6) NULL,
  start_time     DATETIME(6) NOT NULL,
  end_time       DATETIME(6) NULL,
  status         VARCHAR(32) NOT NULL,      -- queued|running|ok|skipped|error
  result_json    JSON        NULL,
  error_text     TEXT        NULL,
  INDEX idx_job_runs_jobid (job_id),
  CONSTRAINT fk_job_runs_job FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE
);