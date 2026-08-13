import { useEffect, useMemo, useState } from 'react';
import { Search } from 'lucide-react';

import { Column, Columns, TranslucentCard } from '../components';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { useErrorToast, useSuccessToast } from '../components/ui/toast';

function Member({ member, mutate, onChanged }) {
  const [busy, setBusy] = useState(false);
  const showError = useErrorToast();
  const showSuccess = useSuccessToast();
  const isLead = member.functional_role === 'leitung';
  const changeRole = async () => {
    const functionalRole = isLead ? 'teamer' : 'leitung';
    setBusy(true);
    try {
      await mutate(`/api/admin/memberships/${member.id}/role/`, { functional_role: functionalRole });
      onChanged(member.id, functionalRole);
      showSuccess(isLead ? `${member.name} ist jetzt Teamer.` : `${member.name} ist jetzt Leitung.`);
    } catch (error) {
      showError(error.payload?.detail || 'Die Funktionsrolle konnte nicht geändert werden.');
    } finally {
      setBusy(false);
    }
  };
  return (
    <li className="flex items-center justify-between gap-3 border-t border-border py-3 first:border-t-0">
      <div className="min-w-0">
        <p className="font-medium">{member.name}</p>
        <p className="text-sm text-muted-foreground">
          {member.role_label}{member.team_label ? ` · ${member.team_label}` : ''}
        </p>
      </div>
      <Button aria-label={`${member.name} ${isLead ? 'als Leitung entfernen' : 'als Leitung einsetzen'}`} type="button" size="sm" variant={isLead ? 'outline' : 'secondary'} disabled={busy} onClick={changeRole}>
        {busy ? 'Wird gespeichert…' : isLead ? 'Leitung entfernen' : 'Als Leitung einsetzen'}
      </Button>
    </li>
  );
}

export function AdminTeamOverviewPage({ data, mutate }) {
  const [query, setQuery] = useState('');
  const [years, setYears] = useState(data.years || []);
  const [selectedTurnusId, setSelectedTurnusId] = useState(() => data.years?.[0]?.turnuses?.[0]?.id ?? null);
  const normalized = query.trim().toLocaleLowerCase('de');
  const filtered = useMemo(() => years.map(year => ({
    ...year,
    turnuses: year.turnuses.filter(turnus => !normalized
      || turnus.label.toLocaleLowerCase('de').includes(normalized)
      || turnus.members.some(member => `${member.name} ${member.team_label} ${member.role_label}`.toLocaleLowerCase('de').includes(normalized))),
  })).filter(year => year.turnuses.length), [years, normalized]);
  const visibleTurnuses = useMemo(() => filtered.flatMap(year => year.turnuses), [filtered]);
  const selectedTurnus = visibleTurnuses.find(turnus => turnus.id === selectedTurnusId) || null;
  useEffect(() => {
    if (!selectedTurnus && visibleTurnuses.length) setSelectedTurnusId(visibleTurnuses[0].id);
    if (!visibleTurnuses.length && selectedTurnusId !== null) setSelectedTurnusId(null);
  }, [selectedTurnus, selectedTurnusId, visibleTurnuses]);
  const changed = (membershipId, functionalRole) => setYears(current => current.map(year => ({
    ...year,
    turnuses: year.turnuses.map(turnus => ({
      ...turnus,
      members: turnus.members.map(member => member.id === membershipId ? {
        ...member,
        functional_role: functionalRole,
        role_label: functionalRole === 'leitung' ? 'Leitung' : 'Teamer',
      } : member),
    })),
  })));
  return (
    <Columns className="mx-auto grid w-full max-w-6xl px-4 py-5">
      <Column className="min-w-0" id="team-management">
        <label className="relative mb-5 block max-w-xl">
          <span className="sr-only">Turnusse und Personen suchen</span>
          <Search className="pointer-events-none absolute left-3 top-2.5 size-5 text-muted-foreground" aria-hidden="true" />
          <Input className="pl-10" value={query} onChange={event => setQuery(event.target.value)} placeholder="Turnusse und Personen suchen" />
        </label>
        <div className="grid items-start gap-4 min-[901px]:grid-cols-[minmax(14rem,1fr)_minmax(0,3fr)]" data-slot="team-master-detail">
          <nav className="flex min-w-0 gap-4 overflow-x-visible max-[900px]:overflow-x-auto min-[901px]:flex-col" aria-label="Turnus auswählen">
            {filtered.map(year => (
              <section className="min-w-max min-[901px]:min-w-0" key={year.year}>
                <h2 className="mb-2 text-lg font-semibold">{year.year}</h2>
                <div className="flex gap-2 min-[901px]:flex-col">
                  {year.turnuses.map(turnus => (
                    <Button
                      className="justify-start whitespace-nowrap"
                      key={turnus.id}
                      type="button"
                      variant={turnus.id === selectedTurnusId ? 'secondary' : 'outline'}
                      aria-label={`${turnus.label} auswählen`}
                      aria-pressed={turnus.id === selectedTurnusId}
                      onClick={() => setSelectedTurnusId(turnus.id)}
                    >
                      {turnus.label}
                    </Button>
                  ))}
                </div>
              </section>
            ))}
          </nav>
          {selectedTurnus && (
            <TranslucentCard title={selectedTurnus.label} expanded onExpandedChange={() => {}}>
              {Number.isInteger(selectedTurnus.request_summary?.pending) && (
                <p className="mb-2 text-sm text-muted-foreground">{selectedTurnus.request_summary.pending} offene Anfragen</p>
              )}
              {selectedTurnus.members.length
                ? <ul>{selectedTurnus.members.map(member => <Member key={member.id} member={member} mutate={mutate} onChanged={changed} />)}</ul>
                : <p>Noch keine Teammitglieder.</p>}
            </TranslucentCard>
          )}
        </div>
        {!filtered.length && <p>Keine Turnusse oder Personen gefunden.</p>}
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
}];
