import { cleanup, fireEvent, render as testingLibraryRender, screen, waitFor, within } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { Toaster } from '../components/ui/toast';
import { routeDataRequest } from '../dataLoader';
import { parseRoute } from '../routes';
import { expectErrorToastOnly } from '../test-support';
import { AuditPage } from './audit';

const render = ui => testingLibraryRender(ui, {
  wrapper: ({ children }) => <Toaster timeout={0}>{children}</Toaster>,
});

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
  details_summary: {
    sensitive: false,
    available_fields: ['changed_fields', 'station_name'],
  },
  details_url: '/api/audit-events/8/?turnus=2',
};

const kidEditEvent = {
  ...event,
  id: 9,
  actor: { id: 4, label: 'Grace Teamer' },
  action: 'kid.edit',
  resource: { type: 'child', id: '27', label: 'Kind #27' },
  details_summary: {
    schema: 'budo.kid-edit',
    version: 1,
    result: 'updated',
    changed_paths: ['illness', 'swp.17', 'happy_cleaning_number', 'happy_cleaning.42'],
    sensitive: true,
  },
  details_url: '/api/audit-events/9/',
};

const data = {
  authorized: true,
  events: [event, kidEditEvent],
  filters: { turnus: '2', actor: '', action: '', outcome: '', resource_type: '', resource_id: '', from: '', to: '' },
  filter_options: {
    turnuses: [{ id: 2, label: 'T2-2026' }, { id: 3, label: 'T3-2026' }],
    actions: ['happy_cleaning.station.update'],
    outcomes: ['success'],
    resource_types: ['station'],
  },
  pagination: { page: 1, page_size: 50, total: 51, pages: 2, has_previous: false, has_next: true, snapshot_id: 811 },
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
    expect(screen.getByLabelText('Turnus')).toHaveAttribute('data-slot', 'native-select');
    expect(screen.getByLabelText('Von')).toBeInTheDocument();
    expect(screen.getByLabelText('Bis')).toBeInTheDocument();
    expect(screen.getByLabelText('Akteur:in')).toBeInTheDocument();
    expect(screen.getByLabelText('Aktion')).toBeInTheDocument();
    expect(screen.getByLabelText('Ergebnis')).toBeInTheDocument();
    expect(screen.getByLabelText('Ressourcentyp')).toBeInTheDocument();
    expect(screen.getByLabelText('Ressourcen-ID')).toBeInTheDocument();
    expect(screen.getByText(/Ada Teamer/)).toBeInTheDocument();
    expect(screen.getByRole('table').closest('[data-slot="table-scroll"]')).not.toBeNull();
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

  it('keeps the snapshot only while paging, never when filtering or resetting', () => {
    render(<AuditPage data={{
      ...data,
      pagination: {
        ...data.pagination, page: 2, pages: 3,
        has_previous: true, has_next: true,
      },
    }} />);

    expect(screen.getByRole('link', { name: 'Vorherige Seite' })).toHaveAttribute(
      'href', expect.stringContaining('snapshot_id=811'),
    );
    expect(screen.getByRole('link', { name: 'Nächste Seite' })).toHaveAttribute(
      'href', expect.stringContaining('snapshot_id=811'),
    );
    expect(document.querySelector('form input[name="snapshot_id"]')).toBeNull();
    expect(screen.getByRole('link', { name: 'Zurücksetzen' })).toHaveAttribute(
      'href', '/audit/',
    );
  });

  it('renders only bounded summaries and accessible exact detail links', () => {
    expect(event).not.toHaveProperty('details');
    expect(kidEditEvent).not.toHaveProperty('details');
    render(<AuditPage data={data} />);

    expect(screen.getByText(/4 geänderte Pfade/i)).toBeInTheDocument();
    expect(screen.getByText(/changed_fields.*station_name/i)).toBeInTheDocument();
    expect(screen.queryByText('illness')).not.toBeInTheDocument();
    expect(screen.queryByText('happy_cleaning.42')).not.toBeInTheDocument();

    const legacyRow = screen.getByText('happy_cleaning.station.update').closest('tr');
    expect(within(legacyRow).getByRole('link', { name: /Details anzeigen/i })).toHaveAttribute(
      'href', event.details_url,
    );
    const kidRow = screen.getByText('kid.edit').closest('tr');
    expect(within(kidRow).getByRole('button', { name: 'Sensible Details anzeigen' })).toBeEnabled();
    expect(within(kidRow).queryByRole('link', { name: 'Details anzeigen' })).not.toBeInTheDocument();
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

  it('shows failed audit exports as error toasts, never inline', async () => {
    const fetchImpl = vi.fn().mockResolvedValue({ ok: false, status: 503 });
    render(<AuditPage data={data} fetchImpl={fetchImpl} />);
    fireEvent.click(screen.getByRole('checkbox', { name: /personenbezogene Daten/i }));
    fireEvent.click(screen.getByRole('button', { name: 'Audit-Log herunterladen' }));
    await expectErrorToastOnly('Export fehlgeschlagen (503)');
    expect(screen.getByText(/Ada Teamer/)).toBeInTheDocument();
  });
});
