import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { AppSidebar, ApplicationShell } from './app-sidebar';
import { Header, Messages } from './components';
import {
  loadBootstrap,
  loadRouteData,
  routeDataRequest,
} from './dataLoader';
import { notFoundRoute } from './domains/shared';
import { useHappyCleaningSync } from './happyCleaningSync';
import { isPublicRoute, parseRoute, renderRoute, resolveRouteTitle, routeHeaderAction } from './routes';

export { parseRoute } from './routes';

function ErrorState({ title, error }) {
  return <div className="react-error"><div className="card"><h1>{title}</h1><p>{error.message}</p></div></div>;
}

const browserNavigate = path => window.location.assign(path);

export default function App({
  fetchImpl = fetch,
  navigate = browserNavigate,
}) {
  const route = useMemo(() => parseRoute(window.location.pathname), []);
  const [bootstrap, setBootstrap] = useState(null);
  const [bootstrapError, setBootstrapError] = useState(null);
  const [routeState, setRouteState] = useState({
    loading: false,
    data: null,
    error: null,
    notFound: false,
    authenticationRequired: false,
  });
  const routeRequestSequence = useRef(0);
  const request = useMemo(() => routeDataRequest(route), [route]);

  const refreshBootstrap = useCallback(async () => {
    try {
      setBootstrapError(null);
      setBootstrap(await loadBootstrap(fetchImpl));
    } catch (caught) {
      setBootstrapError(caught);
    }
  }, [fetchImpl]);

  const refreshRoute = useCallback(async ({
    propagateError = false,
    preserveData = false,
  } = {}) => {
    const sequence = ++routeRequestSequence.current;
    if (!request) {
      setRouteState({ loading: false, data: null, error: null, notFound: false, authenticationRequired: false });
      return;
    }
    if (!preserveData) {
      setRouteState(current => ({ ...current, loading: true, error: null, notFound: false, authenticationRequired: false }));
    }
    try {
      const result = await loadRouteData(route, fetchImpl);
      if (sequence !== routeRequestSequence.current) return null;
      setRouteState({
        loading: false,
        data: result.data,
        error: null,
        notFound: result.notFound,
        authenticationRequired: result.authenticationRequired,
      });
      return result.data;
    } catch (caught) {
      if (sequence !== routeRequestSequence.current) return null;
      if (preserveData) {
        setRouteState(current => ({ ...current, loading: false }));
      } else {
        setRouteState({ loading: false, data: null, error: caught, notFound: false, authenticationRequired: false });
      }
      if (propagateError) throw caught;
      return null;
    }
  }, [fetchImpl, request, route]);

  useEffect(() => { refreshBootstrap(); }, [refreshBootstrap]);
  useEffect(() => {
    if (bootstrap?.authenticated && request) refreshRoute();
  }, [bootstrap?.authenticated, refreshRoute, request]);
  useEffect(() => {
    if (
      (bootstrap && !bootstrap.authenticated && !isPublicRoute(route))
      || routeState.authenticationRequired
    ) {
      navigate(`/login/?next=${encodeURIComponent(window.location.pathname)}`);
    }
  }, [bootstrap, navigate, route, routeState.authenticationRequired]);

  const realtimeSync = useHappyCleaningSync({
    enabled: Boolean(
      bootstrap?.authenticated
      && route.domain === 'happy-cleaning'
      && route.event_id
      && routeState.data?.event
    ),
    eventId: route.event_id,
    revision: routeState.data?.event?.revision,
    refresh: () => refreshRoute({ propagateError: true, preserveData: true }),
  });

  const data = routeState.data ? {
    ...bootstrap,
    ...routeState.data,
    authenticated: bootstrap?.authenticated,
    csrf_token: bootstrap?.csrf_token,
    messages: bootstrap?.messages || [],
    permissions: bootstrap?.permissions,
    search_index: bootstrap?.search_index,
    turnus: routeState.data.turnus ?? bootstrap?.turnus,
  } : bootstrap;
  const mutate = async (url, payload, json = true) => {
    if (realtimeSync.enabled && !realtimeSync.writesEnabled) {
      const error = new Error('Realtime reconciliation required before writing');
      error.payload = { code: 'sync_unavailable' };
      throw error;
    }
    const options = { method: 'POST', credentials: 'same-origin', headers: { 'X-CSRFToken': data.csrf_token } };
    if (json) {
      options.headers['Content-Type'] = 'application/json';
      options.body = JSON.stringify(payload);
    } else {
      const body = new FormData();
      Object.entries(payload).forEach(([key, value]) => body.append(key, value));
      options.body = body;
    }
    const response = await fetchImpl(url, options);
    if (!response.ok) {
      const error = new Error(`Update failed (${response.status})`);
      try { error.payload = await response.json(); } catch { error.payload = null; }
      throw error;
    }
    let responsePayload = {};
    try { responsePayload = await response.json(); } catch { responsePayload = {}; }
    await refreshRoute();
    return responsePayload;
  };

  if (bootstrapError) return <ErrorState title="Sitzung konnte nicht geladen werden" error={bootstrapError} />;
  if (!bootstrap) return <div className="react-loading">Sitzung wird geladen…</div>;
  if ((!bootstrap.authenticated && !isPublicRoute(route)) || routeState.authenticationRequired) {
    return <div className="react-loading">Weiterleitung zum Login…</div>;
  }
  if (routeState.error) return <ErrorState title="Seitendaten konnten nicht geladen werden" error={routeState.error} />;
  if (routeState.notFound) return renderRoute(notFoundRoute, { data: bootstrap });
  if (bootstrap.authenticated && request && (routeState.loading || !routeState.data)) {
    return <div className="react-loading">Seitendaten werden geladen…</div>;
  }
  const title = resolveRouteTitle(route, data);
  document.title = title;
  const content = (
    <>
      <Messages items={data.messages} />
      {realtimeSync.enabled && (
        realtimeSync.connection !== 'connected' || !realtimeSync.httpAvailable
      ) && (
        <p className="warning realtime-warning" role="status">
          {!realtimeSync.httpAvailable
            ? 'Happy Cleaning ist derzeit nicht erreichbar. Änderungen sind deaktiviert.'
            : 'Realtime-Verbindung unterbrochen. Daten werden abgeglichen…'}
        </p>
      )}
      {renderRoute(route, { data, mutate, refresh: refreshRoute, fetchImpl, realtimeSync })}
    </>
  );
  if (route.standalone) return content;
  return (
    <ApplicationShell
      sidebar={data.authenticated ? <AppSidebar /> : null}
      header={<Header title={title} authenticated={data.authenticated} searchData={data} action={data.authenticated ? routeHeaderAction(route, data) : null} />}
    >
      {content}
    </ApplicationShell>
  );
}
