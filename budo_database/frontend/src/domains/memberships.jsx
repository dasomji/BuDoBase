import { useEffect, useMemo, useRef, useState } from 'react';
import {
  AlertTriangle,
  Check,
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
import { Input } from '../components/ui/input';
import { useErrorToast, useSuccessToast } from '../components/ui/toast';

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

function Member({ member, mutate, onChanged, canManageLeitung, canManageMemberships }) {
  const [busy, setBusy] = useState(false);
  const [editing, setEditing] = useState(false);
  const [teamLabel, setTeamLabel] = useState(member.team_label || '');
  const [labelError, setLabelError] = useState('');
  const labelInput = useRef(null);
  const showError = useErrorToast();
  const showSuccess = useSuccessToast();
  const isLead = member.functional_role === 'leitung';

  useEffect(() => {
    if (labelError) labelInput.current?.querySelector('input')?.focus();
  }, [labelError]);

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

  const saveLabel = async () => {
    setBusy(true);
    setLabelError('');
    try {
      const result = await mutate(`/api/memberships/${member.id}/label/`, { team_label: teamLabel });
      onChanged(member, { team_label: result.team_label });
      setEditing(false);
      showSuccess(`Bezeichnung für ${member.name} gespeichert.`);
    } catch (error) {
      const fieldError = error.payload?.team_label;
      const message = Array.isArray(fieldError) ? fieldError.join(' ') : fieldError;
      setLabelError(message || 'Die Bezeichnung konnte nicht gespeichert werden.');
    } finally {
      setBusy(false);
    }
  };

  const remove = async () => {
    setBusy(true);
    try {
      await mutate(`/api/memberships/${member.id}/remove/`, {});
      onChanged(member, { removed: true });
      showSuccess(`${member.name} wurde aus dem Turnus entfernt.`);
    } catch (error) {
      showError(error.payload?.detail || 'Die Mitgliedschaft konnte nicht entfernt werden.');
    } finally {
      setBusy(false);
    }
  };

  const manageable = canManageLeitung || (canManageMemberships && !isLead);
  return (
    <li className="team-member-tile">
      <span className="team-avatar" aria-hidden="true">{initials(member.name)}</span>
      <span className="team-person-copy">
        <strong>{member.name}</strong>
        <small>{member.role_label}{member.team_label ? ` · ${member.team_label}` : ''}</small>
      </span>
      {manageable && (
        <Button
          className="team-pencil-action"
          aria-label={`${member.name} bearbeiten`}
          aria-expanded={editing}
          title={`${member.name} bearbeiten`}
          type="button"
          size="icon-sm"
          variant="ghost"
          disabled={busy}
          onClick={() => setEditing(value => !value)}
        >
          <PencilIcon aria-hidden="true" />
        </Button>
      )}
      {editing && (
        <div className="team-member-editor">
          {labelError && <p className="text-sm font-medium text-destructive" role="alert" id={`team-label-${member.id}-error`}>{labelError}</p>}
          <label className="grid gap-1" ref={labelInput}>
            <span className="text-sm font-medium">Bezeichnung für {member.name}</span>
            <Input
              maxLength={255}
              value={teamLabel}
              aria-invalid={labelError ? 'true' : undefined}
              aria-describedby={labelError ? `team-label-${member.id}-error` : undefined}
              onChange={event => { setTeamLabel(event.target.value); setLabelError(''); }}
            />
          </label>
          <div className="flex flex-wrap gap-2">
            <Button type="button" disabled={busy} onClick={saveLabel}>Speichern</Button>
            {canManageLeitung && <Button type="button" variant="outline" disabled={busy} onClick={changeRole}>{isLead ? `${member.name} Leitung entfernen` : `${member.name} als Leitung einsetzen`}</Button>}
            <Button type="button" variant="destructive" disabled={busy} onClick={remove}>{member.name} aus dem Turnus entfernen</Button>
            <Button type="button" variant="ghost" disabled={busy} onClick={() => setEditing(false)}>Abbrechen</Button>
          </div>
        </div>
      )}
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
        <Button type="button" size="icon-sm" variant="ghost" disabled={busy} aria-label={`${request.name} ablehnen`} title={`${request.name} ablehnen`} onClick={() => decide('reject')}><X aria-hidden="true" /></Button>
        <Button className="bg-[#54b958]! text-[#163f19]! hover:bg-[#49a84d]!" type="button" size="icon-sm" disabled={busy} aria-label={`${request.name} annehmen`} title={`${request.name} annehmen`} onClick={() => decide('approve')}><Check aria-hidden="true" /></Button>
      </span>
    </li>
  );
}

function PersonDirectory({ people, selectedContext, selectedTurnusId, canManageLeitung, canManageMemberships, addLeitung, addTeamer }) {
  return (
    <section className="team-person-directory" aria-labelledby="person-search-heading">
      <h4 id="person-search-heading">Registrierte Personen</h4>
      {people.length ? (
        <ul>
          {people.map(person => {
            const availableForSelected = selectedContext != null && !(person.turnus_ids || []).includes(selectedTurnusId);
            return (
              <li key={person.id}>
                <span className="team-avatar" aria-hidden="true">{initials(person.name)}</span>
                <span className="team-person-copy">
                  <strong>{person.name}</strong>
                  <small>{person.relationships.length ? person.relationships.join(' · ') : 'Keine Teamzugehörigkeiten · verfügbar'}</small>
                </span>
                {availableForSelected && (canManageLeitung || canManageMemberships) && (
                  <span className="team-directory-actions">
                    {canManageMemberships && <Button aria-label={`${person.name} als Teamer zu ${selectedContext.label} hinzufügen`} type="button" variant="outline" onClick={() => addTeamer(person)}><Plus aria-hidden="true" /> Als Teamer</Button>}
                    {canManageLeitung && <Button aria-label={`${person.name} als Leitung zu ${selectedContext.label} hinzufügen`} type="button" variant="outline" onClick={() => addLeitung(person)}><Plus aria-hidden="true" /> Als Leitung</Button>}
                  </span>
                )}
              </li>
            );
          })}
        </ul>
      ) : <p>Keine registrierten Personen gefunden.</p>}
    </section>
  );
}

export function AdminTeamOverviewPage({ data, mutate, personSearchOpen = false, onPersonSearchOpenChange }) {
  const showError = useErrorToast();
  const showSuccess = useSuccessToast();
  const [query, setQuery] = useState('');
  const [directoryRequested, setDirectoryRequested] = useState(false);
  const searchInput = useRef(null);
  const [years, setYears] = useState(data.years || []);
  const [people, setPeople] = useState(data.people || []);
  const canManageLeitung = data.can_manage_leitung !== false;
  const canManageMemberships = data.can_manage_memberships === true;
  const [selectedTurnusId, setSelectedTurnusId] = useState(() => data.years?.[0]?.turnuses?.[0]?.id ?? null);

  useEffect(() => setYears(data.years || []), [data.years]);
  useEffect(() => setPeople(data.people || []), [data.people]);

  const normalized = query.trim().toLocaleLowerCase('de');
  const filtered = useMemo(() => years.map(year => ({
    ...year,
    turnuses: year.turnuses.filter(turnus => !normalized
      || turnus.label.toLocaleLowerCase('de').includes(normalized)
      || turnus.members.some(member => `${member.name} ${member.team_label} ${member.role_label}`.toLocaleLowerCase('de').includes(normalized))),
  })).filter(year => year.turnuses.length), [years, normalized]);
  const allTurnuses = useMemo(() => years.flatMap(year => year.turnuses), [years]);
  const directoryVisible = personSearchOpen || directoryRequested || normalized.length > 0;
  const matchedPeople = useMemo(() => directoryVisible ? people.filter(person => !normalized
    || `${person.name} ${person.relationships.join(' ')}`.toLocaleLowerCase('de').includes(normalized)) : [], [directoryVisible, normalized, people]);
  const selectedContext = allTurnuses.find(turnus => turnus.id === selectedTurnusId) || null;
  const selectedTurnus = selectedContext;

  useEffect(() => {
    if (!selectedContext && allTurnuses.length) setSelectedTurnusId(allTurnuses[0].id);
    if (!allTurnuses.length && selectedTurnusId !== null) setSelectedTurnusId(null);
  }, [allTurnuses, selectedContext, selectedTurnusId]);

  useEffect(() => {
    if (personSearchOpen) searchInput.current?.focus();
  }, [personSearchOpen]);

  const openDirectory = () => {
    setDirectoryRequested(true);
    onPersonSearchOpenChange?.(true);
    searchInput.current?.focus();
  };

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
      const result = await mutate(url, { user_id: person.id });
      setYears(current => current.map(year => ({
        ...year,
        turnuses: year.turnuses.map(turnus => turnus.id === selectedTurnusId ? {
          ...turnus,
          members: [...turnus.members, {
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
        relationships: [...item.relationships, selectedContext.label],
        turnus_ids: [...(item.turnus_ids || []), selectedTurnusId],
        available: false,
      } : item));
      showSuccess(`${person.name} ist jetzt ${role === 'leitung' ? 'Leitung' : 'Teamer'}.`);
    } catch (error) {
      showError(error.payload?.detail || (role === 'leitung' ? 'Die Leitung konnte nicht hinzugefügt werden.' : 'Die Person konnte nicht hinzugefügt werden.'));
    }
  };

  const addLeitung = person => addPerson(person, { role: 'leitung', url: `/api/admin/turnusse/${selectedTurnusId}/leitung/` });
  const addTeamer = person => addPerson(person, { role: 'teamer', url: `/api/turnusse/${selectedTurnusId}/memberships/` });
  const leads = selectedTurnus?.members.filter(member => member.functional_role === 'leitung') || [];

  return (
    <Columns className="team-management-page">
      <p className="team-management-subtitle">Teams überblicken, Personen im Detail verwalten</p>
      <div className="team-master-detail" data-testid="team-master-detail">
        <nav className="team-turnus-rail" aria-label="Turnus auswählen">
          <label className="team-rail-search">
            <span className="sr-only">Turnusse und Personen suchen</span>
            <Search aria-hidden="true" />
            <Input ref={searchInput} value={query} onChange={event => setQuery(event.target.value)} placeholder="Turnus suchen …" />
          </label>
          <div className="team-year-selector">
            {filtered.map(year => (
              <section className="team-year-group" key={year.year} aria-labelledby={`team-year-${year.year}`}>
                <h2 id={`team-year-${year.year}`}>{year.year}</h2>
                <div className="team-year-turnuses">
                  {year.turnuses.map(turnus => {
                    const pending = turnus.request_summary?.pending || 0;
                    return (
                      <button
                        className="team-turnus-option"
                        data-selected={turnus.id === selectedTurnusId || undefined}
                        key={turnus.id}
                        type="button"
                        aria-label={`${turnus.label} auswählen`}
                        aria-pressed={turnus.id === selectedTurnusId}
                        onClick={() => setSelectedTurnusId(turnus.id)}
                      >
                        <span>
                          <strong>{turnus.label}</strong>
                          <small>{turnus.members.length} Mitglieder · {turnus.members.filter(member => member.functional_role === 'leitung').length} Leitung</small>
                        </span>
                        {pending > 0 && <em aria-label={`${pending} offene ${pending === 1 ? 'Anfrage' : 'Anfragen'}`}>{pending}</em>}
                      </button>
                    );
                  })}
                </div>
              </section>
            ))}
          </div>
          {!filtered.length && <p className="team-rail-empty">Keine Turnusse gefunden.</p>}
        </nav>
        {selectedTurnus && (
          <section className="team-detail" aria-label={`${selectedTurnus.label} verwalten`}>
            <header className="team-detail-header">
              <div>
                {selectedTurnus.start && <span className="team-eyebrow">{formatDateRange(selectedTurnus.start, selectedTurnus.end)}</span>}
                <h2>{selectedTurnus.label}</h2>
                <p><ShieldCheck aria-hidden="true" /> Leitung: {leads.length ? leads.map(member => member.name).join(' und ') : 'noch nicht besetzt'}</p>
              </div>
              {(canManageLeitung || canManageMemberships) && <Button className="team-detail-manage" type="button" variant="secondary" aria-label="Mitglieder verwalten" onClick={openDirectory}><UserPlus aria-hidden="true" /><span>Mitglieder verwalten</span></Button>}
            </header>
            <section className="team-request-panel" data-testid="pending-request-panel" aria-labelledby="pending-requests-heading">
              <h3 id="pending-requests-heading"><Clock3 aria-hidden="true" /> Offene Anfragen ({selectedTurnus.request_summary?.pending ?? 0})</h3>
              {selectedTurnus.pending_requests?.length
                ? <ul>{selectedTurnus.pending_requests.map(request => <PendingRequest key={request.id} request={request} mutate={mutate} onDecided={requestDecided} />)}</ul>
                : <p className="team-empty-state"><Check aria-hidden="true" /> Keine offenen Anfragen.</p>}
              {data.identity_verification_warning && (
                <p className="team-identity-warning" role="alert">
                  <AlertTriangle aria-hidden="true" />
                  <span><strong>Identität zuerst überprüfen</strong>{data.identity_verification_warning}</span>
                </p>
              )}
            </section>
            <section className="team-member-panel" data-testid="member-panel" aria-labelledby="team-members-heading">
              <header>
                <div><span className="team-eyebrow">Team</span><h3 id="team-members-heading">{selectedTurnus.members.length} Personen</h3></div>
                {(canManageLeitung || canManageMemberships) && <button type="button" aria-expanded={directoryVisible} onClick={openDirectory}>Alle verfügbaren Personen durchsuchen</button>}
              </header>
              {directoryVisible && <PersonDirectory people={matchedPeople} selectedContext={selectedContext} selectedTurnusId={selectedTurnusId} canManageLeitung={canManageLeitung} canManageMemberships={canManageMemberships} addLeitung={addLeitung} addTeamer={addTeamer} />}
              {selectedTurnus.members.length
                ? <ul className="team-member-list">{selectedTurnus.members.map(member => <Member key={member.id} member={member} mutate={mutate} onChanged={changed} canManageLeitung={canManageLeitung} canManageMemberships={canManageMemberships} />)}</ul>
                : <p>Noch keine Teammitglieder.</p>}
            </section>
          </section>
        )}
      </div>
      {!filtered.length && !matchedPeople.length && normalized && <p className="team-no-results">Keine Turnusse oder Personen gefunden.</p>}
    </Columns>
  );
}

function membershipHeaderAction(_data, { setPageState }) {
  return (
    <Button
      className="team-management-add-action"
      type="button"
      aria-label="Person hinzufügen"
      onClick={() => setPageState?.(current => ({ ...current, personSearchOpen: true }))}
    >
      <UserPlus aria-hidden="true" />
      <span>Person hinzufügen</span>
    </Button>
  );
}

const renderTeamManagement = ({ data, mutate, pageState, setPageState }) => (
  <AdminTeamOverviewPage
    data={data}
    mutate={mutate}
    personSearchOpen={Boolean(pageState?.personSearchOpen)}
    onPersonSearchOpenChange={open => setPageState?.(current => ({ ...current, personSearchOpen: open }))}
  />
);

export const membershipRoutes = [{
  pattern: /^\/admin\/teams$/,
  page: 'admin-team-overview',
  title: 'Teamverwaltung',
  domain: 'memberships',
  readContractKey: 'admin-team-overview',
  headerAction: membershipHeaderAction,
  render: renderTeamManagement,
}, {
  pattern: /^\/teams$/,
  page: 'team-management',
  title: 'Teamverwaltung',
  domain: 'memberships',
  readContractKey: 'team-management',
  headerAction: membershipHeaderAction,
  render: renderTeamManagement,
}];
