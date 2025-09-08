<?php
/**
 * Personal CV Resume functions and definitions
 *
 * @link https://developer.wordpress.org/themes/basics/theme-functions/
 *
 * @package Personal_CV_Resume
 */

if ( ! defined( '_S_VERSION' ) ) {
	// Replace the version number of the theme on each release.
	define( '_S_VERSION', '1.0.3' );
}

/**
 * Sets up theme defaults and registers support for various WordPress features.
 *
 * Note that this function is hooked into the after_setup_theme hook, which
 * runs before the init hook. The init hook is too late for some features, such
 * as indicating support for post thumbnails.
 */
function personal_cv_resume_setup() {
	/*
	* Make theme available for translation.
	* Translations can be filed in the /languages/ directory.
	* If you're building a theme based on Personal CV Resume, use a find and replace
	* to change 'personal-cv-resume' to the name of your theme in all the template files.
	*/
	load_theme_textdomain( 'personal-cv-resume', get_template_directory() . '/languages' );

	// Add default posts and comments RSS feed links to head.
	add_theme_support( 'automatic-feed-links' );

	/*
	* Let WordPress manage the document title.
	* By adding theme support, we declare that this theme does not use a
	* hard-coded <title> tag in the document head, and expect WordPress to
	* provide it for us.
	*/
	add_theme_support( 'title-tag' );

	/*
	* Enable support for Post Thumbnails on posts and pages.
	*
	* @link https://developer.wordpress.org/themes/functionality/featured-images-post-thumbnails/
	*/
	add_theme_support( 'post-thumbnails' );

	// This theme uses wp_nav_menu() in one location.
	register_nav_menus(
		array(
			'menu-1' => esc_html__( 'Primary', 'personal-cv-resume' ),
		)
	);

	/*
		* Switch default core markup for search form, comment form, and comments
		* to output valid HTML5.
		*/
	add_theme_support(
		'html5',
		array(
			'search-form',
			'comment-form',
			'comment-list',
			'gallery',
			'caption',
			'style',
			'script',
		)
	);

	// Set up the WordPress core custom background feature.
	add_theme_support(
		'custom-background',
		apply_filters(
			'personal_cv_resume_custom_background_args',
			array(
				'default-color' => 'ffffff',
				'default-image' => '',
			)
		)
	);
	// Add theme support for selective refresh for widgets.
	//add_theme_support( 'customize-selective-refresh-widgets' );

	/**
	 * Add support for core custom logo.
	 *
	 * @link https://codex.wordpress.org/Theme_Logo
	 */
	add_theme_support(
		'custom-logo',
		array(
			'height'      => 250,
			'width'       => 250,
			'flex-width'  => true,
			'flex-height' => true,
		)
	);
	/*
	* Enable support for Post Formats.
	* See https://developer.wordpress.org/themes/functionality/post-formats/
	*/
	add_theme_support( 'post-formats', array(
		'image',
		'video',
		'gallery',
		'audio',
		'quote'
	) );

	add_theme_support( 'custom-logo', array(
	'height'               => 200,
	'width'                => 200,
	'flex-height'          => true,
	'flex-width'           => true,
	'header-text'          => array( '', '' ),
	
	) );

	add_theme_support(
		'custom-header',
		apply_filters(
			'personal_cv_resume_custom_header_args',
			array(
				'default-image' => get_template_directory_uri() . '/assets/image/custom-header.jpg',
				'default-text-color' => '000000',
				'width'              => 1000,
				'height'             => 250,
				'flex-height'        => true,
				'wp-head-callback'   => 'personal_cv_resume_header_style',
			)
		)
	);

	register_default_headers( array(
		'default-image' => array(
		'url' => '%s/assets/image/custom-header.jpg',
		'thumbnail_url' => '%s/assets/image/custom-header.jpg',
		'description' => esc_html__( 'Default Header Image', 'personal-cv-resume' ),
		),
	));

	add_theme_support("responsive-embeds");
	add_theme_support( "wp-block-styles" );
	add_theme_support( "align-wide" );

	if ( is_customize_preview() ) {
		require get_template_directory() . '/inc/starter-content.php'; // phpcs:ignore WPThemeReview.CoreFunctionality.FileInclude.FileIncludeFound
		add_theme_support( 'starter-content', personal_cv_resume_get_starter_content() );
	}
	
}
add_action( 'after_setup_theme', 'personal_cv_resume_setup' );

/**
 * Set the content width in pixels, based on the theme's design and stylesheet.
 *
 * Priority 0 to make it available to lower priority callbacks.
 *
 * @global int $content_width
 */
function personal_cv_resume_content_width() {
	$GLOBALS['content_width'] = apply_filters( 'personal_cv_resume_content_width', 640 );
}
add_action( 'after_setup_theme', 'personal_cv_resume_content_width', 0 );

/**
 * Register widget area.
 *
 * @link https://developer.wordpress.org/themes/functionality/sidebars/#registering-a-sidebar
 */
function personal_cv_resume_widgets_init() {
	register_sidebar(
		array(
			'name'          => esc_html__( 'Fly Sidebar', 'personal-cv-resume' ),
			'id'            => 'sidebar-1',
			'description'   => esc_html__( 'Add widgets here.', 'personal-cv-resume' ),
			'before_widget' => '<section id="%1$s" class="widget %2$s">',
			'after_widget'  => '</section>',
			'before_title'  => '<h3 class="widget-title"><span>',
			'after_title'   => '</span></h3>',
		)
	);
}
add_action( 'widgets_init', 'personal_cv_resume_widgets_init' );

/**
 * Enqueue scripts and styles.
 */
function personal_cv_resume_scripts() {
	/* vendor css*/
	wp_enqueue_style( 'google-font', 'https://fonts.googleapis.com/css?family=K2D:300,400,500,600,700|Roboto:400,500,700|Jost:400,500,700&display=swap' );

	wp_enqueue_style( 'fontawesome', get_template_directory_uri() . '/vendors/font-awesome/css/all.css', array(), '4.7' );
	
	wp_enqueue_style( 'bootstrap', get_template_directory_uri() . '/vendors/bootstrap/css/bootstrap.css', array(), '4.0.0' );
	
	wp_enqueue_style( 'fancybox', get_template_directory_uri() . '/vendors/fancybox/jquery.fancybox.css', array(), '3.5.6' );

	wp_enqueue_style( 'owl-carousel', get_template_directory_uri() . '/vendors/owl-carousel/assets/animate.css', array(), '3.5.6' );

	wp_enqueue_style( 'owl-animate', get_template_directory_uri() . '/vendors/owl-carousel/assets/owl.carousel.css', array(), '3.5.6' );

	wp_enqueue_style( 'aos-next', get_template_directory_uri() . '/vendors/aos-next/aos.css');
	
	wp_enqueue_style( 'personal-cv-resume-css', get_template_directory_uri() . '/assets/css/personal-cv-resume.css', array(), '1.0.0' );

	
	wp_enqueue_style( 'personal-cv-resume-style', get_stylesheet_uri(), array('dashicons') );
	
	
	
	/* vendor js*/
	wp_enqueue_script( 'bootstrap-js', get_template_directory_uri() . '/vendors/bootstrap/js/bootstrap.js', array('jquery'), '20151215', true  );

	wp_enqueue_script( 'fancybox-js', get_template_directory_uri() . '/vendors/fancybox/jquery.fancybox.js', array(), '', true  );
	
	wp_enqueue_script( 'owl-carousel-js', get_template_directory_uri() . '/vendors/owl-carousel/owl.carousel.js', array(), '', true  );

	wp_enqueue_script( 'aos-next-js', get_template_directory_uri() . '/vendors/aos-next/aos.js', array(), '', true );

	wp_enqueue_script( 'slimscroll', get_template_directory_uri() . '/vendors/slimscroll/jquery.slimscroll.js', array(), '', true );
	
	wp_enqueue_script( 'personal-cv-resume-js', get_template_directory_uri() . '/assets/js/personal-cv-resume.js', array(), _S_VERSION, true );

	if ( is_singular() && comments_open() && get_option( 'thread_comments' ) ) {
		wp_enqueue_script( 'comment-reply' );
	}
}
add_action( 'wp_enqueue_scripts', 'personal_cv_resume_scripts' );

/**
 * Sample implementation of the Custom Header feature
 *
 * You can add an optional custom header image to header.php like so ...
 *
	<?php the_header_image_tag(); ?>
 *
 * @link https://developer.wordpress.org/themes/functionality/custom-headers/
 *
 * @package Personal_CV_Resume
 */


if ( ! function_exists( 'personal_cv_resume_header_style' ) ) :
	/**
	 * Styles the header image and text displayed on the blog.
	 *
	 * @see personal_cv_resume_custom_header_setup().
	 */
	function personal_cv_resume_header_style() {
		$header_text_color = get_header_textcolor();

		/*
		 * If no custom options for text are set, let's bail.
		 * get_header_textcolor() options: Any hex value, 'blank' to hide text. Default: add_theme_support( 'custom-header' ).
		 */
		if ( get_theme_support( 'custom-header', 'default-text-color' ) === $header_text_color ) {
			return;
		}

		// If we get this far, we have custom styles. Let's do this.
		?>
		<style type="text/css">
		<?php
		// Has the text been hidden?
		if ( ! display_header_text() ) :
			?>
			.site-title,
			.site-description {
				position: absolute;
				clip: rect(1px, 1px, 1px, 1px);
				}
			<?php
			// If the user has set a custom color for the text use that.
		else :
			?>
			.site-title a,
			.site-description {
				color: #<?php echo esc_attr( $header_text_color ); ?>;
			}
		<?php endif; ?>
		</style>
		<?php
	}
endif;

// Include custom style editor (TinyMCE visual editor)
function personal_cv_resume_editor_styles() {
    add_editor_style( 'assets/css/editor-style.css' );
}
add_action( 'admin_init', 'personal_cv_resume_editor_styles' );