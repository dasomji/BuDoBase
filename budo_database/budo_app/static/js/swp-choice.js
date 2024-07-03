document.addEventListener('DOMContentLoaded', function () {
    const swpChoices = document.querySelectorAll('.swp-choice-link');

    swpChoices.forEach(choice => {
        choice.addEventListener('click', function (e) {
            e.preventDefault();
            const kidId = this.closest('.swp-choice').dataset.kidId;
            const swpId = this.closest('.swp-choice').dataset.swpId;
            const choiceRank = this.dataset.choice;

            updateSchwerpunktWahl(kidId, swpId, choiceRank, this);
        });
    });

    function updateSchwerpunktWahl(kidId, swpId, choiceRank, clickedElement) {
        fetch('/update-schwerpunkt-wahl/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({
                kid_id: kidId,
                swp_id: swpId,
                choice_rank: choiceRank
            })
        })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    console.log('Schwerpunkt choice updated successfully');
                    // Find the parent row of the clicked element
                    const parentRow = clickedElement.closest('tr');
                    // Remove .active class from all links in the same row with the same choice rank
                    parentRow.querySelectorAll(`.swp-choice-link[data-choice="${choiceRank}"]`).forEach(link => {
                        link.classList.remove('active');
                    });
                    // Add .active class to the clicked element
                    clickedElement.classList.add('active');
                } else {
                    console.error('Error updating Schwerpunkt choice');
                }
            })
            .catch(error => {
                console.error('Error:', error);
            });
    }

    // Helper function to get CSRF token
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
});
