import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Printer } from 'lucide-react';

import {
  HappyCleaningAssignmentPage,
  HappyCleaningNumberBatchAction,
} from './happyCleaningAssignment';
import {
  HappyCleaningStationDetailPage,
  happyCleaningStationDetailRoutes,
} from './happyCleaningStationDetail';
import { BulkStationCopyDialog, ConflictResolution } from './happyCleaningCopy';


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
  if (code === 'overbooking_confirmation_required') {
    return 'Die Einteilung hat sich geändert. Bitte aktuelle Überbelegung prüfen und erneut bestätigen.';
  }
  return error?.message || 'Die Änderung konnte nicht gespeichert werden.';
};

function Progress({ value }) {
  return <span className="happy-cleaning-progress" aria-label="Todo-Fortschritt">{value === null ? '—' : `${value}%`}</span>;
}

function DeleteConfirmationDialog({ event, onCancel, onConfirm }) {
  const [confirmation, setConfirmation] = useState('');
  const eventName = `Happy Cleaning ${event.display_number}`;
  const titleId = `happy-cleaning-delete-title-${event.id}`;
  const confirmationId = `happy-cleaning-delete-confirmation-${event.id}`;
  const confirmed = confirmation === eventName;
  return (
    <div className="happy-cleaning-delete-backdrop">
      <section
        className="card happy-cleaning-delete-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        onKeyDown={key => { if (key.key === 'Escape') onCancel(); }}
      >
        <h2 id={titleId}>{eventName} löschen</h2>
        <p>Diese Aktion kann nicht rückgängig gemacht werden.</p>
        <label htmlFor={confirmationId}>
          „{eventName}“ zur Bestätigung eingeben
        </label>
        <input
          id={confirmationId}
          autoComplete="off"
          autoFocus
          spellCheck="false"
          value={confirmation}
          onChange={change => setConfirmation(change.target.value)}
        />
        <div className="react-actions">
          <button className="button" type="button" onClick={onCancel}>Abbrechen</button>
          <button
            className="button danger"
            type="button"
            disabled={!confirmed}
            aria-label={`${eventName} endgültig löschen`}
            onClick={onConfirm}
          >
            Endgültig löschen
          </button>
        </div>
      </section>
    </div>
  );
}

export function HappyCleaningCreateButton({ mutate }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const create = async () => {
    setBusy(true);
    setError('');
    try {
      await mutate('/api/happy-cleaning/events/create/', { request_id: requestId() });
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setBusy(false);
    }
  };
  return <><button className="button" type="button" disabled={busy} onClick={create}>Happy Cleaning hinzufügen</button>{error && <span className="error header-action-error" role="alert">{error}</span>}</>;
}

const overviewColumns = [
  { key: 'name', label: 'Stationsname' },
  { key: 'max_kids', label: 'Max Kinder' },
  { key: 'meeting_point', label: 'Treffpunkt' },
  { key: 'task_item_count', label: 'Anzahl Todos' },
];

const compareStationValues = (left, right, key) => {
  const a = left[key];
  const b = right[key];
  if (typeof a === 'number' && typeof b === 'number') return a - b;
  return String(a ?? '').localeCompare(String(b ?? ''), 'de', {
    numeric: true,
    sensitivity: 'base',
  });
};

function StationSummaryTable({ event, stations, sort, onSort, onSelect, selection, rowRefs }) {
  const sorted = useMemo(() => stations
    .map((station, index) => ({ station, index }))
    .sort((left, right) => {
      const compared = compareStationValues(left.station, right.station, sort.key);
      return (sort.direction === 'asc' ? compared : -compared) || left.index - right.index;
    })
    .map(item => item.station), [stations, sort]);
  return (
    <div className="happy-cleaning-overview-table-wrap">
      <table className="happy-cleaning-overview-table">
        <thead>
          <tr>
            {overviewColumns.map(column => {
              const active = sort.key === column.key;
              return (
                <th key={column.key} scope="col" aria-sort={active ? (sort.direction === 'asc' ? 'ascending' : 'descending') : 'none'}>
                  <button className="table-sort-button" type="button" aria-label={`${column.label} sortieren`} onClick={() => onSort(column.key)}>
                    {column.label}
                    {active && <span className="sort-indicator" aria-hidden="true">{sort.direction === 'asc' ? '↑' : '↓'}</span>}
                  </button>
                </th>
              );
            })}
          </tr>
        </thead>
        <tbody>
          {sorted.map(station => (
            <tr
              key={station.id}
              tabIndex={0}
              aria-label={`Station ${station.name}`}
              aria-selected={selection?.eventId === event.id && selection.stationId === station.id}
              onClick={() => onSelect(event, station)}
              onKeyDown={key => {
                if (key.key === 'Enter' || key.key === ' ') {
                  key.preventDefault();
                  onSelect(event, station);
                }
              }}
            >
              <td><button
                className="happy-cleaning-station-row-button"
                type="button"
                ref={node => {
                  const key = `${event.id}:${station.id}`;
                  if (node) rowRefs.current.set(key, node);
                  else rowRefs.current.delete(key);
                }}
                aria-label={`Station ${station.name} öffnen`}
                onClick={click => {
                  click.stopPropagation();
                  onSelect(event, station);
                }}
              >{station.name}</button></td>
              <td>{station.overbooked_count > 0
                ? `${station.overbooked_count} überbelegt`
                : station.max_kids}</td>
              <td>{station.meeting_point}</td>
              <td>{station.task_item_count}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {!stations.length && <p className="happy-cleaning-empty-stations">Noch keine Stationen angelegt.</p>}
    </div>
  );
}

const readOverviewPreference = (key, activeYear) => {
  try {
    const stored = JSON.parse(globalThis.localStorage?.getItem(key) || 'null');
    if (stored && Array.isArray(stored.openYears) && stored.sort) return stored;
  } catch {
    // Storage can be unavailable or contain stale data; use safe defaults.
  }
  return { openYears: [activeYear], sort: { key: 'name', direction: 'asc' } };
};

export function HappyCleaningOverviewPage({
  data,
  mutate,
  fetchImpl = fetch,
  setPageState = () => {},
  realtimeSync,
}) {
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [deleteCandidate, setDeleteCandidate] = useState(null);
  const [copySource, setCopySource] = useState(null);
  const storageKey = `happy-cleaning-overview:${data.user_id}`;
  const [preference, setPreference] = useState(
    () => readOverviewPreference(storageKey, data.active_year),
  );
  const [years, setYears] = useState(data.years);
  const [loadingYears, setLoadingYears] = useState([]);
  const loadingYearRequests = useRef(new Set());
  const detailRequestId = useRef(0);
  const rowRefs = useRef(new Map());
  const detailNavigationGuard = useRef(null);
  const [selection, setSelection] = useState(null);
  const [restoreFocusKey, setRestoreFocusKey] = useState(null);
  const [detail, setDetail] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const loadDetail = useCallback(async selected => {
    const request = ++detailRequestId.current;
    setDetailLoading(true);
    setError('');
    try {
      const response = await fetchImpl(
        `/api/route-data/happy-cleaning-station-detail/?event_id=${selected.eventId}&station_id=${selected.stationId}`,
        { credentials: 'same-origin' },
      );
      if (!response.ok) throw new Error(`Station konnte nicht geladen werden (${response.status})`);
      const payload = await response.json();
      if (request === detailRequestId.current) setDetail(payload);
    } catch (caught) {
      if (request === detailRequestId.current) setError(caught.message);
    } finally {
      if (request === detailRequestId.current) setDetailLoading(false);
    }
  }, [fetchImpl]);
  const selectStationNow = (event, station) => {
    const selected = { eventId: event.id, stationId: station.id };
    setSelection(selected);
    setDetail(null);
    setPageState(current => ({ ...current, happyCleaningEventId: event.id }));
    loadDetail(selected);
  };
  const selectStation = (event, station) => {
    const destination = () => selectStationNow(event, station);
    if (detailNavigationGuard.current) detailNavigationGuard.current(destination);
    else destination();
  };
  const closeDetailNow = () => {
    const key = selection && `${selection.eventId}:${selection.stationId}`;
    detailRequestId.current += 1;
    setRestoreFocusKey(key);
    setSelection(null);
    setDetail(null);
    setPageState(current => ({ ...current, happyCleaningEventId: null }));
  };
  const removeStationLocally = stationId => {
    setYears(current => current.map(group => ({
      ...group,
      turnuses: group.turnuses.map(turnus => ({
        ...turnus,
        events: turnus.events.map(event => ({
          ...event,
          stations: event.stations?.filter(station => station.id !== stationId),
        })),
      })),
    })));
    detailNavigationGuard.current = null;
    closeDetailNow();
  };
  const createStationDraftNow = event => {
    const draft = {
      event,
      responsible_profiles: data.responsible_profiles || [],
      station: {
        id: null,
        version: 1,
        name: '',
        max_kids: 1,
        meeting_point: '',
        wishes: '',
        responsible: null,
        position: null,
        has_ever_had_assignment: false,
        document: { type: 'doc', content: [] },
        content: [],
        todos: [],
        children: [],
        todo_checked_count: 0,
        todo_total_count: 0,
        todo_progress_percentage: null,
        can_edit: true,
        can_delete: false,
        can_toggle_tasks: true,
        is_historical: false,
        is_draft: true,
      },
    };
    setSelection({ eventId: event.id, stationId: null });
    setDetail(draft);
    setPageState(current => ({ ...current, happyCleaningEventId: event.id }));
  };
  const createStationDraft = event => {
    const destination = () => createStationDraftNow(event);
    if (detailNavigationGuard.current) detailNavigationGuard.current(destination);
    else destination();
  };
  const savedStationDetail = result => {
    const station = result.station;
    const paragraphContent = (station.document?.content || [])
      .filter(block => block.type === 'paragraph')
      .map(block => ({
        type: 'paragraph',
        text: (block.content || []).map(node => node.text).join(''),
      }));
    const patched = {
      ...station,
      content: paragraphContent,
      children: [],
      todo_checked_count: 0,
      todo_total_count: station.todos.length,
      todo_progress_percentage: station.todos.length ? 0 : null,
      can_edit: true,
      can_delete: true,
      can_toggle_tasks: true,
      is_historical: false,
    };
    setYears(current => current.map(group => ({
      ...group,
      turnuses: group.turnuses.map(turnus => ({
        ...turnus,
        events: turnus.events.map(event => event.id === result.event.id ? {
          ...event,
          revision: result.event.revision,
          stations: [
            ...(event.stations || []),
            {
              id: station.id,
              name: station.name,
              max_kids: station.max_kids,
              meeting_point: station.meeting_point,
              task_item_count: station.task_item_count,
            },
          ],
        } : event),
      })),
    })));
    setSelection({ eventId: result.event.id, stationId: station.id });
    setDetail({
      event: result.event,
      responsible_profiles: data.responsible_profiles || [],
      station: patched,
    });
  };
  const patchCopiedTarget = (targetEventId, result) => {
    const affected = result.affected_stations || result.copied_stations || [];
    if (!affected.length) return;
    setYears(current => current.map(group => ({
      ...group,
      turnuses: group.turnuses.map(turnus => ({
        ...turnus,
        events: turnus.events.map(event => {
          if (event.id !== targetEventId) return event;
          const affectedById = new Map(affected.map(station => [station.id, station]));
          const retained = (event.stations || []).map(station => {
            const replacement = affectedById.get(station.id);
            if (!replacement) return station;
            affectedById.delete(station.id);
            return {
              ...station,
              ...replacement,
              task_item_count: replacement.todos?.length ?? station.task_item_count,
            };
          });
          return {
            ...event,
            revision: result.event?.revision ?? event.revision,
            stations: [
              ...retained,
              ...[...affectedById.values()].map(station => ({
                ...station,
                task_item_count: station.todos?.length ?? 0,
              })),
            ],
          };
        }),
      })),
    })));
  };
  useEffect(() => {
    if (!selection && restoreFocusKey) {
      rowRefs.current.get(restoreFocusKey)?.focus();
      setRestoreFocusKey(null);
    }
  }, [restoreFocusKey, selection]);
  useEffect(() => {
    setYears(current => data.years.map(group => (
      group.loaded ? group : current.find(item => item.year === group.year && item.loaded) || group
    )));
  }, [data.years]);
  useEffect(() => {
    if (selection?.stationId != null) loadDetail(selection);
    // Realtime refresh replaces overview data; refresh the selected detail too.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data.years]);
  useEffect(() => {
    try {
      globalThis.localStorage?.setItem(storageKey, JSON.stringify(preference));
    } catch {
      // Browser persistence is best-effort.
    }
  }, [preference, storageKey]);
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
    setDeleteCandidate(null);
    run(`/api/happy-cleaning/events/${event.id}/delete/`, {
      expected_revision: event.revision,
    });
  };
  const changeSort = key => setPreference(current => ({
    ...current,
    sort: {
      key,
      direction: current.sort.key === key && current.sort.direction === 'asc' ? 'desc' : 'asc',
    },
  }));
  const loadYear = async group => {
    if (group.loaded || loadingYearRequests.current.has(group.year)) return;
    loadingYearRequests.current.add(group.year);
    setLoadingYears(current => [...current, group.year]);
    try {
      const response = await fetchImpl(
        `/api/route-data/happy-cleaning-overview/?year=${group.year}`,
        { credentials: 'same-origin' },
      );
      if (!response.ok) throw new Error(`Historisches Jahr konnte nicht geladen werden (${response.status})`);
      const payload = await response.json();
      const loaded = payload.years?.[0];
      if (!loaded) throw new Error('Historisches Jahr konnte nicht geladen werden.');
      setYears(current => current.map(item => item.year === group.year ? loaded : item));
    } catch (caught) {
      setError(caught.message);
    } finally {
      loadingYearRequests.current.delete(group.year);
      setLoadingYears(current => current.filter(year => year !== group.year));
    }
  };
  const toggleYear = async group => {
    const opening = !preference.openYears.includes(group.year);
    setPreference(current => ({
      ...current,
      openYears: opening
        ? [...new Set([...current.openYears, group.year])]
        : current.openYears.filter(year => year !== group.year),
    }));
    if (opening) await loadYear(group);
  };
  useEffect(() => {
    years
      .filter(group => preference.openYears.includes(group.year) && !group.loaded)
      .forEach(group => { loadYear(group); });
    // Re-run only when switching users; subsequent openings load in toggleYear.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [storageKey]);
  const eventCount = years.reduce(
    (count, group) => count + group.turnuses.reduce(
      (subtotal, turnus) => subtotal + turnus.events.length, 0,
    ), 0,
  );
  const overview = (
    <div className="happy-cleaning-overview-list">
      {deleteCandidate && (
        <DeleteConfirmationDialog
          event={deleteCandidate}
          onCancel={() => setDeleteCandidate(null)}
          onConfirm={() => remove(deleteCandidate)}
        />
      )}
      {copySource && (
        <BulkStationCopyDialog
          source={copySource}
          targets={data.copy_targets || []}
          mutate={mutate}
          close={() => setCopySource(null)}
          onSuccess={patchCopiedTarget}
        />
      )}
      {error && <p className="error" role="alert">{error}</p>}
      {!eventCount && <p>Noch kein Happy Cleaning angelegt.</p>}
      <div className="happy-cleaning-years">
        {years.map(group => {
          const open = preference.openYears.includes(group.year);
          const loading = loadingYears.includes(group.year);
          return (
            <section className={`card transparent happy-cleaning-year ${open ? '' : 'closed-card'}`} key={group.year}>
              <button className="info-header-container card-toggle" type="button" aria-expanded={open} aria-label={`${group.year} ${open ? 'schließen' : 'öffnen'}`} onClick={() => toggleYear(group)}>
                <h2>{group.year}</h2>
              </button>
              {open && (
                <div className="card-info-container">
                  <div className="card-info-content">
                    {loading && <p role="status">Stationstabellen werden geladen…</p>}
                    {group.loaded && group.turnuses.flatMap(turnus => turnus.events.map(event => (
                      <article className="card happy-cleaning-event" key={event.id}>
                        <h3>{turnus.number}. Turnus {group.year} · Happy Cleaning {event.display_number}</h3>
                        <StationSummaryTable
                          event={event}
                          stations={event.stations}
                          sort={preference.sort}
                          onSort={changeSort}
                          onSelect={selectStation}
                          selection={selection}
                          rowRefs={rowRefs}
                        />
                        <div className="react-actions">
                          {turnus.is_active && (
                            <button
                              className="button"
                              type="button"
                              disabled={busy}
                              onClick={() => createStationDraft(event)}
                            >
                              Station hinzufügen
                            </button>
                          )}
                          <button
                            className="button"
                            type="button"
                            disabled={busy || !event.stations.length}
                            aria-label={`Stationen aus Happy Cleaning ${event.display_number} kopieren`}
                            onClick={() => setCopySource(event)}
                          >
                            Stationen kopieren
                          </button>
                          {event.can_delete && (
                            <button className="button danger" type="button" disabled={busy} aria-label={`Happy Cleaning ${event.display_number} löschen`} onClick={() => setDeleteCandidate(event)}>
                              Löschen
                            </button>
                          )}
                        </div>
                      </article>
                    )))}
                  </div>
                </div>
              )}
            </section>
          );
        })}
      </div>
    </div>
  );
  return (
    <main className={`happy-cleaning-page happy-cleaning-overview-layout ${selection ? 'happy-cleaning-overview-split' : ''}`} id="body-container">
      {overview}
      {selection && (
        <aside className="happy-cleaning-overview-detail" aria-live="polite">
          {detailLoading && !detail && <p role="status">Station wird geladen…</p>}
          {detail && (
            <HappyCleaningStationDetailPage
              data={detail}
              mutate={async (...args) => {
                const result = await mutate(...args);
                if (!detail.station.is_draft && !args[0].endsWith('/delete/')) {
                  await loadDetail(selection);
                }
                return result;
              }}
              realtimeSync={realtimeSync}
              embedded
              onBack={closeDetailNow}
              onDeleted={removeStationLocally}
              initialEditing={Boolean(detail.station.is_draft)}
              refresh={detail.station.is_draft ? savedStationDetail : () => loadDetail(selection)}
              registerNavigationGuard={guard => { detailNavigationGuard.current = guard; }}
              onCopySuccess={patchCopiedTarget}
            />
          )}
        </aside>
      )}
    </main>
  );
}

function PrintSection({ id, title, columns, rows, children }) {
  return (
    <section className="happy-cleaning-print-section" aria-labelledby={id}>
      <h2 id={id}>{title}</h2>
      {children}
      {!rows.length
        ? <p className="happy-cleaning-print-empty">Keine Kinder in diesem Abschnitt.</p>
        : (
          <div className="happy-cleaning-print-table-container">
            <table className="happy-cleaning-print-table" aria-labelledby={id}>
              <thead>
                <tr>{columns.map(column => <th key={column.key} scope="col">{column.label}</th>)}</tr>
              </thead>
              <tbody>
                {rows.map(child => (
                  <tr key={child.id}>
                    {columns.map(column => (
                      <td className={column.className} key={column.key}>
                        {column.render ? column.render(child) : child[column.key]}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
    </section>
  );
}

function HappyCleaningPrintAction() {
  return (
    <button
      aria-label="Drucken"
      className="button mobile-icon-action"
      type="button"
      onClick={() => window.print()}
    >
      <span className="desktop-action-label">Drucken</span>
      <Printer className="mobile-action-label" size={20} aria-hidden="true" />
    </button>
  );
}

export function HappyCleaningPrintPage({ data, mutate, refresh, realtimeSync }) {
  const writeBlocked = Boolean(realtimeSync?.enabled && !realtimeSync.writesEnabled);
  return (
    <main className="happy-cleaning-print-page" id="body-container">
      <header className="happy-cleaning-print-title">
        <h1>Happy Cleaning · Nummernliste</h1>
      </header>
      <PrintSection
        id="happy-cleaning-present-numberless"
        title="Anwesend ohne Nummer"
        columns={[{ key: 'full_name', label: 'Name' }]}
        rows={data.present_numberless}
      >
        {data.number_batch?.available && (
          <div className="happy-cleaning-numberless-actions react-actions">
            <HappyCleaningNumberBatchAction
              eventId={data.number_batch_event_id}
              numberBatch={data.number_batch}
              mutate={mutate}
              refresh={refresh}
              disabled={writeBlocked}
            />
          </div>
        )}
      </PrintSection>
      <PrintSection
        id="happy-cleaning-present-numbered"
        title="Anwesend mit Nummer"
        columns={[
          { key: 'number', label: 'Nummer', className: 'happy-cleaning-print-number' },
          { key: 'full_name', label: 'Name' },
        ]}
        rows={data.present_numbered}
      />
      <PrintSection
        id="happy-cleaning-absent"
        title="Abwesend"
        columns={[
          {
            key: 'number',
            label: 'Nummer',
            className: 'happy-cleaning-print-number',
            render: child => child.number ?? '—',
          },
          { key: 'full_name', label: 'Name' },
        ]}
        rows={data.absent}
      />
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
      const numericCapacity = Number(capacity);
      const overbookedCount = Math.max(
        (station.assigned_count || 0) - numericCapacity, 0,
      );
      if (overbookedCount > 0 && !window.confirm(
        `Die Station wäre ${overbookedCount} überbelegt. Kapazität trotzdem speichern?`,
      )) return;
      onSave({
        name,
        max_kids: numericCapacity,
        meeting_point: meetingPoint,
        wishes,
        responsible_profile_id: responsible ? Number(responsible) : null,
        ...(overbookedCount > 0 ? {
          overbooking_confirmation: {
            capacity: numericCapacity,
            assigned_count: station.assigned_count,
            station_version: station.version,
          },
        } : {}),
      });
    }}>
      <label>Name<input aria-label={`Name der Station ${label}`} value={name} onChange={event => setName(event.target.value)} /></label>
      <label>Kapazität<input aria-label={`Kapazität der Station ${label}`} type="number" min="1" required value={capacity} onChange={event => setCapacity(event.target.value)} /></label>
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
        {station.overbooked_count > 0 && <strong>{station.overbooked_count} überbelegt</strong>}
        <Progress value={station.todo_progress_percentage} />
        <div className="happy-cleaning-order-controls">
          <button className="button" type="button" disabled={busy || index === 0} aria-label={`${station.name} nach oben`} onClick={() => reorderStations(index, -1)}>↑</button>
          <button className="button" type="button" disabled={busy || index === count - 1} aria-label={`${station.name} nach unten`} onClick={() => reorderStations(index, 1)}>↓</button>
        </div>
      </div>
      {expanded && (
        <div className="happy-cleaning-station-details">
          <StationForm key={station.version} station={station} profiles={profiles} busy={busy} onSave={async fields => {
            const url = `/api/happy-cleaning/events/${event.id}/stations/${station.id}/update/`;
            try {
              return await perform(url, { expected_version: station.version, ...fields }, station.id);
            } catch (caught) {
              const confirmation = caught?.payload?.confirmation;
              if (
                caught?.payload?.code !== 'overbooking_confirmation_required'
                || !confirmation
                || !window.confirm(
                  `Die Einteilung hat sich geändert: ${confirmation.overbooked_count} überbelegt. Trotzdem speichern?`,
                )
              ) throw caught;
              return perform(url, {
                expected_version: confirmation.station_version,
                ...fields,
                overbooking_confirmation: {
                  capacity: confirmation.capacity,
                  assigned_count: confirmation.assigned_count,
                  station_version: confirmation.station_version,
                },
              }, station.id);
            }
          }} />
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
  const [conflictResult, setConflictResult] = useState(null);
  const [decisions, setDecisions] = useState({});
  const copy = async (copyAll = true) => {
    const selectedStationIds = copyAll
      ? (source?.stations || []).map(station => station.id)
      : [Number(stationId)];
    const payload = {
      request_id: requestId(),
      expected_revision: conflictResult?.target_revision ?? data.event.revision,
      source_event_id: conflictResult?.source_event_id ?? Number(sourceId),
      station_ids: conflictResult?.station_ids ?? selectedStationIds,
      ...(conflictResult ? { resolutions: Object.entries(decisions).map(([id, decision]) => ({
        source_station_id: Number(id),
        action: decision.action,
        target_station_id: ['overwrite', 'append'].includes(decision.action) ? Number(decision.target_station_id) : null,
      })) } : {}),
    };
    try {
      const result = await perform(
        `/api/happy-cleaning/events/${data.event.id}/stations/copy/`,
        payload,
        null,
        true,
      );
      if (result?.result === 'conflicts') setConflictResult(result);
      else if (result) close();
    } catch {
      // The management page owns transport and validation error presentation.
    }
  };
  const source = data.copy_sources.find(item => String(item.id) === sourceId);
  return (
    <section className="card happy-cleaning-copy" role="dialog" aria-label="Stationen kopieren">
      <h2>Stationen kopieren</h2>
      <label>Quell-Happy-Cleaning<select aria-label="Quell-Happy-Cleaning" value={sourceId} onChange={event => { setSourceId(event.target.value); setStationId(''); setConflictResult(null); setDecisions({}); }}>
        <option value="">Bitte wählen</option>
        {data.copy_sources.map(source => <option key={source.id} value={source.id}>{source.label}</option>)}
      </select></label>
      {source && (
        <label>Einzelne Station<select aria-label="Einzelne Quellstation" value={stationId} onChange={event => setStationId(event.target.value)}>
          <option value="">Bitte wählen</option>
          {source.stations.map(station => <option key={station.id} value={station.id}>{station.name}</option>)}
        </select></label>
      )}
      {conflictResult && (
        <div role="alert">
          <p>Ähnliche Stationen gefunden (Zielversion {conflictResult.target_revision}):</p>
          <ConflictResolution preview={conflictResult} decisions={decisions} setDecisions={setDecisions} />
        </div>
      )}
      <div className="react-actions">
        <button className="button" type="button" disabled={busy || !sourceId || (
          conflictResult && new Set(conflictResult.conflicts.map(item => item.source_station_id)).size !== Object.values(decisions).filter(item => item.action).length
        )} onClick={() => copy()}>{conflictResult ? 'Auswahl verbindlich kopieren' : 'Alle Stationen kopieren'}</button>
        <button className="button" type="button" disabled={busy || !stationId || !!conflictResult} onClick={() => copy(false)}>Ausgewählte Station kopieren</button>
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
    headerAction: (_data, { mutate }) => <HappyCleaningCreateButton mutate={mutate} />,
    render: ({ data, mutate, fetchImpl, setPageState, realtimeSync }) => (
      <HappyCleaningOverviewPage
        data={data}
        mutate={mutate}
        fetchImpl={fetchImpl}
        setPageState={setPageState}
        realtimeSync={realtimeSync}
      />
    ),
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
    pattern: /^\/happy-cleaning\/print$/,
    page: 'happy-cleaning-print',
    title: 'Nummernliste · Happy Cleaning',
    domain: 'happy-cleaning',
    readContractKey: 'happy-cleaning-print',
    headerAction: () => <HappyCleaningPrintAction />,
    render: ({ data, mutate, refresh, realtimeSync }) => (
      <HappyCleaningPrintPage
        data={data}
        mutate={mutate}
        refresh={refresh}
        realtimeSync={realtimeSync}
      />
    ),
  },
  ...happyCleaningStationDetailRoutes,
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
