$(window).on('resize', function () {
    if ($('#header-content').height() >= 53) {
        $('#headertitle').css('order', 10);
    } else {
        $('#headertitle').css('order', ''); // Reset to default order
    }
}).trigger('resize'); // Trigger the function on page load
