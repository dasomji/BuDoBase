import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { routeDataRequest } from '../dataLoader';
import { parseRoute } from '../routes';
import {
  HappyCleaningStationDetailPage,
} from './happyCleaningStationDetail';


const detailData = {
  event: { id: 7, display_number: 2, revision: 5 },
  station: {
    id: 10,
    version: 3,
    name: 'Speisesaal',
    max_kids: 4,
    meeting_point: 'Vor dem Saal',
    wishes: 'Fenster nicht vergessen',
    content: [{ type: 'paragraph', text: 'Fenster öffnen' }],
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
    todos: [
      { id: 100, version: 2, text: 'Tische wischen', position: 1, checked: true },
      { id: 101, version: 1, text: 'Boden kehren', position: 2, checked: false },
    ],
  },
};


describe('Happy Cleaning station detail', () => {
  afterEach(cleanup);

  it('declares a deep-linkable immutable event/station route', () => {
    const route = parseRoute('/happy-cleaning/7/stations/10/');

    expect(route).toMatchObject({
      event_id: '7',
      station_id: '10',
      readContractKey: 'happy-cleaning-station-detail',
    });
    expect(routeDataRequest(route).url).toBe(
      '/api/route-data/happy-cleaning-station-detail/?event_id=7&station_id=10',
    );
  });

  it('shows operational fields, full child names and the ordered checklist only', () => {
    render(<HappyCleaningStationDetailPage data={detailData} mutate={vi.fn()} />);

    expect(screen.getByRole('heading', { name: 'Speisesaal' })).toBeInTheDocument();
    expect(screen.getByText('Vor dem Saal')).toBeInTheDocument();
    expect(screen.getByText('4')).toBeInTheDocument();
    expect(screen.getByText('Fenster nicht vergessen')).toBeInTheDocument();
    expect(screen.getByText('Fenster öffnen')).toBeInTheDocument();
    expect(screen.getByText('Mira')).toBeInTheDocument();
    expect(screen.getByText('Ada Lovelace')).toBeInTheDocument();
    expect(screen.getByText('Grace Hopper')).toBeInTheDocument();
    expect(screen.getByLabelText('Todo-Fortschritt')).toHaveTextContent('1/2 · 50%');
    expect(screen.getAllByRole('listitem', { name: /Aufgabe/ }).map(item => item.textContent)).toEqual([
      expect.stringContaining('Tische wischen'),
      expect.stringContaining('Boden kehren'),
    ]);
    expect(screen.queryByRole('button', { name: /löschen|bearbeiten|nach oben|nach unten/i })).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/Name der Station|Treffpunkt der Station/)).not.toBeInTheDocument();
  });

  it('keeps hide-completed local and sends versioned check/reopen commands', async () => {
    const mutate = vi.fn().mockResolvedValue({ ok: true });
    render(<HappyCleaningStationDetailPage data={detailData} mutate={mutate} />);

    fireEvent.click(screen.getByRole('checkbox', { name: 'Erledigte Aufgaben anzeigen' }));
    expect(screen.queryByText('Tische wischen')).not.toBeInTheDocument();
    expect(screen.getByText('Boden kehren')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Boden kehren erledigen' }));

    await waitFor(() => expect(mutate).toHaveBeenCalledWith(
      '/api/happy-cleaning/events/7/stations/10/todos/101/check/',
      expect.objectContaining({ expected_version: 1, request_id: expect.any(String) }),
    ));

    fireEvent.click(screen.getByRole('checkbox', { name: 'Erledigte Aufgaben anzeigen' }));
    fireEvent.click(screen.getByRole('button', { name: 'Tische wischen wieder öffnen' }));
    await waitFor(() => expect(mutate).toHaveBeenCalledWith(
      '/api/happy-cleaning/events/7/stations/10/todos/100/reopen/',
      expect.objectContaining({ expected_version: 2, request_id: expect.any(String) }),
    ));
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

    fireEvent.click(screen.getByRole('button', { name: 'Boden kehren erledigen' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('erneut versuchen');
    await waitFor(() => expect(refresh).toHaveBeenCalledTimes(1));
    expect(screen.getByRole('button', { name: 'Boden kehren erledigen' })).toBeEnabled();
  });

  it('allows independent task items to be changed concurrently', async () => {
    let finishFirst;
    const mutate = vi.fn()
      .mockImplementationOnce(() => new Promise(resolve => { finishFirst = resolve; }))
      .mockResolvedValueOnce({ ok: true });
    render(<HappyCleaningStationDetailPage data={detailData} mutate={mutate} />);

    fireEvent.click(screen.getByRole('button', { name: 'Boden kehren erledigen' }));
    expect(screen.getByRole('button', { name: 'Boden kehren erledigen' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Tische wischen wieder öffnen' })).toBeEnabled();
    fireEvent.click(screen.getByRole('button', { name: 'Tische wischen wieder öffnen' }));

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
    expect(screen.queryByRole('button', { name: /erledigen|wieder öffnen/i })).not.toBeInTheDocument();
    expect(screen.queryByText('Eingeteilte Kinder')).not.toBeInTheDocument();
    expect(screen.queryByText('Mira')).not.toBeInTheDocument();
    expect(screen.queryByText('Ada Lovelace')).not.toBeInTheDocument();
    expect(screen.queryByRole('textbox')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Bearbeiten' })).not.toBeInTheDocument();
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

    fireEvent.click(screen.getByRole('button', { name: 'Bearbeiten' }));
    expect(screen.queryByRole('toolbar')).not.toBeInTheDocument();
    expect(await screen.findByRole('checkbox', {
      name: 'Aufgabenstatus wird beim Bearbeiten nicht geändert',
    })).toBeDisabled();
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

  it('guards dirty Escape and retains the draft when a structural save is stale', async () => {
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

    fireEvent.click(screen.getByRole('button', { name: 'Bearbeiten' }));
    fireEvent.change(screen.getByLabelText('Name der Station'), { target: { value: 'Entwurf' } });
    fireEvent.keyDown(document, { key: 'Escape' });
    expect(screen.getByRole('dialog', { name: 'Ungespeicherte Änderungen' })).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Weiter bearbeiten' }));
    fireEvent.click(screen.getByRole('button', { name: 'Detail schließen' }));
    expect(screen.getByRole('dialog', { name: 'Ungespeicherte Änderungen' })).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Weiter bearbeiten' }));
    fireEvent.keyDown(document, { key: 'Escape' });
    fireEvent.click(screen.getByRole('button', { name: 'Speichern und weiter' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('inzwischen geändert');
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

  it('renders the zero state as a dash and converges when remote data is rerendered', () => {
    const { rerender } = render(<HappyCleaningStationDetailPage data={{
      ...detailData,
      station: {
        ...detailData.station,
        todo_checked_count: 0,
        todo_total_count: 0,
        todo_progress_percentage: null,
        children: [],
        todos: [],
      },
    }} mutate={vi.fn()} />);

    expect(screen.getByLabelText('Todo-Fortschritt')).toHaveTextContent('—');
    expect(screen.getByText('Noch keine Aufgabe angelegt.')).toBeInTheDocument();
    expect(screen.getByText('Noch keine Kinder eingeteilt.')).toBeInTheDocument();

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
      },
    }} mutate={vi.fn()} />);

    expect(screen.getByText('Linus Torvalds')).toBeInTheDocument();
    expect(screen.getByLabelText('Todo-Fortschritt')).toHaveTextContent('2/2 · 100%');
  });
});
