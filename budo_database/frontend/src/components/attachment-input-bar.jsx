import { useId, useRef, useState } from 'react';
import { ImagePlusIcon } from 'lucide-react';

import { RestForm } from '../components';
import { Button } from './ui/button';
import { Textarea } from './ui/input';

export function AttachmentInputBar({
  target,
  token,
  className = '',
  onSuccess,
  textId,
  textName,
  textLabel,
  textLabelVisible = false,
  placeholder,
  required = false,
  photoId,
  photoName,
  photoLabel,
  photoButtonLabel,
  photoAccept = 'image/*',
  submitLabel,
  submitName,
  submitValue,
}) {
  const generatedId = useId();
  const resolvedTextId = textId || `${generatedId}-text`;
  const resolvedPhotoId = photoId || `${generatedId}-photos`;
  const photoInputRef = useRef(null);
  const [photoCount, setPhotoCount] = useState(0);
  const saved = onSuccess
    ? async (result, form) => {
        await onSuccess(result, form);
        setPhotoCount(0);
      }
    : undefined;

  return (
    <RestForm
      className={`min-w-0 ${className}`.trim()}
      target={target}
      token={token}
      encType="multipart/form-data"
      onSuccess={saved}
      resetOnSuccess
    >
      {({ submitting }) => (
        <>
          <label className={textLabelVisible ? 'mb-2 block' : 'sr-only'} htmlFor={resolvedTextId}>
            {textLabel}
          </label>
          <div className="flex min-w-0 items-center gap-2" data-slot="attachment-input-bar">
            <div className="relative min-w-0 flex-1" data-slot="attachment-input-field">
              <Textarea
                className="max-h-[4lh] min-h-10 resize-none overflow-y-auto bg-background pr-10 [field-sizing:content]"
                id={resolvedTextId}
                name={textName}
                placeholder={placeholder}
                rows="1"
                required={required}
              />
              <Button
                className="absolute top-1/2 right-1 z-1 -translate-y-1/2"
                variant="ghost"
                size="icon"
                type="button"
                aria-label={photoButtonLabel}
                disabled={submitting}
                onClick={() => photoInputRef.current?.click()}
              >
                <ImagePlusIcon aria-hidden="true" />
                {photoCount > 0 && (
                  <span
                    className="absolute -right-1 -bottom-1 grid h-4 min-w-4 place-items-center rounded-full bg-destructive px-0.5 text-[10px] font-bold text-destructive-foreground"
                    data-slot="attachment-count"
                    aria-hidden="true"
                  >
                    {photoCount}
                  </span>
                )}
              </Button>
              <input
                className="sr-only"
                id={resolvedPhotoId}
                ref={photoInputRef}
                aria-label={photoLabel}
                name={photoName}
                type="file"
                accept={photoAccept}
                multiple
                tabIndex={-1}
                onChange={event => setPhotoCount(event.target.files?.length || 0)}
              />
            </div>
            <Button
              className="shrink-0"
              size="icon"
              type="submit"
              name={submitName}
              value={submitValue}
              aria-label={submitLabel}
              disabled={submitting}
            >
              ➤
            </Button>
          </div>
        </>
      )}
    </RestForm>
  );
}
