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
    meeting_point: 'Vor dem Saal',
    wishes: 'Fenster nicht vergessen',
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
    expect(screen.getByText('Fenster nicht vergessen')).toBeInTheDocument();
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

  it('adds at the bottom with the station version and maps errors into composer retry', async () => {
    const stale = new Error('Update failed');
    stale.payload = { code: 'stale' };
    const mutate = vi.fn()
      .mockRejectedValueOnce(stale)
      .mockResolvedValueOnce({ ok: true });
    render(<HappyCleaningStationDetailPage data={detailData} mutate={mutate} />);

    const input = screen.getByRole('textbox', { name: 'Neue Aufgabe' });
    fireEvent.change(input, { target: { value: 'Müll rausbringen' } });
    fireEvent.click(screen.getByRole('button', { name: 'Aufgabe hinzufügen' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('inzwischen geändert');
    expect(input).toHaveValue('Müll rausbringen');
    expect(mutate).toHaveBeenLastCalledWith(
      '/api/happy-cleaning/events/7/stations/10/todos/add/',
      expect.objectContaining({
        expected_version: 3,
        request_id: expect.any(String),
        text: 'Müll rausbringen',
      }),
    );
    fireEvent.click(screen.getByRole('button', { name: 'Erneut versuchen' }));
    await waitFor(() => expect(input).toHaveValue(''));
    expect(input).toHaveFocus();
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
