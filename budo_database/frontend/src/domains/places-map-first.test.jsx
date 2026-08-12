import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { parseRoute } from '../routes';
import { PlacesPage } from './places';

const response = data => ({ ok: true, status: 200, json: vi.fn().mockResolvedValue(data) });

const places = [
  {
    id: 1,
    name: 'BuDo',
    street: 'Lagerstraße 1',
    city: 'Mönichkirchen',
    postal_code: '2872',
    country: 'Österreich',
    coordinates: '47.51000, 16.01000',
    driving_minutes: 0,
    walking_minutes: 0,
    tags: [],
    images: [],
    notes: [],
  },
  {
    id: 7,
    name: 'Waldwiese',
    street: 'Waldweg 4',
    city: 'Sallingstadt',
    state: 'Niederösterreich',
    postal_code: '3931',
    country: 'Österreich',
    coordinates: '48.50000, 15.00000',
    driving_minutes: 14,
    walking_minutes: 51,
    maps_link: 'https://maps.example.test/waldwiese',
    description: 'Schattiger Lagerplatz am Waldrand.',
    contact: 'Försterin Ada',
    parking_link: 'https://maps.example.test/parkplatz',
    parking_coordinates: '48.51000, 15.01000',
    tags: ['Wanderung', 'Lagerfeuer'],
    images: ['/media/wald-1.webp', '/media/wald-2.webp'],
    notes: [{
      id: 11,
      author: 'Mia',
      date: '2026-08-10',
      day: '10.08.',
      text: 'Das Gatter bitte schließen.',
      photos: [{ id: 12, url: '/media/gatter.webp', alt: 'Kommentarbild zu Waldwiese' }],
    }],
  },
  {
    id: 8,
    name: 'Badesee',
    street: 'Seeweg 2',
    city: 'Sallingstadt',
    postal_code: '3931',
    country: 'Österreich',
    coordinates: '48.60000, 15.10000',
    driving_minutes: 20,
    walking_minutes: 75,
    tags: ['Badeplatz'],
    images: [],
    notes: [],
  },
  {
    id: 9,
    name: 'Scheune ohne Koordinaten',
    street: 'Dorf 9',
    city: 'Sallingstadt',
    postal_code: '3931',
    country: 'Österreich',
    coordinates: null,
    driving_minutes: 8,
    walking_minutes: 25,
    tags: ['Schlechtwetter'],
    images: [],
    notes: [],
  },
];

const data = {
  csrf_token: 'csrf-token',
  available_tags: ['Badeplatz', 'Lagerfeuer', 'Schlechtwetter', 'Wanderung'],
  places,
};

let mapProps;
function MapStub(props) {
  mapProps = props;
  return (
    <section aria-label="Google Karte">
      <span>Basiskarte mit Satellitenansicht</span>
      {props.places.filter(place => place.coordinates).map(place => (
        <button type="button" aria-label={`Marker ${place.name}`} onClick={() => props.onSelectPlace(place.id)} key={place.id}>{place.name}</button>
      ))}
      {props.homePlace && <span>Heimatmarker {props.homePlace.name}</span>}
      {props.parkingCoordinates && <span>Parkspotmarker {props.parkingCoordinates}</span>}
    </section>
  );
}

const renderPage = props => render(<PlacesPage data={data} MapComponent={MapStub} {...props} />);

describe('map-first Auslagerorte', () => {
  beforeEach(() => {
    vi.stubGlobal('ResizeObserver', class {
      observe() {}
      disconnect() {}
    });
  });

  afterEach(() => {
    cleanup();
    mapProps = undefined;
    vi.unstubAllGlobals();
    window.history.replaceState({}, '', '/');
    window.matchMedia = vi.fn().mockImplementation(query => ({
      matches: false,
      media: query,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    }));
  });

  it('keeps the map, result list, AND tag search, walking filter, and URL in one screen', async () => {
    window.history.replaceState({}, '', '/auslagerorte-list/');
    const user = userEvent.setup();
    renderPage();

    expect(screen.getByRole('region', { name: 'Google Karte' })).toBeInTheDocument();
    expect(mapProps.homePlace).toMatchObject({ id: 1, name: 'BuDo' });
    expect(mapProps.places.map(place => place.name)).toEqual(['BuDo', 'Waldwiese', 'Badesee', 'Scheune ohne Koordinaten']);
    expect(screen.getByText('Scheune ohne Koordinaten').closest('button')).toHaveTextContent('kein Pin');

    await user.click(screen.getByRole('button', { name: 'Wanderung' }));
    await user.click(screen.getByRole('button', { name: 'Lagerfeuer' }));
    expect(mapProps.places.map(place => place.name)).toEqual(['Waldwiese']);
    expect(new URLSearchParams(window.location.search).getAll('tag')).toEqual(['Wanderung', 'Lagerfeuer']);

    await user.click(screen.getByRole('button', { name: 'Tagfilter zurücksetzen' }));
    await user.click(screen.getByRole('button', { name: 'Höchstens 60 Minuten zu Fuß' }));
    expect(mapProps.places.map(place => place.name)).toEqual(['BuDo', 'Waldwiese', 'Scheune ohne Koordinaten']);
    expect(new URLSearchParams(window.location.search).get('max_walk')).toBe('60');

    await user.type(screen.getByRole('searchbox', { name: 'Auslagerort suchen' }), 'wald');
    expect(mapProps.places.map(place => place.name)).toEqual(['Waldwiese']);
    expect(new URLSearchParams(window.location.search).get('q')).toBe('wald');
  });

  it('opens complete details from a marker and supports directions, gallery, and back', async () => {
    const user = userEvent.setup();
    renderPage();

    await user.click(screen.getByRole('button', { name: 'Marker Waldwiese' }));
    const details = screen.getByRole('complementary', { name: 'Waldwiese' });
    expect(within(details).getByRole('heading', { name: 'Waldwiese' })).toBeInTheDocument();
    expect(details).toHaveTextContent('Wanderung');
    expect(details).toHaveTextContent('14 min');
    expect(details).toHaveTextContent('51 min');
    expect(details).toHaveTextContent('Schattiger Lagerplatz am Waldrand.');
    expect(details).toHaveTextContent('Waldweg 4');
    expect(details).toHaveTextContent('48.50000, 15.00000');
    expect(details).toHaveTextContent('Försterin Ada');
    expect(details).toHaveTextContent('Das Gatter bitte schließen.');
    expect(within(details).getByRole('img', { name: 'Kommentarbild zu Waldwiese' })).toBeInTheDocument();
    expect(within(details).getByRole('link', { name: 'Bearbeiten' })).toHaveAttribute('href', '/auslagerorte/7/update');
    expect(within(details).getByRole('link', { name: 'Route zur Adresse' })).toHaveAttribute(
      'href',
      'https://www.google.com/maps/dir/?api=1&destination=Waldweg%204%2C%203931%20Sallingstadt%2C%20%C3%96sterreich',
    );
    expect(within(details).getByRole('link', { name: 'Route zum Parkspot' })).toHaveAttribute(
      'href',
      'https://www.google.com/maps/dir/?api=1&destination=48.51000%2C15.01000',
    );
    expect(mapProps.parkingCoordinates).toBe('48.51000, 15.01000');

    await user.click(within(details).getByRole('button', { name: 'Galerie öffnen' }));
    expect(screen.getByRole('dialog', { name: 'Bilder von Waldwiese' })).toHaveTextContent('1 / 2');
    fireEvent.keyDown(window, { key: 'ArrowRight' });
    expect(screen.getByRole('dialog', { name: 'Bilder von Waldwiese' })).toHaveTextContent('2 / 2');
    fireEvent.keyDown(window, { key: 'Escape' });
    expect(screen.queryByRole('dialog', { name: 'Bilder von Waldwiese' })).not.toBeInTheDocument();

    await user.click(within(details).getByRole('button', { name: 'Zurück zur Liste' }));
    expect(screen.queryByRole('complementary', { name: 'Waldwiese' })).not.toBeInTheDocument();
  });

  it('submits a comment with photos from the sidebar through the existing endpoint', async () => {
    const onSaved = vi.fn();
    const fetchMock = vi.fn().mockResolvedValue(response({ ok: true }));
    vi.stubGlobal('fetch', fetchMock);
    const user = userEvent.setup();
    renderPage({ initialPlaceId: '7', onSaved });

    const comment = screen.getByRole('textbox', { name: 'Kommentar' });
    await user.type(comment, 'Neuer Hinweis');
    const photo = new File(['gate'], 'gatter.jpg', { type: 'image/jpeg' });
    await user.upload(screen.getByLabelText('Kommentar-Bilder'), photo);
    await user.click(screen.getByRole('button', { name: 'Kommentar senden' }));

    await waitFor(() => expect(onSaved).toHaveBeenCalledOnce());
    const body = fetchMock.mock.calls[0][1].body;
    expect(body.get('_target')).toBe('/auslagerorte/7/');
    expect(body.get('notiz')).toBe('Neuer Hinweis');
    expect(body.getAll('images')).toEqual([photo]);
  });

  it('turns historic detail routes into the list contract with the selected Ort open', () => {
    const route = parseRoute('/auslagerorte/7/');
    expect(route.readContractKey).toBe('places-list');
    const page = route.render({ route, data });
    expect(page.type).toBe(PlacesPage);
    expect(page.props.initialPlaceId).toBe('7');
  });

  it('uses mutually exclusive mobile list and detail sheets with peek gestures', async () => {
    window.matchMedia = vi.fn().mockImplementation(query => ({
      matches: query === '(max-width: 900px)',
      media: query,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    }));
    const user = userEvent.setup();
    renderPage();

    const listToggle = screen.getByRole('button', { name: 'Liste ausklappen' });
    expect(listToggle).toHaveTextContent('4 Auslagerorte');
    await user.click(listToggle);
    expect(screen.getByRole('button', { name: 'Liste einklappen' })).toHaveAttribute('aria-expanded', 'true');
    await user.click(screen.getByRole('button', { name: /^Waldwiese/ }));

    expect(screen.queryByRole('button', { name: /Liste (ein|aus)klappen/ })).not.toBeInTheDocument();
    const gallery = screen.getByRole('button', { name: 'Galerie öffnen' });
    fireEvent.touchStart(gallery, { touches: [{ clientY: 100 }] });
    fireEvent.touchEnd(gallery, { changedTouches: [{ clientY: 180 }] });
    const peek = screen.getByRole('button', { name: 'Details ausklappen' });
    expect(peek).toHaveTextContent('Waldwiese');
    expect(peek).toHaveTextContent('14 min');
    expect(screen.queryByRole('button', { name: 'Liste ausklappen' })).not.toBeInTheDocument();

    fireEvent.touchStart(peek, { touches: [{ clientY: 180 }] });
    fireEvent.touchEnd(peek, { changedTouches: [{ clientY: 100 }] });
    expect(screen.getByRole('complementary', { name: 'Waldwiese' })).toBeInTheDocument();
  });
});
