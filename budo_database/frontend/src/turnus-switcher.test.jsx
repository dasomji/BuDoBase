import { cleanup, fireEvent, render, screen, within } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { AppSidebar } from './app-sidebar';
import { SidebarProvider } from '@/components/ui/sidebar';

describe('Turnus switcher navigation', () => {
  afterEach(cleanup);

  it('shows the active Turnus as text and switches from an accessible dialog', () => {
    const onTurnusChange = vi.fn();
    render(
      <SidebarProvider>
        <AppSidebar
          turnusSelection={{
            selected_id: 2,
            options: [
              { id: 2, label: 'T2-2026' },
              { id: 4, label: 'T4-2027' },
            ],
          }}
          onTurnusChange={onTurnusChange}
        />
      </SidebarProvider>,
    );

    expect(screen.queryByText('Aktiver Turnus')).not.toBeInTheDocument();
    const activeTurnus = screen.getByText('T2-2026');
    expect(activeTurnus).toHaveAttribute('data-slot', 'active-turnus');
    expect(activeTurnus.parentElement.parentElement).toHaveClass('px-4');
    expect(screen.queryByRole('combobox', { name: 'Aktiver Turnus' })).not.toBeInTheDocument();

    const trigger = screen.getByRole('button', { name: 'Turnus wechseln' });
    const switchIcon = trigger.querySelector('svg');
    expect(switchIcon).toHaveAttribute('aria-hidden', 'true');
    expect(switchIcon).toHaveClass('lucide-arrow-right-left');
    expect(activeTurnus.nextElementSibling).toBe(trigger);
    fireEvent.click(trigger);

    const dialog = screen.getByRole('dialog', { name: 'Turnus wechseln' });
    expect(within(dialog).getByRole('button', { name: /T2-2026/ })).toHaveAttribute(
      'aria-current',
      'true',
    );
    fireEvent.click(within(dialog).getByRole('button', { name: 'T4-2027' }));

    expect(onTurnusChange).toHaveBeenCalledWith(4);
    expect(screen.queryByRole('dialog', { name: 'Turnus wechseln' })).not.toBeInTheDocument();
  });

  it('exposes an accessible busy state and disables the dialog trigger during a switch', () => {
    render(
      <SidebarProvider>
        <AppSidebar
          turnusSelection={{
            selected_id: 2,
            options: [{ id: 2, label: 'T2-2026' }, { id: 4, label: 'T4-2027' }],
          }}
          turnusSwitching
        />
      </SidebarProvider>,
    );

    const trigger = screen.getByRole('button', { name: 'Turnus wechseln' });
    expect(trigger).toBeDisabled();
    expect(trigger).toHaveAttribute('aria-busy', 'true');
    fireEvent.click(trigger);
    expect(screen.queryByRole('dialog', { name: 'Turnus wechseln' })).not.toBeInTheDocument();
  });
});
