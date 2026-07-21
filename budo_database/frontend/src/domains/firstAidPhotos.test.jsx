import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import App from '../App';
import { DashboardPage } from './dashboard';
import { KidDetailPage, KidInteractionForm } from './kids';

const emptyPage = { items: [], next_cursor: null, has_more: false, limit: 20 };
const photos = [
  {
    id: 101,
    url: '/api/first-aid/photos/101/media/',
    width: 640,
    height: 480,
    alt: 'EH-Foto 1 von Ada Lovelace, EH-Eintrag 9',
  },
  {
    id: 102,
    url: '/api/first-aid/photos/102/media/',
    width: 480,
    height: 640,
    alt: 'EH-Foto 2 von Ada Lovelace, EH-Eintrag 9',
  },
];
const firstAidEntry = {
  id: 9,
  author: 'Boris',
  date: '2026-07-02T10:00:00Z',
  kid_id: 7,
  kid: 'Ada Lovelace',
  text: 'Private medizinische Beschreibung',
  photos,
};

const response = (data, { ok = true, status = 200 } = {}) => ({
  ok,
  status,
  json: vi.fn().mockResolvedValue(data),
});

function kidDetailData() {
  return {
    csrf_token: 'token',
    turnus: { label: 'T2' },
    kids: [{
      id: 7,
      full_name: 'Ada Lovelace',
      present: true,
      weeks: 2,
      birthday: '2012-07-02',
      notes: [],
      first_aid_entries: [firstAidEntry],
      transactions: [],
      remaining_money: 10,
      deposit: 0,
    }],
  };
}

function dashboardData(firstAidPage = { ...emptyPage, items: [firstAidEntry] }) {
  return {
    profile: { budo_family: null, focus_ids: [] },
    totals: {
      checked_in: 1,
      kids: 1,
      train_arrival: 0,
      train_departure: 0,
    },
    kids: [{
      id: 7,
      full_name: 'Ada Lovelace',
      present: true,
      age: 14,
      sex: 'weiblich',
      weeks: 2,
      budo_experience: true,
      birthday_during_turnus: false,
      special_food: '',
      drugs: '',
      illness: '',
      budo_family: 'M',
    }],
    focuses: [],
    focus_assignments_complete: { w1: false, w2: false },
    activity: {
      notes: emptyPage,
      first_aid: firstAidPage,
      transactions: emptyPage,
    },
  };
}

function bootstrapData() {
  return {
    authenticated: true,
    csrf_token: 'token',
    messages: [],
    profile: { id: 1, rufname: 'Ada' },
    turnus: { id: 2, label: 'T2' },
    permissions: {},
    search_index: { kids: [], focuses: [], places: [] },
  };
}

function acceptedPhotoInput(input) {
  const accepted = input.getAttribute('accept').toLocaleLowerCase();
  for (const format of ['jpeg', 'png', 'webp', 'heic', 'heif']) {
    expect(accepted).toContain(format);
  }
}

describe('EH photo upload and card strips', () => {
  beforeEach(() => {
    document.cookie = 'interaction-bar=; Max-Age=0; Path=/';
    window.history.pushState({}, '', '/kid_details/7');
    window.matchMedia = vi.fn().mockReturnValue({
      matches: false,
      media: '',
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    });
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
    window.history.pushState({}, '', '/');
  });

  it('submits description and multiple files together, advertises limits, and resets after success', async () => {
    const resetSpy = vi.spyOn(window.HTMLFormElement.prototype, 'reset');
    const onSaved = vi.fn().mockResolvedValue(undefined);
    const fetchMock = vi.fn().mockResolvedValue(response({ ok: true }));
    vi.stubGlobal('fetch', fetchMock);
    render(<KidInteractionForm kid={{ id: 7 }} token="token" onSaved={onSaved} />);

    fireEvent.click(screen.getByText('Notiz'));
    fireEvent.click(screen.getByText('Taschengeld'));
    const form = screen.getByRole('button', { name: 'EH-Eintrag senden' }).closest('form');
    const description = screen.getByPlaceholderText('Erste-Hilfe-Maßnahme...');
    const photoInput = screen.getByLabelText(/EH-Fotos/i);
    const files = [
      new File(['jpeg'], 'first.jpg', { type: 'image/jpeg' }),
      new File(['heif'], 'second.heif', { type: 'image/heif' }),
    ];

    expect(form).toHaveAttribute('enctype', 'multipart/form-data');
    expect(photoInput).toHaveAttribute('type', 'file');
    expect(photoInput).toHaveAttribute('multiple');
    acceptedPhotoInput(photoInput);

    fireEvent.change(description, { target: { value: 'Knie verbunden' } });
    fireEvent.change(photoInput, { target: { files } });
    expect(document.querySelector('.first-aid-input-field .attachment-count')).toHaveTextContent('2');
    expect(document.querySelector('.first-aid-input-field .attachment-button')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'EH-Eintrag senden' }));

    await waitFor(() => expect(onSaved).toHaveBeenCalledOnce());
    const body = fetchMock.mock.calls[0][1].body;
    expect(body).toBeInstanceOf(FormData);
    expect(body.get('interaction_kind')).toBe('first_aid');
    expect(body.get('erste_hilfe_beschreibung')).toBe('Knie verbunden');
    expect(body.getAll('erste_hilfe_fotos')).toEqual(files);
    expect(resetSpy).toHaveBeenCalledOnce();
    expect(description).toHaveValue('');
  });

  it('keeps the EH payload for correction and displays backend photo failures', async () => {
    const onSaved = vi.fn();
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response(
      { ok: false, errors: ['Es sind höchstens 5 Fotos erlaubt.'] },
      { ok: false, status: 422 },
    )));
    render(<KidInteractionForm kid={{ id: 7 }} token="token" onSaved={onSaved} />);

    fireEvent.click(screen.getByText('Notiz'));
    fireEvent.click(screen.getByText('Taschengeld'));
    const description = screen.getByPlaceholderText('Erste-Hilfe-Maßnahme...');
    const photoInput = screen.getByLabelText(/EH-Fotos/i);
    fireEvent.change(description, { target: { value: 'Knie verbunden' } });
    fireEvent.change(photoInput, {
      target: { files: [new File(['bad'], 'bad.gif', { type: 'image/gif' })] },
    });
    fireEvent.click(screen.getByRole('button', { name: 'EH-Eintrag senden' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('Es sind höchstens 5 Fotos erlaubt.');
    expect(description).toHaveValue('Knie verbunden');
    expect(photoInput.files).toHaveLength(1);
    expect(onSaved).not.toHaveBeenCalled();
  });

  it('focused-refreshes only the selected kid contract after multipart success', async () => {
    let detailReads = 0;
    const fetchImpl = vi.fn(async url => {
      if (url === '/api/bootstrap/') return response(bootstrapData());
      if (url === '/api/route-data/kid-detail/?id=7') {
        detailReads += 1;
        const data = kidDetailData();
        data.kids[0].first_aid_entries = detailReads === 1 ? [] : [firstAidEntry];
        return response(data);
      }
      throw new Error(`Unexpected focused read: ${url}`);
    });
    const formFetch = vi.fn().mockResolvedValue(response({ ok: true }));
    vi.stubGlobal('fetch', formFetch);
    render(<App fetchImpl={fetchImpl} />);

    expect(await screen.findByText('Noch keine EH-Einträge.')).toBeInTheDocument();
    fireEvent.click(screen.getByText('Notiz'));
    fireEvent.click(screen.getByText('Taschengeld'));
    fireEvent.change(screen.getByPlaceholderText('Erste-Hilfe-Maßnahme...'), {
      target: { value: 'Private medizinische Beschreibung' },
    });
    fireEvent.change(screen.getByLabelText(/EH-Fotos/i), {
      target: { files: [new File(['photo'], 'photo.webp', { type: 'image/webp' })] },
    });
    fireEvent.click(screen.getByRole('button', { name: 'EH-Eintrag senden' }));

    expect(await screen.findByRole('img', { name: 'EH-Foto 1 von Ada Lovelace, EH-Eintrag 9' })).toBeInTheDocument();
    expect(detailReads).toBe(2);
    expect(fetchImpl.mock.calls.filter(([url]) => url === '/api/bootstrap/')).toHaveLength(1);
    expect(fetchImpl.mock.calls.some(([url]) => url.includes('dashboard'))).toBe(false);
  });

  it('renders the same bounded, lazy, labelled photo-strip shape on kid detail and dashboard', () => {
    const assertPhotoEntry = card => {
      const entry = card.querySelector('.first-aid-entry');
      const strip = within(card).getByRole('region', { name: /EH-Fotos.*Ada Lovelace/i });
      const images = within(strip).getAllByRole('img');

      expect(entry).not.toBeNull();
      expect(strip).toHaveClass('first-aid-photo-strip');
      expect(strip).toHaveAttribute('tabindex', '0');
      expect(images).toHaveLength(2);
      expect(images[0]).toHaveAttribute('src', photos[0].url);
      expect(images[0]).toHaveAttribute('width', '640');
      expect(images[0]).toHaveAttribute('height', '480');
      expect(images[0]).toHaveAttribute('loading', 'lazy');
      expect(images[0]).toHaveAccessibleName('EH-Foto 1 von Ada Lovelace, EH-Eintrag 9');
      expect(images[0]).not.toHaveAccessibleName(/Private medizinische Beschreibung/i);
      expect(within(entry).queryByRole('button', { name: /bearbeiten|löschen/i })).not.toBeInTheDocument();
      expect(within(entry).queryByRole('link', { name: /bearbeiten|löschen/i })).not.toBeInTheDocument();
      return { entryClass: entry.className, stripClass: strip.className };
    };

    const kidRender = render(<KidDetailPage
      data={kidDetailData()}
      id="7"
      mutate={vi.fn()}
    />);
    const kidCard = screen.getByRole('heading', { name: 'Erste Hilfe' }).closest('.card');
    const kidShape = assertPhotoEntry(kidCard);
    fireEvent.click(within(kidCard).getByRole('img', { name: photos[0].alt }));
    expect(window.location.pathname).toBe('/kid_details/7');
    expect(screen.getByRole('dialog', { name: 'EH-Fotogalerie' })).toBeInTheDocument();
    kidRender.unmount();

    render(<DashboardPage data={dashboardData()} />);
    const dashboardCard = screen.getByRole('heading', { name: 'Erste Hilfe' }).closest('.card');
    expect(assertPhotoEntry(dashboardCard)).toEqual(kidShape);
  });

  it('exposes initial and appended dashboard EH items at page level for Unit 03', async () => {
    const older = {
      ...firstAidEntry,
      id: 8,
      text: 'Älterer EH-Eintrag',
      photos: [{ ...photos[0], id: 100, url: '/api/first-aid/photos/100/media/' }],
    };
    const fetchImpl = vi.fn().mockResolvedValue(response({
      activity: {
        first_aid: { ...emptyPage, items: [older] },
      },
    }));
    const onFirstAidItemsChange = vi.fn();
    render(<DashboardPage
      data={dashboardData({
        items: [firstAidEntry],
        next_cursor: 'older cursor',
        has_more: true,
        limit: 20,
      })}
      fetchImpl={fetchImpl}
      onFirstAidItemsChange={onFirstAidItemsChange}
    />);

    await waitFor(() => expect(onFirstAidItemsChange).toHaveBeenLastCalledWith([firstAidEntry]));
    fireEvent.click(screen.getByRole('button', { name: 'Ältere EH-Einträge laden' }));

    await waitFor(() => expect(onFirstAidItemsChange).toHaveBeenLastCalledWith([firstAidEntry, older]));
    expect(fetchImpl).toHaveBeenCalledTimes(1);
  });
});

describe('EH photo strip CSS contract', () => {
  const css = readFileSync(resolve(process.cwd(), 'src/app.css'), 'utf8');
  const declarationsFor = selector => {
    const escaped = selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const match = css.match(new RegExp(`${escaped}\\s*\\{([^}]*)\\}`));
    expect(match, `Missing CSS rule for ${selector}`).not.toBeNull();
    return match[1].replace(/\s+/g, '').toLocaleLowerCase();
  };

  it('contains photos inside an internal horizontal scroller without widening cards or pages', () => {
    const entry = declarationsFor('.first-aid-entry');
    const strip = declarationsFor('.first-aid-photo-strip');
    const trigger = declarationsFor('.first-aid-photo-trigger');
    const image = declarationsFor('.first-aid-photo');
    const galleryImage = declarationsFor('.first-aid-gallery-image');

    expect(entry).toContain('min-width:0');
    expect(entry).toContain('max-width:100%');
    expect(strip).toContain('width:100%');
    expect(strip).toContain('max-width:100%');
    expect(strip).toContain('min-width:0');
    expect(strip).toContain('overflow-x:auto');
    expect(trigger).toContain('flex:00auto');
    expect(trigger).toContain('max-width:100%');
    expect(image).toContain('width:auto');
    expect(image).toContain('height:auto');
    expect(image).toContain('max-width:100%');
    expect(image).toContain('max-height:200px');
    expect(image).toContain('object-fit:contain');
    expect(galleryImage).toContain('touch-action:pan-y');
  });
});
