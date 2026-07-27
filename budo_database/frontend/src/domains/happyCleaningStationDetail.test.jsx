import { cleanup, fireEvent, render as testingLibraryRender, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Editor } from '@tiptap/core';
import Document from '@tiptap/extension-document';
import Paragraph from '@tiptap/extension-paragraph';
import Text from '@tiptap/extension-text';
import TaskList from '@tiptap/extension-task-list';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { Toaster } from '../components/ui/toast';
import { routeDataRequest } from '../dataLoader';
import { parseRoute } from '../routes';
import {
  HappyCleaningStationDetailPage,
  StableTaskItem,
} from './happyCleaningStationDetail';


const render = ui => testingLibraryRender(ui, {
  wrapper: ({ children }) => <Toaster timeout={0}>{children}</Toaster>,
});

const detailData = {
  event: { id: 7, display_number: 2, revision: 5 },
  copy_targets: [
    { id: 8, display_number: 1, revision: 3, label: 'Happy Cleaning 1' },
  ],
  station: {
    id: 10,
    version: 3,
    name: 'Speisesaal',
    max_kids: 4,
    meeting_point: 'Vor dem Saal',
    wishes: 'Fenster nicht vergessen',
    content: [{ type: 'paragraph', text: 'Dieser Projektionsinhalt darf nicht erscheinen' }],
    document: {
      type: 'doc',
      content: [
        {
          type: 'paragraph',
          content: [{ type: 'text', text: 'Fenster öffnen' }],
        },
        {
          type: 'taskList',
          content: [{
            type: 'taskItem',
            attrs: { id: 100, checked: true, version: 2 },
            content: [{
              type: 'paragraph',
              content: [{ type: 'text', text: 'Tische wischen' }],
            }],
          }],
        },
        {
          type: 'paragraph',
          content: [{ type: 'text', text: 'Danach kontrollieren' }],
        },
        {
          type: 'taskList',
          content: [{
            type: 'taskItem',
            attrs: { id: 101, checked: false, version: 1 },
            content: [{
              type: 'paragraph',
              content: [{ type: 'text', text: 'Boden kehren' }],
            }],
          }],
        },
      ],
    },
    is_historical: false,
    can_toggle_tasks: true,
    responsible: { id: 4, name: 'Mira' },
    todo_checked_count: 1,
    todo_total_count: 2,
    todo_progress_percentage: 50,
    children: [
      { id: 1, full_name: 'Ada Lovelace', assignment_version: 6 },
      { id: 2, full_name: 'Grace Hopper', assignment_version: 4 },
    ],
    // Deliberately stale: read-mode behavior must come from the canonical document above.
    todos: [
      { id: 100, version: 200, text: 'Tische wischen', position: 1, checked: false },
      { id: 101, version: 100, text: 'Boden kehren', position: 2, checked: true },
    ],
  },
};


describe('Happy Cleaning station detail', () => {
  afterEach(cleanup);

  it('shows the complete canonical document in its original paragraph and task order', () => {
    const onBack = vi.fn();
    render(<HappyCleaningStationDetailPage data={detailData} mutate={vi.fn()} onBack={onBack} />);

    const stationHeading = screen.getByRole('heading', { level: 2, name: 'Speisesaal' });
    const stationCard = stationHeading.closest('.card');
    const stationToggle = stationHeading.closest('.card-toggle');
    expect(stationCard).toHaveClass('card');
    expect(stationToggle).toHaveAttribute('aria-expanded', 'true');
    expect(stationToggle.querySelector('.icon')).not.toBeInTheDocument();
    const close = screen.getByRole('button', { name: 'Detail schließen' });
    expect(close).toHaveAttribute('data-slot', 'button');
    fireEvent.click(close);
    expect(onBack).toHaveBeenCalledOnce();
    expect(stationToggle).toHaveAttribute('aria-expanded', 'true');
    fireEvent.click(stationHeading);
    expect(stationToggle).toHaveAttribute('aria-expanded', 'false');
    expect(stationCard.querySelector('.card-info-container')).toHaveAttribute('inert');
    fireEvent.click(stationToggle);

    expect(screen.getByText('Vor dem Saal')).toBeInTheDocument();
    expect(screen.getByText('4')).toBeInTheDocument();
    expect(screen.getByText('Fenster nicht vergessen')).toBeInTheDocument();
    expect(screen.getByText('Mira')).toBeInTheDocument();
    const facts = screen.getByText('Hauptverantwortlich').closest('dl');
    expect([...facts.querySelectorAll('dt')].map(term => term.textContent)).toEqual([
      'Hauptverantwortlich', 'Max Kinder', 'Treffpunkt', 'Wünsche',
    ]);
    expect(within(facts).queryByText('Plätze')).not.toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: 'Eingeteilte Kinder' })).not.toBeInTheDocument();
    expect(screen.queryByText('Ada Lovelace')).not.toBeInTheDocument();
    expect(screen.queryByText('Grace Hopper')).not.toBeInTheDocument();
    expect(screen.queryByLabelText('Todo-Fortschritt')).not.toBeInTheDocument();
    expect(stationCard.querySelector('.card-header-action')).toContainElement(close);

    const document = screen.getByLabelText('Stationsinhalt');
    expect(document).toHaveAttribute('contenteditable', 'false');
    expect([...document.querySelectorAll('p')].map(paragraph => paragraph.textContent)).toEqual([
      'Fenster öffnen',
      'Tische wischen',
      'Danach kontrollieren',
      'Boden kehren',
    ]);
    expect(screen.queryByText('Dieser Projektionsinhalt darf nicht erscheinen')).not.toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: 'Inhalt' })).not.toBeInTheDocument();
    const tasksHeading = screen.getByRole('heading', { level: 2, name: 'Aufgaben' });
    expect(tasksHeading.nextElementSibling).toContainElement(document);
    expect(screen.queryByRole('button', { name: /löschen|bearbeiten|nach oben|nach unten/i })).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/Name der Station|Treffpunkt der Station/)).not.toBeInTheDocument();
  });

  it('gives the Aufgaben heading its annotated vertical padding', () => {
    render(<HappyCleaningStationDetailPage data={detailData} mutate={vi.fn()} />);

    expect(screen.getByRole('heading', { level: 2, name: 'Aufgaben' })).toHaveStyle({
      paddingTop: '12px',
      paddingBottom: '8px',
    });
  });

  it('places edit and copy actions together at the end of the card body', () => {
    render(<HappyCleaningStationDetailPage data={{
      ...detailData,
      station: { ...detailData.station, can_edit: true },
    }} mutate={vi.fn()} />);

    const stationCard = screen.getByRole('heading', { level: 2, name: 'Speisesaal' })
      .closest('.card');
    const cardBody = stationCard.querySelector('.card-info-content');
    const actions = cardBody.lastElementChild;
    const actionButtons = within(actions).getAllByRole('button');
    expect(actionButtons.map(button => button.textContent)).toEqual([
      'Bearbeiten', 'Station kopieren',
    ]);
    actionButtons.forEach(button => expect(button).toHaveAttribute('data-slot', 'button'));
    expect(actions.previousElementSibling).toContainElement(
      screen.getByRole('heading', { level: 2, name: 'Aufgaben' }),
    );
  });

  it('always displays completed tasks and sends versioned check/reopen commands', async () => {
    const mutate = vi.fn().mockResolvedValue({ ok: true });
    render(<HappyCleaningStationDetailPage data={detailData} mutate={mutate} />);

    const completed = screen.getByRole('checkbox', { name: 'Tische wischen wieder öffnen' });
    const open = screen.getByRole('checkbox', { name: 'Boden kehren erledigen' });
    expect(completed).toBeChecked();
    expect(open).not.toBeChecked();
    fireEvent.click(open);

    await waitFor(() => expect(mutate).toHaveBeenCalledWith(
      '/api/happy-cleaning/events/7/stations/10/todos/101/check/',
      expect.objectContaining({ expected_version: 1, request_id: expect.any(String) }),
    ));
    expect(open).not.toBeChecked();

    fireEvent.click(completed);
    await waitFor(() => expect(mutate).toHaveBeenCalledWith(
      '/api/happy-cleaning/events/7/stations/10/todos/100/reopen/',
      expect.objectContaining({ expected_version: 2, request_id: expect.any(String) }),
    ));
    expect(completed).toBeChecked();
  });

  it('refreshes a stale task conflict so the same item can be retried', async () => {
    const stale = new Error('Update failed');
    stale.payload = { code: 'stale', current_version: 2 };
    const mutate = vi.fn().mockRejectedValue(stale);
    const refresh = vi.fn().mockResolvedValue();
    render(
      <HappyCleaningStationDetailPage
        data={detailData}
        mutate={mutate}
        refresh={refresh}
      />,
    );

    const completed = screen.getByRole('checkbox', { name: 'Boden kehren erledigen' });
    const stationCard = completed.closest('.card');
    fireEvent.click(completed);

    const toast = await screen.findByText(/erneut versuchen/, { selector: '.app-toast-description' });
    expect(toast.closest('.app-toast')).toHaveAttribute('data-type', 'error');
    expect(stationCard.querySelector('.error')).not.toBeInTheDocument();
    await waitFor(() => expect(refresh).toHaveBeenCalledTimes(1));
    expect(screen.getByRole('checkbox', { name: 'Boden kehren erledigen' })).toBeEnabled();
  });

  it('allows independent task items to be changed concurrently', async () => {
    let finishFirst;
    const mutate = vi.fn()
      .mockImplementationOnce(() => new Promise(resolve => { finishFirst = resolve; }))
      .mockResolvedValueOnce({ ok: true });
    render(<HappyCleaningStationDetailPage data={detailData} mutate={mutate} />);

    fireEvent.click(screen.getByRole('checkbox', { name: 'Boden kehren erledigen' }));
    expect(screen.getByRole('checkbox', { name: 'Boden kehren erledigen' })).toBeDisabled();
    expect(screen.getByRole('checkbox', { name: 'Tische wischen wieder öffnen' })).toBeEnabled();
    fireEvent.click(screen.getByRole('checkbox', { name: 'Tische wischen wieder öffnen' }));

    await waitFor(() => expect(mutate).toHaveBeenCalledTimes(2));
    finishFirst({ ok: true });
  });

  it('keeps historical details read-only and does not render redacted people', () => {
    const historical = {
      event: detailData.event,
      station: {
        ...detailData.station,
        is_historical: true,
        can_toggle_tasks: false,
      },
    };
    delete historical.station.responsible;
    delete historical.station.children;
    render(<HappyCleaningStationDetailPage data={historical} mutate={vi.fn()} />);

    expect(screen.getByText('Tische wischen')).toBeInTheDocument();
    expect(screen.getByRole('checkbox', { name: 'Tische wischen wieder öffnen' })).toBeDisabled();
    expect(screen.getByRole('checkbox', { name: 'Boden kehren erledigen' })).toBeDisabled();
    expect(screen.queryByRole('button', { name: /erledigen|wieder öffnen/i })).not.toBeInTheDocument();
    expect(screen.queryByText('Eingeteilte Kinder')).not.toBeInTheDocument();
    expect(screen.queryByText('Mira')).not.toBeInTheDocument();
    expect(screen.queryByText('Ada Lovelace')).not.toBeInTheDocument();
    expect(screen.queryByRole('textbox')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Bearbeiten' })).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Station kopieren' })).toBeInTheDocument();
  });

  it('reuses the fixed-source copy wizard without mutating or closing detail state', async () => {
    const user = userEvent.setup();
    let finish;
    const mutate = vi.fn(() => new Promise(resolve => { finish = resolve; }));
    const onBack = vi.fn();
    const onCopySuccess = vi.fn();
    render(
      <HappyCleaningStationDetailPage
        data={detailData}
        mutate={mutate}
        onBack={onBack}
        onCopySuccess={onCopySuccess}
      />,
    );

    screen.getByRole('button', { name: 'Station kopieren' }).focus();
    await user.keyboard('{Enter}');
    const dialog = screen.getByRole('dialog', { name: 'Station kopieren' });
    expect(dialog).toHaveTextContent('Quelle: Speisesaal');
    expect(screen.queryByLabelText('Alle Stationen auswählen')).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/Station .* auswählen/)).not.toBeInTheDocument();
    await user.selectOptions(screen.getByLabelText('Ziel-Happy-Cleaning'), '8');
    const copyButton = screen.getByRole('button', { name: 'Prüfen und kopieren' });
    expect(copyButton).toHaveAttribute('data-slot', 'button');
    copyButton.focus();
    await user.keyboard('{Enter}');

    expect(screen.getByRole('status')).toHaveTextContent('Stationen werden geprüft');
    expect(mutate).toHaveBeenCalledWith(
      '/api/happy-cleaning/events/8/stations/copy/10/',
      {
        request_id: expect.any(String),
        expected_revision: 3,
      },
    );
    finish({
      ok: true,
      result: 'copied',
      affected_stations: [{ id: 90, name: 'Speisesaal' }],
    });
    await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent('Station wurde kopiert'));
    expect(onCopySuccess).toHaveBeenCalledWith(8, expect.objectContaining({
      affected_stations: [{ id: 90, name: 'Speisesaal' }],
    }));
    expect(screen.getByRole('heading', { name: 'Speisesaal', hidden: true })).toBeInTheDocument();
    expect(onBack).not.toHaveBeenCalled();

    const closeButton = screen.getByRole('button', { name: 'Schließen' });
    expect(closeButton).toHaveAttribute('data-slot', 'button');
    closeButton.focus();
    await user.keyboard('{Enter}');
    expect(screen.queryByRole('dialog', { name: 'Station kopieren' })).not.toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Speisesaal', hidden: true })).toBeInTheDocument();
    expect(onBack).not.toHaveBeenCalled();
  });

  it('shares bulk validation, conflict actions, and stale errors', async () => {
    const stale = Object.assign(new Error('stale'), {
      payload: { code: 'stale', current_version: 4 },
    });
    const mutate = vi.fn()
      .mockResolvedValueOnce({
        ok: true,
        result: 'conflicts',
        target_revision: 4,
        conflicts: [{
          source_station_id: 10,
          source_name: 'Speisesaal',
          source_task_count: 2,
          target_station_id: 90,
          target_name: 'Speisesaal groß',
          target_task_count: 1,
          overwrite_eligible: true,
        }],
      })
      .mockRejectedValueOnce(stale);
    render(<HappyCleaningStationDetailPage data={detailData} mutate={mutate} />);

    fireEvent.click(screen.getByRole('button', { name: 'Station kopieren' }));
    const submit = screen.getByRole('button', { name: 'Prüfen und kopieren' });
    expect(submit).toBeDisabled();
    fireEvent.change(screen.getByLabelText('Ziel-Happy-Cleaning'), {
      target: { value: '8' },
    });
    expect(submit).toBeEnabled();
    fireEvent.click(submit);

    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent('Speisesaal → Speisesaal groß');
    expect(within(alert).getByRole('group', { name: 'Speisesaal (2 Aufgaben)' })).toBeInTheDocument();
    expect(screen.getAllByRole('radio')).toHaveLength(4);
    fireEvent.click(screen.getByRole('radio', { name: 'Als eigene Station kopieren' }));
    expect(screen.getByRole('button', { name: 'Auswahl verbindlich kopieren' })).toBeEnabled();

    fireEvent.click(screen.getByRole('button', { name: 'Erneut prüfen' }));
    const toast = await screen.findByText(/inzwischen geändert/, { selector: '.app-toast-description' });
    expect(toast.closest('.app-toast')).toHaveAttribute('data-type', 'error');
    expect(screen.getByRole('heading', { name: 'Speisesaal', hidden: true })).toBeInTheDocument();
  });

  it('edits an active station through the restricted document command', async () => {
    const mutate = vi.fn().mockResolvedValue({ ok: true });
    const refresh = vi.fn().mockResolvedValue();
    render(<HappyCleaningStationDetailPage data={{
      ...detailData,
      responsible_profiles: [{ id: 4, name: 'Mira' }],
      station: {
        ...detailData.station,
        can_edit: true,
        can_delete: true,
        document: {
          type: 'doc',
          content: [{
            type: 'taskList',
            content: [{
              type: 'taskItem',
              attrs: { id: 100, checked: true, version: 2 },
              content: [{ type: 'paragraph', content: [{ type: 'text', text: 'Tische wischen' }] }],
            }],
          }],
        },
      },
    }} mutate={mutate} refresh={refresh} onBack={vi.fn()} />);

    const stationCard = screen.getByRole('heading', { level: 2, name: 'Speisesaal' })
      .closest('.card');
    const stationToggle = stationCard.querySelector('.card-toggle');
    fireEvent.click(screen.getByRole('button', { name: 'Bearbeiten' }));
    expect(screen.queryByRole('toolbar')).not.toBeInTheDocument();
    const nameField = screen.getByLabelText('Name der Station');
    const responsibleField = screen.getByLabelText('Verantwortlich');
    expect(screen.getByLabelText('Kapazität der Station')).toHaveAttribute('min', '0');
    expect(stationCard).toContainElement(nameField);
    const form = nameField.closest('form');
    expect(form.children[0]).toContainElement(nameField);
    expect(form.children[1]).toContainElement(responsibleField);
    expect(screen.queryByLabelText('Hauptverantwortlich')).not.toBeInTheDocument();
    const tasksGroup = screen.getByRole('group', { name: 'Aufgaben' });
    expect(within(tasksGroup).getByLabelText('Aufgaben')).toHaveAttribute('contenteditable', 'true');
    expect(stationCard.querySelector('.card-toggle')).toBe(stationToggle);
    const taskStatus = await screen.findByRole('checkbox', {
      name: 'Aufgabenstatus wird beim Bearbeiten nicht geändert',
    });
    expect(taskStatus).toBeDisabled();
    expect(taskStatus).toHaveAttribute('tabindex', '-1');
    fireEvent.change(screen.getByLabelText('Name der Station'), { target: { value: 'Saal' } });
    fireEvent.click(screen.getByRole('button', { name: 'Speichern' }));

    await waitFor(() => expect(mutate).toHaveBeenCalledWith(
      '/api/happy-cleaning/events/7/stations/10/update/',
      expect.objectContaining({
        expected_version: 3,
        name: 'Saal',
        document: expect.objectContaining({ type: 'doc' }),
      }),
    ));
    expect(refresh).toHaveBeenCalled();
  });

  it('clears persisted task identity when Enter splits a task item', () => {
    const editor = new Editor({
      extensions: [Document, Paragraph, Text, TaskList, StableTaskItem.configure({ nested: false })],
      content: {
        type: 'doc',
        content: [{
          type: 'taskList',
          content: [{
            type: 'taskItem',
            attrs: { id: 100, checked: false, version: 2 },
            content: [{
              type: 'paragraph',
              content: [{ type: 'text', text: 'Tische wischen' }],
            }],
          }],
        }],
      },
    });

    editor.commands.setTextSelection('end');
    expect(editor.commands.splitListItem('taskItem')).toBe(true);
    const tasks = editor.getJSON().content[0].content;
    expect(tasks.map(task => task.attrs)).toEqual([
      { checked: false, id: 100, version: 2 },
      { checked: false, id: null, version: null },
    ]);
    editor.destroy();
  });

  it('confirms exact overbooking before saving a lower capacity', async () => {
    vi.spyOn(globalThis, 'confirm').mockReturnValue(true);
    const mutate = vi.fn().mockResolvedValue({ ok: true });
    render(<HappyCleaningStationDetailPage data={{
      ...detailData,
      station: {
        ...detailData.station,
        assigned_count: 4,
        overbooked_count: 0,
        can_edit: true,
        document: { type: 'doc', content: [] },
      },
    }} mutate={mutate} />);

    fireEvent.click(screen.getByRole('button', { name: 'Bearbeiten' }));
    fireEvent.change(screen.getByLabelText('Kapazität der Station'), {
      target: { value: '2' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Speichern' }));

    expect(globalThis.confirm).toHaveBeenCalledWith(
      'Die Station wäre 2 überbelegt. Kapazität trotzdem speichern?',
    );
    await waitFor(() => expect(mutate).toHaveBeenCalledWith(
      '/api/happy-cleaning/events/7/stations/10/update/',
      expect.objectContaining({
        max_kids: 2,
        overbooking_confirmation: {
          capacity: 2,
          assigned_count: 4,
          station_version: 3,
        },
      }),
    ));
  });

  it('guards dirty Escape with a backdrop and retains the draft when a structural save is stale', async () => {
    const user = userEvent.setup();
    const onBack = vi.fn();
    const mutate = vi.fn().mockRejectedValue(Object.assign(new Error('failed'), {
      payload: { code: 'stale', current_version: 4 },
    }));
    render(<HappyCleaningStationDetailPage data={{
      ...detailData,
      station: {
        ...detailData.station,
        can_edit: true,
        document: { type: 'doc', content: [] },
      },
    }} mutate={mutate} onBack={onBack} />);

    screen.getByRole('button', { name: 'Bearbeiten' }).focus();
    await user.keyboard('{Enter}');
    const name = screen.getByLabelText('Name der Station');
    const stationCard = name.closest('.card');
    name.focus();
    await user.clear(name);
    await user.keyboard('Entwurf');
    await user.keyboard('{Escape}');
    const dirtyDialog = screen.getByRole('dialog', { name: 'Ungespeicherte Änderungen' });
    expect(dirtyDialog).toBeInTheDocument();
    expect(within(dirtyDialog).getByRole('heading', {
      level: 2,
      name: 'Ungespeicherte Änderungen',
    })).toBeInTheDocument();
    expect(stationCard).not.toContainElement(dirtyDialog);
    const dirtyDialogViewport = dirtyDialog.parentElement;
    const dirtyDialogBackdrop = dirtyDialogViewport?.previousElementSibling;
    expect(dirtyDialogViewport).toHaveAttribute('role', 'presentation');
    expect(dirtyDialogBackdrop).toHaveAttribute('role', 'presentation');
    expect(dirtyDialogBackdrop).toHaveAttribute('data-open');
    screen.getByRole('button', { name: 'Weiter bearbeiten' }).focus();
    await user.keyboard('{Enter}');
    const closeDetail = screen.getByRole('button', { name: 'Detail schließen' });
    expect(closeDetail.closest('.card-toggle')).toBeInTheDocument();
    closeDetail.focus();
    await user.keyboard('{Enter}');
    expect(screen.getByRole('dialog', { name: 'Ungespeicherte Änderungen' })).toBeInTheDocument();
    screen.getByRole('button', { name: 'Weiter bearbeiten' }).focus();
    await user.keyboard('{Enter}');
    await user.click(screen.getByRole('button', { name: 'Detail schließen' }));
    screen.getByRole('button', { name: 'Speichern und weiter' }).focus();
    await user.keyboard('{Enter}');

    const toast = await screen.findByText(/inzwischen geändert/, { selector: '.app-toast-description' });
    expect(toast.closest('.app-toast')).toHaveAttribute('data-type', 'error');
    expect(screen.getByLabelText('Name der Station').closest('form').querySelector('.error')).not.toBeInTheDocument();
    expect(screen.getByLabelText('Name der Station')).toHaveValue('Entwurf');
    expect(onBack).not.toHaveBeenCalled();
  });

  it('confirms an eligible delete and delegates local removal without refresh', async () => {
    vi.spyOn(globalThis, 'confirm').mockReturnValue(true);
    const mutate = vi.fn().mockResolvedValue({ ok: true });
    const onDeleted = vi.fn();
    render(<HappyCleaningStationDetailPage data={{
      ...detailData,
      station: {
        ...detailData.station,
        can_edit: true,
        can_delete: true,
        document: { type: 'doc', content: [] },
      },
    }} mutate={mutate} onDeleted={onDeleted} />);

    fireEvent.click(screen.getByRole('button', { name: 'Bearbeiten' }));
    fireEvent.click(screen.getByRole('button', { name: 'Station löschen' }));

    await waitFor(() => expect(mutate).toHaveBeenCalledWith(
      '/api/happy-cleaning/events/7/stations/10/delete/',
      expect.objectContaining({ expected_version: 3 }),
      true,
      false,
    ));
    expect(onDeleted).toHaveBeenCalledWith(10);
  });

  it('renders the empty task state and converges when remote data is rerendered', () => {
    const { rerender } = render(<HappyCleaningStationDetailPage data={{
      ...detailData,
      station: {
        ...detailData.station,
        todo_checked_count: 0,
        todo_total_count: 0,
        todo_progress_percentage: null,
        children: [],
        todos: [],
        document: { type: 'doc', content: [] },
      },
    }} mutate={vi.fn()} />);

    expect(screen.queryByLabelText('Todo-Fortschritt')).not.toBeInTheDocument();
    expect(document.querySelector('.card-header-action')).not.toBeInTheDocument();
    expect(screen.getByRole('heading', { level: 2, name: 'Aufgaben' })).toBeInTheDocument();
    expect(screen.getByText('Noch kein Inhalt angelegt.')).toBeInTheDocument();
    expect(screen.queryByText('Noch keine Kinder eingeteilt.')).not.toBeInTheDocument();

    rerender(<HappyCleaningStationDetailPage data={{
      event: { ...detailData.event, revision: 8 },
      station: {
        ...detailData.station,
        todo_checked_count: 2,
        todo_total_count: 2,
        todo_progress_percentage: 100,
        children: [...detailData.station.children, {
          id: 3,
          full_name: 'Linus Torvalds',
          assignment_version: 8,
        }],
        todos: detailData.station.todos.map(todo => ({
          ...todo,
          checked: true,
          version: todo.version + 1,
        })),
        document: {
          ...detailData.station.document,
          content: detailData.station.document.content.map(block => (
            block.type !== 'taskList' ? block : {
              ...block,
              content: block.content.map(task => ({
                ...task,
                attrs: {
                  ...task.attrs,
                  checked: true,
                  version: task.attrs.version + 1,
                },
              })),
            }
          )),
        },
      },
    }} mutate={vi.fn()} />);

    expect(screen.queryByText('Linus Torvalds')).not.toBeInTheDocument();
    expect(screen.queryByLabelText('Todo-Fortschritt')).not.toBeInTheDocument();
    expect(document.querySelector('.card-header-action')).not.toBeInTheDocument();
    expect(screen.getByRole('checkbox', { name: 'Boden kehren wieder öffnen' })).toBeChecked();
  });
});
