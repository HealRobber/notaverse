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
class personal_cv_resume_header_layout{
	/**
	 * Function that is run after instantiation.
	 *
	 * @return void
	 */
	public function __construct() {

		add_action('personal_cv_resume_header_layout_1_branding', array( $this, 'get_site_branding' ), 10 );

		add_action('personal_cv_resume_header_layout_1_navigation', array( $this, 'get_site_navigation' ), 10 );

		add_action('personal_cv_resume_site_header', array( $this, 'site_skip_to_content' ), 5 );
		
		add_action('personal_cv_resume_site_header', array( $this, 'site_header_layout' ), 30 );
	
		add_action('personal_cv_resume_site_header', array( $this, 'site_get_sidebar' ), 999);
	}
	
	/**
	 * Aside Sidebar
	 *
	 * @param     NUll
	 * @return    $sidebar widgets
	 */
	function site_get_sidebar( ) {
		if ( ! is_active_sidebar( 'sidebar-1' ) ) { return; }
	?>
	<div id="fly-sidebar"> 
        <button class="side-bar-icon" id="sidebar-actions">
            <span></span>
            <span></span>
            <span></span>
        </button>
        
        <div class="sidewrapper sidenav">
        	<?php get_sidebar(); ?>
        </div>
    </div>    
    <?php
	}

	/**
	* Container before
	*
	* @return $html
	*/
	function site_skip_to_content(){
		
		echo '<a class="skip-link screen-reader-text" href="#primary">'. esc_html__( 'Skip to content', 'personal-cv-resume' ) .'</a>';
	}

	
	/**
	* Container before
	*
	* @return $html
	*/
	function site_header_layout(){
		?>
		<div id="aside-nav-wrapper" class="fixed">
			<button class="side-bar-icon" id="sidebar-actions-header">
	            <span></span>
	            <span></span>
	            <span></span>
	        </button>
			<div class="header-wrap">
				<?php do_action('personal_cv_resume_header_layout_1_branding');?>
				<?php do_action('personal_cv_resume_header_layout_1_navigation');?>
			</div>
		</div>
		<?php		
	}

	/**
	* Get the Site logo
	*
	* @return HTML
	*/
	public function get_site_branding (){

		$header = ( get_header_image() != "" ) ? 'background-image: url('. esc_url( get_header_image() ).'); background-size:cover;' : '';

		$html = '<div class="logo-wrap profile-wrp">';
		
		$html .= '<div class="wp-header-image" style="'.esc_attr( $header ).'"></div>';

		if ( function_exists( 'the_custom_logo' ) && has_custom_logo() ) {
			$html .= '<div class="my-photo">'.get_custom_logo().'</div>';
		}
		
		$html .= '</div>';
		
		if ( display_header_text() == true ){
			
			$html .= '<div class="branding-text"><h3><a href="'.esc_url( home_url( '/' ) ).'" rel="home" class="site-title">';
			$html .= get_bloginfo( 'name' );
			$html .= '</a></h3>';
			$description = get_bloginfo( 'description', 'display' );
		
			if ( $description ) :
			    $html .=  '<div class="site-description">'.esc_html($description).'</div>';
			endif;
			$html .= '</div>';
		}
		
		$html = apply_filters( 'get_site_branding_filter', $html );
		
		echo wp_kses( $html, $this->alowed_tags() );
		
	}
	
	/**
	* Get the Site Main Menu / Navigation
	*
	* @return HTML
	*/
	public function get_site_navigation (){
		?>
       <nav id="navbar" class="navbar-fill">
			
		<?php
			wp_nav_menu( array(
				'theme_location'    => 'menu-1',
				'depth'             => 3,
				'menu_class'  		=> 'emart-main-menu navigation-menu',
				'container'			=> 'ul',
				'walker' 			=> new personal_cv_resume_navwalker(),
		        'fallback_cb'       => 'personal_cv_resume_navwalker::fallback',
			) );
		?>
		
		</nav>
		<?php 
		
	}
	
	/**
	 * Add Banner Title.
	 *
	 * @since 1.0.0
	 */
	function hero_block_heading() {
		echo '<div class="site-header-text-wrap">';
		
			if ( is_home() ) {
					echo '<h1 class="page-title-text">';
					echo bloginfo( 'name' );
					echo '</h1>';
					echo '<p class="subtitle">';
					echo esc_html(get_bloginfo( 'description', 'display' ));
					echo '</p>';
			}else if ( function_exists('is_shop') && is_shop() ){
				if ( in_array( 'woocommerce/woocommerce.php', apply_filters( 'active_plugins', get_option( 'active_plugins' ) ) ) ) {
					echo '<h1 class="page-title-text">';
					echo esc_html( woocommerce_page_title() );
					echo '</h1>';
				}
			}else if( function_exists('is_product_category') && is_product_category() ){
				echo '<h1 class="page-title-text">';
				echo esc_html( woocommerce_page_title() );
				echo '</h1>';
				echo '<p class="subtitle">';
				do_action( 'woocommerce_archive_description' );
				echo '</p>';
				
			}elseif ( is_singular() ) {
				echo '<h1 class="page-title-text">';
					echo single_post_title( '', false );
				echo '</h1>';
			} elseif ( is_archive() ) {
				
				the_archive_title( '<h1 class="page-title-text">', '</h1>' );
				the_archive_description( '<p class="archive-description subtitle">', '</p>' );
				
			} elseif ( is_search() ) {
				echo '<h1 class="title">';
					printf( /* translators:straing */ esc_html__( 'Search Results for: %s', 'personal-cv-resume' ),  get_search_query() );
				echo '</h1>';
			} elseif ( is_404() ) {
				echo '<h1 class="display-1">';
					esc_html_e( 'Oops! That page can&rsquo;t be found.', 'personal-cv-resume' );
				echo '</h1>';
			}
		
		echo '</div>';
	}
	private function alowed_tags(){
		
		if( function_exists('personal_cv_resume_alowed_tags') ){ 
			return personal_cv_resume_alowed_tags(); 
		}else{
			return array();	
		}
		
	}
}

$personal_cv_resume_header_layout = new personal_cv_resume_header_layout();