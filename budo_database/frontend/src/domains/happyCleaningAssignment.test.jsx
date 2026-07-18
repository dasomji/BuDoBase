import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { routeDataRequest } from '../dataLoader';
import { parseRoute } from '../routes';
import { HappyCleaningAssignmentPage } from './happyCleaningAssignment';


const assignmentData = {
  event: { id: 7, display_number: 2, revision: 5 },
  summary: { assigned_present: 1, present_total: 2 },
  children: [
    {
      id: 1,
      first_name: 'Ada',
      last_name: 'Lovelace',
      full_name: 'Ada Lovelace',
      number: 7,
      number_version: 2,
      present: true,
      absence_location: null,
      assigned_station: { id: 10, name: 'Speisesaal' },
      assignment_version: 6,
    },
    {
      id: 2,
      first_name: 'Grace',
      last_name: 'Hopper',
      full_name: 'Grace Hopper',
      number: null,
      number_version: 1,
      present: true,
      absence_location: null,
      assigned_station: null,
      assignment_version: null,
    },
    {
      id: 3,
      first_name: 'Linus',
      last_name: 'Torvalds',
      full_name: 'Linus Torvalds',
      number: 3,
      number_version: 1,
      present: false,
      absence_location: 'Sallingstadt',
      assigned_station: { id: 11, name: 'Bad' },
      assignment_version: 4,
    },
  ],
  stations: [
    {
      id: 10,
      version: 3,
      name: 'Speisesaal',
      wishes: 'Fenster',
      meeting_point: 'Vor dem Saal',
      responsible: { id: 4, name: 'Mira' },
      max_kids: 2,
      assigned_count: 1,
      free_seats: 1,
      todo_progress_percentage: 50,
      children: [{ id: 1, full_name: 'Ada Lovelace', short_name: 'Ada Lo', present: true, assignment_version: 6 }],
    },
    {
      id: 11,
      version: 2,
      name: 'Bad',
      wishes: '',
      meeting_point: 'Im Gang',
      responsible: null,
      max_kids: 1,
      assigned_count: 1,
      free_seats: 0,
      todo_progress_percentage: null,
      children: [{ id: 3, full_name: 'Linus Torvalds', short_name: 'Linus To', present: false, assignment_version: 4 }],
    },
  ],
};

const setViewport = mobile => {
  window.matchMedia = vi.fn().mockReturnValue({
    matches: mobile,
    media: '(max-width: 759px)',
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
  });
};


describe('Happy Cleaning assignment', () => {
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it('loads an assignment snapshot by immutable Happy Cleaning ID', () => {
    const route = parseRoute('/happy-cleaning/7/assignment/');

    expect(route).toMatchObject({
      page: 'happy-cleaning-assignment',
      domain: 'happy-cleaning',
      event_id: '7',
      readContractKey: 'happy-cleaning-assignment',
    });
    expect(routeDataRequest(route).url).toBe(
      '/api/route-data/happy-cleaning-assignment/?event_id=7',
    );
  });

  it('searches all Turnus children with an accessible desktop keyboard interaction', () => {
    setViewport(false);
    render(<HappyCleaningAssignmentPage data={assignmentData} mutate={vi.fn()} />);

    const search = screen.getByRole('combobox', { name: 'Kind suchen' });
    fireEvent.change(search, { target: { value: 'Ada' } });

    expect(search).toHaveAttribute('aria-expanded', 'true');
    expect(search).toHaveAttribute('aria-controls', 'happy-cleaning-child-results');
    const option = screen.getByRole('option', { name: /Ada Lovelace/ });
    expect(option).toHaveTextContent('Nummer 7');
    expect(option).toHaveTextContent('Speisesaal');
    expect(option).toHaveTextContent('Anwesend');

    fireEvent.keyDown(search, { key: 'ArrowDown' });
    expect(search).toHaveAttribute('aria-activedescendant', 'happy-cleaning-child-1');
    fireEvent.keyDown(search, { key: 'Enter' });

    expect(screen.queryByRole('listbox')).not.toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Ada Lovelace' })).toBeInTheDocument();
    expect(screen.getByRole('combobox', { name: 'Kind suchen' })).toHaveValue('Ada Lovelace');
  });

  it('scrolls keyboard options into view and closes results with Escape without moving focus', () => {
    setViewport(false);
    const scrollIntoView = vi.fn();
    window.HTMLElement.prototype.scrollIntoView = scrollIntoView;
    render(<HappyCleaningAssignmentPage data={assignmentData} mutate={vi.fn()} />);

    const search = screen.getByRole('combobox', { name: 'Kind suchen' });
    search.focus();
    fireEvent.change(search, { target: { value: 'a' } });
    fireEvent.keyDown(search, { key: 'ArrowDown' });
    fireEvent.keyDown(search, { key: 'ArrowDown' });
    fireEvent.keyDown(search, { key: 'ArrowUp' });

    expect(search).toHaveAttribute('aria-activedescendant', 'happy-cleaning-child-1');
    expect(scrollIntoView).toHaveBeenCalled();
    fireEvent.keyDown(search, { key: 'Escape' });
    expect(search).toHaveAttribute('aria-expanded', 'false');
    expect(search).toHaveFocus();
  });

  it('keeps mobile suggestions name-only and reveals details after a pointer selection', () => {
    setViewport(true);
    render(<HappyCleaningAssignmentPage data={assignmentData} mutate={vi.fn()} />);

    const search = screen.getByRole('combobox', { name: 'Kind suchen' });
    fireEvent.change(search, { target: { value: 'Linus' } });
    const option = screen.getByRole('option', { name: 'Linus Torvalds' });
    expect(option).toHaveTextContent(/^Linus Torvalds$/);
    expect(option).not.toHaveTextContent('Sallingstadt');

    fireEvent.click(option);

    expect(screen.getByRole('heading', { name: 'Linus Torvalds' })).toBeInTheDocument();
    expect(screen.getByText('Abwesend · Sallingstadt')).toBeInTheDocument();
    expect(screen.getByText('Nummer').nextElementSibling).toHaveTextContent('3');
  });

  it('counts only present children and selects from the present unassigned list', () => {
    setViewport(false);
    render(<HappyCleaningAssignmentPage data={assignmentData} mutate={vi.fn()} />);

    fireEvent.click(screen.getByRole('button', { name: '1 von 2 anwesenden Kindern eingeteilt' }));

    const list = screen.getByRole('list', { name: 'Anwesende nicht eingeteilte Kinder' });
    expect(list).toHaveTextContent('Grace Hopper');
    expect(list).not.toHaveTextContent('Ada Lovelace');
    expect(list).not.toHaveTextContent('Linus Torvalds');

    fireEvent.click(screen.getByRole('button', { name: 'Grace Hopper auswählen' }));
    expect(screen.getByRole('heading', { name: 'Grace Hopper' })).toBeInTheDocument();
    expect(screen.getByRole('combobox', { name: 'Kind suchen' })).toHaveValue('Grace Hopper');
  });

  it('renders the complete desktop station table and compact mobile cards', () => {
    setViewport(false);
    const desktop = render(<HappyCleaningAssignmentPage data={assignmentData} mutate={vi.fn()} />);

    const table = screen.getByRole('table', { name: 'Happy Cleaning Stationen' });
    expect(within(table).getByRole('columnheader', { name: 'Wünsche' })).toBeInTheDocument();
    expect(within(table).getByRole('link', { name: 'Speisesaal' })).toHaveAttribute(
      'href', '/happy-cleaning/7/stations/10/',
    );
    expect(within(table).getByText('Fenster')).toBeInTheDocument();
    expect(within(table).getByText('Vor dem Saal')).toBeInTheDocument();
    expect(within(table).getByText('Mira')).toBeInTheDocument();
    expect(within(table).getByText('1 / 2 frei')).toBeInTheDocument();
    expect(within(table).getByText('50%')).toBeInTheDocument();
    expect(within(table).getAllByText('—').length).toBeGreaterThan(0);
    expect(within(table).getByRole('button', { name: 'Ada Lovelace aus Speisesaal entfernen' })).toHaveTextContent('Ada Lo');

    desktop.unmount();
    setViewport(true);
    render(<HappyCleaningAssignmentPage data={assignmentData} mutate={vi.fn()} />);

    expect(screen.queryByRole('table')).not.toBeInTheDocument();
    const card = screen.getByRole('article', { name: 'Station Speisesaal' });
    expect(card).toHaveTextContent('Wünsche');
    expect(card).toHaveTextContent('Fenster');
    expect(card).toHaveTextContent('Treffpunkt');
    expect(card).toHaveTextContent('Vor dem Saal');
    expect(card).toHaveTextContent('Mira');
  });

  it('gates station assignment on a versioned number entry', async () => {
    setViewport(false);
    const mutate = vi.fn().mockResolvedValue({ ok: true });
    render(<HappyCleaningAssignmentPage data={assignmentData} mutate={mutate} />);

    const search = screen.getByRole('combobox', { name: 'Kind suchen' });
    fireEvent.change(search, { target: { value: 'Grace' } });
    fireEvent.click(screen.getByRole('option', { name: /Grace Hopper/ }));

    expect(screen.getByText('Vor der Einteilung braucht Grace Hopper eine Nummer.')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Grace Hopper Speisesaal zuweisen' })).toBeDisabled();
    fireEvent.change(screen.getByRole('spinbutton', { name: 'Happy Cleaning Nummer für Grace Hopper' }), { target: { value: '8' } });
    fireEvent.click(screen.getByRole('button', { name: 'Nummer speichern' }));

    await waitFor(() => expect(mutate).toHaveBeenCalledWith(
      '/api/happy-cleaning/children/2/number/',
      expect.objectContaining({ number: 8, expected_version: 1 }),
    ));
  });

  it('keeps existing numbers editable and renders the authoritative duplicate neighborhood', async () => {
    setViewport(false);
    const duplicate = new Error('duplicate');
    duplicate.payload = {
      code: 'duplicate_number',
      neighborhood: [
        { number: 5, free: true, child: null },
        { number: 6, free: true, child: null },
        { number: 7, free: false, child: { id: 1, display_name: 'Ada Lovelace' } },
        { number: 8, free: false, child: { id: 9, display_name: 'Alan Turing' } },
        { number: 9, free: true, child: null },
        { number: 10, free: true, child: null },
        { number: 11, free: true, child: null },
      ],
    };
    const mutate = vi.fn().mockRejectedValue(duplicate);
    render(<HappyCleaningAssignmentPage data={assignmentData} mutate={mutate} />);

    const search = screen.getByRole('combobox', { name: 'Kind suchen' });
    fireEvent.change(search, { target: { value: 'Ada' } });
    fireEvent.keyDown(search, { key: 'ArrowDown' });
    fireEvent.keyDown(search, { key: 'Enter' });
    const number = screen.getByRole('spinbutton', { name: 'Happy Cleaning Nummer für Ada Lovelace' });
    expect(number).toHaveValue(7);
    fireEvent.change(number, { target: { value: '8' } });
    fireEvent.click(screen.getByRole('button', { name: 'Nummer speichern' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('Nummer 8 ist bereits vergeben.');
    const neighborhood = screen.getByRole('list', { name: 'Nummern rund um 8' });
    expect(neighborhood).toHaveTextContent('5 frei');
    expect(neighborhood).toHaveTextContent('8 Alan Turing');
    expect(neighborhood).toHaveTextContent('11 frei');
    expect(screen.getByRole('heading', { name: 'Ada Lovelace' })).toBeInTheDocument();
  });

  it('assigns a numbered child and restores the cleared search with a toast', async () => {
    setViewport(false);
    const data = {
      ...assignmentData,
      children: assignmentData.children.map(child => child.id === 2
        ? { ...child, number: 8 }
        : child),
    };
    const mutate = vi.fn().mockResolvedValue({ ok: true });
    render(<HappyCleaningAssignmentPage data={data} mutate={mutate} />);

    const search = screen.getByRole('combobox', { name: 'Kind suchen' });
    fireEvent.change(search, { target: { value: 'Grace' } });
    fireEvent.click(screen.getByRole('option', { name: /Grace Hopper/ }));
    fireEvent.click(screen.getByRole('button', { name: 'Grace Hopper Speisesaal zuweisen' }));

    await waitFor(() => expect(mutate).toHaveBeenCalledWith(
      '/api/happy-cleaning/events/7/assignments/assign/',
      expect.objectContaining({ child_id: 2, station_id: 10 }),
    ));
    expect(await screen.findByRole('status')).toHaveTextContent('Grace Hopper wurde Speisesaal zugeteilt.');
    expect(screen.queryByRole('heading', { name: 'Grace Hopper' })).not.toBeInTheDocument();
    expect(screen.getByRole('combobox', { name: 'Kind suchen' })).toHaveValue('');
    expect(screen.getByRole('combobox', { name: 'Kind suchen' })).toHaveFocus();
  });

  it('disables full stations and confirms an atomic move to an available station', async () => {
    setViewport(false);
    const numberedGrace = {
      ...assignmentData,
      children: assignmentData.children.map(child => child.id === 2 ? { ...child, number: 8 } : child),
    };
    const full = render(<HappyCleaningAssignmentPage data={numberedGrace} mutate={vi.fn()} />);
    fireEvent.change(screen.getByRole('combobox', { name: 'Kind suchen' }), { target: { value: 'Grace' } });
    fireEvent.click(screen.getByRole('option', { name: /Grace Hopper/ }));
    expect(screen.getByRole('button', { name: 'Grace Hopper Bad zuweisen' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Grace Hopper Bad zuweisen' })).toHaveTextContent('🚫');
    full.unmount();

    const available = {
      ...assignmentData,
      stations: assignmentData.stations.map(station => station.id === 11
        ? { ...station, assigned_count: 0, free_seats: 1, children: [] }
        : station),
    };
    const mutate = vi.fn().mockResolvedValue({ ok: true });
    const confirm = vi.spyOn(window, 'confirm').mockReturnValue(true);
    render(<HappyCleaningAssignmentPage data={available} mutate={mutate} />);
    fireEvent.change(screen.getByRole('combobox', { name: 'Kind suchen' }), { target: { value: 'Ada' } });
    fireEvent.click(screen.getByRole('option', { name: /Ada Lovelace/ }));
    fireEvent.click(screen.getByRole('button', { name: 'Ada Lovelace Bad zuweisen' }));

    expect(confirm).toHaveBeenCalledWith('Ada Lovelace von Speisesaal nach Bad verschieben?');
    await waitFor(() => expect(mutate).toHaveBeenCalledWith(
      '/api/happy-cleaning/events/7/assignments/1/move/',
      expect.objectContaining({ station_id: 11, expected_version: 6 }),
    ));
    expect(screen.getByRole('status')).toHaveTextContent('Ada Lovelace wurde nach Bad verschoben.');
  });

  it('confirms pill removal with the assignment version', async () => {
    setViewport(false);
    const mutate = vi.fn().mockResolvedValue({ ok: true });
    const confirm = vi.spyOn(window, 'confirm').mockReturnValue(true);
    render(<HappyCleaningAssignmentPage data={assignmentData} mutate={mutate} />);

    fireEvent.click(screen.getByRole('button', { name: 'Ada Lovelace aus Speisesaal entfernen' }));

    expect(confirm).toHaveBeenCalledWith('Ada Lovelace aus Speisesaal entfernen?');
    await waitFor(() => expect(mutate).toHaveBeenCalledWith(
      '/api/happy-cleaning/events/7/assignments/1/remove/',
      expect.objectContaining({ expected_version: 6 }),
    ));
    expect(screen.getByRole('status')).toHaveTextContent('Ada Lovelace wurde aus Speisesaal entfernt.');
    await waitFor(() => expect(screen.getByRole('combobox', { name: 'Kind suchen' })).toHaveFocus());
  });

  it('retains selection and reconciles the focused snapshot after a station conflict', async () => {
    setViewport(false);
    const data = {
      ...assignmentData,
      children: assignmentData.children.map(child => child.id === 2 ? { ...child, number: 8 } : child),
    };
    const conflict = new Error('full');
    conflict.payload = { code: 'station_full', station: { id: 10, free_seats: 0 } };
    const mutate = vi.fn().mockRejectedValue(conflict);
    const refresh = vi.fn().mockResolvedValue(undefined);
    render(<HappyCleaningAssignmentPage data={data} mutate={mutate} refresh={refresh} />);
    fireEvent.change(screen.getByRole('combobox', { name: 'Kind suchen' }), { target: { value: 'Grace' } });
    fireEvent.click(screen.getByRole('option', { name: /Grace Hopper/ }));

    fireEvent.click(screen.getByRole('button', { name: 'Grace Hopper Speisesaal zuweisen' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('Speisesaal ist inzwischen voll.');
    expect(screen.getByRole('heading', { name: 'Grace Hopper' })).toBeInTheDocument();
    expect(refresh).toHaveBeenCalledOnce();
    expect(screen.queryByText(/wurde Speisesaal zugeteilt/)).not.toBeInTheDocument();
  });

  it('visibly gates every assignment write while realtime data is not fresh', () => {
    setViewport(false);
    render(<HappyCleaningAssignmentPage
      data={assignmentData}
      mutate={vi.fn()}
      realtimeSync={{ enabled: true, writesEnabled: false }}
    />);
    fireEvent.change(screen.getByRole('combobox', { name: 'Kind suchen' }), { target: { value: 'Ada' } });
    fireEvent.click(screen.getByRole('option', { name: /Ada Lovelace/ }));

    expect(screen.getByRole('spinbutton', { name: 'Happy Cleaning Nummer für Ada Lovelace' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Nummer speichern' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Ada Lovelace aus Speisesaal entfernen' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Ada Lovelace Bad zuweisen' })).toBeDisabled();
  });

  it('keeps selection while a focused realtime refetch replaces child and progress revisions', () => {
    setViewport(false);
    const { rerender } = render(<HappyCleaningAssignmentPage data={assignmentData} mutate={vi.fn()} />);
    fireEvent.change(screen.getByRole('combobox', { name: 'Kind suchen' }), { target: { value: 'Ada' } });
    fireEvent.click(screen.getByRole('option', { name: /Ada Lovelace/ }));

    const refreshed = {
      ...assignmentData,
      event: { ...assignmentData.event, revision: 8 },
      children: assignmentData.children.map(child => child.id === 1
        ? { ...child, number: 9, number_version: 3, assigned_station: { id: 11, name: 'Bad' }, assignment_version: 8 }
        : child),
      stations: assignmentData.stations.map(station => station.id === 10
        ? { ...station, todo_progress_percentage: 100 }
        : station),
    };
    rerender(<HappyCleaningAssignmentPage data={refreshed} mutate={vi.fn()} />);

    expect(screen.getByRole('spinbutton', { name: 'Happy Cleaning Nummer für Ada Lovelace' })).toHaveValue(9);
    expect(within(screen.getByLabelText('Ausgewähltes Kind')).getByText('Station').nextElementSibling).toHaveTextContent('Bad');
    expect(screen.getByRole('table', { name: 'Happy Cleaning Stationen' })).toHaveTextContent('100%');
  });
});
