;(function($) {
'use strict'
// Dom Ready
//Trap focus inside mobile menu modal
		//Based on https://codepen.io/eskjondal/pen/zKZyyg	
		var trapFocusInsiders = function(elem) {
			
				
			var tabbable = elem.find('select, input, textarea, button, a').filter(':visible');
			
			var firstTabbable = tabbable.first();
			var lastTabbable = tabbable.last();
			/*set focus on first input*/
			firstTabbable.focus();
			
			/*redirect last tab to first input*/
			lastTabbable.on('keydown', function (e) {
			   if ((e.which === 9 && !e.shiftKey)) {
				   e.preventDefault();
				   
				   firstTabbable.focus();
				  
			   }
			});
			
			/*redirect first shift+tab to last input*/
			firstTabbable.on('keydown', function (e) {
				if ((e.which === 9 && e.shiftKey)) {
					e.preventDefault();
					lastTabbable.focus();
				}
			});
			
			/* allow escape key to close insiders div */
			elem.on('keyup', function(e){
			  if (e.keyCode === 27 ) {
				elem.hide();
			  };
			});
			
		};

		var focus_to = function(action,element) {

			$(action).keyup(function (e) {
			    e.preventDefault();
				var code = e.keyCode || e.which;
				if(code == 13) { 
					$(element).focus();
				}
			});		
			
		}
	$(function() {
		
		if( $('.widget.widget_block h2').length ){
			$('.widget.widget_block h2').each(function() {
  				
  				$(this).html('<span>'+ $(this).text() +'</span>');
			});
		}
		

		if($("#fly-sidebar").length ) {
			$('#sidebar-actions').click

			$("#sidebar-actions").on('click', function(e){
				e.preventDefault();
				$(this).toggleClass('active');
				$("#fly-sidebar").find('.sidewrapper').toggleClass('active');
				
				if ($(this).hasClass("active")) {
					trapFocusInsiders( $('#fly-sidebar') );	
				}else{
					focus_to('#sidebar-actions');
				}
	   		});	

			$('#secondary').slimScroll({
			    height: '100vh'
			});
		}

		/*=============================================
	    =            Main Menu         =
	    =============================================*/
	   
		$('#navbar .navigation-menu li > a').keyup(function (e) {
			if ( matchMedia( 'only screen and (min-width: 992px)' ).matches ) {
				$("#navbar .navigation-menu li").removeClass('focus');
				$(this).parents('li.menu-item-has-children').addClass('focus').addClass('focus-mode');
			}
		});	

		$('#aside-nav-wrapper').hover(function(){	
			$("li.menu-item-has-children").removeClass('focus-mode');	
		});	

		$("#sidebar-actions-header").on('click', function(e){
				e.preventDefault();
				$(this).toggleClass('active');

				$("#aside-nav-wrapper").toggleClass('active');
				if ($(this).hasClass("active")) {
					trapFocusInsiders( $('#aside-nav-wrapper') );	
				}else{
					focus_to('#sidebar-actions-header');
				}
	   		});	

		$("a.thickbox").fancybox();
		$("a.fancy_group").fancybox();

		var tsSlider = $ (".fs-product-slider");
            if(tsSlider.length) {
                tsSlider.owlCarousel({
                  loop:true,
                  nav:false,
                  dots:false,
                  autoplay:true,
                  margin:30,
                  autoplayTimeout:4000,
                  autoplaySpeed:1000,
                  lazyLoad:true,
                  singleItem:true,
                  responsive:{
                      0:{
                          items:1
                      },
                      768:{
                          items:1
                      }
                  }
              });
            }

        $('#navbar li.menu-item-has-children').each(function( index ) {
			$(this).find('a').eq(0).after('<button class="dashicons dashicons-arrow-down responsive-submenu-toggle" tabindex="0" autofocus="autofocus"></button>');
		});

		$(".responsive-submenu-toggle").on('click', function(e){
			$(this).next('ul').toggleClass('focus-active');
			$(this).toggleClass('dashicons-arrow-up');
	   });

		AOS.init();
		
	});
})(jQuery);