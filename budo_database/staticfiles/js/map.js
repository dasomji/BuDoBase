window.addEventListener('DOMContentLoaded', () => {
    setTimeout(() => {
        const key = '1kn4MSxztk96Wwv8LkgK';
        const mapData = document.getElementById('map-data').textContent;
        const jsonString = JSON.parse(mapData);
        const data = JSON.parse(jsonString);

        // Parse mainView string into an array of numbers
        const firstSchwerpunkt = data.orte[0];
        const mainViewRaw = firstSchwerpunkt.koordinaten;
        const mainView = mainViewRaw.split(',').map(Number);
        const orte = data.orte;

        console.log("Main View Coordinates:", mainView); // Debugging line

        var map = L.map('map').setView(mainView, 12);
        const mtLayer = L.maptilerLayer({
            maxZoom: 19,
            apiKey: key,
            style: "0c0b0e33-3ca7-4c0b-98b0-8cbd7f8600f4", //optional
        }).addTo(map);

        var markers = [];
        orte.forEach(function (swp) {
            console.log(swp);
            if (swp.koordinaten) {
                // Parse the coordinates string into an array of numbers
                const coordinates = swp.koordinaten.split(',').map(Number);
                console.log("Adding marker for:", swp.name, "at", coordinates); // Debugging line
                var auslagerortIcon = L.divIcon({ className: 'leaflet-text', html: `<b><a href='/${swp.kind}/${swp.id}/'>📍${swp.name}</a></b>` });
                var marker = L.marker(coordinates, { icon: auslagerortIcon }).addTo(map);
                markers.push(marker);
            } else {
                console.warn("Missing coordinates for:", swp.name); // Debugging line
            }
        });

        console.log(markers.length)

        if (markers.length > 0) {
            var group = new L.featureGroup(markers);
            map.fitBounds(group.getBounds(), { paddingBottomRight: [150, 0] });
        }


    }, 100);
});

function toggleModal(cardId) {
    const card = document.getElementById(cardId);
    card.classList.toggle('map-modal');
}