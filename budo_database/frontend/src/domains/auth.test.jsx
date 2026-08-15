import { cleanup, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';

import { AuthPage } from './auth';

describe('authentication pages', () => {
  afterEach(cleanup);

  it('keeps login public, posts to the existing login URL, and offers registration', () => {
    render(<AuthPage kind="login" data={{ csrf_token: 'token' }} />);

    expect(screen.getByRole('heading', { name: 'Login' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Login' }).form).toHaveAttribute('action', '/login/');
    expect(screen.getByText('Noch keinen Account?')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Registrieren' })).toHaveAttribute('href', '/register/');
  });
});
