import { cleanup, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';

import { AuthPage } from './auth';

describe('authentication pages', () => {
  afterEach(cleanup);

  it('keeps login public and posts to the existing login URL', () => {
    render(<AuthPage kind="login" data={{ csrf_token: 'token' }} />);

    expect(screen.getByRole('heading', { name: 'Login' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Login' }).form).toHaveAttribute('action', '/login/');
  });
});
