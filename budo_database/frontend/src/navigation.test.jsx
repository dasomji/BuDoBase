import { cleanup, fireEvent, render, screen, within } from '@testing-library/react';
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
    render(<ApplicationShell sidebar={<AppSidebar />} header={<div>Header</div>}><div>Inhalt</div></ApplicationShell>);

    const navigation = screen.getByRole('navigation', { name: 'Hauptnavigation' });
    const lists = within(navigation).getByRole('button', { name: 'Listen' });
    const allocations = within(navigation).getByRole('button', { name: 'Einteilungen' });
    const orga = within(navigation).getByRole('button', { name: 'Orgi' });

    expect(lists).toHaveAttribute('aria-expanded', 'true');
    expect(allocations).toHaveAttribute('aria-expanded', 'true');
    expect(orga).toHaveAttribute('aria-expanded', 'true');
    expect(within(navigation).getByRole('link', { name: 'Team' })).toHaveAttribute('href', '/team/');
    expect(within(navigation).getByRole('link', { name: 'Alle Kinder' })).toHaveAttribute('href', '/all_kids');
    expect(within(navigation).getByRole('link', { name: 'Happy Cleaning' })).toHaveAttribute('href', '/happy-cleaning/');
    expect(within(navigation).getByRole('link', { name: 'SWP 1' })).toHaveAttribute('href', '/swp-einteilung-w1');
    expect(within(navigation).getByRole('link', { name: 'Spiele' })).toHaveAttribute('target', '_blank');
    expect(within(navigation).getByRole('link', { name: 'Admin' })).toHaveAttribute('href', '/admin/');
    expect(screen.getByRole('link', { name: 'Profil' })).toHaveAttribute('href', '/profil/');
    expect(within(navigation).getByRole('link', { name: 'Alle Kinder' })).toHaveAttribute('data-active');
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
});
