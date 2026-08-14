import { PencilIcon } from 'lucide-react';

import { Card, Column, Columns, FieldList, NativeForm, ResponsiveCardGrid } from '../components';
import { Button } from '../components/ui/button';
import { NotFoundPage } from './shared';

const familyLabels = {
  S: 'Smallie',
  M: 'Medi',
  L: 'Largie',
  XL: 'X-largie',
};

function AssignedFocuses({ focuses = [] }) {
  return <><p><span className="label">Meine Schwerpunkte</span>:</p><ul>{focuses.length ? focuses.map(focus => <li key={focus.id}><a href={`/schwerpunkt/${focus.id}/`}>{focus.name}</a></li>) : <li>Keine Schwerpunkte zugeteilt.</li>}</ul></>;
}

function PersonCard({ person, focuses, id = 'db-profil', updateHref }) {
  return <Card title={person.rufname} id={id}><FieldList items={[
    ['Essen', person.food_display],
    ['BuDo-Familie', familyLabels[person.budo_family]],
    ['Allergien', person.allergies],
    ['Kaffee', person.coffee],
    ['Email', person.email ? <a href={`mailto:${person.email}`}>{person.email}</a> : null],
    ['Mobil', person.phone ? <a href={`tel:${person.phone}`}>{person.phone}</a> : null],
  ]} /><AssignedFocuses focuses={focuses} />{updateHref && <Button href={updateHref}>Informationen aktualisieren</Button>}</Card>;
}

export function TeamPage({ data }) {
  if (!data.team?.length) {
    return <Columns className="block"><p>Kein Team für den aktiven Turnus vorhanden.</p></Columns>;
  }
  const ownProfileId = data.profile?.id;
  const canChangeProfiles = Boolean(data.permissions?.change_profiles);
  return (
    <ResponsiveCardGrid>
      {data.team.map(person => {
        let updateHref = null;
        if (person.id === ownProfileId) updateHref = '/profil/bearbeiten/';
        else if (canChangeProfiles) updateHref = `/profil/${person.id}/`;
        return (
          <PersonCard
            id={`team-profile-${person.id}`}
            person={person}
            focuses={person.focuses}
            updateHref={updateHref}
            key={person.id}
          />
        );
      })}
    </ResponsiveCardGrid>
  );
}

export function ProfilePage({ data }) {
  const profile = data.profile;
  if (!profile) return <NotFoundPage />;
  return <Columns><Column id="single-column"><PersonCard person={profile} focuses={data.focuses} /></Column></Columns>;
}

export function ProfileEditPage({ data, target = '/profil/bearbeiten/' }) {
  const profile = data.profile;
  if (!profile) return <NotFoundPage />;
  const fields = [
    { name: 'rufname', label: 'Rufname', value: profile.rufname },
    { name: 'allergien', label: 'Allergien', value: profile.allergies },
    { name: 'coffee', label: 'Kaffee', value: profile.coffee },
    { name: 'essen', label: 'Essen', type: 'select', value: profile.food, options: [{ value: 'ft', label: 'Flexitarisch' }, { value: 'vt', label: 'Vegetarisch' }, { value: 'vn', label: 'Vegan' }] },
    { name: 'budo_family', label: 'BuDo-Familie', type: 'select', value: profile.budo_family, options: [{ value: '', label: 'Nicht zugeordnet' }, { value: 'S', label: 'Smallie' }, { value: 'M', label: 'Medi' }, { value: 'L', label: 'Largie' }, { value: 'XL', label: 'X-largie' }] },
    { name: 'telefonnummer', label: 'Telefonnummer', value: profile.phone },
  ];
  return <Columns><Column id="single-column"><Card title="Profil"><NativeForm token={data.csrf_token} action={target} fields={fields} /></Card></Column></Columns>;
}

export const profileRoutes = [
  {
    pattern: /^\/team$/,
    page: 'team',
    title: 'Team',
    domain: 'profiles',
    readContractKey: 'team',
    render: ({ data }) => <TeamPage data={data} />,
  },
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
