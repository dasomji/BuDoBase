import { firstAidPhotoLabel, FirstAidGalleryTrigger } from './first-aid-gallery';
import { formatGermanDate } from './shared';

export function FirstAidPhotoStrip({ childName, entryId, photos = [] }) {
  if (!photos.length) return null;
  return (
    <div
      className="first-aid-photo-strip"
      role="region"
      aria-label={`EH-Fotos von ${childName}`}
      tabIndex={0}
    >
      {photos.map((photo, index) => {
        const ordinal = index + 1;
        const alt = photo.alt || firstAidPhotoLabel(childName, entryId, ordinal);
        return (
          <FirstAidGalleryTrigger
            photo={photo}
            childName={childName}
            entryId={entryId}
            ordinal={ordinal}
            key={photo.id}
          >
            <img
              className="first-aid-photo"
              src={photo.url}
              width={photo.width}
              height={photo.height}
              loading="lazy"
              decoding="async"
              alt={alt}
            />
          </FirstAidGalleryTrigger>
        );
      })}
    </div>
  );
}

export function FirstAidEntry({ entry, childName, showChildLink = false }) {
  const name = childName || entry.kid;
  return (
    <li className="first-aid-entry">
      <p>
        <strong>{entry.author}</strong> am {formatGermanDate(entry.date)}:{' '}
        {showChildLink
          ? <a href={`/kid_details/${entry.kid_id}`}>{name}</a>
          : entry.text}
      </p>
      {showChildLink && <p>{entry.text}</p>}
      <FirstAidPhotoStrip childName={name} entryId={entry.id} photos={entry.photos} />
    </li>
  );
}

export function NoteEntry({ entry, childName, showChildLink = false }) {
  const name = childName || entry.kid;
  return (
    <li className="first-aid-entry">
      <p>
        <strong>{entry.author}</strong> am {formatGermanDate(entry.date)}:{' '}
        {showChildLink
          ? <a href={`/kid_details/${entry.kid_id}`}>{name}</a>
          : entry.text}
      </p>
      {showChildLink && <p>{entry.text}</p>}
      <FirstAidPhotoStrip childName={name} entryId={entry.id} photos={entry.photos} />
    </li>
  );
}
