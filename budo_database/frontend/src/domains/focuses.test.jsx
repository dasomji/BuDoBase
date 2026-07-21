import { cleanup, fireEvent, render, screen, within } from '@testing-library/react';
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
    document.cookie = 'swp_map_week=; Path=/; Max-Age=0';
  });

  it('renders a compact dashboard and flags focuses without meal assignments', () => {
    const unassignedFocus = { ...focus, id: 4, name: 'See', meals_assigned: false };
    render(<FocusDashboardPage data={{ focuses: [focus, unassignedFocus] }} />);

    const weekColumn = screen.getByRole('heading', { name: 'Woche 1' }).closest('.detail-column');
    const mapColumn = screen.getByRole('heading', { name: 'Karte' }).closest('.detail-column');
    expect(weekColumn).toHaveClass('focus-weeks-column');
    expect(mapColumn).toHaveClass('focus-map-column');
    expect(weekColumn.nextElementSibling).toBe(mapColumn);
    expect(screen.queryByRole('columnheader', { name: 'Essenseinteilung' })).not.toBeInTheDocument();
    expect(screen.queryByRole('columnheader', { name: 'Aktionen' })).not.toBeInTheDocument();

    const assignedName = screen.getByRole('link', { name: 'Wald' });
    expect(assignedName).toHaveAttribute('href', '/schwerpunkt/3/');
    expect(assignedName.closest('strong')).not.toBeNull();
    const row = assignedName.closest('tr');
    expect(within(row).getByRole('link', { name: 'Waldplatz' })).toHaveAttribute('href', '/auslagerorte/7/');
    expect(within(row).getByText('Grace')).toBeInTheDocument();
    expect(within(row).getByText('1')).toBeInTheDocument();
    expect(within(row).getByText('Ja')).toBeInTheDocument();

    const unassignedName = screen.getByRole('link', { name: 'See ❗🍔' });
    expect(unassignedName).toHaveAttribute('href', '/schwerpunkt/4/');
    expect(unassignedName.closest('strong')).not.toBeNull();
    expect(screen.queryByRole('link', { name: '🍔' })).not.toBeInTheDocument();
    expect(screen.queryByRole('link', { name: '✏️' })).not.toBeInTheDocument();
    expect(screen.queryByRole('link', { name: '👁️' })).not.toBeInTheDocument();
    const allocationLinks = screen.getAllByRole('link', { name: 'Kinder einteilen' });
    expect(allocationLinks).toEqual(
      expect.arrayContaining([expect.objectContaining({ href: expect.stringContaining('/swp-einteilung-w1') })]),
    );
    expect(allocationLinks[0].closest('.info-header-container')).not.toBeNull();
    expect(allocationLinks[0].closest('.card-info-container')).toBeNull();
  });

  it('switches map locations by week and remembers the selection', () => {
    globalThis.ResizeObserver = class {
      observe() {}
      disconnect() {}
    };
    const weekOne = { ...focus, coordinates: '48.2,16.3' };
    const weekTwo = { ...focus, id: 4, name: 'See', week: 'w2', coordinates: '48.3,16.4' };
    render(<FocusDashboardPage data={{ focuses: [weekOne, weekTwo] }} />);

    const weekOneButton = screen.getByRole('button', { name: 'Woche 1' });
    const weekTwoButton = screen.getByRole('button', { name: 'Woche 2' });
    expect(weekOneButton).toHaveAttribute('aria-pressed', 'true');
    expect(weekTwoButton).toHaveAttribute('aria-pressed', 'false');
    expect(document.querySelector('#map')).toHaveTextContent('Wald');
    expect(document.querySelector('#map')).not.toHaveTextContent('See');

    fireEvent.click(weekTwoButton);

    expect(weekTwoButton).toHaveAttribute('aria-pressed', 'true');
    expect(document.querySelector('#map')).toHaveTextContent('See');
    expect(document.querySelector('#map')).not.toHaveTextContent('Wald');
    expect(document.cookie).toContain('swp_map_week=w2');
  });

  it('renders one focused detail with assignments, timing, place, meals, and links', () => {
    render(<FocusDetailPage data={{ focus, kids: [kid] }} id="3" />);

    expect(screen.getByRole('heading', { name: 'Wald' })).toBeInTheDocument();
    expect(screen.getByText(/Bäume kennenlernen/)).toBeInTheDocument();
    const detailFields = document.querySelector('.focus-detail-fields');
    expect([...detailFields.querySelectorAll('p')].map(item => item.querySelector('.label').textContent)).toEqual([
      'Ort', 'Auslagern', 'Betreuende', 'Kinder', 'Wann', 'Beginnt am', 'Beschreibung',
    ]);
    expect(within(detailFields).getByText('Beschreibung').closest('p')).toHaveClass('full-width');
    expect(screen.getByRole('link', { name: 'Waldplatz' })).toHaveAttribute('href', '/auslagerorte/7/');
    expect(screen.getByText(/Grace/)).toBeInTheDocument();
    expect(screen.getByText('Beginnt am').closest('p')).toHaveTextContent('05.07.2026');
    expect(screen.queryByText('Geschätzte Abreise')).not.toBeInTheDocument();
    expect(screen.queryByText('Geschätzte Rückkehr')).not.toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Ada Kind' })).toHaveAttribute('href', '/kid_details/21');
    expect(screen.getByText('Asthmaspray')).toBeInTheDocument();
    expect(screen.getByText('Allergie')).toBeInTheDocument();
    const mealsCard = screen.getByRole('heading', { name: 'Essen' }).closest('.card');
    expect(mealsCard).toHaveClass('focus-meals-card');
    expect(within(mealsCard).getByText('warm')).toBeInTheDocument();
    const editFocus = screen.getByRole('link', { name: 'SWP bearbeiten' });
    expect(editFocus).toHaveAttribute('href', '/schwerpunkt/3/update');
    expect(editFocus.closest('.focus-detail-actions')).not.toBeNull();
    expect(within(mealsCard).getByRole('link', { name: 'Essen bearbeiten' })).toHaveAttribute('href', '/swpmeals/3');
    expect(within(mealsCard).getByRole('link', { name: 'Essen bearbeiten' }).closest('.react-actions')).not.toBeNull();
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
