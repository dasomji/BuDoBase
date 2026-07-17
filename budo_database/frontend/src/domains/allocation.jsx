import { Card, Column, Columns, SearchTable } from '../components';
import { displayOrPlaceholder, linkKid } from './shared';

export function AllocationPage({ data, week, mutate }) {
  const focuses = data.focuses.filter(focus => focus.week === `w${week}`);
  const rows = data.kids.map(kid => ({ ...kid, filterText: kid.full_name }));
  const columns = [
    { key: 'name', label: 'Name', render: linkKid },
    { key: 'assigned', label: 'Einteilung', sortValue: kid => focuses.find(focus => kid.focus_ids.includes(focus.id))?.name || '', render: kid => <select value={kid.focus_ids.find(id => focuses.some(f => f.id === id)) || ''} onChange={event => event.target.value && mutate('/update-schwerpunkt-wahl/', { kid_id: kid.id, swp_id: Number(event.target.value), choice_rank: null })}><option value="">Nicht zugeordnet</option>{focuses.map(focus => <option value={focus.id} key={focus.id}>{focus.name}</option>)}</select> },
    ...focuses.map(focus => ({ key: `focus-${focus.id}`, label: focus.name, render: kid => { const choice = kid.choices.find(item => item.week === `w${week}`); return <span className="swp-choice">{['1', '2', '3'].map(rank => <button className={Number(choice?.[{ 1: 'first', 2: 'second', 3: 'third' }[rank]]) === focus.id ? 'active' : ''} type="button" key={rank} onClick={() => mutate('/update-schwerpunkt-wahl/', { kid_id: kid.id, swp_id: focus.id, choice_rank: rank })}>{rank}</button>)}</span>; } })),
    { key: 'friends', label: 'Freunde', sortValue: kid => kid.choices.find(choice => choice.week === `w${week}`)?.friends || '', render: kid => { const friends = kid.choices.find(c => c.week === `w${week}`)?.friends || ''; return <>{friends || '---'} <button type="button" onClick={() => { const value = window.prompt('Freunde bearbeiten', friends); if (value !== null) mutate('/update_freunde/', { kid_id: kid.id, freunde: value, week }); }}>✏️</button></>; } },
    { key: 'age', label: 'Alter' },
    { key: 'siblings', label: 'Geschwister', render: kid => displayOrPlaceholder(kid.siblings) },
  ];
  return <Columns><Column id="left-column">{focuses.map(focus => <Card title={`${focus.name}: ${focus.kid_ids.length}`} key={focus.id}><ul>{data.kids.filter(kid => focus.kid_ids.includes(kid.id)).map(kid => <li key={kid.id}>{linkKid(kid)}</li>)}</ul></Card>)}</Column><Column id="right-column"><SearchTable columns={columns} rows={rows} showFilter /></Column></Columns>;
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
