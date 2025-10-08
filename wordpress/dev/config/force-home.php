<?php
/**
 * Plugin Name: Force Home/SiteURL (non-www)
 * Description: 홈/사이트 URL을 notaverse.org로 강제하고 RSS <link>도 비www로 고정합니다.
 */

// DB 조회 전에 우선 적용 (가장 강력)
add_filter('pre_option_home',    fn() => 'https://notaverse.org');
add_filter('pre_option_siteurl', fn() => 'https://notaverse.org');

// 혹시 다른 훅/테마가 url, home, wpurl을 건드려도 보정
add_filter('bloginfo_url', function($url, $show){
    if (in_array($show, ['url','home','wpurl'], true)) {
        $url = preg_replace('#^https?://www\.notaverse\.org#', 'https://notaverse.org', $url);
    }
    return $url;
}, 10, 2);

// RSS 채널에 <link>를 안전하게 주입/보정 (최우선 실행)
// 기본 템플릿이 <link>를 출력하더라도, 대부분의 리더는 첫 번째를 우선 사용합니다.
// add_action('rss2_head', function () {
//     echo "<link>https://notaverse.org/</link>\n";
// }, 1);
