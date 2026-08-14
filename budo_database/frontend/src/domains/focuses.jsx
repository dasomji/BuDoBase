import { useState } from 'react';
import { PlusIcon } from 'lucide-react';

import {
  Card,
  Column,
  Columns,
  DataTable,
  findById,
  NativeForm,
  RestForm,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
  TableScroll,
} from '../components';
import { GoogleMapCard } from '../components/google-map';
import { Button } from '../components/ui/button';
import { NativeSelect } from '../components/ui/input';
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
  return <Columns className="grid grid-cols-1 items-start min-[901px]:h-[calc(100svh-var(--app-header-height,0px))] min-[901px]:min-h-0 min-[901px]:grid-cols-[auto_minmax(0,1fr)] min-[901px]:overflow-hidden">
    <Column id="left-column" className="min-w-0 min-[901px]:overflow-y-auto">
      {tables.map(([week, title]) => <Card title={title} className="transparent" key={week} headerAction={week !== 'u' ? <Button href={`/swp-einteilung-${week}`}>Kinder einteilen</Button> : null}><DataTable columns={columns} rows={group(week)} /></Card>)}
    </Column>
    <Column id="right-column" className="min-w-0 min-[901px]:[&_.card-info-container]:min-h-0 min-[901px]:[&_.card-info-content]:min-h-0 min-[901px]:[&_.interactive-map]:h-full min-[901px]:[&_.interactive-map]:min-h-70 min-[901px]:[&>#swp-map]:flex min-[901px]:[&>#swp-map]:h-full min-[901px]:[&>#swp-map]:min-h-0 min-[901px]:[&>#swp-map]:flex-col min-[901px]:[&>#swp-map:not(.closed-card)>.card-info-container]:flex-1">
      <GoogleMapCard
        apiKey={data.google_maps_browser_api_key}
        mapId={data.google_maps_map_id}
        places={data.focuses.filter(focus => focus.week === mapWeek && focus.coordinates).map(focus => ({ id: focus.id, name: focus.name, coordinates: focus.coordinates, href: `/schwerpunkt/${focus.id}/` }))}
        headerAction={<span className="inline-flex gap-1" role="group" aria-label="Kartenwoche">
          {['w1', 'w2'].map(week => <Button key={week} type="button" variant={mapWeek === week ? 'default' : 'outline'} aria-pressed={mapWeek === week} onClick={() => selectMapWeek(week)}>Woche {week.slice(1)}</Button>)}
        </span>}
      />
    </Column>
  </Columns>;
}

function FocusDetails({ focus, kidCount }) {
  const fields = [
    ['Ort', focus.place_id ? <a href={`/auslagerorte/${focus.place_id}/`}>{focus.place}</a> : 'Noch unklar'],
    ['Auslagern', yesNo(focus.off_site)],
    ['Betreuende', focus.carers],
    ['Kinder', kidCount],
    ['Wann', focus.time],
    ['Beginnt am', formatGermanDate(focus.start)],
    ['Beschreibung', focus.description, 'full-width'],
  ];
  return <div className="flex flex-wrap gap-x-6">{fields.map(([label, value, className]) => <p className={`${className ? 'basis-full' : 'min-w-56 flex-[1_1_calc(50%-0.75rem)]'}`} key={label}><span className="label">{label}</span>: {value}</p>)}</div>;
}

export function FocusDetailPage({ data, id }) {
  const focus = data.focus;
  if (!focus) return <NotFoundPage />;
  const kids = data.kids;
  return <Columns className="grid min-w-0 grid-cols-1 items-start">
    <Column id="focus-detail-content" className="w-full min-w-0">
      <section className="grid min-w-0 grid-cols-1 items-start gap-4 min-[901px]:grid-cols-2" aria-label="Schwerpunktübersicht">
        <Card className="min-w-0" title={focus.name} actions={<Button href={`/schwerpunkt/${focus.id}/update`}>SWP bearbeiten</Button>}><FocusDetails focus={focus} kidCount={kids.length} /></Card>
        <Card className="min-w-0" title="Essen" actions={<Button href={`/swpmeals/${focus.id}`}>Essen bearbeiten</Button>}><MealTable focus={focus} /></Card>
      </section>
      <DataTable columns={focusKidColumns} rows={kids} />
    </Column>
  </Columns>;
}

export function FocusFormPage({ data, id }) {
  const focus = id ? data.focus : null;
  const fields = [
    { name: 'schwerpunktzeit', label: 'Schwerpunktzeit', type: 'select', value: focus?.time_id, options: data.focus_times.map(item => ({ value: item.id, label: item.label })) },
    { name: 'swp_name', label: 'Schwerpunktname', value: focus?.name, required: true },
    { name: 'ort', label: 'Ort', type: 'select', value: focus?.place_id, options: [{ value: '', label: '---------' }, ...data.places.map(item => ({ value: item.id, label: item.name }))] },
    { name: 'auslagern', label: 'Ja', groupLabel: 'Lagert ihr aus?', type: 'checkbox', value: focus?.off_site ?? false },
    { name: 'betreuende', label: 'Betreuende', type: 'checkbox-group', value: focus?.carer_ids || [], options: data.team.map(item => ({ value: item.id, label: item.rufname })) },
    { name: 'beschreibung', label: 'Beschreibung', type: 'textarea', value: focus?.description },
  ];
  return <Columns><Column id="single-column"><Card title={`Schwerpunkt ${focus ? 'updaten' : 'erstellen'}`}><NativeForm token={data.csrf_token} action={focus ? `/schwerpunkt/${focus.id}/update` : '/schwerpunkt/create'} fields={fields}><Button href="/swp-dashboard/" variant="secondary">Cancel</Button></NativeForm></Card></Column></Columns>;
}

export function MealsPage({ data, id }) {
  const focus = data.focus;
  if (!focus) return <NotFoundPage />;
  const entries = focus.meal_items;
  const days = [...new Set(entries.map(meal => meal.day))].sort((left, right) => left - right);
  const mealTypes = Object.entries(data.meal_types);
  const indexedMeals = new Map(entries.map((meal, index) => [`${meal.day}-${meal.type}`, { meal, index }]));
  return (
    <Columns>
      <Column id="single-column" className="min-w-0 w-full max-w-5xl">
        <Card title="Wann esst ihr wo?" className="min-w-0">
          <RestForm target={`/swpmeals/${focus.id}`} token={data.csrf_token} className="form-grid min-w-0">
            <input type="hidden" name="form-TOTAL_FORMS" value={entries.length} />
            <input type="hidden" name="form-INITIAL_FORMS" value={entries.length} />
            <TableScroll className="min-w-0 max-w-full">
              <Table className="min-w-full min-[901px]:min-w-[40rem]">
                <TableHeader>
                  <TableRow>
                    <TableHead scope="col">Tag</TableHead>
                    {mealTypes.map(([type, label]) => <TableHead scope="col" key={type}>{label}</TableHead>)}
                  </TableRow>
                </TableHeader>
                <TableBody>{days.map(day => (
                  <TableRow key={day}>
                    <TableHead className="font-bold whitespace-nowrap" scope="row">Tag {day}</TableHead>
                    {mealTypes.map(([type, label]) => {
                      const indexedMeal = indexedMeals.get(`${day}-${type}`);
                      if (!indexedMeal) return <TableCell key={type}>—</TableCell>;
                      const { meal, index } = indexedMeal;
                      const fieldId = `meal-${meal.id}`;
                      return (
                        <TableCell key={type}>
                          <input type="hidden" name={`form-${index}-id`} value={meal.id} />
                          <label className="sr-only" htmlFor={fieldId}>Tag {day} · {label}</label>
                          <NativeSelect className="min-[901px]:min-w-36" id={fieldId} name={`form-${index}-meal_choice`} defaultValue={meal.choice}>
                            {data.meal_choices.map(choice => (
                              <option value={choice.value} key={choice.value}>{choice.label}</option>
                            ))}
                          </NativeSelect>
                        </TableCell>
                      );
                    })}
                  </TableRow>
                ))}</TableBody>
              </Table>
            </TableScroll>
            <Button className="justify-self-end" type="submit">Speichern</Button>
          </RestForm>
        </Card>
      </Column>
    </Columns>
  );
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
    headerAction: () => (
      <Button className="mobile-icon-action" size="responsive-icon" href="/schwerpunkt/create" aria-label="SWP hinzufügen">
        <span className="desktop-action-label">SWP hinzufügen</span>
        <PlusIcon className="mobile-action-label" aria-hidden="true" />
      </Button>
    ),
    render: ({ data }) => <FocusDashboardPage data={data} />,
  },
];
