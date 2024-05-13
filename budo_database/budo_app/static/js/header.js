$(window).on('resize', function () {
    if ($('#header-content').height() >= 53) {
        $('#headertitle').css('order', 10);
    } else {
        $('#headertitle').css('order', ''); // Reset to default order
    }
}).trigger('resize'); // Trigger the function on page load

// function openNav() {
//     document.getElementById("sidebar-container").style.display = "flex";
// }

// function closeNav() {
//     document.getElementById("sidebar-container").style.display = "none";
// }

function openNav() {
    document.getElementById("sidebar-container").classList.add('open');
}

function closeNav() {
    document.getElementById("sidebar-container").classList.remove('open');
}