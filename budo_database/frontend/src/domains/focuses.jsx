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

export function FocusDashboardPage({ data }) {
  const group = week => data.focuses.filter(focus => focus.week === week);
  const columns = [{ key: 'name', label: 'Name', render: focus => <a href={`/schwerpunkt/${focus.id}/`}>{focus.name}</a> }, { key: 'place', label: 'Ort', render: focus => focus.place || '---' }, { key: 'carers', label: 'Betreuende', render: focus => focus.carers || '---' }, { key: 'off_site', label: 'Auslagern', render: focus => yesNo(focus.off_site) }, { key: 'kids', label: 'Kinder', render: focus => focus.kid_ids.length, sortValue: focus => focus.kid_ids.length }, { key: 'meals', label: 'Essenseinteilung', render: focus => focus.meal_items.some(meal => meal.choice) ? 'Ja' : 'Nein', sortValue: focus => focus.meal_items.some(meal => meal.choice) }, { key: 'actions', label: 'Aktionen', sortable: false, render: focus => <a href={`/schwerpunkt/${focus.id}/update`}>✏️</a> }];
  const tables = [['u', 'Unklar Wann'], ['w1', 'Woche 1'], ['w2', 'Woche 2']].filter(([week]) => group(week).length || week !== 'u');
  return <Columns><Column id="left-column"><MapCard places={data.focuses.filter(focus => focus.coordinates).map(focus => ({ id: focus.id, name: focus.name, coordinates: focus.coordinates, href: `/schwerpunkt/${focus.id}/` }))} /></Column><Column id="right-column" className="normal-column">{tables.map(([week, title]) => <Card title={title} className="transparent" key={week}><SearchTable columns={columns} rows={group(week)} />{week !== 'u' && <div className="react-actions"><a className="button" href={`/swp-einteilung-${week}`}>Kinder einteilen</a></div>}</Card>)}</Column></Columns>;
}

export function FocusDetailPage({ data, id }) {
  const focus = findById(data.focuses, id);
  if (!focus) return <NotFoundPage />;
  const kids = data.kids.filter(kid => focus.kid_ids.includes(kid.id));
  return <Columns><Column id="left-column"><Card title={focus.name}><FieldList items={[["Beschreibung", focus.description], ["Kinder", kids.length], ["Ort", focus.place], ["Auslagern", yesNo(focus.off_site)], ["Betreuende", focus.carers], ["Wann", focus.time], ["Beginnt am", formatGermanDate(focus.start)]]} /><MealTable focus={focus} /><div className="react-actions"><a className="button" href={`/schwerpunkt/${focus.id}/update`}>SWP bearbeiten</a><a className="button" href={`/swpmeals/${focus.id}`}>Essen bearbeiten</a></div></Card><MapCard places={focus.place_id ? data.places.filter(place => place.id === focus.place_id) : []} /></Column><Column id="right-column"><SearchTable columns={focusKidColumns} rows={kids} /></Column></Columns>;
}

export function FocusFormPage({ data, id }) {
  const focus = id ? findById(data.focuses, id) : null;
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
  return <Columns><Column id="single-column"><Card title={`Schwerpunkt ${focus ? 'updaten' : 'erstellen'}`}><NativeForm token={data.csrf_token} action={focus ? `/schwerpunkt/${focus.id}/update` : '/schwerpunkt/create'} fields={fields} /></Card></Column></Columns>;
}

export function MealsPage({ data, id }) {
  const focus = findById(data.focuses, id);
  if (!focus) return <NotFoundPage />;
  const entries = focus.meal_items;
  return <Columns><Column id="single-column"><Card title="Wann esst ihr wo?"><RestForm target={`/swpmeals/${focus.id}`} token={data.csrf_token} className="form-grid"><input type="hidden" name="form-TOTAL_FORMS" value={entries.length} /><input type="hidden" name="form-INITIAL_FORMS" value={entries.length} />{entries.map((meal, index) => <label key={meal.id}>Tag {meal.day} · {{ breakfast: 'Frühstück', lunch: 'Mittagessen', dinner: 'Abendessen' }[meal.type]}<input type="hidden" name={`form-${index}-id`} value={meal.id} /><select name={`form-${index}-meal_choice`} defaultValue={meal.choice}><option value="">---------</option><option value="box">Box</option><option value="budo">Im BuDo</option><option value="warm">Warm geliefert</option></select></label>)}<input className="button" type="submit" value="Speichern" /></RestForm></Card></Column></Columns>;
}

const selectedFocusTitle = (route, data) => findById(data.focuses, route.id)?.name || route.title;

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
