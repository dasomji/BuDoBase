import { useEffect, useId, useMemo, useRef, useState } from 'react';
import { Dialog } from '@base-ui/react/dialog';
import { ArrowLeftIcon, CarIcon, ChevronLeftIcon, ChevronRightIcon, FootprintsIcon, ImagePlusIcon, ListFilterIcon, MapIcon, MapPinIcon, PencilIcon, PlusIcon, SatelliteIcon, SearchIcon, Trash2Icon, XIcon } from 'lucide-react';

import { Card, Column, Columns, ConfirmationDialog, findById, NativeForm, RestForm } from '../components';
import { DirectionsButton } from '../components/directions-button';
import { GoogleMap } from '../components/google-map';
import { TagIcon, tagIconForName } from '../components/tag-icon';
import SettingsTagIconPicker from '../components/tag-icon-picker';
import { Button } from '../components/ui/button';
import { Input, Textarea } from '../components/ui/input';
import { useErrorToast, useSuccessToast } from '../components/ui/toast';
import { useIsMobile } from '../hooks/use-mobile';
import { formatGermanDate, NotFoundPage } from './shared';

const tagChipClass = 'inline-flex min-h-8 items-center rounded-full border border-input px-3 py-1 text-sm font-medium wrap-anywhere';
const formatTravelMinutes = minutes => {
  if (minutes == null) return '---';
  if (minutes <= 60) return `${minutes} min`;
  return `${Math.floor(minutes / 60)} h ${minutes % 60} min`;
};
const GALLERY_SWIPE_THRESHOLD = 48;
const galleryButtonClass = 'border-overlay-foreground/50 bg-modal-overlay text-overlay-foreground hover:bg-overlay-foreground hover:text-foreground';

function TimeBadges({ place }) {
  return (
    <span className="flex flex-wrap gap-2 text-xs text-muted-foreground">
      <span className="inline-flex items-center gap-1">
        <CarIcon className="size-3.5" aria-hidden="true" />
        {formatTravelMinutes(place.driving_minutes)}
      </span>
      <span className="inline-flex items-center gap-1">
        <FootprintsIcon className="size-3.5" aria-hidden="true" />
        {formatTravelMinutes(place.walking_minutes)}
      </span>
    </span>
  );
}

function Filters({ filters, row = false }) {
  const [walkingFiltersOpen, setWalkingFiltersOpen] = useState(false);
  const walkingFiltersId = useId();
  const walkingFilterLabel = filters.maximumWalkingMinutes == null
    ? 'Gehzeit filtern'
    : `Gehzeitfilter: höchstens ${filters.maximumWalkingMinutes} Minuten`;
  const chips = <>
    {filters.availableTags.map(tag => <Button className="h-auto min-h-8 shrink-0 rounded-full px-3 py-1" size="sm" variant={filters.tags.includes(tag) ? 'secondary' : 'outline'} type="button" aria-pressed={filters.tags.includes(tag)} onClick={() => filters.toggleTag(tag)} key={tag}><TagIcon className="size-3.5" name={tagIconForName(filters.tagCatalog, tag)} aria-hidden="true" />{tag}</Button>)}
    <Button
      size="icon-sm"
      variant={filters.maximumWalkingMinutes == null ? 'outline' : 'secondary'}
      type="button"
      aria-label={walkingFilterLabel}
      aria-controls={walkingFiltersId}
      aria-expanded={walkingFiltersOpen}
      aria-pressed={filters.maximumWalkingMinutes != null}
      onClick={() => setWalkingFiltersOpen(open => !open)}
    >
      <ListFilterIcon aria-hidden="true" />
    </Button>
    {walkingFiltersOpen && <span className="contents" id={walkingFiltersId}>
      {[30, 60, 90].map(minutes => <Button className="h-auto min-h-8 shrink-0 rounded-full px-3 py-1" size="sm" variant={filters.maximumWalkingMinutes === minutes ? 'secondary' : 'outline'} type="button" aria-pressed={filters.maximumWalkingMinutes === minutes} onClick={() => { filters.setMaximumWalkingMinutes(filters.maximumWalkingMinutes === minutes ? null : minutes); setWalkingFiltersOpen(false); }} key={minutes}>Höchstens {minutes} Minuten zu Fuß</Button>)}
    </span>}
    {filters.tags.length > 0 && <Button size="xs" variant="ghost" type="button" onClick={() => filters.setTags([])}>Tagfilter zurücksetzen</Button>}
  </>;
  return <div className={row ? 'flex gap-1.5 overflow-x-auto pb-1' : 'flex flex-wrap gap-1.5'} role="group" aria-label="Auslagerorte filtern">{chips}</div>;
}

function Search({ filters }) {
  return <label className="relative block"><span className="sr-only">Auslagerort suchen</span><SearchIcon className="absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" aria-hidden="true" /><Input className="bg-background pl-9" type="search" aria-label="Auslagerort suchen" placeholder="Auslagerort suchen" value={filters.query} onChange={event => filters.setQuery(event.target.value)} /></label>;
}

function PlaceTags({ tags, catalog, className = '' }) {
  return <span className={`flex flex-wrap gap-1 ${className}`}>{tags.map(tag => <span className="inline-flex items-center gap-1 rounded-full bg-background px-2 py-1 text-xs" key={tag}><TagIcon className="size-3.5" name={tagIconForName(catalog, tag)} aria-hidden="true" />{tag}</span>)}</span>;
}

function PlaceList({ places, selectedPlaceId, onSelect, tagCatalog }) {
  return (
    <ul className="m-0 h-full min-h-0 list-none divide-y divide-border overflow-y-auto p-0">
      {places.map(place => {
        const selected = Number(selectedPlaceId) === place.id;
        return (
          <li key={place.id}>
            <Button
              className={`h-auto flex-col items-start gap-1 px-1 py-2 text-left ${selected ? 'bg-secondary' : ''}`}
              variant="full-surface"
              type="button"
              aria-current={selected ? 'true' : undefined}
              onClick={() => onSelect(place.id)}
            >
              <strong className="text-sm">
                {place.name}
                {!place.coordinates && <span className="ml-1 text-xs font-normal text-warning-foreground">(kein Pin)</span>}
              </strong>
              <span className="flex flex-wrap items-center gap-x-2 gap-y-1" role="group" aria-label={`Reisezeiten und Tags für ${place.name}`}>
                <TimeBadges place={place} />
                {place.tags.length > 0 && <PlaceTags tags={place.tags} catalog={tagCatalog} />}
              </span>
            </Button>
          </li>
        );
      })}
      {!places.length && <li className="py-3 text-sm text-muted-foreground">Keine Orte für diesen Filter.</li>}
    </ul>
  );
}

const galleryImagesFor = place => place.gallery_images || (place.images || []).map((url, index) => ({
  id: null,
  url,
  alt: `${place.name} ${index + 1}`,
  comment_text: null,
}));

function Gallery({ place, images, initialIndex, onClose, onRequestDelete }) {
  const [index, setIndex] = useState(initialIndex);
  const touchStart = useRef(null);
  const move = direction => setIndex(current => (
    current + direction + images.length
  ) % images.length);
  useEffect(() => {
    const handleWindowKeyDown = event => {
      if (event.key === 'ArrowRight') setIndex(current => (current + 1) % images.length);
      if (event.key === 'ArrowLeft') setIndex(current => (current - 1 + images.length) % images.length);
      if (event.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleWindowKeyDown);
    return () => window.removeEventListener('keydown', handleWindowKeyDown);
  }, [images.length, onClose]);
  const handleTouchStart = event => {
    const touch = event.touches[0];
    touchStart.current = { x: touch.clientX, y: touch.clientY };
  };
  const handleTouchEnd = event => {
    if (!touchStart.current) return;
    const touch = event.changedTouches[0];
    const horizontal = touch.clientX - touchStart.current.x;
    const vertical = touch.clientY - touchStart.current.y;
    touchStart.current = null;
    if (Math.abs(horizontal) < GALLERY_SWIPE_THRESHOLD || Math.abs(horizontal) <= Math.abs(vertical)) return;
    move(horizontal < 0 ? 1 : -1);
  };
  const image = images[index];

  return (
    <Dialog.Root open modal onOpenChange={open => { if (!open) onClose(); }}>
      <Dialog.Portal>
        <Dialog.Backdrop className="fixed inset-0 z-[var(--z-modal)] bg-modal-overlay" />
        <Dialog.Viewport className="fixed inset-0 z-[calc(var(--z-modal)+1)] grid place-items-center p-4">
          <Dialog.Popup className={`relative grid h-full max-h-[90svh] w-full items-center gap-2 text-overlay-foreground ${images.length > 1 ? 'grid-cols-[auto_minmax(0,1fr)_auto]' : 'grid-cols-1'}`}>
            <Dialog.Title className="sr-only">Bilder von {place.name}</Dialog.Title>
            <Dialog.Description className="sr-only">Bild {index + 1} von {images.length}</Dialog.Description>
            <Dialog.Close className="absolute top-0 right-0 z-10" render={<Button className={galleryButtonClass} size="icon" variant="outline" />} aria-label="Galerie schließen">
              <XIcon aria-hidden="true" />
            </Dialog.Close>
            {onRequestDelete && image.id != null && <Button className={`absolute top-0 right-12 z-10 ${galleryButtonClass}`} size="icon" variant="outline" type="button" aria-label="Bild löschen" onClick={() => onRequestDelete(image)}>
              <Trash2Icon aria-hidden="true" />
            </Button>}
            {images.length > 1 && <Button className={galleryButtonClass} size="icon" variant="outline" aria-label="Vorheriges Bild" onClick={() => move(-1)}>
              <ChevronLeftIcon aria-hidden="true" />
            </Button>}
            <img className="max-h-[85svh] max-w-full touch-pan-y justify-self-center object-contain" src={image.url} alt={image.alt} onTouchStart={handleTouchStart} onTouchEnd={handleTouchEnd} draggable="false" />
            {images.length > 1 && <Button className={galleryButtonClass} size="icon" variant="outline" aria-label="Nächstes Bild" onClick={() => move(1)}>
              <ChevronRightIcon aria-hidden="true" />
            </Button>}
            {(image.comment_text || images.length > 1) && <div className="absolute inset-x-12 bottom-0 text-center">
              {image.comment_text && <p className="mx-auto max-w-2xl rounded-lg bg-modal-overlay px-3 py-2">{image.comment_text}</p>}
              {images.length > 1 && <p>{index + 1} / {images.length}</p>}
            </div>}
          </Dialog.Popup>
        </Dialog.Viewport>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

function Carousel({ place, onBack, onPeek, onOpenGallery }) {
  const [index, setIndex] = useState(0);
  const touchY = useRef(null);
  const images = place.images || [];
  return <div className="relative h-52 shrink-0 bg-muted max-[900px]:h-72" onTouchStart={event => { touchY.current = event.touches[0].clientY; }} onTouchEnd={event => { if (touchY.current !== null && event.changedTouches[0].clientY - touchY.current > 24) onPeek?.(); touchY.current = null; }}>
    {images.length ? <Button className="h-full" variant="full-surface" type="button" aria-label="Galerie öffnen" onClick={() => onOpenGallery(images[index])}><img className="h-full w-full object-cover" src={images[index]} alt={`${place.name} ${index + 1}`} /></Button> : <div className="grid h-full place-items-center text-muted-foreground">Keine Bilder</div>}
    <Button className="absolute top-3 left-3" size="icon" variant="outline" type="button" aria-label="Zurück zur Liste" onClick={onBack}><ArrowLeftIcon aria-hidden="true" /></Button>
    {images.length > 1 && <><Button className="absolute top-1/2 left-2 -translate-y-1/2" size="icon" variant="outline" aria-label="Vorheriges Bild" onClick={() => setIndex((index - 1 + images.length) % images.length)}><ChevronLeftIcon aria-hidden="true" /></Button><Button className="absolute top-1/2 right-2 -translate-y-1/2" size="icon" variant="outline" aria-label="Nächstes Bild" onClick={() => setIndex((index + 1) % images.length)}><ChevronRightIcon aria-hidden="true" /></Button><div className="absolute inset-x-0 bottom-2 flex justify-center gap-1">{images.map((_, dot) => <span className={`size-2 rounded-full ${dot === index ? 'bg-secondary' : 'bg-background/75'}`} key={dot} />)}</div></>}
    {onPeek && <Button className="absolute inset-x-1/2 bottom-2 z-10 h-auto w-20 -translate-x-1/2 py-2" variant="outline" type="button" aria-label="Details einklappen" onClick={onPeek}><span className="block h-1 w-10 rounded-full bg-ring/60" /></Button>}
  </div>;
}

function InfoRow({ icon, label, action, children }) {
  return <div className="flex items-start gap-3 border-b border-border px-4 py-3"><span className="mt-0.5 text-muted-foreground">{icon}</span><div className="min-w-0 flex-1 text-sm"><p className="m-0 text-xs text-muted-foreground">{label}</p><div>{children}</div></div>{action}</div>;
}

function AddPlaceImagesButton({ place, token, onSaved }) {
  const inputRef = useRef(null);
  const inputId = `place-images-${place.id}`;
  return <RestForm className="contents" target={`/auslagerorte/${place.id}/upload-image/`} token={token} encType="multipart/form-data" onSuccess={onSaved} resetOnSuccess>
    {({ submitting }) => <>
      <Button size="icon" variant="secondary" type="button" aria-label="Bilder hinzufügen" disabled={submitting} onClick={() => inputRef.current?.click()}><ImagePlusIcon aria-hidden="true" /></Button>
      <input
        className="sr-only"
        id={inputId}
        ref={inputRef}
        name="images"
        type="file"
        accept="image/*"
        multiple
        aria-label="Bilder auswählen"
        onChange={event => { if (event.target.files?.length) event.currentTarget.form.requestSubmit(); }}
      />
    </>}
  </RestForm>;
}

function CommentForm({ place, token, onSaved }) {
  const [photos, setPhotos] = useState([]);
  const saved = async result => { setPhotos([]); await onSaved?.(result); };
  return <RestForm className="mt-3 flex items-center gap-2" target={`/auslagerorte/${place.id}/`} token={token} encType="multipart/form-data" onSuccess={saved} resetOnSuccess><div className="relative flex-1"><Textarea className="min-h-10 bg-background pr-10" rows="1" aria-label="Kommentar" name="notiz" placeholder="Kommentar…" /><label className="absolute top-1/2 right-1 grid size-8 -translate-y-1/2 place-items-center" htmlFor="place-comment-images"><span className="sr-only">Kommentar-Bilder</span><ImagePlusIcon className="size-4" aria-hidden="true" />{photos.length > 0 && <span className="absolute -right-1 -bottom-1 grid size-4 rounded-full bg-destructive text-[10px] text-destructive-foreground">{photos.length}</span>}</label><input id="place-comment-images" className="sr-only" aria-label="Kommentar-Bilder" name="images" type="file" accept="image/*" multiple onChange={event => setPhotos([...event.target.files])} /></div><Button size="icon" type="submit" aria-label="Kommentar senden">➤</Button></RestForm>;
}

function PlaceDeleteDialog({ place, onCancel, onConfirm }) {
  const [confirmation, setConfirmation] = useState('');
  const inputRef = useRef(null);
  const confirmationId = `place-delete-confirmation-${place.id}`;
  return <ConfirmationDialog
    open
    title={`${place.name} löschen`}
    confirmLabel="Endgültig löschen"
    confirmAriaLabel={`${place.name} endgültig löschen`}
    cancelLabel="Abbrechen"
    onConfirm={confirmation === place.name ? onConfirm : null}
    onCancel={onCancel}
    destructive
    initialFocusRef={inputRef}
  >
    <p>Der Auslagerort mit allen Kommentaren und Bildern wird unwiderruflich gelöscht.</p>
    <label className="mt-4 mb-1 block font-medium" htmlFor={confirmationId}>„{place.name}“ zur Bestätigung eingeben</label>
    <Input id={confirmationId} ref={inputRef} autoComplete="off" spellCheck="false" value={confirmation} onChange={event => setConfirmation(event.target.value)} />
  </ConfirmationDialog>;
}

function ImageDeleteDialog({ onCancel, onConfirm }) {
  return <ConfirmationDialog open title="Bild löschen?" confirmLabel="Bild endgültig löschen" cancelLabel="Abbrechen" onConfirm={onConfirm} onCancel={onCancel} destructive>
    <p>Das Bild wird unwiderruflich gelöscht.</p>
  </ConfirmationDialog>;
}

function DetailSidebar({ place, token, onBack, onSaved, onPeek, tagCatalog, permissions = {}, mutate, navigateRoute }) {
  const [galleryIndex, setGalleryIndex] = useState(null);
  const [deleteImage, setDeleteImage] = useState(null);
  const [deletePlace, setDeletePlace] = useState(false);
  const [busy, setBusy] = useState(false);
  const showError = useErrorToast();
  const showSuccess = useSuccessToast();
  const galleryImages = galleryImagesFor(place);
  const openGallery = image => {
    const url = typeof image === 'string' ? image : image.url;
    const nextIndex = galleryImages.findIndex(item => item.url === url);
    if (nextIndex >= 0) setGalleryIndex(nextIndex);
  };
  const requestImageDelete = image => {
    setGalleryIndex(null);
    setDeleteImage(image);
  };
  const removeImage = async () => {
    setBusy(true);
    try {
      await mutate(`/api/places/${place.id}/images/${deleteImage.id}/delete/`, {});
      showSuccess('Bild gelöscht.');
      setDeleteImage(null);
    } catch (error) {
      showError(error.payload?.detail || 'Bild konnte nicht gelöscht werden.');
    } finally { setBusy(false); }
  };
  const removePlace = async () => {
    setBusy(true);
    try {
      await mutate(`/api/places/${place.id}/delete/`, { confirmation_name: place.name }, true, false);
      showSuccess(`Auslagerort „${place.name}“ gelöscht.`);
      if (navigateRoute) navigateRoute('/auslagerorte-list/', { replace: true });
      else window.location.assign('/auslagerorte-list/');
    } catch (error) {
      showError(error.payload?.detail || 'Auslagerort konnte nicht gelöscht werden.');
      setBusy(false);
    }
  };
  const address = [place.street, [place.postal_code, place.city].filter(Boolean).join(' '), place.state, place.country].filter(Boolean).join(', ');
  return <aside className="absolute inset-y-0 left-0 z-20 flex w-full max-w-100 flex-col overflow-y-auto bg-surface-solid shadow-elevated max-[900px]:max-w-none" aria-label={place.name}>
    <Carousel place={place} onBack={onBack} onPeek={onPeek} onOpenGallery={openGallery} />
    <div className="border-b border-border px-4 py-3"><div className="flex items-start justify-between gap-2"><h2 className="m-0 text-lg font-bold">{place.name}</h2><div className="flex shrink-0 gap-2"><AddPlaceImagesButton place={place} token={token} onSaved={onSaved} /><Button size="icon" variant="outline" href={`/auslagerorte/${place.id}/update`} aria-label="Bearbeiten"><PencilIcon aria-hidden="true" /></Button>{permissions.delete_places && <Button size="icon" variant="destructive" type="button" aria-label="Auslagerort löschen" onClick={() => setDeletePlace(true)}><Trash2Icon aria-hidden="true" /></Button>}</div></div><PlaceTags className="mt-2" tags={place.tags} catalog={tagCatalog} /><div className="mt-2"><TimeBadges place={place} /></div>{!place.coordinates && <p className="mt-2 text-xs text-warning-foreground">Keine Koordinaten — kein Pin auf der Karte.</p>}</div>
    {place.description && <div className="border-b border-border px-4 py-3 text-sm"><p className="text-xs text-muted-foreground">Beschreibung</p><p>{place.description}</p></div>}
    {place.contact && <InfoRow icon={<span aria-hidden="true">☎</span>} label="Kontakt">{place.contact}</InfoRow>}
    {address && <InfoRow icon={<MapPinIcon className="size-4" />} label="Adresse" action={<DirectionsButton destination={place.coordinates?.replace(/\s/g, '') || address} label="Route zur Adresse" />}>{address}</InfoRow>}
    {(place.parking_coordinates || place.parking_link) && <InfoRow icon={<CarIcon className="size-4" />} label="Parkspot" action={place.parking_coordinates && <DirectionsButton destination={place.parking_coordinates.replace(/\s/g, '')} label="Route zum Parkspot" />}>{place.parking_coordinates || <a className="text-link underline" href={place.parking_link} target="_blank" rel="noreferrer">Google Maps Link</a>}</InfoRow>}
    <div className="px-4 py-3"><p className="text-xs text-muted-foreground">Kommentare</p><ul className="mt-2 grid gap-3">{place.notes.map(note => <li className="text-sm" key={note.id}><p className="text-xs text-muted-foreground"><strong className="text-foreground">{note.author}</strong> am {formatGermanDate(note.date)}</p><p>{note.text}</p>{note.photos?.length > 0 && <div className="mt-1 flex gap-1 overflow-x-auto">{note.photos.map(photo => <Button className="h-24 w-auto shrink-0 overflow-hidden rounded-lg p-0" variant="full-surface" type="button" aria-label={`Kommentarbild öffnen: ${note.text}`} onClick={() => openGallery(photo)} key={photo.id}><img className="h-24 object-cover" src={photo.url} alt={photo.alt} /></Button>)}</div>}</li>)}</ul><CommentForm place={place} token={token} onSaved={onSaved} /></div>
    {galleryIndex != null && galleryImages.length > 0 && <Gallery place={place} images={galleryImages} initialIndex={galleryIndex} onClose={() => setGalleryIndex(null)} onRequestDelete={permissions.delete_place_images ? requestImageDelete : null} />}
    {deleteImage && <ImageDeleteDialog onCancel={() => setDeleteImage(null)} onConfirm={busy ? null : removeImage} />}
    {deletePlace && <PlaceDeleteDialog place={place} onCancel={() => setDeletePlace(false)} onConfirm={busy ? null : removePlace} />}
  </aside>;
}

function MobileListSheet({ places, selectedPlaceId, onSelect, tagCatalog }) {
  const [open, setOpen] = useState(false);
  const touchY = useRef(null);
  const finishSwipe = event => {
    const delta = touchY.current - event.changedTouches[0].clientY;
    if (Math.abs(delta) > 24) setOpen(delta > 0);
    touchY.current = null;
  };
  return (
    <div className={`absolute inset-x-0 bottom-0 z-10 flex flex-col rounded-t-2xl bg-surface-solid shadow-sheet transition-[height] ${open ? 'h-[55%]' : 'h-[5.5rem]'}`}>
      <Button
        className="h-auto shrink-0 flex-col items-stretch px-4 pt-2 pb-1 text-left"
        variant="full-surface"
        type="button"
        aria-expanded={open}
        aria-label={open ? 'Liste einklappen' : 'Liste ausklappen'}
        onClick={() => setOpen(current => !current)}
        onTouchStart={event => { touchY.current = event.touches[0].clientY; }}
        onTouchEnd={finishSwipe}
      >
        <span className="mx-auto block h-1 w-10 rounded-full bg-ring/40" />
        <strong className="mt-2 block text-sm">{places.length} Auslagerorte</strong>
      </Button>
      <div className="min-h-0 flex-1 overflow-hidden px-4" inert={open ? undefined : ''} aria-hidden={!open}>
        <PlaceList places={places} selectedPlaceId={selectedPlaceId} onSelect={onSelect} tagCatalog={tagCatalog} />
      </div>
    </div>
  );
}

export function PlacesPage({ data, MapComponent = GoogleMap, initialPlaceId = null, mapTypeId = 'roadmap', onSaved, navigateRoute, mutate }) {
  const isMobile = useIsMobile();
  const params = new URLSearchParams(window.location.search);
  const [query, setQueryState] = useState(params.get('q') || '');
  const [tags, setTagsState] = useState(() => (data.available_tags || []).filter(tag => params.getAll('tag').includes(tag)));
  const [maximumWalkingMinutes, setMaximumWalkingMinutesState] = useState(
    () => Number(params.get('max_walk')) || null,
  );
  const [selectedPlaceId, setSelectedPlaceId] = useState(initialPlaceId ? Number(initialPlaceId) : null);
  const [peek, setPeek] = useState(false);
  const updateUrl = (nextQuery, nextTags, nextMaximumWalkingMinutes) => {
    const nextParameters = new URLSearchParams(window.location.search);
    nextParameters.delete('q');
    nextParameters.delete('tag');
    nextParameters.delete('max_walk');
    if (nextQuery) nextParameters.set('q', nextQuery);
    nextTags.forEach(tag => nextParameters.append('tag', tag));
    if (nextMaximumWalkingMinutes) {
      nextParameters.set('max_walk', nextMaximumWalkingMinutes);
    }
    window.history.replaceState(
      window.history.state,
      '',
      `${window.location.pathname}${nextParameters.size ? `?${nextParameters}` : ''}`,
    );
  };
  const setQuery = nextQuery => {
    setQueryState(nextQuery);
    updateUrl(nextQuery, tags, maximumWalkingMinutes);
  };
  const setTags = nextTags => {
    setTagsState(nextTags);
    updateUrl(query, nextTags, maximumWalkingMinutes);
  };
  const setMaximumWalkingMinutes = nextMaximum => {
    setMaximumWalkingMinutesState(nextMaximum);
    updateUrl(query, tags, nextMaximum);
  };
  const filters = {
    query,
    setQuery,
    tags,
    setTags,
    toggleTag: tag => setTags(
      tags.includes(tag) ? tags.filter(item => item !== tag) : [...tags, tag],
    ),
    maximumWalkingMinutes,
    setMaximumWalkingMinutes,
    availableTags: data.available_tags || [],
    tagCatalog: data.tag_catalog,
  };
  const filtered = useMemo(() => (data.places || []).filter(place => (
    place.name.toLocaleLowerCase('de').includes(query.toLocaleLowerCase('de'))
      && (tags.length === 0 || tags.some(tag => place.tags.includes(tag)))
      && (
        maximumWalkingMinutes == null
        || (
          place.walking_minutes != null
          && place.walking_minutes <= maximumWalkingMinutes
        )
      )
  )), [data.places, maximumWalkingMinutes, query, tags]);
  const selected = findById(data.places || [], selectedPlaceId);
  const homePlace = (data.places || []).find(
    place => place.name.trim().toLocaleLowerCase('de') === 'budo',
  ) || null;
  const choose = id => { setSelectedPlaceId(Number(id)); setPeek(false); };
  const closeDetails = () => {
    setSelectedPlaceId(null);
    if (initialPlaceId != null) {
      const target = `/auslagerorte-list/${window.location.search}`;
      if (navigateRoute) navigateRoute(target, { replace: true });
      else window.history.replaceState(window.history.state, '', target);
    }
  };
  return <div className="relative h-[calc(100svh-var(--app-header-height,0px))] min-h-80 w-full overflow-hidden"><MapComponent apiKey={data.google_maps_browser_api_key} mapId={data.google_maps_map_id} mapTypeId={mapTypeId} className="absolute inset-0 h-full w-full" places={filtered} homePlace={homePlace} selectedPlaceId={selectedPlaceId} onSelectPlace={choose} />
    {isMobile ? <><div className="absolute top-2 right-2 left-2 z-10 flex flex-col gap-1.5 rounded-xl border border-border bg-card p-2 shadow-elevated backdrop-blur"><Search filters={filters} /><Filters filters={filters} row /></div>{!selected && <MobileListSheet places={filtered} selectedPlaceId={selectedPlaceId} onSelect={choose} tagCatalog={data.tag_catalog} />}</> : <div className="absolute top-3 left-3 z-10 flex max-h-[calc(100%-1.5rem)] w-80 max-w-[calc(100%-1.5rem)] flex-col gap-2 rounded-xl border border-border bg-card p-3 shadow-elevated backdrop-blur"><Search filters={filters} /><Filters filters={filters} /><PlaceList places={filtered} selectedPlaceId={selectedPlaceId} onSelect={choose} tagCatalog={data.tag_catalog} /></div>}
    {selected && !peek && <DetailSidebar place={selected} token={data.csrf_token} onBack={closeDetails} onSaved={onSaved} onPeek={isMobile ? () => setPeek(true) : undefined} tagCatalog={data.tag_catalog} permissions={data.permissions} mutate={mutate} navigateRoute={navigateRoute} />}
    {selected && isMobile && peek && <div className="absolute inset-x-0 bottom-0 z-20 rounded-t-2xl bg-surface-solid shadow-sheet"><Button className="h-auto flex-col items-stretch px-4 pt-2 pb-3 text-left" variant="full-surface" type="button" aria-label="Details ausklappen" onClick={() => setPeek(false)} onTouchStart={event => { event.currentTarget.dataset.touchY = event.touches[0].clientY; }} onTouchEnd={event => { if (Number(event.currentTarget.dataset.touchY) - event.changedTouches[0].clientY > 24) setPeek(false); }}><span className="mx-auto block h-1 w-10 rounded-full bg-ring/40" /><span className="mt-2 flex justify-between gap-2"><span><strong className="block">{selected.name}</strong><TimeBadges place={selected} /></span>{selected.images[0] && <img className="h-12 w-16 rounded-lg object-cover" src={selected.images[0]} alt="" />}</span></Button></div>}
  </div>;
}

function TagInput({ availableTags, initialTags, tagCatalog }) {
  const [tags, setTags] = useState(initialTags || []);
  const [draft, setDraft] = useState('');
  const suggestionsId = useId();
  const isSelected = candidate => tags.some(tag => tag.toLocaleLowerCase('de') === candidate.toLocaleLowerCase('de'));
  const add = tag => { if (!isSelected(tag)) setTags(current => [...current, tag]); };
  const addDraft = () => {
    const normalized = draft.trim().replace(/\s+/g, ' ');
    if (!normalized) return;
    const existing = availableTags.find(tag => tag.toLocaleLowerCase('de') === normalized.toLocaleLowerCase('de')) || normalized;
    add(existing);
    setDraft('');
  };
  const available = availableTags.filter(tag => !isSelected(tag));
  return <fieldset className="grid gap-3"><legend className="font-medium">Tags</legend>
    <div><p className="mb-1 text-sm font-medium">Ausgewählt <span className="font-normal text-muted-foreground">(erster Tag bestimmt das Kartensymbol)</span></p><div className="flex min-h-9 flex-wrap gap-1">{tags.map(tag => <span className={`${tagChipClass} gap-2 bg-secondary`} key={tag}><TagIcon className="size-4" name={tagIconForName(tagCatalog, tag)} aria-hidden="true" />{tag}<Button className="-mr-2" size="icon-xs" variant="ghost" type="button" aria-label={`Tag ${tag} entfernen`} onClick={() => setTags(current => current.filter(item => item !== tag))}>×</Button><input type="hidden" name="tags" value={tag} /></span>)}{tags.length === 0 && <span className="text-sm text-muted-foreground">Keine Tags ausgewählt.</span>}</div></div>
    {available.length > 0 && <div><p className="mb-1 text-sm font-medium">Verfügbar</p><div className="flex flex-wrap gap-1">{available.map(tag => <Button className="h-auto min-h-8 rounded-full px-3 py-1" size="sm" variant="outline" type="button" onClick={() => add(tag)} key={tag}><TagIcon className="size-4" name={tagIconForName(tagCatalog, tag)} aria-hidden="true" />{tag}</Button>)}</div></div>}
    <div className="flex flex-wrap items-end gap-2"><label className="min-w-48 flex-1">Neuen Tag anlegen<Input value={draft} list={suggestionsId} onChange={event => setDraft(event.target.value)} onKeyDown={event => { if (event.key === 'Enter' || event.key === ',') { event.preventDefault(); addDraft(); } }} /></label><datalist id={suggestionsId}>{available.map(tag => <option value={tag} key={tag} />)}</datalist><Button size="sm" variant="secondary" type="button" onClick={addDraft}>Hinzufügen</Button></div><p className="m-0 text-sm text-muted-foreground">Mit Enter oder Komma hinzufügen. Neue Tags erhalten zunächst das Standard-Symbol.</p>
  </fieldset>;
}

export function PlaceFormPage({ data, id }) {
  const place = id ? findById(data.places, id) : null; const keys = { name: 'name', strasse: 'street', ort: 'city', bundesland: 'state', postleitzahl: 'postal_code', land: 'country', maps_link: 'maps_link', beschreibung: 'description', kontakt: 'contact', maps_link_parkspot: 'parking_link' };
  const fields = [['name', 'Name'], ['strasse', 'Straße'], ['ort', 'Stadt'], ['bundesland', 'Bundesland'], ['postleitzahl', 'Postleitzahl'], ['land', 'Land'], ['maps_link', 'Google Maps Link'], ['beschreibung', 'Beschreibung', 'textarea'], ['kontakt', 'Kontakt', 'textarea'], ['maps_link_parkspot', 'Google Maps Link Parkspot']].map(([name, label, type]) => ({ name, label, type, value: place?.[keys[name]] })); fields.push({ name: 'tags', render: () => <TagInput availableTags={data.available_tags || []} initialTags={place?.tags || []} tagCatalog={data.tag_catalog || []} /> });
  return <Columns><Column id="single-column"><Card title={`Auslagerort ${place ? 'updaten' : 'erstellen'}`}><NativeForm token={data.csrf_token} action={place ? `/auslagerorte/${place.id}/update` : '/auslagerorte/create'} fields={fields} /></Card></Column></Columns>;
}

export function ImageUploadPage({ data, id }) { const place = findById(data.places, id); return <Columns><Column id="single-column"><Card title={`Upload Images for ${place?.name || ''}`}><NativeForm token={data.csrf_token} action={`/auslagerorte/${id}/upload-image/`} encType="multipart/form-data" fields={[{ name: 'images', label: 'Select multiple images', type: 'file', multiple: true, required: true, accept: 'image/*' }]} submit="Upload" /></Card></Column></Columns>; }
const selectedPlaceTitle = (route, data) => findById(data.places, route.id)?.name || route.title;
const placesMapType = pageState => pageState?.placesMapType === 'satellite' ? 'satellite' : 'roadmap';

function MapTypeSegment({ mapTypeId, onMapTypeChange }) {
  return <div className="inline-flex rounded-lg shadow-sm max-[900px]:rounded-full" role="group" aria-label="Kartendarstellung">
    <Button className="rounded-r-none max-[900px]:size-8 max-[900px]:rounded-l-full max-[900px]:rounded-r-none max-[900px]:px-0" variant={mapTypeId === 'roadmap' ? 'secondary' : 'outline'} type="button" aria-pressed={mapTypeId === 'roadmap'} onClick={() => onMapTypeChange('roadmap')}><MapIcon aria-hidden="true" /><span className="max-[900px]:sr-only">Karte</span></Button>
    <Button className="rounded-l-none border-l-0 max-[900px]:size-8 max-[900px]:rounded-l-none max-[900px]:rounded-r-full max-[900px]:px-0" variant={mapTypeId === 'satellite' ? 'secondary' : 'outline'} type="button" aria-pressed={mapTypeId === 'satellite'} onClick={() => onMapTypeChange('satellite')}><SatelliteIcon aria-hidden="true" /><span className="max-[900px]:sr-only">Satellit</span></Button>
  </div>;
}

const placesHeaderAction = (includeCreate = false) => (_data, { pageState, setPageState }) => {
  const mapTypeId = placesMapType(pageState);
  const setMapTypeId = nextMapType => setPageState?.(current => ({
    ...current,
    placesMapType: nextMapType,
  }));
  return <div className="flex items-center gap-2">
    <MapTypeSegment mapTypeId={mapTypeId} onMapTypeChange={setMapTypeId} />
    {includeCreate && <Button className="mobile-icon-action" size="responsive-icon" href="/auslagerorte/create" aria-label="Ort hinzufügen"><span className="desktop-action-label">Ort hinzufügen</span><PlusIcon className="mobile-action-label" aria-hidden="true" /></Button>}
  </div>;
};

function IconPicker(props) {
  return <SettingsTagIconPicker {...props} />;
}

function TagEditor({ tag, choices, canDelete, mutate }) {
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState(tag.name);
  const [icon, setIcon] = useState(tag.icon);
  const [saving, setSaving] = useState(false);
  const showError = useErrorToast();
  const showSuccess = useSuccessToast();
  const cancel = () => {
    setName(tag.name);
    setIcon(tag.icon);
    setEditing(false);
  };
  const save = async event => {
    event.preventDefault();
    setSaving(true);
    try {
      await mutate(`/api/place-tags/${tag.id}/update/`, { name, icon });
      showSuccess(`Tag „${name}“ gespeichert.`);
      setEditing(false);
    } catch (error) {
      showError(error.payload?.detail || 'Tag konnte nicht gespeichert werden.');
    } finally { setSaving(false); }
  };
  const remove = async () => {
    if (!window.confirm(`Tag „${tag.name}“ wirklich löschen? Er wird von allen Auslagerorten entfernt.`)) return;
    setSaving(true);
    try {
      await mutate(`/api/place-tags/${tag.id}/delete/`, {});
      showSuccess(`Tag „${tag.name}“ gelöscht.`);
    } catch (error) {
      showError(error.payload?.detail || 'Tag konnte nicht gelöscht werden.');
      setSaving(false);
    }
  };
  return <article className="grid gap-3 rounded-xl border border-border p-4"><div className="flex flex-wrap items-center gap-3"><span className="grid size-10 shrink-0 place-items-center rounded-full bg-muted"><TagIcon className="size-5" name={tag.icon} aria-hidden="true" /></span><h3 className="mr-auto text-base font-medium">{tag.name}</h3><Button variant="secondary" type="button" disabled={saving} onClick={() => setEditing(true)}>Bearbeiten</Button>{canDelete && <Button variant="destructive" type="button" disabled={saving} onClick={remove}>Löschen</Button>}</div>{editing && <form className="grid gap-3 border-t border-border pt-3" onSubmit={save}><label className="font-medium">Name<Input value={name} maxLength={100} required onChange={event => setName(event.target.value)} /></label><IconPicker choices={choices} value={icon} onChange={setIcon} label="Kartensymbol" /><div className="flex justify-end gap-2"><Button variant="ghost" type="button" disabled={saving} onClick={cancel}>Abbrechen</Button><Button variant="secondary" type="submit" disabled={saving}>Speichern</Button></div></form>}<details className="border-t border-border pt-3"><summary className="cursor-pointer font-medium">Auslagerorte ({tag.places?.length || 0})</summary>{tag.places?.length ? <ul className="mt-2 grid gap-1 pl-5">{tag.places.map(place => <li key={place.id}><a className="underline-offset-2 hover:underline" href={`/auslagerorte/${place.id}`}>{place.name}</a></li>)}</ul> : <p className="mt-2 text-sm text-muted-foreground">Keine Auslagerorte verwenden diesen Tag.</p>}</details></article>;
}

function CreateTagDialog({ choices, mutate, open, onOpenChange }) {
  const [name, setName] = useState('');
  const [icon, setIcon] = useState('map-pin');
  const [saving, setSaving] = useState(false);
  const showError = useErrorToast();
  const showSuccess = useSuccessToast();
  const create = async event => {
    event.preventDefault();
    setSaving(true);
    try {
      await mutate('/api/place-tags/', { name, icon });
      showSuccess(`Tag „${name}“ angelegt.`);
      setName('');
      setIcon('map-pin');
      onOpenChange(false);
    } catch (error) {
      showError(error.payload?.detail || 'Tag konnte nicht angelegt werden.');
    } finally { setSaving(false); }
  };
  return <Dialog.Root open={open} onOpenChange={onOpenChange}><Dialog.Portal><Dialog.Backdrop className="fixed inset-0 z-[var(--z-modal)] bg-black/45" /><Dialog.Viewport className="fixed inset-0 z-[var(--z-modal)] grid place-items-center overflow-y-auto p-4"><Dialog.Popup className="card grid max-h-[calc(100dvh-2rem)] w-full max-w-xl gap-4 overflow-y-auto bg-surface-solid p-4"><div className="flex items-center justify-between gap-2"><Dialog.Title className="text-lg font-bold">Neuen Tag anlegen</Dialog.Title><Dialog.Close render={<Button size="icon" variant="ghost" aria-label="Dialog schließen" />}><XIcon aria-hidden="true" /></Dialog.Close></div><form className="grid gap-3" onSubmit={create}><label className="font-medium">Name<Input value={name} maxLength={100} required autoFocus onChange={event => setName(event.target.value)} /></label><IconPicker choices={choices} value={icon} onChange={setIcon} label="Kartensymbol" /><div className="flex justify-end gap-2"><Dialog.Close render={<Button variant="ghost" type="button" disabled={saving} />}>Abbrechen</Dialog.Close><Button type="submit" disabled={saving}>Anlegen</Button></div></form></Dialog.Popup></Dialog.Viewport></Dialog.Portal></Dialog.Root>;
}

export function PlaceTagSettingsPage({ data, mutate, createOpen = false, onCreateOpenChange = () => {} }) {
  return <><Columns><Column id="single-column"><Card title="Auslagerort-Tags"><p className="mb-4 text-sm text-muted-foreground">Tags klassifizieren Auslagerorte. Bei mehreren Tags bestimmt der erste ausgewählte Tag das Symbol auf der Karte.</p><div className="grid gap-4">{data.tags.map(tag => <TagEditor tag={tag} choices={data.icon_choices} canDelete={data.permissions?.delete_tags} mutate={mutate} key={tag.id} />)}{data.tags.length === 0 && <p className="text-muted-foreground">Noch keine Tags vorhanden.</p>}</div></Card></Column></Columns><CreateTagDialog choices={data.icon_choices} mutate={mutate} open={createOpen} onOpenChange={onCreateOpenChange} /></>;
}

const tagSettingsHeaderAction = (_data, { setPageState }) => <Button className="mobile-icon-action" size="responsive-icon" type="button" aria-label="Tag hinzufügen" onClick={() => setPageState?.(current => ({ ...current, createTagOpen: true }))}><span className="desktop-action-label">Tag hinzufügen</span><PlusIcon className="mobile-action-label" aria-hidden="true" /></Button>;

export const placeRoutes = [
  { pattern: /^\/auslagerorte\/tags$/, page: 'place-tag-settings', title: 'Auslagerort-Tags', domain: 'places', readContractKey: 'place-tag-settings', headerAction: tagSettingsHeaderAction, render: ({ data, mutate, pageState, setPageState }) => <PlaceTagSettingsPage data={data} mutate={mutate} createOpen={Boolean(pageState?.createTagOpen)} onCreateOpenChange={open => setPageState?.(current => ({ ...current, createTagOpen: open }))} /> },
  { pattern: /^\/auslagerorte-list$/, page: 'places', title: 'Auslagerorte', domain: 'places', readContractKey: 'places-list', headerAction: placesHeaderAction(true), render: ({ data, refresh, mutate, navigateRoute, pageState }) => <PlacesPage data={data} mapTypeId={placesMapType(pageState)} onSaved={refresh} mutate={mutate} navigateRoute={navigateRoute} /> },
  { pattern: /^\/auslagerorte\/create$/, page: 'place-create', title: 'Neuer Auslagerort', domain: 'places', readContractKey: 'place-create', render: ({ data }) => <PlaceFormPage data={data} /> },
  { pattern: /^\/auslagerorte\/(\d+)\/update$/, page: 'place-update', title: 'Auslagerort bearbeiten', domain: 'places', readContractKey: 'place-update', params: match => ({ id: match[1] }), resolveTitle: selectedPlaceTitle, render: ({ route, data }) => <PlaceFormPage data={data} id={route.id} /> },
  { pattern: /^\/auslagerorte\/(\d+)\/upload-image$/, page: 'place-images', title: 'Bilder hochladen', domain: 'places', readContractKey: 'place-images', params: match => ({ id: match[1] }), resolveTitle: selectedPlaceTitle, render: ({ route, data }) => <ImageUploadPage data={data} id={route.id} /> },
  { pattern: /^\/auslagerorte\/(\d+)$/, page: 'place-detail', title: 'Auslagerort', domain: 'places', readContractKey: 'places-list', params: match => ({ id: match[1] }), resolveTitle: selectedPlaceTitle, headerAction: placesHeaderAction(), render: ({ route, data, refresh, mutate, navigateRoute, pageState }) => <PlacesPage data={data} initialPlaceId={route.id} mapTypeId={placesMapType(pageState)} onSaved={refresh} mutate={mutate} navigateRoute={navigateRoute} /> },
];
