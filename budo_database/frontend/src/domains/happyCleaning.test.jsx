import { cleanup, fireEvent, render as testingLibraryRender, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { Toaster } from '../components/ui/toast';
import { routeDataRequest } from '../dataLoader';
import { parseRoute, resolveRouteTitle, routeHeaderAction } from '../routes';
import { expectErrorToastOnly } from '../test-support';
import {
  HappyCleaningCreateButton,
  HappyCleaningManagementPage,
  HappyCleaningOverviewPage,
  HappyCleaningPrintPage,
} from './happyCleaning';

const render = ui => testingLibraryRender(ui, {
  wrapper: ({ children }) => <Toaster timeout={0}>{children}</Toaster>,
});

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
    document.getElementById('react-app-styles')?.remove();
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
    expect(management.page).toBe('not-found');
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
    const user = userEvent.setup();
    const mutate = vi.fn().mockResolvedValue({ ok: true });
    const fetchImpl = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        years: [{
          year: 2025, loaded: true, is_active: false,
          turnuses: [{ id: 3, number: 4, start: '2025-08-01', is_active: false, events: [{
            id: 5, display_number: 1, revision: 2, can_delete: false,
            stations: [{
              id: 50, name: 'Archiv', max_kids: 8, meeting_point: 'Altbau',
              responsible: null, task_item_count: 1,
            }],
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
                {
                  id: 70, name: 'Küche', max_kids: 2, meeting_point: 'Gang',
                  responsible: { id: 4, name: 'Mira' }, task_item_count: 4,
                },
                {
                  id: 71, name: 'Bad', max_kids: 5, meeting_point: 'Hof',
                  responsible: null, task_item_count: 1,
                },
                {
                  id: 72, name: 'Balkon', max_kids: 5, meeting_point: 'Hof',
                  responsible: { id: 5, name: 'Zora' }, task_item_count: 2,
                },
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

    const activeYearToggle = screen.getByRole('button', { name: '2026 schließen' });
    expect(activeYearToggle).toHaveAttribute('aria-expanded', 'true');
    expect(activeYearToggle.querySelector('.icon')).toHaveTextContent('−');
    expect(screen.getByRole('button', { name: '2025 öffnen' })).toHaveAttribute('aria-expanded', 'false');

    expect(screen.getByRole('heading', {
      level: 2,
      name: '3. Turnus 2026 · Happy Cleaning 1',
    })).toBeInTheDocument();
    const eventToggle = screen.getByRole('button', {
      name: '3. Turnus 2026 · Happy Cleaning 1 schließen',
    });
    const controlledContent = document.getElementById(eventToggle.getAttribute('aria-controls'));
    expect(eventToggle).toHaveAttribute('aria-expanded', 'true');
    expect(controlledContent).toHaveAttribute('aria-hidden', 'false');
    fireEvent.click(eventToggle);
    const closedEventToggle = screen.getByRole('button', {
      name: '3. Turnus 2026 · Happy Cleaning 1 öffnen',
    });
    expect(closedEventToggle).toHaveAttribute('aria-expanded', 'false');
    expect(controlledContent).toHaveAttribute('inert');
    fireEvent.click(closedEventToggle);

    expect(screen.getAllByRole('table')).toHaveLength(1);
    expect(screen.getByText('Noch keine Stationen angelegt.')).toBeInTheDocument();
    const activeTable = screen.getByRole('table');
    expect(activeTable).toHaveAttribute('data-slot', 'table');
    expect(activeTable.parentElement).toHaveAttribute('data-slot', 'table-scroll');
    expect(activeTable.parentElement).toHaveAttribute('data-sticky-first-column', '');
    expect(within(activeTable).getAllByRole('columnheader').map(cell => cell.textContent)).toEqual([
      'Stationsname↑', 'Max Kinder', 'Treffpunkt', 'Verantwortlicher', 'To-Dos',
    ]);
    expect(within(activeTable).getAllByRole('row')[1]).toHaveTextContent('Bad');
    expect(within(activeTable).getAllByRole('row')[1].children[3]).toHaveTextContent('—');
    expect(within(activeTable).getAllByRole('row')[3].children[3]).toHaveTextContent('Mira');
    const responsibleSort = within(activeTable).getByRole('button', { name: 'Verantwortlicher sortieren' });
    await user.click(responsibleSort);
    expect(within(activeTable).getAllByRole('row').slice(1).map(row => row.children[3].textContent)).toEqual([
      '—', 'Mira', 'Zora',
    ]);
    await user.click(responsibleSort);
    expect(within(activeTable).getAllByRole('row').slice(1).map(row => row.children[3].textContent)).toEqual([
      'Zora', 'Mira', '—',
    ]);
    const capacitySort = within(activeTable).getByRole('button', { name: 'Max Kinder sortieren' });
    capacitySort.focus();
    await user.keyboard('{Enter}');
    expect(within(activeTable).getAllByRole('row')[1]).toHaveTextContent('Küche');
    await user.keyboard('{Enter}');
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
    expect(confirmation).toHaveAttribute('data-slot', 'input');
    expect(confirmation.labels).toHaveLength(1);
    expect(confirmation.labels[0]).toHaveTextContent('„Happy Cleaning 2“ zur Bestätigung eingeben');
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

  it('prints one task page per station, then restores normal overview printing', async () => {
    let printedText = '';
    let printStylesMedia = '';
    const printedViews = [];
    const stylesheet = document.createElement('link');
    stylesheet.id = 'react-app-styles';
    stylesheet.media = 'screen';
    document.head.append(stylesheet);
    const print = vi.spyOn(window, 'print').mockImplementation(() => {
      const todoPrintPages = document.querySelector('.happy-cleaning-todo-print-pages');
      printedText = todoPrintPages?.textContent || '';
      printStylesMedia = stylesheet.media;
      printedViews.push({
        overview: Boolean(document.querySelector('#body-container')),
        todoPrintPages: Boolean(todoPrintPages),
      });
    });
    const fetchImpl = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        event: { id: 7, display_number: 1, revision: 2 },
        stations: [
          {
            id: 70,
            name: 'Küche',
            document: {
              type: 'doc',
              content: [{
                type: 'taskList',
                content: [
                  {
                    type: 'taskItem', attrs: { checked: false },
                    content: [{ type: 'paragraph', content: [{ type: 'text', text: 'Boden kehren' }] }],
                  },
                  {
                    type: 'taskItem', attrs: { checked: true },
                    content: [{ type: 'paragraph', content: [{ type: 'text', text: 'Tische wischen' }] }],
                  },
                ],
              }],
            },
          },
          { id: 71, name: 'Bad', document: { type: 'doc', content: [] } },
        ],
      }),
    });
    render(<HappyCleaningOverviewPage data={{
      user_id: 42,
      active_year: 2026,
      years: [{
        year: 2026, loaded: true, is_active: true,
        turnuses: [{ id: 1, number: 3, start: '2026-07-01', is_active: true, events: [{
          id: 7, display_number: 1, revision: 2, can_delete: false,
          stations: [
            {
              id: 70,
              name: 'Küche',
              max_kids: 2,
              meeting_point: 'Gang',
              task_item_count: 2,
              document: {
                type: 'doc',
                content: [{
                  type: 'taskList',
                  content: [
                    {
                      type: 'taskItem', attrs: { checked: false },
                      content: [{ type: 'paragraph', content: [{ type: 'text', text: 'Boden kehren' }] }],
                    },
                    {
                      type: 'taskItem', attrs: { checked: true },
                      content: [{ type: 'paragraph', content: [{ type: 'text', text: 'Tische wischen' }] }],
                    },
                  ],
                }],
              },
            },
            {
              id: 71, name: 'Bad', max_kids: 2, meeting_point: 'Hof',
              task_item_count: 0, document: { type: 'doc', content: [] },
            },
          ],
        }] }],
      }],
    }} mutate={vi.fn()} fetchImpl={fetchImpl} />);

    fireEvent.click(screen.getByRole('button', { name: 'To-Dos für Happy Cleaning 1 drucken' }));

    await waitFor(() => expect(print).toHaveBeenCalledOnce());
    expect(printedText).toContain('Küche');
    expect(printedText).toContain('Boden kehren');
    expect(printStylesMedia).toBe('screen');
    expect(stylesheet).toHaveAttribute('media', 'screen');
    stylesheet.remove();
    expect(fetchImpl).toHaveBeenCalledWith(
      '/api/route-data/happy-cleaning-todo-print/?event_id=7',
      { credentials: 'same-origin' },
    );
    const pages = document.querySelector('.happy-cleaning-todo-print-pages');
    expect(pages.parentElement).toBe(document.body);
    expect(pages).toHaveAccessibleName('To-Dos für Happy Cleaning 1');
    const stations = [...pages.querySelectorAll('.happy-cleaning-todo-print-station')];
    expect(stations).toHaveLength(2);
    expect(stations.map(station => station.querySelector('h1').textContent)).toEqual(['Küche', 'Bad']);
    expect(stations[0]).toHaveTextContent('☐Boden kehren');
    expect(stations[0]).toHaveTextContent('☒Tische wischen');
    expect(stations[1]).toHaveTextContent('Keine Aufgaben hinterlegt.');

    fireEvent(window, new Event('afterprint'));
    await waitFor(() => {
      expect(document.querySelector('.happy-cleaning-todo-print-pages')).not.toBeInTheDocument();
    });

    window.print();
    expect(print).toHaveBeenCalledTimes(2);
    expect(printedViews).toEqual([
      { overview: true, todoPrintPages: true },
      { overview: true, todoPrintPages: false },
    ]);
  });

  it('opens fullscreen station detail below the header, switches locally, and restores focus', async () => {
    const user = userEvent.setup();
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
    kitchen.focus();
    await user.keyboard('{Enter}');
    const detailHeading = await screen.findByRole('heading', { name: 'Küche' });
    const detailOverlay = detailHeading.closest('aside[aria-live="polite"]');
    expect(detailOverlay).toHaveStyle({
      top: 'var(--app-header-height, 0px)',
      right: '0px',
      bottom: '0px',
      left: '0px',
    });
    expect(window.location.pathname).toBe(originalPath);

    screen.getByRole('row', { name: 'Station Bad' }).focus();
    await user.keyboard('{Enter}');
    expect(await screen.findByRole('heading', { name: 'Bad' })).toBeInTheDocument();
    expect(window.location.pathname).toBe(originalPath);

    screen.getByRole('button', { name: 'Zur Liste' }).focus();
    await user.keyboard('{Enter}');
    await waitFor(() => expect(screen.queryByRole('heading', { name: 'Bad' })).not.toBeInTheDocument());
    expect(screen.getByRole('button', { name: 'Station Bad öffnen' })).toHaveFocus();
  });

  it('patches only the target card after copying from an open detail', async () => {
    const fetchImpl = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        event: { id: 7, display_number: 1, revision: 2 },
        copy_targets: [{ id: 9, display_number: 2, revision: 4, label: 'Happy Cleaning 2' }],
        station: {
          id: 70, version: 1, name: 'Küche', max_kids: 2,
          meeting_point: 'Gang', wishes: '', content: [], is_historical: false,
          can_toggle_tasks: true, responsible: null, children: [],
          todo_checked_count: 0, todo_total_count: 0,
          todo_progress_percentage: null, todos: [],
        },
      }),
    });
    const mutate = vi.fn().mockResolvedValue({
      ok: true,
      result: 'copied',
      event: { id: 9, display_number: 2, revision: 5 },
      affected_stations: [{
        id: 90, name: 'Küche', max_kids: 2, meeting_point: 'Gang', todos: [],
      }],
    });
    render(<HappyCleaningOverviewPage data={{
      user_id: 42,
      active_year: 2026,
      copy_targets: [
        { id: 7, display_number: 1, revision: 2, label: 'Happy Cleaning 1' },
        { id: 9, display_number: 2, revision: 4, label: 'Happy Cleaning 2' },
      ],
      years: [{
        year: 2026, loaded: true, is_active: true,
        turnuses: [{ id: 1, number: 3, start: '2026-07-01', is_active: true, events: [
          {
            id: 7, display_number: 1, revision: 2, can_delete: false,
            stations: [{ id: 70, name: 'Küche', max_kids: 2, meeting_point: 'Gang', task_item_count: 0 }],
          },
          {
            id: 9, display_number: 2, revision: 4, can_delete: false, stations: [],
          },
        ] }],
      }],
    }} mutate={mutate} fetchImpl={fetchImpl} />);

    fireEvent.click(screen.getByRole('button', { name: 'Station Küche öffnen' }));
    await screen.findByRole('heading', { name: 'Küche' });
    fireEvent.click(screen.getByRole('button', { name: 'Station kopieren' }));
    fireEvent.change(screen.getByLabelText('Ziel-Happy-Cleaning'), {
      target: { value: '9' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Prüfen und kopieren' }));

    await waitFor(() => expect(mutate).toHaveBeenCalled());
    expect(screen.getByRole('heading', { name: 'Küche', hidden: true })).toBeInTheDocument();
    const targetCard = screen.getByRole('heading', {
      name: '3. Turnus 2026 · Happy Cleaning 2',
      hidden: true,
    }).closest('article');
    expect(within(targetCard).getByRole('button', { name: 'Station Küche öffnen', hidden: true })).toBeInTheDocument();
  });

  it('creates an active-Turnus station from a local draft and patches the sorted card', async () => {
    const fetchImpl = vi.fn();
    const mutate = vi.fn().mockResolvedValue({
      ok: true,
      event: { id: 7, display_number: 1, revision: 3 },
      station: {
        id: 73,
        version: 1,
        name: 'Abstellraum',
        max_kids: 3,
        meeting_point: 'Gang',
        wishes: '',
        position: 99,
        has_ever_had_assignment: false,
        document: { type: 'doc', content: [] },
        task_item_count: 0,
        todos: [],
        responsible: { id: 4, name: 'Mira' },
      },
    });
    const data = {
      user_id: 42,
      active_year: 2026,
      responsible_profiles: [{ id: 4, name: 'Mira' }],
      years: [
        {
          year: 2026, loaded: true, is_active: true,
          turnuses: [{
            id: 1, number: 3, start: '2026-07-01', is_active: true, events: [{
              id: 7, display_number: 1, revision: 2, can_delete: false,
              stations: [
                { id: 70, name: 'Küche', max_kids: 2, meeting_point: 'Gang', task_item_count: 4 },
              ],
            }],
          }],
        },
        {
          year: 2025, loaded: true, is_active: false,
          turnuses: [{
            id: 2, number: 2, start: '2025-07-01', is_active: false, events: [{
              id: 5, display_number: 1, revision: 2, can_delete: false,
              stations: [],
            }],
          }],
        },
      ],
    };
    const { rerender } = render(
      <HappyCleaningOverviewPage
        data={data}
        mutate={mutate}
        fetchImpl={fetchImpl}
      />,
    );

    expect(screen.getAllByRole('button', { name: 'Station hinzufügen' })).toHaveLength(1);
    fireEvent.click(screen.getByRole('button', { name: 'Station hinzufügen' }));
    expect(screen.getByLabelText('Name der Station')).toHaveValue('');
    expect(screen.getByLabelText('Verantwortlich')).toHaveTextContent('Mira');
    expect(mutate).not.toHaveBeenCalled();

    fireEvent.change(screen.getByLabelText('Name der Station'), {
      target: { value: 'Verwerfen' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Station hinzufügen' }));
    expect(screen.getByRole('dialog', { name: 'Ungespeicherte Änderungen' })).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Weiter bearbeiten' }));
    rerender(
      <HappyCleaningOverviewPage
        data={{ ...data, years: data.years.map(group => ({ ...group })) }}
        mutate={mutate}
        fetchImpl={fetchImpl}
      />,
    );
    expect(screen.getByLabelText('Name der Station')).toHaveValue('Verwerfen');
    expect(fetchImpl).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole('button', { name: 'Detail schließen' }));
    fireEvent.click(screen.getByRole('button', { name: 'Verwerfen' }));
    expect(screen.queryByDisplayValue('Verwerfen')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Station Verwerfen öffnen' })).not.toBeInTheDocument();
    expect(mutate).not.toHaveBeenCalled();

    fireEvent.click(screen.getByRole('button', { name: 'Station hinzufügen' }));
    fireEvent.change(screen.getByLabelText('Name der Station'), {
      target: { value: 'Abstellraum' },
    });
    fireEvent.change(screen.getByLabelText('Kapazität der Station'), {
      target: { value: '3' },
    });
    fireEvent.change(screen.getByLabelText('Treffpunkt der Station'), {
      target: { value: 'Gang' },
    });
    fireEvent.change(screen.getByLabelText('Verantwortlich'), {
      target: { value: '4' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Speichern' }));

    await waitFor(() => expect(mutate).toHaveBeenCalledWith(
      '/api/happy-cleaning/events/7/stations/create/',
      expect.objectContaining({
        request_id: expect.any(String),
        expected_revision: 2,
        name: 'Abstellraum',
        max_kids: 3,
        responsible_profile_id: 4,
        document: { type: 'doc', content: [] },
      }),
    ));
    expect(fetchImpl).not.toHaveBeenCalled();
    expect(screen.getByRole('heading', { name: 'Abstellraum' })).toBeInTheDocument();
    const rows = within(screen.getAllByRole('table')[0]).getAllByRole('row');
    expect(rows[1]).toHaveTextContent('Abstellraum');
    expect(rows[1].children[3]).toHaveTextContent('Mira');
    expect(rows[2]).toHaveTextContent('Küche');
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
    expect(dialog.getByLabelText('Ziel-Happy-Cleaning')).toHaveAttribute('data-slot', 'native-select');
    fireEvent.click(dialog.getByLabelText('Alle Stationen auswählen'));
    expect(dialog.getByLabelText('Station Küche auswählen')).toBeChecked();
    expect(dialog.getByLabelText('Station Bad auswählen')).toBeChecked();
    fireEvent.change(dialog.getByLabelText('Ziel-Happy-Cleaning'), { target: { value: '9' } });
    fireEvent.click(dialog.getByRole('button', { name: 'Prüfen und kopieren' }));
    expect(dialog.getByRole('status')).toHaveTextContent('Stationen werden geprüft');
    expect(dialog.getByRole('button', { name: 'Prüfen und kopieren' })).toBeDisabled();
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

  it('traps keyboard focus in the copy dialog, supports Escape, and restores its trigger', async () => {
    const user = userEvent.setup();
    render(<HappyCleaningOverviewPage data={{
      user_id: 42,
      active_year: 2026,
      copy_targets: [
        { id: 7, display_number: 1, revision: 2, label: 'Happy Cleaning 1' },
        { id: 9, display_number: 2, revision: 4, label: 'Happy Cleaning 2' },
      ],
      years: [{
        year: 2026, loaded: true, is_active: true,
        turnuses: [{ id: 1, number: 3, start: '2026-07-01', is_active: true, events: [{
          id: 7, display_number: 1, revision: 2, can_delete: false,
          stations: [{ id: 70, name: 'Küche', max_kids: 2, meeting_point: 'Gang', task_item_count: 4 }],
        }] }],
      }],
    }} mutate={vi.fn()} />);

    const trigger = screen.getByRole('button', { name: 'Stationen aus Happy Cleaning 1 kopieren' });
    await user.click(trigger);
    const dialog = screen.getByRole('dialog', { name: 'Stationen kopieren' });
    const first = within(dialog).getByRole('checkbox', { name: 'Alle Stationen auswählen' });
    const last = within(dialog).getByRole('button', { name: 'Schließen' });
    expect(first).toHaveFocus();

    last.focus();
    await user.keyboard('{Tab}');
    expect(document.activeElement).toHaveAttribute('data-base-ui-focus-guard');
    expect(trigger).not.toHaveFocus();
    await user.keyboard('{Shift>}{Tab}{/Shift}');
    expect(dialog.contains(document.activeElement)).toBe(true);
    await user.keyboard('{Escape}');

    expect(screen.queryByRole('dialog', { name: 'Stationen kopieren' })).not.toBeInTheDocument();
    expect(trigger).toHaveFocus();
  });

  it('shows failed station copies as error toasts, never inline', async () => {
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
    await expectErrorToastOnly('network down');
  });

  it('requires an accessible explicit conflict decision and one eligible candidate', async () => {
    const user = userEvent.setup();
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
    const copyTrigger = screen.getByRole('button', { name: 'Stationen aus Happy Cleaning 1 kopieren' });
    copyTrigger.focus();
    await user.keyboard('{Enter}');
    const dialog = within(screen.getByRole('dialog', { name: 'Stationen kopieren' }));
    dialog.getByLabelText('Station Bad auswählen').focus();
    await user.keyboard(' ');
    await user.selectOptions(dialog.getByLabelText('Ziel-Happy-Cleaning'), '9');
    dialog.getByRole('button', { name: 'Prüfen und kopieren' }).focus();
    await user.keyboard('{Enter}');
    expect(await dialog.findByText('1 Konfliktgruppe(n) ungelöst.')).toBeInTheDocument();
    expect(dialog.getByRole('radio', { name: 'Bestehende Station überschreiben' })).not.toBeChecked();
    expect(dialog.getByRole('button', { name: 'Auswahl verbindlich kopieren' })).toBeDisabled();
    await user.selectOptions(dialog.getByLabelText('Bestehende Station für Bad'), '90');
    expect(dialog.getByLabelText('Bestehende Station für Bad')).toHaveAttribute('data-slot', 'native-select');
    expect(dialog.getByRole('radio', { name: /Bestehende Station überschreiben/ })).toBeDisabled();
    expect(dialog.getByText('Bereits zugeordnet.')).toBeInTheDocument();
    await user.selectOptions(dialog.getByLabelText('Bestehende Station für Bad'), '91');
    for (const name of [
      'Bestehende Station überschreiben',
      'Inhalte anhängen',
      'Als eigene Station kopieren',
      'Überspringen',
    ]) {
      const action = dialog.getByRole('radio', { name });
      action.focus();
      await user.keyboard(' ');
      expect(action).toBeChecked();
    }
    expect(dialog.getByRole('button', { name: 'Auswahl verbindlich kopieren' })).toBeEnabled();
  });

  it('creates Happy Cleaning from the responsive header action', async () => {
    const mutate = vi.fn().mockResolvedValue({ ok: true });
    render(<HappyCleaningCreateButton mutate={mutate} />);

    const createButton = screen.getByRole('button', { name: 'Happy Cleaning hinzufügen' });
    expect(createButton).toHaveAttribute('data-slot', 'button');
    expect(createButton).toHaveClass('mobile-icon-action');
    expect(createButton.querySelector('.desktop-action-label')).toHaveTextContent('Happy Cleaning hinzufügen');
    expect(createButton.querySelector('.mobile-action-label')).toHaveAttribute('aria-hidden', 'true');
    fireEvent.click(createButton);

    await waitFor(() => expect(mutate).toHaveBeenCalledWith(
      '/api/happy-cleaning/events/create/',
      expect.objectContaining({ request_id: expect.any(String) }),
    ));
  });

  it('shows failed overview writes as error toasts, never inline', async () => {
    const mutate = vi.fn().mockRejectedValue(new Error('network down'));
    render(<HappyCleaningCreateButton mutate={mutate} />);

    fireEvent.click(screen.getByRole('button', { name: 'Happy Cleaning hinzufügen' }));

    await expectErrorToastOnly('network down');
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
    for (const table of screen.getAllByRole('table')) {
      expect(table).toHaveAttribute('data-slot', 'table');
      expect(table.parentElement).toHaveAttribute('data-slot', 'table-scroll');
    }
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
    expect(printButton).toHaveTextContent('Drucken');
    expect(printButton.querySelector('svg')).toHaveAttribute('aria-hidden', 'true');
    expect(printButton).not.toHaveTextContent('Nummernliste');

    fireEvent.click(printButton);
    expect(print).toHaveBeenCalledOnce();
  });
});
