import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { parseRoute, renderRoute, resolveRouteTitle, routeDefinitions, routeHeaderAction } from './routes';

describe('route inventory', () => {
  afterEach(cleanup);

  it.each([
    ['/', 'dashboard', 'dashboard', 'dashboard'],
    ['/dashboard/', 'dashboard', 'dashboard', 'dashboard'],
    ['/gut-zu-wissen/', 'good-to-know', 'dashboard', 'gut-zu-wissen'],
    ['/dokumentation/', 'documentation', 'documentation', 'documentation'],
    ['/audit/', 'audit', 'audit', 'audit-events'],
    ['/login', 'login', 'auth', null],
    ['/register', 'register', 'auth', null],
    ['/profil', 'profile', 'profiles', 'profile'],
    ['/profil/bearbeiten', 'profile-edit', 'profiles', 'profile'],
    ['/profil/5', 'profile-edit', 'profiles', 'profile'],
    ['/upload', 'turnus-upload', 'maintenance', 'turnus-list'],
    ['/upload_excel/9', 'turnus-upload', 'maintenance', 'turnus-upload'],
    ['/settings/', 'admin-settings', 'maintenance', 'admin-settings'],
    ['/teams/', 'team-management', 'memberships', 'team-management'],
    ['/admin/teams/', 'admin-team-overview', 'memberships', 'admin-team-overview'],
    ['/all_kids', 'kids', 'kids', 'kids-directory'],
    ['/zugabreise', 'train-departure', 'attendance', 'train-departure'],
    ['/zuganreise', 'train-arrival', 'attendance', 'train-arrival'],
    ['/kid_details/21', 'kid', 'kids', 'kid-detail'],
    ['/check_in/21', 'check-in', 'attendance', 'check-in'],
    ['/check_out/21', 'check-out', 'attendance', 'check-out'],
    ['/serienbrief', 'serial-letter', 'reports', 'serial-letter'],
    ['/murdergame', 'murder', 'reports', 'murder-game'],
    ['/schwerpunkt/create', 'focus-create', 'focuses', 'focus-create'],
    ['/schwerpunkt/3/update', 'focus-update', 'focuses', 'focus-update'],
    ['/schwerpunkt/3', 'focus-detail', 'focuses', 'focus-detail'],
    ['/swpmeals/3', 'focus-meals', 'focuses', 'focus-meals'],
    ['/auslagerorte-list', 'places', 'places', 'places-list'],
    ['/auslagerorte/create', 'place-create', 'places', 'place-create'],
    ['/auslagerorte/4/update', 'place-update', 'places', 'place-update'],
    ['/auslagerorte/4/upload-image/', 'place-images', 'places', 'place-images'],
    ['/auslagerorte/4', 'place-detail', 'places', 'places-list'],
    ['/kitchen', 'kitchen', 'kitchen', 'kitchen'],
    ['/swp-einteilung-w2', 'allocation', 'allocation', 'allocation'],
    ['/kindergesamtzahl', 'kid-count', 'reports', 'kid-count'],
    ['/budo_familien', 'families', 'reports', 'families'],
    ['/kindergeburtstage/', 'birthdays', 'reports', 'birthdays'],
  ])('maps %s to the %s page in %s with contract %s', (path, page, domain, readContractKey) => {
    expect(parseRoute(path)).toMatchObject({ page, domain, readContractKey });
  });

  it.each([
    '/login',
    '/register',
    '/swp-dashboard',
    '/upload_spezialfamilien',
    '/spezial_familien',
    '/does-not-exist',
  ])(
    'does not declare protected route data for %s',
    path => expect(parseRoute(path).readContractKey).toBeNull(),
  );

  it('gives every declared route one domain-owned renderer and an explicit contract key', () => {
    for (const route of routeDefinitions) {
      expect(route.domain).toBeTruthy();
      expect(route).toHaveProperty('readContractKey');
      expect(route).not.toHaveProperty('focusedReadContract');
      if (route.domain === 'auth') expect(route.readContractKey).toBeNull();
      else expect(route.readContractKey).toBeTypeOf('string');
      expect(route.render).toBeTypeOf('function');
    }
  });

  it('propagates entity identifiers and the allocation week for future loaders', () => {
    expect(parseRoute('/kid_details/21')).toMatchObject({ id: '21' });
    expect(parseRoute('/swp-einteilung-w2')).toMatchObject({ week: '2' });
  });

  it.each([
    ['/swp-einteilung-w1', 'SWP 1'],
    ['/swp-einteilung-w2', 'SWP 2'],
  ])('uses the short allocation title on %s', (path, title) => {
    expect(resolveRouteTitle(parseRoute(path), { authenticated: true })).toBe(title);
  });

  it('names Team management consistently in the page title', () => {
    expect(resolveRouteTitle(parseRoute('/teams/'), { authenticated: true })).toBe('Team & Turnus');
    expect(resolveRouteTitle(parseRoute('/admin/teams/'), { authenticated: true })).toBe('Team & Turnus');
  });

  it('keeps dynamic titles owned by their route domains', () => {
    const data = {
      authenticated: true,
      kids: [{ id: 21, full_name: 'Ada Kind' }],
      focuses: [{ id: 3, name: 'Wald SWP' }],
      places: [{ id: 4, name: 'Berghütte' }],
      profile: { rufname: 'Mein Profil' },
      team: [{ id: 5, rufname: 'Grace Teamer' }],
    };

    expect(resolveRouteTitle(parseRoute('/kid_details/21'), data)).toBe('Ada Kind');
    expect(resolveRouteTitle(parseRoute('/schwerpunkt/3'), data)).toBe('Wald SWP');
    expect(resolveRouteTitle(parseRoute('/auslagerorte/4'), data)).toBe('Berghütte');
    expect(resolveRouteTitle(parseRoute('/profil'), data)).toBe('Mein Profil');
    expect(resolveRouteTitle(parseRoute('/profil/bearbeiten'), data)).toBe('Profil bearbeiten');
    expect(resolveRouteTitle(parseRoute('/profil/5'), data)).toBe('Mein Profil');
  });

  it.each([
    ['/profil', 'link', 'Profil bearbeiten', 'href', '/profil/bearbeiten/'],
    ['/auslagerorte-list', 'link', 'Ort hinzufügen', 'href', '/auslagerorte/create'],
    ['/kindergeburtstage', 'button', 'Geburtstage aktualisieren', 'formAction', '/update-birthdays-from-sv/'],
  ])('keeps the header action for %s', (path, role, label, attribute, target) => {
    render(routeHeaderAction(parseRoute(path), { csrf_token: 'token' }));
    const action = screen.getByRole(role, { name: label });
    expect(attribute === 'formAction' ? action.form : action).toHaveAttribute(attribute === 'formAction' ? 'action' : attribute, target);
  });

  it.each([
    ['/profil', 'Profil bearbeiten'],
    ['/auslagerorte-list', 'Ort hinzufügen'],
  ])('marks the create action on %s for compact mobile placement', (path, label) => {
    render(routeHeaderAction(parseRoute(path), {}));

    const action = screen.getByRole('link', { name: label });
    expect(action).toHaveClass('mobile-icon-action');
    expect(action.querySelector('.mobile-action-label')).toHaveAttribute('aria-hidden', 'true');
  });

  it.each([
    ['1', 'w1'],
    ['2', 'w2'],
  ])('offers create, print, and visibility actions for allocation week %s', (week, origin) => {
    render(routeHeaderAction(
      parseRoute(`/swp-einteilung-w${week}`),
      {},
      { pageState: {} },
    ));

    const createAction = screen.getByRole('link', { name: 'SWP hinzufügen' });
    expect(createAction).toHaveAttribute('href', `/schwerpunkt/create?from=${origin}`);
    expect(createAction).toHaveClass('mobile-icon-action');
    expect(createAction.querySelector('.mobile-action-label')).toHaveAttribute('aria-hidden', 'true');
    const print = vi.spyOn(window, 'print').mockImplementation(() => {});
    fireEvent.click(screen.getByRole('button', { name: 'Drucken' }));
    expect(print).toHaveBeenCalledOnce();
    print.mockRestore();
    expect(screen.getByRole('button', { name: 'Kinder ausblenden' })).toBeInTheDocument();
  });

  it.each([
    ['/profil', 'link', 'Profil bearbeiten'],
    ['/auslagerorte-list', 'link', 'Ort hinzufügen'],
    ['/kindergeburtstage', 'button', 'Geburtstage aktualisieren'],
    ['/kitchen', 'button', 'Drucken'],
    ['/murdergame', 'button', 'Drucken'],
    ['/swp-einteilung-w1', 'button', 'Drucken'],
    ['/swp-einteilung-w1', 'button', 'Kinder ausblenden'],
    ['/happy-cleaning', 'button', 'Happy Cleaning hinzufügen'],
    ['/happy-cleaning/print', 'button', 'Drucken'],
    ['/dokumentation', 'button', 'Dokumentation drucken'],
  ])('renders the header action on %s as a labeled icon affordance', (path, role, name) => {
    render(routeHeaderAction(
      parseRoute(path),
      { csrf_token: 'token' },
      { mutate: () => Promise.resolve(), pageState: {} },
    ));

    const action = screen.getByRole(role, { name });
    expect(action.querySelector('svg')).toHaveAttribute('aria-hidden', 'true');
  });

  it('keeps standalone and not-found layout behavior declared in routing', () => {
    expect(parseRoute('/serienbrief').standalone).toBe(true);
    expect(parseRoute('/murdergame').standalone).toBeFalsy();
    expect(parseRoute('/kindergesamtzahl').standalone).toBe(true);

    render(renderRoute(parseRoute('/does-not-exist'), { data: {} }));
    expect(screen.getByRole('heading', { name: 'Seite nicht gefunden' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Zum Dashboard' })).toHaveAttribute('href', '/dashboard/');
  });
});
