import { useEffect, useMemo, useRef, useState } from 'react';
import { Dialog } from '@base-ui/react/dialog';
import { Eye, EyeOff, Pencil, X } from 'lucide-react';

import { Card } from '../components';
import { Button } from '../components/ui/button';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
  TableScroll,
} from '../components/ui/table';
import { useErrorToast, useToastManager } from '../components/ui/toast';
import { useIsMobile } from '../hooks/use-mobile';


const requestId = () => globalThis.crypto?.randomUUID?.()
  || `happy-cleaning-${Date.now()}-${Math.random().toString(36).slice(2)}`;

const dialogBackdropClass = 'fixed inset-0 z-[var(--z-modal)] bg-black/[.45]';
const dialogViewportClass = 'fixed inset-0 z-[calc(var(--z-modal)+1)] grid place-items-center p-4';
const dialogPopupClass = 'relative max-h-[calc(100dvh-2rem)] w-full max-w-[37.5rem] overflow-y-auto rounded-lg bg-surface-solid p-6 shadow-xl';
const dialogCloseClass = 'absolute right-2 top-2';

function presenceLabel(child) {
  if (child.present) return 'Anwesend';
  return child.absence_location
    ? `Abwesend · ${child.absence_location}`
    : 'Abwesend';
}

function PlaceholderChildDetails() {
  return (
    <div className="min-w-0" role="region" aria-label="Platzhalter Kind">
      <Card title="Carlos" className="m-0 w-full min-w-0">
        <dl className="grid gap-2">
          <div className="min-w-0"><dt className="font-semibold">Nummer</dt><dd className="m-0 wrap-anywhere">∞</dd></div>
          <div className="min-w-0"><dt className="font-semibold">Station</dt><dd className="m-0 wrap-anywhere">überall und nirgends</dd></div>
        </dl>
      </Card>
    </div>
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
    <form className="flex flex-wrap items-stretch gap-1" onSubmit={event => {
      event.preventDefault();
      onNumber(Number(number));
    }}>
      <input
        className="w-[3.125rem] min-w-0 flex-none rounded-lg border-2 border-white bg-white p-1"
        type="number"
        min="1"
        required
        aria-label={`Happy Cleaning Nummer für ${child.full_name}`}
        disabled={busy}
        value={number}
        onChange={event => setNumber(event.target.value)}
      />
      <Button type="submit" disabled={busy}>
        {child.number === null ? 'Nummer speichern' : 'Nummer aktualisieren'}
      </Button>
      {child.number !== null && (
        <Button
          variant="secondary"
          type="button"
          disabled={busy}
          onClick={() => {
            setNumber(String(child.number));
            setEditingNumber(false);
          }}
        >
          Abbrechen
        </Button>
      )}
    </form>
  );
  return (
    <div className="min-w-0" role="region" aria-label="Ausgewähltes Kind">
      <Card title={`${child.full_name}${!child.present ? ' ❌' : ''}`} className="m-0 w-full min-w-0">
        <dl className="grid gap-2">
          <div className="min-w-0">
            <dt className="font-semibold">Nummer</dt>
            <dd className="m-0 wrap-anywhere">
              {editingNumber
                ? numberForm
                : (
                  <span className="inline-flex items-center gap-1">
                    {child.number}
                    <Button
                      variant="ghost"
                      size="icon-sm"
                      type="button"
                      aria-label={`Nummer für ${child.full_name} bearbeiten`}
                      title="Nummer bearbeiten"
                      onClick={() => setEditingNumber(true)}
                    >
                      <Pencil size={18} aria-hidden="true" />
                    </Button>
                  </span>
                )}
            </dd>
          </div>
          <div className="min-w-0">
            <dt className="font-semibold">Station</dt>
            <dd className="m-0 wrap-anywhere">
              {child.assigned_station?.name
                || (child.number === null
                  ? 'Kann erst eingeteilt werden, wenn eine Nummer eingetragen wurde'
                  : 'Auf den Stationsnamen in der Liste klicken zum einteilen')}
            </dd>
          </div>
        </dl>
      </Card>
    </div>
  );
}

function DuplicateNumberDialog({ error, neighborhood, busy, onSelect, onClose }) {
  return (
    <Dialog.Root open onOpenChange={open => { if (!open) onClose(); }}>
      <Dialog.Portal>
        <Dialog.Backdrop className={dialogBackdropClass} />
        <Dialog.Viewport className={dialogViewportClass}>
          <Dialog.Popup className={dialogPopupClass}>
            <Dialog.Title className="mr-10 text-xl font-semibold">{error}</Dialog.Title>
            <Dialog.Description>
              Klicke auf eine freie Zahl zum zuweisen
            </Dialog.Description>
            <Dialog.Close
              className={dialogCloseClass}
              render={<Button variant="ghost" size="icon" />}
              aria-label="Dialog schließen"
            >
              <X size={20} aria-hidden="true" />
            </Dialog.Close>
            <ul className="mt-4 grid list-none gap-1 p-0" aria-label="Freie Nummer auswählen">
              {neighborhood.map(item => (
                <li key={item.number}>
                  {item.free
                    ? (
                      <Button
                        className="grid h-auto w-full grid-cols-[minmax(3rem,auto)_minmax(0,1fr)] justify-normal gap-2 p-2 text-left"
                        variant="secondary"
                        type="button"
                        disabled={busy}
                        aria-label={`${item.number} als Nummer zuweisen`}
                        onClick={() => onSelect(item.number)}
                      >
                        <strong>{item.number}</strong>
                        <span>frei</span>
                      </Button>
                    )
                    : (
                      <span className="grid w-full grid-cols-[minmax(3rem,auto)_minmax(0,1fr)] items-center gap-2 rounded-lg bg-black/8 p-2 text-left text-black/65">
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
  designSystem = false,
}) {
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const showError = useErrorToast();
  if (!numberBatch?.available) return null;

  const assignments = numberBatch.children.map(child => ({
    child_id: child.id,
    number: child.number,
    expected_version: child.expected_version,
  }));
  const confirm = async () => {
    setBusy(true);
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
      showError(code === 'stale'
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
    setOpen(nextOpen);
  };

  return (
    <Dialog.Root open={open} onOpenChange={changeOpen}>
      {designSystem
        ? (
          <Dialog.Trigger
            render={<Button className="h-auto max-w-full py-2 text-center whitespace-normal" variant="secondary" />}
            disabled={disabled}
          >
            Kindern ohne Nummern, Nummern zuteilen
          </Dialog.Trigger>
        )
        : (
          <Dialog.Trigger
            className="button happy-cleaning-batch-trigger"
            disabled={disabled}
          >
            Kindern ohne Nummern, Nummern zuteilen
          </Dialog.Trigger>
        )}
      <Dialog.Portal>
        <Dialog.Backdrop className={designSystem ? dialogBackdropClass : 'happy-cleaning-dialog-backdrop'} />
        <Dialog.Viewport className={designSystem ? dialogViewportClass : 'happy-cleaning-dialog-viewport'}>
          <Dialog.Popup className={designSystem ? dialogPopupClass : 'card happy-cleaning-number-dialog happy-cleaning-batch-dialog'}>
            <Dialog.Title className={designSystem ? 'mr-10 text-xl font-semibold' : undefined}>Nummern zuteilen</Dialog.Title>
            <Dialog.Description>
              Die vorgeschlagenen Nummern werden gemeinsam zugeteilt.
            </Dialog.Description>
            {designSystem
              ? (
                <Dialog.Close
                  className={dialogCloseClass}
                  render={<Button variant="ghost" size="icon" />}
                  aria-label="Dialog schließen"
                  disabled={busy}
                >
                  <X size={20} aria-hidden="true" />
                </Dialog.Close>
              )
              : (
                <Dialog.Close className="happy-cleaning-dialog-close" aria-label="Dialog schließen" disabled={busy}>
                  <X size={20} aria-hidden="true" />
                </Dialog.Close>
              )}
            <ul
              className={designSystem ? 'my-4 grid list-none gap-1 p-0' : 'happy-cleaning-batch-list'}
              aria-label="Vorgeschlagene Nummern"
            >
              {numberBatch.children.map(child => (
                <li
                  className={designSystem ? 'grid grid-cols-[minmax(0,1fr)_auto] items-center gap-2 rounded-lg bg-white/55 p-2' : undefined}
                  key={child.id}
                >
                  <span>{child.full_name}</span>
                  <strong className={designSystem ? 'min-w-[2ch] text-right tabular-nums' : undefined}>{child.number}</strong>
                </li>
              ))}
            </ul>
            <div
              className={designSystem ? 'mt-4 flex flex-wrap justify-end gap-2' : 'happy-cleaning-batch-actions'}
              role="group"
              aria-label="Dialogaktionen"
            >
              {designSystem
                ? <Dialog.Close render={<Button variant="secondary" />} disabled={busy}>Abbrechen</Dialog.Close>
                : <Dialog.Close className="button" disabled={busy}>Abbrechen</Dialog.Close>}
              {designSystem
                ? (
                  <Button type="button" disabled={busy || disabled} onClick={confirm}>
                    {busy ? 'Wird zugeteilt…' : 'Bestätigen'}
                  </Button>
                )
                : (
                  <button className="button" type="button" disabled={busy || disabled} onClick={confirm}>
                    {busy ? 'Wird zugeteilt…' : 'Bestätigen'}
                  </button>
                )}
            </div>
          </Dialog.Popup>
        </Dialog.Viewport>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

function ChildSearch({ children, selected, onSelect, inputRef }) {
  const mobile = useIsMobile();
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
    <div className="relative w-full min-w-0">
      <label className="sr-only" htmlFor="happy-cleaning-child-search">Kind suchen</label>
      <input
        className="w-full rounded-lg border-2 border-white bg-white p-2 text-foreground"
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
        <div
          id="happy-cleaning-child-results"
          className="absolute inset-x-0 top-[calc(100%+0.25rem)] z-[calc(var(--z-table-header)+1)] max-h-[min(60vh,28rem)] overflow-y-auto rounded-lg bg-white shadow-lg"
          role="listbox"
        >
          {results.map((child, index) => (
            <Button
              id={`happy-cleaning-child-${child.id}`}
              className={`grid h-auto w-full rounded-none border-b border-black/10 px-2 py-2 text-left whitespace-normal max-[900px]:block ${
                index === activeIndex ? 'bg-secondary' : 'bg-white'
              } min-[901px]:grid-cols-[minmax(10rem,1fr)_minmax(20rem,2fr)]`}
              variant="ghost"
              type="button"
              role="option"
              aria-selected={index === activeIndex}
              key={child.id}
              onClick={() => choose(child)}
            >
              <strong>{child.full_name}</strong>
              {!mobile && (
                <span className="grid grid-cols-3 gap-2">
                  <span>#{child.number ?? '—'}</span>
                  <span>{child.assigned_station?.name || 'Nicht eingeteilt'}</span>
                  <span>{presenceLabel(child)}</span>
                </span>
              )}
            </Button>
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
    <div className="flex flex-wrap items-center gap-1" role="group" aria-label="Einteilungsaktionen">
      <span className="rounded-lg bg-surface-header px-2 py-[.45rem] font-medium">{count}</span>
      <Dialog.Root open={open} onOpenChange={setOpen}>
        <Dialog.Trigger render={<Button variant="secondary" />}>
          Nicht eingeteilte Kinder anzeigen
        </Dialog.Trigger>
        <Dialog.Portal>
          <Dialog.Backdrop className={dialogBackdropClass} />
          <Dialog.Viewport className={dialogViewportClass}>
            <Dialog.Popup className={dialogPopupClass}>
              <Dialog.Title className="mr-10 text-xl font-semibold">Anwesende nicht eingeteilte Kinder</Dialog.Title>
              <Dialog.Close
                className={dialogCloseClass}
                render={<Button variant="ghost" size="icon" />}
                aria-label="Dialog schließen"
              >
                <X size={20} aria-hidden="true" />
              </Dialog.Close>
              <ul className="mt-4 grid list-none gap-1 p-0" aria-label="Anwesende nicht eingeteilte Kinder">
                {unassigned.map(child => (
                  <li key={child.id}>
                    <Button
                      className="w-full justify-start"
                      variant="secondary"
                      type="button"
                      aria-label={`${child.full_name} auswählen`}
                      onClick={() => { onSelect(child); setOpen(false); }}
                    >
                      {child.full_name}
                    </Button>
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

function StationName({ station, selected, busy, onActivate }) {
  const full = !station.is_excused && station.free_seats === 0;
  const label = `${station.name}${full ? ' 🚫' : ''}`;
  if (!selected) {
    return <span>{label}</span>;
  }
  const currentTarget = selected.assigned_station?.id === station.id;
  const fullTarget = full && !currentTarget;
  return (
    <Button
      className="h-auto justify-start p-0 text-left whitespace-normal"
      variant="ghost"
      type="button"
      aria-label={`${selected.full_name} ${station.name} zuweisen`}
      disabled={busy || (!station.is_excused && selected.number === null) || fullTarget || currentTarget}
      onClick={() => onActivate(station)}
    >
      {label}
    </Button>
  );
}

function ChildPills({ station, onSelect, hidden = false }) {
  return (
    <div
      className="flex flex-wrap gap-1"
      role="group"
      aria-label="Eingeteilte Kinder"
      aria-hidden={hidden}
      hidden={hidden}
    >
      {station.children.map(child => (
        <Button
          className="h-auto rounded-full border border-current px-2 py-[.2rem]"
          variant="secondary"
          type="button"
          aria-label={`${child.full_name} auswählen`}
          title={`${child.full_name} #${child.number ?? '—'}`}
          onClick={() => onSelect(child)}
          key={child.id}
        >
          {child.short_name}{!child.present && ' ❌'}
        </Button>
      ))}
    </div>
  );
}

const progress = station => station.todo_progress_percentage === null
  ? '—'
  : `${station.todo_progress_percentage}%`;

const places = station => station.overbooked_count > 0
  ? `${station.overbooked_count} überbelegt`
  : `${station.free_seats} / ${station.max_kids} frei`;

function StationDetailsDialog({ station, onSelect }) {
  const [open, setOpen] = useState(false);
  return (
    <Dialog.Root open={open} onOpenChange={setOpen}>
      <Dialog.Trigger
        render={<Button variant="ghost" size="icon" />}
        aria-label={`Details zu ${station.name} anzeigen`}
        title={`Details zu ${station.name} anzeigen`}
      >
        <Eye size={20} aria-hidden="true" />
      </Dialog.Trigger>
      <Dialog.Portal>
        <Dialog.Backdrop className={dialogBackdropClass} />
        <Dialog.Viewport className={dialogViewportClass}>
          <Dialog.Popup className={dialogPopupClass}>
            <Dialog.Title className="mr-10 text-xl font-semibold">{station.name}</Dialog.Title>
            <Dialog.Close
              className={dialogCloseClass}
              render={<Button variant="ghost" size="icon" />}
              aria-label="Dialog schließen"
            >
              <X size={20} aria-hidden="true" />
            </Dialog.Close>
            <dl className="grid gap-2">
              <div><dt className="font-semibold">Wünsche</dt><dd className="m-0 wrap-anywhere">{station.wishes || '—'}</dd></div>
              <div><dt className="font-semibold">Treffpunkt</dt><dd className="m-0 wrap-anywhere">{station.meeting_point}</dd></div>
              <div><dt className="font-semibold">Verantwortlich</dt><dd className="m-0 wrap-anywhere">{station.responsible?.name || '—'}</dd></div>
              <div><dt className="font-semibold">Plätze</dt><dd className="m-0 wrap-anywhere">{places(station)}</dd></div>
              <div><dt className="font-semibold">Aufgaben</dt><dd className="m-0 wrap-anywhere">{progress(station)}</dd></div>
              <div>
                <dt className="font-semibold">Kinder</dt>
                <dd className="m-0 wrap-anywhere">
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

function StationsTable({ stations, selected, busy, onActivate, onSelect, mobile }) {
  const [childrenVisible, setChildrenVisible] = useState(true);
  const toggleLabel = childrenVisible ? 'Kindernamen verbergen' : 'Kindernamen anzeigen';
  return (
    <TableScroll
      className="rounded-lg"
      role="region"
      aria-label="Happy Cleaning Stationstabelle"
      tabIndex={0}
    >
      <Table aria-label="Happy Cleaning Stationen">
        <TableHeader>
          <TableRow>
            <TableHead scope="col">{mobile ? 'SWP' : 'Station'}</TableHead>
            <TableHead scope="col" data-priority="low">Wünsche</TableHead>
            <TableHead scope="col" data-priority="low">Treffpunkt</TableHead>
            <TableHead scope="col" data-priority="low">Verantwortlich</TableHead>
            <TableHead scope="col">Plätze</TableHead>
            <TableHead scope="col" data-priority="low">Aufgaben</TableHead>
            <TableHead scope="col" data-priority="low">
              <div className="inline-flex items-center gap-1">
              <span>Kinder</span>
              <Button
                variant="ghost"
                size="icon-sm"
                type="button"
                aria-label={toggleLabel}
                title={toggleLabel}
                onClick={() => setChildrenVisible(value => !value)}
              >
                {childrenVisible ? <Eye size={20} /> : <EyeOff size={20} />}
              </Button>
              </div>
            </TableHead>
            {mobile && <TableHead scope="col"><span className="sr-only">Details</span></TableHead>}
          </TableRow>
        </TableHeader>
        <TableBody>
          {stations.map(station => (
            <TableRow className={station.is_excused ? 'bg-white/20' : ''} key={station.id}>
              <TableHead scope="row">
                <StationName station={station} selected={selected} busy={busy} onActivate={onActivate} />
              </TableHead>
              {station.is_excused
                ? (
                  <TableCell className="min-w-0" colSpan={mobile ? 7 : 6}>
                    {!childrenVisible && (
                      <span
                        className="font-medium tabular-nums"
                        aria-label={`${station.children.length} ${station.children.length === 1 ? 'eingeteiltes Kind' : 'eingeteilte Kinder'}`}
                      >
                        {station.children.length}
                      </span>
                    )}
                    <ChildPills station={station} onSelect={onSelect} hidden={!childrenVisible} />
                  </TableCell>
                )
                : (
                  <>
                    <TableCell data-priority="low">{station.wishes || '—'}</TableCell>
                    <TableCell data-priority="low">{station.meeting_point}</TableCell>
                    <TableCell data-priority="low">{station.responsible?.name || '—'}</TableCell>
                    <TableCell>{places(station)}</TableCell>
                    <TableCell data-priority="low">{progress(station)}</TableCell>
                    <TableCell data-priority="low">
                      {!childrenVisible && (
                        <span
                          className="font-medium tabular-nums"
                          aria-label={`${station.children.length} ${station.children.length === 1 ? 'eingeteiltes Kind' : 'eingeteilte Kinder'}`}
                        >
                          {station.children.length}
                        </span>
                      )}
                      <ChildPills station={station} onSelect={onSelect} hidden={!childrenVisible} />
                    </TableCell>
                    {mobile && (
                      <TableCell className="w-px text-center whitespace-nowrap">
                        <StationDetailsDialog station={station} onSelect={onSelect} />
                      </TableCell>
                    )}
                  </>
                )}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableScroll>
  );
}

function HappyCleaningAssignmentContent({ data, mutate, refresh, realtimeSync }) {
  const [selectedId, setSelectedId] = useState(null);
  const [busy, setBusy] = useState(false);
  const [duplicateError, setDuplicateError] = useState('');
  const [neighborhood, setNeighborhood] = useState([]);
  const [restoreFocus, setRestoreFocus] = useState(false);
  const toastManager = useToastManager();
  const showError = useErrorToast();
  const searchRef = useRef(null);
  const selected = data.children.find(child => child.id === selectedId) || null;
  const mobile = useIsMobile();
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
    setDuplicateError('');
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
        setDuplicateError(`Nummer ${number} ist bereits vergeben.`);
        setNeighborhood(caught.payload.neighborhood || []);
      } else {
        if (caught?.payload?.code === 'stale') await refresh?.({ preserveData: true });
        showError(caught?.payload?.code === 'stale'
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
      showError(caught?.payload?.code === 'station_full'
        ? `${station.name} ist inzwischen voll. Die Einteilung wurde aktualisiert.`
        : 'Die Einteilung konnte nicht gespeichert werden. Bitte erneut versuchen.');
    } finally {
      setBusy(false);
    }
  };
  return (
    <main className="mx-auto block min-h-0 w-full min-w-0 max-w-[96rem] p-2" id="body-container">
      <div
        className="my-8 grid w-full min-w-0 items-start gap-2 min-[901px]:grid-cols-2"
        role="group"
        aria-label="Kind auswählen und bearbeiten"
      >
        <div className="relative z-[calc(var(--z-table-header)+1)] grid w-full min-w-0 gap-1">
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
                designSystem
              />
            )}
          />
          <ChildSearch key={selectedId || 'empty'} children={data.children} selected={selected} onSelect={setSelected} inputRef={searchRef} />
        </div>
        {selected
          ? <ChildDetails child={selected} busy={writeBusy} onNumber={saveNumber} />
          : <PlaceholderChildDetails />}
      </div>
      {neighborhood.length > 0 && (
        <DuplicateNumberDialog
          error={duplicateError}
          neighborhood={neighborhood}
          busy={writeBusy}
          onSelect={saveNumber}
          onClose={() => {
            setDuplicateError('');
            setNeighborhood([]);
          }}
        />
      )}
      <StationsTable
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
