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
    $('.card:not(.closed-card) > .card-info-container').show();
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

    // Append toggle-all button if there is at least one card
    if ($('.card').length > 0) {
        $('body').append('<div id="toggle-all" class="toggle-all-button">Toggle cards</div>');

        // Toggle all cards
        $('#toggle-all').click(function () {
            let allClosed = $('.card:not(.closed-card)').length === 0;

            if (allClosed) {
                $('.card').removeClass('closed-card');
                $('.card .card-info-container').slideDown();
            } else {
                $('.card').addClass('closed-card');
                $('.card .card-info-container').slideUp();
            }

            // Update cookie
            let closedCards = $('.closed-card').map(function () {
                return this.id;
            }).get();
            Cookies.set('closedCards', JSON.stringify(closedCards));
        });
    }
});
