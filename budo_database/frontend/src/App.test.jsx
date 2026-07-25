import { cleanup, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import App from './App';

const response = (data, { ok = true, status = 200 } = {}) => ({
  ok,
  status,
  json: vi.fn().mockResolvedValue(data),
});

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
