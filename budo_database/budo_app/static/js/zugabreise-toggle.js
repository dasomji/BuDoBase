document.addEventListener('DOMContentLoaded', function () {
    var switches = document.querySelectorAll('[id^="switch-"]');
    switches.forEach(function (switchElement) {
        switchElement.addEventListener('click', function () {
            var kidId = this.dataset.id;
            var kidname = this.dataset.kidname;
            var zugabreise_feld = document.getElementById(`zugabreise-${kidId}`);
            var zugabreise_toggle = document.getElementById(`zugabreise-toggle-${kidId}`);
            var confirmAction = confirm(`Zugabreise-Status für ${kidname} ändern?`);
            if (confirmAction) {
                var xhr = new XMLHttpRequest();
                var url = this.dataset.url;
                xhr.open('POST', url, true);
                xhr.setRequestHeader('Content-type', 'application/x-www-form-urlencoded');
                xhr.setRequestHeader('X-CSRFToken', '{{ csrf_token }}');
                xhr.onload = function () {
                    if (this.status == 200) {
                        var response = JSON.parse(this.responseText);
                        if (response.status == 'success') {
                            zugabreise_feld.textContent = zugabreise_feld.textContent === "Ja" ? "Nein" : "Ja";
                            var switchElementInner = zugabreise_toggle.querySelector(".switch"); // Access .switch element directly from the zugabreise_toggle
                            if (switchElementInner) {
                                switchElementInner.classList.remove("ja", "nein"); // Remove both classes first
                                switchElementInner.classList.add(zugabreise_feld.textContent.toLowerCase()); // Add the appropriate class based on the new text content
                            }
                        }
                    }
                };
                xhr.send('id=' + kidId);
            }
        });
    });
});