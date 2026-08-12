import { cleanup, render, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

const mapsMock = vi.hoisted(() => {
  const state = { mapOptions: null, mapConstructions: 0, fitBoundsCalls: 0, mapTypeIds: [], markerOptions: [], markerKinds: [], advancedEventTypes: [], removedMarkers: 0 };
  class Map {
    constructor(_element, options) {
      state.mapOptions = options;
      state.mapConstructions += 1;
    }

    fitBounds() { state.fitBoundsCalls += 1; }

    setMapTypeId(mapTypeId) { state.mapTypeIds.push(mapTypeId); }
  }
  class Marker {
    constructor(options) {
      state.markerOptions.push(options);
      state.markerKinds.push('legacy');
    }

    addListener() {
      return { remove: vi.fn() };
    }

    setMap(map) {
      if (map === null) state.removedMarkers += 1;
    }
  }
  class AdvancedMarkerElement {
    constructor(options) {
      Object.assign(this, options);
      state.markerOptions.push(options);
      state.markerKinds.push('advanced');
    }

    addEventListener(eventType) { state.advancedEventTypes.push(eventType); }

    removeEventListener() {}
  }
  class LatLngBounds {
    extend() {}

    isEmpty() { return false; }
  }
  return {
    state,
    Map,
    Marker,
    LatLngBounds,
    importLibrary: vi.fn(name => ({
      maps: { Map },
      marker: { Marker, AdvancedMarkerElement },
      core: {
        ControlPosition: { RIGHT_CENTER: 6 },
        LatLngBounds,
        event: { clearInstanceListeners: vi.fn() },
      },
    })[name]),
    setOptions: vi.fn(),
  };
});

vi.mock('@googlemaps/js-api-loader', () => ({
  importLibrary: mapsMock.importLibrary,
  setOptions: mapsMock.setOptions,
}));

import { GoogleMap } from './google-map';

describe('GoogleMap loader seam', () => {
  afterEach(() => {
    cleanup();
    mapsMock.state.mapOptions = null;
    mapsMock.state.mapConstructions = 0;
    mapsMock.state.fitBoundsCalls = 0;
    mapsMock.state.mapTypeIds = [];
    mapsMock.state.markerOptions = [];
    mapsMock.state.markerKinds = [];
    mapsMock.state.advancedEventTypes = [];
    mapsMock.state.removedMarkers = 0;
    mapsMock.importLibrary.mockClear();
  });

  it('loads marker constructors officially and keeps map controls clear of overlays', async () => {
    render(<GoogleMap
      apiKey="browser-key"
      mapId="map-id"
      mapTypeId="roadmap"
      places={[{ id: 1, name: 'Hütte', coordinates: '47.1,15.2' }]}
      selectedPlaceId={1}
    />);

    await waitFor(() => expect(mapsMock.state.mapOptions).not.toBeNull());
    expect(mapsMock.importLibrary).toHaveBeenCalledWith('maps');
    expect(mapsMock.importLibrary).toHaveBeenCalledWith('marker');
    expect(mapsMock.importLibrary).toHaveBeenCalledWith('core');
    expect(mapsMock.state.mapOptions.mapTypeControl).toBe(false);
    expect(mapsMock.state.mapOptions.zoomControlOptions).toEqual({ position: 6 });
    expect(mapsMock.state.markerOptions).toHaveLength(1);
    expect(mapsMock.state.markerKinds).toEqual(['advanced']);
    expect(mapsMock.state.markerOptions[0].content).toHaveTextContent('Hütte');
    expect(mapsMock.state.markerOptions[0].gmpClickable).toBe(false);
  });

  it('uses the Advanced Marker click event instead of the deprecated legacy event', async () => {
    render(<GoogleMap
      apiKey="browser-key"
      mapId="map-id"
      places={[{ id: 1, name: 'Hütte', coordinates: '47.1,15.2' }]}
      onSelectPlace={vi.fn()}
    />);

    await waitFor(() => expect(mapsMock.state.markerOptions).toHaveLength(1));
    expect(mapsMock.state.markerOptions[0].gmpClickable).toBe(true);
    expect(mapsMock.state.advancedEventTypes).toEqual(['gmp-click']);
  });

  it('switches map type without constructing another billable map', async () => {
    const { rerender } = render(
      <GoogleMap apiKey="browser-key" mapId="map-id" mapTypeId="roadmap" />,
    );
    await waitFor(() => expect(mapsMock.state.mapConstructions).toBe(1));

    rerender(<GoogleMap apiKey="browser-key" mapId="map-id" mapTypeId="satellite" />);

    await waitFor(() => expect(mapsMock.state.mapTypeIds).toContain('satellite'));
    expect(mapsMock.state.mapConstructions).toBe(1);
  });

  it('creates the billable map once while selection only replaces markers', async () => {
    const places = [
      { id: 1, name: 'Hütte', coordinates: '47.1,15.2' },
      { id: 2, name: 'See', coordinates: '47.2,15.3' },
    ];
    const { rerender, unmount } = render(
      <GoogleMap apiKey="browser-key" places={places} selectedPlaceId={1} />,
    );

    await waitFor(() => expect(mapsMock.state.markerOptions).toHaveLength(2));
    expect(mapsMock.state.mapConstructions).toBe(1);
    expect(mapsMock.state.fitBoundsCalls).toBe(1);

    rerender(<GoogleMap apiKey="browser-key" places={places} selectedPlaceId={2} />);

    await waitFor(() => expect(mapsMock.state.markerOptions).toHaveLength(4));
    expect(mapsMock.state.mapConstructions).toBe(1);
    expect(mapsMock.state.fitBoundsCalls).toBe(1);
    expect(mapsMock.state.removedMarkers).toBe(2);

    unmount();
    expect(mapsMock.state.removedMarkers).toBe(4);
  });

  it('shows an honest empty state when no marker can be placed', async () => {
    const { getByText } = render(
      <GoogleMap apiKey="browser-key" places={[{ id: 1, name: 'Ohne Pin' }]} />,
    );

    expect(getByText('Keine Orte mit Koordinaten vorhanden.')).toBeInTheDocument();
  });
});
