import { cleanup, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { Toaster } from '../components/ui/toast';
import { AdminTeamOverviewPage } from './memberships';

const viewport = vi.hoisted(() => ({ mobile: false }));
vi.mock('../hooks/use-mobile', () => ({ useIsMobile: () => viewport.mobile }));

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

describe('admin team overview', () => {
  afterEach(() => {
    cleanup();
    viewport.mobile = false;
  });

  it('prominently repeats the email identity warning and resolves a request explicitly', async () => {
    const user = userEvent.setup();
    const mutate = vi.fn().mockResolvedValue({
      status: 'approved',
      membership_id: 40,
      approved_member: {
        id: 40, user_id: 41, name: 'Dana Anfrage', functional_role: 'teamer', role_label: 'Teamer', team_label: '',
      },
    });
    const warning = 'Bitte kontaktiere die Person über einen dir bekannten, unabhängigen Kanal. Prüfe dabei, dass die E-Mail-Adresse wirklich zu ihr gehört und dass sie diese Anfrage selbst gestellt hat.';
    render(<Toaster><AdminTeamOverviewPage data={{ ...data, identity_verification_warning: warning, can_manage_leitung: false }} mutate={mutate} /></Toaster>);

    expect(screen.getByRole('alert')).toHaveTextContent(warning);
    await user.click(screen.getByRole('button', { name: 'Dana Anfrage annehmen' }));
    expect(mutate).toHaveBeenCalledWith('/api/join-requests/21/decision/', { decision: 'approve' });
    expect(await screen.findByText('Keine offenen Anfragen.')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Team (3)' })).toBeInTheDocument();
    expect(screen.getByText('Dana Anfrage')).toBeInTheDocument();
    expect(screen.getByText('Teamer', { selector: 'p' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Alex Muster bearbeiten/ })).not.toBeInTheDocument();
  });

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

  it('lets desktop users choose an ordered Turnus and see only its detail', async () => {
    const user = userEvent.setup();
    const multiple = { years: [{ year: 2026, turnuses: [
      data.years[0].turnuses[0],
      { id: 5, label: 'T3-2026', members: [{ id: 13, name: 'Chris Demo', functional_role: 'teamer', role_label: 'Teamer', team_label: '' }] },
    ] }, { year: 2025, turnuses: [
      { id: 3, label: 'T1-2025', members: [{ id: 10, name: 'Zora Alt', functional_role: 'teamer', role_label: 'Teamer', team_label: '' }] },
    ] }] };
    render(<Toaster><AdminTeamOverviewPage data={multiple} mutate={vi.fn()} /></Toaster>);

    expect(screen.getAllByRole('button', { name: / auswählen$/ }).map(button => button.getAttribute('aria-label')))
      .toEqual(['T2-2026 auswählen', 'T3-2026 auswählen', 'T1-2025 auswählen']);
    await user.click(screen.getByRole('button', { name: 'T3-2026 auswählen' }));
    expect(screen.getByText('Chris Demo')).toBeInTheDocument();
    expect(screen.queryByText('Alex Muster')).not.toBeInTheDocument();
  });

  it('keeps mobile navigation usable while year and detail cards expand and collapse', async () => {
    viewport.mobile = true;
    const user = userEvent.setup();
    const multiple = { years: [{ year: 2026, turnuses: [
      data.years[0].turnuses[0],
      { id: 5, label: 'T3-2026', members: [{ id: 13, name: 'Chris Demo', functional_role: 'teamer', role_label: 'Teamer', team_label: '' }] },
    ] }] };
    render(<Toaster><AdminTeamOverviewPage data={multiple} mutate={vi.fn()} /></Toaster>);

    expect(screen.getByRole('button', { name: '2026 schließen' })).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: '2026 schließen' }));
    expect(screen.getByRole('button', { name: '2026 öffnen' })).toHaveAttribute('aria-expanded', 'false');
    await user.click(screen.getByRole('button', { name: '2026 öffnen' }));
    await user.click(screen.getByRole('button', { name: 'T3-2026 auswählen' }));
    await user.click(screen.getByRole('button', { name: 'T3-2026 öffnen' }));
    expect(screen.getByText('Chris Demo')).toBeInTheDocument();
    expect(screen.queryByText('Alex Muster')).not.toBeInTheDocument();
  });

  it('synchronizes controlled year expansion only when crossing the mobile breakpoint', async () => {
    const user = userEvent.setup();
    const multiple = { years: [data.years[0], { year: 2025, turnuses: [{ id: 3, label: 'T1-2025', members: [] }] }], people: [] };
    const view = render(<Toaster><AdminTeamOverviewPage data={multiple} mutate={vi.fn()} /></Toaster>);
    await user.click(screen.getByRole('button', { name: '2025 schließen' }));
    expect(screen.getByRole('button', { name: '2025 öffnen' })).toBeInTheDocument();

    viewport.mobile = true;
    view.rerender(<Toaster><AdminTeamOverviewPage data={multiple} mutate={vi.fn()} /></Toaster>);
    expect(screen.getByRole('button', { name: '2026 schließen' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '2025 öffnen' })).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: '2026 schließen' }));
    view.rerender(<Toaster><AdminTeamOverviewPage data={multiple} mutate={vi.fn()} /></Toaster>);
    expect(screen.getByRole('button', { name: '2026 öffnen' })).toBeInTheDocument();

    viewport.mobile = false;
    view.rerender(<Toaster><AdminTeamOverviewPage data={multiple} mutate={vi.fn()} /></Toaster>);
    expect(screen.getByRole('button', { name: '2026 schließen' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '2025 schließen' })).toBeInTheDocument();
  });

  it('reconciles refreshed membership data while preserving local navigation state', async () => {
    const user = userEvent.setup();
    const mutate = vi.fn().mockResolvedValue({ functional_role: 'leitung' });
    const multiple = {
      ...data,
      years: [{ year: 2026, turnuses: [
        data.years[0].turnuses[0],
        { id: 5, label: 'T3-2026', members: [{ id: 13, name: 'Chris Demo', functional_role: 'teamer', role_label: 'Teamer', team_label: '' }], request_summary: { pending: 0 }, pending_requests: [] },
      ] }, { year: 2025, turnuses: [{ id: 3, label: 'T1-2025', members: [], request_summary: { pending: 0 }, pending_requests: [] }] }],
    };
    const view = render(<Toaster><AdminTeamOverviewPage data={multiple} mutate={mutate} /></Toaster>);
    await user.click(screen.getByRole('button', { name: 'T3-2026 auswählen' }));
    await user.click(screen.getByRole('button', { name: '2025 schließen' }));
    await user.click(screen.getByRole('button', { name: 'Chris Demo bearbeiten: als Leitung einsetzen' }));

    // Parent rerenders with its still-stale route data before App's mutation
    // refresh completes. That must not undo the local mutation result.
    view.rerender(<Toaster><AdminTeamOverviewPage data={{ ...multiple }} mutate={mutate} /></Toaster>);
    expect(screen.getByRole('button', { name: 'Chris Demo bearbeiten: Leitung entfernen' })).toBeInTheDocument();

    const refreshed = {
      ...multiple,
      years: multiple.years.map(year => ({
        ...year,
        turnuses: year.turnuses.map(turnus => turnus.id === 5 ? {
          ...turnus,
          members: [
            { ...turnus.members[0], functional_role: 'leitung', role_label: 'Leitung' },
            { id: 14, name: 'Neue Person', functional_role: 'teamer', role_label: 'Teamer', team_label: 'Logistik' },
          ],
          request_summary: { pending: 1 },
          pending_requests: [{ id: 22, name: 'Neue Anfrage' }],
        } : turnus),
      })),
      people: [...multiple.people, { id: 31, name: 'Neue Suche', relationships: [], turnus_ids: [], available: true }],
    };
    view.rerender(<Toaster><AdminTeamOverviewPage data={refreshed} mutate={mutate} /></Toaster>);

    expect(screen.getByRole('button', { name: 'T3-2026 auswählen' })).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByRole('button', { name: '2025 öffnen' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Chris Demo bearbeiten: Leitung entfernen' })).toBeInTheDocument();
    expect(screen.getByText('Neue Person')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Offene Anfragen (1)' })).toBeInTheDocument();
    expect(screen.getByText('Neue Anfrage')).toBeInTheDocument();
    await user.type(screen.getByRole('textbox', { name: 'Turnusse und Personen suchen' }), 'Neue Suche');
    expect(screen.getByText('Neue Suche')).toBeInTheDocument();
  });

  it('finds registered users without memberships and communicates availability', async () => {
    const user = userEvent.setup();
    render(<Toaster><AdminTeamOverviewPage data={data} mutate={vi.fn()} /></Toaster>);
    await user.type(screen.getByRole('textbox', { name: 'Turnusse und Personen suchen' }), 'Chris');
    expect(screen.getByText('Chris Frei')).toBeInTheDocument();
    expect(screen.getByText('Keine Teamzugehörigkeiten · verfügbar')).toBeInTheDocument();
  });

  it('adds a searched person as Leitung to the selected Turnus with a person-specific action', async () => {
    const user = userEvent.setup();
    const mutate = vi.fn().mockResolvedValue({ membership_id: 31, role_label: 'Leitung', team_label: '' });
    render(<Toaster><AdminTeamOverviewPage data={{ ...data, people: [{ ...data.people[0], turnus_ids: [] }] }} mutate={mutate} /></Toaster>);
    await user.type(screen.getByRole('textbox', { name: 'Turnusse und Personen suchen' }), 'Chris');
    await user.click(screen.getByRole('button', { name: 'Chris Frei als Leitung zu T2-2026 hinzufügen' }));
    expect(mutate).toHaveBeenCalledWith('/api/admin/turnusse/4/leitung/', { user_id: 30 });
    expect(await screen.findByText('Leitung')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Chris Frei als Leitung zu T2-2026 hinzufügen' })).not.toBeInTheDocument();
  });

  it('lets Leitung add, relabel, and remove Teamers through accessible actions', async () => {
    const user = userEvent.setup();
    const mutate = vi.fn()
      .mockResolvedValueOnce({ membership_id: 31, role_label: 'Teamer', team_label: '' })
      .mockResolvedValueOnce({ membership_id: 11, team_label: 'Material' })
      .mockResolvedValueOnce({ membership_id: 11, removed: true });
    const leitungData = { ...data, can_manage_leitung: false, can_manage_memberships: true, people: [{ ...data.people[0], turnus_ids: [] }] };
    render(<Toaster><AdminTeamOverviewPage data={leitungData} mutate={mutate} /></Toaster>);
    expect(screen.queryByRole('button', { name: 'Bea Beispiel bearbeiten' })).not.toBeInTheDocument();
    await user.type(screen.getByRole('textbox', { name: 'Turnusse und Personen suchen' }), 'Chris');
    await user.click(screen.getByRole('button', { name: 'Chris Frei als Teamer zu T2-2026 hinzufügen' }));
    expect(mutate).toHaveBeenCalledWith('/api/turnusse/4/memberships/', { user_id: 30 });
    await user.clear(screen.getByRole('textbox', { name: 'Turnusse und Personen suchen' }));
    await user.click(screen.getByRole('button', { name: 'Alex Muster bearbeiten' }));
    const label = screen.getByRole('textbox', { name: 'Bezeichnung für Alex Muster' });
    await user.clear(label);
    await user.type(label, 'Material');
    await user.click(screen.getByRole('button', { name: 'Speichern' }));
    expect(mutate).toHaveBeenCalledWith('/api/memberships/11/label/', { team_label: 'Material' });
    await user.click(screen.getByRole('button', { name: 'Alex Muster bearbeiten' }));
    await user.click(screen.getByRole('button', { name: 'Alex Muster entfernen' }));
    expect(mutate).toHaveBeenCalledWith('/api/memberships/11/remove/', {});
    expect(screen.queryByText('Alex Muster')).not.toBeInTheDocument();
  });

  it('keeps the selected assignment target visible when search matches a person and another Turnus', async () => {
    const user = userEvent.setup();
    const mutate = vi.fn().mockResolvedValue({ membership_id: 32, role_label: 'Leitung', team_label: '' });
    const multiple = {
      years: [{ year: 2026, turnuses: [
        data.years[0].turnuses[0],
        { id: 5, label: 'T3-2026', members: [{ id: 13, name: 'Chris Frei', functional_role: 'teamer', role_label: 'Teamer', team_label: '' }] },
      ] }],
      people: [{ id: 30, name: 'Chris Frei', relationships: ['T3-2026'], turnus_ids: [5] }],
    };
    render(<Toaster><AdminTeamOverviewPage data={multiple} mutate={mutate} /></Toaster>);

    await user.type(screen.getByRole('textbox', { name: 'Turnusse und Personen suchen' }), 'Chris');

    expect(screen.getByRole('heading', { name: 'T2-2026' })).toBeInTheDocument();
    const add = screen.getByRole('button', { name: 'Chris Frei als Leitung zu T2-2026 hinzufügen' });
    expect(add).toHaveTextContent('Chris Frei als Leitung zu T2-2026 hinzufügen');
    await user.click(add);
    expect(mutate).toHaveBeenCalledWith('/api/admin/turnusse/4/leitung/', { user_id: 30 });
  });
});
