import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { BottomComposer } from './BottomComposer';


describe('BottomComposer', () => {
  afterEach(cleanup);

  it('makes empty, loading, and successful focus behavior explicit', async () => {
    let finish;
    const onSubmit = vi.fn(() => new Promise(resolve => { finish = resolve; }));
    render(<BottomComposer
      label="Neue Aufgabe"
      placeholder="Aufgabe hinzufügen…"
      submitLabel="Hinzufügen"
      onSubmit={onSubmit}
    />);

    const input = screen.getByRole('textbox', { name: 'Neue Aufgabe' });
    const button = screen.getByRole('button', { name: 'Hinzufügen' });
    expect(button).toBeDisabled();

    fireEvent.change(input, { target: { value: '  Boden kehren  ' } });
    fireEvent.click(button);

    expect(onSubmit).toHaveBeenCalledWith('Boden kehren');
    expect(input).toHaveValue('  Boden kehren  ');
    expect(input).toBeDisabled();
    expect(screen.getByRole('status')).toHaveTextContent('Wird gespeichert…');

    finish();
    await waitFor(() => expect(input).toHaveValue(''));
    expect(input).toHaveFocus();
    expect(button).toBeDisabled();
  });

  it('preserves text and offers a keyboard-accessible retry after failure', async () => {
    const onSubmit = vi.fn()
      .mockRejectedValueOnce(new Error('Netzwerk unterbrochen'))
      .mockResolvedValueOnce({ ok: true });
    render(<BottomComposer
      label="Neue Aufgabe"
      placeholder="Aufgabe hinzufügen…"
      submitLabel="Hinzufügen"
      onSubmit={onSubmit}
    />);
    const input = screen.getByRole('textbox', { name: 'Neue Aufgabe' });

    fireEvent.change(input, { target: { value: 'Fenster wischen' } });
    fireEvent.submit(input.closest('form'));

    expect(await screen.findByRole('alert')).toHaveTextContent('Netzwerk unterbrochen');
    expect(input).toHaveValue('Fenster wischen');
    fireEvent.click(screen.getByRole('button', { name: 'Erneut versuchen' }));

    await waitFor(() => expect(input).toHaveValue(''));
    expect(onSubmit).toHaveBeenCalledTimes(2);
  });
});
