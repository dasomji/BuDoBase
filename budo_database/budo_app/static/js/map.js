window.addEventListener('DOMContentLoaded', () => {
    setTimeout(() => {
        const mapData = document.getElementById('map-data').textContent;
        const jsonString = JSON.parse(mapData);
        const data = JSON.parse(jsonString);

        // Parse mainView string into an array of numbers
        const mainView = data.mainView.split(',').map(Number);
        const schwerpunkte = data.schwerpunkte;

        console.log("Main View Coordinates:", mainView); // Debugging line

        var map = L.map('map').setView(mainView, 12);
        L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
            maxZoom: 19,
            attribution: '&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        }).addTo(map);

        var markers = [];
        schwerpunkte.forEach(function (swp) {
            console.log(swp.ort);
            if (swp.ort && swp.ort.koordinaten) {
                // Parse the coordinates string into an array of numbers
                const coordinates = swp.ort.koordinaten.split(',').map(Number);
                console.log("Adding marker for:", swp.swp_name, "at", coordinates); // Debugging line
                var auslagerortIcon = L.divIcon({ className: 'leaflet-text', html: "<b><a href='/schwerpunkt/" + swp.id + "/'>📍" + swp.swp_name + "</a></b>" });
                var marker = L.marker(coordinates, { icon: auslagerortIcon }).addTo(map);
                markers.push(marker);
            } else {
                console.warn("Missing coordinates for:", swp.swp_name); // Debugging line
            }
        });

        if (markers.length > 0) {
            var group = new L.featureGroup(markers);
            map.fitBounds(group.getBounds(), { paddingBottomRight: [150, 0] });
        }
    }, 100);
});
