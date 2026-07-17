import { describe, expect, it, vi } from 'vitest';

import {
  loadRouteData,
  routeDataRequest,
} from './dataLoader';
import { parseRoute } from './routes';

describe('route data loading', () => {
  it('selects focused data with the parsed identifier and week', () => {
    expect(routeDataRequest(parseRoute('/kid_details/21'))).toEqual({
      contractKey: 'kid-detail',
      params: { id: '21' },
      url: '/api/route-data/kid-detail/?id=21',
    });
    expect(routeDataRequest(parseRoute('/swp-einteilung-w2'))).toEqual({
      contractKey: 'allocation',
      params: { week: '2' },
      url: '/api/route-data/allocation/?week=2',
    });
  });

  it('never selects protected route data for public or unknown routes', () => {
    expect(routeDataRequest(parseRoute('/login'))).toBeNull();
    expect(routeDataRequest(parseRoute('/register'))).toBeNull();
    expect(routeDataRequest(parseRoute('/does-not-exist'))).toBeNull();
  });

  it('has no legacy fallback when a route declares a read contract', () => {
    expect(routeDataRequest({
      readContractKey: 'kid-detail',
      id: 21,
    })).toEqual({
      contractKey: 'kid-detail',
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

  it.each([401, 403])(
    'reports route authentication expiry structurally for HTTP %s',
    async status => {
      const expired = await loadRouteData(
        parseRoute('/kid_details/21'),
        vi.fn().mockResolvedValue({
          ok: false,
          status,
        }),
      );

      expect(expired).toEqual({
        authenticationRequired: true,
        notFound: false,
        data: null,
      });
    },
  );

  it('retains the legacy authenticated-false fallback', async () => {
    const expired = await loadRouteData(
      parseRoute('/kid_details/21'),
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: vi.fn().mockResolvedValue({ authenticated: false }),
      }),
    );

    expect(expired).toEqual({
      authenticationRequired: true,
      notFound: false,
      data: null,
    });
  });
});
