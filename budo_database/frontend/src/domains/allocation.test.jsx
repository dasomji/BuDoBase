import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import App from '../App';
import { AllocationPage } from './allocation';

const response = data => ({
  ok: true,
  status: 200,
  json: vi.fn().mockResolvedValue(data),
});

describe('allocation page', () => {
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
    window.history.pushState({}, '', '/');
  });

  it('renders assignment stats above a two-column kid list and highlights selected choices', () => {
    render(<AllocationPage week="2" mutate={vi.fn()} data={{
      focuses: [{
        id: 2,
        name: 'Wald',
        week: 'w2',
        kid_ids: [1, 2, 3],
        stats: {
          average_age: 12.5,
          sex: { male: 1, female: 1, diverse: 1 },
          families: { S: 1, M: 1, L: 0, XL: 1 },
        },
      }],
      kids: [
        { id: 1, full_name: 'Ada', present: true, focus_ids: [2], choices: [{ week: 'w2', first: 2, friends: 'Bea' }], age: 12, budo_family: 'M', siblings: '' },
        { id: 2, full_name: 'Bea', present: true, focus_ids: [2], choices: [], age: 13, siblings: '' },
        { id: 3, full_name: 'Chris', present: true, focus_ids: [2], choices: [], age: null, siblings: '' },
      ],
    }} />);

    const card = screen.getByRole('heading', { name: 'Wald: 3' }).closest('.card');
    expect(card.parentElement).toHaveClass('allocation-card-row');
    expect(card.parentElement.parentElement).toHaveClass('table-sticky-controls');
    expect(within(card.parentElement.parentElement).getByRole('searchbox', { name: 'Kinder filtern' })).toBeInTheDocument();
    const stats = within(card).getByLabelText('Statistik Wald');
    expect(stats).toHaveTextContent('Ø Alter: 12,5');
    expect(stats).toHaveTextContent('Geschlechter: 1 ♂ · 1 ♀ · 1 ⚧');
    expect(stats).toHaveTextContent('BuDo-Familien: 1 S · 1 M · 0 L · 1 XL');
    expect(within(card).getByRole('heading', { name: 'Wald' })).toHaveClass('allocation-print-title');
    expect(within(card).getByRole('list')).toHaveClass('allocation-kids');
    expect(screen.getAllByRole('option', { name: 'Wald' })[0].selected).toBe(true);
    expect(screen.getAllByRole('button', { name: '1' })[0]).toHaveClass('swp-medal', 'swp-medal-1', 'active');
    expect(screen.getAllByRole('button', { name: '2' })[0]).toHaveClass('swp-medal-2');
    expect(screen.getAllByRole('button', { name: '3' })[0]).toHaveClass('swp-medal-3');
    expect(screen.getAllByRole('button', { name: '1' })[0]).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByRole('button', { name: 'Familie sortieren' })).toBeInTheDocument();
    expect(screen.getByRole('row', { name: /Ada/ })).toHaveTextContent('M');
    expect(screen.getByRole('row', { name: /Ada/ })).toHaveTextContent('Bea');
  });

  it('keeps the allocation UI mounted while refreshing after a choice click', async () => {
    window.history.pushState({}, '', '/swp-einteilung-w1');
    const bootstrap = {
      authenticated: true,
      csrf_token: 'token',
      messages: [],
      profile: { id: 7, rufname: 'Teamer' },
      turnus: { id: 2, label: 'T2' },
      permissions: {},
      search_index: { kids: [], focuses: [], places: [] },
    };
    const allocation = {
      kids: [{
        id: 1,
        full_name: 'Ada Kind',
        focus_ids: [],
        choices: [{ week: 'w1', first: null, second: null, third: null, friends: '' }],
        age: 14,
        siblings: '',
      }],
      focuses: [{
        id: 2,
        name: 'Wald',
        week: 'w1',
        kid_ids: [],
        stats: { average_age: null, sex: {}, families: {} },
      }],
    };
    let finishRefresh;
    const pendingRefresh = new Promise(resolve => { finishRefresh = resolve; });
    const fetchImpl = vi.fn()
      .mockResolvedValueOnce(response(bootstrap))
      .mockResolvedValueOnce(response(allocation))
      .mockResolvedValueOnce(response({ status: 'success' }))
      .mockReturnValueOnce(pendingRefresh);

    render(<App fetchImpl={fetchImpl} />);

    expect(await screen.findByRole('row', { name: /Ada Kind/ })).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '1' }));
    await waitFor(() => expect(fetchImpl).toHaveBeenCalledTimes(4));

    expect(screen.queryByText('Seitendaten werden geladen…')).not.toBeInTheDocument();
    expect(screen.getByRole('row', { name: /Ada Kind/ })).toBeInTheDocument();

    finishRefresh(response(allocation));
    await waitFor(() => expect(fetchImpl).toHaveBeenCalledTimes(4));
  });

  it('refreshes only allocation data and renders every affected value coherently', async () => {
    window.history.pushState({}, '', '/swp-einteilung-w2');
    const bootstrap = {
      authenticated: true,
      csrf_token: 'token',
      messages: [],
      profile: { id: 7, rufname: 'Teamer' },
      turnus: { id: 2, label: 'T2' },
      permissions: {},
      search_index: { kids: [], focuses: [], places: [] },
    };
    const kid = (focusId, first, friends) => ({
      id: 1,
      full_name: 'Ada Kind',
      focus_ids: [focusId],
      choices: [{ week: 'w2', first, second: null, third: null, friends }],
      age: 14,
      siblings: '',
    });
    const stats = {
      average_age: 14,
      sex: { male: 0, female: 1, diverse: 0 },
      families: { S: 0, M: 1, L: 0, XL: 0 },
    };
    const focuses = (forestKids, lakeKids) => [
      { id: 2, name: 'Wald', week: 'w2', kid_ids: forestKids, stats },
      { id: 3, name: 'See', week: 'w2', kid_ids: lakeKids, stats },
    ];
    const initial = { kids: [kid(2, 2, 'Bea')], focuses: focuses([1], []) };
    const assigned = { kids: [kid(3, 2, 'Bea')], focuses: focuses([], [1]) };
    const chosen = { kids: [kid(3, 3, 'Bea')], focuses: focuses([], [1]) };
    const befriended = { kids: [kid(3, 3, 'Cora')], focuses: focuses([], [1]) };
    const fetchImpl = vi.fn()
      .mockResolvedValueOnce(response(bootstrap))
      .mockResolvedValueOnce(response(initial))
      .mockResolvedValueOnce(response({ status: 'success' }))
      .mockResolvedValueOnce(response(assigned))
      .mockResolvedValueOnce(response({ status: 'success' }))
      .mockResolvedValueOnce(response(chosen))
      .mockResolvedValueOnce(response({ status: 'success' }))
      .mockResolvedValueOnce(response(befriended));

    render(<App fetchImpl={fetchImpl} />);

    expect(await screen.findByRole('heading', { name: 'Wald: 1' })).toBeInTheDocument();
    expect(fetchImpl.mock.calls[1][0]).toBe('/api/route-data/allocation/?week=2');

    const toggleKids = screen.getByRole('button', { name: 'Kinder ausblenden' });
    expect(toggleKids).toHaveAttribute('aria-pressed', 'true');
    expect(document.querySelectorAll('.allocation-kids')).toHaveLength(2);
    fireEvent.click(toggleKids);
    expect(toggleKids).toHaveAttribute('aria-pressed', 'false');
    expect(toggleKids).toHaveTextContent('Kinder anzeigen');
    expect(document.querySelectorAll('.allocation-kids.screen-hidden-kids')).toHaveLength(2);
    expect(document.querySelectorAll('.allocation-kids[aria-hidden="true"]')).toHaveLength(2);
    expect(document.querySelectorAll('.allocation-stats.without-kid-divider')).toHaveLength(2);

    const kidRow = screen.getByRole('row', { name: /Ada Kind/ });
    fireEvent.change(within(kidRow).getByRole('combobox'), { target: { value: '3' } });
    expect(await screen.findByRole('heading', { name: 'See: 1' })).toBeInTheDocument();
    expect(screen.getByRole('option', { name: 'See' }).selected).toBe(true);

    fireEvent.click(screen.getAllByRole('button', { name: '1' })[1]);
    await waitFor(() => expect(screen.getAllByRole('button', { name: '1' })[1]).toHaveClass('active'));

    vi.spyOn(window, 'prompt').mockReturnValue('Cora');
    fireEvent.click(screen.getByRole('button', { name: 'Freunde von Ada Kind bearbeiten' }));
    expect(await screen.findByText('Cora')).toBeInTheDocument();

    expect(fetchImpl.mock.calls.filter(([url]) => url === '/api/bootstrap/')).toHaveLength(1);
    expect(fetchImpl.mock.calls.filter(([url]) => url === '/api/route-data/allocation/?week=2')).toHaveLength(4);
    expect(fetchImpl.mock.calls[2][0]).toBe('/update-schwerpunkt-wahl/');
    expect(JSON.parse(fetchImpl.mock.calls[2][1].body)).toEqual({ kid_id: 1, swp_id: 3, choice_rank: null });
    expect(JSON.parse(fetchImpl.mock.calls[4][1].body)).toEqual({ kid_id: 1, swp_id: 3, choice_rank: '1' });
    expect(fetchImpl.mock.calls[6][0]).toBe('/update_freunde/');
    expect(JSON.parse(fetchImpl.mock.calls[6][1].body)).toEqual({ kid_id: 1, freunde: 'Cora', week: '2' });
  });
});
