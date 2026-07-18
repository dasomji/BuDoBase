import { useState } from 'react';

import { BottomComposer } from '../BottomComposer';
import './happyCleaningStationDetail.css';


const requestId = () => globalThis.crypto?.randomUUID?.()
  || `happy-cleaning-todo-${Date.now()}-${Math.random().toString(36).slice(2)}`;

const errorMessage = error => {
  const errors = error?.payload?.errors;
  if (errors) return Object.values(errors).flat().join(' ');
  if (error?.payload?.code === 'stale') {
    return 'Die Daten wurden inzwischen geändert. Bitte erneut versuchen.';
  }
  if (error?.payload?.code === 'sync_unavailable') {
    return 'Vor der nächsten Änderung müssen aktuelle Daten geladen werden.';
  }
  return error?.message || 'Die Änderung konnte nicht gespeichert werden.';
};

function Progress({ station }) {
  const total = station.todo_total_count;
  if (!total) {
    return <span className="happy-cleaning-detail-progress" aria-label="Todo-Fortschritt">—</span>;
  }
  return (
    <span className="happy-cleaning-detail-progress" aria-label="Todo-Fortschritt">
      {station.todo_checked_count}/{total} · {station.todo_progress_percentage}%
    </span>
  );
}

export function HappyCleaningStationDetailPage({ data, mutate, realtimeSync }) {
  const { event, station } = data;
  const [showCompleted, setShowCompleted] = useState(true);
  const [busyTodoId, setBusyTodoId] = useState(null);
  const [error, setError] = useState('');
  const writesBlocked = realtimeSync?.enabled && !realtimeSync.writesEnabled;
  const orderedTodos = [...station.todos].sort((left, right) => (
    left.position - right.position || left.id - right.id
  ));
  const visibleTodos = showCompleted
    ? orderedTodos
    : orderedTodos.filter(todo => !todo.checked);

  const setTodoState = async todo => {
    setBusyTodoId(todo.id);
    setError('');
    const operation = todo.checked ? 'reopen' : 'check';
    try {
      await mutate(
        `/api/happy-cleaning/events/${event.id}/stations/${station.id}/todos/${todo.id}/${operation}/`,
        {
          request_id: requestId(),
          expected_version: todo.version,
        },
      );
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setBusyTodoId(null);
    }
  };

  const addTodo = text => mutate(
    `/api/happy-cleaning/events/${event.id}/stations/${station.id}/todos/add/`,
    {
      request_id: requestId(),
      expected_version: station.version,
      text,
    },
  );

  return (
    <main className="happy-cleaning-station-detail-page" id="body-container">
      <section className="card happy-cleaning-station-detail-card">
        <div className="happy-cleaning-station-detail-heading">
          <h1>{station.name}</h1>
          <Progress station={station} />
        </div>
        <dl className="happy-cleaning-station-facts">
          <div><dt>Treffpunkt</dt><dd>{station.meeting_point || '—'}</dd></div>
          <div><dt>Wünsche</dt><dd>{station.wishes || '—'}</dd></div>
          {station.responsible && (
            <div><dt>Hauptverantwortlich</dt><dd>{station.responsible.name}</dd></div>
          )}
        </dl>

        <h2>Eingeteilte Kinder</h2>
        {!station.children.length && <p>Noch keine Kinder eingeteilt.</p>}
        {station.children.length > 0 && (
          <ul className="happy-cleaning-detail-children">
            {station.children.map(child => <li key={child.id}>{child.full_name}</li>)}
          </ul>
        )}

        <div className="happy-cleaning-checklist-heading">
          <h2>Aufgaben</h2>
          <label>
            <input
              type="checkbox"
              checked={showCompleted}
              onChange={change => setShowCompleted(change.target.checked)}
            />
            Erledigte Aufgaben anzeigen
          </label>
        </div>
        {error && <p className="error" role="alert">{error}</p>}
        {!orderedTodos.length && <p>Noch keine Aufgabe angelegt.</p>}
        {orderedTodos.length > 0 && !visibleTodos.length && (
          <p>Alle Aufgaben sind erledigt.</p>
        )}
        <ol className="happy-cleaning-detail-todos">
          {visibleTodos.map(todo => (
            <li
              key={todo.id}
              aria-label={`Aufgabe ${todo.text}`}
              className={todo.checked ? 'completed' : ''}
            >
              <span>{todo.text}</span>
              <button
                className="button"
                type="button"
                disabled={writesBlocked || busyTodoId !== null}
                aria-label={todo.checked
                  ? `${todo.text} wieder öffnen`
                  : `${todo.text} erledigen`}
                onClick={() => setTodoState(todo)}
              >
                {todo.checked ? 'Wieder öffnen' : 'Erledigt'}
              </button>
            </li>
          ))}
        </ol>
      </section>

      <BottomComposer
        label="Neue Aufgabe"
        placeholder="Aufgabe hinzufügen…"
        submitLabel="Aufgabe hinzufügen"
        onSubmit={addTodo}
        disabled={writesBlocked}
        errorText={errorMessage}
      />
    </main>
  );
}

export const happyCleaningStationDetailRoutes = [{
  pattern: /^\/happy-cleaning\/(\d+)\/stations\/(\d+)$/,
  page: 'happy-cleaning-station-detail',
  title: 'Happy Cleaning Station',
  domain: 'happy-cleaning',
  readContractKey: 'happy-cleaning-station-detail',
  params: match => ({ event_id: match[1], station_id: match[2] }),
  resolveTitle: (_route, data) => data.station?.name || 'Happy Cleaning Station',
  render: ({ data, mutate, realtimeSync }) => (
    <HappyCleaningStationDetailPage
      data={data}
      mutate={mutate}
      realtimeSync={realtimeSync}
    />
  ),
}];
