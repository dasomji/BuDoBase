import { createContext, useContext, useMemo, useRef, useState } from 'react';
import { Dialog } from '@base-ui/react/dialog';

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
      <button className="first-aid-photo-trigger" type="button" aria-label={label}>
        {children}
      </button>
    );
  }

  return (
    <Dialog.Trigger
      className="first-aid-photo-trigger"
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
      <Dialog.Backdrop className="first-aid-gallery-backdrop" />
      <Dialog.Viewport className="first-aid-gallery-viewport">
        <Dialog.Popup className="first-aid-gallery" aria-modal="true" onKeyDown={handleKeyDown}>
          <Dialog.Title className="first-aid-gallery-title">EH-Fotogalerie</Dialog.Title>
          <Dialog.Description className="first-aid-gallery-description">
            {current.alt}; Bild {currentIndex + 1} von {inventory.length}
          </Dialog.Description>
          <Dialog.Close className="first-aid-gallery-close" aria-label="Galerie schließen">
            <span aria-hidden="true">×</span>
          </Dialog.Close>
          <button
            className="first-aid-gallery-control first-aid-gallery-previous"
            type="button"
            aria-label="Vorheriges Foto"
            onClick={() => move(-1)}
          >
            <span aria-hidden="true">‹</span>
          </button>
          <div className="first-aid-gallery-media">
            <img
              className="first-aid-gallery-image"
              src={current.url}
              width={current.width}
              height={current.height}
              alt={current.alt}
              onTouchStart={handleTouchStart}
              onTouchEnd={handleTouchEnd}
              draggable="false"
            />
          </div>
          <button
            className="first-aid-gallery-control first-aid-gallery-next"
            type="button"
            aria-label="Nächstes Foto"
            onClick={() => move(1)}
          >
            <span aria-hidden="true">›</span>
          </button>
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
