import { cleanup, fireEvent, render, screen, within } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import App from '../App';
import { parseRoute } from '../routes';
import { KitchenPage } from './kitchen';

const response = data => ({
  ok: true,
  status: 200,
  json: vi.fn().mockResolvedValue(data),
});

describe('Küche page', () => {
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
    window.history.pushState({}, '', '/');
  });

  it('retains both weekly meal-plan and Schwerpunkt sections', () => {
    render(<KitchenPage data={{ focuses: [], kids: [], team: [] }} />);

    expect(screen.getByRole('heading', { name: 'Menüplan Woche 1' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Menüplan Woche 2' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Schwerpunktinfos Woche 1' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Essen & Allergien bei Kindern' })).toBeInTheDocument();

    const layout = document.querySelector('.kitchen-layout');
    expect(layout).not.toBeNull();
    expect([...layout.children].map(column => column.id)).toEqual(['left-column', 'right-column']);
    expect([...layout.querySelector('#right-column').querySelectorAll(':scope > .card > .card-toggle > h2')]
      .map(heading => heading.textContent)).toEqual([
      'Essen & Allergien bei Kindern',
      'Team',
      'Schwerpunktinfos Woche 1',
      'Schwerpunktinfos Woche 2',
    ]);
  });

  it('renders attendance, food, allergies, meals, and Schwerpunkt context from the focused projection', () => {
    render(<KitchenPage data={{
      kids: [{
        id: 7,
        full_name: 'Ada Lovelace',
        present: false,
        food: '🌱 - glutenfrei',
        special_food: 'glutenfrei',
      }],
      team: [{
        id: 3,
        rufname: 'Kathi',
        food_display: '🧀 Vegetarisch',
        allergies: 'Haselnüsse',
      }],
      focuses: [{
        id: 11,
        name: 'Waldküche',
        week: 'w1',
        duration: 1,
        kid_count: 1,
        carer_count: 1,
        carers: 'Kathi',
        dietary_counts: {
          flexitarian: 0,
          vegetarian: 1,
          vegan: 1,
        },
        intolerances: {
          kids: [{ name: 'Ada Lovelace', diet: 'vegetarian', details: 'glutenfrei' }],
          team: [{ name: 'Kathi', diet: 'vegan', details: 'Haselnüsse' }],
        },
        meals: [
          { day: 1, type: 'breakfast', choice: 'box' },
          { day: 1, type: 'lunch', choice: 'warm' },
          { day: 1, type: 'dinner', choice: 'budo' },
        ],
      }],
    }} />);

    const page = within(document.querySelector('.kitchen-layout'));
    expect(page.getByRole('link', { name: 'Ada Lovelace ❌' })).toHaveAttribute('href', '/kid_details/7');
    const kidFoodEntry = page.getByRole('link', { name: 'Ada Lovelace ❌' }).closest('.print-nobreak');
    expect(kidFoodEntry.querySelectorAll('p')).toHaveLength(1);
    expect(kidFoodEntry).toHaveTextContent('🌱 - glutenfrei');
    expect(page.getByText(/Kathi: 🧀 Vegetarisch · Haselnüsse/)).toBeInTheDocument();
    expect(page.getByText('Kinder', { selector: '.label' }).closest('p')).toHaveTextContent('Kinder: 1');
    expect(page.getByText('Betreuende', { selector: '.label' }).closest('p')).toHaveTextContent('Betreuende: Kathi');
    expect(page.queryByText('Ort')).not.toBeInTheDocument();
    expect(page.getByText('Flexitarisch').closest('p')).toHaveTextContent('Flexitarisch: 0');
    expect(page.getByText('Vegetarisch').closest('p')).toHaveTextContent('Vegetarisch: 1');
    expect(page.getByText('Vegan').closest('p')).toHaveTextContent('Vegan: 1');
    expect(page.getByText('Ada Lovelace (Vegetarisch): glutenfrei')).toBeInTheDocument();
    expect(page.getByText('Kathi (Vegan): Haselnüsse')).toBeInTheDocument();
    const focusInfo = page.getByRole('heading', { name: 'Waldküche' }).closest('.focus-kitchen-info');
    expect(focusInfo.querySelector('.card-table-container')).not.toBeInTheDocument();
    expect(page.getAllByText('Waldküche (0 🥩, 1 🧀, 1 🌱)')).toHaveLength(3);
    expect(page.getByRole('heading', { name: 'Tag 1' })).toBeInTheDocument();
    const menuTable = page.getByRole('table', { name: 'Menüplan Tag 1' });
    expect(within(menuTable).getAllByText('2 (0 🥩, 1 🧀, 1 🌱)')).toHaveLength(2);
    expect(page.getByLabelText('Menüplan Tag 1 horizontal scrollen')).toContainElement(menuTable);
  });

  it('renders each Schwerpunkt in a meal cell on its own line', () => {
    const focus = (id, name) => ({
      id,
      name,
      week: 'w1',
      duration: 1,
      kid_count: 1,
      carer_count: 0,
      dietary_counts: { flexitarian: 1, vegetarian: 0, vegan: 0 },
      meals: [{ day: 1, type: 'breakfast', choice: 'box' }],
    });
    render(<KitchenPage data={{
      kids: [],
      team: [],
      focuses: [focus(11, 'Blubb'), focus(12, 'Test'), focus(13, 'rumm')],
    }} />);

    const menuTable = within(document.querySelector('.kitchen-layout'))
      .getByRole('table', { name: 'Menüplan Tag 1' });
    const boxCell = within(menuTable).getByText('Frühstück').closest('tr').children[1];

    expect([...boxCell.querySelectorAll(':scope > .kitchen-meal-focus')]
      .map(entry => entry.textContent)).toEqual([
      'Blubb (1 🥩, 0 🧀, 0 🌱)',
      'Test (1 🥩, 0 🧀, 0 🌱)',
      'rumm (1 🥩, 0 🧀, 0 🌱)',
    ]);
  });

  it('provides one print menu page per active week and one page per Schwerpunkt', () => {
    const focus = (id, name, week) => ({
      id,
      name,
      week,
      duration: 1,
      kid_count: 1,
      carer_count: 0,
      carers: '',
      dietary_counts: { flexitarian: 1, vegetarian: 0, vegan: 0 },
      intolerances: { kids: [], team: [] },
      meals: [
        { day: 1, type: 'breakfast', choice: 'box' },
        { day: 1, type: 'lunch', choice: 'budo' },
        { day: 1, type: 'dinner', choice: 'warm' },
      ],
    });
    render(<KitchenPage data={{
      kids: [],
      team: [],
      focuses: [focus(11, 'Waldküche', 'w1'), focus(12, 'Seecamp', 'w2')],
    }} />);

    const printPages = screen.getByRole('region', { name: 'Küchen-Druckseiten', hidden: true });
    const pages = [...printPages.querySelectorAll(':scope > .kitchen-print-page')];
    expect(pages.map(page => page.getAttribute('aria-label'))).toEqual([
      'Menüplan Woche 1',
      'Schwerpunktzettel Woche 1: Waldküche',
      'Menüplan Woche 2',
      'Schwerpunktzettel Woche 2: Seecamp',
    ]);
    expect(within(pages[0]).getByRole('table', { name: 'Menüplan Tag 1', hidden: true })).toBeInTheDocument();
    expect(pages[1].querySelectorAll('.focus-kitchen-info')).toHaveLength(1);
    expect(within(pages[1]).getByRole('heading', { name: 'Waldküche', hidden: true })).toBeInTheDocument();
  });

  it('uses the Küche route contract and renders its response', async () => {
    expect(parseRoute('/kitchen')).toMatchObject({
      readContractKey: 'kitchen',
    });
    window.history.pushState({}, '', '/kitchen');
    const fetchImpl = vi.fn()
      .mockResolvedValueOnce(response({
        authenticated: true,
        csrf_token: 'token',
        messages: [],
        profile: { id: 1, rufname: 'Kathi' },
        turnus: { id: 2, label: 'T2' },
        permissions: {},
        search_index: { kids: [], focuses: [], places: [] },
      }))
      .mockResolvedValueOnce(response({ kids: [], team: [], focuses: [] }));

    const print = vi.spyOn(window, 'print').mockImplementation(() => {});
    render(<App fetchImpl={fetchImpl} />);

    expect(await screen.findByRole('heading', { name: 'Menüplan Woche 1' })).toBeInTheDocument();
    const printButton = screen.getByRole('button', { name: 'Drucken' });
    const search = screen.getByRole('combobox', { name: 'Suche' });
    expect(search.compareDocumentPosition(printButton) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    fireEvent.click(printButton);
    expect(print).toHaveBeenCalledOnce();
    expect(fetchImpl.mock.calls[1][0]).toBe('/api/route-data/kitchen/');
    expect(fetchImpl.mock.calls.some(([url]) => url.startsWith('/api/app-data/'))).toBe(false);
  });
});
