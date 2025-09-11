SET search_path = content, public;

-- Enums
DO $$ BEGIN CREATE TYPE job_status AS ENUM ('PENDING','RUNNING','SUCCEEDED','FAILED','CANCELED','RETRY'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE TYPE plan_status AS ENUM ('DRAFT','SCHEDULED','IN_PROGRESS','COMPLETED','CANCELED'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE TYPE post_status AS ENUM ('DRAFT','REVIEW','READY','PUBLISHED','ARCHIVED'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE TYPE channel_type AS ENUM ('WORDPRESS','MEDIUM','GHOST','CUSTOM_WEBHOOK'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE TYPE step_type AS ENUM ('DRAFTING','FACT_CHECK','REWRITE','IMAGE_GEN','SEO','SUMMARY'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE TYPE priority_level AS ENUM ('LOW','NORMAL','HIGH','CRITICAL'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- topic / series / plan
CREATE TABLE IF NOT EXISTS topic(
  id BIGSERIAL PRIMARY KEY,
  slug TEXT UNIQUE NOT NULL,
  title TEXT NOT NULL,
  description TEXT,
  lang TEXT DEFAULT 'ko',
  disabled BOOLEAN DEFAULT false,
  followup_locked BOOLEAN DEFAULT false,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS topic_edge(
  from_topic_id BIGINT REFERENCES topic(id) ON DELETE CASCADE,
  to_topic_id   BIGINT REFERENCES topic(id) ON DELETE CASCADE,
  relation TEXT DEFAULT 'related',
  weight NUMERIC(5,4) DEFAULT 0.0,
  PRIMARY KEY(from_topic_id, to_topic_id)
);

CREATE TABLE IF NOT EXISTS series(
  id BIGSERIAL PRIMARY KEY,
  title TEXT NOT NULL,
  description TEXT,
  topic_id BIGINT REFERENCES topic(id) ON DELETE SET NULL,
  status TEXT DEFAULT 'ACTIVE',
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS content_plan(
  id BIGSERIAL PRIMARY KEY,
  topic_id BIGINT REFERENCES topic(id) ON DELETE SET NULL,
  series_id BIGINT REFERENCES series(id) ON DELETE SET NULL,
  title_hint TEXT,
  persona TEXT,
  target_channel channel_type[] DEFAULT ARRAY['WORDPRESS']::channel_type[],
  planned_at TIMESTAMPTZ,
  status plan_status DEFAULT 'DRAFT',
  priority priority_level DEFAULT 'NORMAL',
  meta JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- model/prompt/pipeline/steps
CREATE TABLE IF NOT EXISTS model_registry(
  id BIGSERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  provider TEXT NOT NULL,
  default_params JSONB DEFAULT '{}',
  enabled BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS prompt(
  id BIGSERIAL PRIMARY KEY,
  name TEXT UNIQUE NOT NULL,
  template TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS pipeline(
  id BIGSERIAL PRIMARY KEY,
  name TEXT UNIQUE NOT NULL,
  description TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS pipeline_step(
  id BIGSERIAL PRIMARY KEY,
  pipeline_id BIGINT REFERENCES pipeline(id) ON DELETE CASCADE,
  order_no INT NOT NULL,
  step step_type NOT NULL,
  prompt_id BIGINT REFERENCES prompt(id) ON DELETE SET NULL,
  model_id BIGINT REFERENCES model_registry(id) ON DELETE SET NULL,
  step_params JSONB DEFAULT '{}',
  UNIQUE(pipeline_id, order_no)
);

-- jobs / posts
CREATE TABLE IF NOT EXISTS generation_job(
  id BIGSERIAL PRIMARY KEY,
  plan_id BIGINT REFERENCES content_plan(id) ON DELETE CASCADE,
  pipeline_id BIGINT REFERENCES pipeline(id) ON DELETE SET NULL,
  step_id BIGINT REFERENCES pipeline_step(id) ON DELETE SET NULL,
  status job_status DEFAULT 'PENDING',
  attempts INT DEFAULT 0,
  priority priority_level DEFAULT 'NORMAL',
  scheduled_at TIMESTAMPTZ,
  started_at TIMESTAMPTZ,
  finished_at TIMESTAMPTZ,
  input_payload JSONB DEFAULT '{}',
  output_payload JSONB DEFAULT '{}',
  error TEXT,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS post(
  id BIGSERIAL PRIMARY KEY,
  plan_id BIGINT REFERENCES content_plan(id) ON DELETE SET NULL,
  series_id BIGINT REFERENCES series(id) ON DELETE SET NULL,
  topic_id BIGINT REFERENCES topic(id) ON DELETE SET NULL,
  title TEXT,
  status post_status DEFAULT 'DRAFT',
  canonical_url TEXT,
  published_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS post_version(
  id BIGSERIAL PRIMARY KEY,
  post_id BIGINT REFERENCES post(id) ON DELETE CASCADE,
  v_no INT NOT NULL,
  body_markdown TEXT NOT NULL,
  summary TEXT,
  notes TEXT,
  created_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(post_id, v_no)
);

-- channel / publish / bindings / kv
CREATE TABLE IF NOT EXISTS channel(
  id BIGSERIAL PRIMARY KEY,
  type channel_type NOT NULL,
  name TEXT NOT NULL,
  credentials JSONB NOT NULL,
  enabled BOOLEAN DEFAULT true,
  extra JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS channel_binding(
  id BIGSERIAL PRIMARY KEY,
  channel_id BIGINT REFERENCES channel(id) ON DELETE CASCADE,
  post_id BIGINT REFERENCES post(id) ON DELETE CASCADE,
  external_id TEXT,
  url TEXT,
  created_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(channel_id, post_id)
);

CREATE TABLE IF NOT EXISTS publish_job(
  id BIGSERIAL PRIMARY KEY,
  channel_id BIGINT REFERENCES channel(id) ON DELETE CASCADE,
  post_id BIGINT REFERENCES post(id) ON DELETE CASCADE,
  status job_status DEFAULT 'PENDING',
  scheduled_at TIMESTAMPTZ,
  started_at TIMESTAMPTZ,
  finished_at TIMESTAMPTZ,
  error TEXT,
  payload JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS kv_store(
  k TEXT PRIMARY KEY,
  v JSONB NOT NULL,
  updated_at TIMESTAMPTZ DEFAULT now()
);
