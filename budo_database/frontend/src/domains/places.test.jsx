import { cleanup, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';

import { ImageUploadPage } from './places';

describe('Auslagerorte image uploads', () => {
  afterEach(cleanup);

  it('requires multiple images and hints accepted file types', () => {
    render(<ImageUploadPage data={{
      csrf_token: 'token',
      places: [{ id: 4, name: 'Test place' }],
    }} id="4" />);

    const input = screen.getByLabelText('Select multiple images');
    expect(input).toHaveAttribute('type', 'file');
    expect(input).toBeRequired();
    expect(input).toHaveAttribute('multiple');
    expect(input).toHaveAttribute('accept', 'image/*');
  });
});
