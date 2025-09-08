<?php
// Exit if accessed directly
if ( !defined( 'ABSPATH' ) ) exit;

// BEGIN ENQUEUE PARENT ACTION
function personal_resume_portfolio_theme_setup(){

    // Make theme available for translation.
    load_theme_textdomain( 'personal-resume-portfolio', get_stylesheet_directory_uri() . '/languages' );
    
    add_theme_support( 'custom-header', apply_filters( 'personal_resume_portfolio_header_args', array(
        'default-image' => get_stylesheet_directory_uri() . '/assets/images/header-background.jpg',
        'default-text-color'     => '000000',
        'width'                  => 1000,
        'height'                 => 350,
        'flex-height'            => true,
        'wp-head-callback'       => 'personal_cv_resume_header_style',
    ) ) );
    
    register_default_headers( array(
        'default-image' => array(
        'url' => '%s/assets/images/header-background.jpg',
        'thumbnail_url' => '%s/assets/images/header-background.jpg',
        'description' => esc_html__( 'Default Header Image', 'personal-resume-portfolio' ),
        ),
    ));

}
add_action( 'after_setup_theme', 'personal_resume_portfolio_theme_setup' );


if ( !function_exists( 'personal_resume_portfolio_cfg_locale_css' ) ):
    function personal_resume_portfolio_cfg_locale_css( $uri ){
        if ( empty( $uri ) && is_rtl() && file_exists( get_template_directory() . '/rtl.css' ) )
            $uri = get_template_directory_uri() . '/rtl.css';
        return $uri;
    }
endif;
add_filter( 'locale_stylesheet_uri', 'personal_resume_portfolio_cfg_locale_css' );

if ( !function_exists( 'personal_resume_portfolio_cfg_parent_css' ) ):
    function personal_resume_portfolio_cfg_parent_css() {
         wp_enqueue_style( 'Roboto+Condensed', '//fonts.googleapis.com/css2?family=Roboto+Condensed:ital,wght@0,100..900;1,100..900&display=swap' );
         
        wp_enqueue_style( 'personal_resume_portfolio_parent', trailingslashit( get_template_directory_uri() ) . 'style.css', array( 'fontawesome','bootstrap','fancybox','owl-carousel','owl-animate','aos-next','personal-cv-resume-css' ) );

        wp_enqueue_script( 'sticky-sidebar-js', get_theme_file_uri( '/assets/js/sticky-sidebar.js'),  array(), '', true);

        wp_enqueue_script( 'personal-resume-portfolio', get_theme_file_uri( '/assets/js/personal-resume-portfolio.js'),  array('jquery','jquery-masonry'),  wp_get_theme()->get('Version'), true);
    }
endif;
add_action( 'wp_enqueue_scripts', 'personal_resume_portfolio_cfg_parent_css', 10 );


if( !function_exists('personal_resume_portfolio_disable_from_parent') ):
    add_action('init','personal_resume_portfolio_disable_from_parent',10);
    function personal_resume_portfolio_disable_from_parent(){
      global $personal_cv_resume_header_layout;
      remove_action('personal_cv_resume_site_header', array( $personal_cv_resume_header_layout, 'site_skip_to_content' ), 5 );
      remove_action('personal_cv_resume_site_header', array( $personal_cv_resume_header_layout, 'site_get_sidebar' ), 999 );
      add_action('personal_resume_portfolio_sidebar', array( $personal_cv_resume_header_layout, 'site_get_sidebar' ), 20);
      global $personal_cv_resume_post_related;
      remove_action( 'personal_cv_resume_site_content_type', array( $personal_cv_resume_post_related,'site_content_type' ), 30 ); 
      remove_action( 'personal_cv_resume_site_content_type', array( $personal_cv_resume_post_related,'site_loop_heading' ), 20 ); 
    }
    
endif;
if( !function_exists( 'personal_resume_portfolio_skip_to_content' )):
    function personal_resume_portfolio_skip_to_content(){
        echo '<a class="skip-link screen-reader-text" href="#primary">'. esc_html__( 'Skip to content', 'personal-resume-portfolio' ) .'</a>';
    }
    add_action('wp_body_open', 'personal_resume_portfolio_skip_to_content', 5 );
endif;

class PersonalResumePortfolio_Customizer {
    public static function init() {
        add_action('customize_register', [__CLASS__, 'register_options']);
    }

    public static function register_options($wp_customize) {
        // Section
        $wp_customize->add_section('personal_res_port_content_display', [
            'title'    => __('Content Display Options', 'personal-resume-portfolio'),
            'priority' => 30,
            'description' => __('These options control how posts are displayed on blog, archive, and category pages.', 'personal-resume-portfolio'),
        ]);
        // Show full content or excerpt
        $wp_customize->add_setting('personal_res_port_show_full_content', [
            'default'   => true,
            'transport' => 'refresh',
            'sanitize_callback' => 'personal_resume_portfolio_sanitize_checkbox',
        ]);
        $wp_customize->add_control('personal_res_port_show_full_content', [
            'label'    => __('Show post excerpt?', 'personal-resume-portfolio'),
            'section'  => 'personal_res_port_content_display',
            'type'     => 'checkbox',
        ]);

        // Show author
        $wp_customize->add_setting('personal_res_port_show_author', [
            'default'   => true,
            'transport' => 'refresh',
            'sanitize_callback' => 'personal_resume_portfolio_sanitize_checkbox',
        ]);
        $wp_customize->add_control('personal_res_port_show_author', [
            'label'    => __('Show author name', 'personal-resume-portfolio'),
            'section'  => 'personal_res_port_content_display',
            'type'     => 'checkbox',
        ]);
        // Show date
        $wp_customize->add_setting('personal_res_port_show_date', [
            'default'   => false,
            'transport' => 'refresh',
            'sanitize_callback' => 'personal_resume_portfolio_sanitize_checkbox',
        ]);
        $wp_customize->add_control('personal_res_port_show_date', [
            'label'    => __('Show post date', 'personal-resume-portfolio'),
            'section'  => 'personal_res_port_content_display',
            'type'     => 'checkbox',
        ]);
        // Show categories
        $wp_customize->add_setting('personal_res_port_show_category', [
            'default'   => false,
            'transport' => 'refresh',
            'sanitize_callback' => 'personal_resume_portfolio_sanitize_checkbox',
        ]);
        $wp_customize->add_control('personal_res_port_show_category', [
            'label'    => __('Show categories', 'personal-resume-portfolio'),
            'section'  => 'personal_res_port_content_display',
            'type'     => 'checkbox',
        ]);
        // Show comment count
        $wp_customize->add_setting('personal_res_port_show_comments', [
            'default'   => false,
            'transport' => 'refresh',
            'sanitize_callback' => 'personal_resume_portfolio_sanitize_checkbox',
        ]);
        $wp_customize->add_control('personal_res_port_show_comments', [
            'label'    => __('Show comment count', 'personal-resume-portfolio'),
            'section'  => 'personal_res_port_content_display',
            'type'     => 'checkbox',
        ]);
    }
}

// Initialize the class
PersonalResumePortfolio_Customizer::init();

if( !function_exists('personal_resume_portfolio_sanitize_checkbox') ):
function personal_resume_portfolio_sanitize_checkbox( $checked ) {
    return ( ( isset( $checked ) && true === $checked ) ? true : false );
}
endif;

if( !function_exists('personal_resume_portfolio_content_type') ):
    function personal_resume_portfolio_content_type(){
        echo '<div class="content-wrap">';
            if( ! is_single() && !is_page()):
                if (get_theme_mod('personal_res_port_show_full_content', true)) :
                 echo wp_kses_post( get_the_excerpt() );
                endif;
            else:
                the_content();
            endif;
        echo '</div>';
    }
add_action( 'personal_cv_resume_site_content_type', 'personal_resume_portfolio_content_type', 30 );    
endif;
if( !function_exists('personal_resume_portfolio_post_title') ):
    function personal_resume_portfolio_post_title(){
        if ( is_singular() ) :
            the_title( '<h2 class="entry-title">', '</h2>' );
        else :
            the_title( '<h3 class="entry-title"><a href="' . esc_url( get_permalink() ) . '" rel="bookmark" >', '</a></h3>' );
        endif;
    }
add_action( 'personal_cv_resume_site_content_type', 'personal_resume_portfolio_post_title', 20 ); 
endif;