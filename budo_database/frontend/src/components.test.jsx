import { act, cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { Card, GlobalSearch, RestForm, SearchTable } from './components';

describe('reusable components', () => {
  afterEach(() => {
    cleanup();
    vi.useRealTimers();
  });

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

  it('shows selectable results from kids, focuses, and places', () => {
    render(<GlobalSearch data={{
      search_index: {
        kids: [{ id: 1, full_name: 'Ada Lovelace', present: false }],
        focuses: [{ id: 2, name: 'Ada im Wald' }],
        places: [{ id: 3, name: 'Ada Hütte' }],
      },
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
      search_index: {
        kids: [{ id: 1, full_name: 'Ada Lovelace', present: true }],
        focuses: [],
        places: [],
      },
    }} onNavigate={onNavigate} />);
    const search = screen.getByRole('combobox', { name: 'Suche' });

    fireEvent.focus(search);
    fireEvent.change(search, { target: { value: 'ada' } });
    fireEvent.keyDown(search, { key: 'ArrowDown' });
    fireEvent.keyDown(search, { key: 'Enter' });

    expect(onNavigate).toHaveBeenCalledWith('/kid_details/1');
  });

  it('matches German names case-insensitively and supports mouse selection', () => {
    const onNavigate = vi.fn();
    render(<GlobalSearch data={{
      search_index: {
        kids: [],
        focuses: [{ id: 2, name: 'Überleben' }],
        places: [{ id: 3, name: 'Ötscher Hütte' }],
      },
    }} onNavigate={onNavigate} />);
    const search = screen.getByRole('combobox', { name: 'Suche' });

    fireEvent.focus(search);
    fireEvent.change(search, { target: { value: 'ÜBERLEBEN' } });
    expect(screen.getByRole('option', { name: '🚀Überleben' })).toBeInTheDocument();

    fireEvent.change(search, { target: { value: 'ötscher' } });
    fireEvent.click(screen.getByRole('option', { name: '🏡 Ötscher Hütte' }));
    expect(onNavigate).toHaveBeenCalledWith('/auslagerorte/3');
  });

  it('supports ArrowUp and Escape while preserving focus behavior', () => {
    const onNavigate = vi.fn();
    render(<GlobalSearch data={{
      search_index: {
        kids: [{ id: 1, full_name: 'Ada Kind', present: true }],
        focuses: [{ id: 2, name: 'Ada Fokus' }],
        places: [],
      },
    }} onNavigate={onNavigate} />);
    const search = screen.getByRole('combobox', { name: 'Suche' });

    fireEvent.focus(search);
    fireEvent.change(search, { target: { value: 'ada' } });
    fireEvent.keyDown(search, { key: 'ArrowDown' });
    fireEvent.keyDown(search, { key: 'ArrowDown' });
    fireEvent.keyDown(search, { key: 'ArrowUp' });
    fireEvent.keyDown(search, { key: 'Enter' });
    expect(onNavigate).toHaveBeenCalledWith('/kid_details/1');

    fireEvent.keyDown(search, { key: 'Escape' });
    expect(search).toHaveAttribute('aria-expanded', 'false');
  });

  it('hides the result list at the existing twenty-result threshold', () => {
    render(<GlobalSearch data={{
      search_index: {
        kids: Array.from({ length: 20 }, (_, index) => ({
          id: index + 1,
          full_name: `Ada Kind ${index + 1}`,
          present: true,
        })),
        focuses: [],
        places: [],
      },
    }} />);
    const search = screen.getByRole('combobox', { name: 'Suche' });

    fireEvent.focus(search);
    fireEvent.change(search, { target: { value: 'ada' } });

    expect(search).toHaveAttribute('aria-expanded', 'false');
    expect(screen.queryByRole('option')).not.toBeInTheDocument();
  });

  it('closes results after the search field loses focus', () => {
    vi.useFakeTimers();
    render(<GlobalSearch data={{
      search_index: {
        kids: [{ id: 1, full_name: 'Ada Kind', present: true }],
        focuses: [],
        places: [],
      },
    }} />);
    const search = screen.getByRole('combobox', { name: 'Suche' });

    fireEvent.focus(search);
    fireEvent.change(search, { target: { value: 'ada' } });
    fireEvent.blur(search);
    act(() => vi.advanceTimersByTime(150));

    expect(search).toHaveAttribute('aria-expanded', 'false');
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
