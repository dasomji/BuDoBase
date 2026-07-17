import { cleanup, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';

import { parseRoute, renderRoute, resolveRouteTitle, routeDefinitions, routeHeaderAction } from './routes';

describe('route inventory', () => {
  afterEach(cleanup);

  it.each([
    ['/', 'dashboard', 'dashboard', 'dashboard'],
    ['/dashboard/', 'dashboard', 'dashboard', 'dashboard'],
    ['/login', 'login', 'auth', null],
    ['/register', 'register', 'auth', null],
    ['/profil', 'profile', 'people', 'profile'],
    ['/upload', 'turnus-upload', 'maintenance', 'turnus-list'],
    ['/upload_excel/9', 'turnus-upload', 'maintenance', 'turnus-upload'],
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
    ['/swp-dashboard', 'focus-dashboard', 'focuses', 'focus-dashboard'],
    ['/auslagerorte-list', 'places', 'places', 'places-list'],
    ['/auslagerorte/create', 'place-create', 'places', 'place-create'],
    ['/auslagerorte/4/update', 'place-update', 'places', 'place-update'],
    ['/auslagerorte/4/upload-image/', 'place-images', 'places', 'place-images'],
    ['/auslagerorte/4', 'place-detail', 'places', 'place-detail'],
    ['/kitchen', 'kitchen', 'kitchen', 'kitchen'],
    ['/swp-einteilung-w2', 'allocation', 'allocation', 'allocation'],
    ['/kindergesamtzahl', 'kid-count', 'reports', 'kid-count'],
    ['/budo_familien', 'families', 'reports', 'families'],
    ['/upload_spezialfamilien', 'special-upload', 'maintenance', 'special-upload'],
    ['/spezial_familien', 'special-families', 'reports', 'special-families'],
    ['/kindergeburtstage/', 'birthdays', 'reports', 'birthdays'],
    ['/teamer/5', 'teamer', 'people', 'teamer'],
  ])('maps %s to the %s page in %s with contract %s', (path, page, domain, readContractKey) => {
    expect(parseRoute(path)).toMatchObject({ page, domain, readContractKey });
  });

  it.each(['/login', '/register', '/does-not-exist'])(
    'does not declare protected route data for %s',
    path => expect(parseRoute(path).readContractKey).toBeNull(),
  );

  it('gives every declared route one domain-owned renderer and an explicit contract key', () => {
    for (const route of routeDefinitions) {
      expect(route.domain).toBeTruthy();
      expect(route).toHaveProperty('readContractKey');
      expect(route.render).toBeTypeOf('function');
    }
  });

  it('propagates entity identifiers and the allocation week for future loaders', () => {
    expect(parseRoute('/kid_details/21')).toMatchObject({ id: '21' });
    expect(parseRoute('/swp-einteilung-w2')).toMatchObject({ week: '2' });
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
    expect(resolveRouteTitle(parseRoute('/teamer/5'), data)).toBe('Grace Teamer');
  });

  it.each([
    ['/swp-dashboard', 'link', 'SWP hinzufügen', 'href', '/schwerpunkt/create'],
    ['/auslagerorte-list', 'link', 'Ort hinzufügen', 'href', '/auslagerorte/create'],
    ['/kindergeburtstage', 'button', '🔄 Geburtstage aktualisieren', 'formAction', '/update-birthdays-from-sv/'],
  ])('keeps the header action for %s', (path, role, label, attribute, target) => {
    render(routeHeaderAction(parseRoute(path), { csrf_token: 'token' }));
    const action = screen.getByRole(role, { name: label });
    expect(attribute === 'formAction' ? action.form : action).toHaveAttribute(attribute === 'formAction' ? 'action' : attribute, target);
  });

  it('keeps standalone and not-found layout behavior declared in routing', () => {
    expect(parseRoute('/serienbrief').standalone).toBe(true);
    expect(parseRoute('/murdergame').standalone).toBe(true);
    expect(parseRoute('/kindergesamtzahl').standalone).toBe(true);

    render(renderRoute(parseRoute('/does-not-exist'), { data: {} }));
    expect(screen.getByRole('heading', { name: 'Seite nicht gefunden' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Zum Dashboard' })).toHaveAttribute('href', '/dashboard/');
  });
});
