import { Children, useEffect, useState } from 'react';

import { Card, Column, Columns, FieldList, NativeForm } from '../components';
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

function PersonCard({ person, focuses, turnus, id = 'db-profil', updateHref }) {
  return <Card title={person.rufname} id={id}><FieldList items={[
    ['Rolle', person.role_display],
    ['Turnus', turnus?.label],
    ['Essen', person.food_display],
    ['BuDo-Familie', familyLabels[person.budo_family]],
    ['Allergien', person.allergies],
    ['Kaffee', person.coffee],
    ['Email', person.email ? <a href={`mailto:${person.email}`}>{person.email}</a> : null],
    ['Mobil', person.phone ? <a href={`tel:${person.phone}`}>{person.phone}</a> : null],
  ]} /><AssignedFocuses focuses={focuses} />{updateHref && <a className="button" href={updateHref}>Informationen aktualisieren</a>}</Card>;
}

const teamMediaQueries = ['(max-width: 900px)', '(max-width: 1200px)'];

function teamColumnCount() {
  if (typeof window === 'undefined' || !window.matchMedia) return 3;
  if (window.matchMedia(teamMediaQueries[0]).matches) return 1;
  if (window.matchMedia(teamMediaQueries[1]).matches) return 2;
  return 3;
}

function useTeamColumnCount() {
  const [count, setCount] = useState(teamColumnCount);

  useEffect(() => {
    const mediaQueries = teamMediaQueries.map(query => window.matchMedia(query));
    const update = () => setCount(teamColumnCount());
    mediaQueries.forEach(query => query.addEventListener('change', update));
    update();
    return () => mediaQueries.forEach(query => query.removeEventListener('change', update));
  }, []);

  return count;
}

function TeamColumns({ children }) {
  const columnCount = useTeamColumnCount();
  const columns = Array.from({ length: columnCount }, () => []);
  Children.toArray(children).forEach((card, index) => {
    columns[index % columnCount].push(card);
  });

  return (
    <Columns className="team-page">
      {columns.map((cards, index) => (
        <Column className="team-column" id={`team-column-${index + 1}`} key={index}>
          {cards}
        </Column>
      ))}
    </Columns>
  );
}

export function TeamPage({ data }) {
  if (!data.team?.length) {
    return <Columns className="team-page team-empty"><p>Kein Team für den aktiven Turnus vorhanden.</p></Columns>;
  }
  const ownProfileId = data.profile?.id;
  const canChangeProfiles = Boolean(data.permissions?.change_profiles);
  return (
    <TeamColumns>
      {data.team.map(person => {
        let updateHref = null;
        if (person.id === ownProfileId) updateHref = '/profil/';
        else if (canChangeProfiles) updateHref = `/profil/${person.id}/`;
        return (
          <PersonCard
            id={`team-profile-${person.id}`}
            person={person}
            focuses={person.focuses}
            turnus={data.turnus}
            updateHref={updateHref}
            key={person.id}
          />
        );
      })}
    </TeamColumns>
  );
}

export function ProfilePage({ data, target = '/profil/' }) {
  const profile = data.profile;
  if (!profile) return <NotFoundPage />;
  const fields = [
    { name: 'rufname', label: 'Rufname', value: profile.rufname },
    { name: 'allergien', label: 'Allergien', value: profile.allergies },
    { name: 'coffee', label: 'Kaffee', value: profile.coffee },
    { name: 'rolle', label: 'Rolle', type: 'select', value: profile.role, options: [{ value: 'b', label: 'Betreuer:in' }, { value: 'k', label: 'Küche' }, { value: 'o', label: 'Organisator' }, { value: 'f', label: 'Freiwillige:r' }] },
    { name: 'essen', label: 'Essen', type: 'select', value: profile.food, options: [{ value: 'ft', label: 'Flexitarisch' }, { value: 'vt', label: 'Vegetarisch' }, { value: 'vn', label: 'Vegan' }] },
    { name: 'budo_family', label: 'BuDo-Familie', type: 'select', value: profile.budo_family, options: [{ value: '', label: 'Nicht zugeordnet' }, { value: 'S', label: 'Smallie' }, { value: 'M', label: 'Medi' }, { value: 'L', label: 'Largie' }, { value: 'XL', label: 'X-largie' }] },
    { name: 'telefonnummer', label: 'Telefonnummer', value: profile.phone },
  ];
  if (profile.can_change_turnus) {
    fields.push({ name: 'turnus', label: 'Turnus', type: 'select', value: data.turnus?.id, options: data.turnuses.map(item => ({ value: item.id, label: item.label })) });
  }
  return <Columns><Column id="left-column"><PersonCard person={profile} focuses={data.focuses} turnus={data.turnus} /></Column><Column id="center-column"><Card title="Profil"><NativeForm token={data.csrf_token} action={target} fields={fields} /></Card></Column></Columns>;
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
    render: ({ data }) => <ProfilePage data={data} />,
  },
  {
    pattern: /^\/profil\/(\d+)$/,
    page: 'profile',
    title: 'Profil',
    domain: 'profiles',
    readContractKey: 'profile',
    params: match => ({ id: match[1] }),
    resolveTitle: (route, data) => data.profile?.rufname || route.title,
    render: ({ route, data }) => <ProfilePage data={data} target={`/profil/${route.id}/`} />,
  },
];
