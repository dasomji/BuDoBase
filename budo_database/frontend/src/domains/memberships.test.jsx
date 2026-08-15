import { cleanup, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { Toaster } from '../components/ui/toast';
import { parseRoute, routeHeaderAction } from '../routes';
import { AdminTeamOverviewPage } from './memberships';

const alexProfile = {
  id: 51,
  email: 'alex@example.test',
  rufname: 'Alex',
  phone: '+4312345',
  allergies: 'Nüsse',
  coffee: 'Schwarz',
  food: 'vt',
  food_display: '🧀 Vegetarisch',
  budo_family: 'M',
  turnuses: ['T2-2026', 'T3-2026'],
  focuses: [{ id: 3, name: 'Wald' }],
};

const data = { csrf_token: 'token', years: [{ year: 2026, turnuses: [{
  id: 4,
  label: 'T2-2026',
  start: '2026-07-04',
  end: '2026-07-17',
  excel_uploaded: false,
  members: [
    { id: 11, name: 'Alex Muster', functional_role: 'teamer', role_label: 'Teamer', team_label: 'Küche', profile: alexProfile },
    { id: 12, name: 'Bea Beispiel', functional_role: 'leitung', role_label: 'Leitung', team_label: 'Organisation', profile: { ...alexProfile, id: 52, rufname: 'Bea', email: 'bea@example.test', focuses: [] } },
  ],
  request_summary: { pending: 1 },
  pending_requests: [{ id: 21, name: 'Dana Anfrage', email: 'dana@example.test' }],
}] }], people: [{ id: 30, name: 'Chris Frei', email: 'chris.frei@example.test', relationships: [], available: true }], can_manage_memberships: true };

describe('admin team overview', () => {
  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
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
    expect(await screen.findByRole('heading', { name: '3 Personen' })).toBeInTheDocument();
    expect(screen.queryByTestId('pending-request-panel')).not.toBeInTheDocument();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    expect(screen.getByText('Dana Anfrage')).toBeInTheDocument();
    expect(screen.getAllByText('Teamer', { selector: 'small' })).not.toHaveLength(0);
    expect(screen.queryByRole('button', { name: /Alex Muster bearbeiten/ })).not.toBeInTheDocument();
  });

  it('opens the existing profile card from a member name without edit controls for a Teamer', async () => {
    const user = userEvent.setup();
    const readonly = {
      ...data,
      can_manage_leitung: false,
      can_manage_memberships: false,
      years: [{ ...data.years[0], turnuses: [{
        ...data.years[0].turnuses[0],
        can_manage_memberships: false,
        can_edit_profiles: false,
        request_summary: { pending: 0 },
        pending_requests: [],
      }] }],
    };
    render(<Toaster><AdminTeamOverviewPage data={readonly} mutate={vi.fn()} /></Toaster>);

    expect(screen.queryByRole('button', { name: 'Person hinzufügen' })).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Alex Muster Profil öffnen' }));

    const dialog = screen.getByRole('dialog', { name: 'Profil von Alex Muster' });
    expect(dialog).toHaveTextContent('🧀 Vegetarisch');
    expect(dialog).toHaveTextContent('Nüsse');
    expect(within(dialog).getByRole('link', { name: 'alex@example.test' })).toHaveAttribute('href', 'mailto:alex@example.test');
    expect(dialog).toHaveTextContent('Turnis: T2-2026, T3-2026');
    expect(dialog).toHaveTextContent('Schwerpunkte:');
    expect(dialog).not.toHaveTextContent('Meine Schwerpunkte');
    expect(within(dialog).getByRole('link', { name: 'Wald' })).toHaveAttribute('href', '/schwerpunkt/3/');
    expect(within(dialog).queryByLabelText('Rufname')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Alex Muster bearbeiten' })).not.toBeInTheDocument();
  });

  it('keeps profile viewing read-only and lets Leitung edit every profile field through the pencil flow', async () => {
    const user = userEvent.setup();
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ ok: true, redirect: '/teams/' }),
    });
    vi.stubGlobal('fetch', fetchMock);
    const editable = {
      ...data,
      can_manage_leitung: false,
      can_manage_memberships: true,
      years: [{ ...data.years[0], turnuses: [{
        ...data.years[0].turnuses[0],
        can_manage_memberships: true,
        can_edit_profiles: true,
      }] }],
    };
    render(<Toaster><AdminTeamOverviewPage data={editable} mutate={vi.fn()} /></Toaster>);

    await user.click(screen.getByRole('button', { name: 'Alex Muster Profil öffnen' }));
    const profileDialog = screen.getByRole('dialog', { name: 'Profil von Alex Muster' });
    expect(within(profileDialog).queryByLabelText('Rufname')).not.toBeInTheDocument();
    expect(within(profileDialog).queryByRole('button', { name: 'Speichern' })).not.toBeInTheDocument();
    await user.click(within(profileDialog).getByRole('button', { name: 'Dialog schließen' }));

    await user.click(screen.getByRole('button', { name: 'Alex Muster bearbeiten' }));
    const editDialog = screen.getByRole('dialog', { name: 'Alex Muster bearbeiten' });
    expect(within(editDialog).queryByText('Mitgliedschaft verwalten.')).not.toBeInTheDocument();
    expect(within(editDialog).getByLabelText('Rufname')).toHaveValue('Alex');
    expect(within(editDialog).getByLabelText('E-Mail')).toHaveValue('alex@example.test');
    expect(within(editDialog).getByLabelText('E-Mail')).toHaveAttribute('type', 'email');
    expect(within(editDialog).getByLabelText('E-Mail')).toBeRequired();
    expect(within(editDialog).getByLabelText('Allergien')).toHaveValue('Nüsse');
    expect(within(editDialog).getByLabelText('Kaffee')).toHaveValue('Schwarz');
    expect(within(editDialog).getByLabelText('Essen')).toHaveValue('vt');
    expect(within(editDialog).getByLabelText('BuDo-Familie')).toHaveValue('M');
    expect(within(editDialog).getByLabelText('Telefonnummer')).toHaveValue('+4312345');

    await user.clear(within(editDialog).getByLabelText('Rufname'));
    await user.type(within(editDialog).getByLabelText('Rufname'), 'Alex Neu');
    await user.clear(within(editDialog).getByLabelText('E-Mail'));
    await user.type(within(editDialog).getByLabelText('E-Mail'), 'alex.neu@example.test');
    await user.click(within(editDialog).getByRole('button', { name: 'Speichern' }));

    expect(fetchMock).toHaveBeenCalledOnce();
    const [url, options] = fetchMock.mock.calls[0];
    expect(url).toBe('/api/form-submit/');
    expect(options.body.get('_target')).toBe('/profil/51/');
    expect(options.body.get('rufname')).toBe('Alex Neu');
    expect(options.body.get('email')).toBe('alex.neu@example.test');
    expect(within(editDialog).getByLabelText('Rufname')).toHaveValue('Alex Neu');

    await user.click(within(editDialog).getByRole('button', { name: 'Dialog schließen' }));
    expect(screen.getByRole('button', { name: 'Alex Neu Profil öffnen' })).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Alex Neu Profil öffnen' }));
    expect(within(screen.getByRole('dialog', { name: 'Profil von Alex Neu' })).getByRole('link', {
      name: 'alex.neu@example.test',
    })).toHaveAttribute('href', 'mailto:alex.neu@example.test');
  });

  it('hides the request panel when the selected Turnus has no requests', () => {
    const noRequests = {
      ...data,
      years: [{ ...data.years[0], turnuses: [{
        ...data.years[0].turnuses[0],
        request_summary: { pending: 0 },
        pending_requests: [],
      }] }],
    };
    render(<Toaster><AdminTeamOverviewPage data={noRequests} mutate={vi.fn()} /></Toaster>);

    expect(screen.queryByTestId('pending-request-panel')).not.toBeInTheDocument();
    expect(screen.queryByText('Keine offenen Anfragen.')).not.toBeInTheDocument();
  });

  it('offers Turnus creation from the route header only when authorized', async () => {
    const user = userEvent.setup();
    const setPageState = vi.fn();
    const { unmount } = render(routeHeaderAction(
      parseRoute('/teams/'),
      { can_create_turnus: true },
      { setPageState },
    ));

    await user.click(screen.getByRole('button', { name: 'Turnus hinzufügen' }));
    expect(setPageState.mock.calls[0][0]({ untouched: true })).toEqual({
      untouched: true,
      createTurnusOpen: true,
    });
    unmount();

    render(routeHeaderAction(parseRoute('/teams/'), { can_create_turnus: false }, { setPageState }));
    expect(screen.queryByRole('button', { name: 'Turnus hinzufügen' })).not.toBeInTheDocument();
  });

  it('creates a Turnus from an opaque dialog with a Saturday-only calendar', async () => {
    const user = userEvent.setup();
    const mutate = vi.fn().mockResolvedValue({ id: 9, label: 'T3-2027' });
    const onCreateOpenChange = vi.fn();
    render(
      <Toaster>
        <AdminTeamOverviewPage
          data={data}
          mutate={mutate}
          createOpen
          onCreateOpenChange={onCreateOpenChange}
        />
      </Toaster>,
    );

    const dialog = screen.getByRole('dialog', { name: 'Turnus hinzufügen' });
    expect(dialog).toHaveClass('bg-popover');
    expect(dialog).not.toHaveClass('card');
    expect(within(dialog).getByLabelText('Welcher Turnus?')).toBeInTheDocument();
    expect(within(dialog).getByRole('button', { name: 'Startdatum' })).toBeInTheDocument();
    expect(within(dialog).queryByLabelText(/Excel/i)).not.toBeInTheDocument();

    await user.type(within(dialog).getByLabelText('Welcher Turnus?'), '3');
    await user.click(within(dialog).getByRole('button', { name: 'Startdatum' }));
    const calendar = screen.getByRole('dialog', { name: 'Startdatum auswählen' });
    const dateButtons = within(calendar).getAllByRole('button').filter(button => button.dataset.date);
    expect(dateButtons.length).toBeGreaterThan(0);
    dateButtons.forEach(button => {
      const isSaturday = new Date(`${button.dataset.date}T00:00:00Z`).getUTCDay() === 6;
      expect(button).toHaveProperty('disabled', !isSaturday);
    });
    const saturday = dateButtons.find(button => !button.disabled);
    const selectedDate = saturday.dataset.date;
    await user.click(saturday);
    await user.click(within(dialog).getByRole('button', { name: 'Turnus hinzufügen' }));

    expect(mutate).toHaveBeenCalledWith('/api/turnusse/', {
      turnus_nr: 3,
      turnus_beginn: selectedDate,
    }, true, true, true);
    expect(onCreateOpenChange).toHaveBeenCalledWith(false);
  });

  it('warns about a missing or non-numeric Turnus number and does not save', async () => {
    const user = userEvent.setup();
    const mutate = vi.fn();
    render(
      <Toaster>
        <AdminTeamOverviewPage data={data} mutate={mutate} createOpen />
      </Toaster>,
    );

    const dialog = screen.getByRole('dialog', { name: 'Turnus hinzufügen' });
    const number = within(dialog).getByLabelText('Welcher Turnus?');
    await user.type(number, 'keine Zahl');

    expect(number).toHaveValue('');
    expect(within(dialog).getByText('Nur Zahlen möglich')).toBeInTheDocument();
    await user.click(within(dialog).getByRole('button', { name: 'Turnus hinzufügen' }));

    expect(number).toHaveFocus();
    expect(number).toHaveAttribute('aria-invalid', 'true');
    expect(mutate).not.toHaveBeenCalled();
  });

  it('uploads Excel for the selected Turnus and replaces the option with a green check', async () => {
    const user = userEvent.setup();
    const mutate = vi.fn().mockResolvedValue({ excel_uploaded: true });
    render(<Toaster><AdminTeamOverviewPage data={data} mutate={mutate} /></Toaster>);

    await user.click(screen.getByRole('button', { name: 'Upload Excel file' }));
    const file = new File(['workbook'], 'turnus.xlsx', {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    });
    await user.upload(screen.getByLabelText('Excel file'), file);

    expect(mutate).toHaveBeenCalledWith('/api/turnusse/4/excel/', { uploadedFile: file }, false);
    const status = await screen.findByText('Excel uploaded.');
    expect(status).toHaveClass('text-success');
    expect(status.querySelector('svg')).toHaveAttribute('aria-hidden', 'true');
    expect(screen.queryByRole('button', { name: 'Upload Excel file' })).not.toBeInTheDocument();
  });

  it('shows only the successful Excel state when a workbook already exists', () => {
    const uploaded = {
      ...data,
      years: [{ ...data.years[0], turnuses: [{
        ...data.years[0].turnuses[0],
        excel_uploaded: true,
      }] }],
    };
    render(<Toaster><AdminTeamOverviewPage data={uploaded} mutate={vi.fn()} /></Toaster>);

    expect(screen.getByText('Excel uploaded.')).toHaveClass('text-success');
    expect(screen.queryByRole('button', { name: 'Upload Excel file' })).not.toBeInTheDocument();
  });

  it('renders the year, Turnus, and functional roles without membership-specific labels', () => {
    render(<Toaster><AdminTeamOverviewPage data={data} mutate={vi.fn()} /></Toaster>);
    expect(screen.getByRole('heading', { name: '2026' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'T2-2026' })).toBeInTheDocument();
    expect(screen.getByText('Teamer', { selector: 'small' })).toBeInTheDocument();
    expect(screen.getByText('Leitung', { selector: 'small' })).toBeInTheDocument();
    expect(screen.queryByText('Küche')).not.toBeInTheDocument();
    expect(screen.queryByText('Organisation')).not.toBeInTheDocument();
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
    expect(screen.queryByRole('textbox', { name: /Turnusse/ })).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Person hinzufügen' })).toBeInTheDocument();
  });

  it('defaults to an own Turnus and exposes a privacy-safe request flow for another Turnus', async () => {
    const user = userEvent.setup();
    const ownTurnus = {
      ...data.years[0].turnuses[0],
      is_member: true,
      can_view_team: true,
      leads: [{ name: 'Bea Beispiel' }],
      can_manage_memberships: false,
      can_edit_profiles: false,
    };
    const foreignTurnus = {
      id: 5,
      label: 'T3-2026',
      start: '2026-07-18',
      end: '2026-07-31',
      excel_uploaded: false,
      members: [],
      leads: [{ name: 'Chris Leitung' }],
      is_member: false,
      can_view_team: false,
      request_status: null,
      request_summary: { pending: 0 },
      pending_requests: [],
      can_manage_memberships: false,
      can_edit_profiles: false,
    };
    const integrated = {
      ...data,
      can_manage_leitung: false,
      can_manage_memberships: false,
      years: [{ year: 2026, turnuses: [foreignTurnus, ownTurnus] }],
      people: [],
    };
    const mutate = vi.fn().mockResolvedValue({ status: 'pending' });

    render(<Toaster><AdminTeamOverviewPage data={integrated} mutate={mutate} /></Toaster>);

    expect(screen.getByRole('region', { name: 'T2-2026 verwalten' })).toBeInTheDocument();
    expect(screen.getByTestId('member-panel')).toHaveTextContent('Alex Muster');
    await user.click(screen.getByRole('button', { name: 'T3-2026 auswählen' }));

    expect(screen.getByRole('region', { name: 'T3-2026 ansehen' })).toHaveTextContent('Leitung: Chris Leitung');
    expect(screen.queryByTestId('member-panel')).not.toBeInTheDocument();
    expect(screen.queryByText('Alex Muster')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Person hinzufügen' })).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Als Betreuer:in anfragen' }));

    expect(mutate).toHaveBeenCalledWith('/api/turnusse/5/join-requests/', {});
    expect(await screen.findByText('Anfrage ausstehend')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Als Betreuer:in anfragen' })).not.toBeInTheDocument();
  });

  it('opens the admin member editor before changing Leitung through an explicit action', async () => {
    const user = userEvent.setup();
    const mutate = vi.fn().mockResolvedValue({ functional_role: 'leitung' });
    render(<Toaster><AdminTeamOverviewPage data={data} mutate={mutate} /></Toaster>);
    await user.click(screen.getByRole('button', { name: 'Alex Muster bearbeiten' }));
    expect(mutate).not.toHaveBeenCalled();
    const dialog = screen.getByRole('dialog', { name: 'Alex Muster bearbeiten' });
    const roleAction = screen.getByRole('button', { name: 'Alex Muster als Leitung einsetzen' });
    const removeAction = screen.getByRole('button', { name: 'Alex Muster aus dem Turnus entfernen' });
    expect(dialog).toContainElement(roleAction);
    expect(dialog).toContainElement(removeAction);
    expect(roleAction).toHaveTextContent(/^Als Leitung$/);
    expect(removeAction).toHaveTextContent(/^Aus Turnus entfernen$/);
    expect(screen.queryByText(/Bezeichnung/)).not.toBeInTheDocument();
    expect(within(dialog).queryByText('Mitgliedschaft verwalten.')).not.toBeInTheDocument();
    expect(within(dialog).getByLabelText('Rufname')).toHaveValue('Alex');
    expect(within(dialog).getByRole('button', { name: 'Speichern' })).toBeInTheDocument();
    expect(roleAction.compareDocumentPosition(within(dialog).getByLabelText('Rufname')) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
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
    await user.click(screen.getByRole('button', { name: 'Dialog schließen' }));
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
    await user.click(screen.getByRole('button', { name: 'Dialog schließen' }));

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
      people: [...multiple.people, { id: 31, name: 'Neue Suche', email: 'neue@example.test', relationships: [], turnus_ids: [], available: true }],
    };
    view.rerender(<Toaster><AdminTeamOverviewPage data={refreshed} mutate={mutate} /></Toaster>);

    expect(screen.getByRole('button', { name: 'T3-2026 auswählen' })).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByRole('heading', { name: '2025' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Chris Demo bearbeiten' })).toBeInTheDocument();
    expect(screen.getByText('Neue Person')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Offene Anfragen (1)' })).toBeInTheDocument();
    expect(screen.getByText('Neue Anfrage')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Person hinzufügen' }));
    await user.type(screen.getByRole('textbox', { name: 'Person nach Name oder E-Mail-Adresse suchen' }), 'neue@example.test');
    expect(screen.getByText('Neue Suche')).toBeInTheDocument();
  });

  it('opens a Turnus-scoped dialog and finds registered users by name or email', async () => {
    const user = userEvent.setup();
    render(<Toaster><AdminTeamOverviewPage data={data} mutate={vi.fn()} /></Toaster>);
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Person hinzufügen' }));
    const dialog = screen.getByRole('dialog', { name: 'Person zu T2-2026 hinzufügen' });
    const search = screen.getByRole('textbox', { name: 'Person nach Name oder E-Mail-Adresse suchen' });
    expect(dialog).toContainElement(search);
    expect(search).toHaveFocus();
    await user.type(search, 'chris.frei@example.test');
    expect(screen.getByText('Chris Frei')).toBeInTheDocument();
    expect(screen.getByText('chris.frei@example.test')).toBeInTheDocument();
    expect(screen.getByText('Keine Teamzugehörigkeiten · verfügbar')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Dialog schließen' }));
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('adds a searched person as Leitung to the selected Turnus with a person-specific action', async () => {
    const user = userEvent.setup();
    const mutate = vi.fn().mockResolvedValue({ membership_id: 31, role_label: 'Leitung', team_label: '' });
    render(<Toaster><AdminTeamOverviewPage data={{ ...data, people: [{ ...data.people[0], turnus_ids: [] }] }} mutate={mutate} /></Toaster>);
    await user.click(screen.getByRole('button', { name: 'Person hinzufügen' }));
    await user.type(screen.getByRole('textbox', { name: 'Person nach Name oder E-Mail-Adresse suchen' }), 'Chris');
    expect(screen.getByRole('button', { name: 'Chris Frei als Betreuer:in zu T2-2026 hinzufügen' })).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Chris Frei als Leitung zu T2-2026 hinzufügen' }));
    expect(mutate).toHaveBeenCalledWith('/api/admin/turnusse/4/leitung/', { user_id: 30 }, true, true, true);
    expect(await screen.findAllByText('Leitung', { selector: 'small' })).not.toHaveLength(0);
    expect(screen.queryByRole('button', { name: 'Chris Frei als Leitung zu T2-2026 hinzufügen' })).not.toBeInTheDocument();
  });

  it('does not duplicate a person when refreshed route data arrives before the add request resolves', async () => {
    const user = userEvent.setup();
    const addedMember = {
      id: 31,
      user_id: 30,
      name: 'Chris Frei',
      functional_role: 'teamer',
      role_label: 'Teamer',
      team_label: '',
    };
    const refreshed = {
      ...data,
      years: data.years.map(year => ({
        ...year,
        turnuses: year.turnuses.map(turnus => ({
          ...turnus,
          members: [...turnus.members, addedMember],
        })),
      })),
    };
    let view;
    const mutate = vi.fn().mockImplementation(async () => {
      view.rerender(<Toaster><AdminTeamOverviewPage data={refreshed} mutate={mutate} /></Toaster>);
      await new Promise(resolve => setTimeout(resolve, 0));
      return { membership_id: 31, role_label: 'Teamer', team_label: '' };
    });
    view = render(<Toaster><AdminTeamOverviewPage data={data} mutate={mutate} /></Toaster>);

    await user.click(screen.getByRole('button', { name: 'Person hinzufügen' }));
    await user.type(screen.getByRole('textbox', { name: 'Person nach Name oder E-Mail-Adresse suchen' }), 'Chris');
    await user.click(screen.getByRole('button', { name: 'Chris Frei als Betreuer:in zu T2-2026 hinzufügen' }));
    await user.click(screen.getByRole('button', { name: 'Dialog schließen' }));

    expect(within(screen.getByTestId('member-panel')).getAllByText('Chris Frei')).toHaveLength(1);
  });

  it('lets Leitung add and remove Teamers through accessible actions', async () => {
    const user = userEvent.setup();
    const mutate = vi.fn()
      .mockResolvedValueOnce({ membership_id: 31, role_label: 'Teamer', team_label: '' })
      .mockResolvedValueOnce({ membership_id: 11, removed: true });
    const leitungData = { ...data, can_manage_leitung: false, can_manage_memberships: true, people: [{ ...data.people[0], turnus_ids: [] }] };
    render(<Toaster><AdminTeamOverviewPage data={leitungData} mutate={mutate} /></Toaster>);
    expect(screen.getByRole('button', { name: 'Bea Beispiel bearbeiten' })).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Person hinzufügen' }));
    await user.type(screen.getByRole('textbox', { name: 'Person nach Name oder E-Mail-Adresse suchen' }), 'Chris');
    await user.click(screen.getByRole('button', { name: 'Chris Frei als Betreuer:in zu T2-2026 hinzufügen' }));
    expect(mutate).toHaveBeenCalledWith('/api/turnusse/4/memberships/', { user_id: 30 }, true, true, true);
    await user.click(screen.getByRole('button', { name: 'Dialog schließen' }));
    await user.click(screen.getByRole('button', { name: 'Alex Muster bearbeiten' }));
    await user.click(screen.getByRole('button', { name: 'Alex Muster aus dem Turnus entfernen' }));
    expect(mutate).toHaveBeenCalledWith('/api/memberships/11/remove/', {}, true, true, true);
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
    await user.click(screen.getByRole('button', { name: 'Person hinzufügen' }));
    await user.type(screen.getByRole('textbox', { name: 'Person nach Name oder E-Mail-Adresse suchen' }), 'Alex');
    await user.click(screen.getByRole('button', { name: 'Alex Muster als Betreuer:in zu T2-2026 hinzufügen' }));
    expect(mutate).toHaveBeenLastCalledWith('/api/turnusse/4/memberships/', { user_id: 30 }, true, true, true);
    expect(screen.getAllByText('Alex Muster')).not.toHaveLength(0);
  });

  it('keeps the selected Turnus as the assignment target while searching the dialog', async () => {
    const user = userEvent.setup();
    const mutate = vi.fn().mockResolvedValue({ membership_id: 32, role_label: 'Leitung', team_label: '' });
    const multiple = {
      years: [{ year: 2026, turnuses: [
        data.years[0].turnuses[0],
        { id: 5, label: 'T3-2026', members: [{ id: 13, name: 'Chris Frei', functional_role: 'teamer', role_label: 'Teamer', team_label: '' }] },
      ] }],
      people: [{ id: 30, name: 'Chris Frei', email: 'chris@example.test', relationships: ['T3-2026'], turnus_ids: [5] }],
    };
    render(<Toaster><AdminTeamOverviewPage data={multiple} mutate={mutate} /></Toaster>);

    await user.click(screen.getByRole('button', { name: 'Person hinzufügen' }));
    await user.type(screen.getByRole('textbox', { name: 'Person nach Name oder E-Mail-Adresse suchen' }), 'Chris');

    expect(screen.getByRole('dialog', { name: 'Person zu T2-2026 hinzufügen' })).toBeInTheDocument();
    const add = screen.getByRole('button', { name: 'Chris Frei als Leitung zu T2-2026 hinzufügen' });
    await user.click(add);
    expect(mutate).toHaveBeenCalledWith('/api/admin/turnusse/4/leitung/', { user_id: 30 }, true, true, true);
  });
});
