import { useEffect, useId, useMemo, useRef, useState } from 'react';
import { Dialog } from '@base-ui/react/dialog';
import {
  AlertTriangle,
  CalendarDays,
  Check,
  ChevronLeft,
  ChevronRight,
  Clock3,
  PencilIcon,
  Plus,
  Search,
  ShieldCheck,
  UserPlus,
  X,
} from 'lucide-react';

import { Columns } from '../components';
import { Button } from '../components/ui/button';
import { Input, NativeSelect } from '../components/ui/input';
import { useErrorToast, useSuccessToast } from '../components/ui/toast';
import { PersonCard, ProfileForm } from './profiles';

function initials(name) {
  return name
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map(part => part[0]?.toLocaleUpperCase('de'))
    .join('');
}

function parseContractDate(value) {
  return value ? new Date(`${value}T00:00:00Z`) : null;
}

function formatDateRange(startValue, endValue) {
  const start = parseContractDate(startValue);
  const end = parseContractDate(endValue);
  if (!start || Number.isNaN(start.valueOf())) return '';
  const resolvedEnd = end && !Number.isNaN(end.valueOf()) ? end : start;
  const startDay = String(start.getUTCDate()).padStart(2, '0');
  const endDay = String(resolvedEnd.getUTCDate()).padStart(2, '0');
  const startMonth = new Intl.DateTimeFormat('de-AT', { month: 'long', timeZone: 'UTC' }).format(start);
  const endMonth = new Intl.DateTimeFormat('de-AT', { month: 'long', timeZone: 'UTC' }).format(resolvedEnd);
  const startYear = start.getUTCFullYear();
  const endYear = resolvedEnd.getUTCFullYear();
  if (startMonth === endMonth && startYear === endYear) {
    return `${startDay}.–${endDay}. ${endMonth} ${endYear}`;
  }
  return `${startDay}. ${startMonth} ${startYear}–${endDay}. ${endMonth} ${endYear}`;
}

const foodDisplays = {
  ft: '🥩 Flexitarisch',
  vt: '🧀 Vegetarisch',
  vn: '🌱 Vegan',
};

const requestLabels = {
  pending: 'Anfrage ausstehend',
  rejected: 'Anfrage abgelehnt',
  cancelled: 'Anfrage storniert',
  superseded: 'Anfrage ersetzt',
};

function initialTurnusId(years = []) {
  const turnuses = years.flatMap(year => year.turnuses || []);
  return turnuses.find(turnus => turnus.is_member)?.id ?? turnuses[0]?.id ?? null;
}

function Member({ member, mutate, onChanged, canManageLeitung, canManageMemberships, canEditProfiles, token }) {
  const [busy, setBusy] = useState(false);
  const [editing, setEditing] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const showError = useErrorToast();
  const showSuccess = useSuccessToast();
  const isLead = member.functional_role === 'leitung';

  const changeRole = async () => {
    const functionalRole = isLead ? 'teamer' : 'leitung';
    setBusy(true);
    try {
      await mutate(`/api/admin/memberships/${member.id}/role/`, { functional_role: functionalRole });
      onChanged(member, { functional_role: functionalRole });
      showSuccess(isLead ? `${member.name} ist jetzt Teamer.` : `${member.name} ist jetzt Leitung.`);
    } catch (error) {
      showError(error.payload?.detail || 'Die Funktionsrolle konnte nicht geändert werden.');
    } finally {
      setBusy(false);
    }
  };

  const remove = async () => {
    setBusy(true);
    try {
      await mutate(`/api/memberships/${member.id}/remove/`, {}, true, true, true);
      onChanged(member, { removed: true });
      showSuccess(`${member.name} wurde aus dem Turnus entfernt.`);
    } catch (error) {
      showError(error.payload?.detail || 'Die Mitgliedschaft konnte nicht entfernt werden.');
    } finally {
      setBusy(false);
    }
  };

  const profileSaved = async (_result, form) => {
    const formData = new FormData(form);
    const food = formData.get('essen');
    const rufname = formData.get('rufname');
    onChanged(member, {
      name: rufname,
      profile: {
        ...member.profile,
        rufname,
        email: formData.get('email'),
        allergies: formData.get('allergien'),
        coffee: formData.get('coffee'),
        food,
        food_display: foodDisplays[food] || '',
        budo_family: formData.get('budo_family'),
        phone: formData.get('telefonnummer'),
      },
    });
    showSuccess(`Das Profil von ${rufname} wurde aktualisiert.`);
  };

  const manageable = canManageLeitung || (canManageMemberships && !isLead);
  const editable = manageable || (canEditProfiles && member.profile);
  return (
    <li className="team-member-tile">
      {member.profile ? (
        <Button
          aria-label={`${member.name} Profil öffnen`}
          className="grid min-w-0 cursor-pointer grid-cols-[auto_minmax(0,1fr)] items-center gap-[0.5625rem] text-left hover:bg-transparent hover:text-inherit"
          type="button"
          variant="full-surface"
          onClick={() => setProfileOpen(true)}
        >
          <span className="team-avatar" aria-hidden="true">{initials(member.name)}</span>
          <span className="team-person-copy">
            <strong>{member.name}</strong>
            <small>{member.role_label}</small>
          </span>
        </Button>
      ) : (
        <span className="grid min-w-0 grid-cols-[auto_minmax(0,1fr)] items-center gap-[0.5625rem]">
          <span className="team-avatar" aria-hidden="true">{initials(member.name)}</span>
          <span className="team-person-copy">
            <strong>{member.name}</strong>
            <small>{member.role_label}</small>
          </span>
        </span>
      )}
      {editable && (
        <Button
          className="team-pencil-action"
          aria-label={`${member.name} bearbeiten`}
          aria-expanded={editing}
          title={`${member.name} bearbeiten`}
          type="button"
          size="icon"
          variant="ghost"
          disabled={busy}
          onClick={() => setEditing(value => !value)}
        >
          <PencilIcon aria-hidden="true" />
        </Button>
      )}
      <Dialog.Root open={profileOpen} onOpenChange={setProfileOpen}>
        {profileOpen && member.profile && (
          <Dialog.Portal>
            <Dialog.Backdrop className="fixed inset-0 z-[var(--z-modal)] bg-black/45" />
            <Dialog.Viewport className="fixed inset-0 z-[var(--z-modal)] grid place-items-center overflow-y-auto p-4">
              <Dialog.Popup className="relative max-h-[calc(100dvh-2rem)] w-full max-w-lg overflow-y-auto">
                <Dialog.Title className="sr-only">Profil von {member.name}</Dialog.Title>
                <Dialog.Close className="absolute top-2 right-2 z-10" render={<Button type="button" variant="ghost" size="icon" />} aria-label="Dialog schließen">
                  <X aria-hidden="true" />
                </Dialog.Close>
                <PersonCard
                  id={`team-profile-${member.profile.id}`}
                  person={member.profile}
                  focuses={member.profile.focuses}
                />
              </Dialog.Popup>
            </Dialog.Viewport>
          </Dialog.Portal>
        )}
      </Dialog.Root>
      <Dialog.Root open={editing} onOpenChange={setEditing}>
        {editing && (
          <Dialog.Portal>
            <Dialog.Backdrop className="fixed inset-0 z-[var(--z-modal)] bg-black/45" />
            <Dialog.Viewport className="fixed inset-0 z-[var(--z-modal)] grid place-items-center overflow-y-auto p-4">
              <Dialog.Popup className="card relative grid max-h-[calc(100dvh-2rem)] w-full max-w-lg gap-4 overflow-y-auto bg-surface-solid p-5">
                <Dialog.Title className="mr-10 text-xl font-semibold">{member.name} bearbeiten</Dialog.Title>
                <Dialog.Close className="absolute top-2 right-2" render={<Button type="button" variant="ghost" size="icon" />} aria-label="Dialog schließen">
                  <X aria-hidden="true" />
                </Dialog.Close>
                {manageable && (
                  <div className="flex flex-wrap gap-2">
                    {canManageLeitung && (
                      <Button
                        aria-label={isLead ? `${member.name} Leitung entfernen` : `${member.name} als Leitung einsetzen`}
                        type="button"
                        variant="outline"
                        disabled={busy}
                        onClick={changeRole}
                      >
                        {!isLead && <Plus aria-hidden="true" />}
                        {isLead ? 'Leitung entfernen' : 'Als Leitung'}
                      </Button>
                    )}
                    <Button aria-label={`${member.name} aus dem Turnus entfernen`} type="button" variant="destructive" disabled={busy} onClick={remove}>Aus Turnus entfernen</Button>
                  </div>
                )}
                {canEditProfiles && member.profile && (
                  <ProfileForm
                    profile={member.profile}
                    token={token}
                    target={`/profil/${member.profile.id}/`}
                    onSuccess={profileSaved}
                  />
                )}
              </Dialog.Popup>
            </Dialog.Viewport>
          </Dialog.Portal>
        )}
      </Dialog.Root>
    </li>
  );
}

function PendingRequest({ request, mutate, onDecided }) {
  const [busy, setBusy] = useState(false);
  const showError = useErrorToast();
  const showSuccess = useSuccessToast();

  const decide = async decision => {
    setBusy(true);
    try {
      const result = await mutate(`/api/join-requests/${request.id}/decision/`, { decision });
      onDecided(request.id, result.approved_member);
      showSuccess(decision === 'approve'
        ? `${request.name} wurde als Teamer aufgenommen.`
        : `Die Anfrage von ${request.name} wurde abgelehnt.`);
    } catch (error) {
      showError(error.payload?.detail || 'Die Beitrittsanfrage konnte nicht bearbeitet werden.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <li className="team-request-row">
      <span className="team-avatar" aria-hidden="true">{initials(request.name)}</span>
      <span className="team-person-copy">
        <strong>{request.name}</strong>
        {request.email && <small>{request.email}</small>}
      </span>
      <span className="team-request-actions">
        <Button type="button" size="icon" variant="ghost" disabled={busy} aria-label={`${request.name} ablehnen`} title={`${request.name} ablehnen`} onClick={() => decide('reject')}><X aria-hidden="true" /></Button>
        <Button type="button" size="icon" variant="success" disabled={busy} aria-label={`${request.name} annehmen`} title={`${request.name} annehmen`} onClick={() => decide('approve')}><Check aria-hidden="true" /></Button>
      </span>
    </li>
  );
}

function PersonDirectory({ people, selectedContext, selectedTurnusId, canManageLeitung, canManageMemberships, addLeitung, addTeamer }) {
  return (
    <div className="team-person-directory">
      {people.length ? (
        <ul aria-label={`Registrierte Personen für ${selectedContext.label}`}>
          {people.map(person => {
            const availableForSelected = selectedContext != null && !(person.turnus_ids || []).includes(selectedTurnusId);
            return (
              <li key={person.id}>
                <span className="team-avatar" aria-hidden="true">{initials(person.name)}</span>
                <span className="team-person-copy">
                  <strong>{person.name}</strong>
                  {person.email && <small>{person.email}</small>}
                  <small>{person.relationships.length ? person.relationships.join(' · ') : 'Keine Teamzugehörigkeiten · verfügbar'}</small>
                </span>
                {availableForSelected && (canManageLeitung || canManageMemberships) && (
                  <span className="team-directory-actions">
                    {canManageMemberships && <Button aria-label={`${person.name} als Betreuer:in zu ${selectedContext.label} hinzufügen`} type="button" variant="outline" onClick={() => addTeamer(person)}><Plus aria-hidden="true" /> Als Betreuer:in</Button>}
                    {canManageLeitung && <Button aria-label={`${person.name} als Leitung zu ${selectedContext.label} hinzufügen`} type="button" variant="outline" onClick={() => addLeitung(person)}><Plus aria-hidden="true" /> Als Leitung</Button>}
                  </span>
                )}
              </li>
            );
          })}
        </ul>
      ) : <p>Keine registrierten Personen gefunden.</p>}
    </div>
  );
}

function PersonAddDialog({ open, close, people, selectedContext, selectedTurnusId, canManageLeitung, canManageMemberships, addLeitung, addTeamer }) {
  const [query, setQuery] = useState('');
  const normalized = query.trim().toLocaleLowerCase('de');
  const matchedPeople = useMemo(() => people.filter(person => !normalized
    || `${person.name} ${person.email || ''}`.toLocaleLowerCase('de').includes(normalized)), [normalized, people]);
  const closeAndReset = () => {
    setQuery('');
    close();
  };

  return (
    <Dialog.Root open={open} onOpenChange={nextOpen => { if (!nextOpen) closeAndReset(); }}>
      <Dialog.Portal>
        <Dialog.Backdrop className="fixed inset-0 z-[var(--z-modal)] bg-black/45" />
        <Dialog.Viewport className="fixed inset-0 z-[var(--z-modal)] grid place-items-center overflow-y-auto p-4">
          <Dialog.Popup className="card relative grid max-h-[calc(100dvh-2rem)] w-full max-w-2xl grid-rows-[auto_auto_minmax(0,1fr)] gap-4 overflow-hidden bg-surface-solid p-5">
            <div className="mr-10">
              <Dialog.Title className="text-xl font-semibold">Person zu {selectedContext.label} hinzufügen</Dialog.Title>
              <Dialog.Description className="text-sm text-muted-foreground">Registrierte Personen nach Name oder E-Mail-Adresse durchsuchen.</Dialog.Description>
            </div>
            <Dialog.Close className="absolute top-2 right-2" render={<Button type="button" variant="ghost" size="icon" />} aria-label="Dialog schließen">
              <X aria-hidden="true" />
            </Dialog.Close>
            <label className="grid gap-1 font-medium">
              Person suchen
              <span className="team-dialog-search">
                <Search aria-hidden="true" />
                <Input
                  className="pl-9"
                  autoFocus
                  aria-label="Person nach Name oder E-Mail-Adresse suchen"
                  placeholder="Name oder E-Mail-Adresse"
                  value={query}
                  onChange={event => setQuery(event.target.value)}
                />
              </span>
            </label>
            <PersonDirectory
              people={matchedPeople}
              selectedContext={selectedContext}
              selectedTurnusId={selectedTurnusId}
              canManageLeitung={canManageLeitung}
              canManageMemberships={canManageMemberships}
              addLeitung={addLeitung}
              addTeamer={addTeamer}
            />
          </Dialog.Popup>
        </Dialog.Viewport>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

const monthNames = Array.from({ length: 12 }, (_, month) => (
  new Intl.DateTimeFormat('de-AT', { month: 'long', timeZone: 'UTC' })
    .format(new Date(Date.UTC(2026, month, 1)))
));
const weekdayNames = ['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So'];

function isoDate(year, month, day) {
  return `${String(year).padStart(4, '0')}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
}

function isSaturday(value) {
  const date = value ? new Date(`${value}T00:00:00Z`) : null;
  return date != null && !Number.isNaN(date.valueOf()) && date.getUTCDay() === 6;
}

function formatSelectedDate(value) {
  if (!value) return 'Datum auswählen';
  return new Intl.DateTimeFormat('de-AT', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    timeZone: 'UTC',
  }).format(new Date(`${value}T00:00:00Z`));
}

function SaturdayDatePicker({ value, onChange, error, buttonRef }) {
  const now = new Date();
  const [open, setOpen] = useState(false);
  const [viewYear, setViewYear] = useState(now.getFullYear());
  const [viewMonth, setViewMonth] = useState(now.getMonth());
  const errorId = useId();
  const daysInMonth = new Date(Date.UTC(viewYear, viewMonth + 1, 0)).getUTCDate();
  const leadingDays = (new Date(Date.UTC(viewYear, viewMonth, 1)).getUTCDay() + 6) % 7;
  const days = Array.from({ length: daysInMonth }, (_, index) => index + 1);

  const moveMonth = offset => {
    const next = new Date(Date.UTC(viewYear, viewMonth + offset, 1));
    setViewYear(next.getUTCFullYear());
    setViewMonth(next.getUTCMonth());
  };

  return (
    <div className="grid gap-1">
      <span className="font-medium">Startdatum</span>
      <Button
        ref={buttonRef}
        aria-describedby={error ? errorId : undefined}
        aria-expanded={open}
        aria-haspopup="dialog"
        aria-invalid={error ? 'true' : undefined}
        aria-label="Startdatum"
        className="w-full justify-between font-normal"
        type="button"
        variant="outline"
        onClick={() => setOpen(current => !current)}
      >
        <span>{formatSelectedDate(value)}</span>
        <CalendarDays aria-hidden="true" />
      </Button>
      <input name="turnus_beginn" type="hidden" value={value} readOnly />
      {error && <p id={errorId} className="text-sm text-destructive">{error}</p>}
      {open && (
        <div
          aria-label="Startdatum auswählen"
          className="grid gap-3 rounded-lg border border-border bg-popover p-3 shadow-lg"
          role="dialog"
          onKeyDown={event => {
            if (event.key === 'Escape') {
              event.stopPropagation();
              setOpen(false);
              buttonRef.current?.focus();
            }
          }}
        >
          <div className="grid grid-cols-[auto_minmax(0,1fr)_5.5rem_auto] items-center gap-2">
            <Button aria-label="Vorheriger Monat" size="icon" type="button" variant="ghost" onClick={() => moveMonth(-1)}>
              <ChevronLeft aria-hidden="true" />
            </Button>
            <NativeSelect aria-label="Monat" value={viewMonth} onChange={event => setViewMonth(Number(event.target.value))}>
              {monthNames.map((name, month) => <option key={name} value={month}>{name}</option>)}
            </NativeSelect>
            <Input aria-label="Jahr" min="1900" type="number" value={viewYear} onChange={event => setViewYear(Math.max(1900, Number(event.target.value) || 1900))} />
            <Button aria-label="Nächster Monat" size="icon" type="button" variant="ghost" onClick={() => moveMonth(1)}>
              <ChevronRight aria-hidden="true" />
            </Button>
          </div>
          <div className="grid grid-cols-7 text-center text-xs font-medium text-muted-foreground" aria-hidden="true">
            {weekdayNames.map(name => <span key={name}>{name}</span>)}
          </div>
          <div className="grid grid-cols-7 gap-1">
            {Array.from({ length: leadingDays }, (_, index) => <span key={`empty-${index}`} />)}
            {days.map(day => {
              const dateValue = isoDate(viewYear, viewMonth, day);
              const date = new Date(`${dateValue}T00:00:00Z`);
              const saturday = date.getUTCDay() === 6;
              const label = new Intl.DateTimeFormat('de-AT', {
                weekday: 'long', day: 'numeric', month: 'long', year: 'numeric', timeZone: 'UTC',
              }).format(date);
              return (
                <Button
                  key={dateValue}
                  aria-label={`${label} auswählen`}
                  aria-pressed={value === dateValue}
                  className="w-full"
                  data-date={dateValue}
                  disabled={!saturday}
                  size="icon-sm"
                  type="button"
                  variant={value === dateValue ? 'secondary' : 'ghost'}
                  onClick={() => {
                    onChange(dateValue);
                    setOpen(false);
                    buttonRef.current?.focus();
                  }}
                >
                  {day}
                </Button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

function TurnusCreateDialog({ open, onOpenChange, mutate, onCreated }) {
  const [busy, setBusy] = useState(false);
  const [number, setNumber] = useState('');
  const [startDate, setStartDate] = useState('');
  const [errors, setErrors] = useState({});
  const numberRef = useRef(null);
  const dateButtonRef = useRef(null);
  const numberErrorId = useId();
  const showError = useErrorToast();

  const changeOpen = nextOpen => {
    if (!nextOpen) {
      setNumber('');
      setStartDate('');
      setErrors({});
    }
    onOpenChange(nextOpen);
  };

  const changeNumber = event => {
    const next = event.target.value;
    if (!/^\d*$/.test(next)) {
      setErrors(current => ({ ...current, number: 'Nur Zahlen möglich' }));
      return;
    }
    setNumber(next);
    if (Number(next) >= 1) {
      setErrors(current => ({ ...current, number: undefined }));
    }
  };

  const submit = async event => {
    event.preventDefault();
    const nextErrors = {
      number: /^\d+$/.test(number) && Number(number) >= 1 ? undefined : 'Nur Zahlen möglich',
      startDate: isSaturday(startDate) ? undefined : 'Bitte einen Samstag auswählen.',
    };
    setErrors(nextErrors);
    if (nextErrors.number || nextErrors.startDate) {
      if (nextErrors.number) numberRef.current?.focus();
      else dateButtonRef.current?.focus();
      return;
    }

    setBusy(true);
    try {
      const turnus = await mutate('/api/turnusse/', {
        turnus_nr: Number(number),
        turnus_beginn: startDate,
      }, true, true, true);
      onCreated(turnus);
      setNumber('');
      setStartDate('');
      setErrors({});
    } catch (error) {
      showError(error.payload?.detail || 'Der Turnus konnte nicht hinzugefügt werden.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <Dialog.Root open={open} onOpenChange={changeOpen}>
      {open && (
        <Dialog.Portal>
          <Dialog.Backdrop className="fixed inset-0 z-[var(--z-modal)] bg-black/45" />
          <Dialog.Viewport className="fixed inset-0 z-[var(--z-modal)] grid place-items-center overflow-y-auto p-4">
            <Dialog.Popup className="relative grid max-h-[calc(100dvh-2rem)] w-full max-w-md gap-5 overflow-y-auto rounded-xl border border-border bg-popover p-5 text-popover-foreground shadow-xl">
              <Dialog.Title className="mr-10 text-xl font-semibold">Turnus hinzufügen</Dialog.Title>
              <Dialog.Description className="sr-only">Turnusnummer und Startdatum festlegen.</Dialog.Description>
              <Dialog.Close className="absolute top-2 right-2" render={<Button type="button" variant="ghost" size="icon" />} aria-label="Dialog schließen">
                <X aria-hidden="true" />
              </Dialog.Close>
              <form className="grid gap-4" noValidate onSubmit={submit}>
                {(errors.number || errors.startDate) && (
                  <p className="rounded-lg bg-warning p-2 text-sm text-warning-foreground" role="alert">
                    Bitte überprüfe die markierten Eingaben.
                  </p>
                )}
                <label className="grid gap-1 font-medium">
                  Welcher Turnus?
                  <Input
                    ref={numberRef}
                    aria-describedby={errors.number ? numberErrorId : undefined}
                    aria-invalid={errors.number ? 'true' : undefined}
                    autoFocus
                    inputMode="numeric"
                    name="turnus_nr"
                    pattern="[0-9]*"
                    required
                    type="text"
                    value={number}
                    onChange={changeNumber}
                  />
                  {errors.number && <span id={numberErrorId} className="text-sm text-destructive">{errors.number}</span>}
                </label>
                <SaturdayDatePicker
                  buttonRef={dateButtonRef}
                  error={errors.startDate}
                  value={startDate}
                  onChange={value => {
                    setStartDate(value);
                    setErrors(current => ({ ...current, startDate: undefined }));
                  }}
                />
                <div className="flex flex-wrap justify-end gap-2">
                  <Button type="button" variant="outline" disabled={busy} onClick={() => changeOpen(false)}>Abbrechen</Button>
                  <Button type="submit" disabled={busy}>{busy ? 'Wird hinzugefügt…' : 'Turnus hinzufügen'}</Button>
                </div>
              </form>
            </Dialog.Popup>
          </Dialog.Viewport>
        </Dialog.Portal>
      )}
    </Dialog.Root>
  );
}

function TurnusExcelUpload({ turnus, mutate, onUploaded }) {
  const [busy, setBusy] = useState(false);
  const showError = useErrorToast();

  const upload = async event => {
    const input = event.currentTarget;
    const file = input.files?.[0];
    if (!file) return;
    setBusy(true);
    try {
      await mutate(`/api/turnusse/${turnus.id}/excel/`, { uploadedFile: file }, false);
      onUploaded();
    } catch (error) {
      showError(error.payload?.detail || 'Die Excel-Datei konnte nicht hochgeladen werden.');
      input.value = '';
    } finally {
      setBusy(false);
    }
  };

  if (turnus.excel_uploaded) {
    return <p className="flex items-center gap-1.5 font-medium text-success"><Check aria-hidden="true" /> Excel uploaded.</p>;
  }

  return (
    <div>
      <Button type="button" variant="outline" disabled={busy} onClick={event => event.currentTarget.nextElementSibling?.click()}>
        {busy ? 'Uploading Excel…' : 'Upload Excel file'}
      </Button>
      <input
        className="sr-only"
        type="file"
        accept=".xlsx,.xls"
        aria-label="Excel file"
        disabled={busy}
        onChange={upload}
      />
    </div>
  );
}

export function AdminTeamOverviewPage({ data, mutate, createOpen = false, onCreateOpenChange = () => {} }) {
  const showError = useErrorToast();
  const showSuccess = useSuccessToast();
  const [personDialogOpen, setPersonDialogOpen] = useState(false);
  const [years, setYears] = useState(data.years || []);
  const [people, setPeople] = useState(data.people || []);
  const [pendingTurnusId, setPendingTurnusId] = useState(null);
  const [requestBusy, setRequestBusy] = useState(false);
  const canManageLeitung = data.can_manage_leitung !== false;
  const defaultCanManageMemberships = data.can_manage_memberships === true;
  const [selectedTurnusId, setSelectedTurnusId] = useState(() => initialTurnusId(data.years));

  useEffect(() => setYears(data.years || []), [data.years]);
  useEffect(() => setPeople(data.people || []), [data.people]);

  const allTurnuses = useMemo(() => years.flatMap(year => year.turnuses), [years]);
  const selectedContext = allTurnuses.find(turnus => turnus.id === selectedTurnusId) || null;
  const selectedTurnus = selectedContext;
  const canManageMemberships = selectedTurnus?.can_manage_memberships ?? defaultCanManageMemberships;
  const canEditProfiles = selectedTurnus?.can_edit_profiles ?? canManageMemberships;

  useEffect(() => {
    if (pendingTurnusId != null && allTurnuses.some(turnus => turnus.id === pendingTurnusId)) {
      setSelectedTurnusId(pendingTurnusId);
      setPendingTurnusId(null);
      return;
    }
    if (!selectedContext && allTurnuses.length) setSelectedTurnusId(allTurnuses[0].id);
    if (!allTurnuses.length && selectedTurnusId !== null) setSelectedTurnusId(null);
  }, [allTurnuses, pendingTurnusId, selectedContext, selectedTurnusId]);

  const changed = (changedMember, change) => {
    const membershipId = changedMember.id;
    setYears(current => current.map(year => ({
      ...year,
      turnuses: year.turnuses.map(turnus => ({
        ...turnus,
        members: change.removed ? turnus.members.filter(member => member.id !== membershipId) : turnus.members.map(member => member.id === membershipId ? {
          ...member,
          ...change,
          ...(change.functional_role ? { role_label: change.functional_role === 'leitung' ? 'Leitung' : 'Teamer' } : {}),
        } : member),
      })),
    })));
    if (change.removed) setPeople(current => current.map(person => person.id === changedMember.user_id ? {
      ...person,
      relationships: person.relationships.filter(label => label !== selectedContext?.label),
      turnus_ids: (person.turnus_ids || []).filter(id => id !== selectedTurnusId),
      available: (person.turnus_ids || []).filter(id => id !== selectedTurnusId).length === 0,
    } : person));
    if (change.profile) setPeople(current => current.map(person => person.id === changedMember.user_id ? {
      ...person,
      name: change.name || person.name,
      email: change.profile.email,
    } : person));
  };

  const requestDecided = (requestId, approvedMember) => setYears(current => current.map(year => ({
    ...year,
    turnuses: year.turnuses.map(turnus => ({
      ...turnus,
      pending_requests: (turnus.pending_requests || []).filter(request => request.id !== requestId),
      request_summary: { pending: Math.max(0, (turnus.request_summary?.pending || 0) - Number((turnus.pending_requests || []).some(request => request.id === requestId))) },
      members: approvedMember && (turnus.pending_requests || []).some(request => request.id === requestId)
        && !turnus.members.some(member => member.id === approvedMember.id)
        ? [...turnus.members, approvedMember]
        : turnus.members,
    })),
  })));

  const addPerson = async (person, { role, url }) => {
    try {
      const result = await mutate(url, { user_id: person.id }, true, true, true);
      setYears(current => current.map(year => ({
        ...year,
        turnuses: year.turnuses.map(turnus => turnus.id === selectedTurnusId ? {
          ...turnus,
          members: turnus.members.some(member => member.id === result.membership_id)
            ? turnus.members
            : [...turnus.members, {
                id: result.membership_id,
                user_id: person.id,
                name: person.name,
                functional_role: role,
                role_label: result.role_label || (role === 'leitung' ? 'Leitung' : 'Teamer'),
                team_label: result.team_label || '',
              }],
        } : turnus),
      })));
      setPeople(current => current.map(item => item.id === person.id ? {
        ...item,
        relationships: item.relationships.includes(selectedContext.label)
          ? item.relationships
          : [...item.relationships, selectedContext.label],
        turnus_ids: (item.turnus_ids || []).includes(selectedTurnusId)
          ? item.turnus_ids
          : [...(item.turnus_ids || []), selectedTurnusId],
        available: false,
      } : item));
      showSuccess(`${person.name} ist jetzt ${role === 'leitung' ? 'Leitung' : 'Teamer'}.`);
    } catch (error) {
      showError(error.payload?.detail || (role === 'leitung' ? 'Die Leitung konnte nicht hinzugefügt werden.' : 'Die Person konnte nicht hinzugefügt werden.'));
    }
  };

  const addLeitung = person => addPerson(person, { role: 'leitung', url: `/api/admin/turnusse/${selectedTurnusId}/leitung/` });
  const addTeamer = person => addPerson(person, { role: 'teamer', url: `/api/turnusse/${selectedTurnusId}/memberships/` });
  const markExcelUploaded = () => setYears(current => current.map(year => ({
    ...year,
    turnuses: year.turnuses.map(turnus => turnus.id === selectedTurnusId
      ? { ...turnus, excel_uploaded: true }
      : turnus),
  })));
  const requestMembership = async () => {
    setRequestBusy(true);
    try {
      const result = await mutate(`/api/turnusse/${selectedTurnusId}/join-requests/`, {});
      setYears(current => current.map(year => ({
        ...year,
        turnuses: year.turnuses.map(turnus => turnus.id === selectedTurnusId
          ? { ...turnus, request_status: result.status }
          : turnus),
      })));
      showSuccess(`Anfrage für ${selectedContext.label} gesendet.`);
    } catch (error) {
      showError(error.payload?.detail || 'Die Beitrittsanfrage konnte nicht gesendet werden.');
    } finally {
      setRequestBusy(false);
    }
  };
  const turnusCreated = turnus => {
    setPendingTurnusId(turnus.id);
    onCreateOpenChange(false);
  };
  const leads = selectedTurnus?.leads
    || selectedTurnus?.members.filter(member => member.functional_role === 'leitung')
    || [];
  const canViewSelectedTeam = selectedTurnus?.can_view_team !== false;

  return (
    <Columns className="team-management-page">
      <div className="team-master-detail" data-testid="team-master-detail">
        <nav className="team-turnus-rail" aria-label="Turnus auswählen">
          <div className="team-year-selector">
            {years.map(year => (
              <section className="team-year-group" key={year.year} aria-labelledby={`team-year-${year.year}`}>
                <h2 id={`team-year-${year.year}`}>{year.year}</h2>
                <div className="team-year-turnuses">
                  {year.turnuses.map(turnus => {
                    const pending = turnus.request_summary?.pending || 0;
                    return (
                      <Button
                        className="team-turnus-option h-auto justify-between whitespace-normal p-[0.6875rem] text-left max-[900px]:p-[0.5625rem]"
                        data-selected={turnus.id === selectedTurnusId || undefined}
                        key={turnus.id}
                        type="button"
                        variant="ghost"
                        aria-label={`${turnus.label} auswählen`}
                        aria-pressed={turnus.id === selectedTurnusId}
                        onClick={() => setSelectedTurnusId(turnus.id)}
                      >
                        <span>
                          <strong>{turnus.label}</strong>
                          <small>{turnus.can_view_team === false
                            ? `${turnus.leads?.length || 0} Leitung`
                            : `${turnus.members.length} Mitglieder · ${turnus.leads?.length ?? turnus.members.filter(member => member.functional_role === 'leitung').length} Leitung`}</small>
                        </span>
                        {pending > 0 && <em aria-label={`${pending} offene ${pending === 1 ? 'Anfrage' : 'Anfragen'}`}>{pending}</em>}
                      </Button>
                    );
                  })}
                </div>
              </section>
            ))}
          </div>
          {!years.length && <p className="team-rail-empty">Keine Turnusse vorhanden.</p>}
        </nav>
        {selectedTurnus && (
          <section className="team-detail" aria-label={`${selectedTurnus.label} ${canViewSelectedTeam ? 'verwalten' : 'ansehen'}`}>
            <header className="team-detail-header">
              <div>
                {selectedTurnus.start && <span className="team-eyebrow">{formatDateRange(selectedTurnus.start, selectedTurnus.end)}</span>}
                <h2>{selectedTurnus.label}</h2>
                <p><ShieldCheck aria-hidden="true" /> Leitung: {leads.length ? leads.map(member => member.name).join(' und ') : 'noch nicht besetzt'}</p>
              </div>
              {(canManageLeitung || canManageMemberships) && (
                <div className="flex flex-wrap items-center justify-end gap-2">
                  {canManageMemberships && (
                    <TurnusExcelUpload turnus={selectedTurnus} mutate={mutate} onUploaded={markExcelUploaded} />
                  )}
                  <Button className="mobile-icon-action" size="responsive-icon" type="button" variant="secondary" aria-label="Person hinzufügen" onClick={() => setPersonDialogOpen(true)}>
                    <span className="desktop-action-label">Person hinzufügen</span>
                    <UserPlus className="mobile-action-label" aria-hidden="true" />
                  </Button>
                </div>
              )}
            </header>
            {!canViewSelectedTeam && (
              <section className="team-request-panel" aria-label={`Mitgliedschaft für ${selectedTurnus.label} anfragen`}>
                {selectedTurnus.request_status && (
                  <p className="font-medium">{requestLabels[selectedTurnus.request_status] || selectedTurnus.request_status}</p>
                )}
                {selectedTurnus.request_status !== 'pending' && (
                  <Button type="button" disabled={requestBusy} onClick={requestMembership}>
                    {requestBusy ? 'Anfrage wird gesendet…' : 'Als Betreuer:in anfragen'}
                  </Button>
                )}
              </section>
            )}
            {canViewSelectedTeam && Boolean(selectedTurnus.pending_requests?.length) && (
              <section className="team-request-panel" data-testid="pending-request-panel" aria-labelledby="pending-requests-heading">
                <h3 id="pending-requests-heading"><Clock3 aria-hidden="true" /> Offene Anfragen ({selectedTurnus.pending_requests.length})</h3>
                <ul>{selectedTurnus.pending_requests.map(request => <PendingRequest key={request.id} request={request} mutate={mutate} onDecided={requestDecided} />)}</ul>
                {data.identity_verification_warning && (
                  <p className="team-identity-warning" role="alert">
                    <AlertTriangle aria-hidden="true" />
                    <span><strong>Identität zuerst überprüfen</strong>{data.identity_verification_warning}</span>
                  </p>
                )}
              </section>
            )}
            {canViewSelectedTeam && (
              <section className="team-member-panel" data-testid="member-panel" aria-labelledby="team-members-heading">
                <header>
                  <div><span className="team-eyebrow">Team</span><h3 id="team-members-heading">{selectedTurnus.members.length} Personen</h3></div>
                </header>
                {selectedTurnus.members.length
                  ? <ul className="team-member-list">{selectedTurnus.members.map(member => <Member key={member.id} member={member} mutate={mutate} onChanged={changed} canManageLeitung={canManageLeitung} canManageMemberships={canManageMemberships} canEditProfiles={canEditProfiles} token={data.csrf_token} />)}</ul>
                  : <p>Noch keine Teammitglieder.</p>}
              </section>
            )}
          </section>
        )}
      </div>
      <TurnusCreateDialog
        open={createOpen}
        onOpenChange={onCreateOpenChange}
        mutate={mutate}
        onCreated={turnusCreated}
      />
      {personDialogOpen && selectedTurnus && (
        <PersonAddDialog
          open
          close={() => setPersonDialogOpen(false)}
          people={people}
          selectedContext={selectedContext}
          selectedTurnusId={selectedTurnusId}
          canManageLeitung={canManageLeitung}
          canManageMemberships={canManageMemberships}
          addLeitung={addLeitung}
          addTeamer={addTeamer}
        />
      )}
    </Columns>
  );
}

const teamHeaderAction = (data, { setPageState }) => data.can_create_turnus ? (
  <Button
    className="mobile-icon-action"
    size="responsive-icon"
    type="button"
    aria-label="Turnus hinzufügen"
    onClick={() => setPageState?.(current => ({ ...current, createTurnusOpen: true }))}
  >
    <span className="desktop-action-label">Turnus hinzufügen</span>
    <Plus className="mobile-action-label" aria-hidden="true" />
  </Button>
) : null;

const renderTeamManagement = ({ data, mutate, pageState, setPageState }) => (
  <AdminTeamOverviewPage
    data={data}
    mutate={mutate}
    createOpen={Boolean(pageState?.createTurnusOpen)}
    onCreateOpenChange={open => setPageState?.(current => ({ ...current, createTurnusOpen: open }))}
  />
);

export const membershipRoutes = [{
  pattern: /^\/admin\/teams$/,
  page: 'admin-team-overview',
  title: 'Team & Turnus',
  domain: 'memberships',
  readContractKey: 'admin-team-overview',
  headerAction: teamHeaderAction,
  render: renderTeamManagement,
}, {
  pattern: /^\/teams$/,
  page: 'team-management',
  title: 'Team & Turnus',
  domain: 'memberships',
  readContractKey: 'team-management',
  headerAction: teamHeaderAction,
  render: renderTeamManagement,
}];
