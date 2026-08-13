import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { AppSidebar } from './app-sidebar';
import { SidebarProvider } from '@/components/ui/sidebar';

describe('Turnus switcher navigation', () => {
  it('renders approved options with an accessible label and submits selection', () => {
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

    const switcher = screen.getByRole('combobox', { name: 'Aktiver Turnus' });
    expect(switcher).toHaveValue('2');
    expect(screen.getAllByRole('option').map(option => option.textContent)).toEqual([
      'T2-2026', 'T4-2027',
    ]);
    fireEvent.change(switcher, { target: { value: '4' } });
    expect(onTurnusChange).toHaveBeenCalledWith(4);
  });
});
