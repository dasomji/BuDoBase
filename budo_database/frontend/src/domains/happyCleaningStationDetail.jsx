import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Dialog } from '@base-ui/react/dialog';
import { EditorContent, useEditor } from '@tiptap/react';
import Document from '@tiptap/extension-document';
import Paragraph from '@tiptap/extension-paragraph';
import Text from '@tiptap/extension-text';
import TaskList from '@tiptap/extension-task-list';
import TaskItem from '@tiptap/extension-task-item';

import { Card } from '../components';
import { useErrorToast } from '../components/ui/toast';
import './happyCleaningStationDetail.css';
import { SingleStationCopyDialog } from './happyCleaningCopy';

const TaskItemWithIdentity = TaskItem.extend({
  addAttributes() {
    return {
      ...this.parent?.(),
      id: {
        default: null,
        keepOnSplit: false,
        parseHTML: element => {
          const value = Number(element.getAttribute('data-task-id'));
          return Number.isSafeInteger(value) && value > 0 ? value : null;
        },
        renderHTML: attributes => attributes.id == null
          ? {}
          : { 'data-task-id': attributes.id },
      },
      version: {
        default: null,
        keepOnSplit: false,
        parseHTML: element => {
          const value = Number(element.getAttribute('data-task-version'));
          return Number.isSafeInteger(value) && value > 0 ? value : null;
        },
        renderHTML: attributes => attributes.version == null
          ? {}
          : { 'data-task-version': attributes.version },
      },
    };
  },
});

export const StableTaskItem = TaskItemWithIdentity.extend({
  addNodeView() {
    const createNodeView = this.parent?.();
    return props => {
      const nodeView = createNodeView(props);
      const checkbox = nodeView.dom.querySelector('input[type="checkbox"]');
      checkbox.disabled = true;
      checkbox.tabIndex = -1;
      checkbox.setAttribute(
        'aria-label',
        'Aufgabenstatus wird beim Bearbeiten nicht geändert',
      );
      return nodeView;
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

const taskActionLabel = node => {
  const text = node.textContent.trim() || 'Aufgabe';
  return node.attrs.checked ? `${text} wieder öffnen` : `${text} erledigen`;
};

function ReadOnlyStationDocument({
  document: stationDocument,
  canToggle,
  writesBlocked,
  busyTodoIds,
  onToggle,
}) {
  const document = stationDocument || { type: 'doc', content: [] };
  const documentSignature = JSON.stringify(document);
  const documentRoot = useRef(null);
  const interaction = useRef();
  interaction.current = {
    canToggle,
    writesBlocked,
    busyTodoIds,
    onToggle,
  };
  const editor = useEditor({
    editable: false,
    extensions: [
      Document,
      Paragraph,
      Text,
      TaskList,
      TaskItemWithIdentity.configure({
        nested: false,
        a11y: { checkboxLabel: taskActionLabel },
        onReadOnlyChecked: (node, checked) => {
          const current = interaction.current;
          const taskId = String(node.attrs.id);
          if (
            !current.canToggle
            || current.writesBlocked
            || current.busyTodoIds.has(taskId)
            || node.attrs.id == null
            || node.attrs.version == null
            || checked === node.attrs.checked
          ) return false;
          current.onToggle?.({
            id: node.attrs.id,
            version: node.attrs.version,
            checked: node.attrs.checked,
          });
          return false;
        },
      }),
    ],
    content: document,
    editorProps: {
      attributes: { 'aria-label': 'Stationsinhalt' },
    },
  }, [documentSignature]);

  useEffect(() => {
    if (!documentRoot.current) return;
    const disabledForAll = !canToggle || writesBlocked;
    documentRoot.current.querySelectorAll('li[data-task-id]').forEach(taskItem => {
      const checkbox = taskItem.querySelector(':scope > label input[type="checkbox"]');
      if (!checkbox) return;
      const disabled = disabledForAll || busyTodoIds.has(taskItem.dataset.taskId);
      checkbox.disabled = disabled;
      if (disabled) checkbox.tabIndex = -1;
      else checkbox.removeAttribute('tabindex');
    });
  }, [editor, canToggle, writesBlocked, busyTodoIds, documentSignature]);

  if (!document.content?.length) return <p>Noch kein Inhalt angelegt.</p>;
  return (
    <div className="happy-cleaning-readonly-document" ref={documentRoot}>
      <EditorContent editor={editor} />
    </div>
  );
}

function DirtyNavigationDialog({ onContinue, onDiscard, onSave }) {
  return (
    <Dialog.Root open onOpenChange={open => { if (!open) onContinue(); }}>
      <Dialog.Portal>
        <Dialog.Backdrop className="happy-cleaning-dialog-backdrop" />
        <Dialog.Viewport className="happy-cleaning-dialog-viewport">
          <Dialog.Popup className="card happy-cleaning-dirty-dialog">
            <Dialog.Title>Ungespeicherte Änderungen</Dialog.Title>
            <Dialog.Description>Es gibt ungespeicherte Änderungen.</Dialog.Description>
            <div className="react-actions">
              <button className="button" type="button" onClick={onContinue}>Weiter bearbeiten</button>
              <button className="button" type="button" onClick={onDiscard}>Verwerfen</button>
              <button className="button" type="button" onClick={onSave}>Speichern und weiter</button>
            </div>
          </Dialog.Popup>
        </Dialog.Viewport>
      </Dialog.Portal>
    </Dialog.Root>
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
  const [busy, setBusy] = useState(false);
  const [editorRevision, setEditorRevision] = useState(0);
  const showError = useErrorToast();
  const tasksLabelId = `station-editor-tasks-${station.id ?? 'new'}`;
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
      attributes: { 'aria-labelledby': tasksLabelId },
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
          showError(errorMessage(retryError));
          return false;
        }
      }
      showError(errorMessage(caught));
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
    try {
      await mutate(
        `/api/happy-cleaning/events/${event.id}/stations/${station.id}/delete/`,
        { request_id: requestId(), expected_version: station.version },
        true,
        false,
      );
      onDeleted?.(station.id);
    } catch (caught) {
      showError(errorMessage(caught));
      setBusy(false);
    }
  };
  return (
    <>
      <div className="react-actions">
        <button type="button" className="button happy-cleaning-detail-back" onClick={() => navigate(onBack)}>Zur Liste</button>
      </div>
      <form className="form-grid" onSubmit={async event_ => { event_.preventDefault(); await save(); }}>
        <label>Name<input aria-label="Name der Station" value={fields.name} onChange={event_ => setFields(value => ({ ...value, name: event_.target.value }))} /></label>
        <label>Verantwortlich<select aria-label="Verantwortlich" value={fields.responsible_profile_id} onChange={event_ => setFields(value => ({ ...value, responsible_profile_id: event_.target.value }))}>
          <option value="">Niemand</option>
          {(data.responsible_profiles || []).map(profile => <option key={profile.id} value={profile.id}>{profile.name}</option>)}
        </select></label>
        <label>Kapazität<input aria-label="Kapazität der Station" type="number" min="0" required value={fields.max_kids} onChange={event_ => setFields(value => ({ ...value, max_kids: event_.target.value }))} /></label>
        <label>Treffpunkt<input aria-label="Treffpunkt der Station" value={fields.meeting_point} onChange={event_ => setFields(value => ({ ...value, meeting_point: event_.target.value }))} /></label>
        <label>Wünsche<textarea aria-label="Wünsche der Station" value={fields.wishes} onChange={event_ => setFields(value => ({ ...value, wishes: event_.target.value }))} /></label>
        <div className="happy-cleaning-minimal-editor-field" role="group" aria-labelledby={tasksLabelId}>
          <span id={tasksLabelId}>Aufgaben</span>
          <div className="happy-cleaning-minimal-editor">
            <EditorContent editor={editor} />
          </div>
        </div>
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
  const [busyTodoIds, setBusyTodoIds] = useState(() => new Set());
  const [editing, setEditing] = useState(initialEditing);
  const showError = useErrorToast();
  const [copyOpen, setCopyOpen] = useState(false);
  const navigationGuard = useRef(null);
  const writesBlocked = realtimeSync?.enabled && !realtimeSync.writesEnabled;
  const registerDetailNavigationGuard = useCallback(guard => {
    navigationGuard.current = guard;
    registerNavigationGuard?.(guard);
  }, [registerNavigationGuard]);
  const closeDetail = () => {
    if (!onBack) return;
    if (editing && navigationGuard.current) navigationGuard.current(onBack);
    else onBack();
  };

  const setTodoState = async todo => {
    const taskId = String(todo.id);
    setBusyTodoIds(current => new Set(current).add(taskId));
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
      showError(errorMessage(caught));
      if (caught?.payload?.code === 'stale') await refresh?.();
    } finally {
      setBusyTodoIds(current => {
        const next = new Set(current);
        next.delete(taskId);
        return next;
      });
    }
  };

  const Page = embedded ? 'section' : 'main';
  return (
    <Page className="happy-cleaning-station-detail-page" id={embedded ? undefined : 'body-container'}>
      {!editing && onBack && (
        <button className="button happy-cleaning-detail-back" type="button" onClick={onBack}>
          Zur Liste
        </button>
      )}
      <Card
        className="happy-cleaning-station-detail-card"
        title={station.name}
        showToggleIcon={false}
        headerAction={onBack ? (
          <button
            className="button happy-cleaning-detail-close"
            type="button"
            aria-label="Detail schließen"
            onClick={closeDetail}
          >
            ×
          </button>
        ) : null}
      >
        {editing ? (
          <StationEditor
            data={data}
            mutate={mutate}
            onSaved={async result => {
              await refresh?.(result);
              setEditing(false);
            }}
            onDeleted={onDeleted}
            registerNavigationGuard={registerDetailNavigationGuard}
            onBack={onBack}
          />
        ) : (
          <>
            <dl className="happy-cleaning-station-facts">
              {station.responsible && (
                <div><dt>Hauptverantwortlich</dt><dd>{station.responsible.name}</dd></div>
              )}
              <div><dt>Max Kinder</dt><dd>{station.max_kids}</dd></div>
              <div><dt>Treffpunkt</dt><dd>{station.meeting_point || '—'}</dd></div>
              <div><dt>Wünsche</dt><dd>{station.wishes || '—'}</dd></div>
            </dl>
            <section aria-labelledby={`station-tasks-${station.id}`}>
              <h2 className="happy-cleaning-station-tasks-heading" id={`station-tasks-${station.id}`}>Aufgaben</h2>
              <ReadOnlyStationDocument
                document={station.document}
                canToggle={station.can_toggle_tasks}
                writesBlocked={writesBlocked}
                busyTodoIds={busyTodoIds}
                onToggle={setTodoState}
              />
            </section>
            <div className="react-actions happy-cleaning-detail-actions">
              {station.can_edit && (
                <button className="button" type="button" onClick={() => setEditing(true)}>
                  Bearbeiten
                </button>
              )}
              {station.id != null && (
                <button className="button" type="button" onClick={() => setCopyOpen(true)}>
                  Station kopieren
                </button>
              )}
            </div>
          </>
        )}
      </Card>
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
    </Page>
  );
}
