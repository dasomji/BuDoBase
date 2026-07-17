import { cleanup, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';

import { CheckPage } from './attendance';

describe('attendance pages', () => {
  afterEach(cleanup);

  it.each([
    { balance: 12.5, label: 'Taschengeld zurückgegeben (aktuell 12.50 €)', preset: 12.5 },
    { balance: -3, label: 'Taschengeld eingezahlt (schuldet aktuell: 3.00 €)', preset: 0 },
  ])('uses a positive checkout amount when the current balance is $balance', ({ balance, label, preset }) => {
    render(<CheckPage data={{ csrf_token: 'token', kids: [{ id: 7, full_name: 'Ada', pocket_money: balance }] }} id="7" checkout />);

    const amount = screen.getByRole('spinbutton', { name: label });
    expect(amount).toHaveValue(preset);
    expect(amount).toHaveAttribute('min', '0');
  });
});
