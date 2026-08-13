import { cleanup, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { Toaster } from '../components/ui/toast';
import { AdminTeamOverviewPage } from './memberships';

const data = { years: [{ year: 2026, turnuses: [{
  id: 4,
  label: 'T2-2026',
  members: [
    { id: 11, name: 'Alex Muster', functional_role: 'teamer', role_label: 'Teamer', team_label: 'Küche' },
    { id: 12, name: 'Bea Beispiel', functional_role: 'leitung', role_label: 'Leitung', team_label: 'Organisation' },
  ],
  request_summary: { pending: 1 },
  pending_requests: [{ id: 21, name: 'Dana Anfrage' }],
}] }], people: [{ id: 30, name: 'Chris Frei', relationships: [], available: true }] };

function setMobile(matches) {
  window.matchMedia = vi.fn().mockReturnValue({
    matches,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
  });
}

describe('admin team overview', () => {
  afterEach(cleanup);

  it('renders the year, Turnus, functional roles, and membership-specific labels', () => {
    render(<Toaster><AdminTeamOverviewPage data={data} mutate={vi.fn()} /></Toaster>);
    expect(screen.getByRole('heading', { name: '2026' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'T2-2026' })).toBeInTheDocument();
    expect(screen.getByText('Teamer · Küche')).toBeInTheDocument();
    expect(screen.getByText('Leitung · Organisation')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Offene Anfragen (1)' })).toBeInTheDocument();
    expect(screen.getByText('Dana Anfrage')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Alex Muster bearbeiten: als Leitung einsetzen' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Bea Beispiel bearbeiten: Leitung entfernen' })).toBeInTheDocument();
  });

  it('searches people and Turnusse and changes Leitung through the mutation seam', async () => {
    const user = userEvent.setup();
    const mutate = vi.fn().mockResolvedValue({ functional_role: 'leitung' });
    render(<Toaster><AdminTeamOverviewPage data={data} mutate={mutate} /></Toaster>);
    const search = screen.getByRole('textbox', { name: 'Turnusse und Personen suchen' });
    await user.type(search, 'niemand');
    expect(screen.getByText('Keine Turnusse oder Personen gefunden.')).toBeInTheDocument();
    await user.clear(search);
    await user.click(screen.getByRole('button', { name: 'Alex Muster bearbeiten: als Leitung einsetzen' }));
    expect(mutate).toHaveBeenCalledWith('/api/admin/memberships/11/role/', { functional_role: 'leitung' });
    expect(await screen.findByRole('button', { name: 'Alex Muster bearbeiten: Leitung entfernen' })).toBeInTheDocument();
  });

  it('shows one selected Turnus detail and keeps it selected after a demotion', async () => {
    const user = userEvent.setup();
    const multiple = { years: [{ year: 2026, turnuses: [
      data.years[0].turnuses[0],
      { id: 5, label: 'T3-2026', members: [{ id: 13, name: 'Chris Demo', functional_role: 'leitung', role_label: 'Leitung', team_label: '' }] },
    ] }] };
    render(<Toaster><AdminTeamOverviewPage data={multiple} mutate={vi.fn().mockResolvedValue({})} /></Toaster>);
    expect(screen.getByText('Alex Muster')).toBeInTheDocument();
    expect(screen.queryByText('Chris Demo')).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'T3-2026 auswählen' }));
    await user.click(screen.getByRole('button', { name: 'Chris Demo bearbeiten: Leitung entfernen' }));
    expect(screen.getByText('Chris Demo')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'T3-2026 auswählen' })).toHaveAttribute('aria-pressed', 'true');
  });

  it('renders a real mobile single-column layout with a horizontal year-grouped selector', () => {
    setMobile(true);
    render(<Toaster><AdminTeamOverviewPage data={data} mutate={vi.fn()} /></Toaster>);
    expect(document.querySelector('[aria-label="Turnus auswählen"]')).toHaveClass('overflow-x-auto');
    expect(document.querySelector('[data-slot="team-master-detail"]')).toHaveAttribute('data-layout', 'mobile-single-column');
  });

  it('finds registered users without memberships and communicates availability', async () => {
    const user = userEvent.setup();
    render(<Toaster><AdminTeamOverviewPage data={data} mutate={vi.fn()} /></Toaster>);
    await user.type(screen.getByRole('textbox', { name: 'Turnusse und Personen suchen' }), 'Chris');
    expect(screen.getByText('Chris Frei')).toBeInTheDocument();
    expect(screen.getByText('Keine Teamzugehörigkeiten · verfügbar')).toBeInTheDocument();
  });
});
