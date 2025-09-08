<?php
/**
 * Template part for displaying results in search pages
 *
 * @link https://developer.wordpress.org/themes/basics/template-hierarchy/
 *
 * @package Personal_CV_Resume
 */

?>

<article id="post-<?php the_ID(); ?>" <?php post_class( array('content-post-wrap') ); ?> data-aos="fade-up">

 	 <?php
    /**
    * Hook - personal_cv_resume_posts_blog_media.
    *
    * @hooked personal_cv_resume_posts_formats_thumbnail - 10
    */
    do_action( 'personal_cv_resume_posts_blog_media' );
    ?>
    <div class="post">
    	
		<?php
        /**
        * Hook - personal-cv-resume_site_content_type.
        *
		* @hooked site_loop_heading - 10
        * @hooked render_meta_list	- 20
		* @hooked site_content_type - 30
        */
		
		$meta = array();
		
		
		if ( 'post' === get_post_type() ) :
				
			$meta = array( 'author', 'date','category' );

		endif;

		$meta  	 = apply_filters( 'personal_cv_resume_blog_meta', $meta );
		
		do_action( 'personal_cv_resume_site_content_type', $meta  );
        ?>
      
       
    </div>
    
</article><!-- #post-<?php the_ID(); ?> -->
