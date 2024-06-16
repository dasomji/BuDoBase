window.onload = function () {
    const data = JSON.parse(document.getElementById('map-data').textContent);
    const mainView = data.mainView;
    const schwerpunkte = data.schwerpunkte;

    var map = L.map('map').setView(mainView, 12);
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19,
        attribution: '&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>'
    }).addTo(map);

    var markers = [];
    schwerpunkte.forEach(function (swp) {
        if (swp.ort && swp.ort.koordinaten) {
            var auslagerortIcon = L.divIcon({ className: 'leaflet-text', html: "<b><a href='/schwerpunkt/" + swp.id + "/'>📍" + swp.swp_name + "</a></b>" });
            var marker = L.marker(swp.ort.koordinaten, { icon: auslagerortIcon }).addTo(map);
            markers.push(marker);
        }
    });

    if (markers.length > 0) {
        var group = new L.featureGroup(markers);
        map.fitBounds(group.getBounds(), { paddingBottomRight: [150, 0] });
    }
}