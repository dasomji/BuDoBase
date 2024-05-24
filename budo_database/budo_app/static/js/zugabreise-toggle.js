document.addEventListener('DOMContentLoaded', function () {
    var toggles = document.querySelectorAll('[id^="zugabreise-toggle-"]');
    toggles.forEach(function (toggleElement) {
        toggleElement.addEventListener('click', function () {
            var kidId = this.dataset.id;
            var kidname = this.dataset.kidname;
            var switchElementInner = this.querySelector(".switch");
            var currentStatus = switchElementInner.classList.contains("ja") ? "Ja" : "Nein";
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
                            var newStatus = currentStatus === "Ja" ? "Nein" : "Ja";
                            switchElementInner.classList.remove("ja", "nein"); // Remove both classes first
                            switchElementInner.classList.add(newStatus.toLowerCase()); // Add the appropriate class based on the new status
                        }
                    }
                };
                xhr.send('id=' + kidId);
            }
        });
    });
});
