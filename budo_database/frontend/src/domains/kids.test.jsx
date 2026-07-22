import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import App from '../App';
import { parseRoute } from '../routes';
import { KidDetailPage, KidInteractionForm, KidsPage } from './kids';
import { formatGermanDate, formatKidBirthday } from './shared';

const response = (data, { ok = true, status = 200 } = {}) => ({
  ok,
  status,
  json: vi.fn().mockResolvedValue(data),
});

describe('Kinder pages', () => {
  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
    window.history.pushState({}, '', '/');
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

    const note = screen.getByPlaceholderText('Notiz...');
    expect(note).toBeVisible();
    expect(note.tagName).toBe('TEXTAREA');
    expect(note).toHaveAttribute('rows', '2');
    expect(screen.getByRole('button', { name: 'Senden' })).toHaveClass('interaction-send-button');
    expect(screen.getByPlaceholderText('Taschengeld...').closest('#geld-form')).toHaveClass('hidden');
    expect(screen.queryByRole('group', { name: 'Eingabemodus' })).not.toBeInTheDocument();
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

  it('switches to Erste Hilfe and submits a required description', async () => {
    const onSaved = vi.fn();
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ ok: true }),
    });
    vi.stubGlobal('fetch', fetchMock);
    render(<KidInteractionForm kid={{ id: 7 }} token="token" onSaved={onSaved} />);

    fireEvent.click(screen.getByText('Notiz'));
    fireEvent.click(screen.getByText('Taschengeld'));

    const description = screen.getByPlaceholderText('Erste-Hilfe-Maßnahme...');
    expect(description).toBeVisible();
    expect(description.tagName).toBe('TEXTAREA');
    expect(description).toHaveAttribute('rows', '2');
    expect(description).toBeRequired();
    expect(document.cookie).toContain('interaction-bar=erste-hilfe-form');
    fireEvent.change(description, { target: { value: 'Knie verbunden' } });
    fireEvent.click(screen.getByRole('button', { name: 'EH-Eintrag senden' }));

    await waitFor(() => expect(onSaved).toHaveBeenCalledOnce());
    const body = fetchMock.mock.calls[0][1].body;
    expect(body.get('interaction_kind')).toBe('first_aid');
    expect(body.get('erste_hilfe_beschreibung')).toBe('Knie verbunden');
    expect(description).toHaveValue('');
  });

  it('submits note image attachments through the + control', async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ ok: true }) });
    vi.stubGlobal('fetch', fetchMock);
    render(<KidInteractionForm kid={{ id: 7 }} token="token" />);

    const input = screen.getByLabelText('Notiz-Fotos');
    const photo = new File(['photo'], 'iphone.heic', { type: 'image/heic' });
    expect(input).toHaveAttribute('type', 'file');
    expect(input).toHaveAttribute('multiple');
    fireEvent.change(screen.getByPlaceholderText('Notiz...'), { target: { value: 'Mit Foto' } });
    fireEvent.change(input, { target: { files: [photo] } });
    expect(document.querySelector('.attachment-count')).toHaveTextContent('1');
    expect(document.querySelector('.note-input-field .attachment-button')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Senden' }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledOnce());
    const body = fetchMock.mock.calls[0][1].body;
    expect(body.get('notiz')).toBe('Mit Foto');
    expect(body.getAll('notiz_fotos')).toEqual([photo]);
  });

  it('shows the server validation message for a blank first-aid description', async () => {
    const fetchMock = vi.fn().mockResolvedValue(response(
      { ok: false, errors: ['Bitte eine Beschreibung eingeben.'] },
      { ok: false, status: 422 },
    ));
    vi.stubGlobal('fetch', fetchMock);
    render(<KidInteractionForm kid={{ id: 7 }} token="token" />);

    fireEvent.click(screen.getByText('Notiz'));
    fireEvent.click(screen.getByText('Taschengeld'));
    fireEvent.change(screen.getByPlaceholderText('Erste-Hilfe-Maßnahme...'), {
      target: { value: '   ' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'EH-Eintrag senden' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('Bitte eine Beschreibung eingeben.');
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
      first_aid_entries: [
        { id: 3, author: 'Boris', date: '2026-07-03T10:00:00Z', text: 'Knie verbunden' },
      ],
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
    const firstAidCard = screen.getByRole('heading', { name: 'Erste Hilfe' }).closest('.card');
    expect(firstAidCard).toHaveTextContent('Boris am 03.07.2026: Knie verbunden');
    const checkAction = screen.getByRole('link', { name: action });
    expect(checkAction).toHaveAttribute('href', path);
    expect(checkAction.closest('.card')).toHaveAttribute('id', 'budo-container');
  });

  it('keeps the directory columns, filtering, sorting, links, and empty state on focused rows', () => {
    const { rerender } = render(<KidsPage data={{ kids: [
      {
        id: 8,
        full_name: 'Grace Hopper',
        present: true,
        budo_family: 'L',
        special_family: 'Falkenhaus',
        sex_short: '♀',
        age: 14,
        weeks: 2,
        focus_w1: 'Wald',
        focus_w2: 'Theater',
        siblings: '---',
        tent_request: 'Ada',
        food: '🌱',
        drugs: '',
        illness: '',
        note: '',
        booking_note: '',
      },
      {
        id: 7,
        full_name: 'Ada Lovelace',
        present: false,
        budo_family: 'M',
        special_family: 'Biberhaus',
        sex_short: '♀',
        age: 13,
        weeks: 1,
        focus_w1: 'Theater',
        focus_w2: 'Wald',
        siblings: 'Charles',
        tent_request: 'Grace',
        food: '🥩',
        drugs: 'Asthmaspray',
        illness: 'Allergie',
        note: 'Teamnotiz',
        booking_note: 'Buchungsnotiz',
      },
    ] }} />);

    expect(screen.getByRole('link', { name: 'Ada Lovelace ❌' })).toHaveAttribute('href', '/kid_details/7');
    expect(screen.getByRole('columnheader', { name: /Anmerkungen \(Buchung\)/ })).toBeInTheDocument();
    fireEvent.change(screen.getByRole('searchbox', { name: 'Kinder filtern' }), { target: { value: 'grace' } });
    expect(screen.getByRole('link', { name: 'Grace Hopper' })).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: 'Ada Lovelace ❌' })).not.toBeInTheDocument();

    fireEvent.change(screen.getByRole('searchbox', { name: 'Kinder filtern' }), { target: { value: '' } });
    fireEvent.click(screen.getByRole('button', { name: 'Alter sortieren' }));
    expect(screen.getAllByRole('row')[1]).toHaveTextContent('Ada Lovelace');

    rerender(<KidsPage data={{ kids: [] }} />);
    expect(screen.getByText('Keine Einträge')).toBeInTheDocument();
  });

  it('declares the Kinder directory and detail contracts', () => {
    expect(parseRoute('/all_kids')).toMatchObject({
      readContractKey: 'kids-directory',
    });
    expect(parseRoute('/kid_details/21')).toMatchObject({
      readContractKey: 'kid-detail',
      id: '21',
    });
  });

  it('refreshes only the selected Kind contract after a Pfand update', async () => {
    window.history.pushState({}, '', '/kid_details/7');
    let detailReads = 0;
    const fetchImpl = vi.fn(async (url) => {
      if (url === '/api/bootstrap/') {
        return response({
          authenticated: true,
          csrf_token: 'token',
          messages: [],
          profile: { id: 1, rufname: 'Ada' },
          turnus: { id: 2, label: 'T2' },
          permissions: { change_kids: true },
          search_index: { kids: [{ id: 7, full_name: 'Ada Lovelace', present: true }], focuses: [], places: [] },
        });
      }
      if (url === '/api/route-data/kid-detail/?id=7') {
        detailReads += 1;
        const deposit = detailReads;
        return response({
          kids: [{
            id: 7,
            full_name: 'Ada Lovelace',
            present: true,
            weeks: 2,
            birthday: '2012-07-02',
            notes: [],
            transactions: [],
            remaining_money: 10 - deposit * 0.25,
            deposit,
          }],
        });
      }
      if (url === '/update_pfand/') return response({ status: 'success' });
      throw new Error(`Unexpected request: ${url}`);
    });

    render(<App fetchImpl={fetchImpl} />);

    expect(await screen.findByRole('heading', { name: 'Pfand: 1' })).toBeInTheDocument();
    expect(document.querySelector('#headertitle h1 a')).toHaveAttribute('href', '/admin/budo_app/kinder/7/change/');
    fireEvent.click(screen.getByRole('button', { name: '+ Pfand' }));
    expect(await screen.findByRole('heading', { name: 'Pfand: 2' })).toBeInTheDocument();

    expect(detailReads).toBe(2);
    expect(fetchImpl.mock.calls.filter(([url]) => url === '/api/bootstrap/')).toHaveLength(1);
    expect(fetchImpl.mock.calls.some(([url]) => url.startsWith('/api/app-data/'))).toBe(false);
  });

  it('keeps interaction textareas to two through four lines and right-aligns Pfand actions', () => {
    const css = readFileSync(resolve(process.cwd(), 'src/app.css'), 'utf8');

    expect(css).toMatch(/\.interaction-textarea\s*\{[^}]*field-sizing:\s*content;[^}]*min-height:\s*2lh;[^}]*max-height:\s*4lh;[^}]*overflow-y:\s*auto;/s);
    expect(css).toMatch(/#pfand \.card-info-container\s*\{[^}]*padding-top:\s*0;/s);
    expect(css).toMatch(/#pfand \.deposit-actions\s*\{[^}]*justify-content:\s*flex-end;[^}]*margin-top:\s*0;/s);
    expect(css).toMatch(/@media \(max-width: 600px\)[\s\S]*#interaction-bar form:has\(\.interaction-send-button\)\s*\{[^}]*grid-template-columns:\s*minmax\(0, 1fr\) auto;/);
    expect(css).toMatch(/\.interaction-textarea\s*\{[^}]*width:\s*100%;[^}]*max-width:\s*100%;/s);
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
