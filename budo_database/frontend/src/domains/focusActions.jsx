import { PlusIcon } from 'lucide-react';

import { Button } from '../components/ui/button';

export function FocusCreateAction({ week }) {
  const origin = week === '2' ? 'w2' : 'w1';
  return (
    <Button
      className="mobile-icon-action"
      size="responsive-icon"
      href={`/schwerpunkt/create?from=${origin}`}
      aria-label="SWP hinzufügen"
    >
      <span className="desktop-action-label">SWP hinzufügen</span>
      <PlusIcon className="mobile-action-label" aria-hidden="true" />
    </Button>
  );
}
