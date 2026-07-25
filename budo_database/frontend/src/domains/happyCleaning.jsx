import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Printer } from 'lucide-react';

import {
  HappyCleaningAssignmentPage,
  HappyCleaningNumberBatchAction,
} from './happyCleaningAssignment';
import {
  HappyCleaningStationDetailPage,
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
        `/api/route-data/happy-cleaning-overview-station/?event_id=${selected.eventId}&station_id=${selected.stationId}`,
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
];
