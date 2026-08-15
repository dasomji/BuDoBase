import { cleanup, fireEvent, render as testingLibraryRender, screen, waitFor, within } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import App from '../App';
import { Toaster } from '../components/ui/toast';
import { parseRoute } from '../routes';
import { expectErrorToastOnly } from '../test-support';
import { dashboardRoutes, DashboardPage, GoodToKnowPage, PocketMoneyPage } from './dashboard';

const render = ui => testingLibraryRender(ui, {
  wrapper: ({ children }) => <Toaster timeout={0}>{children}</Toaster>,
});

const emptyPage = { items: [], next_cursor: null, has_more: false, limit: 20 };

const dashboardData = (activity = {}) => ({
  profile: {
    focus_ids: [11],
    budo_family: 'M',
  },
  team: [],
  totals: {
    pocket_money_paid: 20,
    pocket_money: 18,
    team_money: 12,
    checked_in: 1,
    kids: 1,
    train_arrival: 1,
    train_departure: 0,
  },
  kids: [{
    id: 7,
    full_name: 'Grace Hopper',
    present: true,
    age: 14,
    sex: 'weiblich',
    weeks: 1,
    budo_experience: false,
    birthday: '2012-07-02',
    birthday_during_turnus: true,
    food: '🌱 - glutenfrei',
    special_food: 'glutenfrei',
    drugs: 'Asthmaspray',
    illness: 'Allergie',
    budo_family: 'M',
    assigned_focus_weeks: ['w1', 'w2'],
  }],
  focuses: [
    { id: 11, name: 'Wald', week: 'w1', kid_ids: [7] },
    { id: 12, name: 'See', week: 'w2', kid_ids: [7] },
  ],
  focus_assignments_complete: { w1: true, w2: true },
  happy_cleanings: [{
    id: 21,
    display_number: 1,
    assignments_complete: true,
    stations: [{
      id: 31,
      name: 'Küche',
      kid_ids: [7],
      document: {
        type: 'doc',
        content: [{
          type: 'taskList',
          content: [{
            type: 'taskItem',
            attrs: { id: 101, checked: false, version: 1 },
            content: [{ type: 'paragraph', content: [{ type: 'text', text: 'Boden fegen' }] }],
          }],
        }],
      },
    }],
  }],
  activity: {
    notes: emptyPage,
    first_aid: emptyPage,
    ...activity,
  },
  turnus: { label: 'T2' },
});

const pocketMoneyData = (transactions = emptyPage) => ({
  totals: {
    pocket_money_paid: 20,
    pocket_money: 18,
  },
  activity: { transactions },
});

const response = (data, { ok = true, status = 200 } = {}) => ({
  ok,
  status,
  json: vi.fn().mockResolvedValue(data),
});

describe('dashboard page', () => {
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
    window.history.pushState({}, '', '/');
  });

  it('shows no dashboard hint while membership is awaiting', () => {
    const mutate = vi.fn();
    render(<DashboardPage data={{
      membership_awaiting: true,
      turnuses: [
        { id: 1, label: '2. Turnus 2027', request_status: 'pending' },
        { id: 2, label: '3. Turnus 2027', request_status: 'rejected' },
      ],
    }} mutate={mutate} />);

    expect(screen.queryByText(/Anfrage/)).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Mitgliedschaft/ })).not.toBeInTheDocument();
    expect(screen.queryByText('Kinder')).not.toBeInTheDocument();
    expect(mutate).not.toHaveBeenCalled();
  });

  it('renders exactly the requested operational dashboard cards', () => {
    render(<DashboardPage data={dashboardData()} />);

    for (const heading of [
      'Kinder: 1',
      'Notizen',
      'Erste Hilfe',
      'Medi',
      'SWP 1: Wald',
      'SWP 2: See',
      'Happy Cleaning 1: Küche',
    ]) {
      expect(screen.getByRole('heading', { name: heading })).toBeInTheDocument();
    }
    for (const removed of [
      'Mein Profil',
      'Team',
      'Finanzen',
      'Speziallisten',
      'Erstes Mal im BuDO: 1/1',
      'Einwöchige: 1',
      'Gesundheitliches',
      'Essen & Allergien',
      'Geburtstagskinder: 1',
      'Verabschiedungsliste: 0',
      'Taschengeld',
      'Taschengeldkasse',
    ]) {
      expect(screen.queryByRole('heading', { name: removed })).not.toBeInTheDocument();
    }
    expect(screen.getAllByRole('link', { name: 'Grace Hopper' }).length).toBeGreaterThan(0);
    const familyCard = screen.getByRole('heading', { name: 'Medi' }).closest('.card');
    expect(within(familyCard).getAllByText('Medi')).toHaveLength(1);
    expect(screen.queryByRole('link', { name: 'Wald' })).not.toBeInTheDocument();
    expect(screen.queryByRole('link', { name: 'See' })).not.toBeInTheDocument();
    const cleaningCard = screen.getByRole('heading', { name: 'Happy Cleaning 1: Küche' }).closest('.card');
    expect(cleaningCard).toHaveClass('transparent');
    const kidsCard = within(cleaningCard).getByRole('heading', { name: 'Kinder' }).closest('.card');
    const todosCard = within(cleaningCard).getByRole('heading', { name: 'To-Dos' }).closest('.card');
    expect(kidsCard).not.toHaveClass('transparent');
    expect(todosCard).not.toHaveClass('transparent');
    expect(within(kidsCard).getByRole('link', { name: 'Zur Einteilung' })).toHaveAttribute('href', '/happy-cleaning/21/assignment/');
    expect(within(todosCard).getByRole('link', { name: 'Küche Details' })).toHaveAttribute('href', '/happy-cleaning/?event_id=21&station_id=31');
    expect(within(todosCard).getByRole('checkbox', { name: 'Boden fegen erledigen' })).toBeInTheDocument();
  });

  it('never renders Turnus membership requests on the dashboard', () => {
    const data = dashboardData();
    data.membership_turnuses = [
      { id: 1, label: '2. Turnus 2027', request_status: 'approved' },
      { id: 2, label: '3. Turnus 2027', request_status: null },
    ];

    render(<DashboardPage data={data} mutate={vi.fn()} />);

    expect(screen.getByRole('heading', { name: 'Kinder: 1' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Mitgliedschaft anfragen/ })).not.toBeInTheDocument();
  });

  it('renders the moved informational cards on Gut zu wissen', () => {
    render(<GoodToKnowPage data={dashboardData()} />);

    for (const heading of [
      'Erstes Mal im BuDO: 1/1',
      'Einwöchige: 1',
      'Gesundheitliches',
      'Essen & Allergien',
      'Geburtstagskinder: 1',
      'Verabschiedungsliste: 0',
    ]) {
      expect(screen.getByRole('heading', { name: heading })).toBeInTheDocument();
    }
    expect(screen.queryByRole('heading', { name: 'Kinder: 1' })).not.toBeInTheDocument();
    expect(screen.getAllByRole('link', { name: 'Grace Hopper' }).length).toBeGreaterThan(0);
  });

  it('builds one printable page per Gut zu wissen card without presence indicators', () => {
    const data = dashboardData();
    data.kids[0].present = false;

    render(<GoodToKnowPage data={data} />);

    const printPages = document.querySelector('.good-to-know-print-pages');
    expect(printPages).toHaveAttribute('aria-label', 'Gut-zu-wissen-Druckseiten');
    const pages = [...printPages.querySelectorAll(':scope > .good-to-know-print-page')];
    expect(pages.map(page => within(page).getByRole('heading', { hidden: true }).textContent)).toEqual([
      'Erstes Mal im BuDO: 1/1',
      'Einwöchige: 1',
      'Gesundheitliches',
      'Essen & Allergien',
      'Geburtstagskinder: 1',
      'Verabschiedungsliste: 0',
    ]);
    pages.forEach(page => {
      expect(within(page).getAllByRole('heading', { hidden: true })).toHaveLength(1);
      expect(within(page).queryByRole('link', { hidden: true })).not.toBeInTheDocument();
      expect(page).not.toHaveTextContent('❌');
    });
    expect(within(printPages).getAllByText('Grace Hopper', { exact: false })).toHaveLength(5);
    expect(document.querySelector('style[data-print-page-style]')).toHaveTextContent('@page { margin: 0; }');
  });

  it('offers Gut zu wissen printing from the shared page header', () => {
    const print = vi.spyOn(window, 'print').mockImplementation(() => {});
    const goodToKnowRoute = dashboardRoutes.find(route => route.page === 'good-to-know');

    render(goodToKnowRoute.headerAction?.());

    const printButton = screen.getByRole('button', { name: 'Drucken' });
    expect(printButton).toHaveTextContent('Drucken');
    expect(printButton.querySelector('svg')).toHaveAttribute('aria-hidden', 'true');
    fireEvent.click(printButton);
    expect(print).toHaveBeenCalledOnce();
  });

  it('owns the focused Gut zu wissen route contract', () => {
    expect(parseRoute('/gut-zu-wissen/')).toMatchObject({
      page: 'good-to-know',
      title: 'Gut zu wissen',
      readContractKey: 'gut-zu-wissen',
    });
  });

  it('loads Gut zu wissen from its focused route endpoint', async () => {
    window.history.pushState({}, '', '/gut-zu-wissen/');
    const fetchImpl = vi.fn()
      .mockResolvedValueOnce(response({
        authenticated: true,
        csrf_token: 'token',
        messages: [],
        profile: { id: 1, rufname: 'Ada' },
        turnus: { id: 2, label: 'T2' },
        permissions: {},
        search_index: { kids: [], focuses: [], places: [] },
      }))
      .mockResolvedValueOnce(response(dashboardData()));

    render(<App fetchImpl={fetchImpl} />);

    expect(await screen.findByRole('heading', { name: 'Gesundheitliches' })).toBeInTheDocument();
    expect(fetchImpl.mock.calls[1][0]).toBe('/api/route-data/gut-zu-wissen/');
  });

  it('owns and loads the dedicated Taschengeld route contract', async () => {
    expect(parseRoute('/taschengeld/')).toMatchObject({
      page: 'pocket-money',
      title: 'Taschengeld',
      readContractKey: 'pocket-money',
    });
    window.history.pushState({}, '', '/taschengeld/');
    const fetchImpl = vi.fn()
      .mockResolvedValueOnce(response({
        authenticated: true,
        csrf_token: 'token',
        messages: [],
        profile: { id: 1, rufname: 'Ada' },
        turnus: { id: 2, label: 'T2' },
        permissions: {},
        search_index: { kids: [], focuses: [], places: [] },
      }))
      .mockResolvedValueOnce(response(pocketMoneyData()));

    render(<App fetchImpl={fetchImpl} />);

    expect(await screen.findByRole('heading', { name: 'Taschengeldkasse' })).toBeInTheDocument();
    expect(fetchImpl.mock.calls[1][0]).toBe('/api/route-data/pocket-money/');
  });

  it('waits to show each personal SWP until all present kids are assigned for that week', () => {
    const data = dashboardData();
    data.focus_assignments_complete = { w1: false, w2: true };

    render(<DashboardPage data={data} />);

    expect(screen.queryByRole('heading', { name: 'SWP 1: Wald' })).not.toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'SWP 2: See' })).toBeInTheDocument();
  });

  it('waits to show a personal Happy Cleaning until all present kids are assigned', () => {
    const data = dashboardData();
    data.happy_cleanings[0].assignments_complete = false;

    render(<DashboardPage data={data} />);

    expect(screen.queryByRole('heading', { name: 'Happy Cleaning 1: Küche' })).not.toBeInTheDocument();
  });

  it('renders the dedicated pocket-money page as one compact card', () => {
    render(<PocketMoneyPage data={pocketMoneyData({
      ...emptyPage,
      items: [{
        id: 41,
        author: 'Ada',
        date: '2026-07-11T10:00:00Z',
        kid_id: 7,
        kid: 'Grace Hopper',
        amount: 3.4,
      }],
    })} />);

    const cashCard = screen.getByRole('heading', { name: 'Taschengeldkasse' }).closest('.card');
    const table = within(cashCard).getByRole('table');
    expect(document.querySelectorAll('.card')).toHaveLength(1);
    expect(cashCard).not.toHaveClass('transparent');
    expect(cashCard.parentElement).toHaveClass('max-w-[800px]');
    expect(cashCard).toHaveTextContent('Gesamt eingezahlt: 20.00 €');
    expect(cashCard).toHaveTextContent('Gesamt ausgegeben: 2.00 €');
    expect(cashCard).toHaveTextContent('Kassenstand: 18.00 €');
    expect(within(table).getAllByRole('columnheader').map(header => header.textContent)).toEqual([
      'Kind',
      'Datum',
      'Betrag',
      'Autor',
    ]);
    const row = within(table).getByRole('link', { name: 'Grace Hopper' }).closest('tr');
    expect(row).toHaveTextContent('Grace Hopper');
    expect(row).toHaveTextContent('11.07');
    expect(row).toHaveTextContent('3.40 €');
    expect(row).toHaveTextContent('Ada');
  });

  it('sorts station children by first name and toggles station To-Dos from the dashboard', async () => {
    const data = dashboardData();
    data.kids.push({
      ...data.kids[0],
      id: 8,
      full_name: 'Ada Lovelace',
    });
    data.happy_cleanings[0].stations[0].kid_ids = [7, 8];
    const mutate = vi.fn().mockResolvedValue({ ok: true });

    render(<DashboardPage data={data} mutate={mutate} />);

    const cleaningCard = screen.getByRole('heading', { name: 'Happy Cleaning 1: Küche' }).closest('.card');
    const kidsCard = within(cleaningCard).getByRole('heading', { name: 'Kinder' }).closest('.card');
    expect(within(kidsCard).getAllByRole('listitem').map(item => item.textContent)).toEqual([
      'Ada Lovelace',
      'Grace Hopper',
    ]);

    fireEvent.click(within(cleaningCard).getByRole('checkbox', { name: 'Boden fegen erledigen' }));
    await waitFor(() => expect(mutate).toHaveBeenCalledWith(
      '/api/happy-cleaning/events/21/stations/31/todos/101/check/',
      expect.objectContaining({ expected_version: 1, request_id: expect.any(String) }),
    ));
  });

  it('loads and appends the selected older activity page without duplicates', async () => {
    const fetchImpl = vi.fn().mockResolvedValue(response({
      activity: {
        notes: {
          items: [
            { id: 1, author: 'Ada', date: '2026-07-01T10:00:00Z', kid_id: 7, kid: 'Grace Hopper', text: 'Alt' },
            { id: 2, author: 'Ada', date: '2026-07-02T10:00:00Z', kid_id: 7, kid: 'Grace Hopper', text: 'Duplikat' },
          ],
          next_cursor: null,
          has_more: false,
          limit: 20,
        },
      },
    }));
    render(<DashboardPage
      data={dashboardData({
        notes: {
          items: [{ id: 2, author: 'Ada', date: '2026-07-02T10:00:00Z', kid_id: 7, kid: 'Grace Hopper', text: 'Neu' }],
          next_cursor: 'stable cursor',
          has_more: true,
          limit: 20,
        },
      })}
      fetchImpl={fetchImpl}
    />);

    fireEvent.click(screen.getByRole('button', { name: 'Ältere Notizen laden' }));

    await waitFor(() => expect(fetchImpl).toHaveBeenCalledWith(
      '/api/route-data/dashboard/?activity=notes&cursor=stable+cursor',
      { credentials: 'same-origin' },
    ));
    expect(await screen.findByText('Alt')).toBeInTheDocument();
    expect(screen.getByText('Neu')).toBeInTheDocument();
    expect(screen.queryByText('Duplikat')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Ältere Notizen laden' })).not.toBeInTheDocument();
  });

  it('renders first-aid activity and appends older EH entries', async () => {
    const fetchImpl = vi.fn().mockResolvedValue(response({
      activity: {
        first_aid: {
          items: [{ id: 8, author: 'Boris', date: '2026-07-01T10:00:00Z', kid_id: 7, kid: 'Grace Hopper', text: 'Hand gekühlt' }],
          next_cursor: null,
          has_more: false,
          limit: 20,
        },
      },
    }));
    render(<DashboardPage
      data={dashboardData({
        first_aid: {
          items: [{ id: 9, author: 'Ada', date: '2026-07-02T10:00:00Z', kid_id: 7, kid: 'Grace Hopper', text: 'Knie verbunden' }],
          next_cursor: 'eh cursor',
          has_more: true,
          limit: 20,
        },
      })}
      fetchImpl={fetchImpl}
    />);

    const card = screen.getByRole('heading', { name: 'Erste Hilfe' }).closest('.card');
    expect(card).toHaveTextContent('Ada am 02.07.2026: Grace Hopper');
    expect(card).toHaveTextContent('Knie verbunden');
    fireEvent.click(screen.getByRole('button', { name: 'Ältere EH-Einträge laden' }));

    await waitFor(() => expect(fetchImpl).toHaveBeenCalledWith(
      '/api/route-data/dashboard/?activity=first_aid&cursor=eh+cursor',
      { credentials: 'same-origin' },
    ));
    expect(await screen.findByText('Hand gekühlt')).toBeInTheDocument();
  });

  it('loads pocket-money activity from its dedicated endpoint and reports failures as toasts', async () => {
    const fetchImpl = vi.fn().mockResolvedValue(response({}, { ok: false, status: 503 }));
    render(<PocketMoneyPage
      data={pocketMoneyData({
        items: [],
        next_cursor: 'money-cursor',
        has_more: true,
        limit: 20,
      })}
      fetchImpl={fetchImpl}
    />);

    fireEvent.click(screen.getByRole('button', { name: 'Ältere Transaktionen laden' }));

    await waitFor(() => expect(fetchImpl).toHaveBeenCalledWith(
      '/api/route-data/pocket-money/?activity=transactions&cursor=money-cursor',
      { credentials: 'same-origin' },
    ));
    await expectErrorToastOnly('Ältere Transaktionen konnten nicht geladen werden.');
    expect(screen.getByRole('button', { name: 'Ältere Transaktionen laden' })).toBeEnabled();
  });

  it('uses the dashboard contract and renders its loading, success, and error states', async () => {
    expect(parseRoute('/dashboard')).toMatchObject({
      readContractKey: 'dashboard',
    });
    window.history.pushState({}, '', '/dashboard');
    let resolveRoute;
    const fetchImpl = vi.fn()
      .mockResolvedValueOnce(response({
        authenticated: true,
        csrf_token: 'token',
        messages: [],
        profile: { id: 1, rufname: 'Ada' },
        turnus: { id: 2, label: 'T2' },
        permissions: {},
        search_index: { kids: [], focuses: [], places: [] },
      }))
      .mockReturnValueOnce(new Promise(resolve => { resolveRoute = resolve; }));
    const { unmount } = render(<App fetchImpl={fetchImpl} />);

    expect(await screen.findByText('Seitendaten werden geladen…')).toBeInTheDocument();
    resolveRoute(response(dashboardData()));
    expect(await screen.findByRole('heading', { name: 'Kinder: 1' })).toBeInTheDocument();
    expect(fetchImpl.mock.calls[1][0]).toBe('/api/route-data/dashboard/');
    expect(fetchImpl.mock.calls.some(([url]) => url.startsWith('/api/app-data/'))).toBe(false);
    unmount();

    fetchImpl.mockReset()
      .mockResolvedValueOnce(response({
        authenticated: true,
        csrf_token: 'token',
        messages: [],
        profile: { id: 1, rufname: 'Ada' },
        turnus: { id: 2, label: 'T2' },
        permissions: {},
        search_index: { kids: [], focuses: [], places: [] },
      }))
      .mockResolvedValueOnce(response({}, { ok: false, status: 500 }));
    render(<App fetchImpl={fetchImpl} />);

    expect(await screen.findByRole('heading', { name: 'Seitendaten konnten nicht geladen werden' })).toBeInTheDocument();
  });
});
