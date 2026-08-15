import { useCallback, useEffect, useState } from 'react';
import { Printer } from 'lucide-react';

import { Card, Columns, DataTable, ResponsiveCardGrid } from '../components';
import { Button } from '../components/ui/button';
import { useErrorToast } from '../components/ui/toast';
import { FirstAidEntry, NoteEntry } from './first-aid';
import { entryPhotoKinds, EntryPhotoGallery } from './entry-photo-gallery';
import { HappyCleaningStationTodoDocument } from './happyCleaningStationDetail';
import { formatGermanDate, formatKidBirthday, linkKid, money, PrintPageStyle } from './shared';

function appendUnique(current, incoming) {
  const existing = new Set(current.map(item => item.id));
  return [...current, ...incoming.filter(item => !existing.has(item.id))];
}

const transactionColumns = [
  {
    key: 'kid',
    label: 'Kind',
    render: transaction => <a href={`/kid_details/${transaction.kid_id}`}>{transaction.kid}</a>,
  },
  {
    key: 'date',
    label: 'Datum',
    render: transaction => {
      const formatted = formatGermanDate(transaction.date);
      return formatted?.slice(0, 5);
    },
  },
  {
    key: 'amount',
    label: 'Betrag',
    render: transaction => money(transaction.amount),
    sortValue: transaction => Number(transaction.amount),
  },
  { key: 'author', label: 'Autor' },
];

function ActivityList({ kind, initialPage, fetchImpl, onItemsChange, contractKey = 'dashboard' }) {
  const [page, setPage] = useState(initialPage);
  const [loading, setLoading] = useState(false);
  const showError = useErrorToast();
  const label = kind === 'notes' ? 'Notizen' : kind === 'first_aid' ? 'EH-Einträge' : 'Transaktionen';

  useEffect(() => {
    setPage(initialPage);
    setLoading(false);
  }, [initialPage]);

  useEffect(() => {
    onItemsChange?.(page.items);
  }, [onItemsChange, page.items]);

  const loadMore = async () => {
    setLoading(true);
    try {
      const query = new URLSearchParams({ activity: kind, cursor: page.next_cursor });
      const response = await fetchImpl(`/api/route-data/${contractKey}/?${query}`, {
        credentials: 'same-origin',
      });
      if (!response.ok) throw new Error(`Dashboard activity request failed (${response.status})`);
      const nextPage = (await response.json()).activity[kind];
      setPage(current => ({
        ...nextPage,
        items: appendUnique(current.items, nextPage.items),
      }));
    } catch {
      showError(`Ältere ${label} konnten nicht geladen werden.`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      {kind === 'transactions'
        ? <DataTable columns={transactionColumns} rows={page.items} empty="Keine Transaktionen" />
        : <ul>{page.items.map(item => (
          kind === 'first_aid'
            ? <FirstAidEntry entry={item} childName={item.kid} showChildLink key={item.id} />
            : <NoteEntry entry={item} childName={item.kid} showChildLink key={item.id} />
        ))}</ul>}
      {page.has_more && (
        <Button type="button" disabled={loading} onClick={loadMore}>
          {loading ? `Ältere ${label} werden geladen…` : `Ältere ${label} laden`}
        </Button>
      )}
    </>
  );
}

const familyLabels = {
  S: 'Smallie',
  M: 'Medi',
  L: 'Largie',
  XL: 'X-largie',
};

const goodToKnowKidName = (kid, plainNames) => plainNames ? kid.full_name : linkKid(kid);

function GoodToKnowKidList({ kids, plainNames = false }) {
  return <>{kids.map(kid => (
    <div className="print-nobreak" key={kid.id}>
      <p><span className="label">{goodToKnowKidName(kid, plainNames)}</span>: {kid.age}</p>
      {kid.illness && <p>Krankheiten: {kid.illness}</p>}
      {kid.drugs && <p>Medikamente: {kid.drugs}</p>}
    </div>
  ))}</>;
}

export function GoodToKnowPage({ data }) {
  const { kids, totals } = data;
  const firstTimers = kids.filter(kid => kid.budo_experience === false);
  const oneWeek = kids.filter(kid => kid.weeks === 1);
  const health = kids.filter(kid => kid.drugs || kid.illness);
  const food = kids.filter(kid => kid.special_food);
  const birthdays = kids.filter(kid => kid.birthday_during_turnus);
  const goodbyes = kids.filter(kid => kid.age > 14.8).sort((left, right) => left.age - right.age);
  const cards = [
    {
      id: 'db-ersties',
      title: `Erstes Mal im BuDO: ${firstTimers.length}/${totals.kids}`,
      initiallyClosed: true,
      content: plainNames => <GoodToKnowKidList kids={firstTimers} plainNames={plainNames} />,
    },
    {
      id: 'db-einwöchig',
      title: `Einwöchige: ${oneWeek.length}`,
      initiallyClosed: true,
      content: plainNames => <GoodToKnowKidList kids={oneWeek} plainNames={plainNames} />,
    },
    {
      id: 'db-gesundheit',
      title: 'Gesundheitliches',
      initiallyClosed: true,
      content: plainNames => <GoodToKnowKidList kids={health} plainNames={plainNames} />,
    },
    {
      id: 'db-essen',
      title: 'Essen & Allergien',
      initiallyClosed: true,
      content: plainNames => food.map(kid => (
        <div className="print-nobreak" key={kid.id}>
          <p>{goodToKnowKidName(kid, plainNames)}: {kid.age}</p>
          <p>{kid.food} · {kid.special_food}</p>
        </div>
      )),
    },
    {
      id: 'db-geburtstagskinder',
      title: `Geburtstagskinder: ${birthdays.length}`,
      content: plainNames => birthdays.map(kid => (
        <p key={kid.id}>{goodToKnowKidName(kid, plainNames)}: {formatKidBirthday(kid)}</p>
      )),
    },
    {
      id: 'db-sechzehner',
      title: `Verabschiedungsliste: ${goodbyes.length}`,
      content: plainNames => goodbyes.map(kid => (
        <p key={kid.id}>{goodToKnowKidName(kid, plainNames)}: {kid.age} – {formatKidBirthday(kid)}</p>
      )),
    },
  ];

  return (
    <>
      <PrintPageStyle />
      <ResponsiveCardGrid className="good-to-know-screen" independentColumns>
        {cards.map(card => (
          <Card
            id={card.id}
            initiallyClosed={card.initiallyClosed}
            key={card.id}
            title={card.title}
          >
            {card.content(false)}
          </Card>
        ))}
      </ResponsiveCardGrid>
      <section
        aria-hidden="true"
        aria-label="Gut-zu-wissen-Druckseiten"
        className="good-to-know-print-pages"
      >
        {cards.map(card => (
          <article className="good-to-know-print-page" key={card.id}>
            <h1>{card.title}</h1>
            {card.content(true)}
          </article>
        ))}
      </section>
    </>
  );
}

function FocusAssignment({ focus, kidsById }) {
  const assignedKids = (focus.kid_ids || [])
    .map(kidId => kidsById.get(Number(kidId)))
    .filter(Boolean);
  return assignedKids.length
    ? <ul>{assignedKids.map(kid => <li key={kid.id}>{linkKid(kid)}</li>)}</ul>
    : <p>Keine Kinder eingeteilt.</p>;
}

function HappyCleaningStationCard({ event, station, kidsById, mutate, refresh }) {
  const assignedKids = (station.kid_ids || [])
    .map(id => kidsById.get(Number(id)))
    .filter(Boolean)
    .sort((left, right) => left.full_name.localeCompare(right.full_name, 'de', {
      sensitivity: 'base',
    }));
  const assignmentHref = `/happy-cleaning/${event.id}/assignment/`;
  const detailHref = `/happy-cleaning/?event_id=${event.id}&station_id=${station.id}`;
  return (
    <Card
      className="transparent"
      id={`db-happy-cleaning-station-${station.id}`}
      title={`Happy Cleaning ${event.display_number}: ${station.name}`}
    >
      <div className="grid grid-cols-1 items-start gap-4">
        <Card
          actions={<Button href={assignmentHref}>Zur Einteilung</Button>}
          headingLevel={3}
          title="Kinder"
        >
          {assignedKids.length
            ? <ul>{assignedKids.map(kid => <li key={kid.id}>{linkKid(kid)}</li>)}</ul>
            : <p>Keine Kinder eingeteilt.</p>}
        </Card>
        <Card
          actions={<Button variant="secondary" href={detailHref}>{station.name} Details</Button>}
          headingLevel={3}
          title="To-Dos"
        >
          <HappyCleaningStationTodoDocument
            eventId={event.id}
            stationId={station.id}
            document={station.document}
            mutate={mutate}
            refresh={refresh}
          />
        </Card>
      </div>
    </Card>
  );
}

export function DashboardPage({ data, fetchImpl = fetch, mutate, refresh, onFirstAidItemsChange }) {
  if (data.membership_awaiting) return null;
  const {
    profile,
    totals,
    kids,
    focuses = [],
    focus_assignments_complete: assignmentsComplete = {},
    happy_cleanings: happyCleanings = [],
    activity,
  } = data;
  const [firstAidItems, setFirstAidItems] = useState(activity.first_aid.items);
  const [noteItems, setNoteItems] = useState(activity.notes.items);
  const handleFirstAidItemsChange = useCallback(items => {
    setFirstAidItems(items);
    onFirstAidItemsChange?.(items);
  }, [onFirstAidItemsChange]);
  const familyKids = profile?.budo_family
    ? kids.filter(kid => kid.budo_family === profile.budo_family)
    : [];
  const familyTitle = profile?.budo_family
    ? familyLabels[profile.budo_family] || profile.budo_family
    : 'Meine BuDo-Familie';
  const kidsById = new Map(kids.map(kid => [Number(kid.id), kid]));
  const personalFocusCards = (week, number) => assignmentsComplete[week]
    ? focuses.filter(focus => focus.week === week).map(focus => (
      <Card title={`SWP ${number}: ${focus.name}`} id={`db-swp-${focus.id}`} key={focus.id}>
        <FocusAssignment focus={focus} kidsById={kidsById} />
      </Card>
    ))
    : [];
  return (
      <ResponsiveCardGrid independentColumns>
      <Card title={`Kinder: ${totals.checked_in}`} id="db-kinderübersicht">
        <p><span className="label">Eingecheckt</span>: {totals.checked_in}/{totals.kids}</p>
        <p><span className="label">Geschlechter</span>: {kids.filter(kid => kid.sex === 'männlich').length} ♂ // {kids.filter(kid => kid.sex === 'weiblich').length} ♀ // {kids.filter(kid => !['männlich', 'weiblich'].includes(kid.sex)).length} ⚧</p>
        <p><span className="label">Kids mit BuDo-Erfahrung</span>: {kids.filter(kid => kid.budo_experience).length}</p>
        <p><span className="label">Zuganreise</span>: {totals.train_arrival}</p>
        <p><span className="label">Zugabreise</span>: {totals.train_departure}</p>
      </Card>
      <EntryPhotoGallery entries={noteItems} photoKind={entryPhotoKinds.notes}>
        <Card title="Notizen" id="db-notizen"><ActivityList kind="notes" initialPage={activity.notes} fetchImpl={fetchImpl} onItemsChange={setNoteItems} /></Card>
      </EntryPhotoGallery>
      <EntryPhotoGallery entries={firstAidItems}>
        <Card title="Erste Hilfe" id="db-erste-hilfe"><ActivityList kind="first_aid" initialPage={activity.first_aid} fetchImpl={fetchImpl} onItemsChange={handleFirstAidItemsChange} /></Card>
      </EntryPhotoGallery>
      <Card title={familyTitle} id="db-budo-familie">
        {profile?.budo_family
          ? familyKids.length
            ? <ul>{familyKids.map(kid => <li key={kid.id}>{linkKid(kid)}</li>)}</ul>
            : <p>Keine Kinder in dieser BuDo-Familie.</p>
          : <p>Noch keine BuDo-Familie im Profil zugeordnet.</p>}
      </Card>
      {personalFocusCards('w1', 1)}
      {personalFocusCards('w2', 2)}
      {happyCleanings.filter(event => event.assignments_complete).flatMap(event => (
        event.stations.map(station => (
          <HappyCleaningStationCard
            event={event}
            station={station}
            kidsById={kidsById}
            mutate={mutate}
            refresh={refresh}
            key={station.id}
          />
        ))
      ))}
      </ResponsiveCardGrid>
  );
}

export function PocketMoneyPage({ data, fetchImpl = fetch }) {
  const { totals, activity } = data;
  return (
    <Columns>
      <div className="w-full max-w-[800px]">
        <Card title="Taschengeldkasse" id="taschengeldkasse">
          <p><span className="label">Gesamt eingezahlt</span>: {money(totals.pocket_money_paid)}</p>
          <p><span className="label">Gesamt ausgegeben</span>: {money(totals.pocket_money_paid - totals.pocket_money)}</p>
          <p><span className="label">Kassenstand</span>: {money(totals.pocket_money)}</p>
          <ActivityList
            kind="transactions"
            initialPage={activity.transactions}
            fetchImpl={fetchImpl}
            contractKey="pocket-money"
          />
        </Card>
      </div>
    </Columns>
  );
}

export const dashboardRoutes = [
  {
    pattern: /^\/$|^\/dashboard$/,
    page: 'dashboard',
    title: 'BuDo Dashboard',
    domain: 'dashboard',
    readContractKey: 'dashboard',
    render: ({ data, fetchImpl, mutate, refresh }) => (
      <DashboardPage data={data} fetchImpl={fetchImpl} mutate={mutate} refresh={refresh} />
    ),
  },
  {
    pattern: /^\/gut-zu-wissen$/,
    page: 'good-to-know',
    title: 'Gut zu wissen',
    domain: 'dashboard',
    readContractKey: 'gut-zu-wissen',
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
    render: ({ data }) => <GoodToKnowPage data={data} />,
  },
  {
    pattern: /^\/taschengeld$/,
    page: 'pocket-money',
    title: 'Taschengeld',
    domain: 'dashboard',
    readContractKey: 'pocket-money',
    render: ({ data, fetchImpl }) => <PocketMoneyPage data={data} fetchImpl={fetchImpl} />,
  },
];
