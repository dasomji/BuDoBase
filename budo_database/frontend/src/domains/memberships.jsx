import { useMemo, useState } from 'react';
import { Search } from 'lucide-react';

import { Column, Columns, TranslucentCard } from '../components';
import { Button } from '../components/ui/button';
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
      <Button type="button" size="sm" variant={isLead ? 'outline' : 'secondary'} disabled={busy} onClick={changeRole}>
        {busy ? 'Wird gespeichert…' : isLead ? 'Leitung entfernen' : 'Als Leitung einsetzen'}
      </Button>
    </li>
  );
}

export function AdminTeamOverviewPage({ data, mutate }) {
  const [query, setQuery] = useState('');
  const [years, setYears] = useState(data.years || []);
  const normalized = query.trim().toLocaleLowerCase('de');
  const filtered = useMemo(() => years.map(year => ({
    ...year,
    turnuses: year.turnuses.filter(turnus => !normalized
      || turnus.label.toLocaleLowerCase('de').includes(normalized)
      || turnus.members.some(member => `${member.name} ${member.team_label} ${member.role_label}`.toLocaleLowerCase('de').includes(normalized))),
  })).filter(year => year.turnuses.length), [years, normalized]);
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
    <Columns className="mx-auto w-full max-w-6xl px-4 py-5">
      <Column id="single-column">
        <label className="relative mb-5 block max-w-xl">
          <span className="sr-only">Turnusse und Personen suchen</span>
          <Search className="pointer-events-none absolute left-3 top-2.5 size-5 text-muted-foreground" aria-hidden="true" />
          <input className="w-full rounded-md border border-input bg-popover py-2 pl-10 pr-3 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring" value={query} onChange={event => setQuery(event.target.value)} placeholder="Turnusse und Personen suchen" />
        </label>
        <div className="space-y-6">
          {filtered.map(year => (
            <TranslucentCard key={year.year} title={String(year.year)} showToggleIcon>
              <div className="grid gap-4 min-[901px]:grid-cols-2">
                {year.turnuses.map(turnus => (
                  <TranslucentCard key={turnus.id} title={turnus.label} showToggleIcon>
                    <p className="mb-2 text-sm text-muted-foreground">{turnus.request_summary.pending} offene Anfragen</p>
                    {turnus.members.length ? <ul>{turnus.members.map(member => <Member key={member.id} member={member} mutate={mutate} onChanged={changed} />)}</ul> : <p>Noch keine Teammitglieder.</p>}
                  </TranslucentCard>
                ))}
              </div>
            </TranslucentCard>
          ))}
          {!filtered.length && <p>Keine Turnusse oder Personen gefunden.</p>}
        </div>
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
