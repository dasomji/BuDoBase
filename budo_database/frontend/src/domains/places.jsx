import { useEffect, useId, useMemo, useRef, useState } from 'react';
import { ArrowLeftIcon, CarIcon, ChevronLeftIcon, ChevronRightIcon, ExternalLinkIcon, FootprintsIcon, ImagePlusIcon, MapPinIcon, NavigationIcon, PencilIcon, PlusIcon, SearchIcon, XIcon } from 'lucide-react';

import { Card, Column, Columns, findById, NativeForm, RestForm } from '../components';
import { GoogleMap } from '../components/google-map';
import { Button } from '../components/ui/button';
import { Input, Textarea } from '../components/ui/input';
import { useIsMobile } from '../hooks/use-mobile';
import { formatGermanDate, NotFoundPage } from './shared';

const tagChipClass = 'inline-flex min-h-8 items-center rounded-full border border-input px-3 py-1 text-sm font-medium wrap-anywhere';
const formatTravelMinutes = minutes => minutes == null ? '---' : `${minutes} min`;
const directionsUrl = destination => `https://www.google.com/maps/dir/?api=1&destination=${encodeURIComponent(destination)}`;

function TimeBadges({ place }) {
  return <span className="flex flex-wrap gap-2 text-xs text-muted-foreground"><span className="inline-flex items-center gap-1"><CarIcon className="size-3.5" aria-hidden="true" />{formatTravelMinutes(place.driving_minutes)}</span><span className="inline-flex items-center gap-1"><FootprintsIcon className="size-3.5" aria-hidden="true" />{formatTravelMinutes(place.walking_minutes)}</span></span>;
}

function Filters({ filters, row = false }) {
  const chips = <>
    {filters.availableTags.map(tag => <Button className="h-auto min-h-8 shrink-0 rounded-full px-3 py-1" size="sm" variant={filters.tags.includes(tag) ? 'secondary' : 'outline'} type="button" aria-pressed={filters.tags.includes(tag)} onClick={() => filters.toggleTag(tag)} key={tag}>{tag}</Button>)}
    {[30, 60, 90].map(minutes => <Button className="h-auto min-h-8 shrink-0 rounded-full px-3 py-1" size="sm" variant={filters.maxWalk === minutes ? 'secondary' : 'outline'} type="button" aria-pressed={filters.maxWalk === minutes} onClick={() => filters.setMaxWalk(filters.maxWalk === minutes ? null : minutes)} key={minutes}>Höchstens {minutes} Minuten zu Fuß</Button>)}
    {filters.tags.length > 0 && <Button size="xs" variant="ghost" type="button" onClick={() => filters.setTags([])}>Tagfilter zurücksetzen</Button>}
  </>;
  return <div className={row ? 'flex gap-1.5 overflow-x-auto pb-1' : 'flex flex-wrap gap-1.5'} role="group" aria-label="Auslagerorte filtern">{chips}</div>;
}

function Search({ filters }) {
  return <label className="relative block"><span className="sr-only">Auslagerort suchen</span><SearchIcon className="absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" aria-hidden="true" /><Input className="bg-background pl-9" type="search" aria-label="Auslagerort suchen" placeholder="Auslagerort suchen" value={filters.query} onChange={event => filters.setQuery(event.target.value)} /></label>;
}

function PlaceList({ places, selectedPlaceId, onSelect }) {
  return <ul className="m-0 min-h-0 list-none divide-y divide-border overflow-y-auto p-0">{places.map(place => <li key={place.id}><button className={`flex w-full flex-col gap-1 px-1 py-2 text-left hover:bg-muted ${Number(selectedPlaceId) === place.id ? 'bg-surface-subtle' : ''}`} type="button" onClick={() => onSelect(place.id)}><strong className="text-sm">{place.name}{!place.coordinates && <span className="ml-1 text-xs font-normal text-amber-700">(kein Pin)</span>}</strong><TimeBadges place={place} /></button></li>)}{!places.length && <li className="py-3 text-sm text-muted-foreground">Keine Orte für diesen Filter.</li>}</ul>;
}

function Gallery({ place, initialIndex, onClose }) {
  const [index, setIndex] = useState(initialIndex);
  useEffect(() => {
    const keyboard = event => {
      if (event.key === 'Escape') onClose();
      if (event.key === 'ArrowRight') setIndex(current => (current + 1) % place.images.length);
      if (event.key === 'ArrowLeft') setIndex(current => (current - 1 + place.images.length) % place.images.length);
    };
    window.addEventListener('keydown', keyboard);
    return () => window.removeEventListener('keydown', keyboard);
  }, [onClose, place.images.length]);
  return <div className="fixed inset-0 z-50 grid place-items-center bg-black/90 p-4" role="dialog" aria-modal="true" aria-label={`Bilder von ${place.name}`}><Button className="absolute top-4 right-4" size="icon" variant="outline" aria-label="Galerie schließen" onClick={onClose}><XIcon aria-hidden="true" /></Button><Button className="absolute left-4" size="icon" variant="outline" aria-label="Vorheriges Bild" onClick={() => setIndex((index - 1 + place.images.length) % place.images.length)}><ChevronLeftIcon aria-hidden="true" /></Button><img className="max-h-[85svh] max-w-full object-contain" src={place.images[index]} alt={`${place.name} ${index + 1}`} /><Button className="absolute right-4" size="icon" variant="outline" aria-label="Nächstes Bild" onClick={() => setIndex((index + 1) % place.images.length)}><ChevronRightIcon aria-hidden="true" /></Button><p className="absolute bottom-4 text-white">{index + 1} / {place.images.length}</p></div>;
}

function Carousel({ place, onBack, onPeek }) {
  const [index, setIndex] = useState(0);
  const [gallery, setGallery] = useState(false);
  const touchY = useRef(null);
  const images = place.images || [];
  return <div className="relative h-52 shrink-0 bg-muted max-[900px]:h-72" onTouchStart={event => { touchY.current = event.touches[0].clientY; }} onTouchEnd={event => { if (touchY.current !== null && event.changedTouches[0].clientY - touchY.current > 24) onPeek?.(); touchY.current = null; }}>
    {images.length ? <button className="h-full w-full" type="button" aria-label="Galerie öffnen" onClick={() => setGallery(true)}><img className="h-full w-full object-cover" src={images[index]} alt={`${place.name} ${index + 1}`} /></button> : <div className="grid h-full place-items-center text-muted-foreground">Keine Bilder</div>}
    <Button className="absolute top-3 left-3" size="icon" variant="outline" type="button" aria-label="Zurück zur Liste" onClick={onBack}><ArrowLeftIcon aria-hidden="true" /></Button>
    {images.length > 1 && <><Button className="absolute top-1/2 left-2 -translate-y-1/2" size="icon" variant="outline" aria-label="Vorheriges Bild" onClick={() => setIndex((index - 1 + images.length) % images.length)}><ChevronLeftIcon aria-hidden="true" /></Button><Button className="absolute top-1/2 right-2 -translate-y-1/2" size="icon" variant="outline" aria-label="Nächstes Bild" onClick={() => setIndex((index + 1) % images.length)}><ChevronRightIcon aria-hidden="true" /></Button><div className="absolute inset-x-0 bottom-2 flex justify-center gap-1">{images.map((_, dot) => <span className={`size-2 rounded-full ${dot === index ? 'bg-secondary' : 'bg-background/75'}`} key={dot} />)}</div></>}
    {gallery && <Gallery place={place} initialIndex={index} onClose={() => setGallery(false)} />}
  </div>;
}

function InfoRow({ icon, label, action, children }) {
  return <div className="flex items-start gap-3 border-b border-border px-4 py-3"><span className="mt-0.5 text-muted-foreground">{icon}</span><div className="min-w-0 flex-1 text-sm"><p className="m-0 text-xs text-muted-foreground">{label}</p><div>{children}</div></div>{action}</div>;
}

function CommentForm({ place, token, onSaved }) {
  const [photos, setPhotos] = useState([]);
  const saved = async result => { setPhotos([]); await onSaved?.(result); };
  return <RestForm className="mt-3 flex items-center gap-2" target={`/auslagerorte/${place.id}/`} token={token} encType="multipart/form-data" onSuccess={saved} resetOnSuccess><div className="relative flex-1"><Textarea className="min-h-10 bg-background pr-10" rows="1" aria-label="Kommentar" name="notiz" placeholder="Kommentar…" /><label className="absolute top-1/2 right-1 grid size-8 -translate-y-1/2 place-items-center" htmlFor="place-comment-images"><span className="sr-only">Kommentar-Bilder</span><ImagePlusIcon className="size-4" aria-hidden="true" />{photos.length > 0 && <span className="absolute -right-1 -bottom-1 grid size-4 rounded-full bg-destructive text-[10px] text-white">{photos.length}</span>}</label><input id="place-comment-images" className="sr-only" aria-label="Kommentar-Bilder" name="images" type="file" accept="image/*" multiple onChange={event => setPhotos([...event.target.files])} /></div><Button size="icon" type="submit" aria-label="Kommentar senden">➤</Button></RestForm>;
}

function DetailSidebar({ place, token, onBack, onSaved, onPeek }) {
  const address = [place.street, [place.postal_code, place.city].filter(Boolean).join(' '), place.country].filter(Boolean).join(', ');
  return <aside className="absolute inset-y-0 left-0 z-20 flex w-full max-w-100 flex-col overflow-y-auto bg-background shadow-2xl max-[900px]:max-w-none" aria-label={place.name}><Carousel place={place} onBack={onBack} onPeek={onPeek} /><div className="border-b border-border px-4 py-3"><div className="flex items-start justify-between gap-2"><h2 className="m-0 text-lg font-bold">{place.name}</h2><Button size="icon" variant="outline" href={`/auslagerorte/${place.id}/update`} aria-label="Bearbeiten"><PencilIcon aria-hidden="true" /></Button></div><div className="mt-2 flex flex-wrap gap-1">{place.tags.map(tag => <span className="rounded-full bg-muted px-2 py-1 text-xs" key={tag}>{tag}</span>)}</div><div className="mt-2"><TimeBadges place={place} /></div>{!place.coordinates && <p className="mt-2 text-xs text-amber-700">Keine Koordinaten — kein Pin auf der Karte.</p>}</div>
    {place.description && <div className="border-b border-border px-4 py-3 text-sm"><p className="text-xs text-muted-foreground">Beschreibung</p><p>{place.description}</p></div>}
    {address && <InfoRow icon={<MapPinIcon className="size-4" />} label="Adresse" action={<Button size="icon" variant="secondary" target="_blank" rel="noreferrer" href={directionsUrl(address)} aria-label="Route zur Adresse"><NavigationIcon aria-hidden="true" /></Button>}>{address}</InfoRow>}
    {place.coordinates && <InfoRow icon={<MapPinIcon className="size-4" />} label="Koordinaten">{place.coordinates}</InfoRow>}
    {place.contact && <InfoRow icon={<span aria-hidden="true">☎</span>} label="Kontakt">{place.contact}</InfoRow>}
    {place.maps_link && <InfoRow icon={<ExternalLinkIcon className="size-4" />} label="Google Maps"><a className="text-link underline" href={place.maps_link} target="_blank" rel="noreferrer">Link öffnen</a></InfoRow>}
    {(place.parking_coordinates || place.parking_link) && <InfoRow icon={<CarIcon className="size-4" />} label="Parkspot" action={place.parking_coordinates && <Button size="icon" variant="secondary" target="_blank" rel="noreferrer" href={directionsUrl(place.parking_coordinates.replace(/\s/g, ''))} aria-label="Route zum Parkspot"><NavigationIcon aria-hidden="true" /></Button>}>{place.parking_coordinates || <a className="text-link underline" href={place.parking_link}>Google Maps Link</a>}</InfoRow>}
    <div className="px-4 py-3"><p className="text-xs text-muted-foreground">Kommentare</p><ul className="mt-2 grid gap-3">{place.notes.map(note => <li className="text-sm" key={note.id}><p className="text-xs text-muted-foreground"><strong className="text-foreground">{note.author}</strong> am {formatGermanDate(note.date)}</p><p>{note.text}</p>{note.photos?.length > 0 && <div className="mt-1 flex gap-1 overflow-x-auto">{note.photos.map(photo => <img className="h-24 rounded-lg object-cover" src={photo.url} alt={photo.alt} key={photo.id} />)}</div>}</li>)}</ul><CommentForm place={place} token={token} onSaved={onSaved} /></div>
  </aside>;
}

function MobileListSheet({ places, selectedPlaceId, onSelect }) {
  const [open, setOpen] = useState(false);
  const touchY = useRef(null);
  return <div className={`absolute inset-x-0 bottom-0 z-10 flex flex-col rounded-t-2xl bg-surface-solid shadow-[0_-4px_16px_rgba(0,0,0,0.15)] transition-[height] ${open ? 'h-[55%]' : 'h-[5.5rem]'}`}><button className="shrink-0 px-4 pt-2 pb-1 text-left" type="button" aria-expanded={open} aria-label={open ? 'Liste einklappen' : 'Liste ausklappen'} onClick={() => setOpen(current => !current)} onTouchStart={event => { touchY.current = event.touches[0].clientY; }} onTouchEnd={event => { const delta = touchY.current - event.changedTouches[0].clientY; if (Math.abs(delta) > 24) setOpen(delta > 0); touchY.current = null; }}><span className="mx-auto block h-1 w-10 rounded-full bg-ring/40" /><strong className="mt-2 block text-sm">{places.length} Auslagerorte</strong></button><div className="min-h-0 px-4"><PlaceList places={places} selectedPlaceId={selectedPlaceId} onSelect={onSelect} /></div></div>;
}

export function PlacesPage({ data, MapComponent = GoogleMap, initialPlaceId = null, onSaved }) {
  const isMobile = useIsMobile();
  const params = new URLSearchParams(window.location.search);
  const [query, setQueryState] = useState(params.get('q') || '');
  const [tags, setTagsState] = useState(() => (data.available_tags || []).filter(tag => params.getAll('tag').includes(tag)));
  const [maxWalk, setMaxWalkState] = useState(() => Number(params.get('max_walk')) || null);
  const [selectedPlaceId, setSelectedPlaceId] = useState(initialPlaceId ? Number(initialPlaceId) : null);
  const [peek, setPeek] = useState(false);
  const updateUrl = (nextQuery, nextTags, nextWalk) => { const next = new URLSearchParams(window.location.search); next.delete('q'); next.delete('tag'); next.delete('max_walk'); if (nextQuery) next.set('q', nextQuery); nextTags.forEach(tag => next.append('tag', tag)); if (nextWalk) next.set('max_walk', nextWalk); window.history.replaceState(window.history.state, '', `${window.location.pathname}${next.size ? `?${next}` : ''}`); };
  const setQuery = next => { setQueryState(next); updateUrl(next, tags, maxWalk); };
  const setTags = next => { setTagsState(next); updateUrl(query, next, maxWalk); };
  const setMaxWalk = next => { setMaxWalkState(next); updateUrl(query, tags, next); };
  const filters = { query, setQuery, tags, setTags, toggleTag: tag => setTags(tags.includes(tag) ? tags.filter(item => item !== tag) : [...tags, tag]), maxWalk, setMaxWalk, availableTags: data.available_tags || [] };
  const filtered = useMemo(() => (data.places || []).filter(place => place.name.toLocaleLowerCase('de').includes(query.toLocaleLowerCase('de')) && tags.every(tag => place.tags.includes(tag)) && (maxWalk == null || place.walking_minutes <= maxWalk)), [data.places, maxWalk, query, tags]);
  const selected = findById(data.places || [], selectedPlaceId);
  const homePlace = (data.places || []).find(place => place.name.toLocaleLowerCase('de') === 'budo') || null;
  const choose = id => { setSelectedPlaceId(Number(id)); setPeek(false); };
  return <div className="relative h-[calc(100svh-var(--app-header-height,0px))] min-h-80 w-full overflow-hidden"><MapComponent apiKey={data.google_maps_browser_api_key} className="absolute inset-0 h-full w-full" places={filtered} homePlace={homePlace} selectedPlaceId={selectedPlaceId} parkingCoordinates={selected?.parking_coordinates} onSelectPlace={choose} />
    {isMobile ? <><div className="absolute top-2 right-2 left-2 z-10 flex flex-col gap-1.5 rounded-xl border border-border bg-card p-2 shadow-lg backdrop-blur"><Search filters={filters} /><Filters filters={filters} row /></div>{!selected && <MobileListSheet places={filtered} selectedPlaceId={selectedPlaceId} onSelect={choose} />}</> : <div className="absolute top-3 left-3 z-10 flex max-h-[calc(100%-1.5rem)] w-80 max-w-[calc(100%-1.5rem)] flex-col gap-2 rounded-xl border border-border bg-card p-3 shadow-lg backdrop-blur"><Search filters={filters} /><Filters filters={filters} /><PlaceList places={filtered} selectedPlaceId={selectedPlaceId} onSelect={choose} /></div>}
    {selected && !peek && <DetailSidebar place={selected} token={data.csrf_token} onBack={() => setSelectedPlaceId(null)} onSaved={onSaved} onPeek={isMobile ? () => setPeek(true) : undefined} />}
    {selected && isMobile && peek && <div className="absolute inset-x-0 bottom-0 z-20 rounded-t-2xl bg-surface-solid px-4 pt-2 pb-3 shadow-[0_-4px_16px_rgba(0,0,0,0.15)]"><button className="flex w-full flex-col text-left" type="button" aria-label="Details ausklappen" onClick={() => setPeek(false)} onTouchStart={event => { event.currentTarget.dataset.touchY = event.touches[0].clientY; }} onTouchEnd={event => { if (Number(event.currentTarget.dataset.touchY) - event.changedTouches[0].clientY > 24) setPeek(false); }}><span className="mx-auto block h-1 w-10 rounded-full bg-ring/40" /><span className="mt-2 flex justify-between gap-2"><span><strong className="block">{selected.name}</strong><TimeBadges place={selected} /></span>{selected.images[0] && <img className="h-12 w-16 rounded-lg object-cover" src={selected.images[0]} alt="" />}</span></button></div>}
  </div>;
}

function TagInput({ availableTags, initialTags }) {
  const [tags, setTags] = useState(initialTags || []); const [draft, setDraft] = useState(''); const suggestionsId = useId();
  const addDraft = () => { const normalized = draft.trim().replace(/\s+/g, ' '); if (!normalized) return; const existing = availableTags.find(tag => tag.toLocaleLowerCase('de') === normalized.toLocaleLowerCase('de')) || normalized; if (!tags.some(tag => tag.toLocaleLowerCase('de') === existing.toLocaleLowerCase('de'))) setTags(current => [...current, existing]); setDraft(''); };
  return <fieldset className="grid gap-2"><legend className="font-medium">Tags</legend>{tags.length > 0 && <div className="flex flex-wrap gap-1">{tags.map(tag => <span className={`${tagChipClass} gap-2 bg-popover`} key={tag}>{tag}<Button className="-mr-2" size="icon-xs" variant="ghost" type="button" aria-label={`Tag ${tag} entfernen`} onClick={() => setTags(current => current.filter(item => item !== tag))}>×</Button><input type="hidden" name="tags" value={tag} /></span>)}</div>}<div className="flex flex-wrap items-end gap-2"><label className="min-w-48 flex-1">Tag hinzufügen<Input name="tags" value={draft} list={suggestionsId} onChange={event => setDraft(event.target.value)} onKeyDown={event => { if (event.key === 'Enter' || event.key === ',') { event.preventDefault(); addDraft(); } }} /></label><datalist id={suggestionsId}>{availableTags.filter(tag => !tags.includes(tag)).map(tag => <option value={tag} key={tag} />)}</datalist><Button size="sm" variant="secondary" type="button" onClick={addDraft}>Hinzufügen</Button></div><p className="m-0 text-sm text-muted-foreground">Mit Enter oder Komma hinzufügen. Neue Tags werden beim Speichern angelegt.</p></fieldset>;
}

export function PlaceFormPage({ data, id }) {
  const place = id ? findById(data.places, id) : null; const keys = { name: 'name', strasse: 'street', ort: 'city', bundesland: 'state', postleitzahl: 'postal_code', land: 'country', maps_link: 'maps_link', beschreibung: 'description', maps_link_parkspot: 'parking_link' };
  const fields = [['name', 'Name'], ['strasse', 'Straße'], ['ort', 'Stadt'], ['bundesland', 'Bundesland'], ['postleitzahl', 'Postleitzahl'], ['land', 'Land'], ['maps_link', 'Google Maps Link'], ['beschreibung', 'Beschreibung', 'textarea'], ['maps_link_parkspot', 'Google Maps Link Parkspot']].map(([name, label, type]) => ({ name, label, type, value: place?.[keys[name]] })); fields.push({ name: 'tags', render: () => <TagInput availableTags={data.available_tags || []} initialTags={place?.tags || []} /> });
  return <Columns><Column id="single-column"><Card title={`Auslagerort ${place ? 'updaten' : 'erstellen'}`}><NativeForm token={data.csrf_token} action={place ? `/auslagerorte/${place.id}/update` : '/auslagerorte/create'} fields={fields} /></Card></Column></Columns>;
}

export function ImageUploadPage({ data, id }) { const place = findById(data.places, id); return <Columns><Column id="single-column"><Card title={`Upload Images for ${place?.name || ''}`}><NativeForm token={data.csrf_token} action={`/auslagerorte/${id}/upload-image/`} encType="multipart/form-data" fields={[{ name: 'images', label: 'Select multiple images', type: 'file', multiple: true, required: true, accept: 'image/*' }]} submit="Upload" /></Card></Column></Columns>; }
const selectedPlaceTitle = (route, data) => findById(data.places, route.id)?.name || route.title;
export const placeRoutes = [
  { pattern: /^\/auslagerorte-list$/, page: 'places', title: 'Auslagerorte', domain: 'places', readContractKey: 'places-list', headerAction: () => <Button className="mobile-icon-action" size="responsive-icon" href="/auslagerorte/create" aria-label="Ort hinzufügen"><span className="desktop-action-label">Ort hinzufügen</span><PlusIcon className="mobile-action-label" aria-hidden="true" /></Button>, render: ({ data, refresh }) => <PlacesPage data={data} onSaved={refresh} /> },
  { pattern: /^\/auslagerorte\/create$/, page: 'place-create', title: 'Neuer Auslagerort', domain: 'places', readContractKey: 'place-create', render: ({ data }) => <PlaceFormPage data={data} /> },
  { pattern: /^\/auslagerorte\/(\d+)\/update$/, page: 'place-update', title: 'Auslagerort bearbeiten', domain: 'places', readContractKey: 'place-update', params: match => ({ id: match[1] }), resolveTitle: selectedPlaceTitle, render: ({ route, data }) => <PlaceFormPage data={data} id={route.id} /> },
  { pattern: /^\/auslagerorte\/(\d+)\/upload-image$/, page: 'place-images', title: 'Bilder hochladen', domain: 'places', readContractKey: 'place-images', params: match => ({ id: match[1] }), resolveTitle: selectedPlaceTitle, render: ({ route, data }) => <ImageUploadPage data={data} id={route.id} /> },
  { pattern: /^\/auslagerorte\/(\d+)$/, page: 'place-detail', title: 'Auslagerort', domain: 'places', readContractKey: 'places-list', params: match => ({ id: match[1] }), resolveTitle: selectedPlaceTitle, render: ({ route, data, refresh }) => <PlacesPage data={data} initialPlaceId={route.id} onSaved={refresh} /> },
];
