<?php
/**
 * The Site Theme Header Class 
 *
 * Eventually, some of the functionality here could be replaced by core features.
 *
 * @package personal-cv-resume
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit; // Exit if accessed directly.
}
class personal_cv_resume_Footer_Layout{
	/**
	 * Function that is run after instantiation.
	 *
	 * @return void
	 */
	public function __construct() {
		add_action('personal_cv_resume_site_footer', array( $this, 'site_footer_container_before' ), 5);
		add_action('personal_cv_resume_site_footer', array( $this, 'site_footer_widgets' ), 10);
		add_action('personal_cv_resume_site_footer', array( $this, 'site_footer_info' ), 80);
		add_action('personal_cv_resume_site_footer', array( $this, 'site_footer_container_after' ), 998);
	}

	/**
	* diet_shop foter conteinr before
	*
	* @return $html
	*/
	public function site_footer_container_before (){
		
		$html = ' <footer id="colophon" class="site-footer">';
						
		$html = apply_filters( 'personal_cv_resume_footer_container_before_filter',$html);		
				
		echo wp_kses( $html, $this->alowed_tags() );
		
						
	}
	
	/**
	* Footer Container before
	*
	* @return $html
	*/
	function site_footer_widgets(){
	

        if ( is_active_sidebar( 'footer' ) ) { ?>
         <div id="footer">tes
         <div class="container">
            <div class="row emart-flex">
                <?php dynamic_sidebar( 'footer' ); ?>
            </div>
         </div>  
         </div>
        <?php }

	}
	
	
	/**
	* diet_shop foter conteinr after
	*
	* @return $html
	*/
	public function site_footer_info (){
		$text ='';
		$html = '<div class="site_info"><div class="container text-center">';
		
			$html .= $this->site_footer_back_top();

			$html .= '<div class="text">';
			
			if( get_theme_mod('copyright_text') != '' ) 
			{
				$text .= esc_html(  get_theme_mod('copyright_text') );
			}else
			{
				/* translators: 1: Current Year, 2: Blog Name  */
				$text .= sprintf( esc_html__( 'Copyright &copy; %1$s %2$s. All Right Reserved.', 'personal-cv-resume' ), date_i18n( _x( 'Y', 'copyright date format', 'personal-cv-resume' ) ), esc_html( get_bloginfo( 'name' ) ) );
				
			}

			$html  .= apply_filters( 'emart_footer_copywrite_filter', $text );
				
		
			/* translators: 1: developer website, 2: WordPress url  */
			$html  .= '<span class="dev_info">'.sprintf( esc_html__( 'Theme : %1$s By %2$s', 'personal-cv-resume' ), '<a href="'. esc_url( 'https://wordpress.org/themes/personal-cv-resume/' ) .'" target="_blank" rel="nofollow">'.esc_html_x( 'Personal CV Resume', 'theme name', 'personal-cv-resume' ).'</a>',  '<a href="'.esc_url( __( 'https://athemeart.com/', 'personal-cv-resume' ) ).'" target="_blank" rel="nofollow">'.esc_html_x( 'aThemeArt', 'credit to developer', 'personal-cv-resume' ).'</a>' ).'</span>';
			
			$html .= '</div>';
			
		$html .= '</div></div>';
		
		echo wp_kses( $html, $this->alowed_tags() );
	
	}
	
	public function site_footer_back_top (){
		
		$html = '<a id="backToTop" class="ui-to-top active"><i class="icofont-rounded-up parallax"></i></a>';
						
		$html = apply_filters( 'emart_site_footer_back_top_filter',$html);		
				
		return wp_kses( $html, $this->alowed_tags() );
	
	}
	/**
	* diet_shop foter conteinr after
	*
	* @return $html
	*/
	public function site_footer_container_after (){
		
		$html = '</footer>';
						
		$html = apply_filters( 'personal_cv_resume_footer_container_after_filter',$html);		
				
		echo wp_kses( $html, $this->alowed_tags() );
	
	}
	
	
	private function alowed_tags(){
		
		if( function_exists('personal_cv_resume_alowed_tags') ){ 
			return personal_cv_resume_alowed_tags(); 
		}else{
			return array();	
		}
		
	}
}

$personal_cv_resume_footer_layout = new personal_cv_resume_Footer_Layout();