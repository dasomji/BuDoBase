import { cleanup, fireEvent, render as testingLibraryRender, screen, waitFor, within } from '@testing-library/react';
import { renderToStaticMarkup } from 'react-dom/server';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { Toaster } from '../components/ui/toast';
import { routeDataRequest } from '../dataLoader';
import { parseRoute } from '../routes';
import { expectErrorToastOnly } from '../test-support';
import { HappyCleaningAssignmentPage } from './happyCleaningAssignment';

const render = ui => testingLibraryRender(ui, {
  wrapper: ({ children }) => <Toaster timeout={0}>{children}</Toaster>,
});

const assignmentData = {
  event: { id: 7, display_number: 2, revision: 5 },
  summary: { assigned_present: 1, present_total: 2 },
  number_batch: { available: false, children: [] },
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
      children: [{ id: 1, full_name: 'Ada Lovelace', short_name: 'Ada Lo', number: 7, present: true, assignment_version: 6 }],
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
      children: [{ id: 3, full_name: 'Linus Torvalds', short_name: 'Linus To', number: 3, present: false, assignment_version: 4 }],
    },
    {
      id: 'excused',
      name: 'Entschuldigt',
      is_excused: true,
      children: [],
    },
  ],
};

const setViewport = mobile => {
  Object.defineProperty(window, 'innerWidth', {
    configurable: true,
    value: mobile ? 375 : 1024,
  });
  window.matchMedia = vi.fn().mockReturnValue({
    matches: mobile,
    media: '(max-width: 900px)',
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

  it('shows the exact overbooked count instead of zero free seats', () => {
    setViewport(false);
    render(<HappyCleaningAssignmentPage
      data={{
        ...assignmentData,
        stations: assignmentData.stations.map(station => station.id === 10
          ? {
            ...station,
            assigned_count: 3,
            free_seats: 0,
            overbooked_count: 1,
          }
          : station),
      }}
      mutate={vi.fn()}
    />);

    expect(screen.getByText('1 überbelegt')).toBeInTheDocument();
    expect(screen.getByText('0 / 1 frei')).toBeInTheDocument();
  });

  it('shows the Carlos placeholder card before a child is selected', () => {
    setViewport(false);
    render(<HappyCleaningAssignmentPage data={assignmentData} mutate={vi.fn()} />);

    const placeholder = screen.getByRole('region', { name: 'Platzhalter Kind' });
    expect(within(placeholder).getByRole('heading', { name: 'Carlos' })).toBeInTheDocument();
    expect(within(placeholder).getByText('Nummer').nextElementSibling).toHaveTextContent('∞');
    expect(within(placeholder).getByText('Station').nextElementSibling).toHaveTextContent('überall und nirgends');
  });

  it('searches all Turnus children with an accessible desktop keyboard interaction', () => {
    setViewport(false);
    render(<HappyCleaningAssignmentPage data={assignmentData} mutate={vi.fn()} />);

    const search = screen.getByRole('combobox', { name: 'Kind suchen' });
    fireEvent.change(search, { target: { value: 'Ada' } });

    expect(search).toHaveAttribute('aria-expanded', 'true');
    expect(search).toHaveAttribute('aria-controls', 'happy-cleaning-child-results');
    const option = screen.getByRole('option', { name: /Ada Lovelace/ });
    expect(option).toHaveTextContent('#7');
    expect(option).toHaveTextContent('Speisesaal');
    expect(option).toHaveTextContent('Anwesend');
    expect(option).toHaveAttribute('aria-selected', 'false');

    fireEvent.keyDown(search, { key: 'ArrowDown' });
    expect(search).toHaveAttribute('aria-activedescendant', 'happy-cleaning-child-1');
    expect(option).toHaveAttribute('aria-selected', 'true');
    fireEvent.keyDown(search, { key: 'Enter' });

    expect(screen.queryByRole('listbox')).not.toBeInTheDocument();
    const heading = screen.getByRole('heading', { name: 'Ada Lovelace' });
    const controls = screen.getByRole('group', { name: 'Kind auswählen und bearbeiten' });
    const selectedSearch = screen.getByRole('combobox', { name: 'Kind suchen' });
    expect(controls).toContainElement(heading);
    expect(controls).toContainElement(selectedSearch);
    expect(controls.children).toHaveLength(2);
    expect(selectedSearch).toHaveValue('Ada Lovelace');
    expect(screen.queryByText('Auf Stationsnamen klicken, um Ada Lovelace einzuteilen.')).not.toBeInTheDocument();
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

    expect(screen.getByRole('heading', { name: 'Linus Torvalds ❌' })).toBeInTheDocument();
    expect(screen.queryByText('Anwesenheit')).not.toBeInTheDocument();
    expect(screen.queryByText('Abwesend · Sallingstadt')).not.toBeInTheDocument();
    expect(screen.getByText('Nummer').nextElementSibling).toHaveTextContent('3');
  });

  it('keeps the child panel and number form reachable after repeated mobile assignments', async () => {
    setViewport(true);
    const mutate = vi.fn().mockResolvedValue({ ok: true });
    render(<HappyCleaningAssignmentPage data={assignmentData} mutate={mutate} />);

    const selectGrace = () => {
      const search = screen.getByRole('combobox', { name: 'Kind suchen' });
      fireEvent.change(search, { target: { value: 'Grace' } });
      fireEvent.click(screen.getByRole('option', { name: 'Grace Hopper' }));
    };

    selectGrace();

    let panelToggle = screen.getByRole('button', { name: 'Grace Hopper schließen' });
    let numberInput = screen.getByRole('spinbutton', { name: 'Happy Cleaning Nummer für Grace Hopper' });
    expect(panelToggle).toHaveAttribute('aria-expanded', 'true');
    expect(panelToggle).toHaveTextContent('−');
    expect(numberInput.closest('.card-info-container')).not.toHaveAttribute('inert');

    fireEvent.click(screen.getByRole('button', { name: 'Grace Hopper Entschuldigt zuweisen' }));
    await waitFor(() => expect(mutate).toHaveBeenCalledWith(
      '/api/happy-cleaning/events/7/assignments/excuse/',
      expect.objectContaining({ child_id: 2 }),
    ));
    expect(screen.queryByRole('heading', { name: 'Grace Hopper' })).not.toBeInTheDocument();

    selectGrace();

    panelToggle = screen.getByRole('button', { name: 'Grace Hopper schließen' });
    numberInput = screen.getByRole('spinbutton', { name: 'Happy Cleaning Nummer für Grace Hopper' });
    expect(panelToggle).toHaveAttribute('aria-expanded', 'true');
    expect(panelToggle).toHaveTextContent('−');
    expect(numberInput.closest('.card-info-container')).not.toHaveAttribute('inert');
  });

  it('keeps a collapsed child panel collapsed when its number changes and expands a different child', () => {
    setViewport(true);
    const view = render(<HappyCleaningAssignmentPage data={assignmentData} mutate={vi.fn()} />);

    fireEvent.change(screen.getByRole('combobox', { name: 'Kind suchen' }), {
      target: { value: 'Ada' },
    });
    fireEvent.click(screen.getByRole('option', { name: 'Ada Lovelace' }));

    let panelToggle = screen.getByRole('button', { name: 'Ada Lovelace schließen' });
    fireEvent.click(panelToggle);
    expect(panelToggle).toHaveAttribute('aria-expanded', 'false');

    view.rerender(<HappyCleaningAssignmentPage
      data={{
        ...assignmentData,
        children: assignmentData.children.map(child => child.id === 1
          ? { ...child, number: 9, number_version: 3 }
          : child),
      }}
      mutate={vi.fn()}
    />);

    panelToggle = screen.getByRole('button', { name: 'Ada Lovelace öffnen' });
    expect(panelToggle).toHaveAttribute('aria-expanded', 'false');
    fireEvent.click(panelToggle);
    expect(screen.getByText('Nummer').nextElementSibling).toHaveTextContent('9');

    fireEvent.change(screen.getByRole('combobox', { name: 'Kind suchen' }), {
      target: { value: 'Grace' },
    });
    fireEvent.click(screen.getByRole('option', { name: 'Grace Hopper' }));
    expect(screen.getByRole('button', { name: 'Grace Hopper schließen' })).toHaveAttribute(
      'aria-expanded',
      'true',
    );
  });

  it('opens present unassigned children in a closable dialog and selects one', async () => {
    setViewport(false);
    render(<HappyCleaningAssignmentPage data={assignmentData} mutate={vi.fn()} />);

    const counterInfo = screen.getByText('Eingeteilt: 1/2');
    const counter = screen.getByRole('button', { name: 'Nicht eingeteilte Kinder anzeigen' });
    const actions = screen.getByRole('group', { name: 'Einteilungsaktionen' });
    expect(actions).toContainElement(counterInfo);
    expect(actions).toContainElement(counter);
    fireEvent.click(counter);

    let dialog = screen.getByRole('dialog');
    expect(within(dialog).getByRole('heading', { level: 2, name: 'Anwesende nicht eingeteilte Kinder' })).toBeInTheDocument();
    const list = within(dialog).getByRole('list', { name: 'Anwesende nicht eingeteilte Kinder' });
    expect(list).toHaveTextContent('Grace Hopper');
    expect(list).not.toHaveTextContent('Ada Lovelace');
    expect(list).not.toHaveTextContent('Linus Torvalds');
    const close = within(dialog).getByRole('button', { name: 'Dialog schließen' });
    expect(close.querySelector('.lucide-x')).toBeInTheDocument();
    fireEvent.click(close);
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());

    fireEvent.click(counter);
    dialog = screen.getByRole('dialog');
    fireEvent.click(within(dialog).getByRole('button', { name: 'Grace Hopper auswählen' }));
    expect(screen.getByRole('heading', { name: 'Grace Hopper' })).toBeInTheDocument();
    expect(screen.getByRole('combobox', { name: 'Kind suchen' })).toHaveValue('Grace Hopper');
  });

  // Phone-width layout is browser-verified under issue #128; jsdom guards only the mobile DOM contract.
  it('renders shared table primitives inside an internal scroll boundary and keeps mobile station details available', () => {
    setViewport(false);
    const desktop = render(<HappyCleaningAssignmentPage data={assignmentData} mutate={vi.fn()} />);

    const table = screen.getByRole('table', { name: 'Happy Cleaning Stationen' });
    expect(table.parentElement).toHaveAttribute('data-slot', 'table-scroll');
    expect(table).toHaveAttribute('data-slot', 'table');
    expect(within(table).getByRole('row', { name: /Station Wünsche/ })).toHaveAttribute('data-slot', 'table-row');
    expect(within(table).getByRole('columnheader', { name: 'Wünsche' })).toHaveAttribute('data-priority', 'low');
    expect(within(table).getByRole('rowheader', { name: 'Speisesaal' })).toBeInTheDocument();
    expect(within(table).getByText('Fenster')).toBeInTheDocument();
    expect(within(table).getByText('Vor dem Saal')).toBeInTheDocument();
    expect(within(table).getByText('Mira')).toBeInTheDocument();
    expect(within(table).getByText('1 / 2 frei')).toBeInTheDocument();
    expect(within(table).getByText('50%')).toBeInTheDocument();
    expect(within(table).getAllByText('—').length).toBeGreaterThan(0);
    const childButton = within(table).getByRole('button', { name: 'Ada Lovelace auswählen' });
    expect(childButton).toHaveTextContent('Ada Lo');
    expect(childButton).toHaveAttribute('title', 'Ada Lovelace #7');

    const hideChildren = within(table).getByRole('button', { name: 'Kindernamen verbergen' });
    expect(hideChildren.querySelector('.lucide-eye')).toBeInTheDocument();
    fireEvent.click(hideChildren);

    expect(within(table).getByRole('button', { name: 'Kindernamen anzeigen' }).querySelector('.lucide-eye-off')).toBeInTheDocument();
    const diningHallRow = within(table).getByRole('rowheader', { name: 'Speisesaal' }).closest('tr');
    expect(within(diningHallRow).getByLabelText('1 eingeteiltes Kind')).toBeVisible();
    expect(childButton).toBeInTheDocument();
    expect(childButton).not.toBeVisible();

    desktop.unmount();
    setViewport(true);
    render(<HappyCleaningAssignmentPage data={assignmentData} mutate={vi.fn()} />);

    const mobileTable = screen.getByRole('table', { name: 'Happy Cleaning Stationen' });
    expect(window.matchMedia).toHaveBeenCalledWith('(max-width: 900px)');
    expect(mobileTable.parentElement).toHaveAttribute('data-slot', 'table-scroll');
    expect(within(mobileTable).getByRole('columnheader', { name: 'SWP' })).toBeInTheDocument();
    expect(within(mobileTable).getByRole('columnheader', { name: 'Plätze' })).toBeInTheDocument();
    expect(within(mobileTable).getByRole('columnheader', { name: 'Details' })).toBeInTheDocument();
    expect(within(mobileTable).getByRole('columnheader', { name: 'Wünsche' })).toHaveAttribute('data-priority', 'low');
    expect(within(mobileTable).getByRole('columnheader', { name: 'Kinder' })).not.toHaveAttribute('data-priority');
    const mobileDiningHallRow = within(mobileTable).getByRole('rowheader', { name: 'Speisesaal' }).closest('tr');
    const childPills = within(mobileDiningHallRow).getByRole('group', { name: 'Eingeteilte Kinder' });
    const mobileChildButton = within(childPills).getByRole('button', { name: 'Ada Lovelace auswählen' });
    expect(childPills).toBeInTheDocument();
    expect(mobileChildButton).toBeInTheDocument();
    const detailsTrigger = within(mobileTable).getByRole('button', { name: 'Details zu Speisesaal anzeigen' });
    expect(detailsTrigger.querySelector('.lucide-eye')).toBeInTheDocument();
    fireEvent.click(detailsTrigger);

    const stationDialog = screen.getByRole('dialog');
    expect(within(stationDialog).getByRole('heading', { name: 'Speisesaal' })).toBeInTheDocument();
    expect(stationDialog).toHaveTextContent('Wünsche');
    expect(stationDialog).toHaveTextContent('Fenster');
    expect(stationDialog).toHaveTextContent('Treffpunkt');
    expect(stationDialog).toHaveTextContent('Vor dem Saal');
    expect(stationDialog).toHaveTextContent('Mira');
    expect(stationDialog).toHaveTextContent('1 / 2 frei');
    expect(stationDialog).toHaveTextContent('50%');
    expect(within(stationDialog).getByRole('button', { name: 'Ada Lovelace auswählen' })).toBeInTheDocument();
  });

  it('renders the mobile station column set in the first frame', () => {
    setViewport(true);

    const markup = renderToStaticMarkup(
      <Toaster timeout={0}>
        <HappyCleaningAssignmentPage data={assignmentData} mutate={vi.fn()} />
      </Toaster>,
    );
    const template = document.createElement('template');
    template.innerHTML = markup;
    const table = template.content.querySelector('table[aria-label="Happy Cleaning Stationen"]');
    const headings = Array.from(table.querySelectorAll('thead th'), heading => heading.textContent);

    expect(headings).toEqual([
      'SWP',
      'Wünsche',
      'Treffpunkt',
      'Verantwortlich',
      'Plätze',
      'Aufgaben',
      'Kinder',
      'Details',
    ]);
    expect(table.querySelector('tbody tr').children).toHaveLength(8);
  });

  it('assigns a numberless child to the built-in Entschuldigt target', async () => {
    setViewport(false);
    const mutate = vi.fn().mockResolvedValue({ ok: true });
    render(<HappyCleaningAssignmentPage data={assignmentData} mutate={mutate} />);

    const table = screen.getByRole('table', { name: 'Happy Cleaning Stationen' });
    const excusedRow = within(table).getByRole('rowheader', { name: 'Entschuldigt' }).closest('tr');
    expect(excusedRow).not.toHaveTextContent(/Wünsche|Treffpunkt|Verantwortlich|Plätze|Aufgaben/);
    expect(within(excusedRow).queryByRole('link', { name: 'Entschuldigt' })).not.toBeInTheDocument();
    expect(within(excusedRow).queryByRole('button', { name: /Details/ })).not.toBeInTheDocument();

    fireEvent.change(screen.getByRole('combobox', { name: 'Kind suchen' }), { target: { value: 'Grace' } });
    fireEvent.click(screen.getByRole('option', { name: /Grace Hopper/ }));

    expect(screen.getByRole('button', { name: 'Grace Hopper Speisesaal zuweisen' })).toBeDisabled();
    const excuse = screen.getByRole('button', { name: 'Grace Hopper Entschuldigt zuweisen' });
    expect(excuse).toBeEnabled();
    fireEvent.click(excuse);

    await waitFor(() => expect(mutate).toHaveBeenCalledWith(
      '/api/happy-cleaning/events/7/assignments/excuse/',
      expect.objectContaining({ child_id: 2 }),
    ));
    expect(await screen.findByRole('dialog')).toHaveTextContent('Grace Hopper wurde als Entschuldigt eingeteilt.');
  });

  it('moves children between a station and Entschuldigt through the target-specific commands', async () => {
    setViewport(false);
    const confirm = vi.spyOn(window, 'confirm').mockReturnValue(true);
    const moveToExcused = vi.fn().mockResolvedValue({ ok: true });
    const normalAssignment = render(
      <HappyCleaningAssignmentPage data={assignmentData} mutate={moveToExcused} />,
    );

    fireEvent.change(screen.getByRole('combobox', { name: 'Kind suchen' }), { target: { value: 'Ada' } });
    fireEvent.click(screen.getByRole('option', { name: /Ada Lovelace/ }));
    fireEvent.click(screen.getByRole('button', { name: 'Ada Lovelace Entschuldigt zuweisen' }));

    expect(confirm).toHaveBeenCalledWith(
      'Ada Lovelace von Speisesaal nach Entschuldigt verschieben?',
    );
    await waitFor(() => expect(moveToExcused).toHaveBeenCalledWith(
      '/api/happy-cleaning/events/7/assignments/1/excuse/',
      expect.objectContaining({ expected_version: 6 }),
    ));
    normalAssignment.unmount();

    const excusedData = {
      ...assignmentData,
      children: assignmentData.children.map(child => child.id === 2
        ? {
          ...child,
          number: 8,
          assigned_station: { id: 'excused', name: 'Entschuldigt', is_excused: true },
          assignment_version: 9,
        }
        : child),
      stations: assignmentData.stations.map(station => station.is_excused
        ? {
          ...station,
          children: [{
            id: 2,
            full_name: 'Grace Hopper',
            short_name: 'Grace Ho',
            number: 8,
            present: true,
            assignment_version: 9,
          }],
        }
        : station),
    };
    const moveToStation = vi.fn().mockResolvedValue({ ok: true });
    render(<HappyCleaningAssignmentPage data={excusedData} mutate={moveToStation} />);

    fireEvent.change(screen.getByRole('combobox', { name: 'Kind suchen' }), { target: { value: 'Grace' } });
    fireEvent.click(screen.getByRole('option', { name: /Grace Hopper/ }));
    expect(screen.getByRole('button', { name: 'Grace Hopper Entschuldigt zuweisen' })).toBeDisabled();
    fireEvent.click(screen.getByRole('button', { name: 'Grace Hopper Speisesaal zuweisen' }));

    expect(confirm).toHaveBeenLastCalledWith(
      'Grace Hopper von Entschuldigt nach Speisesaal verschieben?',
    );
    await waitFor(() => expect(moveToStation).toHaveBeenCalledWith(
      '/api/happy-cleaning/events/7/assignments/2/move/',
      expect.objectContaining({ station_id: 10, expected_version: 9 }),
    ));
  });

  it('shows fixed missing-number suggestions beside the completed counter and confirms them as one batch', async () => {
    setViewport(false);
    const data = {
      ...assignmentData,
      summary: { assigned_present: 2, present_total: 2 },
      number_batch: {
        available: true,
        children: [
          { id: 2, full_name: 'Grace Hopper', number: 2, expected_version: 1 },
          { id: 4, full_name: 'Katherine Johnson', number: 4, expected_version: 3 },
        ],
      },
    };
    const mutate = vi.fn().mockResolvedValue({ ok: true });
    render(<HappyCleaningAssignmentPage data={data} mutate={mutate} />);

    const batch = screen.getByRole('button', { name: 'Kindern ohne Nummern, Nummern zuteilen' });
    expect(screen.getByRole('group', { name: 'Einteilungsaktionen' })).toContainElement(
      screen.getByRole('button', { name: 'Nicht eingeteilte Kinder anzeigen' }),
    );
    fireEvent.click(batch);

    let dialog = screen.getByRole('dialog');
    expect(within(dialog).getByRole('heading', { name: 'Nummern zuteilen' })).toBeInTheDocument();
    expect(within(dialog).getByRole('list', { name: 'Vorgeschlagene Nummern' })).toHaveTextContent('Grace Hopper2');
    expect(within(dialog).getByRole('list', { name: 'Vorgeschlagene Nummern' })).toHaveTextContent('Katherine Johnson4');
    expect(within(dialog).queryByRole('spinbutton')).not.toBeInTheDocument();
    const actions = within(dialog).getByRole('group', { name: 'Dialogaktionen' });
    fireEvent.click(within(actions).getByRole('button', { name: 'Abbrechen' }));
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());

    fireEvent.click(batch);
    dialog = screen.getByRole('dialog');
    fireEvent.click(within(dialog).getByRole('button', { name: 'Bestätigen' }));
    await waitFor(() => expect(mutate).toHaveBeenCalledWith(
      '/api/happy-cleaning/events/7/numbers/assign-missing/',
      {
        request_id: expect.any(String),
        assignments: [
          { child_id: 2, number: 2, expected_version: 1 },
          { child_id: 4, number: 4, expected_version: 3 },
        ],
      },
    ));
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('refreshes stale batch state when another writer assigned every number', async () => {
    setViewport(false);
    const data = {
      ...assignmentData,
      number_batch: {
        available: true,
        children: [
          { id: 2, full_name: 'Grace Hopper', number: 2, expected_version: 1 },
        ],
      },
    };
    const error = new Error('nothing left to assign');
    error.payload = { code: 'nothing_to_assign' };
    const mutate = vi.fn().mockRejectedValue(error);
    const refresh = vi.fn().mockResolvedValue(undefined);
    render(
      <HappyCleaningAssignmentPage
        data={data}
        mutate={mutate}
        refresh={refresh}
      />,
    );

    fireEvent.click(screen.getByRole('button', { name: 'Kindern ohne Nummern, Nummern zuteilen' }));
    fireEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Bestätigen' }));

    await waitFor(() => expect(refresh).toHaveBeenCalledWith({ preserveData: true }));
    await expectErrorToastOnly(
      'Es sind keine Nummern mehr zuzuteilen. Die Daten wurden neu geladen.',
    );
  });

  it('gates station assignment on a versioned number entry', async () => {
    setViewport(false);
    const mutate = vi.fn().mockResolvedValue({ ok: true });
    render(<HappyCleaningAssignmentPage data={assignmentData} mutate={mutate} />);

    const search = screen.getByRole('combobox', { name: 'Kind suchen' });
    fireEvent.change(search, { target: { value: 'Grace' } });
    fireEvent.click(screen.getByRole('option', { name: /Grace Hopper/ }));

    const details = screen.getByRole('region', { name: 'Ausgewähltes Kind' });
    const numberDetails = within(details).getByText('Nummer').nextElementSibling;
    const stationDetails = within(details).getByText('Station').nextElementSibling;
    const numberInput = screen.getByRole('spinbutton', { name: 'Happy Cleaning Nummer für Grace Hopper' });
    expect(numberDetails).toContainElement(numberInput);
    expect(stationDetails).toHaveTextContent('Kann erst eingeteilt werden, wenn eine Nummer eingetragen wurde');
    expect(screen.queryByText('Noch keine Nummer')).not.toBeInTheDocument();
    expect(screen.queryByText('Happy Cleaning Nummer für Grace Hopper')).not.toBeInTheDocument();
    expect(screen.queryByText(/Auf Stationsnamen klicken, um Grace Hopper/)).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Grace Hopper Speisesaal zuweisen' })).toBeDisabled();
    fireEvent.change(numberInput, { target: { value: '8' } });
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
    const mutate = vi.fn()
      .mockRejectedValueOnce(duplicate)
      .mockRejectedValueOnce(duplicate)
      .mockResolvedValueOnce({ ok: true });
    render(<HappyCleaningAssignmentPage data={assignmentData} mutate={mutate} />);

    const search = screen.getByRole('combobox', { name: 'Kind suchen' });
    fireEvent.change(search, { target: { value: 'Ada' } });
    fireEvent.keyDown(search, { key: 'ArrowDown' });
    fireEvent.keyDown(search, { key: 'Enter' });
    const details = screen.getByRole('region', { name: 'Ausgewähltes Kind' });
    const numberDetails = within(details).getByText('Nummer').nextElementSibling;
    expect(numberDetails).toHaveTextContent('7');
    expect(within(numberDetails).queryByRole('spinbutton')).not.toBeInTheDocument();
    fireEvent.click(within(numberDetails).getByRole('button', { name: 'Nummer für Ada Lovelace bearbeiten' }));
    let number = screen.getByRole('spinbutton', { name: 'Happy Cleaning Nummer für Ada Lovelace' });
    expect(numberDetails).toContainElement(number);
    expect(number).toHaveValue(7);
    expect(screen.getByRole('button', { name: 'Nummer aktualisieren' })).toBeInTheDocument();
    fireEvent.change(number, { target: { value: '8' } });
    fireEvent.click(screen.getByRole('button', { name: 'Abbrechen' }));
    expect(screen.queryByRole('spinbutton', { name: 'Happy Cleaning Nummer für Ada Lovelace' })).not.toBeInTheDocument();

    fireEvent.click(within(numberDetails).getByRole('button', { name: 'Nummer für Ada Lovelace bearbeiten' }));
    number = screen.getByRole('spinbutton', { name: 'Happy Cleaning Nummer für Ada Lovelace' });
    expect(number).toHaveValue(7);
    fireEvent.change(number, { target: { value: '8' } });
    fireEvent.click(screen.getByRole('button', { name: 'Nummer aktualisieren' }));

    const dialog = await screen.findByRole('dialog');
    expect(within(dialog).getByRole('heading', { level: 2, name: 'Nummer 8 ist bereits vergeben.' })).toBeInTheDocument();
    expect(within(dialog).getByText('Klicke auf eine freie Zahl zum zuweisen')).toBeInTheDocument();
    const neighborhood = within(dialog).getByRole('list', { name: 'Freie Nummer auswählen' });
    expect(within(neighborhood).getAllByRole('listitem')).toHaveLength(7);
    expect(within(neighborhood).getAllByRole('button', { name: /als Nummer zuweisen/ })).toHaveLength(5);
    expect(within(neighborhood).queryByRole('button', { name: '8 als Nummer zuweisen' })).not.toBeInTheDocument();
    expect(neighborhood).toHaveTextContent('8Alan Turing');
    const close = within(dialog).getByRole('button', { name: 'Dialog schließen' });
    expect(close.querySelector('.lucide-x')).toBeInTheDocument();
    fireEvent.click(close);
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());

    fireEvent.click(screen.getByRole('button', { name: 'Nummer aktualisieren' }));
    const reopenedDialog = await screen.findByRole('dialog');
    fireEvent.click(within(reopenedDialog).getByRole('button', { name: '5 als Nummer zuweisen' }));
    await waitFor(() => expect(mutate).toHaveBeenLastCalledWith(
      '/api/happy-cleaning/children/1/number/',
      expect.objectContaining({ number: 5, expected_version: 2 }),
    ));
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
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
    expect(await screen.findByRole('dialog')).toHaveTextContent('Grace Hopper wurde Speisesaal zugeteilt.');
    expect(screen.getByRole('region', { name: 'Benachrichtigungen' })).toHaveClass('app-toast-viewport');
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
    expect(screen.getByRole('dialog')).toHaveTextContent('Ada Lovelace wurde nach Bad verschoben.');
  });

  it('marks full stations before a child is selected without legacy detail links', () => {
    setViewport(false);
    render(<HappyCleaningAssignmentPage data={assignmentData} mutate={vi.fn()} />);

    expect(screen.getByRole('rowheader', { name: 'Bad 🚫' })).toBeInTheDocument();
    expect(screen.getByRole('rowheader', { name: 'Speisesaal' })).toBeInTheDocument();
    expect(screen.queryByRole('link')).not.toBeInTheDocument();
  });

  it('selects a child pill for the normal child-detail flow without removing it', () => {
    setViewport(false);
    const mutate = vi.fn();
    const confirm = vi.spyOn(window, 'confirm');
    render(<HappyCleaningAssignmentPage data={assignmentData} mutate={mutate} />);

    fireEvent.click(screen.getByRole('button', { name: 'Ada Lovelace auswählen' }));

    expect(screen.getByRole('heading', { name: 'Ada Lovelace' })).toBeInTheDocument();
    expect(screen.getByRole('combobox', { name: 'Kind suchen' })).toHaveValue('Ada Lovelace');
    expect(within(screen.getByRole('region', { name: 'Ausgewähltes Kind' })).getByText('Station').nextElementSibling).toHaveTextContent('Speisesaal');
    expect(confirm).not.toHaveBeenCalled();
    expect(mutate).not.toHaveBeenCalled();
  });

  it('shows failed assignment writes as error toasts, never inline', async () => {
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

    await expectErrorToastOnly(
      'Speisesaal ist inzwischen voll. Die Einteilung wurde aktualisiert.',
    );
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
    fireEvent.click(screen.getByRole('button', { name: 'Nummer für Ada Lovelace bearbeiten' }));

    expect(screen.getByRole('spinbutton', { name: 'Happy Cleaning Nummer für Ada Lovelace' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Nummer aktualisieren' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Abbrechen' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Ada Lovelace auswählen' })).toBeEnabled();
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

    const details = screen.getByLabelText('Ausgewähltes Kind');
    expect(within(details).getByText('Nummer').nextElementSibling).toHaveTextContent('9');
    fireEvent.click(screen.getByRole('button', { name: 'Nummer für Ada Lovelace bearbeiten' }));
    expect(screen.getByRole('spinbutton', { name: 'Happy Cleaning Nummer für Ada Lovelace' })).toHaveValue(9);
    expect(within(details).getByText('Station').nextElementSibling).toHaveTextContent('Bad');
    expect(screen.getByRole('table', { name: 'Happy Cleaning Stationen' })).toHaveTextContent('100%');
  });
});
