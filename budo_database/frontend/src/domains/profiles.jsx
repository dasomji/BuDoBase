import { PencilIcon } from 'lucide-react';

import { Card, Column, Columns, FieldList, NativeForm } from '../components';
import { Button } from '../components/ui/button';
import { NotFoundPage } from './shared';

const familyLabels = {
  S: 'Smallie',
  M: 'Medi',
  L: 'Largie',
  XL: 'X-largie',
};

function AssignedFocuses({ focuses = [] }) {
  return <><p><span className="label">Schwerpunkte</span>:</p><ul>{focuses.length ? focuses.map(focus => <li key={focus.id}><a href={`/schwerpunkt/${focus.id}/`}>{focus.name}</a></li>) : <li>Keine Schwerpunkte zugeteilt.</li>}</ul></>;
}

export function PersonCard({ person, focuses, id = 'db-profil', updateHref, actions }) {
  const cardActions = actions || (updateHref
    ? <Button href={updateHref}>Informationen aktualisieren</Button>
    : null);
  return <Card title={person.rufname} id={id} actions={cardActions}><FieldList items={[
    ['Essen', person.food_display],
    ['BuDo-Familie', familyLabels[person.budo_family]],
    ['Allergien', person.allergies],
    ['Kaffee', person.coffee],
    ['Email', person.email ? <a href={`mailto:${person.email}`}>{person.email}</a> : null],
    ['Mobil', person.phone ? <a href={`tel:${person.phone}`}>{person.phone}</a> : null],
    ['Turnis', person.turnuses?.join(', ')],
  ]} /><AssignedFocuses focuses={focuses} /></Card>;
}

export function ProfilePage({ data }) {
  const profile = data.profile;
  if (!profile) return <NotFoundPage />;
  return <Columns><Column id="single-column"><PersonCard person={profile} focuses={data.focuses} actions={<Button href="/teams/">Zur Turnusliste</Button>} /></Column></Columns>;
}

export function profileFields(profile) {
  return [
    { name: 'rufname', label: 'Rufname', value: profile.rufname },
    { name: 'email', label: 'E-Mail', type: 'email', value: profile.email, required: true },
    { name: 'allergien', label: 'Allergien', value: profile.allergies },
    { name: 'coffee', label: 'Kaffee', value: profile.coffee },
    { name: 'essen', label: 'Essen', type: 'select', value: profile.food, options: [{ value: 'ft', label: 'Flexitarisch' }, { value: 'vt', label: 'Vegetarisch' }, { value: 'vn', label: 'Vegan' }] },
    { name: 'budo_family', label: 'BuDo-Familie', type: 'select', value: profile.budo_family, options: [{ value: '', label: 'Nicht zugeordnet' }, { value: 'S', label: 'Smallie' }, { value: 'M', label: 'Medi' }, { value: 'L', label: 'Largie' }, { value: 'XL', label: 'X-largie' }] },
    { name: 'telefonnummer', label: 'Telefonnummer', value: profile.phone },
  ];
}

export function ProfileForm({ profile, token, target, onSuccess }) {
  return <NativeForm token={token} action={target} fields={profileFields(profile)} onSuccess={onSuccess} />;
}

export function ProfileEditPage({ data, target = '/profil/bearbeiten/' }) {
  const profile = data.profile;
  if (!profile) return <NotFoundPage />;
  return <Columns><Column id="single-column"><Card title="Profil"><ProfileForm profile={profile} token={data.csrf_token} target={target} /></Card></Column></Columns>;
}

export const profileRoutes = [
  {
    pattern: /^\/profil$/,
    page: 'profile',
    title: 'Profil',
    domain: 'profiles',
    readContractKey: 'profile',
    resolveTitle: (route, data) => data.profile?.rufname || route.title,
    headerAction: () => (
      <Button
        aria-label="Profil bearbeiten"
        className="mobile-icon-action"
        size="responsive-icon"
        href="/profil/bearbeiten/"
      >
        <span className="desktop-action-label">Profil bearbeiten</span>
        <PencilIcon className="mobile-action-label" aria-hidden="true" />
      </Button>
    ),
    render: ({ data }) => <ProfilePage data={data} />,
  },
  {
    pattern: /^\/profil\/bearbeiten$/,
    page: 'profile-edit',
    title: 'Profil bearbeiten',
    domain: 'profiles',
    readContractKey: 'profile',
    render: ({ data }) => <ProfileEditPage data={data} />,
  },
  {
    pattern: /^\/profil\/(\d+)$/,
    page: 'profile-edit',
    title: 'Profil',
    domain: 'profiles',
    readContractKey: 'profile',
    params: match => ({ id: match[1] }),
    resolveTitle: (route, data) => data.profile?.rufname || route.title,
    render: ({ route, data }) => <ProfileEditPage data={data} target={`/profil/${route.id}/`} />,
  },
];
