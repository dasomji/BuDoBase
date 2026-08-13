import { RouteIcon } from 'lucide-react';

import { Button } from './ui/button';

const directionsUrl = destination => `https://www.google.com/maps/dir/?api=1&destination=${encodeURIComponent(destination)}`;

export function DirectionsButton({ destination, label }) {
  return (
    <Button
      size="icon"
      variant="secondary"
      target="_blank"
      rel="noreferrer"
      href={directionsUrl(destination)}
      aria-label={label}
    >
      <RouteIcon aria-hidden="true" />
    </Button>
  );
}
