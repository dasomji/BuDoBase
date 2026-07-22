import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import App from '../App';
import { parseRoute } from '../routes';
import { DashboardPage } from './dashboard';

const emptyPage = { items: [], next_cursor: null, has_more: false, limit: 20 };

const dashboardData = (activity = {}) => ({
  profile: {
    focus_ids: [11],
    budo_family: 'M',
  },
  team: [],
  totals: {
    pocket_money_paid: 20,
    pocket_money: 18,
    team_money: 12,
    checked_in: 1,
    kids: 1,
    train_arrival: 1,
    train_departure: 0,
  },
  kids: [{
    id: 7,
    full_name: 'Grace Hopper',
    present: true,
    age: 14,
    sex: 'weiblich',
    weeks: 1,
    budo_experience: false,
    birthday: '2012-07-02',
    birthday_during_turnus: true,
    food: '🌱 - glutenfrei',
    special_food: 'glutenfrei',
    drugs: 'Asthmaspray',
    illness: 'Allergie',
    budo_family: 'M',
    assigned_focus_weeks: ['w1', 'w2'],
  }],
  focuses: [
    { id: 11, name: 'Wald', week: 'w1', kid_ids: [7] },
    { id: 12, name: 'See', week: 'w2', kid_ids: [7] },
  ],
  focus_assignments_complete: { w1: true, w2: true },
  activity: {
    notes: emptyPage,
    first_aid: emptyPage,
    transactions: emptyPage,
    ...activity,
  },
  turnus: { label: 'T2' },
});

const response = (data, { ok = true, status = 200 } = {}) => ({
  ok,
  status,
  json: vi.fn().mockResolvedValue(data),
});

function setDashboardViewport(width) {
  vi.spyOn(window, 'matchMedia').mockImplementation(query => {
    const maxWidth = Number(query.match(/max-width:\s*(\d+)px/)?.[1]);
    return {
      matches: Number.isFinite(maxWidth) && width <= maxWidth,
      media: query,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    };
  });
}

describe('dashboard page', () => {
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
    window.history.pushState({}, '', '/');
  });

  it('renders exactly the requested operational dashboard cards', () => {
    render(<DashboardPage data={dashboardData()} />);

    for (const heading of [
      'Kinder: 1',
      'Notizen',
      'Erste Hilfe',
      'Meine BuDo-Familie',
      'Mein SWP 1',
      'Mein SWP 2',
      'Erstes Mal im BuDO: 1/1',
      'Einwöchige: 1',
      'Gesundheitliches',
      'Essen & Allergien',
      'Geburtstagskinder: 1',
      'Verabschiedungsliste: 0',
      'Taschengeldtransaktionen',
    ]) {
      expect(screen.getByRole('heading', { name: heading })).toBeInTheDocument();
    }
    for (const removed of ['Mein Profil', 'Team', 'Finanzen', 'Speziallisten']) {
      expect(screen.queryByRole('heading', { name: removed })).not.toBeInTheDocument();
    }
    expect(screen.getAllByRole('link', { name: 'Grace Hopper' }).length).toBeGreaterThan(0);
    expect(screen.getByRole('link', { name: 'Wald' })).toHaveAttribute('href', '/schwerpunkt/11/');
    expect(screen.getByRole('link', { name: 'See' })).toHaveAttribute('href', '/schwerpunkt/12/');
  });

  it.each([
    [1400, [
      ['db-kinderübersicht', 'db-budo-familie', 'db-ersties', 'db-essen', 'db-geld'],
      ['db-notizen', 'db-swp-1', 'db-einwöchig', 'db-geburtstagskinder'],
      ['db-erste-hilfe', 'db-swp-2', 'db-gesundheit', 'db-sechzehner'],
    ]],
    [1000, [
      ['db-kinderübersicht', 'db-erste-hilfe', 'db-swp-1', 'db-ersties', 'db-gesundheit', 'db-geburtstagskinder', 'db-geld'],
      ['db-notizen', 'db-budo-familie', 'db-swp-2', 'db-einwöchig', 'db-essen', 'db-sechzehner'],
    ]],
    [700, [[
      'db-kinderübersicht', 'db-notizen', 'db-erste-hilfe', 'db-budo-familie', 'db-swp-1', 'db-swp-2',
      'db-ersties', 'db-einwöchig', 'db-gesundheit', 'db-essen', 'db-geburtstagskinder', 'db-sechzehner', 'db-geld',
    ]]],
  ])('stacks cards without row gaps in fixed flex columns at %ipx', (width, expectedColumns) => {
    setDashboardViewport(width);

    const { container } = render(<DashboardPage data={dashboardData()} />);
    const actualColumns = Array.from(container.querySelectorAll('.dashboard-column'), column => (
      Array.from(column.children, card => card.id)
    ));

    expect(actualColumns).toEqual(expectedColumns);
  });

  it('waits to show each personal SWP until all present kids are assigned for that week', () => {
    const data = dashboardData();
    data.focus_assignments_complete = { w1: false, w2: true };

    render(<DashboardPage data={data} />);

    expect(screen.queryByRole('heading', { name: 'Mein SWP 1' })).not.toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Mein SWP 2' })).toBeInTheDocument();
  });

  it('loads and appends the selected older activity page without duplicates', async () => {
    const fetchImpl = vi.fn().mockResolvedValue(response({
      activity: {
        notes: {
          items: [
            { id: 1, author: 'Ada', date: '2026-07-01T10:00:00Z', kid_id: 7, kid: 'Grace Hopper', text: 'Alt' },
            { id: 2, author: 'Ada', date: '2026-07-02T10:00:00Z', kid_id: 7, kid: 'Grace Hopper', text: 'Duplikat' },
          ],
          next_cursor: null,
          has_more: false,
          limit: 20,
        },
      },
    }));
    render(<DashboardPage
      data={dashboardData({
        notes: {
          items: [{ id: 2, author: 'Ada', date: '2026-07-02T10:00:00Z', kid_id: 7, kid: 'Grace Hopper', text: 'Neu' }],
          next_cursor: 'stable cursor',
          has_more: true,
          limit: 20,
        },
      })}
      fetchImpl={fetchImpl}
    />);

    fireEvent.click(screen.getByRole('button', { name: 'Ältere Notizen laden' }));

    await waitFor(() => expect(fetchImpl).toHaveBeenCalledWith(
      '/api/route-data/dashboard/?activity=notes&cursor=stable+cursor',
      { credentials: 'same-origin' },
    ));
    expect(await screen.findByText('Alt')).toBeInTheDocument();
    expect(screen.getByText('Neu')).toBeInTheDocument();
    expect(screen.queryByText('Duplikat')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Ältere Notizen laden' })).not.toBeInTheDocument();
  });

  it('renders first-aid activity and appends older EH entries', async () => {
    const fetchImpl = vi.fn().mockResolvedValue(response({
      activity: {
        first_aid: {
          items: [{ id: 8, author: 'Boris', date: '2026-07-01T10:00:00Z', kid_id: 7, kid: 'Grace Hopper', text: 'Hand gekühlt' }],
          next_cursor: null,
          has_more: false,
          limit: 20,
        },
      },
    }));
    render(<DashboardPage
      data={dashboardData({
        first_aid: {
          items: [{ id: 9, author: 'Ada', date: '2026-07-02T10:00:00Z', kid_id: 7, kid: 'Grace Hopper', text: 'Knie verbunden' }],
          next_cursor: 'eh cursor',
          has_more: true,
          limit: 20,
        },
      })}
      fetchImpl={fetchImpl}
    />);

    const card = screen.getByRole('heading', { name: 'Erste Hilfe' }).closest('.card');
    expect(card).toHaveTextContent('Ada am 02.07.2026: Grace Hopper');
    expect(card).toHaveTextContent('Knie verbunden');
    fireEvent.click(screen.getByRole('button', { name: 'Ältere EH-Einträge laden' }));

    await waitFor(() => expect(fetchImpl).toHaveBeenCalledWith(
      '/api/route-data/dashboard/?activity=first_aid&cursor=eh+cursor',
      { credentials: 'same-origin' },
    ));
    expect(await screen.findByText('Hand gekühlt')).toBeInTheDocument();
  });

  it('shows a recoverable error when an activity continuation fails', async () => {
    const fetchImpl = vi.fn().mockResolvedValue(response({}, { ok: false, status: 503 }));
    render(<DashboardPage
      data={dashboardData({
        transactions: {
          items: [],
          next_cursor: 'money-cursor',
          has_more: true,
          limit: 20,
        },
      })}
      fetchImpl={fetchImpl}
    />);

    fireEvent.click(screen.getByRole('button', { name: 'Ältere Transaktionen laden' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('Ältere Transaktionen konnten nicht geladen werden.');
    expect(screen.getByRole('button', { name: 'Ältere Transaktionen laden' })).toBeEnabled();
  });

  it('uses the dashboard contract and renders its loading, success, and error states', async () => {
    expect(parseRoute('/dashboard')).toMatchObject({
      readContractKey: 'dashboard',
    });
    window.history.pushState({}, '', '/dashboard');
    let resolveRoute;
    const fetchImpl = vi.fn()
      .mockResolvedValueOnce(response({
        authenticated: true,
        csrf_token: 'token',
        messages: [],
        profile: { id: 1, rufname: 'Ada' },
        turnus: { id: 2, label: 'T2' },
        permissions: {},
        search_index: { kids: [], focuses: [], places: [] },
      }))
      .mockReturnValueOnce(new Promise(resolve => { resolveRoute = resolve; }));
    const { unmount } = render(<App fetchImpl={fetchImpl} />);

    expect(await screen.findByText('Seitendaten werden geladen…')).toBeInTheDocument();
    resolveRoute(response(dashboardData()));
    expect(await screen.findByRole('heading', { name: 'Kinder: 1' })).toBeInTheDocument();
    expect(fetchImpl.mock.calls[1][0]).toBe('/api/route-data/dashboard/');
    expect(fetchImpl.mock.calls.some(([url]) => url.startsWith('/api/app-data/'))).toBe(false);
    unmount();

    fetchImpl.mockReset()
      .mockResolvedValueOnce(response({
        authenticated: true,
        csrf_token: 'token',
        messages: [],
        profile: { id: 1, rufname: 'Ada' },
        turnus: { id: 2, label: 'T2' },
        permissions: {},
        search_index: { kids: [], focuses: [], places: [] },
      }))
      .mockResolvedValueOnce(response({}, { ok: false, status: 500 }));
    render(<App fetchImpl={fetchImpl} />);

    expect(await screen.findByRole('heading', { name: 'Seitendaten konnten nicht geladen werden' })).toBeInTheDocument();
  });
});
