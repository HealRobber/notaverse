2<?php
/**
 * Theme RSS2 Feed Template Override
 * - 채널 <link>를 notaverse.org로 명시 고정
 * - 포스트 목록은 WP 쿼리 결과를 그대로 출력
 */
header('Content-Type: application/rss+xml; charset=' . get_option('blog_charset'), true);
echo '<?xml version="1.0" encoding="' . get_option('blog_charset') . '"?>' . "\n";
?>
<rss version="2.0"
    xmlns:content="http://purl.org/rss/1.0/modules/content/"
    xmlns:wfw="http://wellformedweb.org/CommentAPI/"
    xmlns:dc="http://purl.org/dc/elements/1.1/"
    xmlns:atom="http://www.w3.org/2005/Atom"
    xmlns:sy="http://purl.org/rss/1.0/modules/syndication/"
    xmlns:slash="http://purl.org/rss/1.0/modules/slash/"
    >
<channel>
    <title><?php bloginfo_rss('name'); ?></title>

    <!-- ★ 여기서 채널 <link>를 비www로 확정 -->
    <link><?php echo esc_url( home_url( '/' ) ); ?></link>

    <atom:link href="<?php self_link(); ?>" rel="self" type="application/rss+xml" />
    <description><?php bloginfo_rss('description'); ?></description>
    <lastBuildDate><?php echo mysql2date('r', get_lastpostmodified('GMT'), false); ?></lastBuildDate>
    <language><?php bloginfo_rss('language'); ?></language>
    <sy:updatePeriod><?php echo apply_filters('rss_update_period', 'hourly'); ?></sy:updatePeriod>
    <sy:updateFrequency><?php echo apply_filters('rss_update_frequency', '1'); ?></sy:updateFrequency>
<?php
/**
 * 피드 상단 훅 (다른 플러그인이 메타/태그 추가 가능)
 * 여기에서 중복 <link>를 주입하던 훅이 있었다면, 이제 이 템플릿이 우선합니다.
 */
do_action('rss2_head');

/** 포스트 목록 쿼리 (코어 기본과 유사) */
$rss_query = new WP_Query( apply_filters('feed_rss2_args', array(
    'post_type'           => 'post',
    'posts_per_rss'       => get_option('posts_per_rss'),
    'ignore_sticky_posts' => true
)));

if ( $rss_query->have_posts() ) :
    while ( $rss_query->have_posts() ) : $rss_query->the_post();
?>
    <item>
        <title><?php the_title_rss(); ?></title>
        <link><?php the_permalink_rss(); ?></link>
        <comments><?php comments_link_feed(); ?></comments>
        <pubDate><?php echo mysql2date('r', get_post_time('Y-m-d H:i:s', true), false); ?></pubDate>
        <dc:creator><![CDATA[<?php the_author(); ?>]]></dc:creator>
        <?php the_category_rss('rss2'); ?>
        <guid isPermaLink="false"><?php the_guid(); ?></guid>

        <?php if ( get_option('rss_use_excerpt') ) : ?>
            <description><![CDATA[<?php the_excerpt_rss(); ?>]]></description>
        <?php else : ?>
            <description><![CDATA[<?php the_excerpt_rss(); ?>]]></description>
            <?php if ( strlen( $GLOBALS['post']->post_content ) ) : ?>
                <content:encoded><![CDATA[<?php the_content_feed('rss2'); ?>]]></content:encoded>
            <?php endif; ?>
        <?php endif; ?>

        <?php rss_enclosure(); ?>
        <?php do_action('rss2_item'); ?>
    </item>
<?php
    endwhile;
    wp_reset_postdata();
endif;
?>
</channel>
</rss>
