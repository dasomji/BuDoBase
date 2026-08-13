import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';

import App from '../App';
import { parseRoute, routeHeaderAction } from '../routes';
import { ImageUploadPage, PlaceFormPage, PlacesPage, PlaceTagSettingsPage } from './places';

const response = (data, { ok = true, status = 200 } = {}) => ({
  ok,
  status,
  json: vi.fn().mockResolvedValue(data),
});

describe('Auslagerorte workflows', () => {
  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
    delete document.documentElement.requestFullscreen;
    delete document.exitFullscreen;
    delete document.fullscreenElement;
    window.history.pushState({}, '', '/');
  });

  it('distinguishes selected and available tags while preserving selection order', async () => {
    const user = userEvent.setup();
    render(<PlaceFormPage data={{
      csrf_token: 'token',
      places: [{ id: 4, name: 'Hütte', tags: ['Wald'] }],
      available_tags: ['See', 'Wald'],
      tag_catalog: [
        { id: 1, name: 'Wald', icon: 'trees' },
        { id: 2, name: 'See', icon: 'waves' },
      ],
    }} id="4" />);

    expect(screen.getByText(/erster Tag bestimmt das Kartensymbol/)).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /See/ }));
    expect([...document.querySelectorAll('input[name="tags"]')].map(input => input.value)).toEqual(['Wald', 'See']);
    expect(document.querySelector('.lucide-trees')).not.toBeNull();
    expect(document.querySelector('.lucide-waves-horizontal')).not.toBeNull();
  });

  it('shows and initializes the multiline contact field when editing a place', () => {
    render(<PlaceFormPage data={{
      csrf_token: 'token',
      places: [{ id: 4, name: 'Hütte', contact: 'Ada\n+43 123', tags: [] }],
      available_tags: [],
    }} id="4" />);

    const contact = screen.getByRole('textbox', { name: 'Kontakt' });
    expect(contact.tagName).toBe('TEXTAREA');
    expect(contact).toHaveValue('Ada\n+43 123');
    expect(contact).toHaveAttribute('name', 'kontakt');
  });

  it('opens tag creation from the route header and filters the icon catalog', async () => {
    const user = userEvent.setup();
    const setPageState = vi.fn();
    render(routeHeaderAction(parseRoute('/auslagerorte/tags/'), {}, { setPageState }));

    await user.click(screen.getByRole('button', { name: 'Tag hinzufügen' }));
    expect(setPageState.mock.calls[0][0]({ untouched: true })).toEqual({
      untouched: true,
      createTagOpen: true,
    });

    cleanup();
    const mutate = vi.fn().mockResolvedValue({});
    const onCreateOpenChange = vi.fn();
    render(<PlaceTagSettingsPage data={{
      permissions: { delete_tags: true },
      icon_choices: [{ value: 'map-pin', label: 'Ort' }, { value: 'trees', label: 'Wald' }],
      tags: [],
    }} mutate={mutate} createOpen onCreateOpenChange={onCreateOpenChange} />);

    await user.type(screen.getByLabelText('Name'), 'Neu');
    const search = await screen.findByRole('searchbox', { name: 'Symbole suchen' });
    await user.type(search, 'wald');
    expect(screen.queryByRole('button', { name: 'Ort' })).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Wald' }));
    await user.click(screen.getByRole('button', { name: 'Anlegen' }));
    expect(mutate).toHaveBeenCalledWith('/api/place-tags/', { name: 'Neu', icon: 'trees' });
    expect(onCreateOpenChange).toHaveBeenCalledWith(false);
  });

  it('shows compact tag rows, associated places, and edits only on request', async () => {
    const user = userEvent.setup();
    const mutate = vi.fn().mockResolvedValue({});
    render(<PlaceTagSettingsPage data={{
      permissions: { delete_tags: true },
      icon_choices: [{ value: 'map-pin', label: 'Ort' }, { value: 'trees', label: 'Wald' }],
      tags: [{
        id: 3,
        name: 'Bestehend',
        icon: 'trees',
        places: [{ id: 7, name: 'Waldwiese' }],
      }],
    }} mutate={mutate} />);

    expect(screen.queryByRole('textbox', { name: 'Name' })).not.toBeInTheDocument();
    expect(screen.getByRole('heading', { level: 3, name: 'Bestehend' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Bearbeiten' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Löschen' })).toBeInTheDocument();
    expect(screen.getByText('Auslagerorte (1)')).toBeInTheDocument();

    await user.click(screen.getByText('Auslagerorte (1)'));
    expect(screen.getByRole('link', { name: 'Waldwiese' })).toHaveAttribute('href', '/auslagerorte/7');
    await user.click(screen.getByRole('button', { name: 'Bearbeiten' }));
    expect(screen.getByRole('textbox', { name: 'Name' })).toHaveValue('Bestehend');
    expect(await screen.findByRole('searchbox', { name: 'Symbole suchen' })).toBeInTheDocument();
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

  it('opens the native image picker and uploads all selected images immediately', async () => {
    const user = userEvent.setup();
    const onSaved = vi.fn();
    const place = { id: 4, name: 'Ada Hütte', tags: [], coordinates: null, notes: [], images: [] };
    const fetchMock = vi.fn(async url => {
      if (url === '/api/form-submit/') return response({
        ok: true,
        redirect: '/auslagerorte/4/',
      });
      if (url === '/api/route-data/place-detail/?id=4') return response({
        places: [{ ...place, images: ['/media/one.jpg', '/media/two.png'] }],
      });
      throw new Error(`Unexpected request: ${url}`);
    });
    vi.stubGlobal('fetch', fetchMock);
    render(<PlacesPage data={{ csrf_token: 'csrf-token', available_tags: [], places: [place] }} MapComponent={() => <div />} fetchImpl={fetchMock} onSaved={onSaved} />);
    await user.click(screen.getByRole('button', { name: /Ada Hütte/ }));

    const picker = screen.getByLabelText('Bilder auswählen');
    const openPicker = vi.spyOn(picker, 'click');
    await user.click(screen.getByRole('button', { name: 'Bilder hinzufügen' }));
    expect(openPicker).toHaveBeenCalledOnce();
    expect(picker).toHaveAttribute('accept', 'image/*');
    expect(picker).toHaveAttribute('multiple');
    expect(picker).not.toHaveAttribute('capture');

    const files = [
      new File(['one'], 'one.jpg', { type: 'image/jpeg' }),
      new File(['two'], 'two.png', { type: 'image/png' }),
    ];
    fireEvent.change(picker, { target: { files } });

    await waitFor(() => expect(onSaved).toHaveBeenCalledOnce());
    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(fetchMock.mock.calls[0][0]).toBe('/api/form-submit/');
    expect(fetchMock.mock.calls[1][0]).toBe('/api/route-data/place-detail/?id=4');
    const body = fetchMock.mock.calls[0][1].body;
    expect(body.get('_target')).toBe('/auslagerorte/4/upload-image/');
    expect(body.getAll('images')).toEqual(files);
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

  it('offers a design-system map type segment in the page header', async () => {
    const user = userEvent.setup();
    const setPageState = vi.fn();
    render(routeHeaderAction(
      parseRoute('/auslagerorte-list/'),
      {},
      { pageState: { placesMapType: 'roadmap' }, setPageState },
    ));

    const mapTypeSegment = screen.getByRole('group', { name: 'Kartendarstellung' });
    const roadmapButton = screen.getByRole('button', { name: 'Karte' });
    const satelliteButton = screen.getByRole('button', { name: 'Satellit' });
    expect(mapTypeSegment).toHaveClass('max-[900px]:rounded-full');
    expect(roadmapButton).toHaveClass('h-8', 'max-[900px]:rounded-l-full', 'max-[900px]:rounded-r-none');
    expect(satelliteButton).toHaveClass('h-8', 'max-[900px]:rounded-r-full', 'max-[900px]:rounded-l-none');
    expect(roadmapButton).toHaveAttribute('aria-pressed', 'true');
    await user.click(satelliteButton);
    expect(screen.queryByRole('button', { name: /Vollbild/ })).not.toBeInTheDocument();

    const update = setPageState.mock.calls[0][0];
    expect(update({ placesMapType: 'roadmap', untouched: true })).toEqual({
      placesMapType: 'satellite',
      untouched: true,
    });
  });

  it('updates only the saved place after a sidebar comment without entering route loading', async () => {
    window.history.pushState({}, '', '/auslagerorte/4');
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
        return response({ places: [place], available_tags: [] });
      }
      if (url === '/api/form-submit/') return response({ ok: true });
      if (url === '/api/route-data/place-detail/?id=4') return response({
        places: [{ ...place, notes: [{ id: 7, author: 'ada', date: '2026-07-17', text: 'Wasser abdrehen', photos: [] }] }],
      });
      throw new Error(`Unexpected request: ${url}`);
    });
    vi.stubGlobal('fetch', fetchMock);

    render(<App fetchImpl={fetchMock} />);
    const note = await screen.findByRole('textbox', { name: 'Kommentar' });
    const detail = screen.getByRole('complementary', { name: 'Ada Hütte' });
    fireEvent.change(note, { target: { value: 'Wasser abdrehen' } });
    fireEvent.click(screen.getByRole('button', { name: 'Kommentar senden' }));

    expect(await screen.findByText(/Wasser abdrehen/)).toBeInTheDocument();
    expect(screen.queryByText('Seitendaten werden geladen…')).not.toBeInTheDocument();
    expect(screen.getByRole('complementary', { name: 'Ada Hütte' })).toBe(detail);
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(4));
    expect(fetchMock.mock.calls.map(call => call[0])).toEqual([
      '/api/bootstrap/',
      '/api/route-data/places-list/?id=4',
      '/api/form-submit/',
      '/api/route-data/place-detail/?id=4',
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

  it('centers a single gallery image without previous or next controls', async () => {
    const user = userEvent.setup();
    let fullscreenElement = null;
    document.documentElement.requestFullscreen = vi.fn(async () => {
      fullscreenElement = document.documentElement;
    });
    document.exitFullscreen = vi.fn(async () => {
      fullscreenElement = null;
    });
    Object.defineProperty(document, 'fullscreenElement', {
      configurable: true,
      get: () => fullscreenElement,
    });
    const place = {
      id: 4,
      name: 'Ada Hütte',
      tags: [],
      coordinates: null,
      notes: [],
      images: ['/only.jpg'],
    };
    render(<PlacesPage data={{ available_tags: [], places: [place] }} MapComponent={() => <div />} />);
    await user.click(screen.getByRole('button', { name: /Ada Hütte/ }));
    await user.click(screen.getByRole('button', { name: 'Galerie öffnen' }));

    expect(document.documentElement.requestFullscreen).toHaveBeenCalledWith({ navigationUI: 'hide' });
    const dialog = screen.getByRole('dialog', { name: 'Bilder von Ada Hütte' });
    expect(within(dialog).getByAltText('Ada Hütte 1')).toHaveClass('justify-self-center');
    expect(within(dialog).queryByRole('button', { name: 'Vorheriges Bild' })).not.toBeInTheDocument();
    expect(within(dialog).queryByRole('button', { name: 'Nächstes Bild' })).not.toBeInTheDocument();
    expect(within(dialog).queryByText('1 / 1')).not.toBeInTheDocument();
    await user.click(within(dialog).getByRole('button', { name: 'Galerie schließen' }));
    await waitFor(() => expect(document.exitFullscreen).toHaveBeenCalledOnce());
  });

  it('opens comment photos in the gallery and shows the associated comment', async () => {
    const user = userEvent.setup();
    const place = {
      id: 4,
      name: 'Ada Hütte',
      tags: [],
      coordinates: null,
      images: [],
      gallery_images: [{
        id: 19,
        url: '/damage.jpg',
        alt: 'Kommentarbild zu Ada Hütte',
        comment_text: 'Das Gatter bitte schließen.',
      }],
      notes: [{
        id: 7,
        author: 'Ada',
        date: '2026-07-17',
        text: 'Das Gatter bitte schließen.',
        photos: [{ id: 19, url: '/damage.jpg', alt: 'Kommentarbild zu Ada Hütte' }],
      }],
    };
    render(<PlacesPage data={{ available_tags: [], places: [place] }} MapComponent={() => <div />} />);
    await user.click(screen.getByRole('button', { name: /Ada Hütte/ }));
    await user.click(screen.getByRole('button', { name: 'Kommentarbild öffnen: Das Gatter bitte schließen.' }));

    const dialog = screen.getByRole('dialog', { name: 'Bilder von Ada Hütte' });
    expect(within(dialog).getByText('Das Gatter bitte schließen.')).toBeInTheDocument();
    expect(within(dialog).getByAltText('Kommentarbild zu Ada Hütte')).toBeInTheDocument();
  });

  it('shows permission-gated place deletion and requires the exact place name', async () => {
    const user = userEvent.setup();
    const mutate = vi.fn().mockResolvedValue({});
    const navigateRoute = vi.fn();
    const place = { id: 4, name: 'Ada Hütte', tags: [], coordinates: null, notes: [], images: [] };
    render(<PlacesPage data={{
      available_tags: [],
      permissions: { delete_places: true },
      places: [place],
    }} MapComponent={() => <div />} mutate={mutate} navigateRoute={navigateRoute} />);
    await user.click(screen.getByRole('button', { name: /Ada Hütte/ }));
    await user.click(screen.getByRole('button', { name: 'Auslagerort löschen' }));

    const confirm = screen.getByRole('button', { name: 'Ada Hütte endgültig löschen' });
    expect(confirm).toBeDisabled();
    await user.type(screen.getByRole('textbox', { name: /zur Bestätigung eingeben/ }), 'Ada Hütte');
    expect(confirm).toBeEnabled();
    await user.click(confirm);

    expect(mutate).toHaveBeenCalledWith(
      '/api/places/4/delete/',
      { confirmation_name: 'Ada Hütte' },
      true,
      false,
    );
    expect(navigateRoute).toHaveBeenCalledWith('/auslagerorte-list/', { replace: true });
  });

  it('confirms permission-gated gallery image deletion from left of close', async () => {
    const user = userEvent.setup();
    const mutate = vi.fn().mockResolvedValue({});
    const place = {
      id: 4,
      name: 'Ada Hütte',
      tags: [],
      coordinates: null,
      notes: [],
      images: ['/only.jpg'],
      gallery_images: [{ id: 23, url: '/only.jpg', alt: 'Bild von Ada Hütte', comment_text: null }],
    };
    render(<PlacesPage data={{
      available_tags: [],
      permissions: { delete_place_images: true },
      places: [place],
    }} MapComponent={() => <div />} mutate={mutate} />);
    await user.click(screen.getByRole('button', { name: /Ada Hütte/ }));
    await user.click(screen.getByRole('button', { name: 'Galerie öffnen' }));

    const dialog = screen.getByRole('dialog', { name: 'Bilder von Ada Hütte' });
    const remove = within(dialog).getByRole('button', { name: 'Bild löschen' });
    const close = within(dialog).getByRole('button', { name: 'Galerie schließen' });
    expect(remove.className).toContain('right-12');
    expect(close.className).toContain('right-0');
    await user.click(remove);
    expect(screen.queryByRole('dialog', { name: 'Bilder von Ada Hütte' })).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Bild endgültig löschen' }));

    expect(mutate).toHaveBeenCalledWith('/api/places/4/images/23/delete/', {});
  });

  it('hides destructive place and image controls without delete permissions', async () => {
    const user = userEvent.setup();
    const place = {
      id: 4,
      name: 'Ada Hütte',
      tags: [],
      coordinates: null,
      notes: [],
      images: ['/only.jpg'],
      gallery_images: [{ id: 23, url: '/only.jpg', alt: 'Bild von Ada Hütte', comment_text: null }],
    };
    render(<PlacesPage data={{ available_tags: [], permissions: {}, places: [place] }} MapComponent={() => <div />} />);
    await user.click(screen.getByRole('button', { name: /Ada Hütte/ }));
    expect(screen.queryByRole('button', { name: 'Auslagerort löschen' })).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Galerie öffnen' }));
    expect(screen.queryByRole('button', { name: 'Bild löschen' })).not.toBeInTheDocument();
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
    const modalElements = [...document.body.querySelectorAll('*')];
    expect(modalElements.find(element => element.classList.contains('z-[var(--z-modal)]'))).toHaveClass('bg-modal-overlay');
    expect(modalElements.some(element => element.classList.contains('z-[calc(var(--z-modal)+1)]'))).toBe(true);
    for (const name of ['Galerie schließen', 'Vorheriges Bild', 'Nächstes Bild']) {
      expect(screen.getByRole('button', { name })).toHaveClass(
        'bg-modal-overlay',
        'text-overlay-foreground',
      );
    }
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
