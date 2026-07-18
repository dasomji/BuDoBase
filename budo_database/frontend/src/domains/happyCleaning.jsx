import { useState } from 'react';

import { HappyCleaningAssignmentPage } from './happyCleaningAssignment';


const requestId = () => globalThis.crypto?.randomUUID?.()
  || `happy-cleaning-${Date.now()}-${Math.random().toString(36).slice(2)}`;

const errorMessage = error => {
  const errors = error?.payload?.errors;
  if (errors) return Object.values(errors).flat().join(' ');
  const code = error?.payload?.code;
  if (code === 'stale') return 'Die Daten wurden inzwischen geändert. Bitte neu laden.';
  if (code === 'capacity_locked') return 'Die Kapazität ist nach der ersten Einteilung dauerhaft gesperrt.';
  if (code === 'station_locked') return 'Diese Station kann nach der ersten Einteilung nicht gelöscht werden.';
  if (code === 'sync_unavailable') return 'Vor der nächsten Änderung müssen aktuelle Daten geladen werden.';
  return error?.message || 'Die Änderung konnte nicht gespeichert werden.';
};

function Progress({ value }) {
  return <span className="happy-cleaning-progress" aria-label="Todo-Fortschritt">{value === null ? '—' : `${value}%`}</span>;
}

export function HappyCleaningOverviewPage({ data, mutate }) {
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const run = async (url, payload = {}) => {
    setBusy(true);
    setError('');
    try {
      await mutate(url, { request_id: requestId(), ...payload });
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setBusy(false);
    }
  };
  const remove = event => {
    if (window.confirm(`Happy Cleaning ${event.display_number} wirklich löschen?`)) {
      run(`/api/happy-cleaning/events/${event.id}/delete/`, {
        expected_revision: event.revision,
      });
    }
  };
  return (
    <main className="happy-cleaning-page" id="body-container">
      <div className="happy-cleaning-toolbar">
        <button className="button" type="button" disabled={busy} onClick={() => run('/api/happy-cleaning/events/create/')}>
          Happy Cleaning hinzufügen
        </button>
      </div>
      {error && <p className="error" role="alert">{error}</p>}
      {!data.events.length && <p>Noch kein Happy Cleaning angelegt.</p>}
      <ol className="happy-cleaning-events">
        {data.events.map(event => (
          <li className="card happy-cleaning-event" key={event.id}>
            <h2>Happy Cleaning {event.display_number}</h2>
            <div className="react-actions">
              <a className="button" href={`/happy-cleaning/${event.id}/assignment/`} aria-label={`Einteilung für Happy Cleaning ${event.display_number}`}>
                Einteilung
              </a>
              <a className="button" href={`/happy-cleaning/${event.id}/stations/`} aria-label={`Stationen für Happy Cleaning ${event.display_number}`}>
                Stationen
              </a>
              {event.can_delete && (
                <button className="button danger" type="button" disabled={busy} aria-label={`Happy Cleaning ${event.display_number} löschen`} onClick={() => remove(event)}>
                  Löschen
                </button>
              )}
            </div>
          </li>
        ))}
      </ol>
    </main>
  );
}

function StationForm({ station, profiles, onSave, busy }) {
  const [name, setName] = useState(station.name);
  const [capacity, setCapacity] = useState(String(station.max_kids));
  const [meetingPoint, setMeetingPoint] = useState(station.meeting_point);
  const [wishes, setWishes] = useState(station.wishes);
  const [responsible, setResponsible] = useState(station.responsible_profile_id ? String(station.responsible_profile_id) : '');
  const label = station.name;
  return (
    <form className="form-grid happy-cleaning-station-form" onSubmit={event => {
      event.preventDefault();
      onSave({
        name,
        max_kids: Number(capacity),
        meeting_point: meetingPoint,
        wishes,
        responsible_profile_id: responsible ? Number(responsible) : null,
      });
    }}>
      <label>Name<input aria-label={`Name der Station ${label}`} value={name} onChange={event => setName(event.target.value)} /></label>
      <label>Kapazität<input aria-label={`Kapazität der Station ${label}`} type="number" min="1" required disabled={station.has_ever_had_assignment} value={capacity} onChange={event => setCapacity(event.target.value)} /></label>
      <label>Treffpunkt<input aria-label={`Treffpunkt der Station ${label}`} value={meetingPoint} onChange={event => setMeetingPoint(event.target.value)} /></label>
      <label>Wünsche<textarea aria-label={`Wünsche der Station ${label}`} value={wishes} onChange={event => setWishes(event.target.value)} /></label>
      <label>Hauptverantwortlich<select aria-label={`Hauptverantwortlich für Station ${label}`} value={responsible} onChange={event => setResponsible(event.target.value)}>
        <option value="">Niemand</option>
        {profiles.map(profile => <option key={profile.id} value={profile.id}>{profile.name}</option>)}
      </select></label>
      <button className="button" type="submit" disabled={busy} aria-label={`Station ${label} speichern`}>Station speichern</button>
    </form>
  );
}

function TodoEditor({ todo, index, count, station, busy, command, reorder }) {
  const [text, setText] = useState(todo.text);
  return (
    <li className="happy-cleaning-todo">
      <span aria-label={todo.checked ? 'Erledigt' : 'Offen'}>{todo.checked ? '✓' : '○'}</span>
      <input aria-label={`Aufgabe ${todo.text}`} value={text} onChange={event => setText(event.target.value)} />
      <button className="button" type="button" disabled={busy} aria-label={`Aufgabe ${todo.text} speichern`} onClick={() => command('update', { todo, text })}>Speichern</button>
      <button className="button" type="button" disabled={busy || index === 0} aria-label={`Aufgabe ${todo.text} nach oben`} onClick={() => reorder(index, -1)}>↑</button>
      <button className="button" type="button" disabled={busy || index === count - 1} aria-label={`Aufgabe ${todo.text} nach unten`} onClick={() => reorder(index, 1)}>↓</button>
      <button className="button danger" type="button" disabled={busy} aria-label={`Aufgabe ${todo.text} löschen`} onClick={() => command('delete', { todo })}>×</button>
    </li>
  );
}

function StationCard({ event, station, profiles, index, count, expanded, setExpanded, busy, perform, reorderStations }) {
  const [newTodo, setNewTodo] = useState('');
  const commandTodo = (kind, { todo, text } = {}) => {
    if (kind === 'update') return perform(
      `/api/happy-cleaning/events/${event.id}/stations/${station.id}/todos/${todo.id}/update/`,
      { expected_version: todo.version, text },
      station.id,
    );
    if (kind === 'delete') return perform(
      `/api/happy-cleaning/events/${event.id}/stations/${station.id}/todos/${todo.id}/delete/`,
      { expected_version: todo.version },
      station.id,
    );
    return undefined;
  };
  const reorderTodos = (todoIndex, delta) => {
    const ids = station.todos.map(todo => todo.id);
    [ids[todoIndex], ids[todoIndex + delta]] = [ids[todoIndex + delta], ids[todoIndex]];
    perform(
      `/api/happy-cleaning/events/${event.id}/stations/${station.id}/todos/reorder/`,
      { expected_version: station.version, todo_ids: ids },
      station.id,
    );
  };
  return (
    <article className={`card happy-cleaning-station ${expanded ? 'expanded' : ''}`}>
      <div className="happy-cleaning-station-summary">
        <button className="happy-cleaning-expand" type="button" aria-expanded={expanded} aria-label={`${station.name} ${expanded ? 'schließen' : 'öffnen'}`} onClick={() => setExpanded(expanded ? null : station.id)}>
          <strong>{station.name}</strong>
        </button>
        <Progress value={station.todo_progress_percentage} />
        <div className="happy-cleaning-order-controls">
          <button className="button" type="button" disabled={busy || index === 0} aria-label={`${station.name} nach oben`} onClick={() => reorderStations(index, -1)}>↑</button>
          <button className="button" type="button" disabled={busy || index === count - 1} aria-label={`${station.name} nach unten`} onClick={() => reorderStations(index, 1)}>↓</button>
        </div>
      </div>
      {expanded && (
        <div className="happy-cleaning-station-details">
          <StationForm key={station.version} station={station} profiles={profiles} busy={busy} onSave={fields => perform(
            `/api/happy-cleaning/events/${event.id}/stations/${station.id}/update/`,
            { expected_version: station.version, ...fields },
            station.id,
          )} />
          <h3>Aufgaben</h3>
          {!station.todos.length && <p>Noch keine Aufgabe angelegt.</p>}
          <ul className="happy-cleaning-todos">
            {station.todos.map((todo, todoIndex) => (
              <TodoEditor
                key={`${todo.id}:${todo.version}`}
                todo={todo}
                index={todoIndex}
                count={station.todos.length}
                station={station}
                busy={busy}
                command={commandTodo}
                reorder={reorderTodos}
              />
            ))}
          </ul>
          <form className="happy-cleaning-add-todo" onSubmit={submit => {
            submit.preventDefault();
            perform(
              `/api/happy-cleaning/events/${event.id}/stations/${station.id}/todos/create/`,
              { expected_version: station.version, text: newTodo },
              station.id,
            ).then(result => { if (result) setNewTodo(''); });
          }}>
            <label>Neue Aufgabe<input value={newTodo} onChange={change => setNewTodo(change.target.value)} /></label>
            <button className="button" type="submit" disabled={busy}>Aufgabe hinzufügen</button>
          </form>
          {!station.has_ever_had_assignment && (
            <button className="button danger" type="button" disabled={busy} onClick={() => {
              if (window.confirm(`Station ${station.name} wirklich löschen?`)) {
                perform(
                  `/api/happy-cleaning/events/${event.id}/stations/${station.id}/delete/`,
                  { expected_version: station.version },
                );
              }
            }}>Station löschen</button>
          )}
        </div>
      )}
    </article>
  );
}

function NewStationForm({ event, profiles, busy, perform }) {
  const empty = {
    name: '', max_kids: 1, meeting_point: '', wishes: '',
    responsible_profile_id: null, has_ever_had_assignment: false,
  };
  return (
    <details className="card happy-cleaning-create">
      <summary>Neue Station</summary>
      <StationForm station={empty} profiles={profiles} busy={busy} onSave={fields => perform(
        `/api/happy-cleaning/events/${event.id}/stations/create/`,
        { expected_revision: event.revision, ...fields },
      )} />
    </details>
  );
}

function CopyDialog({ data, busy, perform, close }) {
  const [sourceId, setSourceId] = useState('');
  const [stationId, setStationId] = useState('');
  const [duplicateNames, setDuplicateNames] = useState([]);
  const [pending, setPending] = useState(null);
  const copy = async (duplicateStrategy, copyAll = true) => {
    const base = pending || {
      request_id: requestId(),
      expected_revision: data.event.revision,
      source_event_id: Number(sourceId),
      ...(copyAll
        ? { copy_all: true }
        : { station_ids: [Number(stationId)] }),
    };
    try {
      const result = await perform(
        `/api/happy-cleaning/events/${data.event.id}/stations/copy/`,
        { ...base, duplicate_strategy: duplicateStrategy },
        null,
        true,
      );
      if (result) close();
    } catch (error) {
      if (error?.payload?.code === 'duplicate_names') {
        setPending(base);
        setDuplicateNames(error.payload.duplicate_names || []);
      }
    }
  };
  const source = data.copy_sources.find(item => String(item.id) === sourceId);
  return (
    <section className="card happy-cleaning-copy" role="dialog" aria-label="Stationen kopieren">
      <h2>Stationen kopieren</h2>
      <label>Quell-Happy-Cleaning<select aria-label="Quell-Happy-Cleaning" value={sourceId} onChange={event => { setSourceId(event.target.value); setStationId(''); }}>
        <option value="">Bitte wählen</option>
        {data.copy_sources.map(source => <option key={source.id} value={source.id}>{source.label}</option>)}
      </select></label>
      {source && (
        <label>Einzelne Station<select aria-label="Einzelne Quellstation" value={stationId} onChange={event => setStationId(event.target.value)}>
          <option value="">Bitte wählen</option>
          {source.stations.map(station => <option key={station.id} value={station.id}>{station.name}</option>)}
        </select></label>
      )}
      {duplicateNames.length > 0 && (
        <div role="alert">
          <p>Doppelte Stationsnamen: {duplicateNames.join(', ')}</p>
          <button className="button" type="button" onClick={() => copy('copy')}>Doppelte trotzdem kopieren</button>
          <button className="button" type="button" onClick={() => copy('skip')}>Doppelte überspringen</button>
        </div>
      )}
      <div className="react-actions">
        <button className="button" type="button" disabled={busy || !sourceId} onClick={() => copy(undefined)}>Alle Stationen kopieren</button>
        <button className="button" type="button" disabled={busy || !stationId} onClick={() => copy(undefined, false)}>Ausgewählte Station kopieren</button>
        <button className="button" type="button" onClick={close}>Abbrechen</button>
      </div>
    </section>
  );
}

export function HappyCleaningManagementPage({ data, mutate, realtimeSync }) {
  const [expanded, setExpanded] = useState(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [copyOpen, setCopyOpen] = useState(false);
  const writeBlocked = realtimeSync?.enabled && !realtimeSync.writesEnabled;
  const writeBusy = busy || writeBlocked;
  const perform = async (url, payload, expandId = null, preserveError = false) => {
    setBusy(true);
    if (!preserveError) setError('');
    if (expandId) setExpanded(expandId);
    try {
      return await mutate(url, { request_id: requestId(), ...payload });
    } catch (caught) {
      if (caught?.payload?.code === 'duplicate_names' && preserveError) throw caught;
      setError(errorMessage(caught));
      throw caught;
    } finally {
      setBusy(false);
    }
  };
  const reorderStations = (index, delta) => {
    const ids = data.stations.map(station => station.id);
    [ids[index], ids[index + delta]] = [ids[index + delta], ids[index]];
    perform(
      `/api/happy-cleaning/events/${data.event.id}/stations/reorder/`,
      { expected_revision: data.event.revision, station_ids: ids },
    ).catch(() => {});
  };
  return (
    <main className="happy-cleaning-page happy-cleaning-management" id="body-container">
      <div className="happy-cleaning-toolbar">
        <a className="button" href="/happy-cleaning/">Zur Übersicht</a>
        <button className="button" type="button" onClick={() => setCopyOpen(true)}>Stationen kopieren</button>
      </div>
      {error && <p className="error" role="alert">{error}</p>}
      {copyOpen && <CopyDialog data={data} busy={writeBusy} perform={perform} close={() => setCopyOpen(false)} />}
      <NewStationForm event={data.event} profiles={data.responsible_profiles} busy={writeBusy} perform={(...args) => perform(...args).catch(() => {})} />
      {!data.stations.length && <p>Noch keine Station angelegt.</p>}
      <div className="happy-cleaning-stations">
        {data.stations.map((station, index) => (
          <StationCard
            key={station.id}
            event={data.event}
            station={station}
            profiles={data.responsible_profiles}
            index={index}
            count={data.stations.length}
            expanded={expanded === station.id}
            setExpanded={setExpanded}
            busy={writeBusy}
            perform={(...args) => perform(...args).catch(() => null)}
            reorderStations={reorderStations}
          />
        ))}
      </div>
    </main>
  );
}

export const happyCleaningRoutes = [
  {
    pattern: /^\/happy-cleaning$/,
    page: 'happy-cleaning-overview',
    title: 'Happy Cleaning',
    domain: 'happy-cleaning',
    readContractKey: 'happy-cleaning-overview',
    render: ({ data, mutate }) => <HappyCleaningOverviewPage data={data} mutate={mutate} />,
  },
  {
    pattern: /^\/happy-cleaning\/(\d+)\/assignment$/,
    page: 'happy-cleaning-assignment',
    title: 'Happy Cleaning Einteilung',
    domain: 'happy-cleaning',
    readContractKey: 'happy-cleaning-assignment',
    params: match => ({ event_id: match[1] }),
    resolveTitle: (_route, data) => `Einteilung · Happy Cleaning ${data.event?.display_number || ''}`.trim(),
    render: ({ data, mutate, refresh, realtimeSync }) => <HappyCleaningAssignmentPage data={data} mutate={mutate} refresh={refresh} realtimeSync={realtimeSync} />,
  },
  {
    pattern: /^\/happy-cleaning\/(\d+)\/stations$/,
    page: 'happy-cleaning-stations',
    title: 'Happy Cleaning Stationen',
    domain: 'happy-cleaning',
    readContractKey: 'happy-cleaning-stations',
    params: match => ({ event_id: match[1] }),
    resolveTitle: (_route, data) => `Stationen · Happy Cleaning ${data.event?.display_number || ''}`.trim(),
    render: ({ data, mutate, realtimeSync }) => <HappyCleaningManagementPage data={data} mutate={mutate} realtimeSync={realtimeSync} />,
  },
];
