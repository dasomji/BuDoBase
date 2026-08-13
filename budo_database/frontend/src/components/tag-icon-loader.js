import { MapPinIcon } from 'lucide-react';

import { settingsTagIcons } from './tag-icon-picker';

export function loadTagIcon(name) {
  return Promise.resolve(settingsTagIcons[name] || MapPinIcon);
}

export async function loadTagIcons(names) {
  const uniqueNames = [...new Set(names)];
  const components = await Promise.all(uniqueNames.map(loadTagIcon));
  return Object.fromEntries(uniqueNames.map((name, index) => [name, components[index]]));
}

export function fallbackTagIcon() {
  return MapPinIcon;
}
