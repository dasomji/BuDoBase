import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { Card, GlobalSearch, RestForm, SearchTable } from './components';
import { parseRoute } from './App';
import { CheckPage, formatGermanDate, formatKidBirthday, KidDetailPage, KidInteractionForm } from './pages';

describe('reusable components', () => {
  afterEach(cleanup);

  beforeEach(() => {
    window.matchMedia = vi.fn().mockImplementation(query => ({
      matches: query.includes('max-width') ? false : true,
      media: query,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    }));
  });

  it('toggles card details accessibly', () => {
    render(<Card title="Gesundheit"><p>Details</p></Card>);
    const button = screen.getByRole('button', { name: 'Gesundheit schließen' });

    expect(button).toHaveAttribute('aria-expanded', 'true');
    fireEvent.click(button);

    expect(screen.getByRole('button', { name: 'Gesundheit öffnen' })).toHaveAttribute('aria-expanded', 'false');
    expect(screen.getByText('Details').closest('.card-info-container')).toHaveAttribute('inert');
  });

  it('toggles a card from anywhere in its header', () => {
    render(<Card title="Gesundheit"><p>Details</p></Card>);

    fireEvent.click(screen.getByRole('heading', { name: 'Gesundheit' }));

    expect(screen.getByRole('button', { name: 'Gesundheit öffnen' })).toHaveAttribute('aria-expanded', 'false');
  });

  it('toggles a card header with the keyboard', () => {
    render(<Card title="Gesundheit"><p>Details</p></Card>);

    fireEvent.keyDown(screen.getByRole('button', { name: 'Gesundheit schließen' }), { key: ' ' });

    expect(screen.getByRole('button', { name: 'Gesundheit öffnen' })).toHaveAttribute('aria-expanded', 'false');
  });

  it('switches between the legacy note and pocket-money fields', () => {
    render(<KidInteractionForm kid={{ id: 7 }} token="token" />);

    expect(screen.getByPlaceholderText('Notiz...')).toBeVisible();
    expect(screen.getByPlaceholderText('Taschengeld...').closest('#geld-form')).toHaveClass('hidden');
    fireEvent.click(screen.getByText('Notiz'));

    expect(screen.getByPlaceholderText('Notiz...').closest('#notiz-form')).toHaveClass('hidden');
    expect(screen.getByPlaceholderText('Taschengeld...')).toBeVisible();
    expect(screen.getByPlaceholderText('Taschengeld...')).toHaveAttribute('min', '0');
    expect(screen.getByRole('button', { name: 'Abbuchen' })).toHaveClass('money-withdraw');
    expect(screen.getByRole('button', { name: 'Aufladen' })).toHaveClass('money-topup');
    expect(screen.queryByRole('button', { name: 'Senden' })).not.toBeInTheDocument();
  });

  it.each([
    { balance: 12.5, label: 'Taschengeld zurückgegeben (aktuell 12.50 €)', preset: 12.5 },
    { balance: -3, label: 'Taschengeld eingezahlt (schuldet aktuell: 3.00 €)', preset: 0 },
  ])('uses a positive checkout amount when the current balance is $balance', ({ balance, label, preset }) => {
    render(<CheckPage data={{ csrf_token: 'token', kids: [{ id: 7, full_name: 'Ada', pocket_money: balance }] }} id="7" checkout />);

    const amount = screen.getByRole('spinbutton', { name: label });
    expect(amount).toHaveValue(preset);
    expect(amount).toHaveAttribute('min', '0');
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
    const checkAction = screen.getByRole('link', { name: action });
    expect(checkAction).toHaveAttribute('href', path);
    expect(checkAction.closest('.card')).toHaveAttribute('id', 'budo-container');
  });

  it('shows selectable results from kids, focuses, and places', () => {
    render(<GlobalSearch data={{
      kids: [{ id: 1, full_name: 'Ada Lovelace', present: false }],
      focuses: [{ id: 2, name: 'Ada im Wald' }],
      places: [{ id: 3, name: 'Ada Hütte' }],
    }} />);

    const search = screen.getByRole('combobox', { name: 'Suche' });
    fireEvent.focus(search);
    fireEvent.change(search, { target: { value: 'ada' } });

    expect(screen.getByRole('option', { name: '❌ Ada Lovelace' })).toHaveAttribute('href', '/kid_details/1');
    expect(screen.getByRole('option', { name: '🚀Ada im Wald' })).toHaveAttribute('href', '/schwerpunkt/2');
    expect(screen.getByRole('option', { name: '🏡 Ada Hütte' })).toHaveAttribute('href', '/auslagerorte/3');
  });

  it('supports keyboard selection in the global search', () => {
    const onNavigate = vi.fn();
    render(<GlobalSearch data={{
      kids: [{ id: 1, full_name: 'Ada Lovelace', present: true }],
      focuses: [],
      places: [],
    }} onNavigate={onNavigate} />);
    const search = screen.getByRole('combobox', { name: 'Suche' });

    fireEvent.focus(search);
    fireEvent.change(search, { target: { value: 'ada' } });
    fireEvent.keyDown(search, { key: 'ArrowDown' });
    fireEvent.keyDown(search, { key: 'Enter' });

    expect(onNavigate).toHaveBeenCalledWith('/kid_details/1');
  });

  it('filters table pages by the first-column name only', () => {
    const columns = [{ key: 'name', label: 'Name' }];
    const rows = [
      { id: 1, name: 'Ada', filterText: 'Ada Lovelace', searchText: 'Ada Vienna' },
      { id: 2, name: 'Grace', filterText: 'Grace Hopper', searchText: 'Grace Ada' },
    ];

    render(<SearchTable columns={columns} rows={rows} showFilter />);
    fireEvent.change(screen.getByPlaceholderText('Kinder filtern...'), { target: { value: 'ada' } });

    expect(screen.getByText('Ada')).toBeInTheDocument();
    expect(screen.queryByText('Grace')).not.toBeInTheDocument();
  });

  it('does not add the child filter to ordinary tables', () => {
    render(<SearchTable columns={[{ key: 'name', label: 'Name' }]} rows={[]} />);

    expect(screen.queryByPlaceholderText('Kinder filtern...')).not.toBeInTheDocument();
  });

  it('sorts table columns by text, number, and underlying date values', () => {
    const columns = [
      { key: 'name', label: 'Name', render: row => row.full_name },
      { key: 'age', label: 'Alter' },
      { key: 'birthday_label', label: 'Geburtstag', render: row => row.birthday_label, sortValue: row => row.birthday },
    ];
    const rows = [
      { id: 1, full_name: 'Zora', age: 2, birthday: '2015-12-01', birthday_label: '01.12.2015' },
      { id: 2, full_name: 'Ada', age: 10, birthday: '2012-01-03', birthday_label: '03.01.2012' },
    ];
    const firstColumn = () => screen.getAllByRole('row').slice(1).map(row => row.querySelector('td').textContent);

    render(<SearchTable columns={columns} rows={rows} />);
    fireEvent.click(screen.getByRole('button', { name: 'Name sortieren' }));
    expect(firstColumn()).toEqual(['Ada', 'Zora']);
    expect(screen.getByRole('columnheader', { name: /Name/ })).toHaveAttribute('aria-sort', 'ascending');

    fireEvent.click(screen.getByRole('button', { name: 'Name absteigend sortieren' }));
    expect(firstColumn()).toEqual(['Zora', 'Ada']);
    fireEvent.click(screen.getByRole('button', { name: 'Alter sortieren' }));
    expect(firstColumn()).toEqual(['Zora', 'Ada']);
    fireEvent.click(screen.getByRole('button', { name: 'Geburtstag sortieren' }));
    expect(firstColumn()).toEqual(['Ada', 'Zora']);
  });

  it('keeps form state in React and renders REST validation errors', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      json: async () => ({ ok: false, errors: ['Dieses Feld ist erforderlich.'] }),
    });
    vi.stubGlobal('fetch', fetchMock);
    render(<RestForm target="/profil/" token="token"><input name="rufname" defaultValue="Ada" /><button type="submit" name="money_action" value="withdraw">Speichern</button></RestForm>);

    fireEvent.click(screen.getByRole('button', { name: 'Speichern' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('Dieses Feld ist erforderlich.');
    expect(screen.getByDisplayValue('Ada')).toBeInTheDocument();
    expect(fetchMock.mock.calls[0][1].body.get('money_action')).toBe('withdraw');
    vi.unstubAllGlobals();
  });
});

describe('German date formatting', () => {
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

describe('route inventory', () => {
  it.each([
    ['/kid_details/21', 'kid'],
    ['/schwerpunkt/3/update', 'focus-update'],
    ['/auslagerorte/4/upload-image/', 'place-images'],
    ['/swp-einteilung-w2', 'allocation'],
    ['/kindergeburtstage/', 'birthdays'],
  ])('maps %s to %s', (path, page) => {
    expect(parseRoute(path).page).toBe(page);
  });
});
