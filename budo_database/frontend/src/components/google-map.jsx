import { useEffect, useMemo, useRef, useState } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { importLibrary, setOptions } from '@googlemaps/js-api-loader';

import { Card } from '../components';
import { fallbackTagIcon, loadTagIcons } from './tag-icon-loader';

// Cloud basemap source and deployment instructions live beside this component:
// ./google-map-style.json and ./google-map-style.md
const parsePoint = coordinates => {
  const [lat, lng, ...rest] = String(coordinates || '').split(',').map(Number);
  return rest.length === 0 && Number.isFinite(lat) && Number.isFinite(lng) ? { lat, lng } : null;
};

const markerColor = token => getComputedStyle(document.documentElement)
  .getPropertyValue(`--color-${token}`)
  .trim();

const tagIconMarkup = (icon, loadedIcons) => {
  const Icon = loadedIcons[icon] || fallbackTagIcon();
  return renderToStaticMarkup(
    <Icon width="16" height="16" strokeWidth="2.5" aria-hidden="true" />,
  );
};

const escapedMarkerText = name => String(name)
  .replaceAll('&', '&amp;')
  .replaceAll('<', '&lt;')
  .replaceAll('>', '&gt;');

const legacyMarker = (name, icon, token, expanded, loadedIcons) => {
  const width = expanded ? Math.max(80, Math.min(220, 44 + String(name).length * 7)) : 38;
  const foreground = markerColor('foreground');
  const background = markerColor(token);
  const label = expanded
    ? `<text x="36" y="24" fill="${foreground}" font-family="Roboto,Arial,sans-serif" font-size="12" font-weight="700">${escapedMarkerText(name)}</text>`
    : '';
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="40" viewBox="0 0 ${width} 40"><rect x="2" y="2" width="${width - 4}" height="34" rx="17" fill="${background}" stroke="#fff" stroke-width="2"/><g transform="translate(11 11)" color="${foreground}">${tagIconMarkup(icon, loadedIcons)}</g>${label}</svg>`;
  return { url: `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(svg)}` };
};

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
  const [loadedTagIcons, setLoadedTagIcons] = useState({ key: null, icons: {} });
  const locations = useMemo(() => places.map(place => ({ ...place, point: parsePoint(place.coordinates) })).filter(place => place.point), [places]);
  const tagIconKey = [...new Set([
    ...locations.map(place => place.marker_icon || 'map-pin'),
    ...(parsePoint(homePlace?.coordinates) ? ['house'] : []),
  ])].sort().join('|');
  onSelectPlaceRef.current = onSelectPlace;

  useEffect(() => {
    let active = true;
    const names = tagIconKey ? tagIconKey.split('|') : [];
    loadTagIcons(names).then(icons => {
      if (active) setLoadedTagIcons({ key: tagIconKey, icons });
    });
    return () => { active = false; };
  }, [tagIconKey]);

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
    if (!map || !mapsApi || loadedTagIcons.key !== tagIconKey) return undefined;
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
      const clickable = id != null && (onSelectPlaceRef.current || href);
      const expanded = Boolean(options.expanded);
      const icon = options.icon || 'map-pin';
      const token = options.markerToken || 'surface-solid';
      let marker;
      const usesAdvancedMarker = AdvancedMarkerElement && mapId;
      if (usesAdvancedMarker) {
        const content = document.createElement('span');
        content.className = `map-marker map-marker--${options.kind || 'place'} map-marker--${expanded ? 'selected' : 'compact'}${clickable ? ' map-marker--clickable' : ''}`;
        const iconElement = document.createElement('span');
        iconElement.className = 'map-marker-icon';
        iconElement.setAttribute('aria-hidden', 'true');
        iconElement.insertAdjacentHTML('afterbegin', tagIconMarkup(icon, loadedTagIcons.icons));
        const label = document.createElement('span');
        label.className = 'map-marker-label';
        label.textContent = name;
        content.append(iconElement, label);
        marker = new AdvancedMarkerElement({ ...markerOptions, content, gmpClickable: Boolean(clickable) });
      } else if (Marker) {
        marker = new Marker({
          ...markerOptions,
          icon: legacyMarker(name, icon, token, expanded, loadedTagIcons.icons),
        });
      } else {
        throw new Error('The Google Maps marker library did not provide a marker constructor.');
      }
      markers.push(marker);
      if (!clickable) return;
      const selectMarker = () => {
        if (onSelectPlaceRef.current) onSelectPlaceRef.current(id);
        else window.location.assign(href);
      };
      if (usesAdvancedMarker) {
        marker.addEventListener('gmp-click', selectMarker);
        listeners.push(() => marker.removeEventListener('gmp-click', selectMarker));
      } else {
        const listener = marker.addListener('click', selectMarker);
        listeners.push(() => listener.remove());
      }
    };
    locations.filter(place => place.id !== homePlace?.id).forEach(place => {
      const selected = Number(place.id) === Number(selectedPlaceId);
      addMarker(place, {
        zIndex: selected ? 30 : 10,
        icon: place.marker_icon || 'map-pin',
        markerToken: selected ? 'primary' : 'surface-solid',
        expanded: selected,
      });
    });
    const homePoint = parsePoint(homePlace?.coordinates);
    if (homePoint) {
      const selected = Number(homePlace.id) === Number(selectedPlaceId);
      addMarker({ ...homePlace, point: homePoint }, {
        icon: 'house',
        kind: 'home',
        markerToken: selected ? 'primary' : 'accent',
        expanded: selected,
        zIndex: selected ? 40 : 20,
      });
    }
    return () => {
      listeners.forEach(removeListener => removeListener());
      markers.forEach(marker => {
        if (typeof marker.setMap === 'function') marker.setMap(null);
        else marker.map = null;
      });
    };
  }, [homePlace, loadedTagIcons, locations, mapId, mapsReady, selectedPlaceId, tagIconKey]);

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

  const selectedPoint = locations.find(
    place => Number(place.id) === Number(selectedPlaceId),
  )?.point;
  const selectedPointKey = selectedPoint ? `${selectedPoint.lat},${selectedPoint.lng}` : '';
  useEffect(() => {
    if (selectedPoint) mapRef.current?.panTo(selectedPoint);
  }, [mapsReady, selectedPointKey]);

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
