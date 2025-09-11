-- 사용할 데이터베이스를 선택
USE wordpress_manager;

-- 1. 유저 생성
CREATE USER IF NOT EXISTS 'wordpress_admin'@'%' IDENTIFIED BY 'Djdldjqek!2';

-- 2. 특정 데이터베이스에 모든 권한 부여
GRANT ALL PRIVILEGES ON wordpress_manager.* TO 'wordpress_admin'@'%';

-- 3. 권한 적용
FLUSH PRIVILEGES;