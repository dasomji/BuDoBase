import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { DashboardPage } from './dashboard';
import { KidDetailPage } from './kids';

const emptyPage = { items: [], next_cursor: null, has_more: false, limit: 20 };

const recentPhotos = [
  {
    id: 301,
    url: '/api/first-aid/photos/301/media/',
    width: 640,
    height: 480,
    alt: 'EH-Foto 1 von Ada Lovelace, EH-Eintrag 30',
  },
  {
    id: 302,
    url: '/api/first-aid/photos/302/media/',
    width: 480,
    height: 640,
    alt: 'EH-Foto 2 von Ada Lovelace, EH-Eintrag 30',
  },
];

const olderPhoto = {
  id: 201,
  url: '/api/first-aid/photos/201/media/',
  width: 800,
  height: 600,
  alt: 'EH-Foto 1 von Ada Lovelace, EH-Eintrag 20',
};

const recentEntry = {
  id: 30,
  author: 'Boris',
  date: '2026-07-03T10:00:00Z',
  kid_id: 7,
  kid: 'Ada Lovelace',
  text: 'Vertrauliche medizinische Beschreibung der jüngeren Maßnahme',
  photos: recentPhotos,
};

const olderEntry = {
  id: 20,
  author: 'Grace',
  date: '2026-07-02T10:00:00Z',
  kid_id: 7,
  kid: 'Ada Lovelace',
  text: 'Vertrauliche medizinische Beschreibung der älteren Maßnahme',
  photos: [olderPhoto],
};

function kidDetailData(entries = [recentEntry, olderEntry]) {
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
      first_aid_entries: entries,
      transactions: [],
      remaining_money: 10,
      deposit: 0,
    }],
  };
}

function dashboardData(firstAidPage = { ...emptyPage, items: [recentEntry, olderEntry] }) {
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

const response = data => ({
  ok: true,
  status: 200,
  json: vi.fn().mockResolvedValue(data),
});

function openPhoto(photo, { keyboard = false } = {}) {
  const trigger = screen.getByRole('button', { name: photo.alt });
  trigger.focus();
  fireEvent.click(trigger, { detail: keyboard ? 0 : 1 });
  return trigger;
}

function gallery() {
  return screen.getByRole('dialog', { name: /EH-Fotogalerie/i });
}

function expectCurrentPhoto(dialog, photo) {
  const image = within(dialog).getByRole('img', { name: photo.alt });
  expect(image).toHaveAttribute('src', photo.url);
  return image;
}

function touchGesture(target, { from, to }) {
  fireEvent.touchStart(target, {
    touches: [{ clientX: from.x, clientY: from.y }],
    changedTouches: [{ clientX: from.x, clientY: from.y }],
  });
  fireEvent.touchEnd(target, {
    touches: [],
    changedTouches: [{ clientX: to.x, clientY: to.y }],
  });
}

describe('page-level EH photo gallery', () => {
  beforeEach(() => {
    document.cookie = 'interaction-bar=; Max-Age=0; Path=/';
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

  it.each([
    {
      page: 'kid detail',
      pathname: '/kid_details/7',
      keyboard: false,
      renderPage: () => render(<KidDetailPage data={kidDetailData()} id="7" mutate={vi.fn()} />),
    },
    {
      page: 'dashboard',
      pathname: '/dashboard',
      keyboard: true,
      renderPage: () => render(<DashboardPage data={dashboardData()} />),
    },
  ])('opens the selected photo from $page in the shared route-preserving gallery', ({ pathname, keyboard, renderPage }) => {
    window.history.pushState({}, '', pathname);
    renderPage();

    openPhoto(recentPhotos[1], { keyboard });

    const dialog = gallery();
    expectCurrentPhoto(dialog, recentPhotos[1]);
    expect(dialog).toHaveAttribute('aria-modal', 'true');
    expect(within(dialog).getByRole('button', { name: /vorheriges Foto/i })).toBeVisible();
    expect(within(dialog).getByRole('button', { name: /nächstes Foto/i })).toBeVisible();
    expect(within(dialog).getByRole('button', { name: /Galerie schließen/i })).toBeVisible();
    expect(within(dialog).queryByText(recentEntry.text)).not.toBeInTheDocument();
    for (const control of within(dialog).getAllByRole('button')) {
      expect(control).not.toHaveAccessibleName(/medizinische Beschreibung/i);
    }
    expect(within(dialog).queryByRole('link')).not.toBeInTheDocument();
    expect(window.location.pathname).toBe(pathname);
  });

  it('gives same-child photos collision-free names with safe entry context in cards and gallery', () => {
    render(<KidDetailPage data={kidDetailData()} id="7" mutate={vi.fn()} />);

    const recentTrigger = screen.getByRole('button', { name: recentPhotos[0].alt });
    const olderTrigger = screen.getByRole('button', { name: olderPhoto.alt });
    expect(recentTrigger).not.toHaveAccessibleName(olderPhoto.alt);
    expect(within(recentTrigger).getByRole('img')).toHaveAccessibleName(recentPhotos[0].alt);
    expect(within(olderTrigger).getByRole('img')).toHaveAccessibleName(olderPhoto.alt);
    expect(recentTrigger).not.toHaveAccessibleName(/medizinische Beschreibung/i);
    expect(olderTrigger).not.toHaveAccessibleName(/medizinische Beschreibung/i);

    fireEvent.click(olderTrigger);
    expectCurrentPhoto(gallery(), olderPhoto);
  });

  it('flattens EH chronology and stored photo order and wraps at both boundaries', () => {
    window.history.pushState({}, '', '/kid_details/7');
    render(<KidDetailPage data={kidDetailData()} id="7" mutate={vi.fn()} />);
    openPhoto(recentPhotos[0]);

    const dialog = gallery();
    const previous = within(dialog).getByRole('button', { name: /vorheriges Foto/i });
    const next = within(dialog).getByRole('button', { name: /nächstes Foto/i });

    fireEvent.click(next);
    expectCurrentPhoto(dialog, recentPhotos[1]);
    fireEvent.keyDown(dialog, { key: 'ArrowRight' });
    expectCurrentPhoto(dialog, olderPhoto);
    fireEvent.keyDown(dialog, { key: 'ArrowRight' });
    expectCurrentPhoto(dialog, recentPhotos[0]);
    fireEvent.click(previous);
    expectCurrentPhoto(dialog, olderPhoto);
    fireEvent.keyDown(dialog, { key: 'ArrowLeft' });
    expectCurrentPhoto(dialog, recentPhotos[1]);

    expect(window.location.pathname).toBe('/kid_details/7');
  });

  it('closes by its visible action or Escape and restores focus to the activating photo', async () => {
    window.history.pushState({}, '', '/kid_details/7');
    render(<KidDetailPage data={kidDetailData()} id="7" mutate={vi.fn()} />);

    const trigger = openPhoto(recentPhotos[1], { keyboard: true });
    fireEvent.click(within(gallery()).getByRole('button', { name: /Galerie schließen/i }));

    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
    expect(trigger).toHaveFocus();

    openPhoto(recentPhotos[1]);
    fireEvent.keyDown(document, { key: 'Escape' });

    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
    expect(trigger).toHaveFocus();
    expect(window.location.pathname).toBe('/kid_details/7');
  });

  it('keeps the modal public, cycles focus, ignores its actual backdrop, and returns focus', async () => {
    const user = userEvent.setup();
    render(
      <div>
        <button type="button">Hintergrundaktion</button>
        <KidDetailPage data={kidDetailData()} id="7" mutate={vi.fn()} />
      </div>,
    );
    const backgroundAction = screen.getByRole('button', { name: 'Hintergrundaktion' });
    const trigger = openPhoto(recentPhotos[0]);
    const dialog = gallery();

    await waitFor(() => {
      expect(dialog).toContainElement(document.activeElement);
      expect(backgroundAction.closest('[aria-hidden="true"]')).not.toBeNull();
      expect(screen.queryByRole('button', { name: 'Hintergrundaktion' })).not.toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Hintergrundaktion', hidden: true })).toBe(backgroundAction);
    });

    const close = within(dialog).getByRole('button', { name: /Galerie schließen/i });
    const next = within(dialog).getByRole('button', { name: /Nächstes Foto/i });
    close.focus();
    await user.tab({ shift: true });
    await waitFor(() => expect(next).toHaveFocus());
    await user.tab();
    await waitFor(() => expect(close).toHaveFocus());

    const backdrop = document.querySelector('.first-aid-gallery-backdrop');
    expect(backdrop).not.toBeNull();
    await user.click(backdrop);
    expect(gallery()).toBeInTheDocument();

    await user.click(close);
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
    expect(trigger).toHaveFocus();
  });

  it('uses a horizontal threshold and leaves vertical gestures for CSS pan-y scrolling', () => {
    render(<KidDetailPage data={kidDetailData()} id="7" mutate={vi.fn()} />);
    openPhoto(recentPhotos[0]);
    const dialog = gallery();

    let image = expectCurrentPhoto(dialog, recentPhotos[0]);
    touchGesture(image, { from: { x: 200, y: 100 }, to: { x: 170, y: 103 } });
    image = expectCurrentPhoto(dialog, recentPhotos[0]);

    touchGesture(image, {
      from: { x: 200, y: 100 },
      to: { x: 195, y: 190 },
    });
    image = expectCurrentPhoto(dialog, recentPhotos[0]);

    touchGesture(image, { from: { x: 200, y: 100 }, to: { x: 110, y: 105 } });
    expectCurrentPhoto(dialog, recentPhotos[1]);
  });

  it('adds explicitly loaded older dashboard photos without gallery fetches and preserves the current photo by ID', async () => {
    window.history.pushState({}, '', '/dashboard');
    const appendedEntry = {
      ...olderEntry,
      id: 10,
      date: '2026-07-01T10:00:00Z',
      kid_id: 8,
      kid: 'Grace Hopper',
      text: 'Vertrauliche medizinische Beschreibung der nachgeladenen Maßnahme',
      photos: [{
        id: 101,
        url: '/api/first-aid/photos/101/media/',
        width: 1024,
        height: 768,
        alt: 'EH-Foto 1 von Grace Hopper, EH-Eintrag 10',
      }],
    };
    let resolveOlder;
    const fetchImpl = vi.fn().mockReturnValue(new Promise(resolve => {
      resolveOlder = resolve;
    }));
    render(<DashboardPage
      data={dashboardData({
        items: [recentEntry],
        next_cursor: 'older cursor',
        has_more: true,
        limit: 20,
      })}
      fetchImpl={fetchImpl}
    />);
    fireEvent.click(screen.getByRole('button', { name: 'Ältere EH-Einträge laden' }));
    await waitFor(() => expect(fetchImpl).toHaveBeenCalledWith(
      '/api/route-data/dashboard/?activity=first_aid&cursor=older+cursor',
      { credentials: 'same-origin' },
    ));

    openPhoto(recentPhotos[1]);
    const dialog = gallery();
    expectCurrentPhoto(dialog, recentPhotos[1]);
    expect(fetchImpl).toHaveBeenCalledTimes(1);

    await act(async () => resolveOlder(response({
      activity: {
        first_aid: { ...emptyPage, items: [appendedEntry] },
      },
    })));
    await screen.findByText(appendedEntry.text);
    expectCurrentPhoto(dialog, recentPhotos[1]);

    fireEvent.keyDown(dialog, { key: 'ArrowRight' });
    expectCurrentPhoto(dialog, appendedEntry.photos[0]);
    expect(fetchImpl).toHaveBeenCalledTimes(1);
    expect(window.location.pathname).toBe('/dashboard');
  });
});
