import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { routeDataRequest } from '../dataLoader';
import { parseRoute } from '../routes';
import {
  HappyCleaningManagementPage,
  HappyCleaningOverviewPage,
  HappyCleaningPrintPage,
} from './happyCleaning';


const stationsData = {
  event: { id: 7, display_number: 2, revision: 5 },
  responsible_profiles: [{ id: 4, name: 'Mira' }],
  copy_sources: [{
    id: 3,
    label: 'T1-2026 · Happy Cleaning 1',
    stations: [{ id: 30, name: 'Speisesaal' }, { id: 31, name: 'Bad' }],
  }],
  stations: [
    {
      id: 10,
      version: 3,
      name: 'Speisesaal',
      max_kids: 4,
      meeting_point: 'Vor dem Saal',
      wishes: 'Fenster',
      responsible_profile_id: 4,
      position: 1,
      has_ever_had_assignment: true,
      todo_progress_percentage: 50,
      todos: [
        { id: 100, version: 2, text: 'Tische', position: 1, checked: true },
        { id: 101, version: 1, text: 'Boden', position: 2, checked: false },
      ],
    },
    {
      id: 11,
      version: 1,
      name: 'Bad',
      max_kids: 2,
      meeting_point: 'Gang',
      wishes: '',
      responsible_profile_id: null,
      position: 2,
      has_ever_had_assignment: false,
      todo_progress_percentage: null,
      todos: [],
    },
  ],
};


describe('Happy Cleaning management', () => {
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it('owns refreshable overview and management routes with immutable event IDs', () => {
    const overview = parseRoute('/happy-cleaning/');
    const print = parseRoute('/happy-cleaning/7/print/');
    const management = parseRoute('/happy-cleaning/7/stations/');
    expect(overview).toMatchObject({
      page: 'happy-cleaning-overview',
      domain: 'happy-cleaning',
      readContractKey: 'happy-cleaning-overview',
    });
    expect(management).toMatchObject({
      page: 'happy-cleaning-stations',
      event_id: '7',
      readContractKey: 'happy-cleaning-stations',
    });
    expect(routeDataRequest(management).url).toBe(
      '/api/route-data/happy-cleaning-stations/?event_id=7',
    );
    expect(print).toMatchObject({
      page: 'happy-cleaning-print',
      event_id: '7',
      readContractKey: 'happy-cleaning-print',
    });
    expect(routeDataRequest(print).url).toBe(
      '/api/route-data/happy-cleaning-print/?event_id=7',
    );
  });

  it('lists contiguous events, creates, and confirms only eligible deletion', async () => {
    const mutate = vi.fn().mockResolvedValue({ ok: true });
    vi.spyOn(window, 'confirm').mockReturnValue(true);
    render(<HappyCleaningOverviewPage data={{ events: [
      { id: 7, display_number: 1, revision: 2, can_delete: false },
      { id: 9, display_number: 2, revision: 4, can_delete: true },
    ] }} mutate={mutate} />);

    expect(screen.getByRole('link', { name: 'Einteilung für Happy Cleaning 1' })).toHaveAttribute(
      'href', '/happy-cleaning/7/assignment/',
    );
    expect(screen.getByRole('link', { name: 'Stationen für Happy Cleaning 2' })).toHaveAttribute(
      'href', '/happy-cleaning/9/stations/',
    );
    expect(screen.getByRole('link', { name: 'Nummernliste für Happy Cleaning 1 drucken' })).toHaveAttribute(
      'href', '/happy-cleaning/7/print/',
    );
    expect(screen.queryByRole('button', { name: 'Happy Cleaning 1 löschen' })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Happy Cleaning hinzufügen' }));
    await waitFor(() => expect(mutate).toHaveBeenCalledTimes(1));
    fireEvent.click(screen.getByRole('button', { name: 'Happy Cleaning 2 löschen' }));

    await waitFor(() => expect(mutate).toHaveBeenCalledTimes(2));
    expect(mutate.mock.calls[0][0]).toBe('/api/happy-cleaning/events/create/');
    expect(mutate.mock.calls[1][0]).toBe('/api/happy-cleaning/events/9/delete/');
    expect(mutate.mock.calls[1][1]).toMatchObject({ expected_revision: 4 });
  });

  it('renders compact expandable cards, progress, forms, and accessible ordering', async () => {
    const mutate = vi.fn().mockResolvedValue({ ok: true });
    render(<HappyCleaningManagementPage data={stationsData} mutate={mutate} />);

    expect(screen.getByText('50%')).toBeInTheDocument();
    expect(screen.getByText('—')).toBeInTheDocument();
    expect(screen.queryByLabelText('Name der Station Speisesaal')).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Speisesaal öffnen' }));
    expect(screen.getByLabelText('Name der Station Speisesaal')).toHaveValue('Speisesaal');
    expect(screen.getByLabelText('Kapazität der Station Speisesaal')).toBeDisabled();

    fireEvent.click(screen.getByRole('button', { name: 'Bad nach oben' }));
    await waitFor(() => expect(mutate).toHaveBeenCalledWith(
      '/api/happy-cleaning/events/7/stations/reorder/',
      expect.objectContaining({ expected_revision: 5, station_ids: [11, 10] }),
    ));

    fireEvent.click(screen.getByRole('button', { name: 'Aufgabe Boden nach oben' }));
    await waitFor(() => expect(mutate).toHaveBeenCalledWith(
      '/api/happy-cleaning/events/7/stations/10/todos/reorder/',
      expect.objectContaining({ expected_version: 3, todo_ids: [101, 100] }),
    ));
  });

  it('keeps validation visible and expands the affected card after a failed mutation', async () => {
    const error = new Error('validation');
    error.payload = { errors: { name: ['This field is required.'] } };
    const mutate = vi.fn().mockRejectedValue(error);
    render(<HappyCleaningManagementPage data={stationsData} mutate={mutate} />);
    fireEvent.click(screen.getByRole('button', { name: 'Speisesaal öffnen' }));
    fireEvent.change(screen.getByLabelText('Name der Station Speisesaal'), { target: { value: '' } });
    fireEvent.click(screen.getByRole('button', { name: 'Station Speisesaal speichern' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('This field is required.');
    expect(screen.getByLabelText('Name der Station Speisesaal')).toBeInTheDocument();
  });

  it('requires an explicit copy decision when duplicate station names are returned', async () => {
    const duplicate = new Error('duplicate');
    duplicate.payload = { code: 'duplicate_names', duplicate_names: ['Speisesaal'] };
    const mutate = vi.fn()
      .mockRejectedValueOnce(duplicate)
      .mockResolvedValueOnce({ ok: true });
    render(<HappyCleaningManagementPage data={stationsData} mutate={mutate} />);

    fireEvent.click(screen.getByRole('button', { name: 'Stationen kopieren' }));
    fireEvent.change(screen.getByLabelText('Quell-Happy-Cleaning'), { target: { value: '3' } });
    fireEvent.click(screen.getByRole('button', { name: 'Alle Stationen kopieren' }));
    fireEvent.click(await screen.findByRole('button', { name: 'Doppelte trotzdem kopieren' }));

    await waitFor(() => expect(mutate).toHaveBeenLastCalledWith(
      '/api/happy-cleaning/events/7/stations/copy/',
      expect.objectContaining({
        source_event_id: 3,
        copy_all: true,
        duplicate_strategy: 'copy',
      }),
    ));
  });

  it('renders clear empty states', () => {
    const { unmount } = render(<HappyCleaningOverviewPage data={{ events: [] }} mutate={vi.fn()} />);
    expect(screen.getByText('Noch kein Happy Cleaning angelegt.')).toBeInTheDocument();
    unmount();
    render(<HappyCleaningManagementPage data={{ ...stationsData, stations: [] }} mutate={vi.fn()} />);
    expect(screen.getByText('Noch keine Station angelegt.')).toBeInTheDocument();
  });

  it('renders the printable allow-listed groups in projection order', () => {
    render(<HappyCleaningPrintPage data={{
      event: { id: 7, display_number: 2, revision: 5 },
      present_numbered: [
        { id: 2, full_name: 'Zoe Alpha', number: 2, illness: 'Private Krankheit' },
        { id: 1, full_name: 'Ada Lovelace', number: 7, anmelder_email: 'private@example.test' },
      ],
      present_numberless: [
        { id: 3, full_name: 'Aaron Zebra', anmerkung: 'Private Notiz' },
        { id: 4, full_name: 'Grace Hopper' },
      ],
      absent: [
        { id: 5, full_name: 'Barbara Able', number: 9, absence_location: 'Krankenhaus' },
        { id: 6, full_name: 'Linus Torvalds', number: 3, absence_location: 'Sallingstadt' },
      ],
    }} />);

    const numbered = within(screen.getByRole('region', { name: 'Anwesend mit Nummer' }));
    const numberless = within(screen.getByRole('region', { name: 'Anwesend ohne Nummer' }));
    const absent = within(screen.getByRole('region', { name: 'Abwesend' }));
    expect(numbered.getAllByRole('listitem').map(row => row.textContent)).toEqual([
      '2Zoe Alpha',
      '7Ada Lovelace',
    ]);
    expect(numberless.getAllByRole('listitem').map(row => row.textContent)).toEqual([
      'Aaron Zebra',
      'Grace Hopper',
    ]);
    expect(absent.getAllByRole('listitem').map(row => row.textContent)).toEqual([
      'Barbara AbleNummer 9 · Abwesenheitsort: Krankenhaus',
      'Linus TorvaldsNummer 3 · Abwesenheitsort: Sallingstadt',
    ]);
    expect(screen.queryByText(/Private Krankheit|private@example\.test|Private Notiz/)).not.toBeInTheDocument();
  });

  it('keeps empty sections titled and offers a working print action', () => {
    const print = vi.spyOn(window, 'print').mockImplementation(() => {});
    render(<HappyCleaningPrintPage data={{
      event: { id: 7, display_number: 2, revision: 5 },
      present_numbered: [],
      present_numberless: [],
      absent: [],
    }} />);

    expect(screen.getAllByText('Keine Kinder in diesem Abschnitt.')).toHaveLength(3);
    fireEvent.click(screen.getByRole('button', { name: 'Nummernliste drucken' }));
    expect(print).toHaveBeenCalledOnce();
  });
});
