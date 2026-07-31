import { useState } from 'react';

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

function AuditTable({ events }) {
  if (!events.length) return <p>Keine Audit-Ereignisse gefunden.</p>;
  return (
    <TableScroll stickyHeader>
      <Table>
        <TableHeader><TableRow>
          <TableHead scope="col">Zeit</TableHead><TableHead scope="col">Akteur:in</TableHead><TableHead scope="col">Aktion</TableHead><TableHead scope="col">Ergebnis</TableHead>
          <TableHead scope="col">Ressource</TableHead><TableHead scope="col">IP</TableHead><TableHead scope="col">User-Agent</TableHead><TableHead scope="col">Details</TableHead>
        </TableRow></TableHeader>
        <TableBody>{events.map(event => (
          <TableRow key={event.id}>
            <TableCell>{event.timestamp}</TableCell>
            <TableCell>{event.actor.label}{event.actor.id ? ` (#${event.actor.id})` : ''}</TableCell>
            <TableCell>{event.action}</TableCell>
            <TableCell>{event.outcome}</TableCell>
            <TableCell>{event.resource.label} ({event.resource.type} #{event.resource.id})</TableCell>
            <TableCell>{event.client_ip || '—'}</TableCell>
            <TableCell>{event.user_agent || '—'}</TableCell>
            <TableCell>
              <div className="flex min-w-48 flex-col items-start gap-2">
                <span>{auditDetailsSummary(event.details_summary)}</span>
                <Button href={event.details_url} variant="secondary">Details anzeigen</Button>
              </div>
            </TableCell>
          </TableRow>
        ))}</TableBody>
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
  const showError = useErrorToast();
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
  return (
    <main className="block p-3" id="body-container">
      <Card title="Audit-Ereignisse filtern">
        <AuditFilters data={data} />
        <div className="mt-3 border-t border-current pt-3">
          <p><strong>Datenschutzhinweis:</strong> Der Export enthält personenbezogene Daten wie Namen, IP-Adressen und User-Agents. Vor einer externen Weitergabe oder einem Upload zu einer KI prüfen.</p>
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
      <AuditTable events={data.events} />
      <Pagination filters={data.filters} pagination={data.pagination} />
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
