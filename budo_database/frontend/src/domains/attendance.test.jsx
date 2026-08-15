import { cleanup, fireEvent, render as testingLibraryRender, screen, waitFor, within } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { CheckPage, TrainPage, attendanceRoutes } from './attendance';
import App from '../App';
import { Toaster } from '../components/ui/toast';
import { expectErrorToastOnly } from '../test-support';

const render = ui => testingLibraryRender(ui, {
  wrapper: ({ children }) => <Toaster timeout={0}>{children}</Toaster>,
});

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

  it('declares the four attendance route contracts', () => {
    expect(attendanceRoutes.find(route => route.page === 'train-departure')).toMatchObject({ title: 'Zugabreise' });
    expect(attendanceRoutes.map(route => route.readContractKey)).toEqual([
      'train-departure',
      'train-arrival',
      'check-in',
      'check-out',
    ]);
  });

  it.each([
    ['Zuganreise', 'train-arrival'],
    ['Zugabreise', 'train-departure'],
  ])('offers %s printing from the shared page header', (_title, page) => {
    const print = vi.spyOn(window, 'print').mockImplementation(() => {});
    const route = attendanceRoutes.find(candidate => candidate.page === page);

    render(route.headerAction?.());

    const printButton = screen.getByRole('button', { name: 'Drucken' });
    expect(printButton).toHaveTextContent('Drucken');
    expect(printButton.querySelector('svg')).toHaveAttribute('aria-hidden', 'true');
    fireEvent.click(printButton);
    expect(print).toHaveBeenCalledOnce();
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
    expect(screen.getByRole('table').parentElement).toHaveAttribute('data-sticky-first-column');
    expect(within(screen.getByRole('main')).getByText('Grace Hopper')).toBeInTheDocument();
    expect(screen.getByText(/Kinder mit Top-Jugendticket: 1/)).toBeInTheDocument();
    expect(screen.getByText(/Kinder ohne Top-Jugendticket: 0/)).toBeInTheDocument();
  });

  it('shows every Kind in the editable Zuganreise list but prints only current train arrivals', async () => {
    const mutate = vi.fn().mockResolvedValue({ status: 'success', new_count: 0 });
    render(<TrainPage data={{
      kids: [
        {
          id: 7,
          full_name: 'Ada Lovelace',
          present: true,
          train_arrival: true,
          youth_ticket: true,
          age: 14,
          registrant_name: 'Grace Hopper',
          registrant_phone: '+4312345',
          siblings: '',
        },
        {
          id: 8,
          full_name: 'Katherine Johnson',
          present: true,
          train_arrival: false,
          youth_ticket: false,
          age: 13,
          registrant_name: 'Joylette Goble',
          registrant_phone: '+4354321',
          siblings: '',
        },
      ],
      totals: {
        train_arrival: 1,
        with_youth_ticket: 1,
        without_youth_ticket: 0,
      },
    }} mutate={mutate} />);

    const screenTable = within(screen.getByRole('main')).getByRole('table');
    expect([...screenTable.querySelectorAll('a[href^="/kid_details/"]')].map(link => link.textContent)).toEqual([
      'Ada Lovelace',
      'Katherine Johnson',
    ]);
    const adaControl = within(screenTable).getByRole('group', { name: 'Zuganreise für Ada Lovelace' });
    expect(within(adaControl).getByRole('button', { name: 'Ja' })).toHaveAttribute('aria-pressed', 'true');
    fireEvent.click(within(adaControl).getByRole('button', { name: 'Nein' }));
    expect(mutate).toHaveBeenCalledWith('/toggle_zug_anreise/', { id: 7 }, false);
    expect(await screen.findByText('Zuganreise wurde gespeichert.', { selector: '.app-toast-description' })).toBeInTheDocument();

    const printRegion = document.querySelector('section[aria-label="Zuganreise-Druckliste"]');
    const printTable = within(printRegion).getByRole('table', { hidden: true });
    expect([...printTable.querySelectorAll('a[href^="/kid_details/"]')].map(link => link.textContent)).toEqual([
      'Ada Lovelace',
    ]);
    expect(within(printTable).queryByRole('button', { hidden: true })).not.toBeInTheDocument();
  });

  it('separates the Zugabreise presence indicator from the printable kid name', () => {
    render(<TrainPage departure mutate={vi.fn()} data={{
      kids: [{
        id: 7,
        full_name: 'Ada Lovelace',
        present: false,
        train_departure: false,
        departure_note: '',
        youth_ticket: false,
        age: 14,
        registrant_name: 'Grace Hopper',
        registrant_phone: '+4312345',
        siblings: '',
      }],
      totals: { train_departure: 0 },
    }} />);

    const kidLink = screen.getByRole('link', { name: 'Ada Lovelace ❌' });
    expect(kidLink).toHaveTextContent('Ada Lovelace ❌');
    expect(kidLink.querySelector('.kid-presence-indicator')).toHaveTextContent('❌');
  });

  it('keeps Zugabreise controls on their write interfaces and confirms successful saves', async () => {
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

    const departureControl = screen.getByRole('group', {
      name: 'Zugabreise für Ada Lovelace',
    });
    const yes = within(departureControl).getByRole('button', { name: 'Ja' });
    const no = within(departureControl).getByRole('button', { name: 'Nein' });
    expect(yes).toHaveAttribute('aria-pressed', 'false');
    expect(no).toHaveAttribute('aria-pressed', 'true');

    fireEvent.click(no);
    expect(mutate).not.toHaveBeenCalled();

    fireEvent.click(yes);
    expect(mutate).toHaveBeenCalledWith('/toggle_zug_abreise/', { id: 7 }, false);
    const success = await screen.findByText('Zugabreise wurde gespeichert.', { selector: '.app-toast-description' });
    expect(success.closest('.app-toast')).toHaveAttribute('data-type', 'success');

    fireEvent.click(screen.getByRole('button', { name: 'Abreise-Notiz von Ada Lovelace bearbeiten' }));
    expect(mutate).toHaveBeenCalledWith('/update_notiz_abreise/', {
      id: 7,
      notiz_abreise: 'Neuer Treffpunkt',
    });
  });

  it('keeps the visible Zugabreise row order after a toggle until the page is reloaded', async () => {
    const mutate = vi.fn().mockResolvedValue({ status: 'success', new_count: 2 });
    const kid = (id, fullName, trainDeparture) => ({
      id,
      full_name: fullName,
      present: true,
      train_departure: trainDeparture,
      departure_note: '',
      youth_ticket: false,
      age: 14,
      registrant_name: 'Grace Hopper',
      registrant_phone: '+4312345',
      siblings: '',
    });
    const initialKids = [
      kid(1, 'Ada Alpha', true),
      kid(2, 'Berta Beta', false),
      kid(3, 'Clara Charlie', false),
    ];
    const rowNames = () => screen.getAllByRole('row')
      .map(row => row.querySelector('a[href^="/kid_details/"]')?.textContent)
      .filter(Boolean);
    const view = render(<TrainPage departure mutate={mutate} data={{
      kids: initialKids,
      totals: { train_departure: 1 },
    }} />);

    expect(rowNames()).toEqual(['Ada Alpha', 'Berta Beta', 'Clara Charlie']);
    fireEvent.click(within(screen.getByRole('link', { name: 'Clara Charlie' }).closest('tr')).getByRole('button', { name: 'Ja' }));
    await waitFor(() => expect(mutate).toHaveBeenCalledWith('/toggle_zug_abreise/', { id: 3 }, false));

    const updatedKids = initialKids.map(item => item.id === 3 ? { ...item, train_departure: true } : item);
    view.rerender(<TrainPage departure mutate={mutate} data={{
      kids: updatedKids,
      totals: { train_departure: 2 },
    }} />);
    expect(rowNames()).toEqual(['Ada Alpha', 'Berta Beta', 'Clara Charlie']);

    view.unmount();
    render(<TrainPage departure mutate={mutate} data={{
      kids: updatedKids,
      totals: { train_departure: 2 },
    }} />);
    expect(rowNames()).toEqual(['Ada Alpha', 'Clara Charlie', 'Berta Beta']);
  });

  it('shows failed transport writes as error toasts, never inline', async () => {
    const mutate = vi.fn().mockRejectedValue(new Error('network down'));
    render(<TrainPage departure mutate={mutate} data={{
      kids: [{
        id: 7,
        full_name: 'Ada Lovelace',
        present: true,
        train_departure: false,
        departure_note: '',
        youth_ticket: false,
        age: 14,
        registrant_name: 'Grace Hopper',
        registrant_phone: '+4312345',
        siblings: '',
      }],
      totals: { train_departure: 0 },
    }} />);

    fireEvent.click(screen.getByRole('button', { name: 'Ja' }));

    await expectErrorToastOnly('Die Zugabreise konnte nicht gespeichert werden.');
  });

  it('refreshes only the current transport contract without moving the toggled row', async () => {
    window.history.pushState({}, '', '/zugabreise');
    const kid = (id, fullName, trainDeparture) => ({
      id,
      full_name: fullName,
      present: true,
      train_departure: trainDeparture,
      departure_note: '',
      youth_ticket: false,
      age: 14,
      registrant_name: 'Grace Hopper',
      registrant_phone: '+4312345',
      siblings: '',
    });
    const ada = kid(1, 'Ada Alpha', true);
    const berta = kid(2, 'Berta Beta', false);
    const clara = kid(3, 'Clara Charlie', false);
    const rowNames = () => screen.getAllByRole('row')
      .map(row => row.querySelector('a[href^="/kid_details/"]')?.textContent)
      .filter(Boolean);
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
        kids: [ada, berta, clara],
        totals: { train_departure: 1 },
      }))
      .mockResolvedValueOnce(response({ status: 'success', new_count: 2 }))
      .mockResolvedValueOnce(response({
        kids: [ada, { ...clara, train_departure: true }, berta],
        totals: { train_departure: 2 },
      }));

    render(<App fetchImpl={fetchImpl} />);
    const claraRow = (await screen.findByRole('link', { name: 'Clara Charlie' })).closest('tr');
    expect(rowNames()).toEqual(['Ada Alpha', 'Berta Beta', 'Clara Charlie']);
    fireEvent.click(within(claraRow).getByRole('button', { name: 'Ja' }));

    await waitFor(() => expect(within(claraRow).getByRole('button', {
      name: 'Ja',
      pressed: true,
    })).toBeInTheDocument());
    expect(rowNames()).toEqual(['Ada Alpha', 'Berta Beta', 'Clara Charlie']);
    expect(screen.getByRole('button', { name: 'Zugabreise: 2 sortieren' })).toBeInTheDocument();
    await waitFor(() => expect(fetchImpl).toHaveBeenCalledTimes(4));
    expect(fetchImpl.mock.calls.map(call => call[0])).toEqual([
      '/api/bootstrap/',
      '/api/route-data/train-departure/',
      '/toggle_zug_abreise/',
      '/api/route-data/train-departure/',
    ]);
  });
});
