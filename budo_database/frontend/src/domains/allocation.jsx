import { Card, Column, Columns, SearchTable } from '../components';
import { displayOrPlaceholder, linkKid } from './shared';

const EMPTY_STATS = {
  average_age: null,
  sex: { male: 0, female: 0, diverse: 0 },
  families: { S: 0, M: 0, L: 0, XL: 0 },
};

function formatAverageAge(value) {
  if (value === null || value === undefined || !Number.isFinite(Number(value))) return '---';
  return new Intl.NumberFormat('de-AT', {
    minimumFractionDigits: 1,
    maximumFractionDigits: 2,
  }).format(Number(value));
}

function AllocationStats({ focus }) {
  const stats = focus.stats || EMPTY_STATS;
  const sex = { ...EMPTY_STATS.sex, ...stats.sex };
  const families = { ...EMPTY_STATS.families, ...stats.families };
  return (
    <div className="allocation-stats" aria-label={`Statistik ${focus.name}`}>
      <p><span className="label">Ø Alter</span>: {formatAverageAge(stats.average_age)}</p>
      <p><span className="label">Geschlechter</span>: {sex.male} ♂ · {sex.female} ♀ · {sex.diverse} ⚧</p>
      <p><span className="label">BuDo-Familien</span>: {families.S} S · {families.M} M · {families.L} L · {families.XL} XL</p>
    </div>
  );
}

function AllocationCard({ focus, kids }) {
  const assignedKids = kids.filter(kid => focus.kid_ids.includes(kid.id));
  return (
    <Card title={`${focus.name}: ${focus.kid_ids.length}`}>
      <AllocationStats focus={focus} />
      <ul className="allocation-kids">
        {assignedKids.map(kid => <li key={kid.id}>{linkKid(kid)}</li>)}
      </ul>
    </Card>
  );
}

export function AllocationPage({ data, week, mutate }) {
  const focuses = data.focuses.filter(focus => focus.week === `w${week}`);
  const rows = data.kids.map(kid => ({ ...kid, filterText: kid.full_name }));
  const columns = [
    { key: 'name', label: 'Name', render: linkKid },
    {
      key: 'assigned',
      label: 'Einteilung',
      sortValue: kid => focuses.find(focus => kid.focus_ids.includes(focus.id))?.name || '',
      render: kid => (
        <select
          value={kid.focus_ids.find(id => focuses.some(focus => focus.id === id)) || ''}
          onChange={event => event.target.value && mutate('/update-schwerpunkt-wahl/', {
            kid_id: kid.id,
            swp_id: Number(event.target.value),
            choice_rank: null,
          })}
        >
          <option value="">Nicht zugeordnet</option>
          {focuses.map(focus => <option value={focus.id} key={focus.id}>{focus.name}</option>)}
        </select>
      ),
    },
    ...focuses.map(focus => ({
      key: `focus-${focus.id}`,
      label: focus.name,
      render: kid => {
        const choice = kid.choices.find(item => item.week === `w${week}`);
        return (
          <span className="swp-choice">
            {['1', '2', '3'].map(rank => {
              const choiceKey = { 1: 'first', 2: 'second', 3: 'third' }[rank];
              const selected = Number(choice?.[choiceKey]) === focus.id;
              return (
                <button
                  className={selected ? 'active' : ''}
                  type="button"
                  key={rank}
                  aria-pressed={selected}
                  onClick={() => mutate('/update-schwerpunkt-wahl/', {
                    kid_id: kid.id,
                    swp_id: focus.id,
                    choice_rank: rank,
                  })}
                >
                  {rank}
                </button>
              );
            })}
          </span>
        );
      },
    })),
    {
      key: 'friends',
      label: 'Freunde',
      sortValue: kid => kid.choices.find(choice => choice.week === `w${week}`)?.friends || '',
      render: kid => {
        const friends = kid.choices.find(choice => choice.week === `w${week}`)?.friends || '';
        return (
          <>
            {friends || '---'}{' '}
            <button
              type="button"
              onClick={() => {
                const value = window.prompt('Freunde bearbeiten', friends);
                if (value !== null) mutate('/update_freunde/', { kid_id: kid.id, freunde: value, week });
              }}
            >
              ✏️
            </button>
          </>
        );
      },
    },
    { key: 'age', label: 'Alter' },
    { key: 'siblings', label: 'Geschwister', render: kid => displayOrPlaceholder(kid.siblings) },
  ];
  return (
    <Columns className="allocation-page">
      <Column id="left-column" className="allocation-card-column">
        {focuses.map(focus => <AllocationCard focus={focus} kids={data.kids} key={focus.id} />)}
      </Column>
      <Column id="right-column" className="allocation-table-column">
        <SearchTable columns={columns} rows={rows} showFilter />
      </Column>
    </Columns>
  );
}

export const allocationRoutes = [{
  pattern: /^\/swp-einteilung-w([12])$/,
  page: 'allocation',
  title: 'SWP-Einteilung',
  domain: 'allocation',
  readContractKey: 'allocation',
  params: match => ({ week: match[1], title: `SWP-Einteilung Woche ${match[1]}` }),
  render: ({ route, data, mutate }) => <AllocationPage data={data} week={route.week} mutate={mutate} />,
}];
