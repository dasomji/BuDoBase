import { cleanup, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';

import { ProfilePage } from './people';

describe('Profil and Teamer pages', () => {
  afterEach(cleanup);

  it('retains profile values and active-Turnus selection', () => {
    render(<ProfilePage data={{
      csrf_token: 'token',
      profile: { rufname: 'Ada', allergies: 'Nüsse', coffee: 'Ja', role: 'b', food: 'vt', phone: '123' },
      turnus: { id: 2 },
      turnuses: [{ id: 2, label: 'T2' }],
    }} />);

    expect(screen.getByLabelText('Rufname')).toHaveValue('Ada');
    expect(screen.getByLabelText('Turnus')).toHaveValue('2');
    expect(screen.getByLabelText('Rufname').form).toHaveAttribute('action', '/profil/');
  });
});
