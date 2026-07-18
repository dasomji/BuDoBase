import { useEffect, useMemo, useRef, useState } from 'react';


const requestId = () => globalThis.crypto?.randomUUID?.()
  || `happy-cleaning-${Date.now()}-${Math.random().toString(36).slice(2)}`;

function useMobileViewport() {
  const media = globalThis.matchMedia?.('(max-width: 759px)');
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

function ChildDetails({ child, busy, onNumber }) {
  const [number, setNumber] = useState(child.number === null ? '' : String(child.number));
  useEffect(() => {
    setNumber(child.number === null ? '' : String(child.number));
  }, [child.id, child.number]);
  return (
    <section className="card happy-cleaning-selected-child" aria-label="Ausgewähltes Kind">
      <h2>{child.full_name}</h2>
      <dl>
        <div><dt>Nummer</dt><dd>{child.number ?? 'Noch keine Nummer'}</dd></div>
        <div><dt>Station</dt><dd>{child.assigned_station?.name || 'Nicht eingeteilt'}</dd></div>
        <div><dt>Anwesenheit</dt><dd>{presenceLabel(child)}</dd></div>
      </dl>
      {child.number === null && (
        <p>Vor der Einteilung braucht {child.full_name} eine Nummer.</p>
      )}
      <form className="happy-cleaning-number-form" onSubmit={event => {
        event.preventDefault();
        onNumber(Number(number));
      }}>
        <label>
          Happy Cleaning Nummer für {child.full_name}
          <input type="number" min="1" required disabled={busy} value={number} onChange={event => setNumber(event.target.value)} />
        </label>
        <button className="button" type="submit" disabled={busy}>Nummer speichern</button>
      </form>
    </section>
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
                  <span>Nummer {child.number ?? '—'}</span>
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

function UnassignedCounter({ summary, children, onSelect }) {
  const [open, setOpen] = useState(false);
  const unassigned = children.filter(child => child.present && !child.assigned_station);
  const label = `${summary.assigned_present} von ${summary.present_total} anwesenden Kindern eingeteilt`;
  return (
    <div className="happy-cleaning-unassigned">
      <button
        className="button happy-cleaning-counter"
        type="button"
        aria-label={label}
        aria-expanded={open}
        onClick={() => setOpen(value => !value)}
      >
        {summary.assigned_present} / {summary.present_total}
      </button>
      {open && (
        <ul className="card" aria-label="Anwesende nicht eingeteilte Kinder">
          {unassigned.map(child => (
            <li key={child.id}>
              <button type="button" aria-label={`${child.full_name} auswählen`} onClick={() => { onSelect(child); setOpen(false); }}>
                {child.full_name}
              </button>
            </li>
          ))}
          {!unassigned.length && <li>Alle anwesenden Kinder sind eingeteilt.</li>}
        </ul>
      )}
    </div>
  );
}

function StationName({ eventId, station, selected, busy, onActivate }) {
  if (!selected) {
    return <a href={`/happy-cleaning/${eventId}/stations/${station.id}/`}>{station.name}</a>;
  }
  const full = station.free_seats === 0 && selected.assigned_station?.id !== station.id;
  return (
    <button
      type="button"
      aria-label={`${selected.full_name} ${station.name} zuweisen`}
      disabled={busy || selected.number === null || full || selected.assigned_station?.id === station.id}
      onClick={() => onActivate(station)}
    >
      {station.name}{full && ' 🚫'}
    </button>
  );
}

function ChildPills({ station, busy, onRemove }) {
  return (
    <div className="happy-cleaning-child-pills">
      {station.children.map(child => (
        <button
          className="happy-cleaning-child-pill"
          type="button"
          aria-label={`${child.full_name} aus ${station.name} entfernen`}
          title={child.full_name}
          disabled={busy}
          onClick={() => onRemove(child, station)}
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

function DesktopStations({ eventId, stations, selected, busy, onActivate, onRemove }) {
  return (
    <div className="happy-cleaning-assignment-table-wrap">
      <table aria-label="Happy Cleaning Stationen">
        <thead><tr>
          <th>Station</th><th>Wünsche</th><th>Treffpunkt</th><th>Verantwortlich</th>
          <th>Plätze</th><th>Aufgaben</th><th>Kinder</th>
        </tr></thead>
        <tbody>
          {stations.map(station => (
            <tr key={station.id}>
              <th scope="row"><StationName eventId={eventId} station={station} selected={selected} busy={busy} onActivate={onActivate} /></th>
              <td>{station.wishes || '—'}</td>
              <td>{station.meeting_point}</td>
              <td>{station.responsible?.name || '—'}</td>
              <td>{station.free_seats} / {station.max_kids} frei</td>
              <td>{progress(station)}</td>
              <td><ChildPills station={station} busy={busy} onRemove={onRemove} /></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function MobileStations({ eventId, stations, selected, busy, onActivate, onRemove }) {
  return (
    <div className="happy-cleaning-assignment-cards">
      {stations.map(station => (
        <article className="card happy-cleaning-assignment-card" aria-label={`Station ${station.name}`} key={station.id}>
          <h2><StationName eventId={eventId} station={station} selected={selected} busy={busy} onActivate={onActivate} /></h2>
          <dl>
            <div><dt>Wünsche</dt><dd>{station.wishes || '—'}</dd></div>
            <div><dt>Treffpunkt</dt><dd>{station.meeting_point}</dd></div>
            <div><dt>Verantwortlich</dt><dd>{station.responsible?.name || '—'}</dd></div>
            <div><dt>Plätze</dt><dd>{station.free_seats} / {station.max_kids} frei</dd></div>
            <div><dt>Aufgaben</dt><dd>{progress(station)}</dd></div>
          </dl>
          <ChildPills station={station} busy={busy} onRemove={onRemove} />
        </article>
      ))}
    </div>
  );
}

export function HappyCleaningAssignmentPage({ data, mutate, refresh, realtimeSync }) {
  const [selectedId, setSelectedId] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [neighborhood, setNeighborhood] = useState([]);
  const [requestedNumber, setRequestedNumber] = useState(null);
  const [toast, setToast] = useState('');
  const [restoreFocus, setRestoreFocus] = useState(false);
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
    setRequestedNumber(number);
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
        ? `/api/happy-cleaning/events/${data.event.id}/assignments/${selected.id}/move/`
        : `/api/happy-cleaning/events/${data.event.id}/assignments/assign/`;
      const payload = moving
        ? { request_id: requestId(), station_id: station.id, expected_version: selected.assignment_version }
        : { request_id: requestId(), child_id: selected.id, station_id: station.id };
      const result = await mutate(url, payload);
      if (result?.ok === false) {
        const replayedError = new Error(result.code);
        replayedError.payload = result;
        throw replayedError;
      }
      setToast(moving
        ? `${selected.full_name} wurde nach ${station.name} verschoben.`
        : `${selected.full_name} wurde ${station.name} zugeteilt.`);
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
  const removeChild = async (child, station) => {
    if (!window.confirm(`${child.full_name} aus ${station.name} entfernen?`)) return;
    setBusy(true);
    setError('');
    try {
      const result = await mutate(`/api/happy-cleaning/events/${data.event.id}/assignments/${child.id}/remove/`, {
        request_id: requestId(),
        expected_version: child.assignment_version,
      });
      if (result?.ok === false) {
        const replayedError = new Error(result.code);
        replayedError.payload = result;
        throw replayedError;
      }
      setToast(`${child.full_name} wurde aus ${station.name} entfernt.`);
      setSelectedId(null);
      setRestoreFocus(true);
    } catch (caught) {
      if (caught?.payload?.code === 'stale') await refresh?.({ preserveData: true });
      setSelectedId(child.id);
      setError('Die Entfernung konnte nicht gespeichert werden. Bitte erneut versuchen.');
    } finally {
      setBusy(false);
    }
  };
  return (
    <main className="happy-cleaning-page happy-cleaning-assignment" id="body-container">
      <div className="happy-cleaning-assignment-searchbar">
        <UnassignedCounter summary={data.summary} children={data.children} onSelect={setSelected} />
        <ChildSearch key={selectedId || 'empty'} children={data.children} selected={selected} onSelect={setSelected} inputRef={searchRef} />
      </div>
      {toast && <p className="happy-cleaning-toast" role="status">{toast}</p>}
      {error && <p className="error" role="alert">{error}</p>}
      {selected && <ChildDetails child={selected} busy={writeBusy} onNumber={saveNumber} />}
      {neighborhood.length > 0 && (
        <ul className="happy-cleaning-number-neighborhood" aria-label={`Nummern rund um ${requestedNumber}`}>
          {neighborhood.map(item => (
            <li key={item.number}>
              <strong>{item.number}</strong> {item.free ? 'frei' : item.child?.display_name}
            </li>
          ))}
        </ul>
      )}
      {mobile
        ? <MobileStations eventId={data.event.id} stations={data.stations} selected={selected} busy={writeBusy} onActivate={placeChild} onRemove={removeChild} />
        : <DesktopStations eventId={data.event.id} stations={data.stations} selected={selected} busy={writeBusy} onActivate={placeChild} onRemove={removeChild} />}
    </main>
  );
}
