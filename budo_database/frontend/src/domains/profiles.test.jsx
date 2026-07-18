import { cleanup, render, screen, within } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { parseRoute } from '../routes';
import { ProfilePage, TeamPage } from './profiles';

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
  budo_family: 'M',
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

function setTeamViewport(width) {
  vi.spyOn(window, 'matchMedia').mockImplementation(query => {
    const maxWidth = Number(query.match(/max-width:\s*(\d+)px/)?.[1]);
    return {
      matches: Number.isFinite(maxWidth) && width <= maxWidth,
      media: query,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    };
  });
}

describe('Profil and Team pages', () => {
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
    window.history.pushState({}, '', '/');
  });

  it('renders focused profile, contact, role, and focus information without accounting', () => {
    render(<ProfilePage data={data} />);

    const details = screen.getByRole('heading', { name: 'Ada' }).closest('section');
    expect(within(details).getByText('Rolle').closest('p')).toHaveTextContent('Betreuer:in');
    expect(within(details).getByText('Turnus').closest('p')).toHaveTextContent('T2-2026');
    expect(within(details).getByText('Essen').closest('p')).toHaveTextContent('🧀 Vegetarisch');
    expect(within(details).getByText('BuDo-Familie').closest('p')).toHaveTextContent('Medi');
    expect(within(details).getByText('Allergien').closest('p')).toHaveTextContent('Nüsse');
    expect(within(details).getByText('Kaffee').closest('p')).toHaveTextContent('Schwarz');
    expect(within(details).getByRole('link', { name: 'ada@example.test' })).toHaveAttribute('href', 'mailto:ada@example.test');
    expect(within(details).getByRole('link', { name: '+4312345' })).toHaveAttribute('href', 'tel:+4312345');
    expect(within(details).getByRole('link', { name: 'Wald' })).toHaveAttribute('href', '/schwerpunkt/3/');
    expect(screen.queryByText(/Abrechnung/)).not.toBeInTheDocument();
  });

  it('retains own profile form values, choices, CSRF target, and active Turnus', () => {
    render(<ProfilePage data={data} />);

    expect(screen.getByLabelText('Rufname')).toHaveValue('Ada');
    expect(screen.getByLabelText('Allergien')).toHaveValue('Nüsse');
    expect(screen.getByLabelText('Kaffee')).toHaveValue('Schwarz');
    expect(screen.getByLabelText('Rolle')).toHaveValue('b');
    expect(screen.getByLabelText('Essen')).toHaveValue('vt');
    expect(screen.getByLabelText('BuDo-Familie')).toHaveValue('M');
    expect(screen.getByRole('option', { name: 'X-largie' })).toHaveValue('XL');
    expect(screen.getByLabelText('Telefonnummer')).toHaveValue('+4312345');
    expect(screen.getByLabelText('Turnus')).toHaveValue('2');
    expect(screen.getByRole('option', { name: 'T4-2026' })).toHaveValue('4');
    expect(screen.getByLabelText('Rufname').form).toHaveAttribute('action', '/profil/');
    expect(screen.getByLabelText('Rufname').form.elements.csrfmiddlewaretoken).toHaveValue('token');
  });

  it('targets the selected profile when an authorized admin edits a teammate', () => {
    render(<ProfilePage data={data} target="/profil/5/" />);

    expect(screen.getByLabelText('Rufname').form).toHaveAttribute('action', '/profil/5/');
  });

  it('does not render a Turnus control when existing permissions disallow it', () => {
    render(<ProfilePage data={{
      ...data,
      profile: { ...profile, can_change_turnus: false },
      turnuses: [],
    }} />);

    expect(screen.queryByLabelText('Turnus')).not.toBeInTheDocument();
  });

  it('shows an update button only on the signed-in user’s Team card', () => {
    render(<TeamPage data={{
      profile: { id: 5 },
      permissions: { change_profiles: false },
      turnus: data.turnus,
      team: [
        { ...profile, focuses: data.focuses },
        {
          ...profile,
          id: 6,
          rufname: 'Grace',
          email: 'grace@example.test',
          phone: '+436789',
          focuses: [],
        },
      ],
    }} />);

    const adaCard = screen.getByRole('heading', { name: 'Ada' }).closest('section');
    expect(within(adaCard).getByText('Turnus').closest('p')).toHaveTextContent('T2-2026');
    expect(within(adaCard).getByRole('link', { name: 'Wald' })).toHaveAttribute('href', '/schwerpunkt/3/');
    expect(within(adaCard).getByRole('link', { name: 'Informationen aktualisieren' })).toHaveAttribute('href', '/profil/');
    const graceCard = screen.getByRole('heading', { name: 'Grace' }).closest('section');
    expect(within(graceCard).getByText('Keine Schwerpunkte zugeteilt.')).toBeInTheDocument();
    expect(within(graceCard).queryByRole('link', { name: 'Informationen aktualisieren' })).not.toBeInTheDocument();
  });

  it('lets admins update every profile from its Team card', () => {
    render(<TeamPage data={{
      profile: { id: 5 },
      permissions: { change_profiles: true },
      turnus: data.turnus,
      team: [
        { ...profile, focuses: [] },
        { ...profile, id: 6, rufname: 'Grace', focuses: [] },
      ],
    }} />);

    const adaCard = screen.getByRole('heading', { name: 'Ada' }).closest('section');
    const graceCard = screen.getByRole('heading', { name: 'Grace' }).closest('section');
    expect(within(adaCard).getByRole('link', { name: 'Informationen aktualisieren' })).toHaveAttribute('href', '/profil/');
    expect(within(graceCard).getByRole('link', { name: 'Informationen aktualisieren' })).toHaveAttribute('href', '/profil/6/');
  });

  it.each([
    [1400, [[5, 8], [6, 9], [7]]],
    [1000, [[5, 7, 9], [6, 8]]],
    [700, [[5, 6, 7, 8, 9]]],
  ])('stacks Team profile cards in fixed responsive flex columns at %ipx', (width, expectedColumns) => {
    setTeamViewport(width);
    const team = Array.from({ length: 5 }, (_, index) => ({
      ...profile,
      id: index + 5,
      rufname: `Teamer ${index + 1}`,
      focuses: [],
    }));

    const { container } = render(<TeamPage data={{ team, turnus: data.turnus }} />);
    const actualColumns = Array.from(container.querySelectorAll('.team-column'), column => (
      Array.from(column.children, card => Number(card.id.replace('team-profile-', '')))
    ));

    expect(actualColumns).toEqual(expectedColumns);
  });

  it('shows an empty state when no active-turnus Team exists', () => {
    render(<TeamPage data={{ team: [], turnus: null }} />);

    expect(screen.getByText('Kein Team für den aktiven Turnus vorhanden.')).toBeInTheDocument();
  });

  it('declares own and admin profile editing plus Team routes, but no Teamer detail route', () => {
    const ownProfileRoute = parseRoute('/profil');
    const selectedProfileRoute = parseRoute('/profil/5');
    const teamRoute = parseRoute('/team');

    expect(ownProfileRoute.readContractKey).toBe('profile');
    expect(selectedProfileRoute).toMatchObject({ page: 'profile', readContractKey: 'profile', id: '5' });
    expect(teamRoute).toMatchObject({ page: 'team', readContractKey: 'team', title: 'Team' });
    expect(parseRoute('/teamer/5').page).toBe('not-found');
  });
});
