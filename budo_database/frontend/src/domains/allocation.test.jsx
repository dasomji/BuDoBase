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

  it('renders the selected week with its current assignments and choices', () => {
    render(<AllocationPage week="2" mutate={vi.fn()} data={{
      focuses: [{ id: 2, name: 'Wald', week: 'w2', kid_ids: [1] }],
      kids: [{ id: 1, full_name: 'Ada', present: true, focus_ids: [2], choices: [{ week: 'w2', first: 2, friends: 'Bea' }], age: 12, siblings: '' }],
    }} />);

    expect(screen.getByRole('heading', { name: 'Wald: 1' })).toBeInTheDocument();
    expect(screen.getByRole('option', { name: 'Wald' }).selected).toBe(true);
    expect(screen.getByRole('button', { name: '1' })).toHaveClass('active');
    expect(screen.getByText('Bea')).toBeInTheDocument();
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
    const focuses = (forestKids, lakeKids) => [
      { id: 2, name: 'Wald', week: 'w2', kid_ids: forestKids },
      { id: 3, name: 'See', week: 'w2', kid_ids: lakeKids },
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

    const kidRow = screen.getByRole('row', { name: /Ada Kind/ });
    fireEvent.change(within(kidRow).getByRole('combobox'), { target: { value: '3' } });
    expect(await screen.findByRole('heading', { name: 'See: 1' })).toBeInTheDocument();
    expect(screen.getByRole('option', { name: 'See' }).selected).toBe(true);

    fireEvent.click(screen.getAllByRole('button', { name: '1' })[1]);
    await waitFor(() => expect(screen.getAllByRole('button', { name: '1' })[1]).toHaveClass('active'));

    vi.spyOn(window, 'prompt').mockReturnValue('Cora');
    fireEvent.click(screen.getByRole('button', { name: '✏️' }));
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
