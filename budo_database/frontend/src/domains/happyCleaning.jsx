import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { PlusIcon, Printer } from 'lucide-react';

import {
  Card,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
  TableScroll,
} from '../components';
import { Button } from '../components/ui/button';
import { useErrorToast } from '../components/ui/toast';
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

function DeleteConfirmationDialog({ event, onCancel, onConfirm }) {
  const [confirmation, setConfirmation] = useState('');
  const eventName = `Happy Cleaning ${event.display_number}`;
  const titleId = `happy-cleaning-delete-title-${event.id}`;
  const confirmationId = `happy-cleaning-delete-confirmation-${event.id}`;
  const confirmed = confirmation === eventName;
  return (
    <div className="happy-cleaning-delete-backdrop fixed inset-0 z-[var(--z-modal)] grid place-items-center bg-black/45 p-6">
      <section
        className="card happy-cleaning-delete-dialog w-full max-w-[30rem] bg-surface-solid p-6"
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
        <div className="mt-4 flex flex-wrap justify-end gap-2">
          <Button variant="secondary" type="button" onClick={onCancel}>Abbrechen</Button>
          <Button
            variant="destructive"
            type="button"
            disabled={!confirmed}
            aria-label={`${eventName} endgültig löschen`}
            onClick={onConfirm}
          >
            Endgültig löschen
          </Button>
        </div>
      </section>
    </div>
  );
}

export function HappyCleaningCreateButton({ mutate }) {
  const [busy, setBusy] = useState(false);
  const showError = useErrorToast();
  const create = async () => {
    setBusy(true);
    try {
      await mutate('/api/happy-cleaning/events/create/', { request_id: requestId() });
    } catch (caught) {
      showError(errorMessage(caught));
    } finally {
      setBusy(false);
    }
  };
  return (
    <>
      <Button
        className="mobile-icon-action"
        size="responsive-icon"
        type="button"
        aria-label="Happy Cleaning hinzufügen"
        disabled={busy}
        onClick={create}
      >
        <span className="desktop-action-label">Happy Cleaning hinzufügen</span>
        <PlusIcon className="mobile-action-label" aria-hidden="true" />
      </Button>
    </>
  );
}

const overviewColumns = [
  { key: 'name', label: 'Stationsname' },
  { key: 'max_kids', label: 'Max Kinder' },
  { key: 'meeting_point', label: 'Treffpunkt' },
  { key: 'responsible_name', label: 'Verantwortlicher' },
  { key: 'task_item_count', label: 'To-Dos' },
];

const stationValue = (station, key) => key === 'responsible_name'
  ? station.responsible?.name
  : station[key];

const compareStationValues = (left, right, key) => {
  const a = stationValue(left, key);
  const b = stationValue(right, key);
  if (typeof a === 'number' && typeof b === 'number') return a - b;
  return String(a ?? '').localeCompare(String(b ?? ''), 'de', {
    numeric: true,
    sensitivity: 'base',
  });
};

const renderTodoPrintNode = (node, key) => {
  const children = (node.content || []).map((child, index) => (
    renderTodoPrintNode(child, `${key}-${index}`)
  ));
  if (node.type === 'text') return node.text || '';
  if (node.type === 'paragraph') return <p key={key}>{children}</p>;
  if (node.type === 'taskList') return <ul key={key}>{children}</ul>;
  if (node.type === 'taskItem') {
    return (
      <li key={key}>
        <span className="happy-cleaning-todo-print-marker" aria-hidden="true">
          {node.attrs?.checked ? '☒' : '☐'}
        </span>
        <div>{children}</div>
      </li>
    );
  }
  return <div key={key}>{children}</div>;
};

function HappyCleaningTodoPrintPages({ data }) {
  return createPortal(
    <div className="happy-cleaning-todo-print-pages hidden print:block" aria-label={`To-Dos für Happy Cleaning ${data.event.display_number}`}>
      {data.stations.map(station => {
        const content = station.document?.content || [];
        return (
          <section className="happy-cleaning-todo-print-station" key={station.id}>
            <h1>{station.name}</h1>
            {content.length
              ? content.map((node, index) => renderTodoPrintNode(node, `${station.id}-${index}`))
              : <p>Keine Aufgaben hinterlegt.</p>}
          </section>
        );
      })}
    </div>,
    document.body,
  );
}

function StationSummaryTable({ event, stations, sort, onSort, onSelect, selection, rowRefs }) {
  const sorted = useMemo(() => stations
    .map((station, index) => ({ station, index }))
    .sort((left, right) => {
      const compared = compareStationValues(left.station, right.station, sort.key);
      return (sort.direction === 'asc' ? compared : -compared) || left.index - right.index;
    })
    .map(item => item.station), [stations, sort]);
  return (
    <div>
      <TableScroll>
        <Table>
          <TableHeader>
            <TableRow className="table-header">
            {overviewColumns.map(column => {
              const active = sort.key === column.key;
              return (
                <TableHead key={column.key} scope="col" aria-sort={active ? (sort.direction === 'asc' ? 'ascending' : 'descending') : 'none'}>
                  <button className="table-sort-button" type="button" aria-label={`${column.label} sortieren`} onClick={() => onSort(column.key)}>
                    {column.label}
                    {active && <span className="sort-indicator" aria-hidden="true">{sort.direction === 'asc' ? '↑' : '↓'}</span>}
                  </button>
                </TableHead>
              );
            })}
            </TableRow>
          </TableHeader>
          <TableBody>
          {sorted.map(station => (
            <TableRow
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
              <TableCell><Button
                className="h-auto justify-start p-0 text-left text-inherit no-underline hover:bg-transparent"
                variant="link"
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
              >{station.name}</Button></TableCell>
              <TableCell>{station.overbooked_count > 0
                ? `${station.overbooked_count} überbelegt`
                : station.max_kids}</TableCell>
              <TableCell>{station.meeting_point}</TableCell>
              <TableCell>{station.responsible?.name || '—'}</TableCell>
              <TableCell>{station.task_item_count}</TableCell>
            </TableRow>
          ))}
          </TableBody>
        </Table>
      </TableScroll>
      {!stations.length && <p className="mb-0">Noch keine Stationen angelegt.</p>}
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
  const [busy, setBusy] = useState(false);
  const showError = useErrorToast();
  const [deleteCandidate, setDeleteCandidate] = useState(null);
  const [copySource, setCopySource] = useState(null);
  const [todoPrintRequest, setTodoPrintRequest] = useState(null);
  const [printingEventId, setPrintingEventId] = useState(null);
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
    try {
      const response = await fetchImpl(
        `/api/route-data/happy-cleaning-overview-station/?event_id=${selected.eventId}&station_id=${selected.stationId}`,
        { credentials: 'same-origin' },
      );
      if (!response.ok) throw new Error(`Station konnte nicht geladen werden (${response.status})`);
      const payload = await response.json();
      if (request === detailRequestId.current) setDetail(payload);
    } catch (caught) {
      if (request === detailRequestId.current) showError(caught.message);
    } finally {
      if (request === detailRequestId.current) setDetailLoading(false);
    }
  }, [fetchImpl, showError]);
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
              responsible: station.responsible,
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
    if (!todoPrintRequest) return undefined;
    // Let React commit the portal and Chromium complete print-media layout before
    // opening the native dialog.
    const printTimer = window.setTimeout(() => {
      window.print();
    }, 50);
    return () => window.clearTimeout(printTimer);
  }, [todoPrintRequest]);
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
    try {
      await mutate(url, { request_id: requestId(), ...payload });
    } catch (caught) {
      showError(errorMessage(caught));
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
  const printTodos = async event => {
    setPrintingEventId(event.id);
    setTodoPrintRequest(null);
    try {
      const response = await fetchImpl(
        `/api/route-data/happy-cleaning-todo-print/?event_id=${event.id}`,
        { credentials: 'same-origin' },
      );
      if (!response.ok) throw new Error(`To-Dos konnten nicht geladen werden (${response.status})`);
      setTodoPrintRequest(await response.json());
    } catch (caught) {
      showError(caught.message);
    } finally {
      setPrintingEventId(null);
    }
  };
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
      showError(caught.message);
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
    <div className={`happy-cleaning-overview-list min-w-0 ${selection ? 'max-[900px]:hidden' : ''}`}>
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
      {!eventCount && <p>Noch kein Happy Cleaning angelegt.</p>}
      <div className="grid gap-4">
        {years.map(group => {
          const open = preference.openYears.includes(group.year);
          const loading = loadingYears.includes(group.year);
          return (
            <Card
              className="transparent"
              expanded={open}
              key={group.year}
              onExpandedChange={() => toggleYear(group)}
              title={`${group.year}`}
            >
              {loading && <p role="status">Stationstabellen werden geladen…</p>}
              {group.loaded && group.turnuses.flatMap(turnus => turnus.events.map(event => (
                <Card
                  actions={(
                    <>
                      {turnus.is_active && (
                        <Button type="button" disabled={busy} onClick={() => createStationDraft(event)}>
                          Station hinzufügen
                        </Button>
                      )}
                      <Button
                        variant="secondary"
                        type="button"
                        disabled={busy || printingEventId !== null || !event.stations.length}
                        aria-label={`To-Dos für Happy Cleaning ${event.display_number} drucken`}
                        onClick={() => printTodos(event)}
                      >
                        To-Dos drucken
                      </Button>
                      <Button
                        variant="secondary"
                        type="button"
                        disabled={busy || !event.stations.length}
                        aria-label={`Stationen aus Happy Cleaning ${event.display_number} kopieren`}
                        onClick={() => setCopySource(event)}
                      >
                        Stationen kopieren
                      </Button>
                      {event.can_delete && (
                        <Button variant="destructive" type="button" disabled={busy} aria-label={`Happy Cleaning ${event.display_number} löschen`} onClick={() => setDeleteCandidate(event)}>
                          Löschen
                        </Button>
                      )}
                    </>
                  )}
                  as="article"
                  className="mb-4"
                  headingLevel={2}
                  key={event.id}
                  title={`${turnus.number}. Turnus ${group.year} · Happy Cleaning ${event.display_number}`}
                >
                  <StationSummaryTable
                    event={event}
                    stations={event.stations}
                    sort={preference.sort}
                    onSort={changeSort}
                    onSelect={selectStation}
                    selection={selection}
                    rowRefs={rowRefs}
                  />
                </Card>
              )))}
            </Card>
          );
        })}
      </div>
    </div>
  );
  return (
    <main
      className={`happy-cleaning-overview-layout mx-auto grid w-full max-w-6xl content-start p-4 max-[900px]:block ${selection ? 'happy-cleaning-overview-split grid-cols-2 gap-4' : 'grid-cols-[minmax(0,1fr)_minmax(0,0fr)] gap-0'} ${todoPrintRequest ? 'happy-cleaning-todo-print-ready' : ''}`}
      id="body-container"
    >
      {overview}
      {selection && (
        <aside
          className="happy-cleaning-overview-detail min-w-0 max-[900px]:fixed max-[900px]:inset-x-0 max-[900px]:bottom-0 max-[900px]:z-[15] max-[900px]:overflow-y-auto max-[900px]:bg-background max-[900px]:p-4 max-[900px]:top-[var(--app-header-height,0px)]"
          aria-live="polite"
        >
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
      {todoPrintRequest && <HappyCleaningTodoPrintPages data={todoPrintRequest} />}
    </main>
  );
}

function PrintSection({ id, title, columns, rows, children }) {
  return (
    <section className="happy-cleaning-print-section mb-6" aria-labelledby={id}>
      <h2 className="mb-2 border-b-2 border-current pb-1 text-xl font-bold" id={id}>{title}</h2>
      {children}
      {!rows.length
        ? <p className="happy-cleaning-print-empty border border-dashed border-current p-2">Keine Kinder in diesem Abschnitt.</p>
        : (
          <TableScroll className="happy-cleaning-print-table-container">
            <Table className="happy-cleaning-print-table" aria-labelledby={id}>
              <TableHeader>
                <TableRow className="table-header">{columns.map(column => <TableHead key={column.key} scope="col">{column.label}</TableHead>)}</TableRow>
              </TableHeader>
              <TableBody>
                {rows.map(child => (
                  <TableRow key={child.id}>
                    {columns.map(column => (
                      <TableCell className={column.className} key={column.key}>
                        {column.render ? column.render(child) : child[column.key]}
                      </TableCell>
                    ))}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableScroll>
        )}
    </section>
  );
}

function HappyCleaningPrintAction() {
  return (
    <Button
      aria-label="Drucken"
      className="mobile-icon-action"
      size="responsive-icon"
      type="button"
      onClick={() => window.print()}
    >
      <span className="desktop-action-label">Drucken</span>
      <Printer className="mobile-action-label" size={20} aria-hidden="true" />
    </Button>
  );
}

export function HappyCleaningPrintPage({ data, mutate, refresh, realtimeSync }) {
  const writeBlocked = Boolean(realtimeSync?.enabled && !realtimeSync.writesEnabled);
  return (
    <main className="happy-cleaning-print-page mx-auto block w-[min(52rem,calc(100%-2rem))] p-6 text-black" id="body-container">
      <header className="happy-cleaning-print-title mb-6 border-b-4 border-double border-current pb-2">
        <h1 className="m-0 text-[clamp(1.65rem,5vw,2.4rem)] font-bold whitespace-normal [overflow-wrap:anywhere]">Happy Cleaning · Nummernliste</h1>
      </header>
      <PrintSection
        id="happy-cleaning-present-numberless"
        title="Anwesend ohne Nummer"
        columns={[{ key: 'full_name', label: 'Name' }]}
        rows={data.present_numberless}
      >
        {data.number_batch?.available && (
          <div className="mb-2 flex justify-start print:hidden">
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
          { key: 'number', label: 'Nummer', className: 'w-24 text-right font-bold tabular-nums' },
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
            className: 'w-24 text-right font-bold tabular-nums',
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
