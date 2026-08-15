import { cleanup, fireEvent, render as testingLibraryRender, screen, waitFor, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import App from '../App';
import { Toaster } from '../components/ui/toast';
import { parseRoute } from '../routes';
import { expectErrorToastOnly } from '../test-support';
import { KidDetailPage, KidInteractionForm, KidsPage } from './kids';
import { formatGermanDate, formatKidBirthday } from './shared';

const render = ui => testingLibraryRender(ui, {
  wrapper: ({ children }) => <Toaster timeout={0}>{children}</Toaster>,
});

const response = (data, { ok = true, status = 200 } = {}) => ({
  ok,
  status,
  json: vi.fn().mockResolvedValue(data),
});

function mockResponsiveContainerWidth(width) {
  vi.stubGlobal('ResizeObserver', class {
    constructor(callback) {
      this.callback = callback;
    }

    observe(target) {
      this.callback([{ contentRect: { width }, target }]);
    }

    disconnect() {}
  });
}

describe('Kinder pages', () => {
  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
    window.history.pushState({}, '', '/');
  });

  beforeEach(() => {
    document.cookie = 'kid-detail-activity=; Max-Age=0; Path=/';
    window.matchMedia = vi.fn().mockImplementation(query => ({
      matches: query.includes('max-width') ? false : true,
      media: query,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    }));
  });

  it('saves money from its dedicated form without navigating', async () => {
    const onSaved = vi.fn();
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ ok: true }) });
    vi.stubGlobal('fetch', fetchMock);
    render(<KidInteractionForm kid={{ id: 7 }} token="token" onSaved={onSaved} kind="money" />);

    const amount = screen.getByPlaceholderText('Taschengeld...');
    expect(amount).toBeVisible();
    expect(amount).toHaveAttribute('data-slot', 'input');
    expect(amount).toHaveAttribute('min', '0');
    expect(screen.getByRole('button', { name: 'Abbuchen' })).toBeEnabled();
    expect(screen.getByRole('button', { name: 'Aufladen' })).toBeEnabled();
    fireEvent.change(amount, { target: { value: '5' } });
    fireEvent.click(screen.getByRole('button', { name: 'Abbuchen' }));

    await waitFor(() => expect(onSaved).toHaveBeenCalledOnce());
    expect(fetchMock.mock.calls[0][1].body.get('money_action')).toBe('withdraw');
    expect(amount).toHaveValue(null);
  });

  it('switches to Erste Hilfe and submits a required description', async () => {
    const onSaved = vi.fn();
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ ok: true }),
    });
    vi.stubGlobal('fetch', fetchMock);
    render(<KidInteractionForm kid={{ id: 7 }} token="token" onSaved={onSaved} kind="first_aid" />);

    const description = screen.getByPlaceholderText('Erste-Hilfe-Maßnahme...');
    const guidance = screen.getByText('Was ist passiert und welche Maßnahme wurde getroffen?');
    expect(description).toBeVisible();
    expect(guidance).toBeVisible();
    expect(screen.getByLabelText('Was ist passiert und welche Maßnahme wurde getroffen?')).toBe(description);
    expect(guidance.compareDocumentPosition(description) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(description.tagName).toBe('TEXTAREA');
    expect(description).toHaveAttribute('rows', '1');
    expect(description).toBeRequired();
    expect(description).toHaveAttribute('data-slot', 'textarea');
    expect(screen.getByRole('button', { name: 'Fotos für Erste Hilfe auswählen' }).querySelector('.lucide-image-plus')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'EH-Eintrag senden' })).toHaveTextContent('➤');
    fireEvent.change(description, { target: { value: 'Knie verbunden' } });
    fireEvent.click(screen.getByRole('button', { name: 'EH-Eintrag senden' }));

    await waitFor(() => expect(onSaved).toHaveBeenCalledOnce());
    const body = fetchMock.mock.calls[0][1].body;
    expect(body.get('interaction_kind')).toBe('first_aid');
    expect(body.get('erste_hilfe_beschreibung')).toBe('Knie verbunden');
    expect(description).toHaveValue('');
  });

  it('submits note image attachments through the shared image control', async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ ok: true }) });
    vi.stubGlobal('fetch', fetchMock);
    render(<KidInteractionForm kid={{ id: 7 }} token="token" />);

    const input = screen.getByLabelText('Notiz-Fotos');
    const photo = new File(['photo'], 'iphone.heic', { type: 'image/heic' });
    expect(input).toHaveAttribute('type', 'file');
    expect(input).toHaveAttribute('multiple');
    const photoButton = screen.getByRole('button', { name: 'Fotos zur Notiz auswählen' });
    const inputClick = vi.spyOn(input, 'click');
    fireEvent.click(photoButton);
    expect(inputClick).toHaveBeenCalledOnce();
    fireEvent.change(screen.getByPlaceholderText('Notiz...'), { target: { value: 'Mit Foto' } });
    fireEvent.change(input, { target: { files: [photo] } });
    expect(screen.getByPlaceholderText('Notiz...')).toHaveAttribute('rows', '1');
    expect(document.querySelector('[data-slot="attachment-count"]')).toHaveTextContent('1');
    expect(photoButton.querySelector('.lucide-image-plus')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Notiz senden' })).toHaveTextContent('➤');
    fireEvent.click(screen.getByRole('button', { name: 'Notiz senden' }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledOnce());
    const body = fetchMock.mock.calls[0][1].body;
    expect(body.get('notiz')).toBe('Mit Foto');
    expect(body.getAll('notiz_fotos')).toEqual([photo]);
  });

  it('shows the server validation message for a blank first-aid description', async () => {
    const fetchMock = vi.fn().mockResolvedValue(response(
      { ok: false, errors: ['Bitte eine Beschreibung eingeben.'] },
      { ok: false, status: 422 },
    ));
    vi.stubGlobal('fetch', fetchMock);
    render(<KidInteractionForm kid={{ id: 7 }} token="token" kind="first_aid" />);

    fireEvent.change(screen.getByPlaceholderText('Erste-Hilfe-Maßnahme...'), {
      target: { value: '   ' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'EH-Eintrag senden' }));

    await expectErrorToastOnly('Bitte eine Beschreibung eingeben.');
  });

  it('keeps each input in its owning activity card and enforces accordion behavior', () => {
    const kid = {
      id: 7,
      full_name: 'Ada Lovelace',
      present: true,
      weeks: 2,
      booking_note: 'Buchungsnotiz',
      note: 'Anmerkung',
      notes: [{ id: 4, author: 'Nora', date: '2026-07-04', text: 'Neueste Notiz' }],
      first_aid_entries: [{ id: 5, author: 'Emil', date: '2026-07-05', text: 'Knie verbunden' }],
      transactions: [{ id: 6, author: 'Mia', date: '2026-07-06', amount: 5 }],
      remaining_money: 9.5,
      deposit: 2,
    };
    render(<KidDetailPage data={{ kids: [kid], csrf_token: 'token' }} id="7" mutate={vi.fn()} />);

    const notesCard = screen.getByRole('heading', { name: 'Notizen' }).closest('.card');
    const firstAidCard = screen.getByRole('heading', { name: 'Erste Hilfe' }).closest('.card');
    const moneyCard = screen.getByRole('heading', { name: 'Taschengeld: 9.50 €' }).closest('.card');
    expect(within(notesCard).getByPlaceholderText('Notiz...')).toBeInTheDocument();
    expect(within(firstAidCard).getByPlaceholderText('Erste-Hilfe-Maßnahme...')).toBeInTheDocument();
    expect(within(moneyCard).getByPlaceholderText('Taschengeld...')).toBeInTheDocument();
    expect(notesCard).not.toHaveClass('closed-card');
    expect(firstAidCard).toHaveClass('closed-card');
    expect(moneyCard).toHaveClass('closed-card');

    fireEvent.click(screen.getByRole('button', { name: 'Erste Hilfe öffnen' }));
    expect(notesCard).toHaveClass('closed-card');
    expect(firstAidCard).not.toHaveClass('closed-card');
    fireEvent.click(screen.getByRole('button', { name: 'Erste Hilfe schließen' }));
    expect(notesCard).toHaveClass('closed-card');
    expect(firstAidCard).toHaveClass('closed-card');
    expect(moneyCard).toHaveClass('closed-card');

    fireEvent.click(screen.getByRole('button', { name: 'Taschengeld: 9.50 € öffnen' }));
    expect(moneyCard).not.toHaveClass('closed-card');
    const notesContent = notesCard.querySelector('.card-info-content');
    expect([...notesContent.children].map(child => child.tagName)).toEqual(['P', 'P', 'FORM', 'UL']);
    const moneyContent = moneyCard.querySelector('.card-info-content');
    expect([...moneyContent.children].map(child => child.tagName)).toEqual(['DIV', 'FORM', 'DIV']);
    expect(within(moneyCard).getByLabelText('Pfand')).toHaveTextContent('Pfand:−Pfand2 (0.50 €)+Pfand');
    const transactionTable = within(moneyCard).getByRole('table');
    expect(within(transactionTable).getAllByRole('columnheader').map(header => header.textContent)).toEqual([
      'Author',
      'Datum',
      'Betrag',
    ]);
    const transactionRow = within(transactionTable).getByText('Mia').closest('tr');
    expect(transactionRow).toHaveTextContent('Mia');
    expect(transactionRow).toHaveTextContent('06.07');
    expect(transactionRow).toHaveTextContent('5.00 €');
    expect(document.querySelector('#pfand')).not.toBeInTheDocument();
  });

  it('restores the open activity card when moving to another child', () => {
    const kid = {
      id: 7,
      full_name: 'Ada Lovelace',
      present: true,
      weeks: 2,
      notes: [],
      first_aid_entries: [],
      transactions: [],
      remaining_money: 10,
      deposit: 0,
    };
    const { unmount } = render(<KidDetailPage data={{ kids: [kid], csrf_token: 'token' }} id="7" mutate={vi.fn()} />);

    fireEvent.click(screen.getByRole('button', { name: 'Erste Hilfe öffnen' }));
    expect(document.cookie).toContain('kid-detail-activity=first_aid');
    unmount();

    const nextKid = { ...kid, id: 8, full_name: 'Grace Hopper' };
    render(<KidDetailPage data={{ kids: [nextKid], csrf_token: 'token' }} id="8" mutate={vi.fn()} />);

    expect(screen.getByRole('heading', { name: 'Notizen' }).closest('.card')).toHaveClass('closed-card');
    expect(screen.getByRole('heading', { name: 'Erste Hilfe' }).closest('.card')).not.toHaveClass('closed-card');
    expect(screen.getByRole('heading', { name: 'Taschengeld: 10.00 €' }).closest('.card')).toHaveClass('closed-card');
  });

  it.each([
    { present: false, action: 'Einchecken', path: '/check_in/7', title: 'Ada Lovelace ❌' },
    { present: true, action: 'Auschecken', path: '/check_out/7', title: 'Ada Lovelace' },
  ])('places $action in the BuDo card and reflects attendance in the name', ({ present, action, path, title }) => {
    const kid = {
      id: 7,
      full_name: 'Ada Lovelace',
      present,
      weeks: 2,
      birthday: '2012-07-02',
      social_security_number: '1234 030712',
      consent: present ? false : null,
      over_the_counter_medication: 'Ibuprofen',
      prescription_medication: '',
      tetanus: null,
      tick_vaccine: 'Ja',
      notes: [],
      first_aid_entries: [
        { id: 3, author: 'Boris', date: '2026-07-03T10:00:00Z', text: 'Knie verbunden' },
      ],
      transactions: [],
      remaining_money: 0,
      deposit: 0,
    };
    render(<KidDetailPage data={{ kids: [kid], turnus: { label: 'T2' }, csrf_token: 'token' }} id="7" mutate={vi.fn()} />);

    expect(screen.getByRole('heading', { name: title })).toBeInTheDocument();
    expect(screen.getByText('Geburtstag').closest('p')).toHaveTextContent('Geburtstag: 02.07.2012 ❗');
    expect(screen.getByText('Einverständnis für ärztliche Behandlung').closest('p')).toHaveTextContent(`Einverständnis für ärztliche Behandlung: ${present ? 'Nein' : '❗'}`);
    expect(screen.getByText('Rezeptfreie Medikamente').closest('p')).toHaveTextContent('Rezeptfreie Medikamente: Ibuprofen');
    expect(screen.getByText('Medikamente auf Rezept').closest('p')).toHaveTextContent('Medikamente auf Rezept: ❗');
    expect(screen.getByText('Tetanusimpfung').closest('p')).toHaveTextContent('Tetanusimpfung: ❗');
    expect(screen.getByText('Zeckenimpfung').closest('p')).toHaveTextContent('Zeckenimpfung: Ja');
    const firstAidCard = screen.getByRole('heading', { name: 'Erste Hilfe' }).closest('.card');
    expect(firstAidCard).toHaveTextContent('Boris am 03.07.2026: Knie verbunden');
    const checkAction = screen.getByRole('link', { name: action });
    expect(checkAction).toHaveAttribute('href', path);
    expect(checkAction.closest('.card')).toHaveAttribute('id', 'budo-container');
  });

  it('renders dynamic Schwerpunkt and Happy Cleaning rows from the detail contract', () => {
    const kid = {
      id: 7,
      full_name: 'Ada Lovelace',
      present: true,
      weeks: 2,
      notes: [],
      first_aid_entries: [],
      transactions: [],
      remaining_money: 0,
      deposit: 0,
      focus_assignments: [
        {
          period_id: 12,
          code: 'w2',
          label: 'Woche 2 (2 Tage)',
          focuses: [{ id: 4, label: 'Wald' }],
        },
        {
          period_id: 13,
          code: 'u',
          label: 'unklar (1 Tag)',
          focuses: [],
        },
        {
          period_id: 11,
          code: 'w1',
          label: 'Woche 1 (3 Tage)',
          focuses: [
            { id: 5, label: 'alpha' },
            { id: 6, label: 'Alpha' },
          ],
        },
      ],
      happy_cleaning_number: 42,
      happy_cleaning_assignments: [
        {
          event_id: 21,
          display_number: 1,
          label: 'Happy Cleaning 1',
          target: { kind: 'excused', label: 'Entschuldigt' },
        },
        {
          event_id: 22,
          display_number: 2,
          label: 'Happy Cleaning 2',
          target: { kind: 'station', station_id: 31, label: 'Küche <Nord>' },
        },
        {
          event_id: 23,
          display_number: 3,
          label: 'Happy Cleaning 3',
          target: { kind: 'unassigned', label: 'Nicht eingeteilt' },
        },
      ],
    };

    render(<KidDetailPage data={{ kids: [kid], turnus: { label: 'T2' }, csrf_token: 'token' }} id="7" mutate={vi.fn()} />);

    const budoCard = screen.getByRole('heading', { name: 'BuDo' }).closest('.card');
    expect(within(budoCard).getByText('Woche 2 (2 Tage)').closest('p')).toHaveTextContent('Woche 2 (2 Tage): Wald');
    expect(within(budoCard).getByText('unklar (1 Tag)').closest('p')).toHaveTextContent('unklar (1 Tag): ---');
    expect(within(budoCard).getByText('Woche 1 (3 Tage)').closest('p')).toHaveTextContent('Woche 1 (3 Tage): alpha, Alpha');
    expect(within(budoCard).getByText('Happy Cleaning Nummer').closest('p')).toHaveTextContent('Happy Cleaning Nummer: 42');
    expect(within(budoCard).getByText('Happy Cleaning 1').closest('p')).toHaveTextContent('Happy Cleaning 1: Entschuldigt');
    expect(within(budoCard).getByText('Happy Cleaning 2').closest('p')).toHaveTextContent('Happy Cleaning 2: Küche <Nord>');
    expect(within(budoCard).getByText('Happy Cleaning 3').closest('p')).toHaveTextContent('Happy Cleaning 3: Nicht eingeteilt');
    expect(budoCard.querySelector('nord')).toBeNull();
    expect(within(budoCard).queryByText('SWP 1')).not.toBeInTheDocument();
    expect(within(budoCard).queryByText('SWP 2')).not.toBeInTheDocument();
  });

  it('renders safe dynamic-detail placeholders when periods and cleaning data are empty', () => {
    const kid = {
      id: 7,
      full_name: 'Ada Lovelace',
      present: true,
      weeks: 2,
      notes: [],
      first_aid_entries: [],
      transactions: [],
      remaining_money: 0,
      deposit: 0,
      focus_assignments: [],
      happy_cleaning_number: null,
      happy_cleaning_assignments: [],
    };

    render(<KidDetailPage data={{ kids: [kid], turnus: { label: 'T2' }, csrf_token: 'token' }} id="7" mutate={vi.fn()} />);

    const budoCard = screen.getByRole('heading', { name: 'BuDo' }).closest('.card');
    expect(within(budoCard).getByText('Schwerpunkte').closest('p')).toHaveTextContent('Schwerpunkte: ---');
    expect(within(budoCard).getByText('Happy Cleaning Nummer').closest('p')).toHaveTextContent('Happy Cleaning Nummer: ---');
    expect(within(budoCard).getByText('Happy Cleaning').closest('p')).toHaveTextContent('Happy Cleaning: ---');
    expect(within(budoCard).queryByText('SWP 1')).not.toBeInTheDocument();
    expect(within(budoCard).queryByText('SWP 2')).not.toBeInTheDocument();
  });

  it('uses the dashboard card grid at its two-column available-width breakpoint', async () => {
    mockResponsiveContainerWidth(800);
    const kid = {
      id: 7,
      full_name: 'Ada Lovelace',
      present: true,
      weeks: 2,
      notes: [],
      first_aid_entries: [],
      transactions: [],
      remaining_money: 0,
      deposit: 0,
    };

    render(<KidDetailPage data={{ kids: [kid], turnus: { label: 'T2' }, csrf_token: 'token' }} id="7" mutate={vi.fn()} />);

    const main = screen.getByRole('main');
    await waitFor(() => expect(main.querySelectorAll('[data-card-column]')).toHaveLength(2));
    const cardColumns = main.querySelectorAll('[data-card-column]');
    expect(cardColumns[0]).toHaveTextContent('Ada Lovelace');
    expect(cardColumns[0]).toHaveTextContent('Notizen');
    expect(cardColumns[1]).toHaveTextContent('Gesundheitsinfos');
  });

  it('shows failed deposit writes as error toasts, never inline', async () => {
    const mutate = vi.fn().mockRejectedValue(new Error('network down'));
    const kid = {
      id: 7,
      full_name: 'Ada Lovelace',
      present: true,
      weeks: 2,
      notes: [],
      first_aid_entries: [],
      transactions: [],
      remaining_money: 0,
      deposit: 0,
    };
    render(<KidDetailPage data={{ kids: [kid], csrf_token: 'token' }} id="7" mutate={mutate} />);

    fireEvent.click(screen.getByRole('button', { name: /Taschengeld: 0.00 €.*öffnen/ }));
    fireEvent.click(screen.getByRole('button', { name: 'Pfand erhöhen' }));

    await expectErrorToastOnly('Das Pfand konnte nicht gespeichert werden.');
  });

  it('keeps the directory columns, filtering, sorting, links, and empty state on focused rows', () => {
    const { rerender } = render(<KidsPage data={{ kids: [
      {
        id: 8,
        full_name: 'Grace Hopper',
        present: true,
        budo_family: 'L',
        sex_short: '♀',
        age: 14,
        weeks: 2,
        focus_w1: 'Wald',
        focus_w2: 'Theater',
        siblings: '---',
        tent_request: 'Ada',
        food: '🌱',
        drugs: '',
        illness: '',
        note: '',
        booking_note: '',
      },
      {
        id: 7,
        full_name: 'Ada Lovelace',
        present: false,
        budo_family: 'M',
        sex_short: '♀',
        age: 13,
        weeks: 1,
        focus_w1: 'Theater',
        focus_w2: 'Wald',
        siblings: 'Charles',
        tent_request: 'Grace',
        food: '🥩',
        drugs: 'Asthmaspray',
        illness: 'Allergie',
        note: 'Teamnotiz',
        booking_note: 'Buchungsnotiz',
      },
    ] }} />);

    const table = screen.getByRole('table');
    expect(table).not.toHaveAttribute('id');
    expect(table.parentElement).toHaveAttribute('data-sticky-header');
    expect(table.parentElement).toHaveAttribute('data-sticky-first-column');
    expect(table.parentElement).toHaveAttribute('data-vertical-scroll');
    expect(screen.getByRole('columnheader', { name: /Zeltwunsch/ })).toHaveAttribute('data-priority', 'low');
    expect(screen.queryByRole('columnheader', { name: 'Haus' })).not.toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Ada Lovelace ❌' })).toHaveAttribute('href', '/kid_details/7');
    expect(screen.getByRole('columnheader', { name: /Anmerkungen \(Buchung\)/ })).toBeInTheDocument();
    fireEvent.change(screen.getByRole('searchbox', { name: 'Kinder filtern' }), { target: { value: 'grace' } });
    expect(screen.getByRole('link', { name: 'Grace Hopper' })).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: 'Ada Lovelace ❌' })).not.toBeInTheDocument();

    fireEvent.change(screen.getByRole('searchbox', { name: 'Kinder filtern' }), { target: { value: '' } });
    fireEvent.click(screen.getByRole('button', { name: 'Alter sortieren' }));
    expect(screen.getAllByRole('row')[1]).toHaveTextContent('Ada Lovelace');

    rerender(<KidsPage data={{ kids: [] }} />);
    expect(screen.getByText('Keine Einträge')).toBeInTheDocument();
  });

  it('declares the Kinder directory and detail contracts', () => {
    expect(parseRoute('/all_kids')).toMatchObject({
      readContractKey: 'kids-directory',
    });
    expect(parseRoute('/kid_details/21')).toMatchObject({
      readContractKey: 'kid-detail',
      id: '21',
    });
  });

  it('refreshes only the selected Kind contract after a Pfand update', async () => {
    window.history.pushState({}, '', '/kid_details/7');
    let detailReads = 0;
    const fetchImpl = vi.fn(async (url) => {
      if (url === '/api/bootstrap/') {
        return response({
          authenticated: true,
          csrf_token: 'token',
          messages: [],
          profile: { id: 1, rufname: 'Ada' },
          turnus: { id: 2, label: 'T2' },
          permissions: { change_kids: true },
          search_index: { kids: [{ id: 7, full_name: 'Ada Lovelace', present: true }], focuses: [], places: [] },
        });
      }
      if (url === '/api/route-data/kid-detail/?id=7') {
        detailReads += 1;
        const deposit = detailReads;
        return response({
          kids: [{
            id: 7,
            full_name: 'Ada Lovelace',
            present: true,
            weeks: 2,
            birthday: '2012-07-02',
            notes: [],
            transactions: [],
            remaining_money: 10 - deposit * 0.25,
            deposit,
          }],
        });
      }
      if (url === '/update_pfand/') return response({ status: 'success' });
      throw new Error(`Unexpected request: ${url}`);
    });

    render(<App fetchImpl={fetchImpl} />);

    expect(await screen.findByRole('heading', { name: 'Taschengeld: 9.75 €' })).toBeInTheDocument();
    expect(document.querySelector('#headertitle h1 a')).toHaveAttribute('href', '/admin/budo_app/kinder/7/change/');
    fireEvent.click(screen.getByRole('button', { name: 'Taschengeld: 9.75 € öffnen' }));
    expect(screen.getByLabelText('Pfand')).toHaveTextContent('1 (0.25 €)');
    fireEvent.click(await screen.findByRole('button', { name: 'Pfand erhöhen' }));
    expect(await screen.findByRole('heading', { name: 'Taschengeld: 9.50 €' })).toBeInTheDocument();
    expect(screen.getByLabelText('Pfand')).toHaveTextContent('2 (0.50 €)');

    expect(detailReads).toBe(2);
    expect(fetchImpl.mock.calls.filter(([url]) => url === '/api/bootstrap/')).toHaveLength(1);
    expect(fetchImpl.mock.calls.some(([url]) => url.startsWith('/api/app-data/'))).toBe(false);
  });

});

describe('Kinder date formatting', () => {
  it('formats API dates and datetimes without timezone shifts', () => {
    expect(formatGermanDate('2026-07-02')).toBe('02.07.2026');
    expect(formatGermanDate('2026-07-02T23:30:00Z')).toBe('02.07.2026');
  });

  it('leaves non-date values unchanged', () => {
    expect(formatGermanDate('---')).toBe('---');
    expect(formatGermanDate(null)).toBeNull();
  });

  it.each([
    ['matching birthday', '1234 020712', '02.07.2012'],
    ['mismatching birthday', '1234 030712', '02.07.2012 ❗'],
    ['unavailable SV birthday', 'invalid', '02.07.2012'],
    ['invalid calculated birthday', '1234 310212', '02.07.2012'],
  ])('marks a %s only when the calculated SV birthday differs', (_case, socialSecurityNumber, expected) => {
    expect(formatKidBirthday({
      birthday: '2012-07-02',
      social_security_number: socialSecurityNumber,
    })).toBe(expected);
  });
});
