import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { KidDetailPage, KidInteractionForm } from './kids';
import { formatGermanDate, formatKidBirthday } from './shared';

describe('Kinder pages', () => {
  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  beforeEach(() => {
    document.cookie = 'interaction-bar=; Max-Age=0; Path=/';
    window.matchMedia = vi.fn().mockImplementation(query => ({
      matches: query.includes('max-width') ? false : true,
      media: query,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    }));
  });

  it('switches modes, stores the cookie, and saves money without navigating', async () => {
    const onSaved = vi.fn();
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ ok: true }) });
    vi.stubGlobal('fetch', fetchMock);
    render(<KidInteractionForm kid={{ id: 7 }} token="token" onSaved={onSaved} />);

    expect(screen.getByPlaceholderText('Notiz...')).toBeVisible();
    expect(screen.getByPlaceholderText('Taschengeld...').closest('#geld-form')).toHaveClass('hidden');
    fireEvent.click(screen.getByText('Notiz'));

    expect(screen.getByPlaceholderText('Notiz...').closest('#notiz-form')).toHaveClass('hidden');
    expect(screen.getByPlaceholderText('Taschengeld...')).toBeVisible();
    expect(document.cookie).toContain('interaction-bar=geld-form');
    expect(screen.getByPlaceholderText('Taschengeld...')).toHaveAttribute('min', '0');
    expect(screen.getByRole('button', { name: 'Abbuchen' })).toHaveClass('money-withdraw');
    expect(screen.getByRole('button', { name: 'Aufladen' })).toHaveClass('money-topup');
    expect(screen.queryByRole('button', { name: 'Senden' })).not.toBeInTheDocument();
    fireEvent.change(screen.getByPlaceholderText('Taschengeld...'), { target: { value: '5' } });
    fireEvent.click(screen.getByRole('button', { name: 'Abbuchen' }));

    await waitFor(() => expect(onSaved).toHaveBeenCalledOnce());
    expect(fetchMock.mock.calls[0][1].body.get('money_action')).toBe('withdraw');
    expect(screen.getByPlaceholderText('Taschengeld...')).toHaveValue(null);
  });

  it('restores the saved Taschengeld mode from its cookie', () => {
    document.cookie = 'interaction-bar=geld-form; Path=/';

    render(<KidInteractionForm kid={{ id: 7 }} token="token" />);

    expect(screen.getByPlaceholderText('Taschengeld...')).toBeVisible();
    expect(screen.getByPlaceholderText('Notiz...').closest('#notiz-form')).toHaveClass('hidden');
  });

  it.each([
    { present: false, action: 'Einchecken', path: '/check_in/7', title: 'Ada Lovelace ❌' },
    { present: true, action: 'Auschecken', path: '/check_out/7', title: 'Ada Lovelace' },
  ])('places $action in the BuDo card and reflects attendance in the name', ({ present, action, path, title }) => {
    const kid = {
      id: 7,
      full_name: 'Ada Lovelace',
      present,
      weeks: 2,
      birthday: '2012-07-02',
      social_security_number: '1234 030712',
      consent: present ? false : null,
      over_the_counter_medication: 'Ibuprofen',
      prescription_medication: '',
      tetanus: null,
      tick_vaccine: 'Ja',
      notes: [],
      transactions: [],
      remaining_money: 0,
      deposit: 0,
    };
    render(<KidDetailPage data={{ kids: [kid], turnus: { label: 'T2' }, csrf_token: 'token' }} id="7" mutate={vi.fn()} />);

    expect(screen.getByRole('heading', { name: title })).toBeInTheDocument();
    expect(screen.getByText('Geburtstag').closest('p')).toHaveTextContent('Geburtstag: 02.07.2012 ❗');
    expect(screen.getByText('Einverständnis für ärztliche Behandlung').closest('p')).toHaveTextContent(`Einverständnis für ärztliche Behandlung: ${present ? 'Nein' : '❗'}`);
    expect(screen.getByText('Rezeptfreie Medikamente').closest('p')).toHaveTextContent('Rezeptfreie Medikamente: Ibuprofen');
    expect(screen.getByText('Medikamente auf Rezept').closest('p')).toHaveTextContent('Medikamente auf Rezept: ❗');
    expect(screen.getByText('Tetanusimpfung').closest('p')).toHaveTextContent('Tetanusimpfung: ❗');
    expect(screen.getByText('Zeckenimpfung').closest('p')).toHaveTextContent('Zeckenimpfung: Ja');
    const checkAction = screen.getByRole('link', { name: action });
    expect(checkAction).toHaveAttribute('href', path);
    expect(checkAction.closest('.card')).toHaveAttribute('id', 'budo-container');
  });
});

describe('Kinder date formatting', () => {
  it('formats API dates and datetimes without timezone shifts', () => {
    expect(formatGermanDate('2026-07-02')).toBe('02.07.2026');
    expect(formatGermanDate('2026-07-02T23:30:00Z')).toBe('02.07.2026');
  });

  it('leaves non-date values unchanged', () => {
    expect(formatGermanDate('---')).toBe('---');
    expect(formatGermanDate(null)).toBeNull();
  });

  it.each([
    ['matching birthday', '1234 020712', '02.07.2012'],
    ['mismatching birthday', '1234 030712', '02.07.2012 ❗'],
    ['unavailable SV birthday', 'invalid', '02.07.2012'],
    ['invalid calculated birthday', '1234 310212', '02.07.2012'],
  ])('marks a %s only when the calculated SV birthday differs', (_case, socialSecurityNumber, expected) => {
    expect(formatKidBirthday({
      birthday: '2012-07-02',
      social_security_number: socialSecurityNumber,
    })).toBe(expected);
  });
});
