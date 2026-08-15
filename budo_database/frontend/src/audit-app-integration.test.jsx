import { cleanup, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import App from './App';

const response = (payload, { ok = true, status = 200 } = {}) => ({
  ok,
  status,
  json: vi.fn().mockResolvedValue(payload),
});

const bootstrap = permissions => ({
  authenticated: true,
  csrf_token: 'token',
  messages: [],
  profile: { id: 1, rufname: 'Ada' },
  turnus: { id: 2, label: 'T2' },
  permissions,
  search_index: { kids: [], focuses: [], places: [] },
  happy_cleaning_events: [],
});

const auditData = {
  authorized: true,
  events: [],
  filters: {},
  filter_options: { turnuses: [], actions: [], outcomes: [], resource_types: [] },
  pagination: {
    page: 1, page_size: 50, total: 0, pages: 0,
    has_previous: false, has_next: false, snapshot_id: 0,
  },
  export_url: '/api/audit-events/export/',
};

describe('Audit-Log application integration', () => {
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
    window.history.pushState({}, '', '/');
  });

  it('passes the effective bootstrap permission into the sidebar', async () => {
    window.history.pushState({}, '', '/audit/');
    const fetchImpl = vi.fn()
      .mockResolvedValueOnce(response(bootstrap({
        is_superuser: true,
        view_auditevent: true,
        export_auditevent: false,
      })))
      .mockResolvedValueOnce(response(auditData));

    render(<App fetchImpl={fetchImpl} />);

    expect(await screen.findByRole('link', { name: 'Audit-Log' })).toHaveAttribute('href', '/audit/');
    expect(screen.getByRole('heading', { name: 'Audit-Ereignisse filtern' })).toBeInTheDocument();
  });

  it('redirects an expired audit session and renders a status instead of a blank shell', async () => {
    window.history.pushState({}, '', '/audit/');
    const fetchImpl = vi.fn()
      .mockResolvedValueOnce(response(bootstrap({
        view_auditevent: true,
        export_auditevent: true,
      })))
      .mockResolvedValueOnce(response(
        { detail: 'Anmeldedaten fehlen.' },
        { ok: false, status: 403 },
      ));
    const navigate = vi.fn();

    render(<App fetchImpl={fetchImpl} navigate={navigate} />);

    await waitFor(() => expect(navigate).toHaveBeenCalledWith('/login/?next=%2Faudit%2F'));
    expect(screen.getByText('Weiterleitung zum Login…')).toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: 'Audit-Ereignisse filtern' })).not.toBeInTheDocument();
  });
});
