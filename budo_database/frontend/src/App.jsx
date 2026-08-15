import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { AppSidebar, ApplicationShell } from './app-sidebar';
import { Header, Messages } from './components';
import { Toaster, useErrorToast } from './components/ui/toast';
import {
  loadBootstrap,
  loadRouteData,
  routeDataRequest,
} from './dataLoader';
import { notFoundRoute } from './domains/shared';
import { useHappyCleaningSync } from './happyCleaningSync';
import { isPublicRoute, parseRoute, renderRoute, resolveRouteHeaderTitle, resolveRouteTitle, routeHeaderAction } from './routes';

export { parseRoute } from './routes';

const findHappyCleaningOverviewEvent = (data, eventId) => data?.years
  ?.flatMap(group => group.turnuses || [])
  .flatMap(turnus => turnus.events || [])
  .find(event => event.id === eventId);

function ErrorState({ title, error }) {
  return <div className="react-error"><div className="card"><h1>{title}</h1><p>{error.message}</p></div></div>;
}

const browserNavigate = path => window.location.assign(path);

function AppContent({
  fetchImpl = fetch,
  navigate = browserNavigate,
  reload = () => window.location.reload(),
}) {
  const showError = useErrorToast();
  const [route, setRoute] = useState(() => parseRoute(window.location.pathname));
  const [bootstrap, setBootstrap] = useState(null);
  const [bootstrapError, setBootstrapError] = useState(null);
  const [pageState, setPageState] = useState({});
  const [turnusSwitching, setTurnusSwitching] = useState(false);
  const [switchRecoveryRequired, setSwitchRecoveryRequired] = useState(false);
  const [routeState, setRouteState] = useState({
    loading: false,
    data: null,
    error: null,
    notFound: false,
    authenticationRequired: false,
  });
  const routeRequestSequence = useRef(0);
  const turnusSwitchInFlight = useRef(false);
  const request = useMemo(() => routeDataRequest(route), [route]);
  const withoutTurnus = bootstrap?.authenticated === true && bootstrap.turnus === null;
  const isOwnProfileRoute = route.page === 'profile'
    || (route.page === 'profile-edit' && route.id == null);
  const isWithoutTurnusRoute = route.page === 'team-management' || isOwnProfileRoute;
  const navigateRoute = useCallback((path, { replace = false } = {}) => {
    routeRequestSequence.current += 1;
    const target = new URL(path, window.location.origin);
    window.history[replace ? 'replaceState' : 'pushState'](
      window.history.state,
      '',
      `${target.pathname}${target.search}${target.hash}`,
    );
    setRoute(parseRoute(target.pathname));
    setRouteState({
      loading: true,
      data: null,
      error: null,
      notFound: false,
      authenticationRequired: false,
    });
  }, []);

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
    const handlePopState = () => {
      routeRequestSequence.current += 1;
      setRoute(parseRoute(window.location.pathname));
      setRouteState({
        loading: true,
        data: null,
        error: null,
        notFound: false,
        authenticationRequired: false,
      });
    };
    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);
  useEffect(() => {
    if (bootstrap?.authenticated && request && (!withoutTurnus || isWithoutTurnusRoute)) {
      refreshRoute();
    }
  }, [bootstrap?.authenticated, isWithoutTurnusRoute, refreshRoute, request, withoutTurnus]);
  useEffect(() => {
    if (
      (bootstrap && !bootstrap.authenticated && !isPublicRoute(route))
      || routeState.authenticationRequired
    ) {
      navigate(`/login/?next=${encodeURIComponent(window.location.pathname)}`);
      return;
    }
    if (withoutTurnus && !isWithoutTurnusRoute) {
      navigateRoute('/teams/', { replace: true });
    }
  }, [bootstrap, isWithoutTurnusRoute, navigate, navigateRoute, route, routeState.authenticationRequired, withoutTurnus]);

  const realtimeEventId = route.event_id || pageState.happyCleaningEventId;
  const overviewRealtimeEvent = findHappyCleaningOverviewEvent(
    routeState.data,
    realtimeEventId,
  );
  const realtimeSync = useHappyCleaningSync({
    enabled: Boolean(
      bootstrap?.authenticated
      && route.domain === 'happy-cleaning'
      && realtimeEventId
      && (routeState.data?.event || overviewRealtimeEvent)
    ),
    eventId: realtimeEventId,
    revision: routeState.data?.event?.revision ?? overviewRealtimeEvent?.revision,
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
  const mutate = async (
    url,
    payload,
    json = true,
    refreshAfter = true,
    refreshBootstrapAfter = false,
  ) => {
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
    if (refreshAfter) await refreshRoute({ preserveData: true });
    if (refreshBootstrapAfter) await refreshBootstrap();
    return responsePayload;
  };
  const switchTurnus = async turnusId => {
    if (turnusSwitchInFlight.current) return;
    turnusSwitchInFlight.current = true;
    setTurnusSwitching(true);
    let serverContextChanged = false;
    try {
      const response = await fetchImpl('/api/turnus-selection/', {
        method: 'POST',
        credentials: 'same-origin',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': bootstrap.csrf_token,
        },
        body: JSON.stringify({ turnus_id: turnusId }),
      });
      if (!response.ok) throw new Error(`Turnus switch failed (${response.status})`);
      serverContextChanged = true;

      // The server context has changed. Remove every action and datum from the
      // old scope until a complete replacement context has been loaded.
      setSwitchRecoveryRequired(true);

      // Any route request that began under the previous server context is now
      // stale and must never be allowed to publish into the replacement shell.
      const replacementSequence = ++routeRequestSequence.current;

      // Fetch the new shell and route before publishing either. A partial
      // refresh must not combine old scoped data with the newly selected shell.
      const nextBootstrap = await loadBootstrap(fetchImpl);
      const nextRoute = request ? await loadRouteData(route, fetchImpl) : null;
      if (replacementSequence !== routeRequestSequence.current) {
        reload();
        return;
      }
      setBootstrapError(null);
      setBootstrap(nextBootstrap);
      if (nextRoute) {
        setRouteState({
          loading: false,
          data: nextRoute.data,
          error: null,
          notFound: nextRoute.notFound,
          authenticationRequired: nextRoute.authenticationRequired,
        });
      }
      setSwitchRecoveryRequired(false);
    } catch {
      if (serverContextChanged) {
        reload();
        return;
      }
      showError('Der Turnus konnte nicht gewechselt werden. Bitte erneut versuchen.');
    } finally {
      turnusSwitchInFlight.current = false;
      setTurnusSwitching(false);
    }
  };

  if (switchRecoveryRequired) return <div className="react-loading">Turnus wird gewechselt…</div>;

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
      {renderRoute(route, { data, mutate, navigate, navigateRoute, refresh: refreshRoute, fetchImpl, realtimeSync, pageState, setPageState })}
    </>
  );
  if (route.standalone) return content;
  const overviewSidebarEvents = (data.years || [])
    .flatMap(year => year.turnuses || [])
    .filter(turnus => turnus.is_active)
    .flatMap(turnus => turnus.events || []);
  return (
    <ApplicationShell
      sidebar={data.authenticated ? (
        <AppSidebar happyCleaningEvents={
          route.page === 'happy-cleaning-overview'
            ? overviewSidebarEvents
            : data.happy_cleaning_events
        } permissions={data.permissions}
        turnusSelection={data.turnus_selection}
        withoutTurnus={withoutTurnus}
        turnusSwitching={turnusSwitching}
        onTurnusChange={switchTurnus} />
      ) : null}
      header={<Header title={resolveRouteHeaderTitle(route, data, title)} authenticated={data.authenticated} searchData={data} action={data.authenticated ? routeHeaderAction(route, data, { pageState, setPageState, mutate }) : null} />}
    >
      {content}
    </ApplicationShell>
  );
}

export default function App(props) {
  return (
    <Toaster>
      <AppContent {...props} />
    </Toaster>
  );
}
