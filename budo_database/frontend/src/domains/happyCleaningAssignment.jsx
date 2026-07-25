import { useEffect, useMemo, useRef, useState } from 'react';
import { Dialog } from '@base-ui/react/dialog';
import { Eye, EyeOff, Pencil, X } from 'lucide-react';
import { useToastManager } from '../components/ui/toast';


const requestId = () => globalThis.crypto?.randomUUID?.()
  || `happy-cleaning-${Date.now()}-${Math.random().toString(36).slice(2)}`;

function useMobileViewport() {
  const media = globalThis.matchMedia?.('(max-width: 639px)');
  const [mobile, setMobile] = useState(Boolean(media?.matches));
  useEffect(() => {
    const update = event => setMobile(event.matches);
    media?.addEventListener?.('change', update);
    return () => media?.removeEventListener?.('change', update);
  }, [media]);
  return mobile;
}

function presenceLabel(child) {
  if (child.present) return 'Anwesend';
  return child.absence_location
    ? `Abwesend · ${child.absence_location}`
    : 'Abwesend';
}

function PlaceholderChildDetails() {
  return (
    <section className="card happy-cleaning-selected-child" aria-label="Platzhalter Kind">
      <h2>Carlos</h2>
      <dl>
        <div><dt>Nummer</dt><dd>∞</dd></div>
        <div><dt>Station</dt><dd>überall und nirgends</dd></div>
      </dl>
    </section>
  );
}

function ChildDetails({ child, busy, onNumber }) {
  const [number, setNumber] = useState(child.number === null ? '' : String(child.number));
  const [editingNumber, setEditingNumber] = useState(child.number === null);
  useEffect(() => {
    setNumber(child.number === null ? '' : String(child.number));
    setEditingNumber(child.number === null);
  }, [child.id, child.number]);
  const numberForm = (
    <form className="happy-cleaning-number-form" onSubmit={event => {
      event.preventDefault();
      onNumber(Number(number));
    }}>
      <input
        type="number"
        min="1"
        required
        aria-label={`Happy Cleaning Nummer für ${child.full_name}`}
        disabled={busy}
        value={number}
        onChange={event => setNumber(event.target.value)}
      />
      <button className="button" type="submit" disabled={busy}>
        {child.number === null ? 'Nummer speichern' : 'Nummer aktualisieren'}
      </button>
      {child.number !== null && (
        <button
          className="button happy-cleaning-number-cancel"
          type="button"
          disabled={busy}
          onClick={() => {
            setNumber(String(child.number));
            setEditingNumber(false);
          }}
        >
          Abbrechen
        </button>
      )}
    </form>
  );
  return (
    <section className="card happy-cleaning-selected-child" aria-label="Ausgewähltes Kind">
      <h2>{child.full_name}{!child.present && ' ❌'}</h2>
      <dl>
        <div>
          <dt>Nummer</dt>
          <dd>
            {editingNumber
              ? numberForm
              : (
                <span className="happy-cleaning-number-value">
                  {child.number}
                  <button
                    className="happy-cleaning-number-edit"
                    type="button"
                    aria-label={`Nummer für ${child.full_name} bearbeiten`}
                    title="Nummer bearbeiten"
                    onClick={() => setEditingNumber(true)}
                  >
                    <Pencil size={18} aria-hidden="true" />
                  </button>
                </span>
              )}
          </dd>
        </div>
        <div>
          <dt>Station</dt>
          <dd>
            {child.assigned_station?.name
              || (child.number === null
                ? 'Kann erst eingeteilt werden, wenn eine Nummer eingetragen wurde'
                : 'Auf den Stationsnamen in der Liste klicken zum einteilen')}
          </dd>
        </div>
      </dl>
    </section>
  );
}

function DuplicateNumberDialog({ error, neighborhood, busy, onSelect, onClose }) {
  return (
    <Dialog.Root open onOpenChange={open => { if (!open) onClose(); }}>
      <Dialog.Portal>
        <Dialog.Backdrop className="happy-cleaning-dialog-backdrop" />
        <Dialog.Viewport className="happy-cleaning-dialog-viewport">
          <Dialog.Popup className="card happy-cleaning-number-dialog">
            <Dialog.Title>{error}</Dialog.Title>
            <Dialog.Description>
              Klicke auf eine freie Zahl zum zuweisen
            </Dialog.Description>
            <Dialog.Close className="happy-cleaning-dialog-close" aria-label="Dialog schließen">
              <X size={20} aria-hidden="true" />
            </Dialog.Close>
            <ul className="happy-cleaning-number-neighborhood" aria-label="Freie Nummer auswählen">
              {neighborhood.map(item => (
                <li key={item.number}>
                  {item.free
                    ? (
                      <button
                        type="button"
                        disabled={busy}
                        aria-label={`${item.number} als Nummer zuweisen`}
                        onClick={() => onSelect(item.number)}
                      >
                        <strong>{item.number}</strong>
                        <span>frei</span>
                      </button>
                    )
                    : (
                      <span className="happy-cleaning-number-occupied">
                        <strong>{item.number}</strong>
                        <span>{item.child?.display_name}</span>
                      </span>
                    )}
                </li>
              ))}
            </ul>
          </Dialog.Popup>
        </Dialog.Viewport>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

export function HappyCleaningNumberBatchAction({
  eventId,
  numberBatch,
  mutate,
  refresh,
  disabled = false,
}) {
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  if (!numberBatch?.available) return null;

  const assignments = numberBatch.children.map(child => ({
    child_id: child.id,
    number: child.number,
    expected_version: child.expected_version,
  }));
  const confirm = async () => {
    setBusy(true);
    setError('');
    try {
      const result = await mutate(`/api/happy-cleaning/events/${eventId}/numbers/assign-missing/`, {
        request_id: requestId(),
        assignments,
      });
      if (result?.ok === false) {
        const replayedError = new Error(result.code);
        replayedError.payload = result;
        throw replayedError;
      }
      setOpen(false);
    } catch (caught) {
      const code = caught?.payload?.code;
      if (code === 'stale' || code === 'batch_locked' || code === 'nothing_to_assign') {
        await refresh?.({ preserveData: true });
      }
      setError(code === 'stale'
        ? 'Die Nummernvorschläge sind nicht mehr aktuell. Die Daten wurden neu geladen.'
        : code === 'batch_locked'
          ? 'Die automatische Nummernvergabe ist nicht mehr verfügbar.'
          : code === 'nothing_to_assign'
            ? 'Es sind keine Nummern mehr zuzuteilen. Die Daten wurden neu geladen.'
            : 'Die Nummern konnten nicht zugeteilt werden. Bitte erneut versuchen.');
    } finally {
      setBusy(false);
    }
  };
  const changeOpen = nextOpen => {
    if (!nextOpen && busy) return;
    setError('');
    setOpen(nextOpen);
  };

  return (
    <Dialog.Root open={open} onOpenChange={changeOpen}>
      <Dialog.Trigger
        className="button happy-cleaning-batch-trigger"
        disabled={disabled}
      >
        Kindern ohne Nummern, Nummern zuteilen
      </Dialog.Trigger>
      <Dialog.Portal>
        <Dialog.Backdrop className="happy-cleaning-dialog-backdrop" />
        <Dialog.Viewport className="happy-cleaning-dialog-viewport">
          <Dialog.Popup className="card happy-cleaning-number-dialog happy-cleaning-batch-dialog">
            <Dialog.Title>Nummern zuteilen</Dialog.Title>
            <Dialog.Description>
              Die vorgeschlagenen Nummern werden gemeinsam zugeteilt.
            </Dialog.Description>
            <Dialog.Close className="happy-cleaning-dialog-close" aria-label="Dialog schließen" disabled={busy}>
              <X size={20} aria-hidden="true" />
            </Dialog.Close>
            <ul className="happy-cleaning-batch-list" aria-label="Vorgeschlagene Nummern">
              {numberBatch.children.map(child => (
                <li key={child.id}>
                  <span>{child.full_name}</span>
                  <strong>{child.number}</strong>
                </li>
              ))}
            </ul>
            {error && <p className="error" role="alert">{error}</p>}
            <div className="happy-cleaning-batch-actions" role="group" aria-label="Dialogaktionen">
              <Dialog.Close className="button" disabled={busy}>Abbrechen</Dialog.Close>
              <button className="button" type="button" disabled={busy || disabled} onClick={confirm}>
                {busy ? 'Wird zugeteilt…' : 'Bestätigen'}
              </button>
            </div>
          </Dialog.Popup>
        </Dialog.Viewport>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

function ChildSearch({ children, selected, onSelect, inputRef }) {
  const mobile = useMobileViewport();
  const [query, setQuery] = useState(selected?.full_name || '');
  const [activeIndex, setActiveIndex] = useState(-1);
  const [menuOpen, setMenuOpen] = useState(false);
  useEffect(() => {
    if (selected) setQuery(selected.full_name);
  }, [selected]);
  const results = useMemo(() => {
    const needle = query.trim().toLocaleLowerCase('de');
    if (!needle) return [];
    return children.filter(child => child.full_name.toLocaleLowerCase('de').includes(needle));
  }, [children, query]);
  const open = menuOpen && results.length > 0;
  useEffect(() => {
    if (open && activeIndex >= 0) {
      document.getElementById(`happy-cleaning-child-${results[activeIndex]?.id}`)
        ?.scrollIntoView?.({ block: 'nearest' });
    }
  }, [activeIndex, open, results]);
  const choose = child => {
    onSelect(child);
    setQuery(child.full_name);
    setActiveIndex(-1);
    setMenuOpen(false);
  };
  const onKeyDown = event => {
    if (event.key === 'Escape') {
      setActiveIndex(-1);
      setMenuOpen(false);
      return;
    }
    if (!open) return;
    if (event.key === 'ArrowDown') {
      event.preventDefault();
      setActiveIndex(index => Math.min(index + 1, results.length - 1));
    } else if (event.key === 'ArrowUp') {
      event.preventDefault();
      setActiveIndex(index => Math.max(index - 1, 0));
    } else if (event.key === 'Enter' && activeIndex >= 0) {
      event.preventDefault();
      choose(results[activeIndex]);
    }
  };
  return (
    <div className="happy-cleaning-child-search">
      <label className="sr-only" htmlFor="happy-cleaning-child-search">Kind suchen</label>
      <input
        id="happy-cleaning-child-search"
        type="search"
        role="combobox"
        aria-autocomplete="list"
        aria-controls="happy-cleaning-child-results"
        aria-expanded={open}
        aria-activedescendant={activeIndex >= 0 ? `happy-cleaning-child-${results[activeIndex]?.id}` : undefined}
        placeholder="Kind suchen…"
        value={query}
        ref={inputRef}
        onChange={event => {
          setQuery(event.target.value);
          setActiveIndex(-1);
          setMenuOpen(true);
        }}
        onFocus={() => { if (results.length) setMenuOpen(true); }}
        onKeyDown={onKeyDown}
      />
      <span className="sr-only" aria-live="polite">
        {open ? `${results.length} Suchergebnisse` : ''}
      </span>
      {open && (
        <div id="happy-cleaning-child-results" className="happy-cleaning-child-results" role="listbox">
          {results.map((child, index) => (
            <button
              id={`happy-cleaning-child-${child.id}`}
              className={index === activeIndex ? 'selected' : ''}
              type="button"
              role="option"
              aria-selected={index === activeIndex}
              key={child.id}
              onClick={() => choose(child)}
            >
              <strong>{child.full_name}</strong>
              {!mobile && (
                <span>
                  <span>#{child.number ?? '—'}</span>
                  <span>{child.assigned_station?.name || 'Nicht eingeteilt'}</span>
                  <span>{presenceLabel(child)}</span>
                </span>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function UnassignedCounter({ summary, children, onSelect, batchAction }) {
  const [open, setOpen] = useState(false);
  const unassigned = children.filter(child => child.present && !child.assigned_station);
  const count = `Eingeteilt: ${summary.assigned_present}/${summary.present_total}`;
  return (
    <div className="happy-cleaning-counter-row">
      <span className="happy-cleaning-counter-info">{count}</span>
      <Dialog.Root open={open} onOpenChange={setOpen}>
        <Dialog.Trigger className="button happy-cleaning-counter">
          Nicht eingeteilte Kinder anzeigen
        </Dialog.Trigger>
        <Dialog.Portal>
          <Dialog.Backdrop className="happy-cleaning-dialog-backdrop" />
          <Dialog.Viewport className="happy-cleaning-dialog-viewport">
            <Dialog.Popup className="card happy-cleaning-unassigned-dialog">
              <Dialog.Title>Anwesende nicht eingeteilte Kinder</Dialog.Title>
              <Dialog.Close className="happy-cleaning-dialog-close" aria-label="Dialog schließen">
                <X size={20} aria-hidden="true" />
              </Dialog.Close>
              <ul aria-label="Anwesende nicht eingeteilte Kinder">
                {unassigned.map(child => (
                  <li key={child.id}>
                    <button type="button" aria-label={`${child.full_name} auswählen`} onClick={() => { onSelect(child); setOpen(false); }}>
                      {child.full_name}
                    </button>
                  </li>
                ))}
                {!unassigned.length && <li>Alle anwesenden Kinder sind eingeteilt.</li>}
              </ul>
            </Dialog.Popup>
          </Dialog.Viewport>
        </Dialog.Portal>
      </Dialog.Root>
      {batchAction}
    </div>
  );
}

function StationName({ eventId, station, selected, busy, onActivate }) {
  const full = !station.is_excused && station.free_seats === 0;
  const label = `${station.name}${full ? ' 🚫' : ''}`;
  if (!selected) {
    return station.is_excused
      ? <span>{label}</span>
      : <a href={`/happy-cleaning/${eventId}/stations/${station.id}/`}>{label}</a>;
  }
  const currentTarget = selected.assigned_station?.id === station.id;
  const fullTarget = full && !currentTarget;
  return (
    <button
      type="button"
      aria-label={`${selected.full_name} ${station.name} zuweisen`}
      disabled={busy || (!station.is_excused && selected.number === null) || fullTarget || currentTarget}
      onClick={() => onActivate(station)}
    >
      {label}
    </button>
  );
}

function ChildPills({ station, onSelect }) {
  return (
    <div className="happy-cleaning-child-pills">
      {station.children.map(child => (
        <button
          className="happy-cleaning-child-pill"
          type="button"
          aria-label={`${child.full_name} auswählen`}
          title={`${child.full_name} #${child.number ?? '—'}`}
          onClick={() => onSelect(child)}
          key={child.id}
        >
          {child.short_name}{!child.present && ' ❌'}
        </button>
      ))}
    </div>
  );
}

const progress = station => station.todo_progress_percentage === null
  ? '—'
  : `${station.todo_progress_percentage}%`;

function StationDetailsDialog({ station, onSelect }) {
  const [open, setOpen] = useState(false);
  return (
    <Dialog.Root open={open} onOpenChange={setOpen}>
      <Dialog.Trigger
        className="happy-cleaning-station-details-trigger"
        aria-label={`Details zu ${station.name} anzeigen`}
        title={`Details zu ${station.name} anzeigen`}
      >
        <Eye size={20} aria-hidden="true" />
      </Dialog.Trigger>
      <Dialog.Portal>
        <Dialog.Backdrop className="happy-cleaning-dialog-backdrop" />
        <Dialog.Viewport className="happy-cleaning-dialog-viewport">
          <Dialog.Popup className="card happy-cleaning-station-dialog">
            <Dialog.Title>{station.name}</Dialog.Title>
            <Dialog.Close className="happy-cleaning-dialog-close" aria-label="Dialog schließen">
              <X size={20} aria-hidden="true" />
            </Dialog.Close>
            <dl>
              <div><dt>Wünsche</dt><dd>{station.wishes || '—'}</dd></div>
              <div><dt>Treffpunkt</dt><dd>{station.meeting_point}</dd></div>
              <div><dt>Verantwortlich</dt><dd>{station.responsible?.name || '—'}</dd></div>
              <div><dt>Plätze</dt><dd>{station.free_seats} / {station.max_kids} frei</dd></div>
              <div><dt>Aufgaben</dt><dd>{progress(station)}</dd></div>
              <div>
                <dt>Kinder</dt>
                <dd>
                  <ChildPills station={station} onSelect={child => {
                    onSelect(child);
                    setOpen(false);
                  }} />
                </dd>
              </div>
            </dl>
          </Dialog.Popup>
        </Dialog.Viewport>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

function DesktopStations({ eventId, stations, selected, busy, onActivate, onSelect, mobile }) {
  const [childrenVisible, setChildrenVisible] = useState(true);
  const toggleLabel = childrenVisible ? 'Kindernamen verbergen' : 'Kindernamen anzeigen';
  return (
    <div className="table-container happy-cleaning-assignment-table-wrap">
      <table className={`data-table${childrenVisible ? '' : ' happy-cleaning-children-hidden'}${mobile ? ' happy-cleaning-mobile-table' : ''}`} aria-label="Happy Cleaning Stationen">
        <thead><tr className="table-header">
          <th>{mobile ? 'SWP' : 'Station'}</th>
          <th className="happy-cleaning-desktop-column">Wünsche</th>
          <th className="happy-cleaning-desktop-column">Treffpunkt</th>
          <th className="happy-cleaning-desktop-column">Verantwortlich</th>
          <th className="happy-cleaning-places-column">Plätze</th>
          <th className="happy-cleaning-desktop-column">Aufgaben</th>
          <th className="happy-cleaning-desktop-column">
            <div className="happy-cleaning-children-header">
              <span>Kinder</span>
              <button
                className="happy-cleaning-children-toggle"
                type="button"
                aria-label={toggleLabel}
                title={toggleLabel}
                onClick={() => setChildrenVisible(value => !value)}
              >
                {childrenVisible ? <Eye size={20} /> : <EyeOff size={20} />}
              </button>
            </div>
          </th>
          {mobile && <th><span className="sr-only">Details</span></th>}
        </tr></thead>
        <tbody>
          {stations.map(station => (
            <tr className={`table_row${station.is_excused ? ' happy-cleaning-excused-row' : ''}`} key={station.id}>
              <th scope="row"><StationName eventId={eventId} station={station} selected={selected} busy={busy} onActivate={onActivate} /></th>
              {station.is_excused
                ? (
                  <td className="happy-cleaning-excused-children" colSpan={mobile ? 7 : 6}>
                    <span
                      className="happy-cleaning-assigned-count"
                      aria-label={`${station.children.length} ${station.children.length === 1 ? 'eingeteiltes Kind' : 'eingeteilte Kinder'}`}
                    >
                      {station.children.length}
                    </span>
                    <ChildPills station={station} onSelect={onSelect} />
                  </td>
                )
                : (
                  <>
                    <td className="happy-cleaning-desktop-column">{station.wishes || '—'}</td>
                    <td className="happy-cleaning-desktop-column">{station.meeting_point}</td>
                    <td className="happy-cleaning-desktop-column">{station.responsible?.name || '—'}</td>
                    <td className="happy-cleaning-places-column">{station.free_seats} / {station.max_kids} frei</td>
                    <td className="happy-cleaning-desktop-column">{progress(station)}</td>
                    <td className="happy-cleaning-desktop-column">
                      <span
                        className="happy-cleaning-assigned-count"
                        aria-label={`${station.children.length} ${station.children.length === 1 ? 'eingeteiltes Kind' : 'eingeteilte Kinder'}`}
                      >
                        {station.children.length}
                      </span>
                      <ChildPills station={station} onSelect={onSelect} />
                    </td>
                    {mobile && <td><StationDetailsDialog station={station} onSelect={onSelect} /></td>}
                  </>
                )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function HappyCleaningAssignmentContent({ data, mutate, refresh, realtimeSync }) {
  const [selectedId, setSelectedId] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [neighborhood, setNeighborhood] = useState([]);
  const [restoreFocus, setRestoreFocus] = useState(false);
  const toastManager = useToastManager();
  const searchRef = useRef(null);
  const selected = data.children.find(child => child.id === selectedId) || null;
  const mobile = useMobileViewport();
  const writeBlocked = Boolean(realtimeSync?.enabled && !realtimeSync.writesEnabled);
  const writeBusy = busy || writeBlocked;
  const setSelected = child => setSelectedId(child.id);
  useEffect(() => {
    if (restoreFocus && selectedId === null) {
      searchRef.current?.focus();
      setRestoreFocus(false);
    }
  }, [restoreFocus, selectedId]);
  const saveNumber = async number => {
    setBusy(true);
    setError('');
    setNeighborhood([]);
    try {
      const result = await mutate(`/api/happy-cleaning/children/${selected.id}/number/`, {
        request_id: requestId(),
        number,
        expected_version: selected.number_version,
      });
      if (result?.ok === false) {
        const replayedError = new Error(result.code);
        replayedError.payload = result;
        throw replayedError;
      }
    } catch (caught) {
      if (caught?.payload?.code === 'duplicate_number') {
        setError(`Nummer ${number} ist bereits vergeben.`);
        setNeighborhood(caught.payload.neighborhood || []);
      } else {
        if (caught?.payload?.code === 'stale') await refresh?.({ preserveData: true });
        setError(caught?.payload?.code === 'stale'
          ? 'Die Daten wurden inzwischen geändert. Bitte erneut versuchen.'
          : 'Die Nummer konnte nicht gespeichert werden.');
      }
    } finally {
      setBusy(false);
    }
  };
  const placeChild = async station => {
    const moving = Boolean(selected.assigned_station);
    if (moving && !window.confirm(
      `${selected.full_name} von ${selected.assigned_station.name} nach ${station.name} verschieben?`,
    )) return;
    setBusy(true);
    setError('');
    try {
      const url = moving
        ? station.is_excused
          ? `/api/happy-cleaning/events/${data.event.id}/assignments/${selected.id}/excuse/`
          : `/api/happy-cleaning/events/${data.event.id}/assignments/${selected.id}/move/`
        : station.is_excused
          ? `/api/happy-cleaning/events/${data.event.id}/assignments/excuse/`
          : `/api/happy-cleaning/events/${data.event.id}/assignments/assign/`;
      const payload = moving
        ? station.is_excused
          ? { request_id: requestId(), expected_version: selected.assignment_version }
          : { request_id: requestId(), station_id: station.id, expected_version: selected.assignment_version }
        : station.is_excused
          ? { request_id: requestId(), child_id: selected.id }
          : { request_id: requestId(), child_id: selected.id, station_id: station.id };
      const result = await mutate(url, payload);
      if (result?.ok === false) {
        const replayedError = new Error(result.code);
        replayedError.payload = result;
        throw replayedError;
      }
      toastManager.add({
        description: station.is_excused
          ? moving
            ? `${selected.full_name} wurde nach Entschuldigt verschoben.`
            : `${selected.full_name} wurde als Entschuldigt eingeteilt.`
          : moving
            ? `${selected.full_name} wurde nach ${station.name} verschoben.`
            : `${selected.full_name} wurde ${station.name} zugeteilt.`,
        type: 'success',
      });
      setSelectedId(null);
      setRestoreFocus(true);
    } catch (caught) {
      if (caught?.payload?.code === 'station_full' || caught?.payload?.code === 'stale') {
        await refresh?.({ preserveData: true });
      }
      setError(caught?.payload?.code === 'station_full'
        ? `${station.name} ist inzwischen voll. Die Einteilung wurde aktualisiert.`
        : 'Die Einteilung konnte nicht gespeichert werden. Bitte erneut versuchen.');
    } finally {
      setBusy(false);
    }
  };
  return (
    <main className="happy-cleaning-page happy-cleaning-assignment" id="body-container">
      <div className="happy-cleaning-assignment-controls">
        <div className="happy-cleaning-assignment-searchbar">
          <UnassignedCounter
            summary={data.summary}
            children={data.children}
            onSelect={setSelected}
            batchAction={(
              <HappyCleaningNumberBatchAction
                eventId={data.event.id}
                numberBatch={data.number_batch}
                mutate={mutate}
                refresh={refresh}
                disabled={writeBusy}
              />
            )}
          />
          <ChildSearch key={selectedId || 'empty'} children={data.children} selected={selected} onSelect={setSelected} inputRef={searchRef} />
        </div>
        {selected
          ? <ChildDetails child={selected} busy={writeBusy} onNumber={saveNumber} />
          : <PlaceholderChildDetails />}
      </div>
      {error && neighborhood.length === 0 && <p className="error" role="alert">{error}</p>}
      {neighborhood.length > 0 && (
        <DuplicateNumberDialog
          error={error}
          neighborhood={neighborhood}
          busy={writeBusy}
          onSelect={saveNumber}
          onClose={() => {
            setError('');
            setNeighborhood([]);
          }}
        />
      )}
      <DesktopStations
        eventId={data.event.id}
        stations={data.stations}
        selected={selected}
        busy={writeBusy}
        onActivate={placeChild}
        onSelect={setSelected}
        mobile={mobile}
      />
    </main>
  );
}

export function HappyCleaningAssignmentPage(props) {
  return <HappyCleaningAssignmentContent {...props} />;
}
