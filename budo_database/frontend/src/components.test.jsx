import { StrictMode } from 'react';
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { Printer } from 'lucide-react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { AppSidebar, ApplicationShell } from './app-sidebar';
import {
  Card,
  DataTable,
  GlobalSearch,
  Header,
  Messages,
  RestForm,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
  TableScroll,
} from './components';
import { Button } from './components/ui/button';
import { Toaster } from './components/ui/toast';

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

  it('renders the link variant as a named link', () => {
    render(<Button variant="link" href="/profil/">Profil öffnen</Button>);

    expect(screen.getByRole('link', { name: 'Profil öffnen' })).toHaveAttribute('href', '/profil/');
  });

  it('prevents disabled links from activating', () => {
    const onClick = vi.fn();
    render(<Button variant="link" href="/profil/" disabled onClick={onClick}>Profil öffnen</Button>);

    const link = screen.getByRole('link', { name: 'Profil öffnen' });
    expect(link).toHaveAttribute('aria-disabled', 'true');
    fireEvent.click(link);
    expect(onClick).not.toHaveBeenCalled();
  });

  it('renders each action variant as a named button', () => {
    render(
      <>
        <Button>Primäraktion</Button>
        <Button variant="secondary">Sekundäraktion</Button>
        <Button variant="success">Erfolgsaktion</Button>
        <Button variant="destructive">Löschaktion</Button>
        <Button variant="ghost">Leise Aktion</Button>
      </>,
    );

    for (const name of ['Primäraktion', 'Sekundäraktion', 'Erfolgsaktion', 'Löschaktion', 'Leise Aktion']) {
      expect(screen.getByRole('button', { name })).toBeEnabled();
    }
  });

  it('keeps disabled actions named and inactive', () => {
    const onClick = vi.fn();
    render(<Button disabled onClick={onClick}>Speichern</Button>);

    const button = screen.getByRole('button', { name: 'Speichern' });
    expect(button).toBeDisabled();
    fireEvent.click(button);
    expect(onClick).not.toHaveBeenCalled();
  });

  it('exposes an icon action by its aria-label while hiding its icon', () => {
    render(
      <Button size="icon" aria-label="Drucken">
        <Printer />
      </Button>,
    );

    const button = screen.getByRole('button', { name: 'Drucken' });
    expect(button.querySelector('svg')).toHaveAttribute('aria-hidden', 'true');
  });

  it('orders mobile header controls as title, action, search, and burger', async () => {
    vi.spyOn(window, 'innerWidth', 'get').mockReturnValue(390);
    render(
      <ApplicationShell
        sidebar={<AppSidebar />}
        header={(
          <Header
            title="Küche"
            authenticated
            searchData={{ search_index: { kids: [], focuses: [], places: [] } }}
            action={(
              <Button size="icon" aria-label="Drucken">
                <Printer aria-hidden="true" />
              </Button>
            )}
          />
        )}
      >
        <div>Inhalt</div>
      </ApplicationShell>,
    );

    const title = screen.getByRole('heading', { name: 'Küche' });
    const action = screen.getByRole('button', { name: 'Drucken' });
    const search = await screen.findByRole('button', { name: 'Suche öffnen' });
    const burger = await screen.findByRole('button', { name: 'Sidebar ein- oder ausklappen' });

    await waitFor(() => {
      expect(title.compareDocumentPosition(action) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
      expect(action.compareDocumentPosition(search) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
      expect(search.compareDocumentPosition(burger) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    });

    fireEvent.click(search);
    expect(screen.getByRole('button', { name: 'Suche schließen' })).toHaveAttribute('aria-expanded', 'true');
    fireEvent.click(screen.getByRole('button', { name: 'Suche schließen' }));
    expect(screen.getByRole('button', { name: 'Suche öffnen' })).toHaveAttribute('aria-expanded', 'false');

    fireEvent.click(burger);
    expect(await screen.findByRole('dialog', { name: 'Sidebar' })).toBeInTheDocument();
  });

  it('orders desktop header controls as trigger, title, search, and action', async () => {
    vi.spyOn(window, 'innerWidth', 'get').mockReturnValue(1280);
    render(
      <ApplicationShell
        sidebar={<AppSidebar />}
        header={(
          <Header
            title="Küche"
            authenticated
            searchData={{ search_index: { kids: [], focuses: [], places: [] } }}
            action={<Button aria-label="Drucken">Drucken</Button>}
          />
        )}
      >
        <div>Inhalt</div>
      </ApplicationShell>,
    );

    const trigger = screen.getByRole('button', { name: 'Sidebar ein- oder ausklappen' });
    const title = screen.getByRole('heading', { name: 'Küche' });
    const search = screen.getByRole('combobox', { name: 'Suche' });
    const action = screen.getByRole('button', { name: 'Drucken' });

    await waitFor(() => {
      expect(trigger.compareDocumentPosition(title) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
      expect(title.compareDocumentPosition(search) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
      expect(search.compareDocumentPosition(action) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    });
    expect(screen.queryByRole('button', { name: 'Suche öffnen' })).not.toBeInTheDocument();
  });

  it('publishes and cleans up the measured header height contract', () => {
    const bounds = vi.spyOn(Element.prototype, 'getBoundingClientRect').mockReturnValue({
      width: 800,
      height: 64,
      top: 0,
      right: 800,
      bottom: 64,
      left: 0,
      x: 0,
      y: 0,
      toJSON: () => ({}),
    });
    const view = render(
      <ApplicationShell
        header={<Header title="Dashboard" authenticated={false} />}
      >
        <div>Inhalt</div>
      </ApplicationShell>,
    );

    expect(document.documentElement.style.getPropertyValue('--app-header-height')).toBe('64px');

    view.unmount();
    expect(document.documentElement.style.getPropertyValue('--app-header-height')).toBe('');
    bounds.mockRestore();
  });

  it('publishes Django messages as typed toasts only once', async () => {
    const messages = [
      { text: 'Willkommen zurück!', tags: 'success account' },
      { text: 'Speichern fehlgeschlagen.', tags: 'error' },
    ];
    const toastTree = items => (
      <StrictMode>
        <Toaster timeout={0}>
          <Messages items={items} />
        </Toaster>
      </StrictMode>
    );
    const view = render(toastTree(messages));

    const success = await screen.findByText('Willkommen zurück!', { selector: '.app-toast-description' });
    const error = await screen.findByText('Speichern fehlgeschlagen.', { selector: '.app-toast-description' });
    expect(success.closest('.app-toast')).toHaveAttribute('data-type', 'success');
    expect(error.closest('.app-toast')).toHaveAttribute('data-type', 'error');
    expect(document.querySelector('.messages')).not.toBeInTheDocument();

    view.rerender(toastTree(messages.map(message => ({ ...message }))));

    expect(screen.getAllByText('Willkommen zurück!', { selector: '.app-toast-description' })).toHaveLength(1);
    expect(screen.getAllByText('Speichern fehlgeschlagen.', { selector: '.app-toast-description' })).toHaveLength(1);
  });

  it('toggles card details accessibly', () => {
    render(<Card title="Gesundheit"><p>Details</p></Card>);
    const button = screen.getByRole('button', { name: 'Gesundheit schließen' });

    expect(button).toHaveAttribute('aria-expanded', 'true');
    expect(screen.queryByText('−')).not.toBeInTheDocument();
    fireEvent.click(button);

    expect(screen.getByRole('button', { name: 'Gesundheit öffnen' })).toHaveAttribute('aria-expanded', 'false');
    expect(screen.getByText('Details').closest('.card-info-container')).toHaveAttribute('inert');
    expect(screen.queryByText('+')).not.toBeInTheDocument();
  });

  it('toggles a card from anywhere in its header', () => {
    render(<Card title="Gesundheit"><p>Details</p></Card>);

    fireEvent.click(screen.getByRole('heading', { name: 'Gesundheit' }));

    expect(screen.getByRole('button', { name: 'Gesundheit öffnen' })).toHaveAttribute('aria-expanded', 'false');
  });

  it('shows the open and closed state on transparent cards', () => {
    render(<Card title="Karte" className="transparent"><p>Orte</p></Card>);

    expect(screen.getByText('−')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('heading', { name: 'Karte' }));

    expect(screen.getByText('+')).toBeInTheDocument();
  });

  it('runs a header action without toggling the card', () => {
    const handleAction = vi.fn();
    render(
      <Card
        title="Woche 1"
        headerAction={<button type="button" onClick={handleAction}>Kinder einteilen</button>}
      >
        <p>Details</p>
      </Card>,
    );

    fireEvent.click(screen.getByRole('button', { name: 'Kinder einteilen' }));

    expect(handleAction).toHaveBeenCalledOnce();
    expect(screen.getByRole('button', { name: 'Woche 1 schließen' })).toHaveAttribute('aria-expanded', 'true');
    expect(screen.getByText('Details').closest('[aria-hidden]')).not.toHaveAttribute('inert');
  });

  it('toggles a card header with the keyboard', () => {
    render(<Card title="Gesundheit"><p>Details</p></Card>);
    const details = screen.getByText('Details').closest('[aria-hidden]');

    fireEvent.keyDown(screen.getByRole('button', { name: 'Gesundheit schließen' }), { key: ' ' });

    expect(screen.getByRole('button', { name: 'Gesundheit öffnen' })).toHaveAttribute('aria-expanded', 'false');
    expect(details).toHaveAttribute('aria-hidden', 'true');
    expect(details).toHaveAttribute('inert');

    fireEvent.keyDown(screen.getByRole('button', { name: 'Gesundheit öffnen' }), { key: 'Enter' });

    expect(screen.getByRole('button', { name: 'Gesundheit schließen' })).toHaveAttribute('aria-expanded', 'true');
    expect(details).toHaveAttribute('aria-hidden', 'false');
    expect(details).not.toHaveAttribute('inert');
  });

  it('reacts to the shared mobile boundary at 901px', () => {
    let viewportWidth = 901;
    const listeners = new Set();
    vi.spyOn(window, 'innerWidth', 'get').mockImplementation(() => viewportWidth);
    window.matchMedia = vi.fn().mockImplementation(query => ({
      matches: viewportWidth < 901,
      media: query,
      addEventListener: (_event, listener) => listeners.add(listener),
      removeEventListener: (_event, listener) => listeners.delete(listener),
    }));

    render(<Card title="Gesundheit"><p>Details</p></Card>);
    expect(screen.getByRole('button', { name: 'Gesundheit schließen' })).toHaveAttribute('aria-expanded', 'true');

    act(() => {
      viewportWidth = 900;
      listeners.forEach(listener => listener());
    });
    expect(screen.getByRole('button', { name: 'Gesundheit öffnen' })).toHaveAttribute('aria-expanded', 'false');
    expect(screen.getByText('Details').closest('[aria-hidden]')).toHaveAttribute('inert');

    act(() => {
      viewportWidth = 901;
      listeners.forEach(listener => listener());
    });
    expect(screen.getByRole('button', { name: 'Gesundheit schließen' })).toHaveAttribute('aria-expanded', 'true');
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

  it('renders table primitives inside the shared scroll boundary with optional sticky behavior', () => {
    render(
      <TableScroll stickyHeader stickyFirstColumn verticalScroll>
        <Table>
          <TableHeader>
            <TableRow><TableHead>Name</TableHead></TableRow>
          </TableHeader>
          <TableBody>
            <TableRow><TableCell>Ada</TableCell></TableRow>
          </TableBody>
        </Table>
      </TableScroll>,
    );

    const table = screen.getByRole('table');
    expect(table.parentElement).toHaveAttribute('data-slot', 'table-scroll');
    expect(table.parentElement).toHaveAttribute('data-sticky-header');
    expect(table.parentElement).toHaveAttribute('data-sticky-first-column');
    expect(table.parentElement).toHaveAttribute('data-vertical-scroll');
  });

  it('wraps DataTables by default without generating ids and exposes sticky and priority options', () => {
    const columns = [
      { key: 'name', label: 'Name' },
      { key: 'note', label: 'Notiz', priority: 'low' },
    ];
    const rows = [{ id: 1, name: 'Ada', note: 'Vegetarisch' }];

    render(
      <>
        <DataTable columns={columns} rows={rows} />
        <DataTable columns={columns} rows={rows} stickyHeader stickyFirstColumn verticalScroll />
      </>,
    );

    const tables = screen.getAllByRole('table');
    expect(tables).toHaveLength(2);
    expect(tables.every(table => !table.hasAttribute('id'))).toBe(true);
    expect(tables[0].parentElement).toHaveAttribute('data-slot', 'table-scroll');
    expect(tables[0].parentElement).not.toHaveAttribute('data-sticky-header');
    expect(tables[1].parentElement).toHaveAttribute('data-sticky-header');
    expect(tables[1].parentElement).toHaveAttribute('data-sticky-first-column');
    expect(tables[1].parentElement).toHaveAttribute('data-vertical-scroll');
    expect(screen.getAllByRole('columnheader', { name: /Notiz/ })[0]).toHaveAttribute('data-priority', 'low');
    expect(screen.getAllByRole('cell', { name: 'Vegetarisch' })[0]).toHaveAttribute('data-priority', 'low');
  });

  it('filters table pages by the first-column name only', () => {
    const columns = [{ key: 'name', label: 'Name' }];
    const rows = [
      { id: 1, name: 'Ada', filterText: 'Ada Lovelace', searchText: 'Ada Vienna' },
      { id: 2, name: 'Grace', filterText: 'Grace Hopper', searchText: 'Grace Ada' },
    ];

    render(<DataTable columns={columns} rows={rows} showFilter />);
    fireEvent.change(screen.getByPlaceholderText('Kinder filtern...'), { target: { value: 'ada' } });

    expect(screen.getByText('Ada')).toBeInTheDocument();
    expect(screen.queryByText('Grace')).not.toBeInTheDocument();
  });

  it('does not add the child filter to ordinary tables', () => {
    render(<DataTable columns={[{ key: 'name', label: 'Name' }]} rows={[]} />);

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

    render(<DataTable columns={columns} rows={rows} />);
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

  it('keeps form state in React and shows REST validation errors as a toast', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      json: async () => ({ ok: false, errors: ['Dieses Feld ist erforderlich.'] }),
    });
    vi.stubGlobal('fetch', fetchMock);
    render(<Toaster timeout={0}><RestForm target="/profil/" token="token"><input name="rufname" defaultValue="Ada" /><button type="submit" name="money_action" value="withdraw">Speichern</button></RestForm></Toaster>);

    fireEvent.click(screen.getByRole('button', { name: 'Speichern' }));

    const toast = await screen.findByText('Dieses Feld ist erforderlich.', { selector: '.app-toast-description' });
    expect(toast.closest('.app-toast')).toHaveAttribute('data-type', 'error');
    expect(document.querySelector('.errorlist')).not.toBeInTheDocument();
    expect(screen.getByDisplayValue('Ada')).toBeInTheDocument();
    expect(fetchMock.mock.calls[0][1].body.get('money_action')).toBe('withdraw');
    vi.unstubAllGlobals();
  });
});
