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


-- 확장을 위한 table 생성 추가
-- 1) 주제(선택): 자유주제면 생략해도 됨
CREATE TABLE IF NOT EXISTS topics (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_topics_name (name)
);

-- 2) 연재 정의
CREATE TABLE IF NOT EXISTS series (
    id INT AUTO_INCREMENT PRIMARY KEY,
    topic_id INT NULL,
    title VARCHAR(255) NOT NULL,                 -- 연재 제목(예: "AI 주간 이슈")
    seed_topic VARCHAR(255) NOT NULL,            -- 최초 주제(예: "생성형 AI 최신 동향")
    pipeline_id INT NOT NULL,                    -- 사용할 파이프라인 ID
    cadence VARCHAR(64) NOT NULL,                -- 발행 주기 표현(예: "DAILY@09:30", "CRON:0 9 * * *")
    next_run_at DATETIME NOT NULL,               -- 다음 실행 시각(Asia/Seoul 기준으로 계산해 저장)
    status ENUM('active','paused') DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (topic_id) REFERENCES topics(id)
) ENGINE=InnoDB;

-- 3) 연재 회차(에피소드)
CREATE TABLE IF NOT EXISTS series_episodes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    series_id INT NOT NULL,
    episode_no INT NOT NULL,                     -- 1, 2, 3 ...
    planned_title VARCHAR(255) NOT NULL,         -- 생성 전 계획된 제목(아웃라인에서 뽑음)
    planned_outline TEXT,                        -- 아웃라인 또는 키포인트
    post_id INT NULL,                            -- 게시 성공 시 posts.id 연결
    summary TEXT NULL,                           -- 발행 후 요약(다음 회차 생성에 활용)
    status ENUM('planned','posting','posted','failed') DEFAULT 'planned',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_series_episode (series_id, episode_no),
    FOREIGN KEY (series_id) REFERENCES series(id),
    FOREIGN KEY (post_id) REFERENCES posts(id)
) ENGINE=InnoDB;

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