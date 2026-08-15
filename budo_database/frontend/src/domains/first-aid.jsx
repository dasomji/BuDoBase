import { entryPhotoKinds, entryPhotoLabel, EntryPhotoGalleryTrigger } from './entry-photo-gallery';
import { formatGermanDate } from './shared';

export function EntryPhotoStrip({ childName, entryId, photoKind = entryPhotoKinds.firstAid, photos = [] }) {
  if (!photos.length) return null;
  return (
    <div
      className="flex w-full min-w-0 max-w-full gap-2 overflow-x-auto overflow-y-hidden py-1 overscroll-x-contain touch-pan-x"
      role="region"
      aria-label={`${photoKind.photos} von ${childName}`}
      tabIndex={0}
    >
      {photos.map((photo, index) => {
        const ordinal = index + 1;
        const alt = photo.alt || entryPhotoLabel(photoKind, childName, entryId, ordinal);
        return (
          <EntryPhotoGalleryTrigger
            photo={photo}
            childName={childName}
            entryId={entryId}
            photoKind={photoKind}
            ordinal={ordinal}
            key={photo.id}
          >
            <img
              className="block h-auto max-h-50 w-auto max-w-full object-contain"
              src={photo.url}
              width={photo.width}
              height={photo.height}
              loading="lazy"
              decoding="async"
              alt={alt}
            />
          </EntryPhotoGalleryTrigger>
        );
      })}
    </div>
  );
}

export function FirstAidEntry({ entry, childName, showChildLink = false }) {
  const name = childName || entry.kid;
  return (
    <li className="min-w-0 max-w-full break-words">
      <p>
        <strong>{entry.author}</strong> am {formatGermanDate(entry.date)}:{' '}
        {showChildLink
          ? <a href={`/kid_details/${entry.kid_id}`}>{name}</a>
          : entry.text}
      </p>
      {showChildLink && <p>{entry.text}</p>}
      <EntryPhotoStrip childName={name} entryId={entry.id} photos={entry.photos} />
    </li>
  );
}

export function NoteEntry({ entry, childName, showChildLink = false }) {
  const name = childName || entry.kid;
  return (
    <li className="min-w-0 max-w-full break-words">
      <p>
        <strong>{entry.author}</strong> am {formatGermanDate(entry.date)}:{' '}
        {showChildLink
          ? <a href={`/kid_details/${entry.kid_id}`}>{name}</a>
          : entry.text}
      </p>
      {showChildLink && <p>{entry.text}</p>}
      <EntryPhotoStrip childName={name} entryId={entry.id} photoKind={entryPhotoKinds.notes} photos={entry.photos} />
    </li>
  );
}
