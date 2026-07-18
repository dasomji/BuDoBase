import { useState } from 'react';

import { Card, Column, Columns } from '../components';


function queryUrl(filters, page, pageSize) {
  const params = new URLSearchParams();
  Object.entries(filters || {}).forEach(([key, value]) => {
    if (value) params.set(key, value);
  });
  if (page > 1) params.set('page', String(page));
  if (pageSize && pageSize !== 50) params.set('page_size', String(pageSize));
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
    <form action="/audit/" method="get" className="form-grid audit-filters">
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
          {(options.actions || []).map(value => <option key={value}>{value}</option>)}
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
      <div className="react-actions">
        <button className="button" type="submit">Filtern</button>
        <a className="button" href="/audit/">Zurücksetzen</a>
      </div>
    </form>
  );
}

function AuditTable({ events }) {
  if (!events.length) return <p className="audit-empty">Keine Audit-Ereignisse gefunden.</p>;
  return (
    <div className="table-container">
      <table id="audit-table">
        <thead><tr className="table-header">
          <th>Zeit</th><th>Akteur:in</th><th>Aktion</th><th>Ergebnis</th>
          <th>Ressource</th><th>IP</th><th>User-Agent</th><th>Details</th>
        </tr></thead>
        <tbody>{events.map(event => (
          <tr className="table_row" key={event.id}>
            <td>{event.timestamp}</td>
            <td>{event.actor.label}{event.actor.id ? ` (#${event.actor.id})` : ''}</td>
            <td>{event.action}</td>
            <td>{event.outcome}</td>
            <td>{event.resource.label} ({event.resource.type} #{event.resource.id})</td>
            <td>{event.client_ip || '—'}</td>
            <td>{event.user_agent || '—'}</td>
            <td><code>{JSON.stringify(event.details)}</code></td>
          </tr>
        ))}</tbody>
      </table>
    </div>
  );
}

function Pagination({ filters, pagination }) {
  if (!pagination || pagination.pages <= 1) return null;
  return (
    <nav className="audit-pagination" aria-label="Audit-Seiten">
      {pagination.has_previous && (
        <a className="button" href={queryUrl(filters, pagination.page - 1, pagination.page_size)}>Vorherige Seite</a>
      )}
      <span>Seite {pagination.page} von {pagination.pages}</span>
      {pagination.has_next && (
        <a className="button" href={queryUrl(filters, pagination.page + 1, pagination.page_size)}>Nächste Seite</a>
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
  const [exportError, setExportError] = useState('');
  if (!data.authorized) {
    return <Columns><Column id="single-column"><Card title="Kein Zugriff"><p>Dir fehlt die Berechtigung, Audit-Ereignisse anzusehen.</p></Card></Column></Columns>;
  }
  const download = async () => {
    if (!privacyAccepted || exporting) return;
    setExporting(true);
    setExportError('');
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
      setExportError(error.message || 'Export fehlgeschlagen');
    } finally {
      setExporting(false);
    }
  };
  return (
    <main className="audit-page" id="body-container">
      <section className="card audit-controls">
        <h2>Audit-Ereignisse filtern</h2>
        <AuditFilters data={data} />
        <div className="audit-export">
          <p><strong>Datenschutzhinweis:</strong> Der Export enthält personenbezogene Daten wie Namen, IP-Adressen und User-Agents. Vor einer externen Weitergabe oder einem Upload zu einer KI prüfen.</p>
          <label className="checkbox-row">
            <input type="checkbox" checked={privacyAccepted} onChange={event => setPrivacyAccepted(event.target.checked)} />
            Ich habe verstanden, dass der Export personenbezogene Daten enthält.
          </label>
          <button className="button" type="button" disabled={!privacyAccepted || exporting} onClick={download}>
            {exporting ? 'Export wird erstellt…' : 'Audit-Log herunterladen'}
          </button>
          {exportError && <p role="alert" className="error">{exportError}</p>}
        </div>
      </section>
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
