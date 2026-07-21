import { useState } from 'react';

import { Card, Column, Columns, FieldList, findById, MapCard, NativeForm, RestForm, SearchTable } from '../components';
import { displayOrPlaceholder, formatGermanDate, linkKid, MealTable, NotFoundPage, yesNo } from './shared';

const focusKidColumns = [
  { key: 'name', label: 'Name', render: linkKid },
  { key: 'budo_family', label: 'Familie', render: row => displayOrPlaceholder(row.budo_family) },
  { key: 'sex_short', label: '⚧' },
  { key: 'age', label: 'Alter', className: 'number-cell', render: row => <>{row.birthday_during_turnus && '🥳 '}{displayOrPlaceholder(row.age)}</> },
  { key: 'food', label: 'Ernährung' },
  { key: 'drugs', label: 'Medikamente', render: row => displayOrPlaceholder(row.drugs) },
  { key: 'illness', label: 'Gesundheitliches', render: row => displayOrPlaceholder(row.illness) },
];

const formatGermanDateTime = value => {
  if (!value) return value;
  const match = String(value).match(/^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})/);
  return match ? `${match[3]}.${match[2]}.${match[1]}, ${match[4]}:${match[5]}` : value;
};

const MAP_WEEK_COOKIE = 'swp_map_week';

const storedMapWeek = () => {
  if (typeof document === 'undefined') return 'w1';
  const value = document.cookie.split('; ').find(cookie => cookie.startsWith(`${MAP_WEEK_COOKIE}=`))?.split('=')[1];
  return value === 'w2' ? 'w2' : 'w1';
};

export function FocusDashboardPage({ data }) {
  const [mapWeek, setMapWeek] = useState(storedMapWeek);
  const group = week => data.focuses.filter(focus => focus.week === week);
  const selectMapWeek = week => {
    setMapWeek(week);
    document.cookie = `${MAP_WEEK_COOKIE}=${week}; Path=/; Max-Age=31536000; SameSite=Lax`;
  };
  const columns = [
    {
      key: 'name',
      label: 'Name',
      render: focus => <strong><a href={`/schwerpunkt/${focus.id}/`}>{focus.name}{!focus.meals_assigned && ' ❗🍔'}</a></strong>,
    },
    { key: 'place', label: 'Ort', render: focus => focus.place_id ? <a href={`/auslagerorte/${focus.place_id}/`}>{focus.place}</a> : '---' },
    { key: 'carers', label: 'Betreuende', render: focus => focus.carers || '---' },
    { key: 'off_site', label: 'Auslagern', render: focus => yesNo(focus.off_site) },
    { key: 'kids', label: 'Kinder', render: focus => focus.kid_count, sortValue: focus => focus.kid_count },
  ];
  const tables = [['u', 'Unklar Wann'], ['w1', 'Woche 1'], ['w2', 'Woche 2']].filter(([week]) => group(week).length || week !== 'u');
  return <Columns className="focus-dashboard">
    <Column id="left-column" className="focus-weeks-column">
      {tables.map(([week, title]) => <Card title={title} className="transparent" key={week} headerAction={week !== 'u' ? <a className="button" href={`/swp-einteilung-${week}`}>Kinder einteilen</a> : null}><SearchTable columns={columns} rows={group(week)} /></Card>)}
    </Column>
    <Column id="right-column" className="focus-map-column">
      <MapCard
        places={data.focuses.filter(focus => focus.week === mapWeek && focus.coordinates).map(focus => ({ id: focus.id, name: focus.name, coordinates: focus.coordinates, href: `/schwerpunkt/${focus.id}/` }))}
        headerAction={<span className="map-week-switch" role="group" aria-label="Kartenwoche">
          {['w1', 'w2'].map(week => <button key={week} type="button" className="button" aria-pressed={mapWeek === week} onClick={() => selectMapWeek(week)}>Woche {week.slice(1)}</button>)}
        </span>}
      />
    </Column>
  </Columns>;
}

export function FocusDetailPage({ data, id }) {
  const focus = data.focus;
  if (!focus) return <NotFoundPage />;
  const kids = data.kids;
  const mapPlaces = focus.place_id ? [{ id: focus.place_id, name: focus.place, coordinates: focus.coordinates }] : [];
  return <Columns><Column id="left-column"><Card title={focus.name}><FieldList items={[["Beschreibung", focus.description], ["Kinder", kids.length], ["Ort", focus.place_id ? <a href={`/auslagerorte/${focus.place_id}/`}>{focus.place}</a> : 'Noch unklar'], ["Auslagern", yesNo(focus.off_site)], ["Betreuende", focus.carers], ["Wann", focus.time], ["Beginnt am", formatGermanDate(focus.start)], ["Geschätzte Abreise", focus.off_site ? formatGermanDateTime(focus.departure) : null], ["Geschätzte Rückkehr", focus.off_site ? formatGermanDateTime(focus.arrival) : null]]} /><MealTable focus={focus} /><div className="react-actions"><a className="button" href={`/schwerpunkt/${focus.id}/update`}>SWP bearbeiten</a><a className="button" href={`/swpmeals/${focus.id}`}>Essen bearbeiten</a></div></Card><MapCard places={mapPlaces} /></Column><Column id="right-column"><SearchTable columns={focusKidColumns} rows={kids} /></Column></Columns>;
}

export function FocusFormPage({ data, id }) {
  const focus = id ? data.focus : null;
  const fields = [
    { name: 'swp_name', label: 'Schwerpunktname', value: focus?.name, required: true },
    { name: 'ort', label: 'Ort', type: 'select', value: focus?.place_id, options: [{ value: '', label: '---------' }, ...data.places.map(item => ({ value: item.id, label: item.name }))] },
    { name: 'betreuende', label: 'Betreuende', type: 'select', multiple: true, value: focus?.carer_ids || [], options: data.team.map(item => ({ value: item.id, label: item.rufname })) },
    { name: 'beschreibung', label: 'Beschreibung', type: 'textarea', value: focus?.description },
    { name: 'schwerpunktzeit', label: 'Schwerpunktzeit', type: 'select', value: focus?.time_id, options: data.focus_times.map(item => ({ value: item.id, label: item.label })) },
    { name: 'auslagern', label: 'Auslagern', type: 'checkbox', value: focus?.off_site },
    { name: 'geplante_abreise', label: 'Geplante Abreise', type: 'datetime-local', value: focus?.departure?.slice(0, 16) },
    { name: 'geplante_ankunft', label: 'Geplante Ankunft', type: 'datetime-local', value: focus?.arrival?.slice(0, 16) },
  ];
  return <Columns><Column id="single-column"><Card title={`Schwerpunkt ${focus ? 'updaten' : 'erstellen'}`}><NativeForm token={data.csrf_token} action={focus ? `/schwerpunkt/${focus.id}/update` : '/schwerpunkt/create'} fields={fields}><a className="button" href="/swp-dashboard/">Cancel</a></NativeForm></Card></Column></Columns>;
}

export function MealsPage({ data, id }) {
  const focus = data.focus;
  if (!focus) return <NotFoundPage />;
  const entries = focus.meal_items;
  return <Columns><Column id="single-column"><Card title="Wann esst ihr wo?"><RestForm target={`/swpmeals/${focus.id}`} token={data.csrf_token} className="form-grid"><input type="hidden" name="form-TOTAL_FORMS" value={entries.length} /><input type="hidden" name="form-INITIAL_FORMS" value={entries.length} />{entries.map((meal, index) => { const fieldId = `meal-${meal.id}`; return <div className="meal-input" key={meal.id}><input type="hidden" name={`form-${index}-id`} value={meal.id} /><label htmlFor={fieldId}>Tag {meal.day} · {data.meal_types[meal.type]}</label><select id={fieldId} name={`form-${index}-meal_choice`} defaultValue={meal.choice}>{data.meal_choices.map(choice => <option value={choice.value} key={choice.value}>{choice.label}</option>)}</select></div>; })}<input className="button" type="submit" value="Speichern" /></RestForm></Card></Column></Columns>;
}

const selectedFocusTitle = (route, data) => data.focus?.name || findById(data.focuses || [], route.id)?.name || route.title;

export const focusRoutes = [
  {
    pattern: /^\/schwerpunkt\/create$/,
    page: 'focus-create',
    title: 'Neuer SWP',
    domain: 'focuses',
    readContractKey: 'focus-create',
    render: ({ data }) => <FocusFormPage data={data} />,
  },
  {
    pattern: /^\/schwerpunkt\/(\d+)\/update$/,
    page: 'focus-update',
    title: 'Schwerpunkt bearbeiten',
    domain: 'focuses',
    readContractKey: 'focus-update',
    params: match => ({ id: match[1] }),
    resolveTitle: selectedFocusTitle,
    render: ({ route, data }) => <FocusFormPage data={data} id={route.id} />,
  },
  {
    pattern: /^\/schwerpunkt\/(\d+)$/,
    page: 'focus-detail',
    title: 'Schwerpunkt',
    domain: 'focuses',
    readContractKey: 'focus-detail',
    params: match => ({ id: match[1] }),
    resolveTitle: selectedFocusTitle,
    render: ({ route, data }) => <FocusDetailPage data={data} id={route.id} />,
  },
  {
    pattern: /^\/swpmeals\/(\d+)$/,
    page: 'focus-meals',
    title: 'Essen',
    domain: 'focuses',
    readContractKey: 'focus-meals',
    params: match => ({ id: match[1] }),
    resolveTitle: selectedFocusTitle,
    render: ({ route, data }) => <MealsPage data={data} id={route.id} />,
  },
  {
    pattern: /^\/swp-dashboard$/,
    page: 'focus-dashboard',
    title: 'Schwerpunkte',
    domain: 'focuses',
    readContractKey: 'focus-dashboard',
    headerAction: () => <a className="button" href="/schwerpunkt/create">SWP hinzufügen</a>,
    render: ({ data }) => <FocusDashboardPage data={data} />,
  },
];
