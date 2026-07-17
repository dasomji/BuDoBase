import { cleanup, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';

import { DashboardPage } from './dashboard';

describe('dashboard page', () => {
  afterEach(cleanup);

  it('retains the operational cards for the legacy view model', () => {
    render(<DashboardPage data={{
      profile: { focus_ids: [], role_display: 'Betreuer:in', food_display: 'Vegetarisch', allergies: '', coffee: '', email: 'ada@example.com', phone: '' },
      team: [],
      totals: { pocket_money_paid: 0, pocket_money: 0, team_money: 0, checked_in: 0, kids: 0, train_arrival: 0, train_departure: 0 },
      kids: [],
      focuses: [],
      activity: { notes: [], transactions: [] },
      turnus: { label: 'T2' },
    }} />);

    expect(screen.getByRole('heading', { name: 'Mein Profil' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Kinder: 0' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Notizen' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Taschengeld-Transaktionen' })).toBeInTheDocument();
  });
});
