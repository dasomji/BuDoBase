import {
  cleanup,
  fireEvent,
  render as testingLibraryRender,
  screen,
  waitFor,
  within,
} from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { Toaster } from '../components/ui/toast';
import { AuditPage } from './audit';

const render = ui => testingLibraryRender(ui, {
  wrapper: ({ children }) => <Toaster timeout={0}>{children}</Toaster>,
});

const SCRIPT_LIKE_SECRET = '<script>globalThis.__AUDIT_XSS__=true</script>';

const listEvent = (id, overrides = {}) => ({
  id,
  timestamp: '2026-07-30T12:30:00Z',
  actor: { id: 3, label: 'Audit Reader' },
  action: 'kid.edit',
  outcome: 'success',
  resource: { type: 'child', id: String(20 + id), label: `Kind #${20 + id}` },
  request_id: `request-${id}`,
  client_ip: '192.0.2.4',
  user_agent: 'Audit Browser',
  details_summary: {
    schema: 'budo.kid-edit',
    version: 1,
    result: 'updated',
    changed_paths: ['illness', 'swp.17', 'happy_cleaning.42'],
    sensitive: true,
  },
  details_url: `/api/audit-events/${id}/`,
  ...overrides,
});

const snapshot = ({ changed = false } = {}) => ({
  versions: { edit: changed ? 5 : 4, happy_cleaning_number: 3 },
  fields: {
    first_name: 'Ada',
    last_name: 'Lovelace',
    sex: 'weiblich',
    birthday: '2012-07-02',
    stay_weeks: 2,
    siblings: null,
    tent_request: null,
    budo_experience: true,
    illness: changed ? SCRIPT_LIKE_SECRET : 'Asthma',
    drugs: null,
    vegetarian: 'ja',
    special_food: null,
    swimmer: 'gut',
    consent: true,
    over_the_counter_medication: null,
    prescription_medication: null,
    tetanus: 'ja',
    tick_vaccine: 'Grundimmunisiert',
    organization: 'Ferienverein Nord',
    registrant_first_name: 'Augusta',
    registrant_last_name: 'Lovelace',
    social_security_number: '0207121234',
    registrant_email: 'augusta@example.test',
    registrant_phone: '+43 660 1234567',
    insured_with: 'Augusta Lovelace',
    emergency_contacts: 'Charles\n+43 660 9876543',
    budo_family: 'M',
  },
  happy_cleaning_number: 42,
  swp: [{
    period_id: 17,
    period_code: 'w1',
    period_label: changed ? SCRIPT_LIKE_SECRET : 'Woche 1',
    start: '2026-07-05',
    duration_days: 3,
    focuses: changed ? [{ id: 91, label: SCRIPT_LIKE_SECRET }] : [],
  }],
  happy_cleaning: [{
    event_id: 42,
    display_number: 1,
    event_label: changed ? SCRIPT_LIKE_SECRET : 'Happy Cleaning 1',
    event_revision: changed ? 19 : 18,
    assignment_version: changed ? 19 : 0,
    target: changed
      ? { kind: 'station', station_id: 8, station_label: SCRIPT_LIKE_SECRET }
      : { kind: 'unassigned' },
  }],
});

const detail = (id, overrides = {}) => ({
  ...listEvent(id),
  details: {
    schema: 'budo.kid-edit',
    version: 1,
    result: 'updated',
    changed_paths: ['illness', 'swp.17', 'happy_cleaning.42'],
    before: snapshot(),
    after: snapshot({ changed: true }),
  },
  ...overrides,
});

const data = {
  authorized: true,
  events: [listEvent(9), listEvent(10, {
    resource: { type: 'child', id: '30', label: 'Kind #30' },
    details_url: '/api/audit-events/10/',
  })],
  filters: {
    turnus: '2', actor: '', action: '', outcome: '', resource_type: '',
    resource_id: '', from: '', to: '',
  },
  filter_options: {
    turnuses: [{ id: 2, label: 'T2-2026' }],
    actions: ['kid.edit'],
    outcomes: ['success'],
    resource_types: ['child'],
  },
  pagination: {
    page: 1, page_size: 50, total: 2, pages: 1,
    has_previous: false, has_next: false, snapshot_id: 811,
  },
  export_url: '/api/audit-events/export/',
};

const jsonResponse = payload => ({
  ok: true,
  status: 200,
  json: vi.fn().mockResolvedValue(payload),
});

describe('sensitive audit reveal', () => {
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
    delete globalThis.__AUDIT_XSS__;
    window.history.pushState({}, '', '/audit/');
    localStorage.clear();
    sessionStorage.clear();
  });

  it('loads and renders structured details for every updated form by default', async () => {
    const fetchImpl = vi.fn()
      .mockResolvedValueOnce(jsonResponse(detail(9)))
      .mockResolvedValueOnce(jsonResponse(detail(10, {
        details: {
          ...detail(10).details,
          before: {
            ...snapshot(),
            fields: { ...snapshot().fields, first_name: 'Grace' },
          },
          after: {
            ...snapshot(),
            fields: { ...snapshot().fields, first_name: 'Grace Hopper' },
          },
          changed_paths: ['first_name'],
        },
      })));
    render(<AuditPage data={data} fetchImpl={fetchImpl} />);

    const firstRow = screen.getByText('Kind #29').closest('tr');

    await waitFor(() => expect(fetchImpl).toHaveBeenCalledWith(
      '/api/audit-events/9/',
      { credentials: 'same-origin' },
    ));
    for (const heading of ['Allgemein', 'Gesundheitsinfos', 'Familie', 'SWP', 'Happy Cleaning']) {
      expect(screen.getAllByRole('heading', { name: heading }).length).toBeGreaterThan(0);
    }
    expect(screen.getAllByText('Vorher').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Nachher').length).toBeGreaterThan(0);
    expect(screen.getByRole('heading', { name: 'Krankheiten und Besonderheiten' })).toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: 'BuDo-Familie' })).not.toBeInTheDocument();
    await waitFor(() => expect(fetchImpl).toHaveBeenCalledTimes(2));
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
    expect(screen.getAllByText(SCRIPT_LIKE_SECRET).length).toBeGreaterThan(0);
    expect(await screen.findByText('Grace Hopper')).toBeInTheDocument();
  });

  it('renders script-like values as bounded text and never persists or propagates them', async () => {
    const localWrite = vi.spyOn(Storage.prototype, 'setItem');
    const historyPush = vi.spyOn(window.history, 'pushState');
    const historyReplace = vi.spyOn(window.history, 'replaceState');
    const consoleLog = vi.spyOn(console, 'log').mockImplementation(() => {});
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});
    const fetchImpl = vi.fn().mockResolvedValue(jsonResponse(detail(9)));
    render(<AuditPage data={{ ...data, events: [data.events[0]] }} fetchImpl={fetchImpl} />);

    await screen.findAllByText(SCRIPT_LIKE_SECRET);

    expect(document.querySelector('script')).not.toBeInTheDocument();
    expect(document.querySelector('svg script')).not.toBeInTheDocument();
    expect(globalThis.__AUDIT_XSS__).toBeUndefined();
    expect(localWrite).not.toHaveBeenCalled();
    expect(historyPush).not.toHaveBeenCalled();
    expect(historyReplace).not.toHaveBeenCalled();
    expect(localStorage.length).toBe(0);
    expect(sessionStorage.length).toBe(0);
    expect(window.location.href).not.toContain('AUDIT_XSS');
    for (const node of document.querySelectorAll('*')) {
      for (const attribute of node.attributes) {
        expect(attribute.value).not.toContain('AUDIT_XSS');
      }
    }
    expect(screen.getByRole('region', { name: 'Benachrichtigungen' })).not.toHaveTextContent('AUDIT_XSS');
    expect(JSON.stringify(consoleLog.mock.calls)).not.toContain('AUDIT_XSS');
    expect(JSON.stringify(consoleError.mock.calls)).not.toContain('AUDIT_XSS');
  });

  it('keeps a large unchanged relationship set out of the DOM until explicitly expanded', async () => {
    const unchangedEvents = Array.from({ length: 250 }, (_, index) => ({
      event_id: index + 1,
      display_number: index + 1,
      event_label: `UNCHANGED-EVENT-${index + 1}`,
      event_revision: 1,
      assignment_version: 0,
      target: { kind: 'unassigned' },
    }));
    const before = { ...snapshot(), happy_cleaning: unchangedEvents };
    const after = {
      ...snapshot(),
      versions: { edit: 5, happy_cleaning_number: 3 },
      fields: { ...snapshot().fields, first_name: 'Grace' },
      happy_cleaning: unchangedEvents,
    };
    const largeDetail = detail(9, {
      details: {
        schema: 'budo.kid-edit',
        version: 1,
        result: 'updated',
        changed_paths: ['first_name'],
        before,
        after,
      },
    });
    const fetchImpl = vi.fn().mockResolvedValue(jsonResponse(largeDetail));
    render(<AuditPage data={{ ...data, events: [data.events[0]] }} fetchImpl={fetchImpl} />);

    expect(await screen.findByText('Grace')).toBeInTheDocument();
    expect(screen.queryByText('UNCHANGED-EVENT-250')).not.toBeInTheDocument();

    expect(screen.queryByRole('button', { name: /unveränderte Werte anzeigen/i })).not.toBeInTheDocument();
    expect(fetchImpl).toHaveBeenCalledOnce();
  });

  it('clears the complete payload when filters, snapshot, or page rows change', async () => {
    const fetchImpl = vi.fn().mockResolvedValue(jsonResponse(detail(9)));
    const view = render(<AuditPage data={{ ...data, events: [data.events[0]] }} fetchImpl={fetchImpl} />);
    await screen.findAllByText(SCRIPT_LIKE_SECRET);

    view.rerender(<AuditPage data={{
      ...data,
      events: [data.events[0]],
      filters: { ...data.filters, actor: 'Grace' },
    }} fetchImpl={fetchImpl} />);
    expect(screen.queryByText(SCRIPT_LIKE_SECRET)).not.toBeInTheDocument();

    await screen.findAllByText(SCRIPT_LIKE_SECRET);
    view.rerender(<AuditPage data={{
      ...data,
      events: [data.events[1]],
      pagination: { ...data.pagination, page: 2, snapshot_id: 900 },
    }} fetchImpl={fetchImpl} />);
    expect(screen.queryByText(SCRIPT_LIKE_SECRET)).not.toBeInTheDocument();
  });
});

describe('sensitive audit export acknowledgement', () => {
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it('names every privacy category and external/AI handling before enabling export', () => {
    render(<AuditPage data={data} fetchImpl={vi.fn()} />);

    const privacy = screen.getByText('Datenschutzhinweis:').closest('div');
    for (const category of [
      /Namen/i,
      /IP-Adressen/i,
      /User-Agents/i,
      /Gesundheit/i,
      /Medikament/i,
      /Sozialversicherung/i,
      /Familie/i,
      /Telefon/i,
      /E-Mail/i,
      /Notfallkontakt/i,
      /Zuteilung/i,
    ]) {
      expect(privacy).toHaveTextContent(category);
    }
    expect(privacy).toHaveTextContent(/extern/i);
    expect(privacy).toHaveTextContent(/KI/i);

    const download = within(privacy).getByRole('button', { name: 'Audit-Log herunterladen' });
    expect(download).toBeDisabled();
    fireEvent.click(within(privacy).getByRole('checkbox'));
    expect(download).toBeEnabled();
  });
});
