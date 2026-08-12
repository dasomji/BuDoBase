import { useEffect, useMemo, useRef, useState } from 'react';
import { importLibrary, setOptions } from '@googlemaps/js-api-loader';

import { Card } from '../components';

const parsePoint = coordinates => {
  const [lat, lng, ...rest] = String(coordinates || '').split(',').map(Number);
  return rest.length === 0 && Number.isFinite(lat) && Number.isFinite(lng) ? { lat, lng } : null;
};

let configuredKey;
const loadMaps = apiKey => {
  if (!configuredKey) {
    configuredKey = apiKey;
    setOptions({ key: apiKey, v: 'weekly', language: 'de', region: 'AT', authReferrerPolicy: 'origin' });
  }
  return importLibrary('maps');
};

/** The sole seam that touches the Google Maps JavaScript library. */
export function GoogleMap({
  apiKey,
  places = [],
  homePlace = null,
  parkingCoordinates = null,
  selectedPlaceId = null,
  onSelectPlace = null,
  className = '',
  id,
}) {
  const element = useRef(null);
  const [error, setError] = useState('');
  const locations = useMemo(() => places.map(place => ({ ...place, point: parsePoint(place.coordinates) })).filter(place => place.point), [places]);

  useEffect(() => {
    if (!apiKey || !element.current) return undefined;
    let disposed = false;
    let map;
    const listeners = [];
    loadMaps(apiKey).then(({ Map }) => {
      if (disposed) return;
      map = new Map(element.current, {
        center: { lat: 47.7, lng: 15.9 },
        zoom: 9,
        mapTypeControl: true,
        mapTypeControlOptions: { mapTypeIds: ['roadmap', 'satellite'] },
        streetViewControl: false,
        fullscreenControl: false,
      });
      const bounds = new google.maps.LatLngBounds();
      const addMarker = ({ point, name, id, href }, options = {}) => {
        const marker = new google.maps.Marker({
          map,
          position: point,
          title: name,
          label: options.label || { text: name, color: '#373737', fontWeight: '600' },
          icon: options.icon,
          zIndex: options.zIndex,
        });
        bounds.extend(point);
        if (id != null && (onSelectPlace || href)) listeners.push(marker.addListener('click', () => {
          if (onSelectPlace) onSelectPlace(id);
          else window.location.assign(href);
        }));
      };
      locations.filter(place => place.id !== homePlace?.id).forEach(place => addMarker(place, {
        zIndex: Number(place.id) === Number(selectedPlaceId) ? 30 : 10,
        icon: Number(place.id) === Number(selectedPlaceId) ? 'https://maps.google.com/mapfiles/ms/icons/blue-dot.png' : undefined,
      }));
      const homePoint = parsePoint(homePlace?.coordinates);
      if (homePoint) addMarker({ ...homePlace, point: homePoint }, {
        label: { text: `⌂ ${homePlace.name}`, color: '#373737', fontWeight: '700' },
        icon: 'https://maps.google.com/mapfiles/ms/icons/orange-dot.png',
        zIndex: 40,
      });
      const parkingPoint = parsePoint(parkingCoordinates);
      if (parkingPoint) addMarker({ point: parkingPoint, name: 'Parkspot' }, {
        label: { text: 'P Parkspot', color: '#373737', fontWeight: '700' },
        icon: 'https://maps.google.com/mapfiles/ms/icons/green-dot.png',
        zIndex: 50,
      });
      if (!bounds.isEmpty()) map.fitBounds(bounds, 64);
    }).catch(() => {
      if (!disposed) setError('Google Maps konnte nicht geladen werden.');
    });
    return () => {
      disposed = true;
      listeners.forEach(listener => listener.remove());
      if (map) google.maps.event.clearInstanceListeners(map);
    };
  }, [apiKey, homePlace, locations, onSelectPlace, parkingCoordinates, selectedPlaceId]);

  if (!apiKey) return <div id={id} className={`grid place-items-center bg-muted p-4 text-center text-muted-foreground ${className}`} role="region" aria-label="Google Karte"><span>Google-Maps-Browser-Key ist nicht konfiguriert.</span><span className="sr-only">{places.map(place => place.name).join(', ')}</span></div>;
  return <div id={id} className={`relative ${className}`} role="region" aria-label="Google Karte"><div className="absolute inset-0" ref={element} />{error && <p className="absolute inset-x-4 top-4 rounded-lg bg-background p-3 text-center shadow">{error}</p>}</div>;
}

export function GoogleMapCard({ apiKey, places = [], headerAction = null }) {
  return (
    <Card title="Karte" id="swp-map" className="transparent" headerAction={headerAction}>
      <GoogleMap id="map" apiKey={apiKey} places={places} className="interactive-map min-h-70 w-full" />
    </Card>
  );
}
