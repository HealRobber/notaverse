<?php
/**
 * The template for displaying all pages
 *
 * This is the template that displays all pages by default.
 * Please note that this is the WordPress construct of pages
 * and that other 'pages' on your WordPress site may use a
 * different template.
 *
 * @link https://developer.wordpress.org/themes/basics/template-hierarchy/
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

			get_template_part( 'template-parts/content', 'page' );

		endwhile; // End of the loop.

        wp_link_pages( array(
            'before' => '<div class="page-links">' . esc_html__( 'Pages:', 'personal-cv-resume' ),
            'after'  => '</div>',
        ) );
		?>

<?php
/**
* Hook - container_wrap_end 		- 999
*
* @hooked personal_cv_resume_container_wrap_end
*/
do_action( 'personal_cv_resume_container_wrap_end', esc_attr( $layout ));
get_footer();
