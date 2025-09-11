-- 여기서는 "클러스터 전역 롤/유저"를 만들고, 현재 DB(content_automation)에 대한 권한만 부여합니다.
-- CREATE DATABASE 없음, \connect 없음, dblink 없음.

-- 롤/유저
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='app_admin') THEN
    CREATE ROLE app_admin NOINHERIT;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='content_readonly') THEN
    CREATE ROLE content_readonly NOINHERIT;
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='app_api') THEN
    CREATE USER app_api PASSWORD 'app_api_password';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='app_viewer') THEN
    CREATE USER app_viewer PASSWORD 'app_viewer_password';
  END IF;
END $$;

GRANT app_admin TO app_api;
GRANT content_readonly TO app_viewer;

-- 스키마 생성 및 기본 권한 정책
CREATE SCHEMA IF NOT EXISTS content AUTHORIZATION postgres;

ALTER DEFAULT PRIVILEGES IN SCHEMA content GRANT USAGE, SELECT ON SEQUENCES TO content_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA content GRANT SELECT ON TABLES TO content_readonly;

ALTER DEFAULT PRIVILEGES IN SCHEMA content GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO app_admin;
ALTER DEFAULT PRIVILEGES IN SCHEMA content GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO app_admin;

-- (선택) 접속 시 search_path
ALTER ROLE app_api IN DATABASE content_automation SET search_path = content, public;
ALTER ROLE app_viewer IN DATABASE content_automation SET search_path = content, public;
