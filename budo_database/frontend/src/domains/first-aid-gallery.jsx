import { createContext, useContext, useMemo, useRef, useState } from 'react';
import { Dialog } from '@base-ui/react/dialog';

import { Button } from '../components/ui/button';

const GalleryContext = createContext(null);
const SWIPE_THRESHOLD = 60;

export function firstAidPhotoLabel(childName, entryId, ordinal) {
  return `EH-Foto ${ordinal} von ${childName || 'unbekanntem Kind'}, EH-Eintrag ${entryId}`;
}

export function flattenFirstAidPhotos(entries = [], childName) {
  return entries.flatMap(entry => {
    const name = childName || entry.kid;
    return (entry.photos || []).map((photo, index) => ({
      ...photo,
      childName: name,
      alt: photo.alt || firstAidPhotoLabel(name, entry.id, index + 1),
    }));
  });
}

export function FirstAidGalleryTrigger({ photo, childName, entryId, ordinal, children }) {
  const gallery = useContext(GalleryContext);
  const label = firstAidPhotoLabel(childName, entryId, ordinal);

  if (!gallery) {
    return (
      <Button className="h-auto max-w-full shrink-0 border-0 bg-transparent p-0" variant="ghost" type="button" aria-label={label}>
        {children}
      </Button>
    );
  }

  return (
    <Dialog.Trigger
      render={<Button className="h-auto max-w-full shrink-0 border-0 bg-transparent p-0" variant="ghost" />}
      id={`first-aid-photo-${photo.id}`}
      type="button"
      aria-label={label}
      onClick={() => gallery.select(photo.id)}
    >
      {children}
    </Dialog.Trigger>
  );
}

function GalleryDialog({ inventory, selectedId, select }) {
  const touchStart = useRef(null);
  const selectedIndex = inventory.findIndex(photo => String(photo.id) === String(selectedId));
  const currentIndex = selectedIndex < 0 ? 0 : selectedIndex;
  const current = inventory[currentIndex];

  if (!current) return null;

  const move = offset => {
    const nextIndex = (currentIndex + offset + inventory.length) % inventory.length;
    select(inventory[nextIndex].id);
  };

  const handleKeyDown = event => {
    if (event.key === 'ArrowLeft') {
      event.preventDefault();
      move(-1);
    } else if (event.key === 'ArrowRight') {
      event.preventDefault();
      move(1);
    }
  };

  const handleTouchStart = event => {
    const touch = event.touches[0];
    touchStart.current = touch ? { x: touch.clientX, y: touch.clientY } : null;
  };

  const handleTouchEnd = event => {
    const start = touchStart.current;
    touchStart.current = null;
    const touch = event.changedTouches[0];
    if (!start || !touch) return;
    const horizontal = touch.clientX - start.x;
    const vertical = touch.clientY - start.y;
    if (Math.abs(horizontal) < SWIPE_THRESHOLD || Math.abs(horizontal) <= Math.abs(vertical)) return;
    move(horizontal < 0 ? 1 : -1);
  };

  return (
    <Dialog.Portal>
      <Dialog.Backdrop className="fixed inset-0 z-1000 bg-black/80" data-testid="first-aid-gallery-backdrop" />
      <Dialog.Viewport className="fixed inset-0 z-1001 grid place-items-center p-1 min-[901px]:p-3">
        <Dialog.Popup className="relative grid max-h-[calc(100dvh-0.5rem)] w-full max-w-275 grid-cols-[auto_minmax(0,1fr)_auto] items-center gap-1 rounded-lg bg-[#181818] p-2 text-white shadow-2xl min-[901px]:max-h-[calc(100dvh-1.5rem)] min-[901px]:gap-2 min-[901px]:p-3" aria-modal="true" onKeyDown={handleKeyDown}>
          <Dialog.Title className="col-span-full m-0 px-10 text-center text-xl">EH-Fotogalerie</Dialog.Title>
          <Dialog.Description className="col-span-full m-0 px-10 text-center text-[#eee]">
            {current.alt}; Bild {currentIndex + 1} von {inventory.length}
          </Dialog.Description>
          <Dialog.Close render={<Button className="absolute top-2 right-2 size-11 border-white/45 bg-black/55 text-3xl leading-none text-white" variant="ghost" size="icon" />} aria-label="Galerie schließen">
            <span aria-hidden="true">×</span>
          </Dialog.Close>
          <Button
            className="size-11 border-white/45 bg-black/55 text-3xl leading-none text-white"
            variant="ghost"
            size="icon"
            type="button"
            aria-label="Vorheriges Foto"
            onClick={() => move(-1)}
          >
            <span aria-hidden="true">‹</span>
          </Button>
          <div className="grid min-h-0 min-w-0 place-items-center">
            <img
              className="block h-auto max-h-[calc(100dvh-12rem)] w-auto max-w-full touch-pan-y object-contain select-none"
              src={current.url}
              width={current.width}
              height={current.height}
              alt={current.alt}
              onTouchStart={handleTouchStart}
              onTouchEnd={handleTouchEnd}
              draggable="false"
            />
          </div>
          <Button
            className="size-11 border-white/45 bg-black/55 text-3xl leading-none text-white"
            variant="ghost"
            size="icon"
            type="button"
            aria-label="Nächstes Foto"
            onClick={() => move(1)}
          >
            <span aria-hidden="true">›</span>
          </Button>
        </Dialog.Popup>
      </Dialog.Viewport>
    </Dialog.Portal>
  );
}

export function FirstAidGallery({ entries = [], childName, children }) {
  const inventory = useMemo(
    () => flattenFirstAidPhotos(entries, childName),
    [childName, entries],
  );
  const [selectedId, setSelectedId] = useState(null);
  const context = useMemo(() => ({ select: setSelectedId }), []);

  return (
    <Dialog.Root modal disablePointerDismissal>
      <GalleryContext.Provider value={context}>
        {children}
      </GalleryContext.Provider>
      <GalleryDialog inventory={inventory} selectedId={selectedId} select={setSelectedId} />
    </Dialog.Root>
  );
}
