$(document).ready(function () {
    // Restore state from cookie
    let closedCards = Cookies.get('closedCards');
    if (closedCards) {
        closedCards = JSON.parse(closedCards);
        closedCards.forEach(function (id) {
            let card = $('#' + id);
            card.addClass('closed-card');
            // card.find('.vertical-line').hide();
            card.find('.card-info-container').hide();
        });
    }
    // Show open cards
    $('.card:not(.closed-card) .card-info-container').slideToggle();
    // $('.card:not(.closed-card) .vertical-line').fadeToggle();

    // Save state to cookie when a card is clicked

    $('.info-header-container').click(function () {
        let cardInfoContainer = $(this).next('.card-info-container');
        // let icon = $(this).find('.vertical-line');
        let parentContainer = $(this).parent();

        // icon.fadeToggle()
        cardInfoContainer.slideToggle();
        parentContainer.toggleClass('closed-card');

        let closedCards = $('.closed-card').map(function () {
            return this.id;
        }).get();
        Cookies.set('closedCards', JSON.stringify(closedCards));
    });
});