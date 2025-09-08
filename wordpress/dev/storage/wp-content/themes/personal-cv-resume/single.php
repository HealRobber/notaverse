<?php
/**
 * The template for displaying all single posts
 *
 * @link https://developer.wordpress.org/themes/basics/template-hierarchy/#single-post
 *
 * @package Personal_CV_Resume
 */

get_header();

$layout = 'full-container';

/**
* Hook - container_wrap_start 		- 5
*
* @hooked personal_cv_resume_container_wrap_start
*/
 do_action( 'personal_cv_resume_container_wrap_start', esc_attr( $layout ));
?>
	

		<?php
		while ( have_posts() ) :
			the_post();

			get_template_part( 'template-parts/content', 'single' );

			/**
			* Hook - personal_cv_resume_site_footer
			*
			* @hooked personal_cv_resume_container_wrap_start
			*/
			do_action( 'personal_cv_resume_single_post_navigation');
			

			// If comments are open or we have at least one comment, load up the comment template.
			if ( comments_open() || get_comments_number() ) :
				comments_template();
			endif;

		endwhile; // End of the loop.
		?>

<?php
/**
* Hook - container_wrap_end 		- 999
*
* @hooked personal_cv_resume_container_wrap_end
*/
do_action( 'personal_cv_resume_container_wrap_end', esc_attr( $layout ));
get_footer();