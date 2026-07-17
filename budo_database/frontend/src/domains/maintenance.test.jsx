import { cleanup, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';

import { SimpleUploadPage, TurnusUploadPage } from './maintenance';

describe('maintenance upload pages', () => {
  afterEach(cleanup);

  it('retains multipart workbook inputs for both maintenance workflows', () => {
    const { unmount } = render(<TurnusUploadPage data={{ csrf_token: 'token', turnuses: [] }} />);
    expect(screen.getByLabelText('Excel-File').form).toHaveAttribute('enctype', 'multipart/form-data');
    unmount();

    render(<SimpleUploadPage data={{ csrf_token: 'token' }} />);
    expect(screen.getByLabelText('Datei')).toBeRequired();
    expect(screen.getByLabelText('Datei').form).toHaveAttribute('action', '/upload_spezialfamilien/');
  });
});
