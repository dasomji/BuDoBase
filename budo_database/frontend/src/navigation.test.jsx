import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { AppSidebar, ApplicationShell } from './app-sidebar';

describe('application sidebar navigation', () => {
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
    document.cookie = 'sidebar_state=; Max-Age=0; Path=/';
    window.history.pushState({}, '', '/');
  });

  it('renders the requested navigation hierarchy and profile footer', () => {
    window.history.pushState({}, '', '/all_kids');
    render(<ApplicationShell sidebar={<AppSidebar happyCleaningEvents={[
      { id: 7, display_number: 1 },
      { id: 9, display_number: 2 },
    ]} permissions={{ is_superuser: true }} />} header={<div>Header</div>}><div>Inhalt</div></ApplicationShell>);

    const navigation = screen.getByRole('navigation', { name: 'Hauptnavigation' });
    const lists = within(navigation).getByRole('button', { name: 'Listen' });
    const focuses = within(navigation).getByRole('button', { name: 'Schwerpunkte' });
    const happyCleaning = within(navigation).getByRole('button', { name: 'Happy Cleaning' });
    const documentation = within(navigation).getByRole('link', { name: 'Dokumentation' });
    const orga = within(navigation).getByRole('button', { name: 'Orgi' });
    const admin = within(navigation).getByRole('button', { name: 'Admin' });
    const listsMenu = document.getElementById(lists.getAttribute('aria-controls'));
    const focusesMenu = document.getElementById(focuses.getAttribute('aria-controls'));
    const happyCleaningMenu = document.getElementById(happyCleaning.getAttribute('aria-controls'));
    const orgaMenu = document.getElementById(orga.getAttribute('aria-controls'));
    const adminMenu = document.getElementById(admin.getAttribute('aria-controls'));

    expect(lists).toHaveAttribute('aria-expanded', 'true');
    expect(focuses).toHaveAttribute('aria-expanded', 'true');
    expect(happyCleaning).toHaveAttribute('aria-expanded', 'true');
    expect(orga).toHaveAttribute('aria-expanded', 'true');
    expect(admin).toHaveAttribute('aria-expanded', 'true');
    expect(documentation.compareDocumentPosition(lists) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(documentation.compareDocumentPosition(orga) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(orga.compareDocumentPosition(admin) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(documentation).toHaveAttribute('href', '/dokumentation/');
    expect(within(navigation).getByRole('link', { name: 'Team & Turnus' })).toHaveAttribute('href', '/teams/');
    expect(within(navigation).getByRole('link', { name: 'Alle Kinder' })).toHaveAttribute('href', '/all_kids');
    expect(within(listsMenu).queryByRole('link', { name: 'Spezialfamilien' })).not.toBeInTheDocument();
    expect(within(listsMenu).getByRole('link', { name: 'Gut zu wissen' })).toHaveAttribute('href', '/gut-zu-wissen/');
    expect(within(focusesMenu).getAllByRole('link').map(link => link.textContent)).toEqual([
      'SWP 1',
      'SWP 2',
    ]);
    expect(within(focusesMenu).queryByRole('link', { name: 'Happy Cleaning' })).not.toBeInTheDocument();
    expect(within(happyCleaningMenu).getAllByRole('link').map(link => link.textContent)).toEqual([
      'Übersicht',
      'Nummernliste',
      'Happy Cleaning 1',
      'Happy Cleaning 2',
    ]);
    expect(within(orgaMenu).getAllByRole('link').map(link => link.textContent)).toEqual([
      'Taschengeld',
      'Serienbrief',
      'Aufenthaltsdoku',
    ]);
    expect(within(orgaMenu).getByRole('link', { name: 'Taschengeld' })).toHaveAttribute('href', '/taschengeld/');
    expect(within(adminMenu).getAllByRole('link').map(link => link.textContent)).toEqual([
      'Django',
    ]);
    expect(within(happyCleaningMenu).getByRole('link', { name: 'Übersicht' })).toHaveAttribute('href', '/happy-cleaning/');
    expect(within(happyCleaningMenu).getByRole('link', { name: 'Happy Cleaning 1' })).toHaveAttribute('href', '/happy-cleaning/7/assignment/');
    expect(within(happyCleaningMenu).getByRole('link', { name: 'Nummernliste' })).toHaveAttribute('href', '/happy-cleaning/print/');
    expect(within(navigation).getByRole('link', { name: 'SWP 1' })).toHaveAttribute('href', '/swp-einteilung-w1');
    expect(within(navigation).getByRole('link', { name: 'Spiele' })).toHaveAttribute('target', '_blank');
    expect(within(navigation).getByRole('link', { name: 'Django' })).toHaveAttribute('href', '/admin/');
    expect(screen.getByRole('link', { name: 'Profil' })).toHaveAttribute('href', '/profil/');
    expect(within(navigation).getByRole('link', { name: 'Alle Kinder' })).toHaveAttribute('data-active');
  });

  it('shows only Team & Turnus and Profil when no Turnus is available', () => {
    render(
      <ApplicationShell
        sidebar={<AppSidebar withoutTurnus />}
        header={<div>Header</div>}
      >
        <div>Inhalt</div>
      </ApplicationShell>,
    );

    const navigation = screen.getByRole('navigation', { name: 'Hauptnavigation' });
    expect(within(navigation).getAllByRole('link').map(link => link.textContent)).toEqual([
      'Team & Turnus',
    ]);
    expect(screen.getByRole('link', { name: 'Profil' })).toHaveAttribute('href', '/profil/');
    expect(document.querySelector('.sidebar-brand')).toHaveAttribute('href', '/teams/');
    expect(screen.queryByRole('button', { name: 'Listen' })).not.toBeInTheDocument();
  });

  it('hides the complete Admin group from non-superusers', () => {
    render(
      <ApplicationShell
        sidebar={(
          <AppSidebar permissions={{
            is_superuser: false,
            change_tags: true,
            view_auditevent: true,
            admin_settings: true,
          }} />
        )}
        header={<div>Header</div>}
      >
        <div>Inhalt</div>
      </ApplicationShell>,
    );

    const navigation = screen.getByRole('navigation', { name: 'Hauptnavigation' });
    expect(within(navigation).queryByRole('button', { name: 'Admin' })).not.toBeInTheDocument();
    expect(within(navigation).queryByRole('link', { name: 'Django' })).not.toBeInTheDocument();
    expect(within(navigation).queryByRole('link', { name: 'Audit-Log' })).not.toBeInTheDocument();
  });

  it('keeps the profile navigation active on the edit page', () => {
    window.history.pushState({}, '', '/profil/bearbeiten/');
    render(<ApplicationShell sidebar={<AppSidebar />} header={<div>Header</div>}><div>Inhalt</div></ApplicationShell>);

    expect(screen.getByRole('link', { name: 'Profil' })).toHaveAttribute('data-active');
  });

  it('marks an event item active throughout that Happy Cleaning event', () => {
    window.history.pushState({}, '', '/happy-cleaning/9/stations/');
    render(<ApplicationShell sidebar={<AppSidebar happyCleaningEvents={[
      { id: 7, display_number: 1 },
      { id: 9, display_number: 2 },
    ]} />} header={<div>Header</div>}><div>Inhalt</div></ApplicationShell>);

    const group = screen.getByRole('button', { name: 'Happy Cleaning' });
    const item = screen.getByRole('link', { name: 'Happy Cleaning 2' });

    expect(group).toHaveAttribute('data-active');
    expect(item).toHaveAttribute('data-active');
  });

  it('collapses nested navigation groups accessibly', () => {
    render(<ApplicationShell sidebar={<AppSidebar />} header={<div>Header</div>}><div>Inhalt</div></ApplicationShell>);
    const lists = screen.getByRole('button', { name: 'Listen' });

    fireEvent.click(lists);

    expect(lists).toHaveAttribute('aria-expanded', 'false');
    expect(screen.queryByRole('link', { name: 'Alle Kinder' })).not.toBeInTheDocument();
  });

  it('keeps header actions in the content area beside the search slot', () => {
    render(
      <ApplicationShell
        sidebar={<AppSidebar />}
        header={<header><div>Suche</div><div>Aktion</div></header>}
      >
        <div>Inhalt</div>
      </ApplicationShell>,
    );

    expect(screen.getByText('Suche').closest('.app-shell-content')).toBeInTheDocument();
    expect(screen.getByText('Aktion').closest('.app-shell-content')).toBeInTheDocument();
  });

  it('restores and updates the sidebar state cookie', () => {
    document.cookie = 'sidebar_state=false; Path=/';
    render(<ApplicationShell sidebar={<AppSidebar />} header={<div>Header</div>}><div>Inhalt</div></ApplicationShell>);

    const sidebar = document.querySelector('[data-slot="sidebar"]');
    expect(sidebar).toHaveAttribute('data-state', 'collapsed');

    fireEvent.click(screen.getByRole('button', { name: 'Toggle Sidebar' }));

    expect(sidebar).toHaveAttribute('data-state', 'expanded');
    expect(document.cookie).toContain('sidebar_state=true');
  });

  it('uses the mobile sidebar at tablet widths where the desktop sidebar would overlap content', async () => {
    window.matchMedia = vi.fn().mockImplementation(query => ({
      matches: query === '(max-width: 900px)',
      media: query,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    }));

    render(<ApplicationShell sidebar={<AppSidebar />} header={<div>Header</div>}><div>Inhalt</div></ApplicationShell>);

    await waitFor(() => {
      expect(document.querySelector('[data-slot="sidebar"][data-state]')).not.toBeInTheDocument();
    });
  });
});
