import { Card, Column, Columns, FieldList } from '../components';
import { linkKid, MealTable } from './shared';

export function KitchenPage({ data }) {
  const weeks = ['w1', 'w2'];
  return <Columns><Column id="left-column">{weeks.map(week => <Card title={`Menüplan Woche ${week === 'w1' ? 1 : 2}`} key={week}><WeekMealPlan focuses={data.focuses.filter(focus => focus.week === week)} /></Card>)}</Column><Column id="center-column"><Card title="Essen & Allergien">{data.kids.filter(kid => kid.special_food).map(kid => <div className="print-nobreak" key={kid.id}><p>{linkKid(kid)} · {kid.food}</p><p>{kid.special_food}</p></div>)}</Card><Card title="Team">{data.team.map(member => <p key={member.id}>{member.rufname}: {member.food_display}{member.allergies && ` · ${member.allergies}`}</p>)}</Card></Column><Column id="right-column">{weeks.map(week => <Card title={`Schwerpunktinfos Woche ${week === 'w1' ? 1 : 2}`} key={week}>{data.focuses.filter(f => f.week === week).map(focus => <div key={focus.id}><h2>{focus.name}</h2><FieldList items={[["Kinder", focus.kid_ids.length], ["Betreuende", focus.carers], ["Ort", focus.place]]} /><MealTable focus={focus} /></div>)}</Card>)}</Column></Columns>;
}

function WeekMealPlan({ focuses }) {
  const maxDays = Math.max(0, ...focuses.map(focus => focus.duration));
  const types = [['breakfast', 'Frühstück'], ['lunch', 'Mittagessen'], ['dinner', 'Abendessen']];
  const cell = (day, type, choice) => focuses.filter(focus => focus.meal_items.some(meal => meal.day === day && meal.type === type && meal.choice === choice)).map(focus => `${focus.name} (${focus.kid_ids.length})`);
  return <>{Array.from({ length: maxDays }, (_, index) => index + 1).map(day => <div className="print-nobreak" key={day}><h2>Tag {day}</h2><table className="meal-table"><thead><tr><th>Essen</th><th>Box</th><th>BuDo</th><th>Warm</th><th>Kochportionen</th></tr></thead><tbody>{types.map(([type, label]) => { const budo = cell(day, type, 'budo'); const warm = cell(day, type, 'warm'); const portions = focuses.filter(focus => [...budo, ...warm].some(value => value.startsWith(`${focus.name} (`))).reduce((sum, focus) => sum + focus.kid_ids.length, 0); return <tr key={type}><td>{label}</td><td>{cell(day, type, 'box').join(', ') || '---'}</td><td>{budo.join(', ') || '---'}</td><td>{warm.join(', ') || '---'}</td><td>{portions || '---'}</td></tr>; })}</tbody></table></div>)}</>;
}

export const kitchenRoutes = [{
  pattern: /^\/kitchen$/,
  page: 'kitchen',
  title: 'Küche',
  domain: 'kitchen',
  readContractKey: 'kitchen',
  render: ({ data }) => <KitchenPage data={data} />,
}];
