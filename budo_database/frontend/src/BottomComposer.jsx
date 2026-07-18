import { useEffect, useRef, useState } from 'react';


/**
 * Presentation and interaction seam shared by bottom-edge note/todo composers.
 * The caller owns persistence; the composer owns draft, retry and focus state.
 */
export function BottomComposer({
  label,
  placeholder,
  submitLabel,
  retryLabel = 'Erneut versuchen',
  onSubmit,
  disabled = false,
  errorText = error => error?.message || 'Die Eingabe konnte nicht gespeichert werden.',
}) {
  const [draft, setDraft] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const inputRef = useRef(null);
  const focusAfterSuccess = useRef(false);
  const trimmed = draft.trim();

  useEffect(() => {
    if (!submitting && focusAfterSuccess.current) {
      focusAfterSuccess.current = false;
      inputRef.current?.focus();
    }
  }, [submitting]);

  const submit = async event => {
    event.preventDefault();
    if (!trimmed || submitting || disabled) return;
    setSubmitting(true);
    setError('');
    try {
      await onSubmit(trimmed);
      setDraft('');
      focusAfterSuccess.current = true;
    } catch (caught) {
      setError(errorText(caught));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="bottom-composer">
      <form onSubmit={submit} aria-busy={submitting}>
        <label className="visually-hidden" htmlFor="bottom-composer-input">{label}</label>
        <input
          id="bottom-composer-input"
          ref={inputRef}
          aria-label={label}
          placeholder={placeholder}
          value={draft}
          disabled={disabled || submitting}
          onChange={event => setDraft(event.target.value)}
        />
        <button
          type="submit"
          disabled={disabled || submitting || !trimmed}
        >
          {error ? retryLabel : submitLabel}
        </button>
      </form>
      {submitting && <span role="status">Wird gespeichert…</span>}
      {error && <p className="error" role="alert">{error}</p>}
    </div>
  );
}
