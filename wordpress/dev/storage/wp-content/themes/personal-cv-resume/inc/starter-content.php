<?php
/**
 * Personal CV Resume Starter Content
 *
 * @link https://make.wordpress.org/core/2016/11/30/starter-content-for-themes-in-4-7/
 *
 * @package personal-cv-resume
 * @subpackage personal-cv-resume
 * @since personal-cv-resume 1.0.0
 */

/**
 * Function to return the array of starter content for the theme.
 *
 * Passes it through the `personal-cv-resume_get_starter_content` filter before returning.
 *
 * @since personal-cv-resume 1.0.0
 *
 * @return array A filtered array of args for the starter_content.
 */

function personal_cv_resume_get_starter_content() {

	// Define and register starter content to showcase the theme on new sites.
	$starter_content = array(
		'widgets'     => array(
			// Place three core-defined widgets in the sidebar area.
			'sidebar-1'  => array(
				'search',
				'text_about',
				'text_business_info',
			),
			
		),
		
	);

	/**
	 * Filters personal-cv-resume array of starter content.
	 *
	 * @since personal-cv-resume 1.0.0
	 *
	 * @param array $starter_content Array of starter content.
	 */
	return apply_filters( 'personal_cv_resume_get_starter_content', $starter_content );
}

