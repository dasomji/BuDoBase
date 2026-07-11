import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { Card, GlobalSearch, RestForm, SearchTable } from './components';
import { parseRoute } from './App';
import { formatGermanDate, KidDetailPage, KidInteractionForm } from './pages';

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
      notes: [],
      transactions: [],
      remaining_money: 0,
      deposit: 0,
    };
    render(<KidDetailPage data={{ kids: [kid], turnus: { label: 'T2' }, csrf_token: 'token' }} id="7" mutate={vi.fn()} />);

    expect(screen.getByRole('heading', { name: title })).toBeInTheDocument();
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

  it('keeps form state in React and renders REST validation errors', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: false,
      json: async () => ({ ok: false, errors: ['Dieses Feld ist erforderlich.'] }),
    }));
    render(<RestForm target="/profil/" token="token"><input name="rufname" defaultValue="Ada" /><button type="submit">Speichern</button></RestForm>);

    fireEvent.click(screen.getByRole('button', { name: 'Speichern' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('Dieses Feld ist erforderlich.');
    expect(screen.getByDisplayValue('Ada')).toBeInTheDocument();
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
