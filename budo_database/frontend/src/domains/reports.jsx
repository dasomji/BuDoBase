import { useMemo } from 'react';
import { Card, Column, Columns, RestForm, SearchTable } from '../components';
import { displayOrPlaceholder, formatGermanDate, linkKid, yesNo } from './shared';

export function SerialLetterPage({ data }) {
  return <main>{data.kids.map(kid => <div className="serienbrief-kid" key={kid.id}><div className="serienbrief_name">{kid.full_name}</div><div className="serienbrief-container"><div className="serienbrief">E-Card: {yesNo(kid.e_card)}</div><div className="serienbrief">Ausweis: {yesNo(kid.id_card)}</div></div><div className="serienbrief-container"><div className="serienbrief">Einverständnis für ärztliche Behandlung: {yesNo(kid.consent)}</div><div className="serienbrief">Rezeptfreie Medikamente: {displayOrPlaceholder(kid.over_the_counter_medication)}</div><div className="serienbrief">Medikamente auf Rezept: {displayOrPlaceholder(kid.prescription_medication)}</div></div><div className="serienbrief-container"><div className="serienbrief">Tetanusimpfung: {displayOrPlaceholder(kid.tetanus)}</div><div className="serienbrief">Zeckenimpfung: {displayOrPlaceholder(kid.tick_vaccine)}</div></div><div className="serienbrief-container"><div className="serienbrief">Krankheit: {displayOrPlaceholder(kid.illness)}</div><div className="serienbrief">Medikamente: {displayOrPlaceholder(kid.drugs)}</div><div className="serienbrief">Ernährung: {displayOrPlaceholder(kid.special_food)}</div></div></div>)}</main>;
}

export function MurderPage({ data }) {
  return <main><h2 className="murder_name">Mörderspiel: Kids & Team</h2><div className="murder-container">{data.kids.map(kid => <div className="murder_name" key={`kid-${kid.id}`}>{kid.full_name}</div>)}{data.team.map(member => <div className="murder_name" key={`team-${member.id}`}>{member.role_display} {member.rufname}</div>)}</div></main>;
}

export function FamiliesPage({ data, special = false }) {
  const groups = useMemo(() => data.kids.reduce((result, kid) => { const key = special ? kid.special_family : kid.budo_family; if (key) (result[key] ||= []).push(kid); return result; }, {}), [data.kids, special]);
  return <Columns>{Object.entries(groups).map(([name, kids]) => <Column key={name}><Card title={`${name} (${kids.length})`}><ul>{kids.map(kid => <li key={kid.id}>{linkKid(kid)} – {kid.age}</li>)}</ul></Card></Column>)}</Columns>;
}

export function BirthdaysPage({ data }) {
  const rows = data.kids.map(kid => ({ ...kid, sv: kid.sv_birthday, filterText: kid.full_name }));
  const columns = [
    { key: 'name', label: 'Name', render: linkKid },
    { key: 'birthday', label: 'DB-Geburtstag', render: row => displayOrPlaceholder(row.birthday ? `${formatGermanDate(row.birthday)}${row.sv && row.sv !== row.birthday ? ' ❗' : ''}` : null) },
    { key: 'sv', label: 'SV-Geburtstag', render: row => displayOrPlaceholder(formatGermanDate(row.sv)) },
    { key: 'match', label: 'Check', sortValue: row => row.birthday && row.sv ? Number(row.birthday === row.sv) : -1, render: row => row.birthday && row.sv ? row.birthday === row.sv ? '✅' : '❌' : '---' },
    { key: 'note', label: 'Notiz', sortable: false, render: row => <RestForm target="/kindergeburtstage/" token={data.csrf_token}><input type="hidden" name="kid_id" value={row.id} /><input name="notiz" placeholder="Notiz..." /><button className="button" type="submit">Speichern</button></RestForm> },
  ];
  return <main className="table-only" id="body-container"><SearchTable columns={columns} rows={rows} showFilter /></main>;
}

export function KidCountPage({ data }) {
  return <main className="gesamtkinderzahl-body"><div className="gesamtkinderzahl-container"><h1 className="gesamtkinderzahl">{data.totals.checked_in}/{data.totals.kids}</h1></div></main>;
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
    headerAction: data => <RestForm target="/update-birthdays-from-sv/" token={data.csrf_token}><button className="button" type="submit">🔄 Geburtstage aktualisieren</button></RestForm>,
    render: ({ data }) => <BirthdaysPage data={data} />,
  },
];
