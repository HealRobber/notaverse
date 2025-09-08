<?php
/**
 * Implement the Custom Header feature.
 */
require get_template_directory() . '/inc/theme-core.php';


/**
 * Functions which enhance the theme by hooking into WordPress.
 */
require get_template_directory() . '/inc/template-functions.php';

/**
 * Implement the Custom Header feature.
 */
require get_template_directory() . '/class/class-header.php';

/**
 * Implement the Custom Header feature.
 */
require get_template_directory() . '/class/class-body.php';

/**
 * Implement the Custom Header feature.
 */
require get_template_directory() . '/class/class-footer.php';

/**
 * Implement the Custom Header feature.
 */
require get_template_directory() . '/class/class-template-tags.php';
require get_template_directory() . '/class/class-post-related.php';

/**
 * Load Jetpack compatibility file.
 */
if ( defined( 'JETPACK__VERSION' ) ) {
    require get_template_directory() . '/inc/jetpack.php';
}

/**
* Implement the theme Layout.
*/
require get_template_directory() . '/inc/pro/admin-page.php';

/**
 * Customizer additions.
 */

require_once( trailingslashit( get_template_directory() ) . '/inc/customizer/class-customize.php' );

/**
* TGM Plugins
*/
require get_template_directory() . '/inc/tgm/recommended-plugins.php';