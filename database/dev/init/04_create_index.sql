-- 사용할 데이터베이스를 선택
USE wordpress_manager;

-- 이미지 URL에 인덱스 추가
CREATE INDEX idx_image_url ON images (image_url);
