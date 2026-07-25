import { useState } from 'react';

const requestId = () => globalThis.crypto?.randomUUID?.()
  || `happy-cleaning-copy-${Date.now()}-${Math.random().toString(36).slice(2)}`;

const errorMessage = error => {
  const errors = error?.payload?.errors;
  if (errors) return Object.values(errors).flat().join(' ');
  if (error?.payload?.code === 'stale') {
    return 'Die Daten wurden inzwischen geändert. Bitte neu laden.';
  }
  return error?.message || 'Die Station konnte nicht kopiert werden.';
};

export function ConflictResolution({ preview, decisions, setDecisions }) {
  const groups = Object.values(preview.conflicts.reduce((all, conflict) => {
    (all[conflict.source_station_id] ||= {
      id: conflict.source_station_id,
      name: conflict.source_name,
      taskCount: conflict.source_task_count,
      candidates: [],
    }).candidates.push(conflict);
    return all;
  }, {}));
  const choose = (id, patch) => setDecisions(current => ({
    ...current, [id]: { ...(current[id] || {}), ...patch },
  }));
  return <div className="happy-cleaning-conflict-resolution">
    {!!preview.conflict_free_station_ids?.length && <p>{preview.conflict_free_station_ids.length} konfliktfreie Station(en) werden ebenfalls kopiert.</p>}
    <p role="status">{groups.filter(group => !decisions[group.id]?.action).length} Konfliktgruppe(n) ungelöst.</p>
    {groups.map(group => {
      const decision = decisions[group.id] || {};
      const candidate = group.candidates.find(item => item.target_station_id === Number(decision.target_station_id));
      return <fieldset className="happy-cleaning-conflict-card" key={group.id}>
        <legend>{group.name} ({group.taskCount ?? 0} Aufgaben)</legend>
        <p className="happy-cleaning-conflict-summary">
          {group.candidates.map(item => `${group.name} → ${item.target_name}`).join(', ')}
        </p>
        <label>Bestehende Station
          <select aria-label={`Bestehende Station für ${group.name}`} value={decision.target_station_id || ''} onChange={event => choose(group.id, { target_station_id: Number(event.target.value) || null, action: null })}>
            <option value="">Bitte wählen</option>
            {group.candidates.map(item => <option key={item.target_station_id} value={item.target_station_id}>{item.target_name} ({item.target_task_count ?? 0} Aufgaben)</option>)}
          </select>
        </label>
        <div className="happy-cleaning-conflict-actions">
          {[
            ['overwrite', 'Bestehende Station überschreiben'],
            ['append', 'Inhalte anhängen'],
            ['separate', 'Als eigene Station kopieren'],
            ['skip', 'Überspringen'],
          ].map(([value, label]) => {
            const targetRequired = value === 'overwrite' || value === 'append';
            const locked = value === 'overwrite' && candidate && !candidate.overwrite_eligible;
            return <label className="happy-cleaning-conflict-action" key={value}>
              <input type="radio" name={`resolution-${group.id}`} checked={decision.action === value} disabled={(targetRequired && !candidate) || locked} onChange={() => choose(group.id, { action: value })} />
              <span>{label}</span>
              {locked && <small>{candidate.overwrite_disabled_reason}</small>}
            </label>;
          })}
        </div>
      </fieldset>;
    })}
  </div>;
}

function StationCopyDialog({
  source,
  targets,
  mutate,
  close,
  onSuccess,
  workflow,
}) {
  const [stationIds, setStationIds] = useState(workflow.stationIds);
  const [targetId, setTargetId] = useState('');
  const [state, setState] = useState({ kind: 'ready' });
  const [decisions, setDecisions] = useState({});
  const availableTargets = targets.filter(target => target.id !== source.id);
  const selectedAll = workflow.showSelection && source.stations.length > 0
    && stationIds.length === source.stations.length;
  const toggle = stationId => {
    setState({ kind: 'ready' });
    setDecisions({});
    setStationIds(current => (
      current.includes(stationId)
        ? current.filter(id => id !== stationId)
        : [...current, stationId]
    ));
  };
  const submit = async (forcePreview = false) => {
    const target = availableTargets.find(item => String(item.id) === targetId);
    if (!target) return;
    setState({ kind: 'busy' });
    try {
      const preview = !forcePreview && state.kind === 'conflicts' ? state.result : null;
      const result = await mutate(
        workflow.url(target),
        {
          request_id: requestId(),
          expected_revision: preview?.target_revision ?? target.revision,
          ...workflow.sourcePayload({ preview, source, stationIds }),
          ...(preview ? { resolutions: Object.entries(decisions).map(([id, decision]) => ({
            source_station_id: Number(id),
            action: decision.action,
            target_station_id: ['overwrite', 'append'].includes(decision.action) ? Number(decision.target_station_id) : null,
          })) } : {}),
        },
      );
      if (result.result === 'conflicts') {
        setState({ kind: 'conflicts', result });
      } else {
        const count = result.affected_stations?.length
          ?? result.copied_stations?.length
          ?? stationIds.length - (result.result_counts?.skipped || 0);
        setState({ kind: 'success', count });
        onSuccess?.(target.id, result);
      }
    } catch (caught) {
      setState({ kind: 'error', message: errorMessage(caught) });
    }
  };
  return (
    <section className="card happy-cleaning-copy" role="dialog" aria-modal="true" aria-label={workflow.title}>
      <h2>{workflow.title}</h2>
      <p>Quelle: {workflow.sourceLabel(source)}</p>
      {workflow.showSelection && <>
        <label>
          <input
            type="checkbox"
            aria-label="Alle Stationen auswählen"
            checked={selectedAll}
            onChange={() => { setState({ kind: 'ready' }); setDecisions({}); setStationIds(selectedAll ? [] : source.stations.map(station => station.id)); }}
          />
          Alle auswählen
        </label>
        <div>
          {source.stations.map(station => (
            <label key={station.id}>
              <input
                type="checkbox"
                aria-label={`Station ${station.name} auswählen`}
                checked={stationIds.includes(station.id)}
                onChange={() => toggle(station.id)}
              />
              {station.name}
            </label>
          ))}
        </div>
      </>}
      <label>
        Ziel-Happy-Cleaning
        <select aria-label="Ziel-Happy-Cleaning" value={targetId} onChange={event => { setState({ kind: 'ready' }); setDecisions({}); setTargetId(event.target.value); }}>
          <option value="">Bitte wählen</option>
          {availableTargets.map(target => (
            <option key={target.id} value={target.id}>{target.label}</option>
          ))}
        </select>
      </label>
      {state.kind === 'busy' && (
        <p role="status">
          <span className="happy-cleaning-copy-spinner" aria-hidden="true" />
          Stationen werden geprüft…
        </p>
      )}
      {state.kind === 'success' && <p role="status">{workflow.successMessage(state.count)}</p>}
      {state.kind === 'conflicts' && (
        <div role="alert">
          <p>Ähnliche Stationen gefunden (Zielversion {state.result.target_revision}):</p>
          <ConflictResolution preview={state.result} decisions={decisions} setDecisions={setDecisions} />
        </div>
      )}
      {state.kind === 'error' && <p className="error" role="alert">{state.message}</p>}
      <div className="react-actions">
        <button
          className="button"
          type="button"
          disabled={state.kind === 'busy' || !stationIds.length || !targetId || (
            state.kind === 'conflicts'
            && new Set(state.result.conflicts.map(item => item.source_station_id)).size !== Object.values(decisions).filter(item => item.action).length
          )}
          onClick={submit}
        >
          {state.kind === 'conflicts' ? 'Auswahl verbindlich kopieren' : state.kind === 'error' ? 'Erneut prüfen' : 'Prüfen und kopieren'}
        </button>
        {state.kind === 'conflicts' && <button className="button" type="button" onClick={() => { setDecisions({}); submit(true); }}>Erneut prüfen</button>}
        <button className="button" type="button" disabled={state.kind === 'busy'} onClick={close}>Schließen</button>
      </div>
    </section>
  );
}

export function BulkStationCopyDialog(props) {
  return <StationCopyDialog {...props} workflow={{
    title: 'Stationen kopieren',
    stationIds: [],
    showSelection: true,
    sourceLabel: source => `Happy Cleaning ${source.display_number}`,
    url: target => `/api/happy-cleaning/events/${target.id}/stations/copy/`,
    sourcePayload: ({ preview, source, stationIds }) => ({
      source_event_id: preview?.source_event_id ?? source.id,
      station_ids: preview?.station_ids ?? stationIds,
    }),
    successMessage: count => `${count} Stationen wurden kopiert.`,
  }} />;
}

export function SingleStationCopyDialog({ station, ...props }) {
  return <StationCopyDialog {...props} workflow={{
    title: 'Station kopieren',
    stationIds: [station.id],
    showSelection: false,
    sourceLabel: () => station.name,
    url: target => `/api/happy-cleaning/events/${target.id}/stations/copy/${station.id}/`,
    sourcePayload: () => ({}),
    successMessage: () => 'Station wurde kopiert.',
  }} />;
}
