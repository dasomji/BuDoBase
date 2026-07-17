function routeParams(route) {
  return Object.fromEntries(
    ['id', 'week']
      .filter(key => route[key] !== undefined)
      .map(key => [key, String(route[key])]),
  );
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
  if (response.status === 401) {
    return { authenticationRequired: true, notFound: false, data: null };
  }
  if (response.status === 403) {
    const errorData = await response.json();
    if (errorData.detail === 'Authentication credentials were not provided.') {
      return { authenticationRequired: true, notFound: false, data: null };
    }
    throw new Error(`Route data request failed (${response.status})`);
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

export async function refreshAfterMutation({
  refreshRoute,
  refreshBootstrap,
  shellAffecting = false,
}) {
  await refreshRoute();
  if (shellAffecting) await refreshBootstrap();
}
