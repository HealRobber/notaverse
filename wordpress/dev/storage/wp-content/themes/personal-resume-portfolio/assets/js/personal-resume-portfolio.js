;(function($) {
'use strict'
// Dom Ready
	$(function() {
    	var grid = document.querySelector('#masonry-grid');
        if (grid) {
            new Masonry(grid, {
                itemSelector: '.grid-item',
                columnWidth: '.grid-item',
                percentPosition: true
            });
        }
        if ($(window).width() >= 750) {
        $('#aside-nav-wrapper .header-wrap').stickySidebar({
            topSpacing: 0,
            bottomSpacing:0
        });
        }else{
           $('#aside-nav-wrapper .header-wrap').stickySidebar('destroy');
          
        }
	});
})(jQuery);