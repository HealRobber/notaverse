<?php
/**
 * Template part for displaying posts
 *
 * @link https://developer.wordpress.org/themes/basics/template-hierarchy/
 *
 * @package Personal_CV_Resume
 */

?>
<div class="col-md-6 col-12 grid-item" >
<article id="post-<?php the_ID(); ?>" <?php post_class( array('content-post-wrap') ); ?>>

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
		    if (get_theme_mod('personal_res_port_show_author', true)) : 
		      $meta[] = 'author';
        endif;
        if (get_theme_mod('personal_res_port_show_date', false)) : 
          $meta[] = 'date';
        endif;
        if (get_theme_mod('personal_res_port_show_category', false)) : 
          $meta[] = 'category';
        endif;
        if (get_theme_mod('personal_res_port_show_comments', false)) : 
          $meta[] = 'comments';
        endif;
		
		  do_action( 'personal_cv_resume_site_content_type', $meta  );
        ?>
    </div>
    
</article><!-- #post-<?php the_ID(); ?> -->
</div>