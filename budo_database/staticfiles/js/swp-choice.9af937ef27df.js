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

    // Add event listener for schwerpunkt dropdowns
    const schwerpunktDropdowns = document.querySelectorAll('.schwerpunkt-dropdown');
    schwerpunktDropdowns.forEach(dropdown => {
        dropdown.addEventListener('change', function () {
            const kidId = this.dataset.kidId;
            const swpId = this.value;
            updateSchwerpunktWahl(kidId, swpId, null, this);
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
                    if (clickedElement.tagName === 'SELECT') {
                        // Update the schwerpunkt-selection cell
                        const schwerpunktSelectionCell = clickedElement.closest('.schwerpunkt-selection');
                        schwerpunktSelectionCell.querySelector('select').value = swpId;
                    } else {
                        // Existing code for handling non-dropdown updates
                        const parentRow = clickedElement.closest('tr');
                        parentRow.querySelectorAll(`.swp-choice-link[data-choice="${choiceRank}"]`).forEach(link => {
                            link.classList.remove('active');
                        });
                        clickedElement.classList.add('active');

                        if (choiceRank === '1') {
                            const schwerpunktSelectionCell = parentRow.querySelector('.schwerpunkt-selection');
                            schwerpunktSelectionCell.querySelector('select').value = swpId;
                        }
                    }
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
