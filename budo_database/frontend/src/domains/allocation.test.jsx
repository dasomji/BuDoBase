import { cleanup, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { AllocationPage } from './allocation';

describe('allocation page', () => {
  afterEach(cleanup);

  it('renders the selected week with its current assignments and choices', () => {
    render(<AllocationPage week="2" mutate={vi.fn()} data={{
      focuses: [{ id: 2, name: 'Wald', week: 'w2', kid_ids: [1] }],
      kids: [{ id: 1, full_name: 'Ada', present: true, focus_ids: [2], choices: [{ week: 'w2', first: 2, friends: 'Bea' }], age: 12, siblings: '' }],
    }} />);

    expect(screen.getByRole('heading', { name: 'Wald: 1' })).toBeInTheDocument();
    expect(screen.getByRole('option', { name: 'Wald' }).selected).toBe(true);
    expect(screen.getByRole('button', { name: '1' })).toHaveClass('active');
    expect(screen.getByText('Bea')).toBeInTheDocument();
  });
});
