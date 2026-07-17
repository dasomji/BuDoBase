import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { CheckPage, TrainPage, attendanceRoutes } from './attendance';
import App from '../App';

const response = (data, { ok = true, status = 200 } = {}) => ({
  ok,
  status,
  json: vi.fn().mockResolvedValue(data),
});

describe('attendance pages', () => {
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
    window.history.pushState({}, '', '/');
  });

  it.each([
    { balance: 12.5, label: 'Taschengeld zurückgegeben (aktuell 12.50 €)', preset: 12.5 },
    { balance: -3, label: 'Taschengeld eingezahlt (schuldet aktuell: 3.00 €)', preset: 0 },
  ])('uses a positive checkout amount when the current balance is $balance', ({ balance, label, preset }) => {
    render(<CheckPage data={{ csrf_token: 'token', kid: { id: 7, full_name: 'Ada', pocket_money: balance } }} checkout />);

    const amount = screen.getByRole('spinbutton', { name: label });
    expect(amount).toHaveValue(preset);
    expect(amount).toHaveAttribute('min', '0');
  });

  it('renders check-in from one selected-Kind contract without a Kinder collection', () => {
    render(<CheckPage data={{
      csrf_token: 'token',
      kid: {
        id: 7,
        full_name: 'Ada Lovelace',
        present: false,
        id_card: true,
        e_card: false,
        consent: true,
      },
    }} />);

    expect(screen.getByRole('heading', { name: 'Check-In: Ada Lovelace' })).toBeInTheDocument();
    expect(screen.getByRole('checkbox', { name: 'Ausweis' })).toBeChecked();
    expect(screen.getByRole('checkbox', { name: 'E-Card' })).not.toBeChecked();
    expect(screen.getByRole('checkbox', { name: 'Einverständniserklärung' })).toBeChecked();
  });

  it('opts only the four attendance routes into focused route reads', () => {
    expect(attendanceRoutes.map(route => [route.readContractKey, route.focusedReadContract])).toEqual([
      ['train-departure', true],
      ['train-arrival', true],
      ['check-in', true],
      ['check-out', true],
    ]);
  });

  it('renders the Zuganreise projection, ticket totals, and Kind links', () => {
    render(<TrainPage data={{
      kids: [{
        id: 7,
        full_name: 'Ada Lovelace',
        present: true,
        train_arrival: true,
        youth_ticket: true,
        age: 14,
        registrant_name: 'Grace Hopper',
        registrant_phone: '+4312345',
        siblings: 'Charles',
      }],
      totals: {
        train_arrival: 1,
        with_youth_ticket: 1,
        without_youth_ticket: 0,
      },
    }} mutate={vi.fn()} />);

    expect(screen.getByRole('link', { name: 'Ada Lovelace' })).toHaveAttribute('href', '/kid_details/7');
    expect(screen.getAllByText('Grace Hopper')).toHaveLength(1);
    expect(screen.getByText(/Kinder mit Top-Jugendticket: 1/)).toBeInTheDocument();
    expect(screen.getByText(/Kinder ohne Top-Jugendticket: 0/)).toBeInTheDocument();
  });

  it('keeps Zugabreise toggle and note controls on their existing write interfaces', () => {
    const mutate = vi.fn();
    vi.spyOn(window, 'prompt').mockReturnValue('Neuer Treffpunkt');
    render(<TrainPage departure mutate={mutate} data={{
      kids: [{
        id: 7,
        full_name: 'Ada Lovelace',
        present: true,
        train_departure: false,
        departure_note: 'Westbahnhof',
        youth_ticket: false,
        age: 14,
        registrant_name: 'Grace Hopper',
        registrant_phone: '+4312345',
        siblings: '',
      }],
      totals: { train_departure: 0 },
    }} />);

    fireEvent.click(screen.getByRole('button', { name: 'Nein' }));
    expect(mutate).toHaveBeenCalledWith('/toggle_zug_abreise/', { id: 7 }, false);

    fireEvent.click(screen.getByRole('button', { name: '✏️' }));
    expect(mutate).toHaveBeenCalledWith('/update_notiz_abreise/', {
      id: 7,
      notiz_abreise: 'Neuer Treffpunkt',
    });
  });

  it('refreshes only the current focused transport contract after a toggle', async () => {
    window.history.pushState({}, '', '/zugabreise');
    const kid = {
      id: 7,
      full_name: 'Ada Lovelace',
      present: true,
      departure_note: '',
      youth_ticket: false,
      age: 14,
      registrant_name: 'Grace Hopper',
      registrant_phone: '+4312345',
      siblings: '',
    };
    const fetchImpl = vi.fn()
      .mockResolvedValueOnce(response({
        authenticated: true,
        csrf_token: 'csrf-token',
        messages: [],
        profile: { id: 1, rufname: 'Teamer' },
        turnus: { id: 2, label: 'T2' },
        permissions: {},
        search_index: { kids: [], focuses: [], places: [] },
      }))
      .mockResolvedValueOnce(response({
        kids: [{ ...kid, train_departure: false }],
        totals: { train_departure: 0 },
      }))
      .mockResolvedValueOnce(response({ status: 'success', new_count: 1 }))
      .mockResolvedValueOnce(response({
        kids: [{ ...kid, train_departure: true }],
        totals: { train_departure: 1 },
      }));

    render(<App fetchImpl={fetchImpl} />);
    fireEvent.click(await screen.findByRole('button', { name: 'Nein' }));

    expect(await screen.findByRole('button', { name: 'Ja' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Zugabreise: 1 sortieren' })).toBeInTheDocument();
    await waitFor(() => expect(fetchImpl).toHaveBeenCalledTimes(4));
    expect(fetchImpl.mock.calls.map(call => call[0])).toEqual([
      '/api/bootstrap/',
      '/api/route-data/train-departure/',
      '/toggle_zug_abreise/',
      '/api/route-data/train-departure/',
    ]);
  });
});
