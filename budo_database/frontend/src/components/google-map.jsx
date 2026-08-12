import { useEffect, useMemo, useRef, useState } from 'react';
import { importLibrary, setOptions } from '@googlemaps/js-api-loader';

import { Card } from '../components';

const parsePoint = coordinates => {
  const [lat, lng, ...rest] = String(coordinates || '').split(',').map(Number);
  return rest.length === 0 && Number.isFinite(lat) && Number.isFinite(lng) ? { lat, lng } : null;
};

const markerColor = token => getComputedStyle(document.documentElement)
  .getPropertyValue(`--color-${token}`)
  .trim();

const markerIcon = token => ({
  path: 'M 0,-10 A 10,10 0 1,1 0,10 A 10,10 0 1,1 0,-10',
  fillColor: markerColor(token),
  fillOpacity: 1,
  strokeColor: markerColor('foreground'),
  strokeWeight: 1,
  scale: 1,
});

let configuredKey;
const loadMaps = apiKey => {
  if (!configuredKey) {
    configuredKey = apiKey;
    setOptions({ key: apiKey, v: 'weekly', language: 'de', region: 'AT', authReferrerPolicy: 'origin' });
  }
  return Promise.all([
    importLibrary('maps'),
    importLibrary('marker'),
    importLibrary('core'),
  ]);
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
    let clearMapListeners;
    const listeners = [];
    loadMaps(apiKey).then(([
      { Map },
      { Marker, AdvancedMarkerElement },
      { ControlPosition, LatLngBounds, event: mapEvents },
    ]) => {
      if (disposed) return;
      clearMapListeners = mapEvents.clearInstanceListeners;
      map = new Map(element.current, {
        center: { lat: 47.7, lng: 15.9 },
        zoom: 9,
        mapTypeControl: true,
        mapTypeControlOptions: {
          mapTypeIds: ['roadmap', 'satellite'],
          position: ControlPosition.RIGHT_CENTER,
        },
        streetViewControl: false,
        fullscreenControl: false,
        zoomControlOptions: { position: ControlPosition.RIGHT_CENTER },
      });
      const bounds = new LatLngBounds();
      const addMarker = ({ point, name, id, href }, options = {}) => {
        const markerOptions = {
          map,
          position: point,
          title: name,
          zIndex: options.zIndex,
        };
        let marker;
        if (Marker) {
          marker = new Marker({
            ...markerOptions,
            label: options.label || {
              text: name,
              color: markerColor('foreground'),
              fontWeight: '600',
            },
            icon: options.icon,
          });
        } else if (AdvancedMarkerElement) {
          const content = document.createElement('span');
          content.className = `rounded-full border border-foreground px-2 py-1 text-xs font-semibold ${options.markerClass || 'bg-primary text-primary-foreground'}`;
          content.textContent = options.label?.text || name;
          marker = new AdvancedMarkerElement({ ...markerOptions, content });
        } else {
          throw new Error('The Google Maps marker library did not provide a marker constructor.');
        }
        bounds.extend(point);
        if (id != null && (onSelectPlace || href)) listeners.push(marker.addListener('click', () => {
          if (onSelectPlace) onSelectPlace(id);
          else window.location.assign(href);
        }));
      };
      locations.filter(place => place.id !== homePlace?.id).forEach(place => addMarker(place, {
        zIndex: Number(place.id) === Number(selectedPlaceId) ? 30 : 10,
        icon: Number(place.id) === Number(selectedPlaceId) ? markerIcon('secondary') : undefined,
        markerClass: Number(place.id) === Number(selectedPlaceId)
          ? 'bg-secondary text-secondary-foreground'
          : undefined,
      }));
      const homePoint = parsePoint(homePlace?.coordinates);
      if (homePoint) addMarker({ ...homePlace, point: homePoint }, {
        label: { text: `⌂ ${homePlace.name}`, color: markerColor('foreground'), fontWeight: '700' },
        icon: markerIcon('primary'),
        markerClass: 'bg-primary text-primary-foreground',
        zIndex: 40,
      });
      const parkingPoint = parsePoint(parkingCoordinates);
      if (parkingPoint) addMarker({ point: parkingPoint, name: 'Parkspot' }, {
        label: { text: 'P Parkspot', color: markerColor('foreground'), fontWeight: '700' },
        icon: markerIcon('success'),
        markerClass: 'bg-success text-success-foreground',
        zIndex: 50,
      });
      if (!bounds.isEmpty()) map.fitBounds(bounds, 64);
    }).catch(() => {
      if (!disposed) setError('Google Maps konnte nicht geladen werden.');
    });
    return () => {
      disposed = true;
      listeners.forEach(listener => listener.remove());
      if (map) clearMapListeners?.(map);
    };
  }, [apiKey, homePlace, locations, onSelectPlace, parkingCoordinates, selectedPlaceId]);

  if (!apiKey) return <div id={id} className={`grid place-items-center bg-muted p-4 text-center text-muted-foreground ${className}`} role="region" aria-label="Google Karte"><span>Google-Maps-Browser-Key ist nicht konfiguriert.</span><span className="sr-only">{places.map(place => place.name).join(', ')}</span></div>;
  return <div id={id} className={`relative ${className}`} role="region" aria-label="Google Karte"><div className="absolute inset-0" ref={element} />{error && <p className="absolute inset-x-4 top-4 rounded-lg bg-background p-3 text-center shadow-elevated">{error}</p>}</div>;
}

export function GoogleMapCard({ apiKey, places = [], headerAction = null }) {
  return (
    <Card title="Karte" id="swp-map" className="transparent" headerAction={headerAction}>
      <GoogleMap id="map" apiKey={apiKey} places={places} className="interactive-map min-h-70 w-full" />
    </Card>
  );
}
