import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';

import App from '../App';
import { parseRoute } from '../routes';
import { ImageUploadPage, PlacesPage } from './places';

const response = (data, { ok = true, status = 200 } = {}) => ({
  ok,
  status,
  json: vi.fn().mockResolvedValue(data),
});

describe('Auslagerorte workflows', () => {
  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
    window.history.pushState({}, '', '/');
  });

  it('requires multiple images and hints accepted file types', () => {
    render(<ImageUploadPage data={{
      csrf_token: 'token',
      places: [{ id: 4, name: 'Test place' }],
    }} id="4" />);

    const input = screen.getByLabelText('Select multiple images');
    expect(input).toHaveAttribute('type', 'file');
    expect(input).toBeRequired();
    expect(input).toHaveAttribute('multiple');
    expect(input).toHaveAttribute('accept', 'image/*');
  });

  it('uses the folded list contract for historic detail routes', () => {
    expect([
      '/auslagerorte-list',
      '/auslagerorte/create',
      '/auslagerorte/4/update',
      '/auslagerorte/4/upload-image/',
      '/auslagerorte/4',
    ].map(path => parseRoute(path).readContractKey)).toEqual([
      'places-list',
      'place-create',
      'place-update',
      'place-images',
      'places-list',
    ]);
  });

  it('refreshes the folded list after a sidebar comment without reloading bootstrap', async () => {
    window.history.pushState({}, '', '/auslagerorte/4');
    let listReads = 0;
    const place = { id: 4, name: 'Ada Hütte', tags: [], coordinates: null, notes: [], images: [] };
    const fetchMock = vi.fn(async url => {
      if (url === '/api/bootstrap/') return response({
        authenticated: true,
        csrf_token: 'csrf-token',
        messages: [],
        profile: { id: 1, rufname: 'Ada' },
        turnus: { id: 2, label: 'T2' },
        permissions: {},
        search_index: { kids: [], focuses: [], places: [{ id: 4, name: 'Ada Hütte' }] },
      });
      if (url === '/api/route-data/places-list/?id=4') {
        listReads += 1;
        return response({ places: [{ ...place, notes: listReads === 1 ? [] : [{ id: 7, author: 'ada', date: '2026-07-17', text: 'Wasser abdrehen', photos: [] }] }], available_tags: [] });
      }
      if (url === '/api/form-submit/') return response({ ok: true });
      throw new Error(`Unexpected request: ${url}`);
    });
    vi.stubGlobal('fetch', fetchMock);

    render(<App fetchImpl={fetchMock} />);
    const note = await screen.findByRole('textbox', { name: 'Kommentar' });
    fireEvent.change(note, { target: { value: 'Wasser abdrehen' } });
    fireEvent.click(screen.getByRole('button', { name: 'Kommentar senden' }));

    expect(await screen.findByText(/Wasser abdrehen/)).toBeInTheDocument();
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(4));
    expect(fetchMock.mock.calls.map(call => call[0])).toEqual([
      '/api/bootstrap/',
      '/api/route-data/places-list/?id=4',
      '/api/form-submit/',
      '/api/route-data/places-list/?id=4',
    ]);
  });

  it('excludes places with unknown walking times from a walking maximum', () => {
    window.history.pushState({}, '', '/auslagerorte-list/?max_walk=30');
    const MapComponent = ({ places }) => (
      <div aria-label="Testkarte">{places.map(place => place.name).join(', ')}</div>
    );

    render(<PlacesPage data={{
      available_tags: [],
      places: [
        { id: 1, name: 'Unknown', tags: [], walking_minutes: null },
        { id: 2, name: 'Near', tags: [], walking_minutes: 20 },
      ],
    }} MapComponent={MapComponent} />);

    expect(screen.getByLabelText('Testkarte')).toHaveTextContent('Near');
    expect(screen.getByLabelText('Testkarte')).not.toHaveTextContent('Unknown');
  });

  it('returns a historic detail deep link to the filtered trailing-slash list URL', async () => {
    const user = userEvent.setup();
    window.history.pushState({}, '', '/auslagerorte/4?q=Hütte&tag=ruhig');
    render(<PlacesPage data={{
      available_tags: ['ruhig'],
      places: [{
        id: 4,
        name: 'Ada Hütte',
        tags: ['ruhig'],
        coordinates: null,
        notes: [],
        images: [],
      }],
    }} initialPlaceId="4" MapComponent={() => <div />} />);

    await user.click(screen.getByRole('button', { name: 'Zurück zur Liste' }));

    expect(window.location.pathname).toBe('/auslagerorte-list/');
    expect(window.location.search).toBe('?q=H%C3%BCtte&tag=ruhig');
  });

  it('returns a deep link through App navigation and restores list header actions', async () => {
    const user = userEvent.setup();
    window.history.pushState({}, '', '/auslagerorte/4?q=Hütte');
    const place = {
      id: 4,
      name: 'Ada Hütte',
      tags: [],
      coordinates: null,
      notes: [],
      images: [],
    };
    const fetchMock = vi.fn(async url => {
      if (url === '/api/bootstrap/') return response({
        authenticated: true,
        csrf_token: 'csrf-token',
        messages: [],
        permissions: {},
        search_index: { kids: [], focuses: [], places: [place] },
      });
      if (url === '/api/route-data/places-list/?id=4') {
        return response({ places: [place], available_tags: [] });
      }
      if (url === '/api/route-data/places-list/') {
        return response({ places: [place], available_tags: [] });
      }
      throw new Error(`Unexpected request: ${url}`);
    });

    render(<App fetchImpl={fetchMock} />);
    expect(await screen.findByRole('heading', { name: 'Ada Hütte', level: 1 })).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Zurück zur Liste' }));

    expect(await screen.findByRole('heading', { name: 'Auslagerorte', level: 1 })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Ort hinzufügen' })).toHaveAttribute(
      'href',
      '/auslagerorte/create',
    );
    expect(window.location.pathname).toBe('/auslagerorte-list/');
    expect(window.location.search).toBe('?q=H%C3%BCtte');
  });

  it('keeps the gallery modal keyboard-contained, restores focus, and supports touch swipes', async () => {
    const user = userEvent.setup();
    const place = {
      id: 4,
      name: 'Ada Hütte',
      tags: [],
      coordinates: null,
      notes: [],
      images: ['/one.jpg', '/two.jpg'],
    };
    render(<PlacesPage data={{ available_tags: [], places: [place] }} MapComponent={() => <div />} />);
    await user.click(screen.getByRole('button', { name: /Ada Hütte/ }));
    const trigger = screen.getByRole('button', { name: 'Galerie öffnen' });
    await user.click(trigger);

    const dialog = screen.getByRole('dialog', { name: 'Bilder von Ada Hütte' });
    expect(dialog).toContainElement(document.activeElement);
    const image = within(dialog).getByAltText('Ada Hütte 1');
    fireEvent.touchStart(image, { touches: [{ clientX: 100, clientY: 10 }] });
    fireEvent.touchEnd(image, { changedTouches: [{ clientX: 20, clientY: 12 }] });
    expect(within(dialog).getByAltText('Ada Hütte 2')).toBeInTheDocument();

    fireEvent.keyDown(window, { key: 'ArrowLeft' });
    expect(within(dialog).getByAltText('Ada Hütte 1')).toBeInTheDocument();
    await user.keyboard('{Escape}');
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    expect(trigger).toHaveFocus();
  });
});
