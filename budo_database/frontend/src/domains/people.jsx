import { Card, Column, Columns, FieldList, NativeForm, RestForm } from '../components';
import { formatGermanDate, money, NotFoundPage } from './shared';

function AssignedFocuses({ focuses = [] }) {
  return <><p><span className="label">Meine Schwerpunkte</span>:</p><ul>{focuses.length ? focuses.map(focus => <li key={focus.id}><a href={`/schwerpunkt/${focus.id}/`}>{focus.name}</a></li>) : <li>Keine Schwerpunkte zugeteilt.</li>}</ul></>;
}

function PersonCard({ person, focuses, turnus, showUpdateLink = false }) {
  return <Card title={person.rufname} id="db-profil"><FieldList items={[
    ['Rolle', person.role_display],
    ['Turnus', turnus?.label],
    ['Essen', person.food_display],
    ['Allergien', person.allergies],
    ['Kaffee', person.coffee],
    ['Email', <a href={`mailto:${person.email}`}>{person.email}</a>],
    ['Mobil', <a href={`tel:${person.phone}`}>{person.phone}</a>],
  ]} /><AssignedFocuses focuses={focuses} />{showUpdateLink && <a className="button" href="/profil">Informationen aktualisieren</a>}</Card>;
}

function AccountingCard({ person, children }) {
  return <Card title={`Abrechnung: ${money(person.money_total)}`} id="betreuerinnengeld"><ul>{person.money_items.length ? person.money_items.map(item => <li key={item.id}>{person.rufname} am {formatGermanDate(item.date)}: {item.what} – {money(item.amount)}</li>) : <li>Keine Transaktionen bisher...</li>}</ul>{children}</Card>;
}

export function TeamerPage({ data, id, onSaved }) {
  const person = data.person;
  if (!person || Number(person.id) !== Number(id)) return <NotFoundPage />;
  return <Columns><Column id="left-column"><PersonCard person={person} focuses={data.focuses} turnus={data.turnus} showUpdateLink /></Column><Column id="center-column"><AccountingCard person={person}><RestForm target={`/teamer/${person.id}/`} token={data.csrf_token} className="form-grid" onSuccess={onSaved} resetOnSuccess><label>Betrag in €<input name="amount" type="number" step="0.01" /></label><label>Beschreibung<input name="what" /></label><div className="form-buttons"><button className="button" type="submit">Save</button></div></RestForm></AccountingCard></Column></Columns>;
}

export function ProfilePage({ data }) {
  const profile = data.profile;
  if (!profile) return <NotFoundPage />;
  const fields = [
    { name: 'rufname', label: 'Rufname', value: profile.rufname },
    { name: 'allergien', label: 'Allergien', value: profile.allergies },
    { name: 'coffee', label: 'Kaffee', value: profile.coffee },
    { name: 'rolle', label: 'Rolle', type: 'select', value: profile.role, options: [{ value: 'b', label: 'Betreuer:in' }, { value: 'k', label: 'Küche' }, { value: 'o', label: 'Organisator' }, { value: 'f', label: 'Freiwillige:r' }] },
    { name: 'essen', label: 'Essen', type: 'select', value: profile.food, options: [{ value: 'ft', label: 'Flexitarisch' }, { value: 'vt', label: 'Vegetarisch' }, { value: 'vn', label: 'Vegan' }] },
    { name: 'telefonnummer', label: 'Telefonnummer', value: profile.phone },
  ];
  if (profile.can_change_turnus) {
    fields.push({ name: 'turnus', label: 'Turnus', type: 'select', value: data.turnus?.id, options: data.turnuses.map(item => ({ value: item.id, label: item.label })) });
  }
  return <Columns><Column id="left-column"><PersonCard person={profile} focuses={data.focuses} turnus={data.turnus} /></Column><Column id="center-column"><Card title="Profil"><NativeForm token={data.csrf_token} action="/profil/" fields={fields} /></Card></Column><Column id="right-column"><AccountingCard person={profile} /></Column></Columns>;
}

export const peopleRoutes = [
  {
    pattern: /^\/profil$/,
    page: 'profile',
    title: 'Profil',
    domain: 'people',
    readContractKey: 'profile',
    focusedReadContract: true,
    resolveTitle: (route, data) => data.profile?.rufname || route.title,
    render: ({ data }) => <ProfilePage data={data} />,
  },
  {
    pattern: /^\/teamer\/(\d+)$/,
    page: 'teamer',
    title: 'Teamer',
    domain: 'people',
    readContractKey: 'teamer',
    focusedReadContract: true,
    params: match => ({ id: match[1] }),
    resolveTitle: (route, data) => data.person?.rufname || route.title,
    render: ({ route, data, refresh }) => <TeamerPage data={data} id={route.id} onSaved={refresh} />,
  },
];
