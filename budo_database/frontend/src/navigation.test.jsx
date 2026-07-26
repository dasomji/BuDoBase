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
    ]} />} header={<div>Header</div>}><div>Inhalt</div></ApplicationShell>);

    const navigation = screen.getByRole('navigation', { name: 'Hauptnavigation' });
    const lists = within(navigation).getByRole('button', { name: 'Listen' });
    const allocations = within(navigation).getByRole('button', { name: 'Einteilungen' });
    const happyCleaning = within(navigation).getByRole('button', { name: 'Happy Cleaning' });
    const orga = within(navigation).getByRole('button', { name: 'Orgi' });
    const allocationsMenu = document.getElementById(allocations.getAttribute('aria-controls'));
    const happyCleaningMenu = document.getElementById(happyCleaning.getAttribute('aria-controls'));

    expect(lists).toHaveAttribute('aria-expanded', 'true');
    expect(allocations).toHaveAttribute('aria-expanded', 'true');
    expect(happyCleaning).toHaveAttribute('aria-expanded', 'true');
    expect(orga).toHaveAttribute('aria-expanded', 'true');
    expect(within(navigation).getByRole('link', { name: 'Team' })).toHaveAttribute('href', '/team/');
    expect(within(navigation).getByRole('link', { name: 'Alle Kinder' })).toHaveAttribute('href', '/all_kids');
    expect(within(allocationsMenu).queryByRole('link', { name: 'Happy Cleaning' })).not.toBeInTheDocument();
    expect(within(happyCleaningMenu).getAllByRole('link').map(link => link.textContent)).toEqual([
      'Übersicht',
      'Happy Cleaning 1',
      'Happy Cleaning 2',
      'Nummernliste',
    ]);
    expect(within(happyCleaningMenu).getByRole('link', { name: 'Übersicht' })).toHaveAttribute('href', '/happy-cleaning/');
    expect(within(happyCleaningMenu).getByRole('link', { name: 'Happy Cleaning 1' })).toHaveAttribute('href', '/happy-cleaning/7/assignment/');
    expect(within(happyCleaningMenu).getByRole('link', { name: 'Nummernliste' })).toHaveAttribute('href', '/happy-cleaning/print/');
    expect(within(navigation).getByRole('link', { name: 'SWP 1' })).toHaveAttribute('href', '/swp-einteilung-w1');
    expect(within(navigation).getByRole('link', { name: 'Spiele' })).toHaveAttribute('target', '_blank');
    expect(within(navigation).getByRole('link', { name: 'Admin' })).toHaveAttribute('href', '/admin/');
    expect(screen.getByRole('link', { name: 'Profil' })).toHaveAttribute('href', '/profil/');
    expect(within(navigation).getByRole('link', { name: 'Alle Kinder' })).toHaveAttribute('data-active');
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
    vi.spyOn(window, 'innerWidth', 'get').mockReturnValue(886);

    render(<ApplicationShell sidebar={<AppSidebar />} header={<div>Header</div>}><div>Inhalt</div></ApplicationShell>);

    await waitFor(() => {
      expect(document.querySelector('[data-slot="sidebar"][data-state]')).not.toBeInTheDocument();
    });
  });
});
