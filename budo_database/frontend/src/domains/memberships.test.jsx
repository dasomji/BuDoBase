import { cleanup, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { Toaster } from '../components/ui/toast';
import { AdminTeamOverviewPage } from './memberships';

const data = { years: [{ year: 2026, turnuses: [{
  id: 4,
  label: 'T2-2026',
  start: '2026-07-04',
  end: '2026-07-17',
  members: [
    { id: 11, name: 'Alex Muster', functional_role: 'teamer', role_label: 'Teamer', team_label: 'Küche' },
    { id: 12, name: 'Bea Beispiel', functional_role: 'leitung', role_label: 'Leitung', team_label: 'Organisation' },
  ],
  request_summary: { pending: 1 },
  pending_requests: [{ id: 21, name: 'Dana Anfrage', email: 'dana@example.test' }],
}] }], people: [{ id: 30, name: 'Chris Frei', relationships: [], available: true }], can_manage_memberships: true };

describe('admin team overview', () => {
  afterEach(() => {
    cleanup();
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
    render(<Toaster><AdminTeamOverviewPage data={{ ...data, identity_verification_warning: warning, can_manage_leitung: false, can_manage_memberships: false }} mutate={mutate} /></Toaster>);

    expect(screen.getByRole('alert')).toHaveTextContent(warning);
    await user.click(screen.getByRole('button', { name: 'Dana Anfrage annehmen' }));
    expect(mutate).toHaveBeenCalledWith('/api/join-requests/21/decision/', { decision: 'approve' });
    expect(await screen.findByText('Keine offenen Anfragen.')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: '3 Personen' })).toBeInTheDocument();
    expect(screen.getByText('Dana Anfrage')).toBeInTheDocument();
    expect(screen.getByText('Teamer', { selector: 'small' })).toBeInTheDocument();
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
    expect(screen.getByRole('button', { name: 'Alex Muster bearbeiten' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Bea Beispiel bearbeiten' })).toBeInTheDocument();
  });

  it('renders Variant C as one master-detail surface with distinct request and member panels', () => {
    render(<Toaster><AdminTeamOverviewPage data={data} mutate={vi.fn()} /></Toaster>);

    const composition = screen.getByTestId('team-master-detail');
    expect(composition).toContainElement(screen.getByRole('navigation', { name: 'Turnus auswählen' }));
    expect(composition).toContainElement(screen.getByRole('region', { name: 'T2-2026 verwalten' }));
    expect(screen.getByTestId('pending-request-panel')).toHaveTextContent('Dana Anfrage');
    expect(screen.getByTestId('member-panel')).toHaveTextContent('Alex Muster');
    expect(screen.getByText('04.–17. Juli 2026')).toBeInTheDocument();
    expect(screen.getByText('Leitung: Bea Beispiel')).toBeInTheDocument();
  });

  it('opens the admin member editor before changing Leitung through an explicit action', async () => {
    const user = userEvent.setup();
    const mutate = vi.fn().mockResolvedValue({ functional_role: 'leitung' });
    render(<Toaster><AdminTeamOverviewPage data={data} mutate={mutate} /></Toaster>);
    const search = screen.getByRole('textbox', { name: 'Turnusse und Personen suchen' });
    await user.type(search, 'niemand');
    expect(screen.getByText('Keine Turnusse oder Personen gefunden.')).toBeInTheDocument();
    await user.clear(search);
    await user.click(screen.getByRole('button', { name: 'Alex Muster bearbeiten' }));
    expect(mutate).not.toHaveBeenCalled();
    expect(screen.getByRole('textbox', { name: 'Bezeichnung für Alex Muster' })).toHaveValue('Küche');
    expect(screen.getByRole('button', { name: 'Alex Muster als Leitung einsetzen' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Alex Muster aus dem Turnus entfernen' })).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Alex Muster als Leitung einsetzen' }));
    expect(mutate).toHaveBeenCalledWith('/api/admin/memberships/11/role/', { functional_role: 'leitung' });
    expect(await screen.findByRole('button', { name: 'Alex Muster Leitung entfernen' })).toBeInTheDocument();
  });

  it('shows one selected Turnus detail and keeps it selected after a demotion', async () => {
    const user = userEvent.setup();
    const multiple = { years: [{ year: 2026, turnuses: [
      data.years[0].turnuses[0],
      { id: 5, label: 'T3-2026', members: [{ id: 13, name: 'Chris Demo', functional_role: 'leitung', role_label: 'Leitung', team_label: '' }] },
    ] }] };
    render(<Toaster><AdminTeamOverviewPage data={multiple} mutate={vi.fn().mockResolvedValue({})} /></Toaster>);
    expect(screen.getAllByText('Alex Muster')).not.toHaveLength(0);
    expect(screen.queryByText('Chris Demo')).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'T3-2026 auswählen' }));
    await user.click(screen.getByRole('button', { name: 'Chris Demo bearbeiten' }));
    await user.click(screen.getByRole('button', { name: 'Chris Demo Leitung entfernen' }));
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

  it('keeps every year and Turnus reachable in the non-collapsible mobile selector', async () => {
    const user = userEvent.setup();
    const multiple = { years: [{ year: 2026, turnuses: [
      data.years[0].turnuses[0],
      { id: 5, label: 'T3-2026', members: [{ id: 13, name: 'Chris Demo', functional_role: 'teamer', role_label: 'Teamer', team_label: '' }] },
    ] }] };
    render(<Toaster><AdminTeamOverviewPage data={multiple} mutate={vi.fn()} /></Toaster>);

    expect(screen.getByTestId('team-master-detail')).toBeInTheDocument();
    expect(screen.getByRole('navigation', { name: 'Turnus auswählen' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: '2026' })).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'T3-2026 auswählen' }));
    expect(screen.getByText('Chris Demo')).toBeInTheDocument();
    expect(screen.queryByText('Alex Muster')).not.toBeInTheDocument();
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
    await user.click(screen.getByRole('button', { name: 'Chris Demo bearbeiten' }));
    await user.click(screen.getByRole('button', { name: 'Chris Demo als Leitung einsetzen' }));

    // Parent rerenders with its still-stale route data before App's mutation
    // refresh completes. That must not undo the local mutation result.
    view.rerender(<Toaster><AdminTeamOverviewPage data={{ ...multiple }} mutate={mutate} /></Toaster>);
    expect(screen.getByRole('button', { name: 'Chris Demo bearbeiten' })).toBeInTheDocument();

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
    expect(screen.getByRole('heading', { name: '2025' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Chris Demo bearbeiten' })).toBeInTheDocument();
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
    expect(screen.getByRole('button', { name: 'Chris Frei als Teamer zu T2-2026 hinzufügen' })).toBeInTheDocument();
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
    await user.click(screen.getByRole('button', { name: 'Alex Muster aus dem Turnus entfernen' }));
    expect(mutate).toHaveBeenCalledWith('/api/memberships/11/remove/', {});
    expect(screen.queryByText('Alex Muster')).not.toBeInTheDocument();
  });

  it('makes a removed Teamer immediately available to add again', async () => {
    const user = userEvent.setup();
    const person = { id: 30, name: 'Alex Muster', relationships: ['T2-2026'], turnus_ids: [4], available: false };
    const mutate = vi.fn()
      .mockResolvedValueOnce({ membership_id: 11, removed: true })
      .mockResolvedValueOnce({ membership_id: 41, role_label: 'Teamer', team_label: '' });
    const removableData = { ...data, years: [{ ...data.years[0], turnuses: [{ ...data.years[0].turnuses[0], members: [
      { ...data.years[0].turnuses[0].members[0], user_id: 30 },
      data.years[0].turnuses[0].members[1],
    ] }] }] };
    render(<Toaster><AdminTeamOverviewPage data={{ ...removableData, can_manage_leitung: false, can_manage_memberships: true, people: [person] }} mutate={mutate} /></Toaster>);
    await user.click(screen.getByRole('button', { name: 'Alex Muster bearbeiten' }));
    await user.click(screen.getByRole('button', { name: 'Alex Muster aus dem Turnus entfernen' }));
    await user.type(screen.getByRole('textbox', { name: 'Turnusse und Personen suchen' }), 'Alex');
    await user.click(screen.getByRole('button', { name: 'Alex Muster als Teamer zu T2-2026 hinzufügen' }));
    expect(mutate).toHaveBeenLastCalledWith('/api/turnusse/4/memberships/', { user_id: 30 });
    expect(screen.getAllByText('Alex Muster')).not.toHaveLength(0);
  });

  it('renders label field errors inline and focuses the invalid input without a generic toast', async () => {
    const user = userEvent.setup();
    const mutate = vi.fn().mockRejectedValue({ payload: { team_label: ['Höchstens 255 Zeichen.'] } });
    render(<Toaster><AdminTeamOverviewPage data={{ ...data, can_manage_leitung: false, can_manage_memberships: true }} mutate={mutate} /></Toaster>);
    await user.click(screen.getByRole('button', { name: 'Alex Muster bearbeiten' }));
    const input = screen.getByRole('textbox', { name: 'Bezeichnung für Alex Muster' });
    await user.click(screen.getByRole('button', { name: 'Speichern' }));
    expect(await screen.findByText('Höchstens 255 Zeichen.', { selector: '[role="alert"]' })).toBeInTheDocument();
    expect(input).toHaveAttribute('aria-invalid', 'true');
    expect(input).toHaveAttribute('aria-describedby', 'team-label-11-error');
    expect(input).toHaveFocus();
    expect(screen.queryByText('Die Bezeichnung konnte nicht gespeichert werden.', { selector: '.app-toast-description' })).not.toBeInTheDocument();
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
    await user.click(add);
    expect(mutate).toHaveBeenCalledWith('/api/admin/turnusse/4/leitung/', { user_id: 30 });
  });
});
