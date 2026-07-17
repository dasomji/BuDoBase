import { cleanup, render, screen } from '@testing-library/react';
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
  });

  it('renders attendance, food, allergies, meals, and Schwerpunkt context from the focused projection', () => {
    render(<KitchenPage data={{
      kids: [{
        id: 7,
        full_name: 'Ada Lovelace',
        present: false,
        food: '🥦 - glutenfrei',
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
        carers: 'Kathi',
        place: 'Waldhaus',
        meals: [
          { day: 1, type: 'breakfast', choice: 'box' },
          { day: 1, type: 'lunch', choice: 'warm' },
          { day: 1, type: 'dinner', choice: 'budo' },
        ],
      }],
    }} />);

    expect(screen.getByRole('link', { name: 'Ada Lovelace ❌' })).toHaveAttribute('href', '/kid_details/7');
    expect(screen.getByText('glutenfrei')).toBeInTheDocument();
    expect(screen.getByText(/Kathi: 🧀 Vegetarisch · Haselnüsse/)).toBeInTheDocument();
    expect(screen.getByText('Kinder').closest('p')).toHaveTextContent('Kinder: 1');
    expect(screen.getByText('Betreuende').closest('p')).toHaveTextContent('Betreuende: Kathi');
    expect(screen.getByText('Ort').closest('p')).toHaveTextContent('Ort: Waldhaus');
    expect(screen.getAllByText('Waldküche (1)').length).toBeGreaterThan(0);
    expect(screen.getByRole('heading', { name: 'Tag 1' })).toBeInTheDocument();
  });

  it('opts only Küche into its focused read contract and renders its response', async () => {
    expect(parseRoute('/kitchen')).toMatchObject({
      readContractKey: 'kitchen',
      focusedReadContract: true,
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

    render(<App fetchImpl={fetchImpl} />);

    expect(await screen.findByRole('heading', { name: 'Menüplan Woche 1' })).toBeInTheDocument();
    expect(fetchImpl.mock.calls[1][0]).toBe('/api/route-data/kitchen/');
    expect(fetchImpl.mock.calls.some(([url]) => url.startsWith('/api/app-data/'))).toBe(false);
  });
});
