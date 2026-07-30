import { useCallback, useEffect, useState } from 'react';

import { Card, ResponsiveCardGrid } from '../components';
import { Button } from '../components/ui/button';
import { useErrorToast } from '../components/ui/toast';
import { FirstAidEntry, NoteEntry } from './first-aid';
import { FirstAidGallery } from './first-aid-gallery';
import { HappyCleaningStationTodoDocument } from './happyCleaningStationDetail';
import { formatGermanDate, formatKidBirthday, linkKid, money } from './shared';

function appendUnique(current, incoming) {
  const existing = new Set(current.map(item => item.id));
  return [...current, ...incoming.filter(item => !existing.has(item.id))];
}

function ActivityList({ kind, initialPage, fetchImpl, onItemsChange }) {
  const [page, setPage] = useState(initialPage);
  const [loading, setLoading] = useState(false);
  const showError = useErrorToast();
  const textActivity = kind !== 'transactions';
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
      const response = await fetchImpl(`/api/route-data/dashboard/?${query}`, {
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
      <ul>{page.items.map(item => (
        kind === 'first_aid'
          ? <FirstAidEntry entry={item} childName={item.kid} showChildLink key={item.id} />
          : kind === 'notes'
            ? <NoteEntry entry={item} childName={item.kid} showChildLink key={item.id} />
          : <li key={item.id}>
            <p><strong>{item.author}</strong> am {formatGermanDate(item.date)}: <a href={`/kid_details/${item.kid_id}`}>{item.kid}</a></p>
            <p>{textActivity ? item.text : `Betrag: ${money(item.amount)}`}</p>
          </li>
      ))}</ul>
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

function GoodToKnowKidList({ kids }) {
  return <>{kids.map(kid => (
    <div className="print-nobreak" key={kid.id}>
      <p><span className="label">{linkKid(kid)}</span>: {kid.age}</p>
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

  return (
    <ResponsiveCardGrid independentColumns>
      <Card title={`Erstes Mal im BuDO: ${firstTimers.length}/${totals.kids}`} id="db-ersties" initiallyClosed>
        <GoodToKnowKidList kids={firstTimers} />
      </Card>
      <Card title={`Einwöchige: ${oneWeek.length}`} id="db-einwöchig" initiallyClosed>
        <GoodToKnowKidList kids={oneWeek} />
      </Card>
      <Card title="Gesundheitliches" id="db-gesundheit" initiallyClosed>
        <GoodToKnowKidList kids={health} />
      </Card>
      <Card title="Essen & Allergien" id="db-essen" initiallyClosed>
        {food.map(kid => (
          <div className="print-nobreak" key={kid.id}>
            <p>{linkKid(kid)}: {kid.age}</p>
            <p>{kid.food} · {kid.special_food}</p>
          </div>
        ))}
      </Card>
      <Card title={`Geburtstagskinder: ${birthdays.length}`} id="db-geburtstagskinder">
        {birthdays.map(kid => <p key={kid.id}>{linkKid(kid)}: {formatKidBirthday(kid)}</p>)}
      </Card>
      <Card title={`Verabschiedungsliste: ${goodbyes.length}`} id="db-sechzehner">
        {goodbyes.map(kid => <p key={kid.id}>{linkKid(kid)}: {kid.age} – {formatKidBirthday(kid)}</p>)}
      </Card>
    </ResponsiveCardGrid>
  );
}

function AssignmentSection({ id, name, href, kidIds, kidsById }) {
  const assignedKids = (kidIds || []).map(kidId => kidsById.get(Number(kidId))).filter(Boolean);
  return (
    <section className="[&+&]:mt-3 [&+&]:border-t [&+&]:border-foreground/20 [&+&]:pt-3" aria-labelledby={id}>
      <h3 className="m-0 text-base" id={id}><a href={href}>{name}</a></h3>
      {assignedKids.length
        ? <ul>{assignedKids.map(kid => <li key={kid.id}>{linkKid(kid)}</li>)}</ul>
        : <p>Keine Kinder eingeteilt.</p>}
    </section>
  );
}

function FocusAssignment({ focus, kidsById }) {
  return (
    <AssignmentSection
      id={`dashboard-focus-${focus.id}`}
      name={focus.name}
      href={`/schwerpunkt/${focus.id}/`}
      kidIds={focus.kid_ids}
      kidsById={kidsById}
    />
  );
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
  const kidsById = new Map(kids.map(kid => [Number(kid.id), kid]));
  const focusesByWeek = week => focuses.filter(focus => focus.week === week);
  const personalFocusCard = (week, number) => assignmentsComplete[week] && (
    <Card title={`Mein SWP ${number}`} id={`db-swp-${number}`}>
      {focusesByWeek(week).length
        ? focusesByWeek(week).map(focus => <FocusAssignment focus={focus} kidsById={kidsById} key={focus.id} />)
        : <p>Kein Schwerpunkt zugeteilt.</p>}
    </Card>
  );
  return (
    <FirstAidGallery entries={[...noteItems, ...firstAidItems]}>
      <ResponsiveCardGrid independentColumns>
      <Card title={`Kinder: ${totals.checked_in}`} id="db-kinderübersicht">
        <p><span className="label">Eingecheckt</span>: {totals.checked_in}/{totals.kids}</p>
        <p><span className="label">Geschlechter</span>: {kids.filter(kid => kid.sex === 'männlich').length} ♂ // {kids.filter(kid => kid.sex === 'weiblich').length} ♀ // {kids.filter(kid => !['männlich', 'weiblich'].includes(kid.sex)).length} ⚧</p>
        <p><span className="label">Kids mit BuDo-Erfahrung</span>: {kids.filter(kid => kid.budo_experience).length}</p>
        <p><span className="label">Zuganreise</span>: {totals.train_arrival}</p>
        <p><span className="label">Zugabreise</span>: {totals.train_departure}</p>
      </Card>
      <Card title="Notizen" id="db-notizen"><ActivityList kind="notes" initialPage={activity.notes} fetchImpl={fetchImpl} onItemsChange={setNoteItems} /></Card>
      <Card title="Erste Hilfe" id="db-erste-hilfe"><ActivityList kind="first_aid" initialPage={activity.first_aid} fetchImpl={fetchImpl} onItemsChange={handleFirstAidItemsChange} /></Card>
      <Card title="Meine BuDo-Familie" id="db-budo-familie">
        {profile?.budo_family
          ? <><p><span className="label">{familyLabels[profile.budo_family] || profile.budo_family}</span></p>{familyKids.length ? <ul>{familyKids.map(kid => <li key={kid.id}>{linkKid(kid)}</li>)}</ul> : <p>Keine Kinder in dieser BuDo-Familie.</p>}</>
          : <p>Noch keine BuDo-Familie im Profil zugeordnet.</p>}
      </Card>
      {personalFocusCard('w1', 1)}
      {personalFocusCard('w2', 2)}
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
      <Card title="Taschengeldtransaktionen" id="db-geld"><ActivityList kind="transactions" initialPage={activity.transactions} fetchImpl={fetchImpl} /></Card>
      </ResponsiveCardGrid>
    </FirstAidGallery>
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
    render: ({ data }) => <GoodToKnowPage data={data} />,
  },
];
