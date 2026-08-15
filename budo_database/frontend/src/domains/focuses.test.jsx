import { cleanup, render, screen, within } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';

import {
  FocusDetailPage,
  FocusFormPage,
  focusRoutes,
  MealsPage,
} from './focuses';

const focus = {
  id: 3,
  name: 'Wald',
  description: 'Bäume kennenlernen',
  week: 'w1',
  time: 'Woche 1 (3 Tage) - T2-2026',
  time_id: 11,
  start: '2026-07-05',
  off_site: true,
  place_id: 7,
  place: 'Waldplatz',
  coordinates: '',
  carers: 'Grace',
  carer_ids: [5],
  kid_count: 1,
  meals_assigned: true,
  meals: {
    1: { breakfast: '', lunch: 'warm', dinner: '' },
  },
};

const kid = {
  id: 21,
  full_name: 'Ada Kind',
  present: true,
  budo_family: 'M',
  sex_short: '♀',
  age: 14,
  birthday_during_turnus: true,
  food: '🥩',
  drugs: 'Asthmaspray',
  illness: 'Allergie',
};

const options = {
  csrf_token: 'token',
  places: [{ id: 7, name: 'Waldplatz' }],
  team: [{ id: 5, rufname: 'Grace' }],
  focus_times: [{ id: 11, label: 'Woche 1 (3 Tage) - T2-2026' }],
};

describe('Schwerpunkte pages', () => {
  afterEach(() => {
    cleanup();
    window.history.pushState({}, '', '/');
  });

  it('renders one focused detail with assignments, timing, place, meals, and links', () => {
    render(<FocusDetailPage data={{ focus, kids: [kid] }} id="3" />);

    expect(screen.getByRole('heading', { name: 'Wald' })).toBeInTheDocument();
    expect(screen.getByText(/Bäume kennenlernen/)).toBeInTheDocument();
    const detailFields = screen.getByRole('heading', { name: 'Wald' }).closest('.card').querySelector('.card-info-content > div');
    expect([...detailFields.querySelectorAll('p')].map(item => item.querySelector('.label').textContent)).toEqual([
      'Ort', 'Auslagern', 'Betreuende', 'Kinder', 'Wann', 'Beginnt am', 'Beschreibung',
    ]);
    expect(screen.getByRole('link', { name: 'Waldplatz' })).toHaveAttribute('href', '/auslagerorte/7/');
    expect(screen.getByText(/Grace/)).toBeInTheDocument();
    expect(screen.getByText('Beginnt am').closest('p')).toHaveTextContent('05.07.2026');
    expect(screen.queryByText('Geschätzte Abreise')).not.toBeInTheDocument();
    expect(screen.queryByText('Geschätzte Rückkehr')).not.toBeInTheDocument();
    const kidRow = screen.getByRole('link', { name: 'Ada Kind' }).closest('tr');
    expect(within(kidRow).getByText('🥳 14')).toBeInTheDocument();
    expect(within(kidRow).getByRole('link', { name: 'Ada Kind' })).toHaveAttribute('href', '/kid_details/21');
    expect(screen.getByText('Asthmaspray')).toBeInTheDocument();
    expect(screen.getByText('Allergie')).toBeInTheDocument();
    const detailsCard = screen.getByRole('heading', { name: 'Wald' }).closest('.card');
    const mealsCard = screen.getByRole('heading', { name: 'Essen' }).closest('.card');
    expect(within(mealsCard).getByRole('rowheader', { name: 'Tag 1' })).toBeInTheDocument();
    expect(within(mealsCard).getByText('warm')).toBeInTheDocument();
    const overview = screen.getByRole('region', { name: 'Schwerpunktübersicht' });
    expect(overview).toContainElement(detailsCard);
    expect(overview).toContainElement(mealsCard);
    expect(overview).not.toContainElement(kidRow);
    expect(overview.compareDocumentPosition(kidRow) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(screen.queryByRole('heading', { name: 'Karte' })).not.toBeInTheDocument();
    const editFocus = screen.getByRole('link', { name: 'SWP bearbeiten' });
    expect(editFocus).toHaveAttribute('href', '/schwerpunkt/3/update');
    expect(within(mealsCard).getByRole('link', { name: 'Essen bearbeiten' })).toHaveAttribute('href', '/swpmeals/3');
  });

  it('retains the create form, current option lists, and REST target', () => {
    render(<FocusFormPage data={options} />);

    expect(screen.getByRole('heading', { name: 'Schwerpunkt erstellen' })).toBeInTheDocument();
    expect(screen.getByLabelText('Schwerpunktzeit').compareDocumentPosition(screen.getByLabelText('Schwerpunktname')) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(screen.getByLabelText('Schwerpunktname')).toBeRequired();
    expect(screen.getByLabelText('Schwerpunktname').form).toHaveAttribute('action', '/schwerpunkt/create');
    expect(screen.getByRole('option', { name: 'Waldplatz' })).toHaveValue('7');
    expect(screen.getByRole('group', { name: 'Lagert ihr aus?' })).toBeInTheDocument();
    expect(screen.getByRole('checkbox', { name: 'Ja' })).not.toBeChecked();
    expect(screen.getByRole('group', { name: 'Betreuende' })).toBeInTheDocument();
    expect(screen.getByRole('checkbox', { name: 'Grace' })).toHaveAttribute('value', '5');
    expect(screen.getByRole('checkbox', { name: 'Grace' })).not.toBeChecked();
    expect(screen.getByRole('option', { name: 'Woche 1 (3 Tage) - T2-2026' })).toHaveValue('11');
    expect(screen.getByRole('link', { name: 'Cancel' })).toHaveAttribute('href', '/swp-einteilung-w1');
  });

  it('returns from focus creation to the allocation week it was opened from', () => {
    window.history.pushState({}, '', '/schwerpunkt/create?from=w2');
    const createRoute = focusRoutes.find(route => route.page === 'focus-create');

    render(createRoute.render({ data: options }));

    expect(screen.getByRole('link', { name: 'Cancel' })).toHaveAttribute('href', '/swp-einteilung-w2');
  });

  it('returns from focus updates to the focus allocation week', () => {
    const weekTwoFocus = { ...focus, time_id: 12 };
    delete weekTwoFocus.week;
    render(<FocusFormPage
      data={{
        ...options,
        focus: weekTwoFocus,
        focus_times: [{ id: 12, label: 'Woche 2 (3 Tage) - T2-2026', week: 'w2' }],
      }}
      id="3"
    />);

    expect(screen.getByRole('link', { name: 'Cancel' })).toHaveAttribute('href', '/swp-einteilung-w2');
  });

  it('retains focused update values and target', () => {
    render(<FocusFormPage data={{ ...options, focus }} id="3" />);

    expect(screen.getByRole('heading', { name: 'Schwerpunkt updaten' })).toBeInTheDocument();
    expect(screen.getByLabelText('Schwerpunktname')).toHaveValue('Wald');
    expect(screen.getByLabelText('Ort')).toHaveValue('7');
    expect(screen.getByRole('checkbox', { name: 'Grace' })).toBeChecked();
    expect(screen.getByRole('checkbox', { name: 'Grace' })).toHaveAttribute('name', 'betreuende');
    expect(screen.getByLabelText('Schwerpunktzeit')).toHaveValue('11');
    expect(screen.getByRole('group', { name: 'Lagert ihr aus?' })).toBeInTheDocument();
    expect(screen.getByRole('checkbox', { name: 'Ja' })).toBeChecked();
    expect(screen.getByLabelText('Ort').compareDocumentPosition(screen.getByRole('group', { name: 'Lagert ihr aus?' })) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(screen.queryByLabelText('Geplante Abreise')).not.toBeInTheDocument();
    expect(screen.queryByLabelText('Geplante Ankunft')).not.toBeInTheDocument();
    const cancel = screen.getByRole('link', { name: 'Cancel' });
    expect(cancel).toHaveAttribute('href', '/swp-einteilung-w1');
    expect(cancel.parentElement).toHaveClass('form-buttons');
    expect(cancel.parentElement).toContainElement(screen.getByRole('button', { name: 'Speichern' }));
    expect(screen.getByLabelText('Schwerpunktzeit').compareDocumentPosition(screen.getByLabelText('Schwerpunktname')) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(screen.getByLabelText('Schwerpunktname').form).toHaveAttribute('action', '/schwerpunkt/3/update');
  });

  it('retains meal day/type choices, saved values, and REST target', () => {
    const mealData = {
      csrf_token: 'token',
      focus: {
        id: 3,
        name: 'Wald',
        meal_items: [
          { id: 31, day: 1, type: 'breakfast', choice: 'box' },
          { id: 32, day: 1, type: 'lunch', choice: 'warm' },
          { id: 33, day: 1, type: 'dinner', choice: 'budo' },
          { id: 34, day: 2, type: 'breakfast', choice: 'budo' },
          { id: 35, day: 2, type: 'lunch', choice: 'box' },
          { id: 36, day: 2, type: 'dinner', choice: 'warm' },
          { id: 37, day: 3, type: 'breakfast', choice: 'warm' },
          { id: 38, day: 3, type: 'lunch', choice: 'budo' },
          { id: 39, day: 3, type: 'dinner', choice: 'box' },
        ],
      },
      meal_types: { breakfast: 'Frühstück', lunch: 'Mittagessen', dinner: 'Abendessen' },
      meal_choices: [
        { value: '', label: '---------' },
        { value: 'budo', label: 'BuDo' },
        { value: 'box', label: 'Box' },
        { value: 'warm', label: 'Warm' },
      ],
    };

    render(<MealsPage data={mealData} id="3" />);

    expect(screen.getByRole('heading', { name: 'Wann esst ihr wo?' })).toBeInTheDocument();
    expect(screen.getAllByRole('columnheader').map(header => header.textContent)).toEqual([
      'Tag', 'Frühstück', 'Mittagessen', 'Abendessen',
    ]);
    expect(screen.getAllByRole('rowheader').map(header => header.textContent)).toEqual([
      'Tag 1', 'Tag 2', 'Tag 3',
    ]);
    expect(screen.getAllByRole('combobox')).toHaveLength(9);
    expect(screen.getByRole('combobox', { name: 'Tag 1 · Frühstück' })).toHaveValue('box');
    expect(screen.getByRole('combobox', { name: 'Tag 1 · Mittagessen' })).toHaveValue('warm');
    expect(screen.getByRole('combobox', { name: 'Tag 3 · Abendessen' })).toHaveValue('box');
    expect(screen.getByRole('combobox', { name: 'Tag 1 · Frühstück' }).form).toHaveAttribute('action', '/swpmeals/3');
    expect(screen.getAllByRole('option', { name: 'BuDo' })).toHaveLength(9);
    expect(screen.getAllByRole('option', { name: 'Box' })).toHaveLength(9);
    expect(screen.getAllByRole('option', { name: 'Warm' })).toHaveLength(9);
    expect(screen.getByRole('table').closest('[data-slot="table-scroll"]')).not.toBeNull();
  });

  it('declares every remaining focus route contract without changing its browser URL', () => {
    expect(focusRoutes).toHaveLength(4);
    expect(focusRoutes.every(route => route.readContractKey)).toBe(true);
  });
});
