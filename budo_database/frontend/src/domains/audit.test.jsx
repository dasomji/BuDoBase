import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { routeDataRequest } from '../dataLoader';
import { parseRoute } from '../routes';
import { AuditPage } from './audit';

const event = {
  id: 8,
  timestamp: '2026-07-17T12:30:00Z',
  actor: { id: 3, label: 'Ada Teamer' },
  action: 'happy_cleaning.station.update',
  outcome: 'success',
  resource: { type: 'station', id: '12', label: 'Küche' },
  request_id: 'request-8',
  client_ip: '192.0.2.4',
  user_agent: 'Audit Browser',
  details: { changed_fields: ['name'] },
};

const data = {
  authorized: true,
  events: [event],
  filters: { turnus: '2', actor: '', action: '', outcome: '', resource_type: '', resource_id: '', from: '', to: '' },
  filter_options: {
    turnuses: [{ id: 2, label: 'T2-2026' }, { id: 3, label: 'T3-2026' }],
    actions: ['happy_cleaning.station.update'],
    outcomes: ['success'],
    resource_types: ['station'],
  },
  pagination: { page: 1, page_size: 50, total: 51, pages: 2, has_previous: false, has_next: true },
  export_url: '/api/audit-events/export/',
};

describe('audit explorer', () => {
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it('owns a protected focused route and all filters', () => {
    const route = parseRoute('/audit/');
    expect(route).toMatchObject({ page: 'audit', domain: 'audit', readContractKey: 'audit-events' });
    expect(routeDataRequest(route)).toEqual({
      contractKey: 'audit-events',
      params: {},
      url: '/api/route-data/audit-events/',
    });

    render(<AuditPage data={data} />);
    expect(screen.getByLabelText('Turnus')).toHaveValue('2');
    expect(screen.getByLabelText('Von')).toBeInTheDocument();
    expect(screen.getByLabelText('Bis')).toBeInTheDocument();
    expect(screen.getByLabelText('Akteur:in')).toBeInTheDocument();
    expect(screen.getByLabelText('Aktion')).toBeInTheDocument();
    expect(screen.getByLabelText('Ergebnis')).toBeInTheDocument();
    expect(screen.getByLabelText('Ressourcentyp')).toBeInTheDocument();
    expect(screen.getByLabelText('Ressourcen-ID')).toBeInTheDocument();
    expect(screen.getByText(/Ada Teamer/)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Nächste Seite' })).toHaveAttribute(
      'href',
      expect.stringMatching(/turnus=2.*page=2/),
    );
  });

  it('gates unauthorized readers and renders empty state', () => {
    const { unmount } = render(<AuditPage data={{ authorized: false, events: [] }} />);
    expect(screen.getByRole('heading', { name: 'Kein Zugriff' })).toBeInTheDocument();
    expect(screen.queryByText('Ada Teamer')).not.toBeInTheDocument();
    unmount();

    render(<AuditPage data={{ ...data, events: [], pagination: { ...data.pagination, total: 0, pages: 0, has_next: false } }} />);
    expect(screen.getByText('Keine Audit-Ereignisse gefunden.')).toBeInTheDocument();
  });

  it('requires the privacy acknowledgement and downloads the log response', async () => {
    const click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {});
    vi.stubGlobal('URL', {
      createObjectURL: vi.fn(() => 'blob:audit'),
      revokeObjectURL: vi.fn(),
    });
    const fetchImpl = vi.fn().mockResolvedValue({
      ok: true,
      headers: { get: () => 'attachment; filename="audit-T2-2026.log"' },
      blob: async () => new Blob(['log']),
    });
    render(<AuditPage data={data} fetchImpl={fetchImpl} />);

    const download = screen.getByRole('button', { name: 'Audit-Log herunterladen' });
    expect(download).toBeDisabled();
    expect(screen.getAllByText(/personenbezogene Daten/i)).toHaveLength(2);
    fireEvent.click(screen.getByRole('checkbox', { name: /personenbezogene Daten/i }));
    fireEvent.click(download);

    await waitFor(() => expect(fetchImpl).toHaveBeenCalledWith('/api/audit-events/export/', { credentials: 'same-origin' }));
    expect(click).toHaveBeenCalledOnce();
    expect(URL.revokeObjectURL).toHaveBeenCalledWith('blob:audit');
  });

  it('shows an export error without losing the page', async () => {
    const fetchImpl = vi.fn().mockResolvedValue({ ok: false, status: 503 });
    render(<AuditPage data={data} fetchImpl={fetchImpl} />);
    fireEvent.click(screen.getByRole('checkbox', { name: /personenbezogene Daten/i }));
    fireEvent.click(screen.getByRole('button', { name: 'Audit-Log herunterladen' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Export fehlgeschlagen');
    expect(screen.getByText(/Ada Teamer/)).toBeInTheDocument();
  });
});
