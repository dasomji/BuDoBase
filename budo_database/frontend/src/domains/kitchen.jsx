import { Printer } from 'lucide-react';

import {
  Card,
  Column,
  Columns,
  FieldList,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
  TableScroll,
} from '../components';
import { Button } from '../components/ui/button';
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
    <div key={focus.id}>
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
    <div className="print-nobreak grid gap-3 py-4 first:pt-0" key={day}>
      <h2>Tag {day}</h2>
      <TableScroll
        className="kitchen-meal-table-scroll focus-visible:outline-2 focus-visible:outline-offset-2"
        tabIndex={0}
        aria-label={`Menüplan Tag ${day} horizontal scrollen`}
      >
        <Table className="meal-table min-w-[36rem]" aria-label={`Menüplan Tag ${day}`}>
          <TableHeader><TableRow><TableHead scope="col">Essen</TableHead><TableHead scope="col">Box</TableHead><TableHead scope="col">BuDo</TableHead><TableHead scope="col">Warm</TableHead><TableHead scope="col">Kochportionen</TableHead></TableRow></TableHeader>
          <TableBody>{mealTypes.map(([type, label]) => {
            const cookingFocuses = matchingFocuses(day, type, ['budo', 'warm']);
            const portions = cookingFocuses
              .reduce((sum, focus) => sum + participantCount(focus), 0);
            const cookingPortions = dietaryPortions(cookingFocuses);
            return (
              <TableRow key={type}>
                <TableCell>{label}</TableCell>
                <TableCell><MealFocusList focuses={matchingFocuses(day, type, ['box'])} /></TableCell>
                <TableCell><MealFocusList focuses={matchingFocuses(day, type, ['budo'])} /></TableCell>
                <TableCell><MealFocusList focuses={matchingFocuses(day, type, ['warm'])} /></TableCell>
                <TableCell>{portions ? `${portions} (${formatDietaryPortions(cookingPortions)})` : '---'}</TableCell>
              </TableRow>
            );
          })}</TableBody>
        </Table>
      </TableScroll>
    </div>
  ))}</>;
}

function IntoleranceList({ title, entries }) {
  return (
    <div>
      <h4>{title}</h4>
      {entries.length ? (
        <ul className="list-disc pl-4">{entries.map(entry => {
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
    <div className="focus-kitchen-info [&+&]:mt-4 [&+&]:border-t [&+&]:border-current [&+&]:pt-4 [&_h3]:mt-3 [&_h4]:mt-3">
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
      <Columns className="kitchen-layout grid grid-cols-1 items-start min-[901px]:grid-cols-[minmax(0,2fr)_minmax(20rem,1fr)] [&_.card-info-container]:min-w-0 [&_.card-info-content]:min-w-0 [&_.card]:min-w-0 [&_.detail-column]:min-w-0">
        <Column id="left-column">
          {weeks.map(week => (
            <Card title={`Menüplan Woche ${week === 'w1' ? 1 : 2}`} key={week}>
              <WeekMealPlan focuses={data.focuses.filter(focus => focus.week === week)} />
            </Card>
          ))}
        </Column>
        <Column id="right-column">
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
    <Button
      aria-label="Drucken"
      className="kitchen-print-button mobile-icon-action"
      type="button"
      onClick={() => window.print()}
    >
      <span className="desktop-action-label">Drucken</span>
      <Printer className="mobile-action-label" aria-hidden="true" />
    </Button>
  ),
  render: ({ data }) => <KitchenPage data={data} />,
}];
