import { render, screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { FirstAidEntry } from './first-aid';


describe('first-aid correction boundary', () => {
  it('keeps normal React EH entries read-only even if edit/delete hints appear in data', () => {
    render(
      <ul>
        <FirstAidEntry
          childName="Ada Lovelace"
          entry={{
            id: 9,
            author: 'Boris',
            date: '2026-07-03T10:00:00Z',
            text: 'Knie verbunden',
            can_edit: true,
            can_delete: true,
            edit_url: '/admin/budo_app/erstehilfeeintrag/9/change/',
            delete_url: '/admin/budo_app/erstehilfeeintrag/9/delete/',
            photos: [],
          }}
        />
      </ul>,
    );

    const entry = screen.getByRole('listitem');
    expect(entry).not.toBeNull();
    expect(within(entry).queryByRole('button', { name: /bearbeiten|löschen/i })).not.toBeInTheDocument();
    expect(within(entry).queryByRole('link', { name: /bearbeiten|löschen/i })).not.toBeInTheDocument();
    expect(entry).not.toHaveTextContent(/bearbeiten|löschen/i);
  });
});
