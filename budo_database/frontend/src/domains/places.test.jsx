import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';

import App from '../App';
import { parseRoute } from '../routes';
import { ImageUploadPage, PlaceDetailPage, PlacesPage } from './places';

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

  it('omits the redundant actions column from the places list', () => {
    render(<PlacesPage data={{
      places: [{ id: 4, name: 'Ada Hütte', maps_link: '', parking_link: '', coordinates: null }],
    }} />);

    expect(screen.queryByRole('columnheader', { name: 'Aktionen' })).not.toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Ada Hütte' })).toHaveAttribute('href', '/auslagerorte/4/');
  });

  it('renders both travel times and sorts places by driving minutes', async () => {
    const user = userEvent.setup();
    render(<PlacesPage data={{
      places: [
        { id: 4, name: 'Ferner See', driving_minutes: 38, walking_minutes: 125, maps_link: '', parking_link: '', coordinates: null },
        { id: 5, name: 'Naher Wald', driving_minutes: 9, walking_minutes: 32, maps_link: '', parking_link: '', coordinates: null },
      ],
    }} />);

    expect(screen.getByText('Mit dem Auto: 38 min')).toBeInTheDocument();
    expect(screen.getByText('Zu Fuß: 125 min')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Reisezeit vom BuDo sortieren' }));
    const names = screen.getAllByRole('row').slice(1).map(row => (
      within(row).getByRole('link', { name: /Wald|See/ }).textContent
    ));
    expect(names).toEqual(['Naher Wald', 'Ferner See']);
  });

  it('shows missing travel times per mode instead of inventing a duration', () => {
    render(<PlacesPage data={{
      places: [{
        id: 4,
        name: 'Ort ohne Route',
        driving_minutes: null,
        walking_minutes: null,
        maps_link: '',
        parking_link: '',
        coordinates: null,
      }],
    }} />);

    const row = screen.getByRole('link', { name: 'Ort ohne Route' }).closest('tr');
    expect(within(row).getByText('Mit dem Auto: ---')).toBeInTheDocument();
    expect(within(row).getByText('Zu Fuß: ---')).toBeInTheDocument();
  });

  it('renders place tags and filters with AND semantics using accessible chips', async () => {
    const user = userEvent.setup();
    render(<PlacesPage data={{
      available_tags: ['Badeplatz', 'Schlechtwetter-tauglich'],
      places: [
        { id: 4, name: 'Badesee', tags: ['Badeplatz'], maps_link: '', parking_link: '', coordinates: null },
        { id: 5, name: 'Hallenbad', tags: ['Badeplatz', 'Schlechtwetter-tauglich'], maps_link: '', parking_link: '', coordinates: null },
        { id: 6, name: 'Museum', tags: ['Schlechtwetter-tauglich'], maps_link: '', parking_link: '', coordinates: null },
      ],
    }} />);

    const filters = screen.getByRole('group', { name: 'Nach Tags filtern' });
    const swimming = within(filters).getByRole('button', { name: 'Badeplatz' });
    const rainyDay = within(filters).getByRole('button', { name: 'Schlechtwetter-tauglich' });
    expect(swimming).toHaveAttribute('aria-pressed', 'false');
    expect(screen.getAllByText('Badeplatz')).toHaveLength(3);

    await user.click(swimming);
    expect(swimming).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByRole('link', { name: 'Badesee' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Hallenbad' })).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: 'Museum' })).not.toBeInTheDocument();

    await user.click(rainyDay);
    expect(screen.queryByRole('link', { name: 'Badesee' })).not.toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Hallenbad' })).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: 'Museum' })).not.toBeInTheDocument();
  });

  it('clears tag filters in one action and explains an empty result', async () => {
    const user = userEvent.setup();
    render(<PlacesPage data={{
      available_tags: ['Badeplatz', 'Wanderung'],
      places: [
        { id: 4, name: 'Badesee', tags: ['Badeplatz'], maps_link: '', parking_link: '', coordinates: null },
        { id: 5, name: 'Waldweg', tags: ['Wanderung'], maps_link: '', parking_link: '', coordinates: null },
      ],
    }} />);

    const filters = screen.getByRole('group', { name: 'Nach Tags filtern' });
    await user.click(within(filters).getByRole('button', { name: 'Badeplatz' }));
    await user.click(within(filters).getByRole('button', { name: 'Wanderung' }));

    expect(screen.getByText('Keine Auslagerorte entsprechen den ausgewählten Tags.')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Tagfilter zurücksetzen' }));
    expect(screen.getByRole('link', { name: 'Badesee' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Waldweg' })).toBeInTheDocument();
    expect(within(filters).getByRole('button', { name: 'Badeplatz' })).toHaveAttribute('aria-pressed', 'false');
    expect(within(filters).getByRole('button', { name: 'Wanderung' })).toHaveAttribute('aria-pressed', 'false');
  });

  it('restores tag filters from a shareable URL and keeps changes in the URL', async () => {
    window.history.pushState({}, '', '/auslagerorte-list?tag=Badeplatz&tag=Wanderung');
    const user = userEvent.setup();
    render(<PlacesPage data={{
      available_tags: ['Badeplatz', 'Wanderung'],
      places: [
        { id: 4, name: 'Badesee', tags: ['Badeplatz'], maps_link: '', parking_link: '', coordinates: null },
        { id: 5, name: 'Badeweg', tags: ['Badeplatz', 'Wanderung'], maps_link: '', parking_link: '', coordinates: null },
      ],
    }} />);

    const filters = screen.getByRole('group', { name: 'Nach Tags filtern' });
    expect(within(filters).getByRole('button', { name: 'Badeplatz' })).toHaveAttribute('aria-pressed', 'true');
    expect(within(filters).getByRole('button', { name: 'Wanderung' })).toHaveAttribute('aria-pressed', 'true');
    expect(screen.queryByRole('link', { name: 'Badesee' })).not.toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Badeweg' })).toBeInTheDocument();

    await user.click(within(filters).getByRole('button', { name: 'Wanderung' }));
    expect(new URLSearchParams(window.location.search).getAll('tag')).toEqual(['Badeplatz']);
  });

  it('shows an Auslagerort tags on its detail page', () => {
    render(<PlaceDetailPage data={{
      csrf_token: 'token',
      places: [{
        id: 4,
        name: 'Ada Hütte',
        tags: ['Badeplatz', 'Wanderung'],
        coordinates: null,
        notes: [],
        images: [],
      }],
    }} id="4" />);

    const tags = screen.getByRole('list', { name: 'Tags' });
    expect(within(tags).getAllByRole('listitem').map(item => item.textContent)).toEqual([
      'Badeplatz',
      'Wanderung',
    ]);
  });

  it('shows both travel times alongside the coordinates on the detail page', () => {
    vi.stubGlobal('ResizeObserver', class {
      observe() {}
      disconnect() {}
    });
    render(<PlaceDetailPage data={{
      csrf_token: 'token',
      places: [{
        id: 4,
        name: 'Ada Hütte',
        tags: [],
        coordinates: '48.2,15.2',
        driving_minutes: 12,
        walking_minutes: 47,
        notes: [],
        images: [],
      }],
    }} id="4" />);

    expect(screen.getByText('Koordinaten').closest('p')).toHaveTextContent('48.2,15.2');
    expect(screen.getByText('Mit dem Auto vom BuDo').closest('p')).toHaveTextContent('12 min');
    expect(screen.getByText('Zu Fuß vom BuDo').closest('p')).toHaveTextContent('47 min');
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

  it('declares the Auslagerorte page contracts', () => {
    expect([
      '/auslagerorte-list',
      '/auslagerorte/create',
      '/auslagerorte/4/update',
      '/auslagerorte/4/upload-image/',
      '/auslagerorte/4',
    ].map(path => {
      const route = parseRoute(path);
      return route.readContractKey;
    })).toEqual([
      'places-list',
      'place-create',
      'place-update',
      'place-images',
      'place-detail',
    ]);
  });

  it('refreshes a saved note in place without requesting bootstrap again', async () => {
    window.history.pushState({}, '', '/auslagerorte/4');
    let detailReads = 0;
    const place = {
      id: 4,
      name: 'Ada Hütte',
      coordinates: null,
      notes: [],
      images: [],
    };
    const fetchMock = vi.fn(async url => {
      if (url === '/api/bootstrap/') {
        return response({
          authenticated: true,
          csrf_token: 'csrf-token',
          messages: [],
          profile: { id: 1, rufname: 'Ada' },
          turnus: { id: 2, label: 'T2' },
          permissions: {},
          search_index: { kids: [], focuses: [], places: [{ id: 4, name: 'Ada Hütte' }] },
        });
      }
      if (url === '/api/route-data/place-detail/?id=4') {
        detailReads += 1;
        return response({
          places: [{
            ...place,
            notes: detailReads === 1 ? [] : [{ id: 7, author: 'ada', date: '2026-07-17', text: 'Wasser abdrehen' }],
          }],
        });
      }
      if (url === '/api/form-submit/') {
        return response({ ok: true, redirect: '/auslagerorte/4/' });
      }
      throw new Error(`Unexpected request: ${url}`);
    });
    vi.stubGlobal('fetch', fetchMock);

    render(<App fetchImpl={fetchMock} />);
    const note = await screen.findByPlaceholderText('Kommentar...');
    fireEvent.change(note, { target: { value: 'Wasser abdrehen' } });
    fireEvent.click(screen.getByRole('button', { name: 'Kommentar senden' }));

    expect(await screen.findByText(/Wasser abdrehen/)).toBeInTheDocument();
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(4));
    expect(fetchMock.mock.calls.map(call => call[0])).toEqual([
      '/api/bootstrap/',
      '/api/route-data/place-detail/?id=4',
      '/api/form-submit/',
      '/api/route-data/place-detail/?id=4',
    ]);
    expect(detailReads).toBe(2);
  });

  it('submits detail notes through the established REST form seam', async () => {
    const onSaved = vi.fn();
    const fetchMock = vi.fn().mockResolvedValue(response({ ok: true }));
    vi.stubGlobal('fetch', fetchMock);
    render(<PlaceDetailPage data={{
      csrf_token: 'csrf-token',
      places: [{ id: 4, name: 'Ada Hütte', coordinates: null, notes: [], images: [] }],
    }} id="4" onSaved={onSaved} />);

    const comment = screen.getByRole('textbox', { name: 'Kommentar' });
    expect(comment.tagName).toBe('TEXTAREA');
    expect(comment).toHaveAttribute('rows', '2');
    expect(comment.form).toHaveAttribute('enctype', 'multipart/form-data');
    fireEvent.change(comment, { target: { value: 'Neue Notiz' } });
    fireEvent.click(screen.getByRole('button', { name: 'Kommentar senden' }));

    await waitFor(() => expect(onSaved).toHaveBeenCalledOnce());
    expect(fetchMock.mock.calls[0][1].body.get('_target')).toBe('/auslagerorte/4/');
    expect(fetchMock.mock.calls[0][1].body.get('notiz')).toBe('Neue Notiz');
  });

  it('uploads comment images and shows them with the comment as well as in Bilder', async () => {
    const onSaved = vi.fn();
    const fetchMock = vi.fn().mockResolvedValue(response({ ok: true }));
    vi.stubGlobal('fetch', fetchMock);
    const place = {
      id: 4,
      name: 'Ada Hütte',
      coordinates: null,
      notes: [{ id: 8, author: 'Ada', date: '2026-07-17', text: 'Feuerstelle', photos: [{ id: 9, url: '/media/damage.jpg', alt: 'Kommentarbild zu Ada Hütte' }] }],
      images: ['/media/damage.jpg'],
    };
    render(<PlaceDetailPage data={{ csrf_token: 'csrf-token', places: [place] }} id="4" onSaved={onSaved} />);

    expect(screen.getAllByRole('img', { name: /Ada Hütte/ })).toHaveLength(2);
    const photo = new File(['photo'], 'damage.jpg', { type: 'image/jpeg' });
    fireEvent.change(screen.getByLabelText('Kommentar-Bilder'), { target: { files: [photo] } });
    expect(within(screen.getByLabelText('Kommentar-Bilder').previousElementSibling).getByText('1')).toBeInTheDocument();
    fireEvent.change(screen.getByPlaceholderText('Kommentar...'), { target: { value: 'Mit Bild' } });
    fireEvent.click(screen.getByRole('button', { name: 'Kommentar senden' }));

    await waitFor(() => expect(onSaved).toHaveBeenCalledOnce());
    const body = fetchMock.mock.calls[0][1].body;
    expect(body.get('notiz')).toBe('Mit Bild');
    expect(body.getAll('images')).toEqual([photo]);
  });
});
