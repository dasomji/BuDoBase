import { cleanup, render, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

const mapsMock = vi.hoisted(() => {
  const state = { mapOptions: null, markerOptions: [] };
  class Map {
    constructor(_element, options) {
      state.mapOptions = options;
    }

    fitBounds() {}
  }
  class Marker {
    constructor(options) {
      state.markerOptions.push(options);
    }

    addListener() {
      return { remove: vi.fn() };
    }
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
      marker: { Marker },
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
    mapsMock.state.markerOptions = [];
    mapsMock.importLibrary.mockClear();
  });

  it('loads marker constructors officially and keeps map controls clear of overlays', async () => {
    render(<GoogleMap
      apiKey="browser-key"
      places={[{ id: 1, name: 'Hütte', coordinates: '47.1,15.2' }]}
      selectedPlaceId={1}
    />);

    await waitFor(() => expect(mapsMock.state.mapOptions).not.toBeNull());
    expect(mapsMock.importLibrary).toHaveBeenCalledWith('maps');
    expect(mapsMock.importLibrary).toHaveBeenCalledWith('marker');
    expect(mapsMock.importLibrary).toHaveBeenCalledWith('core');
    expect(mapsMock.state.mapOptions.mapTypeControlOptions).toEqual({
      mapTypeIds: ['roadmap', 'satellite'],
      position: 6,
    });
    expect(mapsMock.state.mapOptions.zoomControlOptions).toEqual({ position: 6 });
    expect(mapsMock.state.markerOptions).toHaveLength(1);
    expect(mapsMock.state.markerOptions[0].icon).toMatchObject({ fillColor: expect.any(String) });
  });
});
