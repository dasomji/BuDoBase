// $(window).on('resize', function () {
//     if ($('#header-content').height() >= 48) {
//         // $('#headertitle').css('order', 10);
//         $('#headertitle').hide();
//         $('#headerbutton').css('order', 11);
//     } else {
//         $('#headerbutton').css('order', ''); // Reset to default order
//         $('#headertitle').show();
//         // $('#headertitle').css('order', ''); // Reset to default order
//     }
// }).trigger('resize'); // Trigger the function on page load

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