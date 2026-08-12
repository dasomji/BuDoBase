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
  mapId = null,
  mapTypeId = 'roadmap',
}) {
  const element = useRef(null);
  const mapRef = useRef(null);
  const mapsApiRef = useRef(null);
  const onSelectPlaceRef = useRef(onSelectPlace);
  const [mapsReady, setMapsReady] = useState(0);
  const [error, setError] = useState('');
  const locations = useMemo(() => places.map(place => ({ ...place, point: parsePoint(place.coordinates) })).filter(place => place.point), [places]);
  onSelectPlaceRef.current = onSelectPlace;

  useEffect(() => {
    if (!apiKey || !element.current) return undefined;
    let disposed = false;
    setError('');
    loadMaps(apiKey).then(([
      { Map },
      { Marker, AdvancedMarkerElement },
      { ControlPosition, LatLngBounds, event: mapEvents },
    ]) => {
      if (disposed) return;
      const map = new Map(element.current, {
        center: { lat: 47.7, lng: 15.9 },
        zoom: 9,
        ...(mapId ? { mapId } : {}),
        mapTypeControl: false,
        streetViewControl: false,
        fullscreenControl: false,
        zoomControlOptions: { position: ControlPosition.RIGHT_CENTER },
      });
      mapRef.current = map;
      mapsApiRef.current = { Marker, AdvancedMarkerElement, LatLngBounds, mapEvents };
      setMapsReady(current => current + 1);
    }).catch(() => {
      if (!disposed) setError('Google Maps konnte nicht geladen werden.');
    });
    return () => {
      disposed = true;
      if (mapRef.current) mapsApiRef.current?.mapEvents.clearInstanceListeners(mapRef.current);
      mapRef.current = null;
      mapsApiRef.current = null;
    };
  }, [apiKey, mapId]);

  useEffect(() => {
    mapRef.current?.setMapTypeId(mapTypeId);
  }, [mapTypeId, mapsReady]);

  useEffect(() => {
    const map = mapRef.current;
    const mapsApi = mapsApiRef.current;
    if (!map || !mapsApi) return undefined;
    const { Marker, AdvancedMarkerElement } = mapsApi;
    if (!Marker && (!AdvancedMarkerElement || !mapId)) {
      setError('Google Maps konnte keine Marker laden. Eine Karten-ID fehlt oder ist ungültig.');
      return undefined;
    }
    const markers = [];
    const listeners = [];
    const addMarker = ({ point, name, id, href }, options = {}) => {
      const markerOptions = {
        map,
        position: point,
        title: name,
        zIndex: options.zIndex,
      };
      let marker;
      if (AdvancedMarkerElement && mapId) {
        const content = document.createElement('span');
        content.className = `rounded-full border border-foreground px-2 py-1 text-xs font-semibold ${options.markerClass || 'bg-primary text-primary-foreground'}`;
        content.textContent = options.label?.text || name;
        marker = new AdvancedMarkerElement({ ...markerOptions, content });
      } else if (Marker) {
        marker = new Marker({
          ...markerOptions,
          label: options.label || {
            text: name,
            color: markerColor('foreground'),
            fontWeight: '600',
          },
          icon: options.icon,
        });
      } else {
        throw new Error('The Google Maps marker library did not provide a marker constructor.');
      }
      markers.push(marker);
      if (id != null && (onSelectPlaceRef.current || href)) listeners.push(marker.addListener('click', () => {
        if (onSelectPlaceRef.current) onSelectPlaceRef.current(id);
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
    return () => {
      listeners.forEach(listener => listener.remove());
      markers.forEach(marker => {
        if (typeof marker.setMap === 'function') marker.setMap(null);
        else marker.map = null;
      });
    };
  }, [homePlace, locations, mapId, mapsReady, parkingCoordinates, selectedPlaceId]);

  const boundsKey = locations
    .map(place => `${place.id}:${place.point.lat},${place.point.lng}`)
    .sort()
    .join('|');
  useEffect(() => {
    const map = mapRef.current;
    const LatLngBounds = mapsApiRef.current?.LatLngBounds;
    if (!map || !LatLngBounds) return;
    const bounds = new LatLngBounds();
    locations.forEach(place => bounds.extend(place.point));
    const homePoint = parsePoint(homePlace?.coordinates);
    if (homePoint) bounds.extend(homePoint);
    if (!bounds.isEmpty()) map.fitBounds(bounds, 64);
  // Selection and parking markers must not reset the user's viewport.
  }, [boundsKey, homePlace?.coordinates, mapsReady]);

  if (!apiKey) return <div id={id} className={`grid place-items-center bg-muted p-4 text-center text-muted-foreground ${className}`} role="region" aria-label="Google Karte"><span>Google-Maps-Browser-Key ist nicht konfiguriert.</span><span className="sr-only">{places.map(place => place.name).join(', ')}</span></div>;
  return <div id={id} className={`relative ${className}`} role="region" aria-label="Google Karte"><div className="absolute inset-0" ref={element} />{locations.length === 0 && !error && <p className="absolute inset-x-4 top-4 rounded-lg bg-background p-3 text-center shadow-elevated">Keine Orte mit Koordinaten vorhanden.</p>}{error && <p className="absolute inset-x-4 top-4 rounded-lg bg-background p-3 text-center shadow-elevated">{error}</p>}</div>;
}

export function GoogleMapCard({ apiKey, mapId = null, places = [], headerAction = null }) {
  return (
    <Card title="Karte" id="swp-map" className="transparent" headerAction={headerAction}>
      <GoogleMap id="map" apiKey={apiKey} mapId={mapId} places={places} className="interactive-map min-h-70 w-full" />
    </Card>
  );
}
