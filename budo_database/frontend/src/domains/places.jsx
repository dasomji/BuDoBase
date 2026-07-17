import { Card, Column, Columns, FieldList, findById, MapCard, NativeForm, RestForm, SearchTable } from '../components';
import { formatGermanDate, NotFoundPage } from './shared';

export function PlacesPage({ data }) {
  const rows = data.places;
  const columns = [
    { key: 'name', label: 'Name', render: row => <a href={`/auslagerorte/${row.id}/`}>{row.name}</a> },
    { key: 'maps_link', label: 'Wo', render: row => row.maps_link ? <a href={row.maps_link}>Google Maps</a> : '---' },
    { key: 'parking_link', label: 'Parkspot', render: row => row.parking_link ? <a href={row.parking_link}>Google Maps</a> : '---' },
    { key: 'actions', label: 'Aktionen', sortable: false, render: row => <><a href={`/auslagerorte/${row.id}/update`}>✏️</a> <a href={`/auslagerorte/${row.id}/`}>👁️</a></> },
  ];
  return <Columns><Column id="left-column" className="normal-column"><SearchTable columns={columns} rows={rows} /></Column><Column id="right-column"><MapCard places={data.places} /></Column></Columns>;
}

export function PlaceDetailPage({ data, id, onSaved }) {
  const place = findById(data.places, id);
  if (!place) return <NotFoundPage />;
  return <><Columns className="auslagerorte-detail"><Column id="left-column"><Card title={place.name}><FieldList items={[["Name", place.name], ["Beschreibung", place.description], ["Koordinaten", place.coordinates], ["Google Maps Link", place.maps_link && <a href={place.maps_link}>Link</a>], ["Google Maps Link Parkspot", place.parking_link && <a href={place.parking_link}>Link</a>], ["Koordinaten Parkspot", place.parking_coordinates], ["Straße", place.street], ["Stadt", place.city], ["Bundesland", place.state], ["Postleitzahl", place.postal_code], ["Land", place.country]]} /><a className="button" href={`/auslagerorte/${place.id}/update`}>Ort bearbeiten</a></Card><Card title="Kommentare"><ul>{place.notes.map(note => <li key={note.id}><strong>{note.author}</strong> am {formatGermanDate(note.date)}: {note.text}</li>)}</ul></Card></Column><Column id="right-column"><Card title="Bilder"><div className="gallery-container">{place.images.map((src, index) => <div className="gallery-item" key={src}><img src={src} alt={`${place.name} ${index + 1}`} /></div>)}</div><a className="button" href={`/auslagerorte/${place.id}/upload-image/`}>Bilder hochladen</a></Card><MapCard places={[place]} /></Column></Columns><div id="interaction-bar"><RestForm target={`/auslagerorte/${place.id}/`} token={data.csrf_token} onSuccess={onSaved} resetOnSuccess><input name="notiz" placeholder="Kommentar..." /><button type="submit">➤</button></RestForm></div></>;
}

export function PlaceFormPage({ data, id }) {
  const place = id ? findById(data.places, id) : null;
  const keys = { name: 'name', strasse: 'street', ort: 'city', bundesland: 'state', postleitzahl: 'postal_code', land: 'country', maps_link: 'maps_link', beschreibung: 'description', maps_link_parkspot: 'parking_link' };
  const fields = [['name', 'Name'], ['strasse', 'Straße'], ['ort', 'Stadt'], ['bundesland', 'Bundesland'], ['postleitzahl', 'Postleitzahl'], ['land', 'Land'], ['maps_link', 'Google Maps Link'], ['beschreibung', 'Beschreibung', 'textarea'], ['maps_link_parkspot', 'Google Maps Link Parkspot']].map(([name, label, type]) => ({ name, label, type, value: place?.[keys[name]] }));
  return <Columns><Column id="single-column"><Card title={`Auslagerort ${place ? 'updaten' : 'erstellen'}`}><NativeForm token={data.csrf_token} action={place ? `/auslagerorte/${place.id}/update` : '/auslagerorte/create'} fields={fields} /></Card></Column></Columns>;
}

export function ImageUploadPage({ data, id }) {
  const place = findById(data.places, id);
  return <Columns><Column id="single-column"><Card title={`Upload Images for ${place?.name || ''}`}><NativeForm token={data.csrf_token} action={`/auslagerorte/${id}/upload-image/`} encType="multipart/form-data" fields={[{ name: 'images', label: 'Select multiple images', type: 'file', multiple: true, required: true, accept: 'image/*' }]} submit="Upload" /></Card></Column></Columns>;
}

const selectedPlaceTitle = (route, data) => findById(data.places, route.id)?.name || route.title;

export const placeRoutes = [
  {
    pattern: /^\/auslagerorte-list$/,
    page: 'places',
    title: 'Auslagerorte',
    domain: 'places',
    readContractKey: 'places-list',
    focusedReadContract: true,
    headerAction: () => <a className="button" href="/auslagerorte/create">Ort hinzufügen</a>,
    render: ({ data }) => <PlacesPage data={data} />,
  },
  {
    pattern: /^\/auslagerorte\/create$/,
    page: 'place-create',
    title: 'Neuer Auslagerort',
    domain: 'places',
    readContractKey: 'place-create',
    focusedReadContract: true,
    render: ({ data }) => <PlaceFormPage data={data} />,
  },
  {
    pattern: /^\/auslagerorte\/(\d+)\/update$/,
    page: 'place-update',
    title: 'Auslagerort bearbeiten',
    domain: 'places',
    readContractKey: 'place-update',
    focusedReadContract: true,
    params: match => ({ id: match[1] }),
    resolveTitle: selectedPlaceTitle,
    render: ({ route, data }) => <PlaceFormPage data={data} id={route.id} />,
  },
  {
    pattern: /^\/auslagerorte\/(\d+)\/upload-image$/,
    page: 'place-images',
    title: 'Bilder hochladen',
    domain: 'places',
    readContractKey: 'place-images',
    focusedReadContract: true,
    params: match => ({ id: match[1] }),
    resolveTitle: selectedPlaceTitle,
    render: ({ route, data }) => <ImageUploadPage data={data} id={route.id} />,
  },
  {
    pattern: /^\/auslagerorte\/(\d+)$/,
    page: 'place-detail',
    title: 'Auslagerort',
    domain: 'places',
    readContractKey: 'place-detail',
    focusedReadContract: true,
    params: match => ({ id: match[1] }),
    resolveTitle: selectedPlaceTitle,
    render: ({ route, data, refresh }) => <PlaceDetailPage data={data} id={route.id} onSaved={refresh} />,
  },
];
