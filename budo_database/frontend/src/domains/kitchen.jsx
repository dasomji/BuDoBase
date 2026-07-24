import { Card, Column, Columns, FieldList } from '../components';
import { linkKid } from './shared';

const mealTypes = [
  ['breakfast', 'Frühstück'],
  ['lunch', 'Mittagessen'],
  ['dinner', 'Abendessen'],
];

const dietaryLabels = {
  flexitarian: 'Flexitarisch',
  vegetarian: 'Vegetarisch',
  vegan: 'Vegan',
};

function mealChoice(focus, day, type) {
  return focus.meals.find(meal => meal.day === day && meal.type === type)?.choice;
}

function participantCount(focus) {
  return focus.kid_count + (focus.carer_count ?? 0);
}

function dietaryPortions(focuses) {
  return focuses.reduce((totals, focus) => ({
    flexitarian: totals.flexitarian + (focus.dietary_counts?.flexitarian ?? 0),
    vegetarian: totals.vegetarian + (focus.dietary_counts?.vegetarian ?? 0),
    vegan: totals.vegan + (focus.dietary_counts?.vegan ?? 0),
  }), { flexitarian: 0, vegetarian: 0, vegan: 0 });
}

function formatDietaryPortions(counts) {
  return `${counts.flexitarian} 🥩, ${counts.vegetarian} 🧀, ${counts.vegan} 🌱`;
}

function MealFocusList({ focuses }) {
  if (!focuses.length) return '---';

  return focuses.map(focus => (
    <div className="kitchen-meal-focus" key={focus.id}>
      {focus.name} ({formatDietaryPortions(dietaryPortions([focus]))})
    </div>
  ));
}

function WeekMealPlan({ focuses }) {
  const maxDays = Math.max(0, ...focuses.map(focus => focus.duration));
  const matchingFocuses = (day, type, choices) => focuses.filter(focus => (
    choices.includes(mealChoice(focus, day, type))
  ));

  return <>{Array.from({ length: maxDays }, (_, index) => index + 1).map(day => (
    <div className="print-nobreak kitchen-meal-day" key={day}>
      <h2>Tag {day}</h2>
      <div
        className="kitchen-meal-table-scroll"
        tabIndex={0}
        aria-label={`Menüplan Tag ${day} horizontal scrollen`}
      >
        <table className="meal-table" aria-label={`Menüplan Tag ${day}`}>
          <thead><tr><th>Essen</th><th>Box</th><th>BuDo</th><th>Warm</th><th>Kochportionen</th></tr></thead>
          <tbody>{mealTypes.map(([type, label]) => {
            const cookingFocuses = matchingFocuses(day, type, ['budo', 'warm']);
            const portions = cookingFocuses
              .reduce((sum, focus) => sum + participantCount(focus), 0);
            const cookingPortions = dietaryPortions(cookingFocuses);
            return (
              <tr key={type}>
                <td>{label}</td>
                <td><MealFocusList focuses={matchingFocuses(day, type, ['box'])} /></td>
                <td><MealFocusList focuses={matchingFocuses(day, type, ['budo'])} /></td>
                <td><MealFocusList focuses={matchingFocuses(day, type, ['warm'])} /></td>
                <td>{portions ? `${portions} (${formatDietaryPortions(cookingPortions)})` : '---'}</td>
              </tr>
            );
          })}</tbody>
        </table>
      </div>
    </div>
  ))}</>;
}

function IntoleranceList({ title, entries }) {
  return (
    <div>
      <h4>{title}</h4>
      {entries.length ? (
        <ul>{entries.map(entry => {
          const diet = dietaryLabels[entry.diet];
          return (
            <li key={`${entry.name}-${entry.details}`}>
              {entry.name}{diet && ` (${diet})`}: {entry.details}
            </li>
          );
        })}</ul>
      ) : <p>Keine bekannt</p>}
    </div>
  );
}

function FocusKitchenInfo({ focus, headingLevel = 2 }) {
  const counts = focus.dietary_counts ?? {};
  const intolerances = focus.intolerances ?? { kids: [], team: [] };
  const Heading = `h${headingLevel}`;
  return (
    <div className="focus-kitchen-info">
      <Heading>{focus.name}</Heading>
      <FieldList items={[
        ['Kinder', focus.kid_count],
        ['Betreuende', focus.carers],
      ]} />
      <h3>Benötigte Portionen</h3>
      <FieldList items={[
        ['Flexitarisch', counts.flexitarian ?? 0],
        ['Vegetarisch', counts.vegetarian ?? 0],
        ['Vegan', counts.vegan ?? 0],
      ]} />
      <h3>Allergien & Unverträglichkeiten</h3>
      <div className="focus-intolerances">
        <IntoleranceList title="Kinder" entries={intolerances.kids ?? []} />
        <IntoleranceList title="Betreuende" entries={intolerances.team ?? []} />
      </div>
    </div>
  );
}

function KitchenPrintPages({ focuses, weeks }) {
  return (
    <section className="kitchen-print-pages" aria-label="Küchen-Druckseiten">
      {weeks.flatMap(week => {
        const weekFocuses = focuses.filter(focus => focus.week === week);
        if (!weekFocuses.length) return [];
        const weekNumber = week === 'w1' ? 1 : 2;
        return [
          <article
            className="kitchen-print-page kitchen-print-menu-page"
            aria-label={`Menüplan Woche ${weekNumber}`}
            key={`${week}-menu`}
          >
            <h1>Menüplan Woche {weekNumber}</h1>
            <WeekMealPlan focuses={weekFocuses} />
          </article>,
          ...weekFocuses.map(focus => (
            <article
              className="kitchen-print-page kitchen-print-focus-page"
              aria-label={`Schwerpunktzettel Woche ${weekNumber}: ${focus.name}`}
              key={`${week}-focus-${focus.id}`}
            >
              <p className="kitchen-print-kicker">Schwerpunktinfo Woche {weekNumber}</p>
              <FocusKitchenInfo focus={focus} headingLevel={1} />
            </article>
          )),
        ];
      })}
    </section>
  );
}

export function KitchenPage({ data }) {
  const weeks = ['w1', 'w2'];
  return (
    <>
      <Columns className="kitchen-layout">
        <Column id="left-column" className="kitchen-menu-column">
          {weeks.map(week => (
            <Card title={`Menüplan Woche ${week === 'w1' ? 1 : 2}`} key={week}>
              <WeekMealPlan focuses={data.focuses.filter(focus => focus.week === week)} />
            </Card>
          ))}
        </Column>
        <Column id="right-column" className="kitchen-info-column">
          <Card title="Essen & Allergien bei Kindern">
            {data.kids.filter(kid => kid.special_food).map(kid => (
              <div className="print-nobreak" key={kid.id}>
                <p>{linkKid(kid)} · {kid.food}</p>
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
          {weeks.map(week => (
            <Card title={`Schwerpunktinfos Woche ${week === 'w1' ? 1 : 2}`} key={week}>
              {data.focuses.filter(focus => focus.week === week).map(focus => (
                <FocusKitchenInfo focus={focus} key={focus.id} />
              ))}
            </Card>
          ))}
        </Column>
      </Columns>
      <KitchenPrintPages focuses={data.focuses} weeks={weeks} />
    </>
  );
}

export const kitchenRoutes = [{
  pattern: /^\/kitchen$/,
  page: 'kitchen',
  title: 'Küche',
  domain: 'kitchen',
  readContractKey: 'kitchen',
  headerAction: () => (
    <button className="button kitchen-print-button" type="button" onClick={() => window.print()}>
      Drucken
    </button>
  ),
  render: ({ data }) => <KitchenPage data={data} />,
}];
