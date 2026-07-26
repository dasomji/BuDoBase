import { useMemo } from 'react';
import { RefreshCwIcon } from 'lucide-react';

import { Card, Column, Columns, DataTable, RestForm } from '../components';
import { Button } from '../components/ui/button';
import { displayOrPlaceholder, formatGermanDate, linkKid, yesNo } from './shared';

export function SerialLetterPage({ data }) {
  return <main>{data.kids.map(kid => <article className="px-8 min-[901px]:px-24" key={kid.id}><h2 className="text-5xl print:[break-before:page]">{kid.full_name}</h2><div className="mb-4 border border-black p-8 text-xl"><p>E-Card: {yesNo(kid.e_card)}</p><p>Ausweis: {yesNo(kid.id_card)}</p></div><div className="mb-4 border border-black p-8 text-xl"><p>Einverständnis für ärztliche Behandlung: {yesNo(kid.consent)}</p><p>Rezeptfreie Medikamente: {displayOrPlaceholder(kid.over_the_counter_medication)}</p><p>Medikamente auf Rezept: {displayOrPlaceholder(kid.prescription_medication)}</p></div><div className="mb-4 border border-black p-8 text-xl"><p>Tetanusimpfung: {displayOrPlaceholder(kid.tetanus)}</p><p>Zeckenimpfung: {displayOrPlaceholder(kid.tick_vaccine)}</p></div><div className="mb-4 border border-black p-8 text-xl"><p>Krankheit: {displayOrPlaceholder(kid.illness)}</p><p>Medikamente: {displayOrPlaceholder(kid.drugs)}</p><p>Ernährung: {displayOrPlaceholder(kid.special_food)}</p></div></article>)}</main>;
}

export function MurderPage({ data }) {
  return <main><h2 className="w-auto px-8 pt-8">Mörderspiel: Kids & Team</h2><div className="flex flex-wrap gap-8 p-8">{data.kids.map(kid => <div className="w-50" key={`kid-${kid.id}`}>{kid.full_name}</div>)}{data.team.map(member => <div className="w-50" key={`team-${member.id}`}>{member.role_display} {member.rufname}</div>)}</div></main>;
}

export function FamiliesPage({ data, special = false }) {
  const groups = useMemo(() => data.kids.reduce((result, kid) => {
    const key = special ? kid.special_family : kid.budo_family;
    if (key) (result[key] ||= []).push(kid);
    return result;
  }, {}), [data.kids, special]);
  return (
    <Columns className="grid grid-cols-1 items-start min-[901px]:grid-cols-2">
      {Object.entries(groups).map(([name, kids]) => (
        <Column className="min-w-0 w-full [&>.card]:w-full" key={name}>
          <Card title={`${name} (${kids.length})`}>
            <ul className="m-0 grid grid-cols-1 gap-x-4 gap-y-1 pl-4 min-[901px]:grid-cols-2 [&>li]:min-w-0 [&>li]:[overflow-wrap:anywhere]">
              {kids.map(kid => <li key={kid.id}>{linkKid(kid)} – {kid.age}</li>)}
            </ul>
          </Card>
        </Column>
      ))}
    </Columns>
  );
}

export function BirthdaysPage({ data }) {
  const rows = data.kids.map(kid => ({ ...kid, sv: kid.sv_birthday, filterText: kid.full_name }));
  const columns = [
    { key: 'name', label: 'Name', render: linkKid },
    { key: 'birthday', label: 'DB-Geburtstag', render: row => displayOrPlaceholder(row.birthday ? `${formatGermanDate(row.birthday)}${row.sv && row.sv !== row.birthday ? ' ❗' : ''}` : null) },
    { key: 'sv', label: 'SV-Geburtstag', render: row => displayOrPlaceholder(formatGermanDate(row.sv)) },
    { key: 'match', label: 'Check', sortValue: row => row.birthday && row.sv ? Number(row.birthday === row.sv) : -1, render: row => row.birthday && row.sv ? row.birthday === row.sv ? '✅' : '❌' : '---' },
    { key: 'note', label: 'Notiz', sortable: false, render: row => <RestForm target="/kindergeburtstage/" token={data.csrf_token}><input type="hidden" name="kid_id" value={row.id} /><input name="notiz" placeholder="Notiz..." /><Button type="submit">Speichern</Button></RestForm> },
  ];
  return <main className="table-only" id="body-container"><DataTable columns={columns} rows={rows} showFilter /></main>;
}

export function KidCountPage({ data }) {
  return <main className="m-0 flex h-screen items-center justify-center p-0"><div className="w-full box-border p-8"><h1 className="m-0 overflow-hidden p-0 text-center text-[20vw] text-ellipsis whitespace-nowrap">{data.totals.checked_in}/{data.totals.kids}</h1></div></main>;
}

export const reportRoutes = [
  {
    pattern: /^\/serienbrief$/,
    page: 'serial-letter',
    title: 'Serienbrief',
    standalone: true,
    domain: 'reports',
    readContractKey: 'serial-letter',
    render: ({ data }) => <SerialLetterPage data={data} />,
  },
  {
    pattern: /^\/murdergame$/,
    page: 'murder',
    title: 'Mörderspiel',
    standalone: true,
    domain: 'reports',
    readContractKey: 'murder-game',
    render: ({ data }) => <MurderPage data={data} />,
  },
  {
    pattern: /^\/kindergesamtzahl$/,
    page: 'kid-count',
    title: 'Kindergesamtzahl',
    standalone: true,
    domain: 'reports',
    readContractKey: 'kid-count',
    render: ({ data }) => <KidCountPage data={data} />,
  },
  {
    pattern: /^\/budo_familien$/,
    page: 'families',
    title: 'BuDo Familien',
    domain: 'reports',
    readContractKey: 'families',
    render: ({ data }) => <FamiliesPage data={data} />,
  },
  {
    pattern: /^\/spezial_familien$/,
    page: 'special-families',
    title: 'Spezial Familien',
    domain: 'reports',
    readContractKey: 'special-families',
    render: ({ data }) => <FamiliesPage data={data} special />,
  },
  {
    pattern: /^\/kindergeburtstage$/,
    page: 'birthdays',
    title: 'Kindergeburtstage',
    domain: 'reports',
    readContractKey: 'birthdays',
    headerAction: data => (
      <RestForm target="/update-birthdays-from-sv/" token={data.csrf_token}>
        <Button
          aria-label="Geburtstage aktualisieren"
          className="mobile-icon-action"
          type="submit"
        >
          <span className="desktop-action-label">Geburtstage aktualisieren</span>
          <RefreshCwIcon className="mobile-action-label" aria-hidden="true" />
        </Button>
      </RestForm>
    ),
    render: ({ data }) => <BirthdaysPage data={data} />,
  },
];
