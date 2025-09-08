#!/bin/bash

set -e

# 기존 entrypoint 유지 (WordPress 원본)
echo "Copying dynamic wp-config.php..."
cp /var/www/html/wp-config-template.php /var/www/html/wp-config.php
cp /var/www/html/.htaccess-template /var/www/html/.htaccess

# 기존 entrypoint 실행
exec docker-entrypoint.sh apache2-foreground
