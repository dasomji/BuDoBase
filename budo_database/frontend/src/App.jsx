import { useEffect, useMemo, useState } from 'react';
import { Header, Messages } from './components';
import { isPublicRoute, parseRoute, renderRoute, resolveRouteTitle, routeHeaderAction } from './routes';

export { parseRoute } from './routes';

export default function App() {
  const route = useMemo(() => parseRoute(window.location.pathname), []);
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const load = async () => {
    try {
      const response = await fetch('/api/app-data/', { credentials: 'same-origin' });
      if (!response.ok) throw new Error(`API request failed (${response.status})`);
      setData(await response.json());
    } catch (caught) {
      setError(caught);
    }
  };
  useEffect(() => { load(); }, []);
  const mutate = async (url, payload, json = true) => {
    const options = { method: 'POST', credentials: 'same-origin', headers: { 'X-CSRFToken': data.csrf_token } };
    if (json) {
      options.headers['Content-Type'] = 'application/json';
      options.body = JSON.stringify(payload);
    } else {
      const body = new FormData();
      Object.entries(payload).forEach(([key, value]) => body.append(key, value));
      options.body = body;
    }
    const response = await fetch(url, options);
    if (!response.ok) throw new Error(`Update failed (${response.status})`);
    await load();
  };

  if (error) return <div className="react-error"><div className="card"><h1>BuDoBase konnte nicht geladen werden</h1><p>{error.message}</p></div></div>;
  if (!data) return <div className="react-loading">BuDoBase lädt…</div>;
  if (!data.authenticated && !isPublicRoute(route)) window.location.assign(`/login/?next=${encodeURIComponent(window.location.pathname)}`);
  const title = resolveRouteTitle(route, data);
  document.title = title;
  return (
    <>
      {!route.standalone && <Header title={title} authenticated={data.authenticated} searchData={data} action={data.authenticated ? routeHeaderAction(route, data) : null} />}
      <Messages items={data.messages} />
      {renderRoute(route, { data, mutate, refresh: load })}
    </>
  );
}
