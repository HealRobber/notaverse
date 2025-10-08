#!/bin/bash

set -e

# 기존 entrypoint 유지 (WordPress 원본)
echo "Copying dynamic wp-config.php..."
cp /var/www/html/wp-config-template.php /var/www/html/wp-config.php
cp /var/www/html/.htaccess-template /var/www/html/.htaccess
cp /var/www/html/force-home.php /var/www/html/wp-content/mu-plugins/force-home.php
cp /var/www/html/feed-rss2.php /var/www/html/wp-content/themes/personal-resume-portfolio/feed-rss2.php
cp /var/www/html/fix-feed-rss2.php /var/www/html/wp-content/mu-plugins/fix-feed-rss2.php
# rm -rf wp-config-template.php .htaccess-template orce-home.php feed-rss2.php fix-feed-rss2.php

# 기존 entrypoint 실행
exec docker-entrypoint.sh apache2-foreground
