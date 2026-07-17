import { describe, expect, it, vi } from 'vitest';

import {
  composeRouteData,
  loadRouteData,
  refreshAfterMutation,
  routeDataRequest,
} from './dataLoader';
import { parseRoute } from './routes';

describe('route data loading', () => {
  it('selects legacy compatibility data with the parsed identifier and week', () => {
    expect(routeDataRequest(parseRoute('/kid_details/21'))).toEqual({
      contractKey: 'kid-detail',
      mode: 'legacy',
      params: { id: '21' },
      url: '/api/app-data/?route=kid-detail&id=21',
    });
    expect(routeDataRequest(parseRoute('/swp-einteilung-w2'))).toEqual({
      contractKey: 'allocation',
      mode: 'legacy',
      params: { week: '2' },
      url: '/api/app-data/?route=allocation&week=2',
    });
  });

  it('never selects protected route data for public or unknown routes', () => {
    expect(routeDataRequest(parseRoute('/login'))).toBeNull();
    expect(routeDataRequest(parseRoute('/register'))).toBeNull();
    expect(routeDataRequest(parseRoute('/does-not-exist'))).toBeNull();
  });

  it('can select a focused contract without changing route parsing', () => {
    expect(routeDataRequest({
      ...parseRoute('/kid_details/21'),
      focusedReadContract: true,
    })).toEqual({
      contractKey: 'kid-detail',
      mode: 'focused',
      params: { id: '21' },
      url: '/api/route-data/kid-detail/?id=21',
    });
  });

  it('distinguishes not-found route responses from other failures', async () => {
    const notFound = await loadRouteData(parseRoute('/kid_details/21'), vi.fn().mockResolvedValue({
      ok: false,
      status: 404,
    }));

    expect(notFound).toEqual({ authenticationRequired: false, notFound: true, data: null });
  });

  it('reports route authentication expiry separately', async () => {
    const forbidden = await loadRouteData(
      parseRoute('/kid_details/21'),
      vi.fn().mockResolvedValue({
        ok: false,
        status: 403,
        json: vi.fn().mockResolvedValue({
          detail: 'Authentication credentials were not provided.',
        }),
      }),
    );
    const expiredLegacySession = await loadRouteData(
      parseRoute('/kid_details/21'),
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: vi.fn().mockResolvedValue({ authenticated: false }),
      }),
    );

    expect(forbidden).toEqual({
      authenticationRequired: true,
      notFound: false,
      data: null,
    });
    expect(expiredLegacySession).toEqual(forbidden);
  });

  it('does not treat an authorization denial as an expired session', async () => {
    const request = loadRouteData(
      parseRoute('/kid_details/21'),
      vi.fn().mockResolvedValue({
        ok: false,
        status: 403,
        json: vi.fn().mockResolvedValue({ detail: 'Forbidden.' }),
      }),
    );

    await expect(request).rejects.toThrow('Route data request failed (403)');
  });

  it('composes bootstrap shell/search state with the legacy page view model', () => {
    const bootstrap = {
      authenticated: true,
      csrf_token: 'bootstrap-token',
      messages: [{ text: 'Einmal', tags: 'success' }],
      profile: { id: 1, rufname: 'Shell name' },
      turnus: { id: 2, label: 'T2' },
      permissions: { change_kids: true },
      search_index: { kids: [{ id: 7, full_name: 'Ada Kind', present: true }], focuses: [], places: [] },
    };
    const legacy = {
      csrf_token: 'legacy-token',
      messages: [],
      profile: { id: 1, phone: '+43' },
      turnus: { id: 2, start: '2026-07-01' },
      kids: [{ id: 7, full_name: 'Ada Kind', illness: 'only legacy route data' }],
    };

    expect(composeRouteData(bootstrap, legacy)).toMatchObject({
      csrf_token: 'bootstrap-token',
      messages: [{ text: 'Einmal', tags: 'success' }],
      profile: { id: 1, rufname: 'Shell name', phone: '+43' },
      turnus: { id: 2, label: 'T2', start: '2026-07-01' },
      kids: legacy.kids,
      search_index: bootstrap.search_index,
    });
  });

  it('refreshes route data by default and bootstrap only for declared shell changes', async () => {
    const refreshRoute = vi.fn();
    const refreshBootstrap = vi.fn();

    await refreshAfterMutation({ refreshRoute, refreshBootstrap });
    expect(refreshRoute).toHaveBeenCalledOnce();
    expect(refreshBootstrap).not.toHaveBeenCalled();

    await refreshAfterMutation({ refreshRoute, refreshBootstrap, shellAffecting: true });
    expect(refreshRoute).toHaveBeenCalledTimes(2);
    expect(refreshBootstrap).toHaveBeenCalledOnce();
  });
});
