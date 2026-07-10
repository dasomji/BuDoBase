import { fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { Card, RestForm, SearchTable } from './components';
import { parseRoute } from './App';

describe('reusable components', () => {
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
  });

  it('filters reusable tables using their search text', () => {
    const columns = [{ key: 'name', label: 'Name' }];
    const rows = [
      { id: 1, name: 'Ada', searchText: 'Ada Lovelace' },
      { id: 2, name: 'Grace', searchText: 'Grace Hopper' },
    ];

    render(<SearchTable columns={columns} rows={rows} query="hopper" />);

    expect(screen.getByText('Grace')).toBeInTheDocument();
    expect(screen.queryByText('Ada')).not.toBeInTheDocument();
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
