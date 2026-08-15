import { cleanup, render, screen, within } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';

import { AppSidebar, ApplicationShell } from './app-sidebar';

function renderSidebar(permissions, path = '/') {
  window.history.pushState({}, '', path);
  return render(
    <ApplicationShell
      sidebar={<AppSidebar permissions={permissions} />}
      header={<div>Header</div>}
    >
      <div>Inhalt</div>
    </ApplicationShell>,
  );
}

describe('Audit-Log navigation capability', () => {
  afterEach(() => {
    cleanup();
    document.cookie = 'sidebar_state=; Max-Age=0; Path=/';
    window.history.pushState({}, '', '/');
  });

  it('denies by default and removes the item from the DOM before active-state calculation', () => {
    renderSidebar(undefined, '/audit/');

    expect(screen.queryByRole('link', { name: 'Audit-Log' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Admin' })).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Orgi' })).not.toHaveAttribute('data-active');
    expect(screen.queryByRole('link', { name: 'Django' })).not.toBeInTheDocument();
  });

  it('shows exactly one ordinary audit anchor under Admin immediately before Django', () => {
    renderSidebar({
      is_superuser: true,
      change_tags: true,
      view_auditevent: true,
      export_auditevent: false,
      admin_settings: true,
    });

    const navigation = screen.getByRole('navigation', { name: 'Hauptnavigation' });
    const audit = within(navigation).getByRole('link', { name: 'Audit-Log' });
    expect(audit.tagName).toBe('A');
    expect(audit).toHaveAttribute('href', '/audit/');
    expect(within(navigation).getAllByRole('link', { name: 'Audit-Log' })).toHaveLength(1);

    const admin = within(navigation).getByRole('button', { name: 'Admin' });
    const adminMenu = document.getElementById(admin.getAttribute('aria-controls'));
    expect(within(adminMenu).getAllByRole('link').map(link => link.textContent)).toEqual([
      'Auslagerort-Tags',
      'Audit-Log',
      'Einstellungen',
      'Django',
    ]);
  });

  it('keeps the exact child and parent active on both accepted pathname spellings only', () => {
    for (const path of ['/audit', '/audit/']) {
      const view = renderSidebar({ is_superuser: true, view_auditevent: true }, path);
      expect(screen.getByRole('link', { name: 'Audit-Log' })).toHaveAttribute('data-active');
      expect(screen.getByRole('button', { name: 'Admin' })).toHaveAttribute('data-active');
      expect(screen.getByRole('button', { name: 'Orgi' })).not.toHaveAttribute('data-active');
      view.unmount();
    }

    renderSidebar({ is_superuser: true, view_auditevent: true }, '/audit-settings/');
    expect(screen.getByRole('link', { name: 'Audit-Log' })).not.toHaveAttribute('data-active');
    expect(screen.getByRole('button', { name: 'Admin' })).not.toHaveAttribute('data-active');
    expect(screen.getByRole('button', { name: 'Orgi' })).not.toHaveAttribute('data-active');
  });

  it('shows tag settings only with tag change permission', () => {
    renderSidebar({ is_superuser: true, change_tags: true }, '/auslagerorte/tags/');

    expect(screen.getByRole('link', { name: 'Auslagerort-Tags' })).toHaveAttribute(
      'href',
      '/auslagerorte/tags/',
    );
    expect(screen.getByRole('link', { name: 'Auslagerort-Tags' })).toHaveAttribute('data-active');
    expect(screen.getByRole('button', { name: 'Admin' })).toHaveAttribute('data-active');
    expect(screen.getByRole('button', { name: 'Orgi' })).not.toHaveAttribute('data-active');
  });

  it('shows app settings only to staff-authorized users', () => {
    const view = renderSidebar({ is_superuser: true, admin_settings: false }, '/settings/');
    expect(screen.queryByRole('link', { name: 'Einstellungen' })).not.toBeInTheDocument();
    view.unmount();

    renderSidebar({ is_superuser: true, admin_settings: true }, '/settings/');
    expect(screen.getByRole('link', { name: 'Einstellungen' })).toHaveAttribute('href', '/settings/');
    expect(screen.getByRole('link', { name: 'Einstellungen' })).toHaveAttribute('data-active');
    expect(screen.getByRole('button', { name: 'Admin' })).toHaveAttribute('data-active');
    expect(screen.getByRole('button', { name: 'Orgi' })).not.toHaveAttribute('data-active');
  });

  it('does not treat export permission alone as view authorization', () => {
    renderSidebar({ is_superuser: true, view_auditevent: false, export_auditevent: true });

    expect(screen.queryByRole('link', { name: 'Audit-Log' })).not.toBeInTheDocument();
  });
});
