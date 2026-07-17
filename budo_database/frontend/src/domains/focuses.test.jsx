import { cleanup, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';

import { FocusFormPage } from './focuses';

describe('Schwerpunkte pages', () => {
  afterEach(cleanup);

  it('retains the existing create form and target', () => {
    render(<FocusFormPage data={{ csrf_token: 'token', focuses: [], places: [], team: [], focus_times: [] }} />);

    expect(screen.getByRole('heading', { name: 'Schwerpunkt erstellen' })).toBeInTheDocument();
    expect(screen.getByLabelText('Schwerpunktname')).toBeRequired();
    expect(screen.getByLabelText('Schwerpunktname').form).toHaveAttribute('action', '/schwerpunkt/create');
  });
});
