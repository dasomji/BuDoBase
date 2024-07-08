document.addEventListener('DOMContentLoaded', function () {
    const modal = document.getElementById('freundeModal');
    const closeBtn = modal.querySelector('.close');
    const saveBtn = document.getElementById('saveFreundeBtn');
    const freundeInput = document.getElementById('freundeInput');
    let currentKidId;

    document.querySelectorAll('.edit-freunde-btn').forEach(btn => {
        btn.addEventListener('click', function () {
            currentKidId = this.dataset.kidId;
            const freundeText = document.querySelector(`.freunde-text[data-kid-id="${currentKidId}"]`).textContent;
            freundeInput.value = freundeText;
            modal.style.display = 'block';
        });
    });

    closeBtn.onclick = function () {
        modal.style.display = 'none';
    }

    window.onclick = function (event) {
        if (event.target == modal) {
            modal.style.display = 'none';
        }
    }

    saveBtn.onclick = function () {
        const newFreunde = freundeInput.value;
        fetch('/update_freunde/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({
                kid_id: currentKidId,
                freunde: newFreunde
            })
        })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    document.querySelector(`.freunde-text[data-kid-id="${currentKidId}"]`).textContent = newFreunde;
                    modal.style.display = 'none';
                } else {
                    alert('Error updating freunde');
                }
            });
    }

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