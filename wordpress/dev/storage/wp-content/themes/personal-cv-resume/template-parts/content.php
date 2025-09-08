<?php
/**
 * Template part for displaying posts
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
		
		if ( is_singular() ) :
			
			if( personal_cv_resume_get_option('signle_meta_hide') != true ){
				
				$meta = array( 'author', 'date', 'category', 'comments' );
			}
			$meta  	 = apply_filters( 'personal_cv_resume_single_post_meta', $meta );
			
		else :
			if( personal_cv_resume_get_option('blog_meta_hide') != true ){
				
				$meta = array( 'author', 'date','category' );
			}
			$meta  	 = apply_filters( 'personal_cv_resume_blog_meta', $meta );
		 endif;
	
		
		 do_action( 'personal_cv_resume_site_content_type', $meta  );
        ?>
      
       
    </div>
    
</article><!-- #post-<?php the_ID(); ?> -->
