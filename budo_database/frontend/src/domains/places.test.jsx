import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import App from '../App';
import { parseRoute } from '../routes';
import { ImageUploadPage } from './places';

const response = (data, { ok = true, status = 200 } = {}) => ({
  ok,
  status,
  json: vi.fn().mockResolvedValue(data),
});

describe('Auslagerorte workflows', () => {
  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
    window.history.pushState({}, '', '/');
  });

  it('requires multiple images and hints accepted file types', () => {
    render(<ImageUploadPage data={{
      csrf_token: 'token',
      places: [{ id: 4, name: 'Test place' }],
    }} id="4" />);

    const input = screen.getByLabelText('Select multiple images');
    expect(input).toHaveAttribute('type', 'file');
    expect(input).toBeRequired();
    expect(input).toHaveAttribute('multiple');
    expect(input).toHaveAttribute('accept', 'image/*');
  });

  it('uses the folded list contract for historic detail routes', () => {
    expect([
      '/auslagerorte-list',
      '/auslagerorte/create',
      '/auslagerorte/4/update',
      '/auslagerorte/4/upload-image/',
      '/auslagerorte/4',
    ].map(path => parseRoute(path).readContractKey)).toEqual([
      'places-list',
      'place-create',
      'place-update',
      'place-images',
      'places-list',
    ]);
  });

  it('refreshes the folded list after a sidebar comment without reloading bootstrap', async () => {
    window.history.pushState({}, '', '/auslagerorte/4');
    let listReads = 0;
    const place = { id: 4, name: 'Ada Hütte', tags: [], coordinates: null, notes: [], images: [] };
    const fetchMock = vi.fn(async url => {
      if (url === '/api/bootstrap/') return response({
        authenticated: true,
        csrf_token: 'csrf-token',
        messages: [],
        profile: { id: 1, rufname: 'Ada' },
        turnus: { id: 2, label: 'T2' },
        permissions: {},
        search_index: { kids: [], focuses: [], places: [{ id: 4, name: 'Ada Hütte' }] },
      });
      if (url === '/api/route-data/places-list/?id=4') {
        listReads += 1;
        return response({ places: [{ ...place, notes: listReads === 1 ? [] : [{ id: 7, author: 'ada', date: '2026-07-17', text: 'Wasser abdrehen', photos: [] }] }], available_tags: [] });
      }
      if (url === '/api/form-submit/') return response({ ok: true });
      throw new Error(`Unexpected request: ${url}`);
    });
    vi.stubGlobal('fetch', fetchMock);

    render(<App fetchImpl={fetchMock} />);
    const note = await screen.findByRole('textbox', { name: 'Kommentar' });
    fireEvent.change(note, { target: { value: 'Wasser abdrehen' } });
    fireEvent.click(screen.getByRole('button', { name: 'Kommentar senden' }));

    expect(await screen.findByText(/Wasser abdrehen/)).toBeInTheDocument();
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(4));
    expect(fetchMock.mock.calls.map(call => call[0])).toEqual([
      '/api/bootstrap/',
      '/api/route-data/places-list/?id=4',
      '/api/form-submit/',
      '/api/route-data/places-list/?id=4',
    ]);
  });
});
