import { cleanup, render, screen, within } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { parseRoute } from '../routes';
import { ProfileEditPage, ProfilePage } from './profiles';

const profile = {
  id: 5,
  email: 'ada@example.test',
  rufname: 'Ada',
  phone: '+4312345',
  allergies: 'Nüsse',
  coffee: 'Schwarz',
  food: 'vt',
  food_display: '🧀 Vegetarisch',
  budo_family: 'M',
};

const data = {
  csrf_token: 'token',
  profile,
  focuses: [{ id: 3, name: 'Wald' }],
  turnus: { id: 2, label: 'T2-2026' },
};

describe('Profil pages', () => {
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
    window.history.pushState({}, '', '/');
  });

  it('renders focused profile, contact, and focus information without membership authority fields', () => {
    render(<ProfilePage data={data} />);

    const details = screen.getByRole('heading', { name: 'Ada' }).closest('section');
    expect(within(details).queryByText('Rolle')).not.toBeInTheDocument();
    expect(within(details).queryByText('Turnus')).not.toBeInTheDocument();
    expect(within(details).getByText('Essen').closest('p')).toHaveTextContent('🧀 Vegetarisch');
    expect(within(details).getByText('BuDo-Familie').closest('p')).toHaveTextContent('Medi');
    expect(within(details).getByText('Allergien').closest('p')).toHaveTextContent('Nüsse');
    expect(within(details).getByText('Kaffee').closest('p')).toHaveTextContent('Schwarz');
    expect(within(details).getByRole('link', { name: 'ada@example.test' })).toHaveAttribute('href', 'mailto:ada@example.test');
    expect(within(details).getByRole('link', { name: '+4312345' })).toHaveAttribute('href', 'tel:+4312345');
    expect(within(details).getByRole('link', { name: 'Wald' })).toHaveAttribute('href', '/schwerpunkt/3/');
    expect(screen.queryByText(/Abrechnung/)).not.toBeInTheDocument();
    expect(screen.queryByLabelText('Rufname')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Speichern' })).not.toBeInTheDocument();
  });

  it('retains editable personal profile values without membership authority controls', () => {
    render(<ProfileEditPage data={data} />);

    expect(screen.getByLabelText('Rufname')).toHaveValue('Ada');
    expect(screen.getByLabelText('E-Mail')).toHaveValue('ada@example.test');
    expect(screen.getByLabelText('E-Mail')).toHaveAttribute('type', 'email');
    expect(screen.getByLabelText('E-Mail')).toBeRequired();
    expect(screen.getByLabelText('Allergien')).toHaveValue('Nüsse');
    expect(screen.getByLabelText('Kaffee')).toHaveValue('Schwarz');
    expect(screen.queryByLabelText('Rolle')).not.toBeInTheDocument();
    expect(screen.getByLabelText('Essen')).toHaveValue('vt');
    expect(screen.getByLabelText('BuDo-Familie')).toHaveValue('M');
    expect(screen.getByRole('option', { name: 'X-largie' })).toHaveValue('XL');
    expect(screen.getByLabelText('Telefonnummer')).toHaveValue('+4312345');
    expect(screen.queryByLabelText('Turnus')).not.toBeInTheDocument();
    expect(screen.getByLabelText('Rufname').form).toHaveAttribute('action', '/profil/bearbeiten/');
    expect(screen.getByLabelText('Rufname').form.elements.csrfmiddlewaretoken).toHaveValue('token');
  });

  it('targets the selected profile when an authorized admin edits a teammate', () => {
    render(<ProfileEditPage data={data} target="/profil/5/" />);

    expect(screen.getByLabelText('Rufname').form).toHaveAttribute('action', '/profil/5/');
    expect(screen.getByLabelText('E-Mail')).toHaveValue('ada@example.test');
    expect(screen.getByLabelText('E-Mail')).toBeRequired();
  });

  it('declares read-only, own-edit, and admin-edit profile routes, but no Teamer detail route', () => {
    const ownProfileRoute = parseRoute('/profil');
    const ownProfileEditRoute = parseRoute('/profil/bearbeiten');
    const selectedProfileRoute = parseRoute('/profil/5');

    expect(ownProfileRoute).toMatchObject({ page: 'profile', readContractKey: 'profile' });
    expect(ownProfileEditRoute).toMatchObject({ page: 'profile-edit', readContractKey: 'profile', title: 'Profil bearbeiten' });
    expect(selectedProfileRoute).toMatchObject({ page: 'profile-edit', readContractKey: 'profile', id: '5' });
    expect(parseRoute('/teamer/5').page).toBe('not-found');
  });
});
