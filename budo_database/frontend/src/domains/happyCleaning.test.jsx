import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { routeDataRequest } from '../dataLoader';
import { parseRoute, resolveRouteTitle, routeHeaderAction } from '../routes';
import {
  HappyCleaningCreateButton,
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
    localStorage.clear();
    vi.restoreAllMocks();
  });

  it('owns refreshable event management and one Turnus-wide number-list route', () => {
    const overview = parseRoute('/happy-cleaning/');
    const print = parseRoute('/happy-cleaning/print/');
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
      readContractKey: 'happy-cleaning-print',
    });
    expect(print).not.toHaveProperty('event_id');
    expect(routeDataRequest(print).url).toBe(
      '/api/route-data/happy-cleaning-print/',
    );
    expect(resolveRouteTitle(print, { authenticated: true })).toBe(
      'Nummernliste · Happy Cleaning',
    );
  });

  it('groups years, lazy loads history, persists user state, and globally sorts every station table', async () => {
    const mutate = vi.fn().mockResolvedValue({ ok: true });
    const fetchImpl = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        years: [{
          year: 2025, loaded: true, is_active: false,
          turnuses: [{ id: 3, number: 4, start: '2025-08-01', is_active: false, events: [{
            id: 5, display_number: 1, revision: 2, can_delete: false,
            stations: [{ id: 50, name: 'Archiv', max_kids: 8, meeting_point: 'Altbau', task_item_count: 1 }],
          }] }],
        }],
      }),
    });
    const data = {
      user_id: 42,
      active_year: 2026,
      years: [
        {
          year: 2026, loaded: true, is_active: true,
          turnuses: [{ id: 1, number: 3, start: '2026-07-01', is_active: true, events: [
            {
              id: 7, display_number: 1, revision: 2, can_delete: false,
              stations: [
                { id: 70, name: 'Küche', max_kids: 2, meeting_point: 'Gang', task_item_count: 4 },
                { id: 71, name: 'Bad', max_kids: 5, meeting_point: 'Hof', task_item_count: 1 },
                { id: 72, name: 'Balkon', max_kids: 5, meeting_point: 'Hof', task_item_count: 2 },
              ],
            },
            { id: 9, display_number: 2, revision: 4, can_delete: true, stations: [] },
          ] }],
        },
        {
          year: 2025, loaded: false, is_active: false,
          turnuses: [{ id: 3, number: 4, start: '2025-08-01', is_active: false, events: [
            { id: 5, display_number: 1, revision: 2, can_delete: false },
          ] }],
        },
      ],
    };
    render(<HappyCleaningOverviewPage data={data} mutate={mutate} fetchImpl={fetchImpl} />);

    expect(screen.getByRole('button', { name: '2026 schließen' })).toHaveAttribute('aria-expanded', 'true');
    expect(screen.getByRole('button', { name: '2025 öffnen' })).toHaveAttribute('aria-expanded', 'false');
    const activeTable = screen.getAllByRole('table')[0];
    expect(within(activeTable).getAllByRole('columnheader').map(cell => cell.textContent)).toEqual([
      'Stationsname↑', 'Max Kinder', 'Treffpunkt', 'Anzahl Todos',
    ]);
    expect(within(activeTable).getAllByRole('row')[1]).toHaveTextContent('Bad');
    fireEvent.click(within(activeTable).getByRole('button', { name: 'Max Kinder sortieren' }));
    expect(within(activeTable).getAllByRole('row')[1]).toHaveTextContent('Küche');
    fireEvent.click(within(activeTable).getByRole('button', { name: 'Max Kinder sortieren' }));
    expect(within(activeTable).getAllByRole('row')[1]).toHaveTextContent('Bad');
    expect(within(activeTable).getAllByRole('row')[2]).toHaveTextContent('Balkon');
    expect(JSON.parse(localStorage.getItem('happy-cleaning-overview:42')).sort).toEqual({
      key: 'max_kids', direction: 'desc',
    });

    fireEvent.click(screen.getByRole('button', { name: '2025 öffnen' }));
    await waitFor(() => expect(fetchImpl).toHaveBeenCalledWith(
      '/api/route-data/happy-cleaning-overview/?year=2025',
      { credentials: 'same-origin' },
    ));
    expect(await screen.findByText('Archiv')).toBeInTheDocument();
    expect(JSON.parse(localStorage.getItem('happy-cleaning-overview:42')).openYears).toContain(2025);

    expect(screen.queryByRole('link', { name: /Nummernliste für Happy Cleaning/ })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Happy Cleaning 1 löschen' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Happy Cleaning hinzufügen' })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Happy Cleaning 2 löschen' }));

    const dialog = within(screen.getByRole('dialog', { name: 'Happy Cleaning 2 löschen' }));
    const confirmation = dialog.getByLabelText('„Happy Cleaning 2“ zur Bestätigung eingeben');
    const deleteButton = dialog.getByRole('button', { name: 'Happy Cleaning 2 endgültig löschen' });
    expect(deleteButton).toBeDisabled();
    fireEvent.change(confirmation, { target: { value: 'Happy Cleaning 1' } });
    expect(deleteButton).toBeDisabled();
    fireEvent.change(confirmation, { target: { value: 'Happy Cleaning 2' } });
    expect(deleteButton).toBeEnabled();
    fireEvent.click(deleteButton);

    await waitFor(() => expect(mutate).toHaveBeenCalledTimes(1));
    expect(mutate.mock.calls[0][0]).toBe('/api/happy-cleaning/events/9/delete/');
    expect(mutate.mock.calls[0][1]).toMatchObject({ expected_revision: 4 });
  });

  it('opens and switches station detail locally, restores focus, and keeps the URL', async () => {
    const originalPath = window.location.pathname;
    const fetchImpl = vi.fn().mockImplementation(async url => ({
      ok: true,
      json: async () => ({
        event: { id: Number(new URL(url, 'https://example.test').searchParams.get('event_id')), revision: 2 },
        station: {
          id: Number(new URL(url, 'https://example.test').searchParams.get('station_id')),
          version: 1,
          name: url.includes('station_id=71') ? 'Bad' : 'Küche',
          max_kids: 5,
          meeting_point: 'Hof',
          wishes: '',
          content: [],
          is_historical: false,
          can_toggle_tasks: true,
          responsible: null,
          children: [],
          todo_checked_count: 0,
          todo_total_count: 0,
          todo_progress_percentage: null,
          todos: [],
        },
      }),
    }));
    render(<HappyCleaningOverviewPage data={{
      user_id: 42,
      active_year: 2026,
      years: [{
        year: 2026, loaded: true, is_active: true,
        turnuses: [{ id: 1, number: 3, start: '2026-07-01', is_active: true, events: [{
          id: 7, display_number: 1, revision: 2, can_delete: false,
          stations: [
            { id: 70, name: 'Küche', max_kids: 2, meeting_point: 'Gang', task_item_count: 4 },
            { id: 71, name: 'Bad', max_kids: 5, meeting_point: 'Hof', task_item_count: 1 },
          ],
        }] }],
      }],
    }} mutate={vi.fn()} fetchImpl={fetchImpl} />);

    const kitchen = screen.getByRole('button', { name: 'Station Küche öffnen' });
    fireEvent.click(kitchen);
    expect(await screen.findByRole('heading', { name: 'Küche' })).toBeInTheDocument();
    expect(document.querySelector('.happy-cleaning-overview-split')).toBeInTheDocument();
    expect(window.location.pathname).toBe(originalPath);

    fireEvent.click(screen.getByRole('row', { name: 'Station Bad' }));
    expect(await screen.findByRole('heading', { name: 'Bad' })).toBeInTheDocument();
    expect(window.location.pathname).toBe(originalPath);

    fireEvent.click(screen.getByRole('button', { name: 'Zur Liste' }));
    await waitFor(() => expect(screen.queryByRole('heading', { name: 'Bad' })).not.toBeInTheDocument());
    expect(screen.getByRole('button', { name: 'Station Bad öffnen' })).toHaveFocus();
  });

  it('copies selected overview stations to another active-Turnus Happy Cleaning with visible states', async () => {
    let resolveCopy;
    const mutate = vi.fn(() => new Promise(resolve => { resolveCopy = resolve; }));
    const data = {
      user_id: 42,
      active_year: 2025,
      copy_targets: [
        { id: 7, display_number: 1, revision: 2, label: 'Happy Cleaning 1' },
        { id: 9, display_number: 2, revision: 4, label: 'Happy Cleaning 2' },
      ],
      years: [{
        year: 2025, loaded: true, is_active: false,
        turnuses: [{ id: 3, number: 4, start: '2025-08-01', is_active: false, events: [{
          id: 5, display_number: 1, revision: 2, can_delete: false,
          stations: [
            { id: 50, name: 'Küche', max_kids: 8, meeting_point: 'Altbau', task_item_count: 1 },
            { id: 51, name: 'Bad', max_kids: 4, meeting_point: 'Gang', task_item_count: 2 },
          ],
        }] }],
      }],
    };
    render(<HappyCleaningOverviewPage data={data} mutate={mutate} />);

    fireEvent.click(screen.getByRole('button', { name: 'Stationen aus Happy Cleaning 1 kopieren' }));
    const dialog = within(screen.getByRole('dialog', { name: 'Stationen kopieren' }));
    expect(dialog.getByRole('option', { name: 'Happy Cleaning 1' })).toBeInTheDocument();
    fireEvent.click(dialog.getByLabelText('Alle Stationen auswählen'));
    expect(dialog.getByLabelText('Station Küche auswählen')).toBeChecked();
    expect(dialog.getByLabelText('Station Bad auswählen')).toBeChecked();
    fireEvent.change(dialog.getByLabelText('Ziel-Happy-Cleaning'), { target: { value: '9' } });
    fireEvent.click(dialog.getByRole('button', { name: 'Prüfen und kopieren' }));
    expect(dialog.getByRole('status')).toHaveTextContent('Stationen werden geprüft');
    expect(dialog.getByRole('status').querySelector('.happy-cleaning-copy-spinner')).toBeInTheDocument();
    expect(mutate).toHaveBeenCalledWith(
      '/api/happy-cleaning/events/9/stations/copy/',
      expect.objectContaining({
        expected_revision: 4,
        source_event_id: 5,
        station_ids: [50, 51],
      }),
    );
    resolveCopy({ ok: true, result: 'copied', copied_stations: [{ id: 100 }, { id: 101 }] });
    await waitFor(() => expect(dialog.getByRole('status')).toHaveTextContent('2 Stationen wurden kopiert'));
  });

  it('keeps copy conflicts and errors in the overview dialog', async () => {
    const conflict = {
      ok: true, result: 'conflicts', target_revision: 4,
      conflicts: [{ source_station_id: 50, source_name: 'Bad', target_station_id: 90, target_name: 'Bad Kinder' }],
    };
    const failed = new Error('network down');
    const mutate = vi.fn().mockResolvedValueOnce(conflict).mockRejectedValueOnce(failed);
    const data = {
      user_id: 42, active_year: 2026,
      copy_targets: [{ id: 9, display_number: 2, revision: 4, label: 'Happy Cleaning 2' }],
      years: [{ year: 2026, loaded: true, is_active: true, turnuses: [{
        id: 1, number: 1, start: '2026-07-01', is_active: true, events: [{
          id: 7, display_number: 1, revision: 2, can_delete: false,
          stations: [{ id: 50, name: 'Bad', max_kids: 4, meeting_point: 'Gang', task_item_count: 2 }],
        }],
      }] }],
    };
    render(<HappyCleaningOverviewPage data={data} mutate={mutate} />);
    fireEvent.click(screen.getByRole('button', { name: 'Stationen aus Happy Cleaning 1 kopieren' }));
    const dialog = within(screen.getByRole('dialog', { name: 'Stationen kopieren' }));
    fireEvent.click(dialog.getByLabelText('Station Bad auswählen'));
    fireEvent.change(dialog.getByLabelText('Ziel-Happy-Cleaning'), { target: { value: '9' } });
    fireEvent.click(dialog.getByRole('button', { name: 'Prüfen und kopieren' }));
    expect(await dialog.findByRole('alert')).toHaveTextContent('Bad → Bad Kinder');
    expect(dialog.getByText(/Zielversion 4/)).toBeInTheDocument();
    fireEvent.click(dialog.getByRole('button', { name: 'Erneut prüfen' }));
    expect(await dialog.findByRole('alert')).toHaveTextContent('network down');
  });

  it('requires an accessible explicit conflict decision and one eligible candidate', async () => {
    const mutate = vi.fn().mockResolvedValue({
      ok: true, result: 'conflicts', target_revision: 4,
      source_event_id: 5, station_ids: [50], conflict_free_station_ids: [],
      conflicts: [
        {
          source_station_id: 50, source_name: 'Bad', source_task_count: 2,
          target_station_id: 90, target_name: 'Bad Kinder', target_task_count: 1,
          overwrite_eligible: false, overwrite_disabled_reason: 'Bereits zugeordnet.',
        },
        {
          source_station_id: 50, source_name: 'Bad', source_task_count: 2,
          target_station_id: 91, target_name: 'Bad Team', target_task_count: 3,
          overwrite_eligible: true, overwrite_disabled_reason: null,
        },
      ],
    });
    const data = {
      user_id: 42, active_year: 2026,
      copy_targets: [{ id: 9, revision: 4, label: 'Happy Cleaning 2' }],
      years: [{ year: 2026, loaded: true, is_active: true, turnuses: [{
        id: 1, number: 1, is_active: true, events: [{
          id: 5, display_number: 1, revision: 2,
          stations: [{ id: 50, name: 'Bad', task_item_count: 2 }],
        }],
      }] }],
    };
    render(<HappyCleaningOverviewPage data={data} mutate={mutate} />);
    fireEvent.click(screen.getByRole('button', { name: 'Stationen aus Happy Cleaning 1 kopieren' }));
    const dialog = within(screen.getByRole('dialog', { name: 'Stationen kopieren' }));
    fireEvent.click(dialog.getByLabelText('Station Bad auswählen'));
    fireEvent.change(dialog.getByLabelText('Ziel-Happy-Cleaning'), { target: { value: '9' } });
    fireEvent.click(dialog.getByRole('button', { name: 'Prüfen und kopieren' }));
    expect(await dialog.findByText('1 Konfliktgruppe(n) ungelöst.')).toBeInTheDocument();
    expect(dialog.getByRole('radio', { name: 'Bestehende Station überschreiben' })).not.toBeChecked();
    expect(dialog.getByRole('button', { name: 'Auswahl verbindlich kopieren' })).toBeDisabled();
    fireEvent.change(dialog.getByLabelText('Bestehende Station für Bad'), { target: { value: '90' } });
    expect(dialog.getByRole('radio', { name: /Bestehende Station überschreiben/ })).toBeDisabled();
    expect(dialog.getByText('Bereits zugeordnet.')).toBeInTheDocument();
    fireEvent.change(dialog.getByLabelText('Bestehende Station für Bad'), { target: { value: '91' } });
    fireEvent.click(dialog.getByRole('radio', { name: 'Inhalte anhängen' }));
    expect(dialog.getByRole('button', { name: 'Auswahl verbindlich kopieren' })).toBeEnabled();
  });

  it('creates Happy Cleaning from the header action', async () => {
    const mutate = vi.fn().mockResolvedValue({ ok: true });
    render(<HappyCleaningCreateButton mutate={mutate} />);

    fireEvent.click(screen.getByRole('button', { name: 'Happy Cleaning hinzufügen' }));

    await waitFor(() => expect(mutate).toHaveBeenCalledWith(
      '/api/happy-cleaning/events/create/',
      expect.objectContaining({ request_id: expect.any(String) }),
    ));
  });

  it('restores the current user overview preference and lazy loads remembered open years', async () => {
    localStorage.setItem('happy-cleaning-overview:8', JSON.stringify({
      openYears: [2026, 2024],
      sort: { key: 'task_item_count', direction: 'desc' },
    }));
    const fetchImpl = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ years: [{
        year: 2024, loaded: true, is_active: false, turnuses: [],
      }] }),
    });
    render(<HappyCleaningOverviewPage data={{
      user_id: 8,
      active_year: 2026,
      years: [
        { year: 2026, loaded: true, is_active: true, turnuses: [] },
        { year: 2024, loaded: false, is_active: false, turnuses: [] },
      ],
    }} mutate={vi.fn()} fetchImpl={fetchImpl} />);

    expect(screen.getByRole('button', { name: '2024 schließen' })).toHaveAttribute('aria-expanded', 'true');
    await waitFor(() => expect(fetchImpl).toHaveBeenCalledWith(
      '/api/route-data/happy-cleaning-overview/?year=2024',
      { credentials: 'same-origin' },
    ));
  });

  it('renders compact expandable cards, progress, forms, and accessible ordering', async () => {
    const mutate = vi.fn().mockResolvedValue({ ok: true });
    render(<HappyCleaningManagementPage data={stationsData} mutate={mutate} />);

    expect(screen.queryByRole('link', { name: 'Zur Übersicht' })).not.toBeInTheDocument();
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

  it('copies all stations selected from the management source', async () => {
    const mutate = vi.fn().mockResolvedValue({ ok: true, result: 'copied' });
    render(<HappyCleaningManagementPage data={stationsData} mutate={mutate} />);

    fireEvent.click(screen.getByRole('button', { name: 'Stationen kopieren' }));
    fireEvent.change(screen.getByLabelText('Quell-Happy-Cleaning'), { target: { value: '3' } });
    fireEvent.click(screen.getByRole('button', { name: 'Alle Stationen kopieren' }));

    await waitFor(() => expect(mutate).toHaveBeenCalledWith(
      '/api/happy-cleaning/events/7/stations/copy/',
      expect.objectContaining({
        source_event_id: 3,
        station_ids: [30, 31],
      }),
    ));
  });

  it('keeps the authoritative conflict preview open from management', async () => {
    const mutate = vi.fn().mockResolvedValue({
      ok: true,
      result: 'conflicts',
      target_revision: 5,
      conflicts: [{
        source_station_id: 30,
        source_name: 'Speisesaal',
        target_station_id: 10,
        target_name: 'Speisesaal groß',
      }],
    });
    render(<HappyCleaningManagementPage data={stationsData} mutate={mutate} />);
    fireEvent.click(screen.getByRole('button', { name: 'Stationen kopieren' }));
    fireEvent.change(screen.getByLabelText('Quell-Happy-Cleaning'), { target: { value: '3' } });
    fireEvent.click(screen.getByRole('button', { name: 'Alle Stationen kopieren' }));

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Speisesaal → Speisesaal groß',
    );
    expect(screen.getByRole('dialog', { name: 'Stationen kopieren' })).toBeInTheDocument();
  });

  it('renders clear empty states', () => {
    const { unmount } = render(<HappyCleaningOverviewPage data={{
      user_id: 1, active_year: 2026, years: [],
    }} mutate={vi.fn()} />);
    expect(screen.getByText('Noch kein Happy Cleaning angelegt.')).toBeInTheDocument();
    unmount();
    render(<HappyCleaningManagementPage data={{ ...stationsData, stations: [] }} mutate={vi.fn()} />);
    expect(screen.getByText('Noch keine Station angelegt.')).toBeInTheDocument();
  });

  it('renders only the printable fields for each group', () => {
    render(<HappyCleaningPrintPage data={{
      number_batch_event_id: 7,
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

    expect(screen.getByRole('heading', { name: 'Happy Cleaning · Nummernliste', level: 1 })).toBeInTheDocument();
    const numbered = within(screen.getByRole('table', { name: 'Anwesend mit Nummer' }));
    const numberless = within(screen.getByRole('table', { name: 'Anwesend ohne Nummer' }));
    const absent = within(screen.getByRole('table', { name: 'Abwesend' }));
    expect(numbered.getAllByRole('columnheader').map(cell => cell.textContent)).toEqual([
      'Nummer',
      'Name',
    ]);
    expect(numbered.getAllByRole('row').slice(1).map(row => (
      within(row).getAllByRole('cell').map(cell => cell.textContent)
    ))).toEqual([
      ['2', 'Zoe Alpha'],
      ['7', 'Ada Lovelace'],
    ]);
    expect(numberless.getAllByRole('row').slice(1).map(row => (
      within(row).getAllByRole('cell').map(cell => cell.textContent)
    ))).toEqual([
      ['Aaron Zebra'],
      ['Grace Hopper'],
    ]);
    expect(absent.getAllByRole('columnheader').map(cell => cell.textContent)).toEqual([
      'Nummer',
      'Name',
    ]);
    expect(absent.getAllByRole('row').slice(1).map(row => (
      within(row).getAllByRole('cell').map(cell => cell.textContent)
    ))).toEqual([
      ['9', 'Barbara Able'],
      ['3', 'Linus Torvalds'],
    ]);
    expect(screen.queryByText(/Private Krankheit|private@example\.test|Private Notiz/)).not.toBeInTheDocument();
  });

  it('offers the same fixed batch-number dialog on the number list after HC1 is complete', async () => {
    const mutate = vi.fn().mockResolvedValue({ ok: true });
    render(<HappyCleaningPrintPage data={{
      number_batch_event_id: 7,
      number_batch: {
        available: true,
        children: [
          { id: 4, full_name: 'Grace Hopper', number: 3, expected_version: 1 },
        ],
      },
      present_numbered: [],
      present_numberless: [{ id: 4, full_name: 'Grace Hopper' }],
      absent: [],
    }} mutate={mutate} />);

    const batchButton = screen.getByRole('button', { name: 'Kindern ohne Nummern, Nummern zuteilen' });
    expect(screen.getByRole('region', { name: 'Anwesend ohne Nummer' })).toContainElement(batchButton);
    expect([...document.querySelectorAll('.happy-cleaning-print-section > h2')].map(heading => heading.textContent)).toEqual([
      'Anwesend ohne Nummer',
      'Anwesend mit Nummer',
      'Abwesend',
    ]);

    fireEvent.click(batchButton);
    const dialog = screen.getByRole('dialog');
    expect(within(dialog).getByRole('list', { name: 'Vorgeschlagene Nummern' })).toHaveTextContent('Grace Hopper3');
    fireEvent.click(within(dialog).getByRole('button', { name: 'Bestätigen' }));

    await waitFor(() => expect(mutate).toHaveBeenCalledWith(
      '/api/happy-cleaning/events/7/numbers/assign-missing/',
      expect.objectContaining({
        assignments: [{ child_id: 4, number: 3, expected_version: 1 }],
      }),
    ));
  });

  it('keeps empty sections titled without duplicating navigation actions in the page', () => {
    render(<HappyCleaningPrintPage data={{
      number_batch_event_id: 7,
      present_numbered: [],
      present_numberless: [],
      absent: [],
    }} />);

    expect(screen.getAllByText('Keine Kinder in diesem Abschnitt.')).toHaveLength(3);
    expect(screen.queryByRole('link', { name: 'Zur Übersicht' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Drucken' })).not.toBeInTheDocument();
  });

  it('provides a compact print-icon header action with the label Drucken', () => {
    const print = vi.spyOn(window, 'print').mockImplementation(() => {});
    render(routeHeaderAction(parseRoute('/happy-cleaning/print/'), {}));

    const printButton = screen.getByRole('button', { name: 'Drucken' });
    expect(printButton).toHaveClass('mobile-icon-action');
    expect(printButton.querySelector('.desktop-action-label')).toHaveTextContent('Drucken');
    expect(printButton.querySelector('.lucide-printer')).toBeInTheDocument();
    expect(printButton).not.toHaveTextContent('Nummernliste');

    fireEvent.click(printButton);
    expect(print).toHaveBeenCalledOnce();
  });
});
