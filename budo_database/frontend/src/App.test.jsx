import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import App from './App';

const response = (data, { ok = true, status = 200 } = {}) => ({
  ok,
  status,
  json: vi.fn().mockResolvedValue(data),
});

function openTurnusDialog() {
  fireEvent.click(screen.getByRole('button', { name: 'Turnus wechseln' }));
  return screen.getByRole('dialog', { name: 'Turnus wechseln' });
}

function chooseTurnus(label) {
  fireEvent.click(within(openTurnusDialog()).getByRole('button', { name: label }));
}

describe('application loading', () => {
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
    window.history.pushState({}, '', '/');
  });

  it('loads only bootstrap for a public page', async () => {
    window.history.pushState({}, '', '/login/');
    const fetchImpl = vi.fn().mockResolvedValue(response({
      authenticated: false,
      csrf_token: 'token',
      messages: [],
    }));

    render(<App fetchImpl={fetchImpl} />);

    expect(screen.getByText('Sitzung wird geladen…')).toBeInTheDocument();
    expect(await screen.findByRole('heading', { name: 'Login', level: 1 })).toBeInTheDocument();
    expect(fetchImpl).toHaveBeenCalledOnce();
    expect(fetchImpl).toHaveBeenCalledWith('/api/bootstrap/', { credentials: 'same-origin' });
  });

  it('shows bootstrap messages in the global toast viewport', async () => {
    window.history.pushState({}, '', '/login/');
    const fetchImpl = vi.fn().mockResolvedValue(response({
      authenticated: false,
      csrf_token: 'token',
      messages: [{ text: 'Hi Ada, welcome back!', tags: 'success' }],
    }));

    render(<App fetchImpl={fetchImpl} />);

    expect(await screen.findByText('Hi Ada, welcome back!')).toBeInTheDocument();
    expect(screen.getByRole('region', { name: 'Benachrichtigungen' })).toBeInTheDocument();
    expect(document.querySelector('.messages')).not.toBeInTheDocument();
  });

  it('does not request protected route data before authentication is known', async () => {
    window.history.pushState({}, '', '/all_kids');
    let resolveBootstrap;
    let resolveRoute;
    const fetchImpl = vi.fn()
      .mockReturnValueOnce(new Promise(resolve => { resolveBootstrap = resolve; }))
      .mockReturnValueOnce(new Promise(resolve => { resolveRoute = resolve; }));

    render(<App fetchImpl={fetchImpl} />);

    expect(fetchImpl).toHaveBeenCalledOnce();
    resolveBootstrap(response({
      authenticated: true,
      csrf_token: 'token',
      messages: [],
      profile: { id: 1, rufname: 'Ada' },
      turnus: { id: 2, label: 'T2' },
      permissions: {},
      search_index: { kids: [], focuses: [], places: [] },
    }));

    expect(await screen.findByText('Seitendaten werden geladen…')).toBeInTheDocument();
    await waitFor(() => expect(fetchImpl).toHaveBeenCalledTimes(2));
    expect(fetchImpl.mock.calls[1][0]).toBe('/api/route-data/kids-directory/');
    resolveRoute(response({ authenticated: true, kids: [], messages: [] }));
  });

  it('builds the Happy Cleaning sidebar from the active-Turnus bootstrap', async () => {
    window.history.pushState({}, '', '/all_kids');
    const fetchImpl = vi.fn()
      .mockResolvedValueOnce(response({
        authenticated: true,
        csrf_token: 'token',
        messages: [],
        profile: { id: 1, rufname: 'Ada' },
        turnus: { id: 2, label: 'T2' },
        permissions: {},
        search_index: { kids: [], focuses: [], places: [] },
        happy_cleaning_events: [
          { id: 7, display_number: 1 },
          { id: 9, display_number: 2 },
        ],
      }))
      .mockResolvedValueOnce(response({ kids: [] }));

    render(<App fetchImpl={fetchImpl} />);

    expect(await screen.findByRole('link', { name: 'Happy Cleaning 2' })).toHaveAttribute(
      'href',
      '/happy-cleaning/9/assignment/',
    );
  });

  it('renders Team management when its Turnus records have no Happy Cleaning events', async () => {
    window.history.pushState({}, '', '/teams/');
    const fetchImpl = vi.fn()
      .mockResolvedValueOnce(response({
        authenticated: true,
        csrf_token: 'token',
        messages: [],
        permissions: {},
        happy_cleaning_events: [],
      }))
      .mockResolvedValueOnce(response({
        years: [{
          year: 2026,
          turnuses: [{
            id: 4,
            label: 'T4-2026',
            members: [],
            pending_requests: [],
            request_summary: { pending: 0 },
          }],
        }],
        people: [],
        can_manage_leitung: true,
        can_manage_memberships: true,
      }));

    render(<App fetchImpl={fetchImpl} />);

    expect(await screen.findByRole('heading', { name: 'T4-2026' })).toBeInTheDocument();
  });

  it('redirects a signed-in user without a Turnus to Team & Turnus', async () => {
    window.history.pushState({}, '', '/all_kids');
    const fetchImpl = vi.fn((url) => {
      if (url === '/api/bootstrap/') {
        return Promise.resolve(response({
          authenticated: true,
          csrf_token: 'token',
          messages: [],
          profile: { id: 1, rufname: 'Ada' },
          turnus: null,
          turnus_selection: { selected_id: null, options: [] },
          permissions: {},
          search_index: { kids: [], focuses: [], places: [] },
          happy_cleaning_events: [],
        }));
      }
      if (url === '/api/route-data/team-management/') {
        return Promise.resolve(response({
          years: [{
            year: 2026,
            turnuses: [{
              id: 4,
              label: 'T4-2026',
              members: [],
              leads: [],
              can_view_team: false,
              request_status: null,
              pending_requests: [],
              request_summary: { pending: 0 },
            }],
          }],
          people: [],
          can_manage_leitung: false,
          can_manage_memberships: false,
        }));
      }
      throw new Error(`Unexpected request: ${url}`);
    });

    render(<App fetchImpl={fetchImpl} />);

    expect(await screen.findByRole('heading', { name: 'T4-2026' })).toBeInTheDocument();
    expect(window.location.pathname).toBe('/teams/');
    expect(fetchImpl).not.toHaveBeenCalledWith('/api/route-data/kids-directory/');
    const navigation = screen.getByRole('navigation', { name: 'Hauptnavigation' });
    expect(within(navigation).getAllByRole('link').map(link => link.textContent)).toEqual([
      'Team & Turnus',
    ]);
    expect(screen.getByRole('link', { name: 'Profil' })).toBeInTheDocument();
  });

  it('keeps Profil reachable for a signed-in user without a Turnus', async () => {
    window.history.pushState({}, '', '/profil/');
    const fetchImpl = vi.fn()
      .mockResolvedValueOnce(response({
        authenticated: true,
        csrf_token: 'token',
        messages: [],
        profile: { id: 1, rufname: 'Ada' },
        turnus: null,
        turnus_selection: { selected_id: null, options: [] },
        permissions: {},
        search_index: { kids: [], focuses: [], places: [] },
        happy_cleaning_events: [],
      }))
      .mockResolvedValueOnce(response({
        profile: {
          id: 1,
          rufname: 'Ada',
          food_display: 'Flexitarisch',
          turnuses: [],
        },
        focuses: [],
      }));

    render(<App fetchImpl={fetchImpl} />);

    expect(await screen.findByRole('heading', { name: 'Ada', level: 2 })).toBeInTheDocument();
    expect(window.location.pathname).toBe('/profil/');
    expect(fetchImpl.mock.calls[1][0]).toBe('/api/route-data/profile/');
  });

  it('refreshes Aktiver Turnus after the signed-in user is added to another Turnus', async () => {
    window.history.pushState({}, '', '/teams/');
    const originalBootstrap = {
      authenticated: true,
      csrf_token: 'token',
      messages: [],
      profile: { id: 1, rufname: 'Ada' },
      turnus: { id: 1, label: 'T1-2026' },
      turnus_selection: { selected_id: 1, options: [{ id: 1, label: 'T1-2026' }] },
      permissions: {},
      search_index: { kids: [], focuses: [], places: [] },
      happy_cleaning_events: [],
    };
    const teamData = {
      years: [{
        year: 2026,
        turnuses: [{
          id: 1, label: 'T1-2026', start: '2026-07-04', end: '2026-07-17',
          excel_uploaded: false, members: [], pending_requests: [], request_summary: { pending: 0 },
        }, {
          id: 2, label: 'T2-2026', start: '2026-07-18', end: '2026-07-31',
          excel_uploaded: false, members: [], pending_requests: [], request_summary: { pending: 0 },
        }],
      }],
      people: [{
        id: 1,
        name: 'Ada Admin',
        email: 'ada@example.test',
        relationships: ['T1-2026'],
        turnus_ids: [1],
        available: false,
      }],
      can_manage_leitung: true,
      can_manage_memberships: true,
      can_create_turnus: true,
    };
    let bootstrapRequests = 0;
    const fetchImpl = vi.fn((url, options = {}) => {
      if (url === '/api/bootstrap/') {
        bootstrapRequests += 1;
        return Promise.resolve(response(bootstrapRequests === 1 ? originalBootstrap : {
          ...originalBootstrap,
          turnus_selection: {
            selected_id: 1,
            options: [{ id: 1, label: 'T1-2026' }, { id: 2, label: 'T2-2026' }],
          },
        }));
      }
      if (url === '/api/route-data/team-management/') return Promise.resolve(response(teamData));
      if (url === '/api/turnusse/2/memberships/' && options.method === 'POST') {
        return Promise.resolve(response({ membership_id: 77, role_label: 'Teamer', team_label: '' }));
      }
      throw new Error(`Unexpected request: ${options.method || 'GET'} ${url}`);
    });

    render(<App fetchImpl={fetchImpl} />);

    await screen.findByRole('button', { name: 'Turnus wechseln' });
    let turnusDialog = openTurnusDialog();
    expect(within(turnusDialog).getByRole('button', { name: /T1-2026/ })).toHaveAttribute(
      'aria-current',
      'true',
    );
    expect(within(turnusDialog).queryByRole('button', { name: 'T2-2026' })).not.toBeInTheDocument();
    fireEvent.click(within(turnusDialog).getByRole('button', { name: 'Abbrechen' }));
    fireEvent.click(screen.getByRole('button', { name: /T2-2026/ }));
    fireEvent.click(screen.getByRole('button', { name: 'Person hinzufügen' }));
    fireEvent.click(await screen.findByRole('button', {
      name: 'Ada Admin als Betreuer:in zu T2-2026 hinzufügen',
    }));
    await screen.findByText('Ada Admin ist jetzt Teamer.');
    fireEvent.click(screen.getByRole('button', { name: 'Dialog schließen' }));

    await waitFor(() => expect(bootstrapRequests).toBe(2));
    turnusDialog = openTurnusDialog();
    expect(within(turnusDialog).getByRole('button', { name: 'T2-2026' })).toBeInTheDocument();
  });

  it('keeps the current page and shows the shared error toast when a Turnus switch fails', async () => {
    window.history.pushState({}, '', '/all_kids');
    const bootstrap = {
      authenticated: true, csrf_token: 'token', messages: [], permissions: {},
      profile: { id: 1, rufname: 'Ada' }, search_index: { kids: [], focuses: [], places: [] },
      turnus: { id: 2, label: 'T2' },
      turnus_selection: { selected_id: 2, options: [{ id: 2, label: 'T2' }, { id: 4, label: 'T4' }] },
    };
    const fetchImpl = vi.fn()
      .mockResolvedValueOnce(response(bootstrap))
      .mockResolvedValueOnce(response({ kids: [] }))
      .mockResolvedValueOnce(response({}, { ok: false, status: 403 }))
      .mockResolvedValueOnce(response(bootstrap));

    render(<App fetchImpl={fetchImpl} />);
    await screen.findByRole('button', { name: 'Turnus wechseln' });
    chooseTurnus('T4');

    expect(await screen.findByText(
      'Der Turnus konnte nicht gewechselt werden. Bitte erneut versuchen.',
      { selector: '.app-toast-description' },
    )).toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: 'Sitzung konnte nicht geladen werden' })).not.toBeInTheDocument();
    expect(screen.getByText('T2', { selector: '[data-slot="active-turnus"]' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Turnus wechseln' })).toBeEnabled();
  });

  it('blocks stale scoped UI and reloads when switch refreshes fail on the network', async () => {
    window.history.pushState({}, '', '/all_kids');
    const bootstrap = {
      authenticated: true, csrf_token: 'token', messages: [], permissions: {},
      profile: { id: 1 }, turnus: { id: 2, label: 'T2' },
      turnus_selection: { selected_id: 2, options: [{ id: 2, label: 'T2' }, { id: 4, label: 'T4' }] },
      search_index: { kids: [], focuses: [], places: [] },
    };
    const fetchImpl = vi.fn()
      .mockResolvedValueOnce(response(bootstrap))
      .mockResolvedValueOnce(response({ kids: [] }))
      .mockResolvedValueOnce(response({ selected_id: 4 }))
      .mockRejectedValueOnce(new TypeError('network down'));

    const reload = vi.fn();
    render(<App fetchImpl={fetchImpl} reload={reload} />);
    await screen.findByRole('button', { name: 'Turnus wechseln' });
    chooseTurnus('T4');

    expect(await screen.findByText('Turnus wird gewechselt…')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Turnus wechseln' })).not.toBeInTheDocument();
    await waitFor(() => expect(reload).toHaveBeenCalledOnce());
  });

  it('serializes rapid Turnus changes while the first selection is pending', async () => {
    window.history.pushState({}, '', '/all_kids');
    const bootstrap = {
      authenticated: true, csrf_token: 'token', messages: [], permissions: {},
      profile: { id: 1 }, turnus: { id: 2, label: 'T2' },
      turnus_selection: {
        selected_id: 2,
        options: [{ id: 2, label: 'T2' }, { id: 4, label: 'T4' }, { id: 6, label: 'T6' }],
      },
      search_index: { kids: [], focuses: [], places: [] },
    };
    let resolveSelection;
    const selection = new Promise(resolve => { resolveSelection = resolve; });
    const fetchImpl = vi.fn()
      .mockResolvedValueOnce(response(bootstrap))
      .mockResolvedValueOnce(response({ kids: [] }))
      .mockReturnValueOnce(selection);

    render(<App fetchImpl={fetchImpl} />);
    const trigger = await screen.findByRole('button', { name: 'Turnus wechseln' });
    chooseTurnus('T4');

    expect(trigger).toBeDisabled();
    expect(trigger).toHaveAttribute('aria-busy', 'true');
    fireEvent.click(trigger);
    expect(screen.queryByRole('button', { name: 'T6' })).not.toBeInTheDocument();
    expect(fetchImpl).toHaveBeenCalledTimes(3);
    expect(fetchImpl.mock.calls[2][1].body).toBe(JSON.stringify({ turnus_id: 4 }));

    resolveSelection(response({}, { ok: false, status: 403 }));
    await waitFor(() => expect(trigger).not.toBeDisabled());
  });

  it('redirects an unauthenticated protected route without loading route data', async () => {
    window.history.pushState({}, '', '/all_kids');
    const fetchImpl = vi.fn().mockResolvedValue(response({
      authenticated: false,
      csrf_token: 'token',
      messages: [],
    }));
    const navigate = vi.fn();

    render(<App fetchImpl={fetchImpl} navigate={navigate} />);

    await waitFor(() => expect(navigate).toHaveBeenCalledWith('/login/?next=%2Fall_kids'));
    expect(fetchImpl).toHaveBeenCalledOnce();
  });

  it('reports bootstrap and route failures independently', async () => {
    const fetchImpl = vi.fn().mockResolvedValue(response({}, { ok: false, status: 503 }));
    const { unmount } = render(<App fetchImpl={fetchImpl} />);

    expect(await screen.findByRole('heading', { name: 'Sitzung konnte nicht geladen werden' })).toBeInTheDocument();
    unmount();

    fetchImpl.mockReset()
      .mockResolvedValueOnce(response({
        authenticated: true,
        csrf_token: 'token',
        messages: [],
        profile: { id: 1 },
        turnus: { id: 2 },
        permissions: {},
        search_index: { kids: [], focuses: [], places: [] },
      }))
      .mockResolvedValueOnce(response({}, { ok: false, status: 500 }));
    render(<App fetchImpl={fetchImpl} />);

    expect(await screen.findByRole('heading', { name: 'Seitendaten konnten nicht geladen werden' })).toBeInTheDocument();
  });

  it('redirects when authentication expires during route loading', async () => {
    window.history.pushState({}, '', '/all_kids');
    const fetchImpl = vi.fn()
      .mockResolvedValueOnce(response({
        authenticated: true,
        csrf_token: 'token',
        messages: [],
        profile: { id: 1 },
        turnus: { id: 2 },
        permissions: {},
        search_index: { kids: [], focuses: [], places: [] },
      }))
      .mockResolvedValueOnce(response(
        { detail: 'Anmeldedaten fehlen.' },
        { ok: false, status: 403 },
      ));
    const navigate = vi.fn();

    render(<App fetchImpl={fetchImpl} navigate={navigate} />);

    await waitFor(() => expect(navigate).toHaveBeenCalledWith('/login/?next=%2Fall_kids'));
    expect(screen.queryByRole('heading', { name: 'Seitendaten konnten nicht geladen werden' })).not.toBeInTheDocument();
  });

  it('renders not found when route data is not found', async () => {
    window.history.pushState({}, '', '/kid_details/999');
    const fetchImpl = vi.fn()
      .mockResolvedValueOnce(response({
        authenticated: true,
        csrf_token: 'token',
        messages: [],
        profile: { id: 1 },
        turnus: { id: 2 },
        permissions: {},
        search_index: { kids: [], focuses: [], places: [] },
      }))
      .mockResolvedValueOnce(response({}, { ok: false, status: 404 }));

    render(<App fetchImpl={fetchImpl} />);

    expect(await screen.findByRole('heading', { name: 'Seite nicht gefunden' })).toBeInTheDocument();
  });
});
