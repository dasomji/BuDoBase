import { Children, useEffect, useState } from 'react';

import { Card, Column, Columns } from '../components';
import { formatGermanDate, formatKidBirthday, linkKid, money } from './shared';

function appendUnique(current, incoming) {
  const existing = new Set(current.map(item => item.id));
  return [...current, ...incoming.filter(item => !existing.has(item.id))];
}

function ActivityList({ kind, initialPage, fetchImpl }) {
  const [page, setPage] = useState(initialPage);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(false);
  const notes = kind === 'notes';
  const label = notes ? 'Notizen' : 'Transaktionen';

  useEffect(() => {
    setPage(initialPage);
    setLoading(false);
    setError(false);
  }, [initialPage]);

  const loadMore = async () => {
    setLoading(true);
    setError(false);
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
      setError(true);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <ul>{page.items.map(item => (
        <li key={item.id}>
          <p><strong>{item.author}</strong> am {formatGermanDate(item.date)}: <a href={`/kid_details/${item.kid_id}`}>{item.kid}</a></p>
          <p>{notes ? item.text : `Betrag: ${money(item.amount)}`}</p>
        </li>
      ))}</ul>
      {error && <p className="activity-error" role="alert">Ältere {label} konnten nicht geladen werden.</p>}
      {page.has_more && (
        <button className="button" type="button" disabled={loading} onClick={loadMore}>
          {loading ? `Ältere ${label} werden geladen…` : `Ältere ${label} laden`}
        </button>
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

function FocusAssignment({ focus, kidsById }) {
  const assignedKids = (focus.kid_ids || []).map(id => kidsById.get(Number(id))).filter(Boolean);
  return (
    <section className="dashboard-focus" aria-labelledby={`dashboard-focus-${focus.id}`}>
      <h3 id={`dashboard-focus-${focus.id}`}><a href={`/schwerpunkt/${focus.id}/`}>{focus.name}</a></h3>
      {assignedKids.length
        ? <ul>{assignedKids.map(kid => <li key={kid.id}>{linkKid(kid)}</li>)}</ul>
        : <p>Keine Kinder eingeteilt.</p>}
    </section>
  );
}

const dashboardMediaQueries = ['(max-width: 900px)', '(max-width: 1200px)'];

function dashboardColumnCount() {
  if (typeof window === 'undefined' || !window.matchMedia) return 3;
  if (window.matchMedia(dashboardMediaQueries[0]).matches) return 1;
  if (window.matchMedia(dashboardMediaQueries[1]).matches) return 2;
  return 3;
}

function useDashboardColumnCount() {
  const [count, setCount] = useState(dashboardColumnCount);

  useEffect(() => {
    const mediaQueries = dashboardMediaQueries.map(query => window.matchMedia(query));
    const update = () => setCount(dashboardColumnCount());
    mediaQueries.forEach(query => query.addEventListener('change', update));
    update();
    return () => mediaQueries.forEach(query => query.removeEventListener('change', update));
  }, []);

  return count;
}

function DashboardColumns({ children }) {
  const columnCount = useDashboardColumnCount();
  const columns = Array.from({ length: columnCount }, () => []);
  Children.toArray(children).forEach((card, index) => {
    columns[index % columnCount].push(card);
  });

  return (
    <Columns className="dashboard-page">
      {columns.map((cards, index) => (
        <Column className="dashboard-column" id={`dashboard-column-${index + 1}`} key={index}>
          {cards}
        </Column>
      ))}
    </Columns>
  );
}

export function DashboardPage({ data, fetchImpl = fetch }) {
  const {
    profile,
    totals,
    kids,
    focuses = [],
    focus_assignments_complete: assignmentsComplete = {},
    activity,
  } = data;
  const firstTimers = kids.filter(kid => kid.budo_experience === false);
  const oneWeek = kids.filter(kid => kid.weeks === 1);
  const health = kids.filter(kid => kid.drugs || kid.illness);
  const food = kids.filter(kid => kid.special_food);
  const birthdays = kids.filter(kid => kid.birthday_during_turnus);
  const goodbyes = kids.filter(kid => kid.age > 14.8).sort((a, b) => a.age - b.age);
  const familyKids = profile?.budo_family
    ? kids.filter(kid => kid.budo_family === profile.budo_family)
    : [];
  const kidsById = new Map(kids.map(kid => [Number(kid.id), kid]));
  const focusesByWeek = week => focuses.filter(focus => focus.week === week);
  const kidList = list => <>{list.map(kid => <div className="print-nobreak" key={kid.id}><p><span className="label">{linkKid(kid)}</span>: {kid.age}</p>{kid.illness && <p>Krankheiten: {kid.illness}</p>}{kid.drugs && <p>Medikamente: {kid.drugs}</p>}</div>)}</>;
  const personalFocusCard = (week, number) => assignmentsComplete[week] && (
    <Card title={`Mein SWP ${number}`} id={`db-swp-${number}`}>
      {focusesByWeek(week).length
        ? focusesByWeek(week).map(focus => <FocusAssignment focus={focus} kidsById={kidsById} key={focus.id} />)
        : <p>Kein Schwerpunkt zugeteilt.</p>}
    </Card>
  );
  return (
    <DashboardColumns>
      <Card title={`Kinder: ${totals.checked_in}`} id="db-kinderübersicht">
        <p><span className="label">Eingecheckt</span>: {totals.checked_in}/{totals.kids}</p>
        <p><span className="label">Geschlechter</span>: {kids.filter(kid => kid.sex === 'männlich').length} ♂ // {kids.filter(kid => kid.sex === 'weiblich').length} ♀ // {kids.filter(kid => !['männlich', 'weiblich'].includes(kid.sex)).length} ⚧</p>
        <p><span className="label">Kids mit BuDo-Erfahrung</span>: {kids.filter(kid => kid.budo_experience).length}</p>
        <p><span className="label">Zuganreise</span>: {totals.train_arrival}</p>
        <p><span className="label">Zugabreise</span>: {totals.train_departure}</p>
      </Card>
      <Card title="Notizen" id="db-notizen"><ActivityList kind="notes" initialPage={activity.notes} fetchImpl={fetchImpl} /></Card>
      <Card title="Meine BuDo-Familie" id="db-budo-familie">
        {profile?.budo_family
          ? <><p><span className="label">{familyLabels[profile.budo_family] || profile.budo_family}</span></p>{familyKids.length ? <ul>{familyKids.map(kid => <li key={kid.id}>{linkKid(kid)}</li>)}</ul> : <p>Keine Kinder in dieser BuDo-Familie.</p>}</>
          : <p>Noch keine BuDo-Familie im Profil zugeordnet.</p>}
      </Card>
      {personalFocusCard('w1', 1)}
      {personalFocusCard('w2', 2)}
      <Card title={`Erstes Mal im BuDO: ${firstTimers.length}/${totals.kids}`} id="db-ersties" initiallyClosed>{kidList(firstTimers)}</Card>
      <Card title={`Einwöchige: ${oneWeek.length}`} id="db-einwöchig" initiallyClosed>{kidList(oneWeek)}</Card>
      <Card title="Gesundheitliches" id="db-gesundheit" initiallyClosed>{kidList(health)}</Card>
      <Card title="Essen & Allergien" id="db-essen" initiallyClosed>{food.map(kid => <div className="print-nobreak" key={kid.id}><p>{linkKid(kid)}: {kid.age}</p><p>{kid.food} · {kid.special_food}</p></div>)}</Card>
      <Card title={`Geburtstagskinder: ${birthdays.length}`} id="db-geburtstagskinder">{birthdays.map(kid => <p key={kid.id}>{linkKid(kid)}: {formatKidBirthday(kid)}</p>)}</Card>
      <Card title={`Verabschiedungsliste: ${goodbyes.length}`} id="db-sechzehner">{goodbyes.map(kid => <p key={kid.id}>{linkKid(kid)}: {kid.age} – {formatKidBirthday(kid)}</p>)}</Card>
      <Card title="Taschengeldtransaktionen" id="db-geld"><ActivityList kind="transactions" initialPage={activity.transactions} fetchImpl={fetchImpl} /></Card>
    </DashboardColumns>
  );
}

export const dashboardRoutes = [{
  pattern: /^\/$|^\/dashboard$/,
  page: 'dashboard',
  title: 'BuDo Dashboard',
  domain: 'dashboard',
  readContractKey: 'dashboard',
  render: ({ data, fetchImpl }) => <DashboardPage data={data} fetchImpl={fetchImpl} />,
}];
