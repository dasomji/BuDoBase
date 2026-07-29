import { screen, within } from '@testing-library/react';
import { expect } from 'vitest';

const isToastLiveAnnouncement = element => {
  const alert = element.closest('[role="alert"][aria-atomic="true"]');
  return alert?.parentElement?.style.clipPath === 'inset(50%)';
};

const isDuplicateNumberRecoveryTitle = element => (
  element.closest('[role="dialog"]')
  && element.matches('h1, h2, h3, h4, h5, h6, [role="heading"]')
  && /^Nummer \d+ ist bereits vergeben\.$/.test(element.textContent.trim())
);

export async function expectErrorToastOnly(expectedMessage) {
  const notifications = screen.getByRole('region', { name: 'Benachrichtigungen' });
  const message = await within(notifications).findByText(expectedMessage);
  const toast = message.closest('[data-type][role]');

  expect(toast).toHaveAttribute('data-type', 'error');

  const inlineMatches = within(document.body)
    .queryAllByText(expectedMessage)
    .filter(element => (
      !notifications.contains(element)
      && !isToastLiveAnnouncement(element)
      && !isDuplicateNumberRecoveryTitle(element)
    ));
  expect(inlineMatches).toHaveLength(0);
}
