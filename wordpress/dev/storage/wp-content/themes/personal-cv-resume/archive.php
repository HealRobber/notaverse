<?php
/**
 * The template for displaying archive pages
 *
 * @link https://developer.wordpress.org/themes/basics/template-hierarchy/
 *
 * @package Personal_CV_Resume
 */

get_header();

$layout = 'full-container';
/**
* Hook - personal_cv_resume_container_wrap_start 	
*
* @hooked personal_cv_resume_container_wrap_start	- 5
*/
 do_action( 'personal_cv_resume_container_wrap_start',  esc_attr( $layout ) );

	if ( have_posts() ) :

		?>
		<header class="page-header">
			<?php
			the_archive_title( '<h1 class="page-title">', '</h1>' );
			the_archive_description( '<div class="archive-description">', '</div>' );
			?>
		</header><!-- .page-header -->
		<?php

		/* Start the Loop */
		while ( have_posts() ) :
			the_post();

			/*
			 * Include the Post-Type-specific template for the content.
			 * If you want to override this in a child theme, then include a file
			 * called content-___.php (where ___ is the Post Type name) and that will be used instead.
			 */
			get_template_part( 'template-parts/content', get_post_type() );

		endwhile;

		/**
		* Hook - personal_cv_resume_loop_navigation 	
		*
		* @hooked site_loop_navigation	- 10
		*/
		 do_action( 'personal_cv_resume_loop_navigation');

	else :

		get_template_part( 'template-parts/content', 'none' );

	endif;
		
/**
* Hook - personal_cv_resume_container_wrap_end	
*
* @hooked container_wrap_end - 999
*/
 do_action( 'personal_cv_resume_container_wrap_end',  esc_attr( $layout ) );
get_footer();