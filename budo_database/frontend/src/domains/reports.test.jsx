import { cleanup, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';

import { KidCountPage } from './reports';

describe('operational report pages', () => {
  afterEach(cleanup);

  it('retains the standalone checked-in Kinder count', () => {
    render(<KidCountPage data={{ totals: { checked_in: 8, kids: 12 } }} />);

    expect(screen.getByRole('heading', { name: '8/12' })).toHaveClass('gesamtkinderzahl');
  });
});
