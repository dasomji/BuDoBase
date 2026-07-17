import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import App from '../App';
import { parseRoute } from '../routes';
import { DashboardPage } from './dashboard';

const emptyPage = { items: [], next_cursor: null, has_more: false, limit: 20 };

const dashboardData = (activity = {}) => ({
  profile: {
    focus_ids: [11],
    role_display: 'Betreuer:in',
    food_display: 'Vegetarisch',
    allergies: '',
    coffee: '',
    email: 'ada@example.com',
    phone: '',
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
    food: '🥦 - glutenfrei',
    special_food: 'glutenfrei',
    drugs: 'Asthmaspray',
    illness: 'Allergie',
  }],
  focuses: [{ id: 11, name: 'Wald' }],
  activity: {
    notes: emptyPage,
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

describe('dashboard page', () => {
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
    window.history.pushState({}, '', '/');
  });

  it('retains every operational summary and list from the focused projection', () => {
    render(<DashboardPage data={dashboardData()} />);

    for (const heading of [
      'Mein Profil',
      'Team',
      'Finanzen',
      'Kinder: 1',
      'Speziallisten',
      'Notizen',
      'Taschengeld-Transaktionen',
      'Erstes Mal im BuDO: 1/1',
      'Einwöchige: 1',
      'Gesundheitliches',
      'Essen & Allergien',
      'Geburtstagskinder: 1',
      'Verabschiedungsliste: 0',
    ]) {
      expect(screen.getByRole('heading', { name: heading })).toBeInTheDocument();
    }
    expect(screen.getByText('Taschengeld aktuell').closest('p')).toHaveTextContent('18.00 €');
    expect(screen.getByRole('link', { name: 'Wald' })).toHaveAttribute('href', '/schwerpunkt/11/');
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

  it('opts into the focused contract and renders its loading, success, and error states', async () => {
    expect(parseRoute('/dashboard')).toMatchObject({
      readContractKey: 'dashboard',
      focusedReadContract: true,
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
    expect(await screen.findByRole('heading', { name: 'Mein Profil' })).toBeInTheDocument();
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
