import { useEffect, useMemo, useState } from 'react';
import { findById, Header, Messages, RestForm } from './components';
import {
  AllocationPage,
  AuthPage,
  BirthdaysPage,
  CheckPage,
  DashboardPage,
  FamiliesPage,
  FocusDashboardPage,
  FocusDetailPage,
  FocusFormPage,
  ImageUploadPage,
  KidCountPage,
  KidDetailPage,
  KidsPage,
  KitchenPage,
  MealsPage,
  MurderPage,
  NotFoundPage,
  PlaceDetailPage,
  PlaceFormPage,
  PlacesPage,
  ProfilePage,
  SerialLetterPage,
  SimpleUploadPage,
  TeamerPage,
  TrainPage,
  TurnusUploadPage,
} from './pages';

export function parseRoute(pathname) {
  const path = pathname.replace(/\/+$/, '') || '/';
  const patterns = [
    [/^\/$|^\/dashboard$/, () => ({ page: 'dashboard', title: 'BuDo Dashboard' })],
    [/^\/login$/, () => ({ page: 'login', title: 'Login' })],
    [/^\/register$/, () => ({ page: 'register', title: 'Registrieren' })],
    [/^\/profil$/, () => ({ page: 'profile', title: 'Profil' })],
    [/^\/upload$/, () => ({ page: 'turnus-upload', title: 'Turnis' })],
    [/^\/upload_excel\/(\d+)$/, match => ({ page: 'turnus-upload', id: match[1], title: 'Excel-Datei hochladen' })],
    [/^\/all_kids$/, () => ({ page: 'kids', title: 'Alle Kinder' })],
    [/^\/zugabreise$/, () => ({ page: 'train-departure', title: 'Alle Kinder' })],
    [/^\/zuganreise$/, () => ({ page: 'train-arrival', title: 'Zuganreise' })],
    [/^\/kid_details\/(\d+)$/, match => ({ page: 'kid', id: match[1], title: 'Kind' })],
    [/^\/check_in\/(\d+)$/, match => ({ page: 'check-in', id: match[1], title: 'Check-In' })],
    [/^\/check_out\/(\d+)$/, match => ({ page: 'check-out', id: match[1], title: 'Check-Out' })],
    [/^\/serienbrief$/, () => ({ page: 'serial-letter', title: 'Serienbrief', standalone: true })],
    [/^\/murdergame$/, () => ({ page: 'murder', title: 'Mörderspiel', standalone: true })],
    [/^\/schwerpunkt\/create$/, () => ({ page: 'focus-create', title: 'Neuer SWP' })],
    [/^\/schwerpunkt\/(\d+)\/update$/, match => ({ page: 'focus-update', id: match[1], title: 'Schwerpunkt bearbeiten' })],
    [/^\/schwerpunkt\/(\d+)$/, match => ({ page: 'focus-detail', id: match[1], title: 'Schwerpunkt' })],
    [/^\/swpmeals\/(\d+)$/, match => ({ page: 'focus-meals', id: match[1], title: 'Essen' })],
    [/^\/swp-dashboard$/, () => ({ page: 'focus-dashboard', title: 'Schwerpunkte' })],
    [/^\/auslagerorte-list$/, () => ({ page: 'places', title: 'Auslagerorte' })],
    [/^\/auslagerorte\/create$/, () => ({ page: 'place-create', title: 'Neuer Auslagerort' })],
    [/^\/auslagerorte\/(\d+)\/update$/, match => ({ page: 'place-update', id: match[1], title: 'Auslagerort bearbeiten' })],
    [/^\/auslagerorte\/(\d+)\/upload-image$/, match => ({ page: 'place-images', id: match[1], title: 'Bilder hochladen' })],
    [/^\/auslagerorte\/(\d+)$/, match => ({ page: 'place-detail', id: match[1], title: 'Auslagerort' })],
    [/^\/kitchen$/, () => ({ page: 'kitchen', title: 'Küche' })],
    [/^\/swp-einteilung-w([12])$/, match => ({ page: 'allocation', week: match[1], title: `SWP-Einteilung Woche ${match[1]}` })],
    [/^\/kindergesamtzahl$/, () => ({ page: 'kid-count', title: 'Kindergesamtzahl', standalone: true })],
    [/^\/budo_familien$/, () => ({ page: 'families', title: 'BuDo Familien' })],
    [/^\/upload_spezialfamilien$/, () => ({ page: 'special-upload', title: 'Upload XLSX' })],
    [/^\/spezial_familien$/, () => ({ page: 'special-families', title: 'Spezial Familien' })],
    [/^\/kindergeburtstage$/, () => ({ page: 'birthdays', title: 'Kindergeburtstage' })],
    [/^\/teamer\/(\d+)$/, match => ({ page: 'teamer', id: match[1], title: 'Teamer' })],
  ];
  for (const [pattern, result] of patterns) {
    const match = path.match(pattern);
    if (match) return result(match);
  }
  return { page: 'not-found', title: 'Seite nicht gefunden' };
}

function RoutePage({ route, data, mutate }) {
  switch (route.page) {
    case 'login': return <AuthPage kind="login" data={data} />;
    case 'register': return <AuthPage kind={data.authenticated ? 'registered' : 'register'} data={data} />;
    case 'dashboard': return <DashboardPage data={data} />;
    case 'profile': return <ProfilePage data={data} />;
    case 'turnus-upload': return <TurnusUploadPage data={data} id={route.id} />;
    case 'kids': return <KidsPage data={data} />;
    case 'train-departure': return <TrainPage data={data} departure mutate={mutate} />;
    case 'train-arrival': return <TrainPage data={data} mutate={mutate} />;
    case 'kid': return <KidDetailPage data={data} id={route.id} mutate={mutate} />;
    case 'check-in': return <CheckPage data={data} id={route.id} />;
    case 'check-out': return <CheckPage data={data} id={route.id} checkout />;
    case 'serial-letter': return <SerialLetterPage data={data} />;
    case 'murder': return <MurderPage data={data} />;
    case 'focus-dashboard': return <FocusDashboardPage data={data} />;
    case 'focus-detail': return <FocusDetailPage data={data} id={route.id} />;
    case 'focus-create': return <FocusFormPage data={data} />;
    case 'focus-update': return <FocusFormPage data={data} id={route.id} />;
    case 'focus-meals': return <MealsPage data={data} id={route.id} />;
    case 'places': return <PlacesPage data={data} />;
    case 'place-detail': return <PlaceDetailPage data={data} id={route.id} />;
    case 'place-create': return <PlaceFormPage data={data} />;
    case 'place-update': return <PlaceFormPage data={data} id={route.id} />;
    case 'place-images': return <ImageUploadPage data={data} id={route.id} />;
    case 'kitchen': return <KitchenPage data={data} />;
    case 'allocation': return <AllocationPage data={data} week={route.week} mutate={mutate} />;
    case 'kid-count': return <KidCountPage data={data} />;
    case 'families': return <FamiliesPage data={data} />;
    case 'special-families': return <FamiliesPage data={data} special />;
    case 'special-upload': return <SimpleUploadPage data={data} />;
    case 'birthdays': return <BirthdaysPage data={data} />;
    case 'teamer': return <TeamerPage data={data} id={route.id} />;
    default: return <NotFoundPage />;
  }
}

function dynamicTitle(route, data) {
  if (!data?.authenticated) return route.title;
  if (['kid', 'check-in', 'check-out'].includes(route.page)) return findById(data.kids, route.id)?.full_name || route.title;
  if (['focus-detail', 'focus-update', 'focus-meals'].includes(route.page)) return findById(data.focuses, route.id)?.name || route.title;
  if (['place-detail', 'place-update', 'place-images'].includes(route.page)) return findById(data.places, route.id)?.name || route.title;
  if (route.page === 'profile') return data.profile?.rufname || route.title;
  if (route.page === 'teamer') return findById(data.team, route.id)?.rufname || route.title;
  return route.title;
}

function headerAction(route, data) {
  if (route.page === 'focus-dashboard') return <a className="button" href="/schwerpunkt/create">SWP hinzufügen</a>;
  if (route.page === 'places') return <a className="button" href="/auslagerorte/create">Ort hinzufügen</a>;
  if (route.page === 'kid') {
    const kid = findById(data.kids, route.id);
    return kid && <a className="button" href={`/${kid.present ? 'check_out' : 'check_in'}/${kid.id}`}>{kid.present ? 'Auschecken' : 'Einchecken'}</a>;
  }
  if (route.page === 'birthdays') return <RestForm target="/update-birthdays-from-sv/" token={data.csrf_token}><button className="button" type="submit">🔄 Geburtstage aktualisieren</button></RestForm>;
  return null;
}

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
  const publicPage = ['login', 'register'].includes(route.page);
  if (!data.authenticated && !publicPage) window.location.assign(`/login/?next=${encodeURIComponent(window.location.pathname)}`);
  const title = dynamicTitle(route, data);
  document.title = title;
  return (
    <>
      {!route.standalone && <Header title={title} authenticated={data.authenticated} searchData={data} action={data.authenticated ? headerAction(route, data) : null} />}
      <Messages items={data.messages} />
      <RoutePage route={route} data={data} mutate={mutate} />
    </>
  );
}
