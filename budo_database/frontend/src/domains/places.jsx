import { useId, useState } from 'react';
import { PlusIcon } from 'lucide-react';

import { Card, Column, Columns, DataTable, FieldList, findById, MapCard, NativeForm, RestForm } from '../components';
import { Button } from '../components/ui/button';
import { Input, Textarea } from '../components/ui/input';
import { formatGermanDate, NotFoundPage } from './shared';

export function PlacesPage({ data }) {
  return <PlacesTablePage data={data} />;
}

const tagChipClass = 'inline-flex min-h-8 items-center rounded-full border border-input px-3 py-1 text-sm font-medium wrap-anywhere';

function TagList({ tags = [], label = 'Tags' }) {
  if (!tags.length) return null;
  return (
    <ul className="m-0 flex list-none flex-wrap gap-1 p-0" aria-label={label}>
      {tags.map(tag => <li className={`${tagChipClass} bg-popover`} key={tag}>{tag}</li>)}
    </ul>
  );
}

function PlacesTablePage({ data }) {
  const availableTags = data.available_tags || [];
  const places = data.places || [];
  const [selectedTags, setSelectedTags] = useState(() => {
    const requested = new Set(new URLSearchParams(window.location.search).getAll('tag'));
    return availableTags.filter(tag => requested.has(tag));
  });

  const setFilters = next => {
    setSelectedTags(next);
    const params = new URLSearchParams(window.location.search);
    params.delete('tag');
    next.forEach(tag => params.append('tag', tag));
    const query = params.toString();
    window.history.replaceState(window.history.state, '', `${window.location.pathname}${query ? `?${query}` : ''}${window.location.hash}`);
  };
  const toggleTag = tag => setFilters(
    selectedTags.includes(tag)
      ? selectedTags.filter(selected => selected !== tag)
      : [...selectedTags, tag],
  );
  const rows = places.filter(place => selectedTags.every(tag => (place.tags || []).includes(tag)));
  const columns = [
    { key: 'name', label: 'Name', render: row => <a href={`/auslagerorte/${row.id}/`}>{row.name}</a> },
    { key: 'tags', label: 'Tags', render: row => <TagList tags={row.tags} label={`Tags für ${row.name}`} />, sortable: false },
    { key: 'maps_link', label: 'Wo', render: row => row.maps_link ? <a href={row.maps_link}>Google Maps</a> : '---' },
    { key: 'parking_link', label: 'Parkspot', render: row => row.parking_link ? <a href={row.parking_link}>Google Maps</a> : '---' },
  ];
  const filters = availableTags.length > 0 && (
    <div className="flex flex-wrap items-center gap-2" role="group" aria-label="Nach Tags filtern">
      {availableTags.map(tag => (
        <Button
          className="h-auto min-h-8 rounded-full px-3 py-1 wrap-anywhere"
          size="sm"
          variant={selectedTags.includes(tag) ? 'default' : 'outline'}
          type="button"
          aria-pressed={selectedTags.includes(tag)}
          onClick={() => toggleTag(tag)}
          key={tag}
        >
          {tag}
        </Button>
      ))}
      {selectedTags.length > 0 && <Button size="xs" variant="ghost" type="button" onClick={() => setFilters([])}>Tagfilter zurücksetzen</Button>}
    </div>
  );
  return <Columns><Column id="left-column"><DataTable beforeFilter={filters} columns={columns} rows={rows} empty={selectedTags.length ? 'Keine Auslagerorte entsprechen den ausgewählten Tags.' : 'Keine Auslagerorte'} /></Column><Column id="right-column"><MapCard places={rows} /></Column></Columns>;
}

function PlaceCommentForm({ place, token, onSaved }) {
  const [photoCount, setPhotoCount] = useState(0);
  const handleSaved = onSaved
    ? async result => {
        await onSaved(result);
        setPhotoCount(0);
      }
    : undefined;
  return (
    <div className="w-full p-2">
      <RestForm className="mx-auto flex w-full max-w-5xl items-center gap-2" target={`/auslagerorte/${place.id}/`} token={token} encType="multipart/form-data" onSuccess={handleSaved} resetOnSuccess>
        <div className="min-w-0 flex-1">
          <p className="relative m-0">
            <Textarea className="max-h-[4lh] min-h-[2lh] resize-none overflow-y-auto pr-10 field-sizing-content" name="notiz" placeholder="Kommentar..." rows="2" aria-label="Kommentar" />
            <label className="absolute top-1/2 right-1 z-1 inline-grid size-8 -translate-y-1/2 place-items-center text-2xl" htmlFor="id_place_comment_images">
              <span className="sr-only">Kommentar-Bilder</span><span aria-hidden="true">+</span>
              {photoCount > 0 && <span className="absolute -right-1 -bottom-1 grid h-4 min-w-4 place-items-center rounded-full bg-[#b42318] px-0.5 text-[0.65rem] leading-none font-bold text-white" aria-hidden="true">{photoCount}</span>}
            </label>
            <input id="id_place_comment_images" className="absolute size-px overflow-hidden [clip-path:inset(50%)]" aria-label="Kommentar-Bilder" name="images" type="file" accept="image/*" multiple onChange={event => setPhotoCount(event.target.files?.length || 0)} />
          </p>
        </div>
        <Button size="icon" type="submit" aria-label="Kommentar senden">➤</Button>
      </RestForm>
    </div>
  );
}

export function PlaceDetailPage({ data, id, onSaved }) {
  const place = findById(data.places, id);
  if (!place) return <NotFoundPage />;
  return (
    <>
      <Columns className="grid grid-cols-1 items-start min-[901px]:grid-cols-[minmax(0,22rem)_minmax(0,1fr)]">
        <Column id="left-column" className="min-w-0">
          <Card
            title={place.name}
            actions={<Button href={`/auslagerorte/${place.id}/update`}>Ort bearbeiten</Button>}
          >
            <div className="mb-3"><TagList tags={place.tags} /></div>
            <FieldList items={[["Name", place.name], ["Beschreibung", place.description], ["Koordinaten", place.coordinates], ["Google Maps Link", place.maps_link && <a href={place.maps_link}>Link</a>], ["Google Maps Link Parkspot", place.parking_link && <a href={place.parking_link}>Link</a>], ["Koordinaten Parkspot", place.parking_coordinates], ["Straße", place.street], ["Stadt", place.city], ["Bundesland", place.state], ["Postleitzahl", place.postal_code], ["Land", place.country]]} />
          </Card>
          <Card title="Kommentare">
            <ul>{place.notes.map(note => <li key={note.id}><strong>{note.author}</strong> am {formatGermanDate(note.date)}: {note.text}{note.photos?.length > 0 && <div className="mt-1 flex gap-1 overflow-x-auto">{note.photos.map(photo => <img className="h-32 w-auto max-w-48 rounded-lg object-cover" src={photo.url} alt={photo.alt} key={photo.id} />)}</div>}</li>)}</ul>
          </Card>
        </Column>
        <Column id="right-column" className="min-w-0">
          <Card
            title="Bilder"
            actions={<Button href={`/auslagerorte/${place.id}/upload-image/`}>Bilder hochladen</Button>}
          >
            <div className="flex flex-wrap gap-2">{place.images.map((src, index) => <div className="min-w-36 flex-auto overflow-hidden rounded-lg" key={src}><img className="h-45 w-full object-cover" src={src} alt={`${place.name} ${index + 1}`} /></div>)}</div>
          </Card>
          <MapCard places={[place]} />
        </Column>
      </Columns>
      <PlaceCommentForm place={place} token={data.csrf_token} onSaved={onSaved} />
    </>
  );
}

function TagInput({ availableTags, initialTags }) {
  const [tags, setTags] = useState(initialTags || []);
  const [draft, setDraft] = useState('');
  const suggestionsId = useId();
  const normalize = value => value.trim().replace(/\s+/g, ' ');
  const addDraft = () => {
    const normalized = normalize(draft);
    if (!normalized) return;
    const existing = availableTags.find(tag => tag.toLocaleLowerCase('de') === normalized.toLocaleLowerCase('de')) || normalized;
    if (!tags.some(tag => tag.toLocaleLowerCase('de') === existing.toLocaleLowerCase('de'))) {
      setTags(current => [...current, existing]);
    }
    setDraft('');
  };
  return (
    <fieldset className="grid gap-2">
      <legend className="font-medium">Tags</legend>
      {tags.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {tags.map(tag => (
            <span className={`${tagChipClass} gap-2 bg-popover`} key={tag}>
              {tag}
              <Button className="-mr-2" size="icon-xs" variant="ghost" type="button" aria-label={`Tag ${tag} entfernen`} onClick={() => setTags(current => current.filter(item => item !== tag))}>×</Button>
              <input type="hidden" name="tags" value={tag} />
            </span>
          ))}
        </div>
      )}
      <div className="flex flex-wrap items-end gap-2">
        <label className="min-w-48 flex-1">Tag hinzufügen
          <Input name="tags" value={draft} list={suggestionsId} onChange={event => setDraft(event.target.value)} onKeyDown={event => {
            if (event.key === 'Enter' || event.key === ',') {
              event.preventDefault();
              addDraft();
            }
          }} />
        </label>
        <datalist id={suggestionsId}>{availableTags.filter(tag => !tags.includes(tag)).map(tag => <option value={tag} key={tag} />)}</datalist>
        <Button size="sm" variant="secondary" type="button" onClick={addDraft}>Hinzufügen</Button>
      </div>
      <p className="m-0 text-sm text-muted-foreground">Mit Enter oder Komma hinzufügen. Neue Tags werden beim Speichern angelegt.</p>
    </fieldset>
  );
}

export function PlaceFormPage({ data, id }) {
  const place = id ? findById(data.places, id) : null;
  const keys = { name: 'name', strasse: 'street', ort: 'city', bundesland: 'state', postleitzahl: 'postal_code', land: 'country', maps_link: 'maps_link', beschreibung: 'description', maps_link_parkspot: 'parking_link' };
  const fields = [['name', 'Name'], ['strasse', 'Straße'], ['ort', 'Stadt'], ['bundesland', 'Bundesland'], ['postleitzahl', 'Postleitzahl'], ['land', 'Land'], ['maps_link', 'Google Maps Link'], ['beschreibung', 'Beschreibung', 'textarea'], ['maps_link_parkspot', 'Google Maps Link Parkspot']].map(([name, label, type]) => ({ name, label, type, value: place?.[keys[name]] }));
  fields.push({ name: 'tags', render: () => <TagInput availableTags={data.available_tags || []} initialTags={place?.tags || []} /> });
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
    headerAction: () => (
      <Button className="mobile-icon-action" size="responsive-icon" href="/auslagerorte/create" aria-label="Ort hinzufügen">
        <span className="desktop-action-label">Ort hinzufügen</span>
        <PlusIcon className="mobile-action-label" aria-hidden="true" />
      </Button>
    ),
    render: ({ data }) => <PlacesPage data={data} />,
  },
  {
    pattern: /^\/auslagerorte\/create$/,
    page: 'place-create',
    title: 'Neuer Auslagerort',
    domain: 'places',
    readContractKey: 'place-create',
    render: ({ data }) => <PlaceFormPage data={data} />,
  },
  {
    pattern: /^\/auslagerorte\/(\d+)\/update$/,
    page: 'place-update',
    title: 'Auslagerort bearbeiten',
    domain: 'places',
    readContractKey: 'place-update',
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
    params: match => ({ id: match[1] }),
    resolveTitle: selectedPlaceTitle,
    render: ({ route, data, refresh }) => <PlaceDetailPage data={data} id={route.id} onSaved={refresh} />,
  },
];
