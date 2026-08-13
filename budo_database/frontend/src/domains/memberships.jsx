import { useEffect, useMemo, useRef, useState } from 'react';
import { Pencil, Plus, Search } from 'lucide-react';

import { Column, Columns, TranslucentCard } from '../components';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { useErrorToast, useSuccessToast } from '../components/ui/toast';
import { useIsMobile } from '../hooks/use-mobile';

function Member({ member, mutate, onChanged, canManageLeitung, canManageMemberships }) {
  const [busy, setBusy] = useState(false);
  const [editing, setEditing] = useState(false);
  const [teamLabel, setTeamLabel] = useState(member.team_label || '');
  const showError = useErrorToast();
  const showSuccess = useSuccessToast();
  const isLead = member.functional_role === 'leitung';
  const changeRole = async () => {
    const functionalRole = isLead ? 'teamer' : 'leitung';
    setBusy(true);
    try {
      await mutate(`/api/admin/memberships/${member.id}/role/`, { functional_role: functionalRole });
      onChanged(member.id, { functional_role: functionalRole });
      showSuccess(isLead ? `${member.name} ist jetzt Teamer.` : `${member.name} ist jetzt Leitung.`);
    } catch (error) {
      showError(error.payload?.detail || 'Die Funktionsrolle konnte nicht geändert werden.');
    } finally {
      setBusy(false);
    }
  };
  const saveLabel = async () => {
    setBusy(true);
    try {
      const result = await mutate(`/api/memberships/${member.id}/label/`, { team_label: teamLabel });
      onChanged(member.id, { team_label: result.team_label });
      setEditing(false);
      showSuccess(`Bezeichnung für ${member.name} gespeichert.`);
    } catch (error) {
      showError(error.payload?.detail || 'Die Bezeichnung konnte nicht gespeichert werden.');
    } finally { setBusy(false); }
  };
  const remove = async () => {
    setBusy(true);
    try {
      await mutate(`/api/memberships/${member.id}/remove/`, {});
      onChanged(member.id, { removed: true });
      showSuccess(`${member.name} wurde aus dem Turnus entfernt.`);
    } catch (error) {
      showError(error.payload?.detail || 'Die Mitgliedschaft konnte nicht entfernt werden.');
    } finally { setBusy(false); }
  };
  const manageable = canManageLeitung || (canManageMemberships && !isLead);
  return (
    <li className="grid gap-3 border-t border-border py-3 first:border-t-0">
      <div className="flex items-center justify-between gap-3"><div className="min-w-0">
        <p className="font-medium">{member.name}</p>
        <p className="text-sm text-muted-foreground">
          {member.role_label}{member.team_label ? ` · ${member.team_label}` : ''}
        </p>
      </div>{manageable && <Button aria-label={canManageLeitung ? `${member.name} bearbeiten: ${isLead ? 'Leitung entfernen' : 'als Leitung einsetzen'}` : `${member.name} bearbeiten`} title={`${member.name} bearbeiten`} type="button" size="icon-sm" variant="ghost" disabled={busy} onClick={canManageLeitung ? changeRole : () => setEditing(value => !value)}>
        <Pencil aria-hidden="true" />
      </Button>}</div>
      {editing && !canManageLeitung && <div className="grid gap-3 rounded-md border border-border p-3">
        <label className="grid gap-1"><span className="text-sm font-medium">Bezeichnung für {member.name}</span><Input maxLength={255} value={teamLabel} onChange={event => setTeamLabel(event.target.value)} /></label>
        <div className="flex flex-wrap gap-2">
          <Button type="button" disabled={busy} onClick={saveLabel}>Speichern</Button>
          {canManageLeitung && <Button type="button" variant="outline" disabled={busy} onClick={changeRole}>{isLead ? 'Zu Teamer ändern' : 'Zu Leitung ändern'}</Button>}
          <Button type="button" variant="destructive" disabled={busy} onClick={remove}>{member.name} entfernen</Button>
          <Button type="button" variant="ghost" disabled={busy} onClick={() => setEditing(false)}>Abbrechen</Button>
        </div>
      </div>}
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
  return <li className="flex flex-wrap items-center justify-between gap-2 border-t border-border py-3 first:border-t-0">
    <span className="min-w-0"><strong>{request.name}</strong>{request.email && <span className="block break-all text-sm text-muted-foreground">{request.email}</span>}</span>
    <span className="flex flex-wrap gap-2">
      <Button type="button" disabled={busy} onClick={() => decide('approve')}>{request.name} annehmen</Button>
      <Button type="button" variant="outline" disabled={busy} onClick={() => decide('reject')}>{request.name} ablehnen</Button>
    </span>
  </li>;
}

export function AdminTeamOverviewPage({ data, mutate }) {
  const showError = useErrorToast();
  const showSuccess = useSuccessToast();
  const [query, setQuery] = useState('');
  const [years, setYears] = useState(data.years || []);
  const [people, setPeople] = useState(data.people || []);
  useEffect(() => setYears(data.years || []), [data.years]);
  useEffect(() => setPeople(data.people || []), [data.people]);
  const isMobile = useIsMobile();
  const canManageLeitung = data.can_manage_leitung !== false;
  const canManageMemberships = data.can_manage_memberships === true;
  const [expandedYears, setExpandedYears] = useState(() => new Set(
    isMobile ? data.years?.slice(0, 1).map(year => year.year) : data.years?.map(year => year.year),
  ));
  const [selectedTurnusId, setSelectedTurnusId] = useState(() => data.years?.[0]?.turnuses?.[0]?.id ?? null);
  const previousMobile = useRef(isMobile);
  const normalized = query.trim().toLocaleLowerCase('de');
  const filtered = useMemo(() => years.map(year => ({
    ...year,
    turnuses: year.turnuses.filter(turnus => !normalized
      || turnus.label.toLocaleLowerCase('de').includes(normalized)
      || turnus.members.some(member => `${member.name} ${member.team_label} ${member.role_label}`.toLocaleLowerCase('de').includes(normalized))),
  })).filter(year => year.turnuses.length), [years, normalized]);
  const allTurnuses = useMemo(() => years.flatMap(year => year.turnuses), [years]);
  const matchedPeople = useMemo(() => normalized ? people.filter(person =>
    `${person.name} ${person.relationships.join(' ')}`.toLocaleLowerCase('de').includes(normalized)
  ) : [], [people, normalized]);
  const selectedContext = allTurnuses.find(turnus => turnus.id === selectedTurnusId) || null;
  // Search narrows the master list, but must never hide the detail that person
  // actions target. Otherwise an add button can mutate an invisible Turnus.
  const selectedTurnus = selectedContext;
  useEffect(() => {
    if (!selectedContext && allTurnuses.length) setSelectedTurnusId(allTurnuses[0].id);
    if (!allTurnuses.length && selectedTurnusId !== null) setSelectedTurnusId(null);
  }, [allTurnuses, selectedContext, selectedTurnusId]);
  useEffect(() => {
    if (previousMobile.current === isMobile) return;
    previousMobile.current = isMobile;
    if (!isMobile) {
      setExpandedYears(new Set(years.map(year => year.year)));
      return;
    }
    const selectedYear = years.find(year => year.turnuses.some(turnus => turnus.id === selectedTurnusId));
    setExpandedYears(new Set([selectedYear?.year ?? years[0]?.year].filter(year => year != null)));
  }, [isMobile, selectedTurnusId, years]);
  const changed = (membershipId, change) => setYears(current => current.map(year => ({
    ...year,
    turnuses: year.turnuses.map(turnus => ({
      ...turnus,
      members: change.removed ? turnus.members.filter(member => member.id !== membershipId) : turnus.members.map(member => member.id === membershipId ? {
        ...member, ...change,
        ...(change.functional_role ? { role_label: change.functional_role === 'leitung' ? 'Leitung' : 'Teamer' } : {}),
      } : member),
    })),
  })));
  const requestDecided = (requestId, approvedMember) => setYears(current => current.map(year => ({
    ...year,
    turnuses: year.turnuses.map(turnus => ({
      ...turnus,
      pending_requests: (turnus.pending_requests || []).filter(request => request.id !== requestId),
      request_summary: { pending: Math.max(0, (turnus.request_summary?.pending || 0) - (turnus.pending_requests || []).some(request => request.id === requestId)) },
      members: approvedMember && (turnus.pending_requests || []).some(request => request.id === requestId)
        && !turnus.members.some(member => member.id === approvedMember.id)
        ? [...turnus.members, approvedMember]
        : turnus.members,
    })),
  })));
  const addLeitung = async person => {
    try {
      const result = await mutate(`/api/admin/turnusse/${selectedTurnusId}/leitung/`, { user_id: person.id });
      setYears(current => current.map(year => ({
        ...year,
        turnuses: year.turnuses.map(turnus => turnus.id === selectedTurnusId ? {
          ...turnus,
          members: [...turnus.members, {
            id: result.membership_id,
            user_id: person.id,
            name: person.name,
            functional_role: 'leitung',
            role_label: result.role_label || 'Leitung',
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
      showSuccess(`${person.name} ist jetzt Leitung.`);
    } catch (error) {
      showError(error.payload?.detail || 'Die Leitung konnte nicht hinzugefügt werden.');
    }
  };
  const addTeamer = async person => {
    try {
      const result = await mutate(`/api/turnusse/${selectedTurnusId}/memberships/`, { user_id: person.id });
      setYears(current => current.map(year => ({ ...year, turnuses: year.turnuses.map(turnus => turnus.id === selectedTurnusId ? {
        ...turnus, members: [...turnus.members, { id: result.membership_id, user_id: person.id, name: person.name, functional_role: 'teamer', role_label: result.role_label || 'Teamer', team_label: result.team_label || '' }],
      } : turnus) })));
      setPeople(current => current.map(item => item.id === person.id ? { ...item, relationships: [...item.relationships, selectedContext.label], turnus_ids: [...(item.turnus_ids || []), selectedTurnusId], available: false } : item));
      showSuccess(`${person.name} ist jetzt Teamer.`);
    } catch (error) { showError(error.payload?.detail || 'Die Person konnte nicht hinzugefügt werden.'); }
  };
  return (
    <Columns className="mx-auto grid w-full max-w-6xl px-4 py-5">
      <Column className="min-w-0" id="team-management">
        <label className="relative mb-5 block max-w-xl">
          <span className="sr-only">Turnusse und Personen suchen</span>
          <Search className="pointer-events-none absolute left-3 top-2.5 size-5 text-muted-foreground" aria-hidden="true" />
          <Input className="pl-10" value={query} onChange={event => setQuery(event.target.value)} placeholder="Turnusse und Personen suchen" />
        </label>
        <div className={isMobile ? 'grid items-start gap-4' : 'grid grid-cols-[minmax(14rem,1fr)_minmax(0,3fr)] items-start gap-4'} data-slot="team-master-detail">
          <nav className={isMobile ? 'flex min-w-0 gap-4 overflow-x-auto pb-2' : 'flex min-w-0 flex-col gap-4'} aria-label="Turnus auswählen">
            {filtered.map(year => (
              <TranslucentCard
                className={isMobile ? 'min-w-max' : 'min-w-0'}
                expanded={expandedYears.has(year.year)}
                key={year.year}
                onExpandedChange={expanded => setExpandedYears(current => {
                  const next = new Set(current);
                  if (expanded) next.add(year.year);
                  else next.delete(year.year);
                  return next;
                })}
                title={`${year.year}`}
              >
                <div className={isMobile ? 'flex gap-2' : 'flex flex-col gap-2'}>
                  {year.turnuses.map(turnus => (
                    <Button
                      className="h-auto justify-start whitespace-nowrap text-left"
                      key={turnus.id}
                      type="button"
                      variant={turnus.id === selectedTurnusId ? 'secondary' : 'outline'}
                      aria-label={`${turnus.label} auswählen`}
                      aria-pressed={turnus.id === selectedTurnusId}
                      onClick={() => setSelectedTurnusId(turnus.id)}
                    >
                      <span className="grid gap-0.5">
                        <strong>{turnus.label}</strong>
                        <small>{turnus.members.length} Mitglieder · {turnus.members.filter(member => member.functional_role === 'leitung').length} Leitung</small>
                      </span>
                    </Button>
                  ))}
                </div>
              </TranslucentCard>
            ))}
          </nav>
          {selectedTurnus && (
            <TranslucentCard title={selectedTurnus.label}>
              <section className="mb-4 border-b border-border pb-4" aria-labelledby="pending-requests-heading">
                <h3 className="font-semibold" id="pending-requests-heading">Offene Anfragen ({selectedTurnus.request_summary?.pending ?? 0})</h3>
                <p className="my-3 rounded-md border border-warning bg-warning/10 p-3 font-semibold" role="alert">
                  {data.identity_verification_warning}
                </p>
                {selectedTurnus.pending_requests?.length
                  ? <ul className="mt-2">{selectedTurnus.pending_requests.map(request => <PendingRequest key={request.id} request={request} mutate={mutate} onDecided={requestDecided} />)}</ul>
                  : <p className="mt-1 text-sm text-muted-foreground">Keine offenen Anfragen.</p>}
              </section>
              <h3 className="font-semibold">Team ({selectedTurnus.members.length})</h3>
              {selectedTurnus.members.length
                ? <ul>{selectedTurnus.members.map(member => <Member key={member.id} member={member} mutate={mutate} onChanged={changed} canManageLeitung={canManageLeitung} canManageMemberships={canManageMemberships} />)}</ul>
                : <p>Noch keine Teammitglieder.</p>}
            </TranslucentCard>
          )}
        </div>
        {normalized && matchedPeople.length > 0 && (
          <section className="mt-5" aria-labelledby="person-search-heading">
            <h2 className="text-lg font-semibold" id="person-search-heading">Registrierte Personen</h2>
            <ul>{matchedPeople.map(person => {
              const availableForSelected = selectedContext != null && !(person.turnus_ids || []).includes(selectedTurnusId);
              return <li className="flex items-center justify-between gap-3 py-2" key={person.id}>
                <span><strong>{person.name}</strong><span className="block text-sm text-muted-foreground">{person.relationships.length ? person.relationships.join(' · ') : 'Keine Teamzugehörigkeiten · verfügbar'}</span></span>
                {availableForSelected && (canManageLeitung || canManageMemberships) && <Button aria-label={`${person.name} als ${canManageLeitung ? 'Leitung' : 'Teamer'} zu ${selectedContext.label} hinzufügen`} type="button" variant="outline" onClick={() => canManageLeitung ? addLeitung(person) : addTeamer(person)}><Plus aria-hidden="true" />{person.name} als {canManageLeitung ? 'Leitung' : 'Teamer'} zu {selectedContext.label} hinzufügen</Button>}
              </li>;
            })}</ul>
          </section>
        )}
        {!filtered.length && !matchedPeople.length && <p>Keine Turnusse oder Personen gefunden.</p>}
      </Column>
    </Columns>
  );
}

export const membershipRoutes = [{
  pattern: /^\/admin\/teams$/,
  page: 'admin-team-overview',
  title: 'Teams verwalten',
  domain: 'memberships',
  readContractKey: 'admin-team-overview',
  render: ({ data, mutate }) => <AdminTeamOverviewPage data={data} mutate={mutate} />,
}, {
  pattern: /^\/teams$/,
  page: 'team-management',
  title: 'Team verwalten',
  domain: 'memberships',
  readContractKey: 'team-management',
  render: ({ data, mutate }) => <AdminTeamOverviewPage data={data} mutate={mutate} />,
}];
