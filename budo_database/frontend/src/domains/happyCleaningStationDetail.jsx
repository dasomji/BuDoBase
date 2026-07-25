import { useEffect, useMemo, useRef, useState } from 'react';
import { EditorContent, useEditor } from '@tiptap/react';
import Document from '@tiptap/extension-document';
import Paragraph from '@tiptap/extension-paragraph';
import Text from '@tiptap/extension-text';
import TaskList from '@tiptap/extension-task-list';
import TaskItem from '@tiptap/extension-task-item';

import './happyCleaningStationDetail.css';
import { SingleStationCopyDialog } from './happyCleaningCopy';

const StableTaskItem = TaskItem.extend({
  addAttributes() {
    return {
      ...this.parent?.(),
      id: { default: null },
      version: { default: null },
    };
  },
});

const requestId = () => globalThis.crypto?.randomUUID?.()
  || `happy-cleaning-todo-${Date.now()}-${Math.random().toString(36).slice(2)}`;

const errorMessage = error => {
  const errors = error?.payload?.errors;
  if (errors) return Object.values(errors).flat().join(' ');
  if (error?.payload?.code === 'stale') {
    return 'Die Daten wurden inzwischen geändert. Bitte erneut versuchen.';
  }
  if (error?.payload?.code === 'sync_unavailable') {
    return 'Vor der nächsten Änderung müssen aktuelle Daten geladen werden.';
  }
  if (error?.payload?.code === 'overbooking_confirmation_required') {
    return 'Die Einteilung hat sich geändert. Bitte aktuelle Überbelegung prüfen und erneut bestätigen.';
  }
  return error?.message || 'Die Änderung konnte nicht gespeichert werden.';
};

const capacityLabel = station => station.overbooked_count > 0
  ? `${station.overbooked_count} überbelegt`
  : `${Math.max(station.max_kids - (station.assigned_count || 0), 0)} / ${station.max_kids} frei`;

function Progress({ station }) {
  const total = station.todo_total_count;
  if (!total) {
    return <span className="happy-cleaning-detail-progress" aria-label="Todo-Fortschritt">—</span>;
  }
  return (
    <span className="happy-cleaning-detail-progress" aria-label="Todo-Fortschritt">
      {station.todo_checked_count}/{total} · {station.todo_progress_percentage}%
    </span>
  );
}

function DirtyNavigationDialog({ onContinue, onDiscard, onSave }) {
  return (
    <section role="dialog" aria-modal="true" aria-label="Ungespeicherte Änderungen">
      <p>Es gibt ungespeicherte Änderungen.</p>
      <button type="button" onClick={onContinue}>Weiter bearbeiten</button>
      <button type="button" onClick={onDiscard}>Verwerfen</button>
      <button type="button" onClick={onSave}>Speichern und weiter</button>
    </section>
  );
}

function StationEditor({ data, mutate, onSaved, onDeleted, registerNavigationGuard, onBack }) {
  const { event, station } = data;
  const creating = station.id == null;
  const commandRequestId = useRef(requestId());
  const [fields, setFields] = useState({
    name: station.name,
    max_kids: String(station.max_kids),
    meeting_point: station.meeting_point,
    wishes: station.wishes,
    responsible_profile_id: station.responsible?.id ? String(station.responsible.id) : '',
  });
  const [pendingNavigation, setPendingNavigation] = useState(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [editorRevision, setEditorRevision] = useState(0);
  const editorContainer = useRef(null);
  const initialDocument = useMemo(() => station.document || { type: 'doc', content: [] }, [station.document]);
  const editor = useEditor({
    extensions: [
      Document,
      Paragraph,
      Text,
      TaskList,
      StableTaskItem.configure({ nested: false }),
    ],
    content: initialDocument,
    editorProps: {
      attributes: { 'aria-label': 'Stationsinhalt' },
      handleDOMEvents: {
        click: (_view, event) => event.target instanceof HTMLInputElement
          && event.target.type === 'checkbox',
      },
    },
    onUpdate: () => setEditorRevision(value => value + 1),
  });
  const editorDocument = editor?.getJSON() || initialDocument;
  const currentDocument = {
    ...editorDocument,
    content: editorDocument.content || [],
  };
  useEffect(() => {
    editorContainer.current?.querySelectorAll('input[type="checkbox"]').forEach(checkbox => {
      checkbox.disabled = true;
      checkbox.tabIndex = -1;
      checkbox.setAttribute('aria-label', 'Aufgabenstatus wird beim Bearbeiten nicht geändert');
    });
  }, [editor, editorRevision]);
  const dirty = JSON.stringify({
    ...fields,
    document: currentDocument,
  }) !== JSON.stringify({
    name: station.name,
    max_kids: String(station.max_kids),
    meeting_point: station.meeting_point,
    wishes: station.wishes,
    responsible_profile_id: station.responsible?.id ? String(station.responsible.id) : '',
    document: initialDocument,
  });
  const save = async () => {
    const capacity = Number(fields.max_kids);
    const assignedCount = station.assigned_count || 0;
    const overbookedCount = Math.max(assignedCount - capacity, 0);
    let overbookingConfirmation;
    if (!creating && overbookedCount > 0) {
      if (!globalThis.confirm?.(
        `Die Station wäre ${overbookedCount} überbelegt. Kapazität trotzdem speichern?`,
      )) return false;
      overbookingConfirmation = {
        capacity,
        assigned_count: assignedCount,
        station_version: station.version,
      };
    }
    const url = creating
      ? `/api/happy-cleaning/events/${event.id}/stations/create/`
      : `/api/happy-cleaning/events/${event.id}/stations/${station.id}/update/`;
    const payload = {
      request_id: commandRequestId.current,
      ...(creating
        ? { expected_revision: event.revision }
        : { expected_version: station.version }),
      ...fields,
      max_kids: capacity,
      ...(overbookingConfirmation ? {
        overbooking_confirmation: overbookingConfirmation,
      } : {}),
      responsible_profile_id: fields.responsible_profile_id
        ? Number(fields.responsible_profile_id)
        : null,
      document: currentDocument,
    };
    setBusy(true);
    setError('');
    try {
      const result = await mutate(url, payload);
      await onSaved?.(result);
      return true;
    } catch (caught) {
      const confirmation = caught?.payload?.confirmation;
      if (
        caught?.payload?.code === 'overbooking_confirmation_required'
        && confirmation
        && globalThis.confirm?.(
          `Die Einteilung hat sich geändert: ${confirmation.overbooked_count} überbelegt. Trotzdem speichern?`,
        )
      ) {
        try {
          const result = await mutate(url, {
            ...payload,
            expected_version: confirmation.station_version,
            overbooking_confirmation: {
              capacity: confirmation.capacity,
              assigned_count: confirmation.assigned_count,
              station_version: confirmation.station_version,
            },
          });
          await onSaved?.(result);
          return true;
        } catch (retryError) {
          setError(errorMessage(retryError));
          return false;
        }
      }
      setError(errorMessage(caught));
      return false;
    } finally {
      setBusy(false);
    }
  };
  const navigate = destination => {
    if (!destination) return;
    if (!dirty) destination();
    else setPendingNavigation(() => destination);
  };
  useEffect(() => {
    registerNavigationGuard?.(navigate);
    return () => registerNavigationGuard?.(null);
  }, [registerNavigationGuard, dirty, editorRevision]);
  useEffect(() => {
    const keydown = event => {
      if (event.key === 'Escape') navigate(onBack);
    };
    document.addEventListener('keydown', keydown);
    return () => document.removeEventListener('keydown', keydown);
  });
  const remove = async () => {
    if (!globalThis.confirm?.(`Station ${station.name} wirklich löschen?`)) return;
    setBusy(true);
    setError('');
    try {
      await mutate(
        `/api/happy-cleaning/events/${event.id}/stations/${station.id}/delete/`,
        { request_id: requestId(), expected_version: station.version },
        true,
        false,
      );
      onDeleted?.(station.id);
    } catch (caught) {
      setError(errorMessage(caught));
      setBusy(false);
    }
  };
  return (
    <>
      <div className="react-actions">
        <button type="button" className="button" onClick={() => navigate(onBack)}>Zur Liste</button>
        <button type="button" className="button" aria-label="Detail schließen" onClick={() => navigate(onBack)}>×</button>
      </div>
      <form className="form-grid" onSubmit={async event_ => { event_.preventDefault(); await save(); }}>
        <label>Name<input aria-label="Name der Station" value={fields.name} onChange={event_ => setFields(value => ({ ...value, name: event_.target.value }))} /></label>
        <label>Kapazität<input aria-label="Kapazität der Station" type="number" min="1" required value={fields.max_kids} onChange={event_ => setFields(value => ({ ...value, max_kids: event_.target.value }))} /></label>
        <label>Treffpunkt<input aria-label="Treffpunkt der Station" value={fields.meeting_point} onChange={event_ => setFields(value => ({ ...value, meeting_point: event_.target.value }))} /></label>
        <label>Wünsche<textarea aria-label="Wünsche der Station" value={fields.wishes} onChange={event_ => setFields(value => ({ ...value, wishes: event_.target.value }))} /></label>
        <label>Hauptverantwortlich<select aria-label="Hauptverantwortlich" value={fields.responsible_profile_id} onChange={event_ => setFields(value => ({ ...value, responsible_profile_id: event_.target.value }))}>
          <option value="">Niemand</option>
          {(data.responsible_profiles || []).map(profile => <option key={profile.id} value={profile.id}>{profile.name}</option>)}
        </select></label>
        <div className="happy-cleaning-minimal-editor" ref={editorContainer}>
          <EditorContent editor={editor} />
        </div>
        {error && <p className="error" role="alert">{error}</p>}
        <div className="react-actions">
          <button className="button" type="submit" disabled={busy}>Speichern</button>
          {!creating && station.can_delete && <button className="button danger" type="button" disabled={busy} onClick={remove}>Station löschen</button>}
        </div>
      </form>
      {pendingNavigation && (
        <DirtyNavigationDialog
          onContinue={() => setPendingNavigation(null)}
          onDiscard={() => pendingNavigation()}
          onSave={async () => { if (await save()) pendingNavigation(); }}
        />
      )}
    </>
  );
}

export function HappyCleaningStationDetailPage({
  data,
  mutate,
  realtimeSync,
  embedded = false,
  onBack,
  refresh,
  onDeleted,
  registerNavigationGuard,
  initialEditing = false,
  onCopySuccess,
}) {
  const { event, station } = data;
  const [showCompleted, setShowCompleted] = useState(true);
  const [busyTodoIds, setBusyTodoIds] = useState(() => new Set());
  const [error, setError] = useState('');
  const [editing, setEditing] = useState(initialEditing);
  const [copyOpen, setCopyOpen] = useState(false);
  const writesBlocked = realtimeSync?.enabled && !realtimeSync.writesEnabled;
  const orderedTodos = [...station.todos].sort((left, right) => (
    left.position - right.position || left.id - right.id
  ));
  const visibleTodos = showCompleted
    ? orderedTodos
    : orderedTodos.filter(todo => !todo.checked);

  const setTodoState = async todo => {
    setBusyTodoIds(current => new Set(current).add(todo.id));
    setError('');
    const operation = todo.checked ? 'reopen' : 'check';
    try {
      await mutate(
        `/api/happy-cleaning/events/${event.id}/stations/${station.id}/todos/${todo.id}/${operation}/`,
        {
          request_id: requestId(),
          expected_version: todo.version,
        },
      );
    } catch (caught) {
      setError(errorMessage(caught));
      if (caught?.payload?.code === 'stale') await refresh?.();
    } finally {
      setBusyTodoIds(current => {
        const next = new Set(current);
        next.delete(todo.id);
        return next;
      });
    }
  };

  const Page = embedded ? 'section' : 'main';
  return (
    <Page className="happy-cleaning-station-detail-page" id={embedded ? undefined : 'body-container'}>
      {editing ? (
        <StationEditor
          data={data}
          mutate={mutate}
          onSaved={async result => {
            await refresh?.(result);
            setEditing(false);
          }}
          onDeleted={onDeleted}
          registerNavigationGuard={registerNavigationGuard}
          onBack={onBack}
        />
      ) : (
      <>
      {onBack && <button className="button happy-cleaning-detail-back" type="button" onClick={onBack}>Zur Liste</button>}
      <section className="card happy-cleaning-station-detail-card">
        <div className="happy-cleaning-station-detail-heading">
          <h1>{station.name}</h1>
          <Progress station={station} />
        </div>
        {station.can_edit && <button className="button" type="button" onClick={() => setEditing(true)}>Bearbeiten</button>}
        {station.id != null && (
          <button className="button" type="button" onClick={() => setCopyOpen(true)}>
            Station kopieren
          </button>
        )}
        <dl className="happy-cleaning-station-facts">
          <div><dt>Max Kinder</dt><dd>{station.max_kids}</dd></div>
          <div><dt>Plätze</dt><dd>{capacityLabel(station)}</dd></div>
          <div><dt>Treffpunkt</dt><dd>{station.meeting_point || '—'}</dd></div>
          <div><dt>Wünsche</dt><dd>{station.wishes || '—'}</dd></div>
          {station.responsible && (
            <div><dt>Hauptverantwortlich</dt><dd>{station.responsible.name}</dd></div>
          )}
        </dl>
        {station.content?.some(block => block.type === 'paragraph') && (
          <section aria-labelledby={`station-content-${station.id}`}>
            <h2 id={`station-content-${station.id}`}>Inhalt</h2>
            {station.content
              .filter(block => block.type === 'paragraph')
              .map((block, index) => <p key={index}>{block.text || '\u00a0'}</p>)}
          </section>
        )}

        {station.children && (
          <>
            <h2>Eingeteilte Kinder</h2>
            {!station.children.length && <p>Noch keine Kinder eingeteilt.</p>}
            {station.children.length > 0 && (
              <ul className="happy-cleaning-detail-children">
                {station.children.map(child => <li key={child.id}>{child.full_name}</li>)}
              </ul>
            )}
          </>
        )}

        <div className="happy-cleaning-checklist-heading">
          <h2>Aufgaben</h2>
          <label>
            <input
              type="checkbox"
              checked={showCompleted}
              onChange={change => setShowCompleted(change.target.checked)}
            />
            Erledigte Aufgaben anzeigen
          </label>
        </div>
        {error && <p className="error" role="alert">{error}</p>}
        {!orderedTodos.length && <p>Noch keine Aufgabe angelegt.</p>}
        {orderedTodos.length > 0 && !visibleTodos.length && (
          <p>Alle Aufgaben sind erledigt.</p>
        )}
        <ol className="happy-cleaning-detail-todos">
          {visibleTodos.map(todo => (
            <li
              key={todo.id}
              aria-label={`Aufgabe ${todo.text}`}
              className={todo.checked ? 'completed' : ''}
            >
              <span>{todo.text}</span>
              {station.can_toggle_tasks && (
                <button
                  className="button"
                  type="button"
                  disabled={writesBlocked || busyTodoIds.has(todo.id)}
                  aria-label={todo.checked
                    ? `${todo.text} wieder öffnen`
                    : `${todo.text} erledigen`}
                  onClick={() => setTodoState(todo)}
                >
                  {todo.checked ? 'Wieder öffnen' : 'Erledigt'}
                </button>
              )}
            </li>
          ))}
        </ol>
      </section>
      {copyOpen && (
        <SingleStationCopyDialog
          source={event}
          station={station}
          targets={data.copy_targets || []}
          mutate={mutate}
          close={() => setCopyOpen(false)}
          onSuccess={onCopySuccess}
        />
      )}
      </>
      )}
    </Page>
  );
}

export const happyCleaningStationDetailRoutes = [{
  pattern: /^\/happy-cleaning\/(\d+)\/stations\/(\d+)$/,
  page: 'happy-cleaning-station-detail',
  title: 'Happy Cleaning Station',
  domain: 'happy-cleaning',
  readContractKey: 'happy-cleaning-station-detail',
  params: match => ({ event_id: match[1], station_id: match[2] }),
  resolveTitle: (_route, data) => data.station?.name || 'Happy Cleaning Station',
  render: ({ data, mutate, realtimeSync, refresh }) => (
    <HappyCleaningStationDetailPage
      data={data}
      mutate={mutate}
      realtimeSync={realtimeSync}
      refresh={refresh}
    />
  ),
}];
