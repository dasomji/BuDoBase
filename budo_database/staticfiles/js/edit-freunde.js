document.addEventListener('DOMContentLoaded', function () {
    const modal = document.getElementById("notizModal");
    const span = document.getElementsByClassName("close")[0];
    const notizInput = document.getElementById("notizInput");
    const saveNotizBtn = document.getElementById("saveNotizBtn");
    let currentKidId = null;

    document.querySelectorAll('.edit-freunde-btn').forEach(button => {
        button.addEventListener('click', function () {
            currentKidId = this.getAttribute('data-id');
            notizInput.value = this.getAttribute('data-notiz');
            modal.style.display = "block";
            notizInput.focus();  // Set focus on the input field
        });
    });

    span.onclick = function () {
        modal.style.display = "none";
    }

    window.onclick = function (event) {
        if (event.target == modal) {
            modal.style.display = "none";
        }
    }

    saveNotizBtn.addEventListener('click', function () {
        const newFreunde = notizInput.value;
        console.log('Current Kid ID:', currentKidId);
        console.log('New Freunde:', newFreunde);

        fetch('/update_freunde/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({ id: currentKidId, freunde: newFreunde })
        })
            .then(response => response.json())
            .then(data => {
                console.log('Server Response:', data);
                if (data.status === 'success') {
                    document.getElementById(`freunde-${currentKidId}`).innerText = newFreunde;
                    modal.style.display = "none";
                } else {
                    alert('Error updating freunde');
                }
            });
    });

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