function routeParams(route) {
  const params = Object.fromEntries(
    ['id', 'week']
      .filter(key => route[key] !== undefined)
      .map(key => [key, String(route[key])]),
  );
  if (route.includeSearch && typeof window !== 'undefined') {
    for (const [key, value] of new URLSearchParams(window.location.search)) {
      params[key] = value;
    }
  }
  return params;
}

function withQuery(path, params) {
  const query = new URLSearchParams(params).toString();
  return query ? `${path}?${query}` : path;
}

export function routeDataRequest(route) {
  if (!route.readContractKey) return null;

  const params = routeParams(route);
  return {
    contractKey: route.readContractKey,
    params,
    url: withQuery(`/api/route-data/${route.readContractKey}/`, params),
  };
}

async function responseData(response, label) {
  if (!response.ok) throw new Error(`${label} (${response.status})`);
  return response.json();
}

export async function loadBootstrap(fetchImpl = fetch) {
  const response = await fetchImpl('/api/bootstrap/', { credentials: 'same-origin' });
  return responseData(response, 'Bootstrap request failed');
}

export async function loadRouteData(route, fetchImpl = fetch) {
  const request = routeDataRequest(route);
  if (!request) return { authenticationRequired: false, notFound: false, data: null };

  const response = await fetchImpl(request.url, { credentials: 'same-origin' });
  // This endpoint has authentication but no separate authorization layer, and
  // DRF SessionAuthentication reports a missing session as 403 rather than 401.
  if (response.status === 401 || response.status === 403) {
    return { authenticationRequired: true, notFound: false, data: null };
  }
  if (response.status === 404) {
    return { authenticationRequired: false, notFound: true, data: null };
  }
  const data = await responseData(response, 'Route data request failed');
  if (data.authenticated === false) {
    return { authenticationRequired: true, notFound: false, data: null };
  }
  return {
    authenticationRequired: false,
    notFound: false,
    data,
  };
}
