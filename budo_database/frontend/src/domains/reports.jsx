import { useMemo } from 'react';
import { Printer, RefreshCwIcon } from 'lucide-react';

import { Card, DataTable, ResponsiveCardGrid, RestForm } from '../components';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import {
  displayOrPlaceholder,
  formatGermanDate,
  linkKid,
  PrintPageStyle,
  yesNo,
} from './shared';

export function SerialLetterPage({ data }) {
  return <main>{data.kids.map(kid => <article className="px-8 min-[901px]:px-24" key={kid.id}><h2 className="text-5xl print:[break-before:page]">{kid.full_name}</h2><div className="mb-4 border border-black p-8 text-xl"><p>E-Card: {yesNo(kid.e_card)}</p><p>Ausweis: {yesNo(kid.id_card)}</p></div><div className="mb-4 border border-black p-8 text-xl"><p>Einverständnis für ärztliche Behandlung: {yesNo(kid.consent)}</p><p>Rezeptfreie Medikamente: {displayOrPlaceholder(kid.over_the_counter_medication)}</p><p>Medikamente auf Rezept: {displayOrPlaceholder(kid.prescription_medication)}</p></div><div className="mb-4 border border-black p-8 text-xl"><p>Tetanusimpfung: {displayOrPlaceholder(kid.tetanus)}</p><p>Zeckenimpfung: {displayOrPlaceholder(kid.tick_vaccine)}</p></div><div className="mb-4 border border-black p-8 text-xl"><p>Krankheit: {displayOrPlaceholder(kid.illness)}</p><p>Medikamente: {displayOrPlaceholder(kid.drugs)}</p><p>Ernährung: {displayOrPlaceholder(kid.special_food)}</p></div></article>)}</main>;
}

export function MurderPage({ data }) {
  return (
    <>
      <PrintPageStyle />
      <main className="murder-print-page" id="body-container">
        <h2 className="w-auto px-8 pt-8">Mörderspiel: Kids & Team</h2>
        <div className="flex flex-wrap gap-8 p-8">
          {data.kids.map(kid => <div className="w-50" key={`kid-${kid.id}`}>{kid.full_name}</div>)}
          {data.team.map(member => <div className="w-50" key={`team-${member.id}`}>{member.role_display} {member.rufname}</div>)}
        </div>
      </main>
    </>
  );
}

export function FamiliesPage({ data }) {
  const groups = useMemo(() => data.kids.reduce((result, kid) => {
    if (kid.budo_family) (result[kid.budo_family] ||= []).push(kid);
    return result;
  }, {}), [data.kids]);
  return (
    <>
      <PrintPageStyle />
      <ResponsiveCardGrid className="families-screen" independentColumns maxColumns={2}>
        {Object.entries(groups).map(([name, kids]) => (
          <Card title={`${name} (${kids.length})`} key={name}>
            <ul className="m-0 grid [grid-template-columns:repeat(auto-fit,minmax(min(14rem,100%),1fr))] gap-x-4 gap-y-1 pl-4 [&>li]:min-w-0 [&>li]:[overflow-wrap:anywhere]">
              {kids.map(kid => <li key={kid.id}>{linkKid(kid)} – {kid.age}</li>)}
            </ul>
          </Card>
        ))}
      </ResponsiveCardGrid>
      <section className="families-page allocation-page" aria-hidden="true" aria-label="BuDo-Familien-Listen">
        <div className="allocation-print-pages">
          {Object.entries(groups).map(([name, kids]) => (
            <article className="allocation-print-page" key={name}>
              <div className="allocation-print-illustration" aria-hidden="true" />
              <h1>{name}</h1>
              <ul>
                {kids.map(kid => <li key={kid.id}>{kid.full_name}</li>)}
              </ul>
            </article>
          ))}
        </div>
      </section>
    </>
  );
}

export function BirthdaysPage({ data }) {
  const rows = data.kids.map(kid => ({ ...kid, sv: kid.sv_birthday, filterText: kid.full_name }));
  const columns = [
    { key: 'name', label: 'Name', render: linkKid },
    { key: 'birthday', label: 'DB-Geburtstag', render: row => displayOrPlaceholder(row.birthday ? `${formatGermanDate(row.birthday)}${row.sv && row.sv !== row.birthday ? ' ❗' : ''}` : null) },
    { key: 'sv', label: 'SV-Geburtstag', render: row => displayOrPlaceholder(formatGermanDate(row.sv)) },
    { key: 'match', label: 'Check', sortValue: row => row.birthday && row.sv ? Number(row.birthday === row.sv) : -1, render: row => row.birthday && row.sv ? row.birthday === row.sv ? '✅' : '❌' : '---' },
    { key: 'note', label: 'Notiz', sortable: false, render: row => <RestForm target="/kindergeburtstage/" token={data.csrf_token}><input type="hidden" name="kid_id" value={row.id} /><Input name="notiz" placeholder="Notiz..." /><Button type="submit">Speichern</Button></RestForm> },
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
    domain: 'reports',
    readContractKey: 'murder-game',
    headerAction: () => (
      <Button
        aria-label="Drucken"
        className="mobile-icon-action"
        size="responsive-icon"
        type="button"
        onClick={() => window.print()}
      >
        <span className="desktop-action-label">Drucken</span>
        <Printer className="mobile-action-label" aria-hidden="true" />
      </Button>
    ),
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
    headerAction: () => (
      <Button
        aria-label="Drucken"
        className="mobile-icon-action"
        size="responsive-icon"
        type="button"
        onClick={() => window.print()}
      >
        <span className="desktop-action-label">Drucken</span>
        <Printer className="mobile-action-label" aria-hidden="true" />
      </Button>
    ),
    render: ({ data }) => <FamiliesPage data={data} />,
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
          size="responsive-icon"
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
