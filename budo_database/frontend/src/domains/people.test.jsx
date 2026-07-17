import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import App from '../App';
import { parseRoute } from '../routes';
import { ProfilePage, TeamerPage } from './people';

const response = (data, { ok = true } = {}) => ({
  ok,
  json: vi.fn().mockResolvedValue(data),
});

const profile = {
  id: 5,
  email: 'ada@example.test',
  rufname: 'Ada',
  phone: '+4312345',
  allergies: 'Nüsse',
  coffee: 'Schwarz',
  role: 'b',
  role_display: 'Betreuer:in',
  food: 'vt',
  food_display: '🧀 Vegetarisch',
  money_total: 12.5,
  money_items: [{
    id: 7,
    amount: 12.5,
    what: 'Material',
    date: '2026-07-17T09:30:00Z',
  }],
  can_change_turnus: true,
};

const data = {
  csrf_token: 'token',
  profile,
  focuses: [{ id: 3, name: 'Wald' }],
  turnus: { id: 2, label: 'T2-2026' },
  turnuses: [
    { id: 2, label: 'T2-2026' },
    { id: 4, label: 'T4-2026' },
  ],
};

describe('Profil and Teamer pages', () => {
  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
    window.history.pushState({}, '', '/');
  });

  it('renders focused profile, contact, role, focus, and accounting information', () => {
    render(<ProfilePage data={data} />);

    const details = screen.getByRole('heading', { name: 'Ada' }).closest('section');
    expect(within(details).getByText('Rolle').closest('p')).toHaveTextContent('Betreuer:in');
    expect(within(details).getByText('Turnus').closest('p')).toHaveTextContent('T2-2026');
    expect(within(details).getByText('Essen').closest('p')).toHaveTextContent('🧀 Vegetarisch');
    expect(within(details).getByText('Allergien').closest('p')).toHaveTextContent('Nüsse');
    expect(within(details).getByText('Kaffee').closest('p')).toHaveTextContent('Schwarz');
    expect(within(details).getByRole('link', { name: 'ada@example.test' })).toHaveAttribute('href', 'mailto:ada@example.test');
    expect(within(details).getByRole('link', { name: '+4312345' })).toHaveAttribute('href', 'tel:+4312345');
    expect(within(details).getByRole('link', { name: 'Wald' })).toHaveAttribute('href', '/schwerpunkt/3/');
    expect(screen.getByRole('heading', { name: 'Abrechnung: 12.50 €' })).toBeInTheDocument();
    expect(screen.getByText(/Ada am 17.07.2026: Material/)).toHaveTextContent('12.50 €');
  });

  it('retains profile form values, choices, CSRF target, and active Turnus', () => {
    render(<ProfilePage data={data} />);

    expect(screen.getByLabelText('Rufname')).toHaveValue('Ada');
    expect(screen.getByLabelText('Allergien')).toHaveValue('Nüsse');
    expect(screen.getByLabelText('Kaffee')).toHaveValue('Schwarz');
    expect(screen.getByLabelText('Rolle')).toHaveValue('b');
    expect(screen.getByLabelText('Essen')).toHaveValue('vt');
    expect(screen.getByLabelText('Telefonnummer')).toHaveValue('+4312345');
    expect(screen.getByLabelText('Turnus')).toHaveValue('2');
    expect(screen.getByRole('option', { name: 'T4-2026' })).toHaveValue('4');
    expect(screen.getByLabelText('Rufname').form).toHaveAttribute('action', '/profil/');
    expect(screen.getByLabelText('Rufname').form.elements.csrfmiddlewaretoken).toHaveValue('token');
  });

  it('does not render a Turnus control when existing permissions disallow it', () => {
    render(<ProfilePage data={{
      ...data,
      profile: { ...profile, can_change_turnus: false },
      turnuses: [],
    }} />);

    expect(screen.queryByLabelText('Turnus')).not.toBeInTheDocument();
  });


  it('renders only the selected Teamer with links, focuses, and accounting form', () => {
    render(<TeamerPage data={{
      csrf_token: 'token',
      person: profile,
      focuses: data.focuses,
      turnus: data.turnus,
    }} id="5" />);

    expect(screen.getByRole('heading', { name: 'Ada' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Wald' })).toHaveAttribute('href', '/schwerpunkt/3/');
    expect(screen.getByRole('link', { name: 'Informationen aktualisieren' })).toHaveAttribute('href', '/profil');
    const accounting = screen.getByRole('heading', { name: 'Abrechnung: 12.50 €' }).closest('section');
    expect(within(accounting).getByText(/Material/)).toBeInTheDocument();
    expect(screen.getByLabelText('Betrag in €').form).toHaveAttribute('action', '/teamer/5/');
    expect(screen.getByRole('button', { name: 'Save' })).toBeInTheDocument();
  });

  it('refreshes a saved Teamer accounting entry through the selected route only', async () => {
    const onSaved = vi.fn();
    const fetchMock = vi.fn().mockResolvedValue(response({
      ok: true,
      redirect: '/teamer/5/',
    }));
    vi.stubGlobal('fetch', fetchMock);
    render(<TeamerPage data={{
      csrf_token: 'token',
      person: { ...profile, money_items: [] },
      focuses: data.focuses,
      turnus: data.turnus,
    }} id="5" onSaved={onSaved} />);

    fireEvent.change(screen.getByLabelText('Betrag in €'), { target: { value: '8.50' } });
    fireEvent.change(screen.getByLabelText('Beschreibung'), { target: { value: 'Einkauf' } });
    fireEvent.click(screen.getByRole('button', { name: 'Save' }));

    await waitFor(() => expect(onSaved).toHaveBeenCalledWith({ ok: true, redirect: '/teamer/5/' }));
    const submitted = fetchMock.mock.calls[0][1].body;
    expect(submitted.get('_target')).toBe('/teamer/5/');
    expect(submitted.get('amount')).toBe('8.50');
    expect(submitted.get('what')).toBe('Einkauf');
  });

  it('reloads only the selected Teamer contract after an in-place accounting save', async () => {
    window.history.pushState({}, '', '/teamer/5');
    let teamerReads = 0;
    const fetchMock = vi.fn(async url => {
      if (url === '/api/bootstrap/') {
        return response({
          authenticated: true,
          csrf_token: 'token',
          messages: [],
          profile: { id: 1, rufname: 'Current user' },
          turnus: data.turnus,
          permissions: {},
          search_index: { kids: [], focuses: [], places: [] },
        });
      }
      if (url === '/api/route-data/teamer/?id=5') {
        teamerReads += 1;
        return response({
          person: {
            ...profile,
            money_total: teamerReads === 1 ? 0 : 8.5,
            money_items: teamerReads === 1 ? [] : [{
              id: 9,
              amount: 8.5,
              what: 'Einkauf',
              date: '2026-07-17T10:00:00Z',
            }],
          },
          focuses: data.focuses,
        });
      }
      if (url === '/api/form-submit/') {
        return response({ ok: true, redirect: '/teamer/5/' });
      }
      throw new Error(`Unexpected request: ${url}`);
    });
    vi.stubGlobal('fetch', fetchMock);
    render(<App fetchImpl={fetchMock} />);

    fireEvent.change(await screen.findByLabelText('Betrag in €'), { target: { value: '8.50' } });
    fireEvent.change(screen.getByLabelText('Beschreibung'), { target: { value: 'Einkauf' } });
    fireEvent.click(screen.getByRole('button', { name: 'Save' }));

    expect(await screen.findByText(/Ada am 17.07.2026: Einkauf/)).toHaveTextContent('8.50 €');
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(4));
    expect(fetchMock.mock.calls.map(call => call[0])).toEqual([
      '/api/bootstrap/',
      '/api/route-data/teamer/?id=5',
      '/api/form-submit/',
      '/api/route-data/teamer/?id=5',
    ]);
  });

  it('opts both people routes into focused contracts and resolves selected titles', () => {
    const profileRoute = parseRoute('/profil');
    const teamerRoute = parseRoute('/teamer/5');

    expect(profileRoute.focusedReadContract).toBe(true);
    expect(teamerRoute.focusedReadContract).toBe(true);
    expect(teamerRoute.resolveTitle(teamerRoute, { person: profile })).toBe('Ada');
  });
});
