import { cleanup, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';

import { KitchenPage } from './kitchen';

describe('Küche page', () => {
  afterEach(cleanup);

  it('retains both weekly meal-plan and Schwerpunkt sections', () => {
    render(<KitchenPage data={{ focuses: [], kids: [], team: [] }} />);

    expect(screen.getByRole('heading', { name: 'Menüplan Woche 1' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Menüplan Woche 2' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Schwerpunktinfos Woche 1' })).toBeInTheDocument();
  });
});
