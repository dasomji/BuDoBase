$(window).on('resize', function () {
    if ($('#header-content').height() >= 53) {
        $('#headertitle').css('order', 10);
    } else {
        $('#headertitle').css('order', ''); // Reset to default order
    }
}).trigger('resize'); // Trigger the function on page load

function w3_open() {
    document.getElementById("mySidebar").style.display = "block";
}

function w3_close() {
    document.getElementById("mySidebar").style.display = "none";
}