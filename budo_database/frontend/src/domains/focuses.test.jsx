import { cleanup, render, screen, within } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';

import {
  FocusDashboardPage,
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
  departure: '2026-07-05T09:30:00Z',
  arrival: '2026-07-05T18:00:00Z',
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
  afterEach(cleanup);

  it('renders dashboard summaries, counts, assignments, and all workflow links', () => {
    render(<FocusDashboardPage data={{ focuses: [focus] }} />);

    expect(screen.getByRole('heading', { name: 'Woche 1' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Wald' })).toHaveAttribute('href', '/schwerpunkt/3/');
    const row = screen.getByRole('link', { name: 'Wald' }).closest('tr');
    expect(within(row).getByRole('link', { name: 'Waldplatz' })).toHaveAttribute('href', '/auslagerorte/7/');
    expect(within(row).getByText('Grace')).toBeInTheDocument();
    expect(within(row).getByText('1')).toBeInTheDocument();
    expect(within(row).getAllByText('Ja')).toHaveLength(2);
    expect(within(row).getByRole('link', { name: '🍔' })).toHaveAttribute('href', '/swpmeals/3');
    expect(within(row).getByRole('link', { name: '✏️' })).toHaveAttribute('href', '/schwerpunkt/3/update');
    expect(within(row).getByRole('link', { name: '👁️' })).toHaveAttribute('href', '/schwerpunkt/3/');
    expect(screen.getAllByRole('link', { name: 'Kinder einteilen' })).toEqual(
      expect.arrayContaining([expect.objectContaining({ href: expect.stringContaining('/swp-einteilung-w1') })]),
    );
  });

  it('renders one focused detail with assignments, timing, place, meals, and links', () => {
    render(<FocusDetailPage data={{ focus, kids: [kid] }} id="3" />);

    expect(screen.getByRole('heading', { name: 'Wald' })).toBeInTheDocument();
    expect(screen.getByText(/Bäume kennenlernen/)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Waldplatz' })).toHaveAttribute('href', '/auslagerorte/7/');
    expect(screen.getByText(/Grace/)).toBeInTheDocument();
    expect(screen.getByText('Beginnt am').closest('p')).toHaveTextContent('05.07.2026');
    expect(screen.getByText('Geschätzte Abreise').closest('p')).toHaveTextContent('05.07.2026, 09:30');
    expect(screen.getByText('Geschätzte Rückkehr').closest('p')).toHaveTextContent('05.07.2026, 18:00');
    expect(screen.getByRole('link', { name: 'Ada Kind' })).toHaveAttribute('href', '/kid_details/21');
    expect(screen.getByText('Asthmaspray')).toBeInTheDocument();
    expect(screen.getByText('Allergie')).toBeInTheDocument();
    expect(screen.getByText('warm')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'SWP bearbeiten' })).toHaveAttribute('href', '/schwerpunkt/3/update');
    expect(screen.getByRole('link', { name: 'Essen bearbeiten' })).toHaveAttribute('href', '/swpmeals/3');
  });

  it('retains the create form, current option lists, and REST target', () => {
    render(<FocusFormPage data={options} />);

    expect(screen.getByRole('heading', { name: 'Schwerpunkt erstellen' })).toBeInTheDocument();
    expect(screen.getByLabelText('Schwerpunktname')).toBeRequired();
    expect(screen.getByLabelText('Schwerpunktname').form).toHaveAttribute('action', '/schwerpunkt/create');
    expect(screen.getByRole('option', { name: 'Waldplatz' })).toHaveValue('7');
    expect(screen.getByRole('option', { name: 'Grace' })).toHaveValue('5');
    expect(screen.getByRole('option', { name: 'Woche 1 (3 Tage) - T2-2026' })).toHaveValue('11');
  });

  it('retains focused update values and target', () => {
    render(<FocusFormPage data={{ ...options, focus }} id="3" />);

    expect(screen.getByRole('heading', { name: 'Schwerpunkt updaten' })).toBeInTheDocument();
    expect(screen.getByLabelText('Schwerpunktname')).toHaveValue('Wald');
    expect(screen.getByLabelText('Ort')).toHaveValue('7');
    expect(screen.getByLabelText('Betreuende')).toHaveValue(['5']);
    expect(screen.getByLabelText('Schwerpunktzeit')).toHaveValue('11');
    expect(screen.getByLabelText('Auslagern')).toBeChecked();
    expect(screen.getByLabelText('Geplante Abreise')).toHaveValue('2026-07-05T09:30');
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
        ],
      },
      meal_types: { breakfast: 'Frühstück', lunch: 'Mittagessen', dinner: 'Abendessen' },
      meal_choices: [
        { value: '', label: '---------' },
        { value: 'box', label: 'Box' },
        { value: 'budo', label: 'Im BuDo' },
        { value: 'warm', label: 'Warm geliefert' },
      ],
    };

    render(<MealsPage data={mealData} id="3" />);

    expect(screen.getByRole('heading', { name: 'Wann esst ihr wo?' })).toBeInTheDocument();
    expect(screen.getByLabelText('Tag 1 · Frühstück')).toHaveValue('box');
    expect(screen.getByLabelText('Tag 1 · Mittagessen')).toHaveValue('warm');
    expect(screen.getByLabelText('Tag 1 · Frühstück').form).toHaveAttribute('action', '/swpmeals/3');
    expect(screen.getAllByRole('option', { name: 'Im BuDo' })).toHaveLength(2);
  });

  it('declares every focus route contract without changing its browser URL', () => {
    expect(focusRoutes).toHaveLength(5);
    expect(focusRoutes.every(route => route.readContractKey)).toBe(true);
  });
});
