import { Fragment, useEffect, useState } from 'react';

import {
  Card,
  Column,
  Columns,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
  TableScroll,
} from '../components';
import { Button } from '../components/ui/button';
import { useErrorToast } from '../components/ui/toast';


function queryUrl(filters, page, pageSize, snapshotId) {
  const params = new URLSearchParams();
  Object.entries(filters || {}).forEach(([key, value]) => {
    if (value) params.set(key, value);
  });
  if (page > 1) params.set('page', String(page));
  if (pageSize && pageSize !== 50) params.set('page_size', String(pageSize));
  if (snapshotId !== undefined && snapshotId !== null) {
    params.set('snapshot_id', String(snapshotId));
  }
  const query = params.toString();
  return `/audit/${query ? `?${query}` : ''}`;
}

function FilterField({ label, name, value, children, type = 'text' }) {
  return (
    <label>
      <span>{label}</span>
      {children || <input type={type} name={name} defaultValue={value || ''} />}
    </label>
  );
}

function AuditFilters({ data }) {
  const { filters = {}, filter_options: options = {} } = data;
  return (
    <form action="/audit/" method="get" className="form-grid grid-cols-[repeat(auto-fit,minmax(11.25rem,1fr))] items-end">
      <FilterField label="Turnus" name="turnus">
        <select name="turnus" defaultValue={filters.turnus || ''}>
          {(options.turnuses || []).map(turnus => (
            <option key={turnus.id} value={turnus.id}>{turnus.label}</option>
          ))}
        </select>
      </FilterField>
      <FilterField label="Von" name="from" type="datetime-local" value={filters.from} />
      <FilterField label="Bis" name="to" type="datetime-local" value={filters.to} />
      <FilterField label="Akteur:in" name="actor" value={filters.actor} />
      <FilterField label="Aktion" name="action">
        <select name="action" defaultValue={filters.action || ''}>
          <option value="">Alle</option>
          {(options.actions || []).map(value => (
            <option key={value} value={value} label={value} />
          ))}
        </select>
      </FilterField>
      <FilterField label="Ergebnis" name="outcome">
        <select name="outcome" defaultValue={filters.outcome || ''}>
          <option value="">Alle</option>
          {(options.outcomes || []).map(value => <option key={value}>{value}</option>)}
        </select>
      </FilterField>
      <FilterField label="Ressourcentyp" name="resource_type">
        <select name="resource_type" defaultValue={filters.resource_type || ''}>
          <option value="">Alle</option>
          {(options.resource_types || []).map(value => <option key={value}>{value}</option>)}
        </select>
      </FilterField>
      <FilterField label="Ressourcen-ID" name="resource_id" value={filters.resource_id} />
      <div className="mt-3 flex flex-wrap gap-2">
        <Button type="submit">Filtern</Button>
        <Button href="/audit/" variant="secondary">Zurücksetzen</Button>
      </div>
    </form>
  );
}

const MAX_SUMMARY_FIELDS = 12;
const MAX_SUMMARY_FIELD_LENGTH = 64;

function auditDetailsSummary(summary) {
  if (summary?.sensitive === true && Array.isArray(summary.changed_paths)) {
    return `${summary.changed_paths.length} geänderte Pfade`;
  }
  if (summary?.sensitive === false && Array.isArray(summary.available_fields)) {
    const fields = summary.available_fields
      .filter(field => typeof field === 'string')
      .slice(0, MAX_SUMMARY_FIELDS)
      .map(field => field.slice(0, MAX_SUMMARY_FIELD_LENGTH));
    return fields.length ? fields.join(', ') : 'Keine Detailfelder verfügbar';
  }
  return 'Keine Zusammenfassung verfügbar';
}

const DETAIL_GROUPS = [
  ['Allgemein', ['first_name', 'last_name', 'sex', 'birthday', 'stay_weeks', 'siblings', 'tent_request', 'budo_experience']],
  ['Gesundheitsinfos', ['social_security_number', 'illness', 'drugs', 'vegetarian', 'special_food', 'swimmer', 'consent', 'over_the_counter_medication', 'prescription_medication', 'tetanus', 'tick_vaccine']],
  ['Familie', ['organization', 'registrant_first_name', 'registrant_last_name', 'registrant_email', 'registrant_phone', 'insured_with', 'emergency_contacts', 'budo_family']],
];

const MAX_DETAIL_TEXT = 10_000;
const boundedText = value => {
  if (value === null || value === undefined || value === '') return '—';
  if (value === true) return 'Ja';
  if (value === false) return 'Nein';
  return String(value).slice(0, MAX_DETAIL_TEXT);
};

function BeforeAfter({ label, before, after }) {
  return (
    <div className="rounded-lg border border-border p-2">
      <h3 className="font-medium">{label}</h3>
      <div className="grid gap-2 min-[901px]:grid-cols-2">
        <div><strong>Vorher</strong><p className="whitespace-pre-wrap break-words">{boundedText(before)}</p></div>
        <div><strong>Nachher</strong><p className="whitespace-pre-wrap break-words">{boundedText(after)}</p></div>
      </div>
    </div>
  );
}

function relationshipText(item, kind) {
  if (!item) return '—';
  if (kind === 'swp') {
    const names = (item.focuses || []).map(focus => boundedText(focus.label));
    return names.length ? names.join(', ') : 'Nicht eingeteilt';
  }
  if (item.target?.kind === 'station') return boundedText(item.target.station_label);
  if (item.target?.kind === 'excused') return 'Entschuldigt';
  return 'Nicht eingeteilt';
}

function RelationshipGroup({ title, kind, before, after, changedPaths }) {
  const [showUnchanged, setShowUnchanged] = useState(false);
  const idName = kind === 'swp' ? 'period_id' : 'event_id';
  const labelName = kind === 'swp' ? 'period_label' : 'event_label';
  const prefix = kind === 'swp' ? 'swp.' : 'happy_cleaning.';
  const beforeById = Object.fromEntries((before || []).map(item => [item[idName], item]));
  const afterById = Object.fromEntries((after || []).map(item => [item[idName], item]));
  const ids = [...new Set([...Object.keys(beforeById), ...Object.keys(afterById)])];
  const changed = ids.filter(id => changedPaths.includes(`${prefix}${id}`));
  const unchanged = ids.filter(id => !changed.includes(id));
  const visible = showUnchanged ? ids : changed;
  return (
    <section className="grid gap-2" aria-label={title}>
      <h2>{title}</h2>
      {visible.map(id => (
        <BeforeAfter
          key={id}
          label={boundedText(afterById[id]?.[labelName] ?? beforeById[id]?.[labelName])}
          before={relationshipText(beforeById[id], kind)}
          after={relationshipText(afterById[id], kind)}
        />
      ))}
      {!showUnchanged && unchanged.length ? (
        <Button type="button" variant="secondary" onClick={() => setShowUnchanged(true)}>
          {unchanged.length} unveränderte Werte anzeigen
        </Button>
      ) : null}
    </section>
  );
}

function SensitiveDetail({ event }) {
  const details = event.details;
  const before = details.before;
  const after = details.after;
  return (
    <div className="grid gap-4 py-2" aria-label={`Sensible Details für Ereignis ${event.id}`}>
      {DETAIL_GROUPS.map(([title, fields]) => (
        <section className="grid gap-2" key={title} aria-label={title}>
          <h2>{title}</h2>
          {fields.map(field => (
            <BeforeAfter key={field} label={field} before={before.fields[field]} after={after.fields[field]} />
          ))}
        </section>
      ))}
      <RelationshipGroup title="SWP" kind="swp" before={before.swp} after={after.swp} changedPaths={details.changed_paths} />
      <RelationshipGroup title="Happy Cleaning" kind="happy_cleaning" before={before.happy_cleaning} after={after.happy_cleaning} changedPaths={details.changed_paths} />
    </div>
  );
}

function RevealWarning({ cancel, confirm }) {
  return (
    <div className="fixed inset-0 z-[var(--z-modal)] grid place-items-center bg-black/45 p-6">
      <section className="card w-full max-w-[34rem] bg-surface-solid p-6" role="alertdialog" aria-modal="true" aria-labelledby="audit-warning-title">
        <h2 id="audit-warning-title">Sensible Audit-Details laden?</h2>
        <p>Die Details können Gesundheit, Medikamente, Sozialversicherungsdaten, Familie, Telefon, E-Mail, Notfallkontakte und Zuteilungen enthalten.</p>
        <div className="mt-4 flex flex-wrap justify-end gap-2">
          <Button type="button" variant="secondary" onClick={cancel}>Abbrechen</Button>
          <Button type="button" onClick={confirm}>Details laden und anzeigen</Button>
        </div>
      </section>
    </div>
  );
}

function AuditTable({ events, revealed, reveal }) {
  if (!events.length) return <p>Keine Audit-Ereignisse gefunden.</p>;
  return (
    <TableScroll stickyHeader>
      <Table>
        <TableHeader><TableRow>
          <TableHead scope="col">Zeit</TableHead><TableHead scope="col">Akteur:in</TableHead><TableHead scope="col">Aktion</TableHead><TableHead scope="col">Ergebnis</TableHead>
          <TableHead scope="col">Ressource</TableHead><TableHead scope="col">IP</TableHead><TableHead scope="col">User-Agent</TableHead><TableHead scope="col">Details</TableHead>
        </TableRow></TableHeader>
        <TableBody>{events.map(event => (
          <Fragment key={event.id}>
          <TableRow>
            <TableCell>{event.timestamp}</TableCell>
            <TableCell>{event.actor.label}{event.actor.id ? ` (#${event.actor.id})` : ''}</TableCell>
            <TableCell>{event.action}</TableCell>
            <TableCell>{event.outcome}</TableCell>
            <TableCell><span>{event.resource.label}</span> ({event.resource.type} #{event.resource.id})</TableCell>
            <TableCell>{event.client_ip || '—'}</TableCell>
            <TableCell>{event.user_agent || '—'}</TableCell>
            <TableCell>
              <div className="flex min-w-48 flex-col items-start gap-2">
                <span>{auditDetailsSummary(event.details_summary)}</span>
                {event.details_summary?.sensitive
                  ? <>
                    <Button href={event.details_url} variant="secondary" onClick={click => { click.preventDefault(); reveal(event); }}>Details anzeigen</Button>
                    <Button type="button" variant="secondary" onClick={() => reveal(event)}>Sensible Details anzeigen</Button>
                  </>
                  : <Button href={event.details_url} variant="secondary">Details anzeigen</Button>}
              </div>
            </TableCell>
          </TableRow>
          {revealed?.id === event.id ? (
            <TableRow><TableCell colSpan={8}><SensitiveDetail event={revealed} /></TableCell></TableRow>
          ) : null}
          </Fragment>
        ))}
        </TableBody>
      </Table>
    </TableScroll>
  );
}

function Pagination({ filters, pagination }) {
  if (!pagination || pagination.pages <= 1) return null;
  return (
    <nav className="flex items-center justify-center gap-3 p-3" aria-label="Audit-Seiten">
      {pagination.has_previous && (
        <Button href={queryUrl(filters, pagination.page - 1, pagination.page_size, pagination.snapshot_id)} variant="secondary">Vorherige Seite</Button>
      )}
      <span>Seite {pagination.page} von {pagination.pages}</span>
      {pagination.has_next && (
        <Button href={queryUrl(filters, pagination.page + 1, pagination.page_size, pagination.snapshot_id)} variant="secondary">Nächste Seite</Button>
      )}
    </nav>
  );
}

function exportFilename(response) {
  const disposition = response.headers.get('Content-Disposition') || '';
  const match = disposition.match(/filename="([^"]+)"/i);
  return match?.[1] || 'audit.log';
}

export function AuditPage({ data, fetchImpl = fetch }) {
  const [privacyAccepted, setPrivacyAccepted] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [revealed, setRevealed] = useState(null);
  const [warningSeen, setWarningSeen] = useState(false);
  const [pendingReveal, setPendingReveal] = useState(null);
  const showError = useErrorToast();
  const listIdentity = JSON.stringify({
    filters: data.filters,
    page: data.pagination?.page,
    snapshot: data.pagination?.snapshot_id,
    ids: (data.events || []).map(event => event.id),
  });
  useEffect(() => setRevealed(null), [listIdentity]);
  if (!data.authorized) {
    return <Columns><Column id="single-column"><Card title="Kein Zugriff"><p>Dir fehlt die Berechtigung, Audit-Ereignisse anzusehen.</p></Card></Column></Columns>;
  }
  const download = async () => {
    if (!privacyAccepted || exporting) return;
    setExporting(true);
    try {
      const response = await fetchImpl(data.export_url, { credentials: 'same-origin' });
      if (!response.ok) throw new Error(`Export fehlgeschlagen (${response.status})`);
      const url = URL.createObjectURL(await response.blob());
      const link = document.createElement('a');
      link.href = url;
      link.download = exportFilename(response);
      link.click();
      URL.revokeObjectURL(url);
    } catch (error) {
      showError(error.message || 'Export fehlgeschlagen');
    } finally {
      setExporting(false);
    }
  };
  const loadDetail = async event => {
    setRevealed(null);
    try {
      const response = await fetchImpl(event.details_url, { credentials: 'same-origin' });
      if (!response.ok) throw new Error(`Details konnten nicht geladen werden (${response.status})`);
      const payload = await response.json();
      setRevealed(payload);
    } catch {
      showError('Die Audit-Details konnten nicht geladen werden.');
    }
  };
  const reveal = event => {
    if (warningSeen) loadDetail(event);
    else setPendingReveal(event);
  };
  return (
    <main className="block p-3" id="body-container">
      <Card title="Audit-Ereignisse filtern">
        <AuditFilters data={data} />
        <div className="mt-3 border-t border-current pt-3">
          <p><strong>Datenschutzhinweis:</strong> Der Export enthält personenbezogene Daten: Namen, IP-Adressen, User-Agents, Gesundheit, Medikamente, Sozialversicherungsdaten, Familie, Telefon, E-Mail, Notfallkontakte und Zuteilungen. Vor externer Weitergabe oder einem Upload zu einer KI prüfen.</p>
          <label className="checkbox-row mb-2">
            <input type="checkbox" checked={privacyAccepted} onChange={event => setPrivacyAccepted(event.target.checked)} />
            Ich habe verstanden, dass der Export personenbezogene Daten enthält.
          </label>
          <Button type="button" disabled={!privacyAccepted || exporting} onClick={download}>
            {exporting ? 'Export wird erstellt…' : 'Audit-Log herunterladen'}
          </Button>
        </div>
      </Card>
      <p>{data.pagination.total} Ereignisse</p>
      <AuditTable events={data.events} revealed={revealed} reveal={reveal} />
      <Pagination filters={data.filters} pagination={data.pagination} />
      {pendingReveal ? (
        <RevealWarning
          cancel={() => setPendingReveal(null)}
          confirm={() => {
            const event = pendingReveal;
            setPendingReveal(null);
            setWarningSeen(true);
            loadDetail(event);
          }}
        />
      ) : null}
    </main>
  );
}

export const auditRoutes = [{
  pattern: /^\/audit$/,
  page: 'audit',
  title: 'Audit-Log',
  domain: 'audit',
  readContractKey: 'audit-events',
  includeSearch: true,
  render: ({ data, fetchImpl }) => <AuditPage data={data} fetchImpl={fetchImpl} />,
}];
