import { Card, Column, Columns, FieldList, findById, NativeForm } from '../components';
import { formatGermanDate, money, NotFoundPage } from './shared';

export function TeamerPage({ data, id }) {
  const profile = findById(data.team, id);
  if (!profile) return <NotFoundPage />;
  return <Columns><Column id="left-column"><Card title={profile.rufname}><FieldList items={[["Rolle", profile.role_display], ["Turnus", data.turnus?.label], ["Essen", profile.food_display], ["Allergien", profile.allergies], ["Kaffee", profile.coffee], ["Email", <a href={`mailto:${profile.email}`}>{profile.email}</a>], ["Mobil", <a href={`tel:${profile.phone}`}>{profile.phone}</a>]]} /></Card></Column><Column id="center-column"><Card title={`Abrechnung: ${money(profile.money_total)}`}><ul>{profile.money_items.length ? profile.money_items.map(item => <li key={item.id}>{profile.rufname} am {formatGermanDate(item.date)}: {item.what} – {money(item.amount)}</li>) : <li>Keine Transaktionen bisher...</li>}</ul><NativeForm token={data.csrf_token} action={`/teamer/${profile.id}/`} fields={[{ name: 'amount', label: 'Betrag in €', type: 'number', step: '0.01' }, { name: 'what', label: 'Beschreibung' }]} /></Card></Column></Columns>;
}

export function ProfilePage({ data }) {
  const profile = data.profile;
  return <Columns><Column id="single-column"><Card title="Profil"><NativeForm token={data.csrf_token} action="/profil/" fields={[
    { name: 'rufname', label: 'Rufname', value: profile.rufname },
    { name: 'allergien', label: 'Allergien', value: profile.allergies },
    { name: 'coffee', label: 'Kaffee', value: profile.coffee },
    { name: 'rolle', label: 'Rolle', type: 'select', value: profile.role, options: [{ value: 'b', label: 'Betreuer:in' }, { value: 'k', label: 'Küche' }, { value: 'o', label: 'Organisator' }, { value: 'f', label: 'Freiwillige:r' }] },
    { name: 'essen', label: 'Essen', type: 'select', value: profile.food, options: [{ value: 'ft', label: 'Flexitarisch' }, { value: 'vt', label: 'Vegetarisch' }, { value: 'vn', label: 'Vegan' }] },
    { name: 'telefonnummer', label: 'Telefonnummer', value: profile.phone },
    { name: 'turnus', label: 'Turnus', type: 'select', value: data.turnus?.id, options: data.turnuses.map(item => ({ value: item.id, label: item.label })) },
  ]} /></Card></Column></Columns>;
}

export const peopleRoutes = [
  {
    pattern: /^\/profil$/,
    page: 'profile',
    title: 'Profil',
    domain: 'people',
    readContractKey: 'profile',
    resolveTitle: (route, data) => data.profile?.rufname || route.title,
    render: ({ data }) => <ProfilePage data={data} />,
  },
  {
    pattern: /^\/teamer\/(\d+)$/,
    page: 'teamer',
    title: 'Teamer',
    domain: 'people',
    readContractKey: 'teamer',
    params: match => ({ id: match[1] }),
    resolveTitle: (route, data) => findById(data.team, route.id)?.rufname || route.title,
    render: ({ route, data }) => <TeamerPage data={data} id={route.id} />,
  },
];
