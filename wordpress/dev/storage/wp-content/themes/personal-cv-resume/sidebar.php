<?php
/**
 * The sidebar containing the main widget area
 *
 * @link https://developer.wordpress.org/themes/basics/template-files/#template-partials
 *
 * @package Personal_CV_Resume
 */

if ( ! is_active_sidebar( 'sidebar-1' ) ) {
	return;
}
dynamic_sidebar( 'sidebar-1' )
?>

