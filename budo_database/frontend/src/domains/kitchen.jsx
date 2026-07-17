import { Card, Column, Columns, FieldList } from '../components';
import { displayOrPlaceholder, linkKid } from './shared';

const mealTypes = [
  ['breakfast', 'Frühstück'],
  ['lunch', 'Mittagessen'],
  ['dinner', 'Abendessen'],
];

function mealChoice(focus, day, type) {
  return focus.meals.find(meal => meal.day === day && meal.type === type)?.choice;
}

function FocusMealTable({ focus }) {
  const days = Array.from({ length: focus.duration }, (_, index) => index + 1);
  return (
    <div className="card-table-container">
      <table className="card-table">
        <thead><tr><th /><th>Frühstück</th><th>Mittagessen</th><th>Abendessen</th></tr></thead>
        <tbody>{days.map(day => (
          <tr key={day}>
            <td>Tag {day}</td>
            {mealTypes.map(([type]) => (
              <td key={type}>{displayOrPlaceholder(mealChoice(focus, day, type))}</td>
            ))}
          </tr>
        ))}</tbody>
      </table>
    </div>
  );
}

function WeekMealPlan({ focuses }) {
  const maxDays = Math.max(0, ...focuses.map(focus => focus.duration));
  const matchingFocuses = (day, type, choices) => focuses.filter(focus => (
    choices.includes(mealChoice(focus, day, type))
  ));
  const cell = (day, type, choice) => matchingFocuses(day, type, [choice])
    .map(focus => `${focus.name} (${focus.kid_count})`);

  return <>{Array.from({ length: maxDays }, (_, index) => index + 1).map(day => (
    <div className="print-nobreak" key={day}>
      <h2>Tag {day}</h2>
      <table className="meal-table">
        <thead><tr><th>Essen</th><th>Box</th><th>BuDo</th><th>Warm</th><th>Kochportionen</th></tr></thead>
        <tbody>{mealTypes.map(([type, label]) => {
          const portions = matchingFocuses(day, type, ['budo', 'warm'])
            .reduce((sum, focus) => sum + focus.kid_count, 0);
          return (
            <tr key={type}>
              <td>{label}</td>
              <td>{cell(day, type, 'box').join(', ') || '---'}</td>
              <td>{cell(day, type, 'budo').join(', ') || '---'}</td>
              <td>{cell(day, type, 'warm').join(', ') || '---'}</td>
              <td>{portions || '---'}</td>
            </tr>
          );
        })}</tbody>
      </table>
    </div>
  ))}</>;
}

export function KitchenPage({ data }) {
  const weeks = ['w1', 'w2'];
  return (
    <Columns>
      <Column id="left-column">
        {weeks.map(week => (
          <Card title={`Menüplan Woche ${week === 'w1' ? 1 : 2}`} key={week}>
            <WeekMealPlan focuses={data.focuses.filter(focus => focus.week === week)} />
          </Card>
        ))}
      </Column>
      <Column id="center-column">
        <Card title="Essen & Allergien">
          {data.kids.filter(kid => kid.special_food).map(kid => (
            <div className="print-nobreak" key={kid.id}>
              <p>{linkKid(kid)} · {kid.food}</p>
              <p>{kid.special_food}</p>
            </div>
          ))}
        </Card>
        <Card title="Team">
          {data.team.map(member => (
            <p key={member.id}>
              {member.rufname}: {member.food_display}
              {member.allergies && ` · ${member.allergies}`}
            </p>
          ))}
        </Card>
      </Column>
      <Column id="right-column">
        {weeks.map(week => (
          <Card title={`Schwerpunktinfos Woche ${week === 'w1' ? 1 : 2}`} key={week}>
            {data.focuses.filter(focus => focus.week === week).map(focus => (
              <div key={focus.id}>
                <h2>{focus.name}</h2>
                <FieldList items={[
                  ['Kinder', focus.kid_count],
                  ['Betreuende', focus.carers],
                  ['Ort', focus.place],
                ]} />
                <FocusMealTable focus={focus} />
              </div>
            ))}
          </Card>
        ))}
      </Column>
    </Columns>
  );
}

export const kitchenRoutes = [{
  pattern: /^\/kitchen$/,
  page: 'kitchen',
  title: 'Küche',
  domain: 'kitchen',
  readContractKey: 'kitchen',
  render: ({ data }) => <KitchenPage data={data} />,
}];
