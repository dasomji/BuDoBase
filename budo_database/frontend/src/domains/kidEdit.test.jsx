import userEvent from '@testing-library/user-event';
import { cleanup, render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { Toaster } from '../components/ui/toast';
import {
  parseRoute,
  renderRoute,
  resolveRouteTitle,
  routeHeaderAction,
} from '../routes';

const FIELD_NAMES = [
  'first_name',
  'last_name',
  'sex',
  'birthday',
  'stay_weeks',
  'siblings',
  'tent_request',
  'budo_experience',
  'social_security_number',
  'illness',
  'drugs',
  'vegetarian',
  'special_food',
  'swimmer',
  'consent',
  'over_the_counter_medication',
  'prescription_medication',
  'tetanus',
  'tick_vaccine',
  'organization',
  'registrant_first_name',
  'registrant_last_name',
  'registrant_email',
  'registrant_phone',
  'insured_with',
  'emergency_contacts',
  'budo_family',
];

const TEXT_FIELDS = new Set([
  'first_name',
  'last_name',
  'siblings',
  'tent_request',
  'social_security_number',
  'illness',
  'drugs',
  'special_food',
  'swimmer',
  'over_the_counter_medication',
  'prescription_medication',
  'tetanus',
  'tick_vaccine',
  'organization',
  'registrant_first_name',
  'registrant_last_name',
  'registrant_email',
  'registrant_phone',
  'insured_with',
  'emergency_contacts',
]);

const baseline = suffix => `v1.${suffix.repeat(43).slice(0, 43)}`;

function editData() {
  const fields = Object.fromEntries(FIELD_NAMES.map(name => [name, TEXT_FIELDS.has(name) ? '' : null]));
  Object.assign(fields, {
    first_name: 'Ada',
    last_name: 'Lovelace',
    birthday: '2012-07-02',
    stay_weeks: 2,
    illness: 'synthetische Allergie',
    budo_family: 'M',
  });
  return {
    kid: {
      id: 7,
      full_name: 'Ada Lovelace',
      edit_version: 4,
      fields,
      field_options: {
        sex: [
          { value: null, label: 'Nicht angegeben' },
          { value: 'female', label: 'weiblich' },
          { value: 'male', label: 'männlich' },
          { value: 'diverse', label: 'divers' },
        ],
        stay_weeks: [
          { value: null, label: 'Nicht angegeben' },
          { value: 1, label: '1 Woche' },
          { value: 2, label: '2 Wochen' },
        ],
        budo_experience: [
          { value: null, label: 'Unbekannt' },
          { value: true, label: 'Ja' },
          { value: false, label: 'Nein' },
        ],
        vegetarian: [
          { value: null, label: 'Unbekannt' },
          { value: true, label: 'Ja' },
          { value: false, label: 'Nein' },
        ],
        consent: [
          { value: null, label: 'Unbekannt' },
          { value: true, label: 'Ja' },
          { value: false, label: 'Nein' },
        ],
        budo_family: [
          { value: null, label: 'Nicht zugeordnet' },
          { value: 'S', label: 'Smallie' },
          { value: 'M', label: 'Medi' },
          { value: 'L', label: 'Largie' },
          { value: 'XL', label: 'X-largie' },
        ],
      },
      field_baselines: Object.fromEntries(FIELD_NAMES.map((name, index) => [name, baseline(String.fromCharCode(65 + (index % 26)))])),
      happy_cleaning_number: { value: 42, version: 3 },
      swp_periods: [
        {
          id: 17,
          code: 'w1',
          label: 'Woche 1 (3 Tage)',
          start: '2026-07-05',
          duration_days: 3,
          baseline: baseline('Y'),
          target: { kind: 'focus', focus_id: 91 },
          options: [
            { target: { kind: 'unassigned' }, label: 'Nicht eingeteilt' },
            { target: { kind: 'focus', focus_id: 91 }, label: 'Theater' },
          ],
        },
        {
          id: 18,
          code: 'u',
          label: 'Unklar (1 Tag)',
          start: '2026-07-08',
          duration_days: 1,
          baseline: baseline('Z'),
          target: { kind: 'unassigned' },
          options: [
            { target: { kind: 'unassigned' }, label: 'Nicht eingeteilt' },
            { target: { kind: 'focus', focus_id: 92 }, label: 'Wald' },
          ],
        },
      ],
      happy_cleaning_events: [
        {
          id: 42,
          display_number: 1,
          label: 'Happy Cleaning 1',
          revision: 19,
          assignment_version: 11,
          target: { kind: 'station', station_id: 8 },
          options: [
            { target: { kind: 'unassigned' }, label: 'Nicht eingeteilt', can_select: true },
            { target: { kind: 'excused' }, label: 'Entschuldigt', can_select: true },
            { target: { kind: 'station', station_id: 8 }, label: 'Küche · 11/12', can_select: true, is_current: true },
            { target: { kind: 'station', station_id: 9 }, label: '<img src=x onerror=alert(1)> · 6/6 (voll)', can_select: false, is_current: false },
          ],
        },
        {
          id: 43,
          display_number: 2,
          label: 'Happy Cleaning 2',
          revision: 7,
          assignment_version: 0,
          target: { kind: 'unassigned' },
          options: [
            { target: { kind: 'unassigned' }, label: 'Nicht eingeteilt', can_select: true },
            { target: { kind: 'excused' }, label: 'Entschuldigt', can_select: true },
          ],
        },
      ],
    },
  };
}

function setMobile(mobile) {
  window.matchMedia = vi.fn().mockImplementation(query => ({
    matches: query === '(max-width: 900px)' ? mobile : !mobile,
    media: query,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
  }));
}

function renderEdit({ data = editData(), mutate = vi.fn(), navigate = vi.fn() } = {}) {
  const route = parseRoute('/kid_details/7/edit');
  return {
    ...render(
      <Toaster timeout={0}>
        {renderRoute(route, { data, mutate, navigate })}
      </Toaster>,
    ),
    mutate,
    navigate,
    route,
  };
}

function fieldControls(form) {
  return [...form.elements].filter(element => (
    element.name
    && !['csrfmiddlewaretoken', 'request_id'].includes(element.name)
    && !['submit', 'button'].includes(element.type)
  ));
}

function commandError(payload) {
  const error = new Error('Update failed');
  error.payload = payload;
  return error;
}

describe('kid edit route and rendered form', () => {
  beforeEach(() => setMobile(false));

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
    window.localStorage.clear();
    window.sessionStorage.clear();
  });

  it('owns the dedicated route/title and exposes Bearbeiten from kid detail', () => {
    const editRoute = parseRoute('/kid_details/7/edit');

    expect(editRoute).toMatchObject({
      page: 'kid-edit',
      domain: 'kids',
      readContractKey: 'kid-edit',
      id: '7',
    });
    expect(resolveRouteTitle(editRoute, { authenticated: true, kid: { id: 7, full_name: 'Ada Lovelace' } })).toBe('Ada Lovelace bearbeiten');

    render(routeHeaderAction(parseRoute('/kid_details/7'), {}));
    const action = screen.getByRole('link', { name: 'Bearbeiten' });
    expect(action).toHaveAttribute('href', '/kid_details/7/edit');
    expect(action).toHaveClass('mobile-icon-action');
    expect(action.querySelector('svg')).toHaveAttribute('aria-hidden', 'true');
  });

  it('renders 28 fixed controls plus every dynamic selector in four-card source order', () => {
    renderEdit();

    const form = screen.getByRole('form', { name: 'Kind bearbeiten' });
    const cardHeadings = within(form).getAllByRole('heading', { level: 2 }).map(heading => heading.textContent);
    expect(cardHeadings).toEqual(['Allgemein', 'Gesundheitsinfos', 'Familie', 'BuDo']);

    const controls = fieldControls(form);
    const names = controls.map(control => control.name);
    expect(names).toEqual([
      ...FIELD_NAMES.slice(0, 27),
      'swp.17',
      'swp.18',
      'happy_cleaning_number',
      'happy_cleaning.42',
      'happy_cleaning.43',
    ]);
    expect(names.filter(name => FIELD_NAMES.includes(name) || name === 'happy_cleaning_number')).toHaveLength(28);
    expect(names.filter(name => name.startsWith('swp.') || name.startsWith('happy_cleaning.'))).toHaveLength(4);

    const requiredControls = controls.filter(control => control.required);
    expect(requiredControls.map(control => control.name)).toEqual(['first_name', 'last_name']);
    expect(screen.getByText(/\* kennzeichnet Pflichtfelder/)).toBeInTheDocument();
    expect(form).not.toHaveTextContent('❗');

    const budo = screen.getByRole('heading', { name: 'BuDo' }).closest('.card');
    expect(within(budo).getAllByRole('heading', { level: 3 }).map(heading => heading.textContent)).toEqual(['Schwerpunkte', 'Happy Cleaning']);
    expect(within(budo).getAllByRole('option', { name: 'Entschuldigt' })).toHaveLength(2);
    expect(within(budo).getAllByRole('option', { name: 'Nicht eingeteilt' })).toHaveLength(4);
    expect(document.querySelector('img[src="x"]')).not.toBeInTheDocument();
  });

  it('keeps all four cards open and one reachable action surface below 901px', () => {
    setMobile(true);
    renderEdit();

    const form = screen.getByRole('form', { name: 'Kind bearbeiten' });
    const toggles = ['Allgemein', 'Gesundheitsinfos', 'Familie', 'BuDo']
      .map(name => within(form).getByRole('button', { name: `${name} schließen` }));
    expect(toggles.every(toggle => toggle.getAttribute('aria-expanded') === 'true')).toBe(true);

    const actions = within(form).getByRole('region', { name: 'Bearbeitungsaktionen' });
    expect(within(actions).getByRole('button', { name: 'Abbrechen' })).toBeEnabled();
    expect(within(actions).getByRole('button', { name: 'Alle Änderungen speichern' })).toBeEnabled();
    expect(form.compareDocumentPosition(actions) & Node.DOCUMENT_POSITION_CONTAINED_BY).toBeTruthy();
    expect(form.lastElementChild).toBe(actions);
  });

  it('shows all field errors accessibly, opens cards, focuses canonical first, and emits no generic toast', async () => {
    const user = userEvent.setup();
    const mutate = vi.fn().mockRejectedValue(commandError({
      ok: false,
      code: 'conflict',
      errors: {
        'happy_cleaning.42': [{ code: 'station_full', message: 'Küche wurde zwischenzeitlich voll (12/12).' }],
        illness: [{ code: 'too_long', message: 'Krankheiten und Besonderheiten darf höchstens 10000 Zeichen lang sein.' }],
        first_name: [{ code: 'stale', message: 'Vorname wurde zwischenzeitlich geändert. Bitte Seite neu laden.' }],
      },
      reload_required: true,
    }));
    renderEdit({ mutate });

    await user.click(screen.getByRole('button', { name: 'Allgemein schließen' }));
    await user.click(screen.getByRole('button', { name: 'Gesundheitsinfos schließen' }));
    await user.click(screen.getByRole('button', { name: 'Alle Änderungen speichern' }));

    const summary = await screen.findByRole('alert');
    expect(summary).toHaveTextContent(/^Nichts gespeichert/);
    expect(summary).toHaveTextContent('3 Fehler');
    expect(within(summary).getByRole('button', { name: 'Zum ersten Fehler' })).toBeEnabled();

    const firstName = screen.getByRole('textbox', { name: /^Vorname(?: \*)?$/ });
    const illness = screen.getByRole('textbox', { name: 'Krankheiten und Besonderheiten' });
    const cleaning = screen.getByRole('combobox', { name: 'Happy Cleaning 1' });
    for (const control of [firstName, illness, cleaning]) {
      expect(control).toHaveAttribute('aria-invalid', 'true');
      const describedBy = control.getAttribute('aria-describedby');
      expect(describedBy).toBeTruthy();
      expect(document.getElementById(describedBy)).toBeInTheDocument();
    }
    expect(document.activeElement).toBe(firstName);
    expect(screen.getByRole('heading', { name: /Allgemein.*1 Fehler/ })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /Gesundheitsinfos.*1 Fehler/ })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /BuDo.*1 Fehler/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Allgemein.*schließen/ })).toHaveAttribute('aria-expanded', 'true');
    expect(screen.getByRole('button', { name: /Gesundheitsinfos.*schließen/ })).toHaveAttribute('aria-expanded', 'true');
    expect(within(screen.getByRole('region', { name: 'Benachrichtigungen' })).queryByText(/nicht gespeichert|voll|zwischenzeitlich/i)).not.toBeInTheDocument();
  });

  it('returns immediately when clean and confirms the exact dirty-cancel flow', async () => {
    const user = userEvent.setup();
    const cleanNavigate = vi.fn();
    const clean = renderEdit({ navigate: cleanNavigate });

    await user.click(screen.getByRole('button', { name: 'Abbrechen' }));
    expect(cleanNavigate).toHaveBeenCalledWith('/kid_details/7');
    clean.unmount();

    const dirtyNavigate = vi.fn();
    renderEdit({ navigate: dirtyNavigate });
    await user.clear(screen.getByRole('textbox', { name: /^Vorname(?: \*)?$/ }));
    await user.type(screen.getByRole('textbox', { name: /^Vorname(?: \*)?$/ }), 'Grace');
    await user.click(screen.getByRole('button', { name: 'Abbrechen' }));

    const dialog = screen.getByRole('dialog', { name: 'Änderungen verwerfen?' });
    expect(dirtyNavigate).not.toHaveBeenCalled();
    await user.click(within(dialog).getByRole('button', { name: 'Weiter bearbeiten' }));
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    expect(screen.getByRole('textbox', { name: /^Vorname(?: \*)?$/ })).toHaveValue('Grace');

    await user.click(screen.getByRole('button', { name: 'Abbrechen' }));
    await user.click(within(screen.getByRole('dialog', { name: 'Änderungen verwerfen?' })).getByRole('button', { name: 'Verwerfen' }));
    expect(dirtyNavigate).toHaveBeenCalledWith('/kid_details/7');
  });

  it.each(['updated', 'no_change'])('submits one complete %s command, redirects, and shows one success toast', async result => {
    const user = userEvent.setup();
    const navigate = vi.fn();
    const mutate = vi.fn().mockResolvedValue({
      ok: true,
      result,
      kid_id: 7,
      redirect: '/kid_details/7',
      versions: {},
      replayed: false,
    });
    renderEdit({ mutate, navigate });

    await user.click(screen.getByRole('button', { name: 'Alle Änderungen speichern' }));

    await waitFor(() => expect(mutate).toHaveBeenCalledOnce());
    const [url, payload] = mutate.mock.calls[0];
    expect(url).toBe('/api/kids/7/edit/');
    expect(payload).toMatchObject({
      expected_edit_version: 4,
      happy_cleaning_number: 42,
      expected_number_version: 3,
    });
    expect(Object.keys(payload.fields)).toEqual(FIELD_NAMES);
    expect(Object.keys(payload.field_baselines)).toEqual(FIELD_NAMES);
    expect(payload.swp.map(item => item.period_id)).toEqual([17, 18]);
    expect(payload.happy_cleaning.map(item => item.event_id)).toEqual([42, 43]);
    expect(payload.request_id).toMatch(/^[0-9A-HJKMNP-TV-Z]{26}$/);
    expect(url).not.toContain('Ada');
    expect(navigate).toHaveBeenCalledWith('/kid_details/7');

    const notifications = screen.getByRole('region', { name: 'Benachrichtigungen' });
    const success = await within(notifications).findByText('Alle Daten und Einteilungen wurden gespeichert.');
    expect(success.closest('.app-toast')).toHaveAttribute('data-type', 'success');
    expect(within(notifications).getAllByText('Alle Daten und Einteilungen wurden gespeichert.')).toHaveLength(1);
  });

  it('keeps optional legacy blanks saveable and sensitive values out of persistence, URLs, and feedback', async () => {
    const user = userEvent.setup();
    const data = editData();
    const privateValue = 'synthetisch-privat-8Qm4';
    data.kid.fields.illness = privateValue;
    data.kid.fields.registrant_email = 'legacy-invalid@';
    const storageSpy = vi.spyOn(Storage.prototype, 'setItem');
    const mutate = vi.fn().mockRejectedValue(new Error('Verbindung unterbrochen'));
    renderEdit({ data, mutate });

    expect(screen.queryByText('❗')).not.toBeInTheDocument();
    expect(screen.getByRole('textbox', { name: 'E-Mail der anmeldenden Person' })).toHaveValue('legacy-invalid@');
    await user.click(screen.getByRole('button', { name: 'Alle Änderungen speichern' }));

    const notifications = screen.getByRole('region', { name: 'Benachrichtigungen' });
    const error = await within(notifications).findByText('Die Änderungen konnten nicht gespeichert werden.');
    expect(error.closest('.app-toast')).toHaveAttribute('data-type', 'error');
    expect(notifications).not.toHaveTextContent(privateValue);
    expect(window.location.href).not.toContain(privateValue);
    expect(storageSpy).not.toHaveBeenCalled();
    expect(window.localStorage).toHaveLength(0);
    expect(window.sessionStorage).toHaveLength(0);
  });
});
