import { MapPinIcon } from 'lucide-react';

const loaders = {
  'tent-tree': () => import('lucide-react/dist/esm/icons/tent-tree.mjs'),
  'house': () => import('lucide-react/dist/esm/icons/house.mjs'),
  'warehouse': () => import('lucide-react/dist/esm/icons/warehouse.mjs'),
  'trees': () => import('lucide-react/dist/esm/icons/trees.mjs'),
  'mountain': () => import('lucide-react/dist/esm/icons/mountain.mjs'),
  'waves': () => import('lucide-react/dist/esm/icons/waves.mjs'),
  'castle': () => import('lucide-react/dist/esm/icons/castle.mjs'),
  'utensils': () => import('lucide-react/dist/esm/icons/utensils.mjs'),
  'bed': () => import('lucide-react/dist/esm/icons/bed.mjs'),
  'bus': () => import('lucide-react/dist/esm/icons/bus.mjs'),
  'accessibility': () => import('lucide-react/dist/esm/icons/accessibility.mjs'),
  'building-2': () => import('lucide-react/dist/esm/icons/building-2.mjs'),
  'school': () => import('lucide-react/dist/esm/icons/school.mjs'),
  'church': () => import('lucide-react/dist/esm/icons/church.mjs'),
  'landmark': () => import('lucide-react/dist/esm/icons/landmark.mjs'),
  'factory': () => import('lucide-react/dist/esm/icons/factory.mjs'),
  'store': () => import('lucide-react/dist/esm/icons/store.mjs'),
  'shopping-cart': () => import('lucide-react/dist/esm/icons/shopping-cart.mjs'),
  'hospital': () => import('lucide-react/dist/esm/icons/hospital.mjs'),
  'cross': () => import('lucide-react/dist/esm/icons/cross.mjs'),
  'stethoscope': () => import('lucide-react/dist/esm/icons/stethoscope.mjs'),
  'heart-pulse': () => import('lucide-react/dist/esm/icons/heart-pulse.mjs'),
  'shield-plus': () => import('lucide-react/dist/esm/icons/shield-plus.mjs'),
  'toilet': () => import('lucide-react/dist/esm/icons/toilet.mjs'),
  'shower-head': () => import('lucide-react/dist/esm/icons/shower-head.mjs'),
  'bath': () => import('lucide-react/dist/esm/icons/bath.mjs'),
  'washing-machine': () => import('lucide-react/dist/esm/icons/washing-machine.mjs'),
  'cooking-pot': () => import('lucide-react/dist/esm/icons/cooking-pot.mjs'),
  'coffee': () => import('lucide-react/dist/esm/icons/coffee.mjs'),
  'cup-soda': () => import('lucide-react/dist/esm/icons/cup-soda.mjs'),
  'ice-cream-bowl': () => import('lucide-react/dist/esm/icons/ice-cream-bowl.mjs'),
  'sandwich': () => import('lucide-react/dist/esm/icons/sandwich.mjs'),
  'pizza': () => import('lucide-react/dist/esm/icons/pizza.mjs'),
  'apple': () => import('lucide-react/dist/esm/icons/apple.mjs'),
  'car': () => import('lucide-react/dist/esm/icons/car.mjs'),
  'train-front': () => import('lucide-react/dist/esm/icons/train-front.mjs'),
  'bike': () => import('lucide-react/dist/esm/icons/bike.mjs'),
  'ship': () => import('lucide-react/dist/esm/icons/ship.mjs'),
  'plane': () => import('lucide-react/dist/esm/icons/plane.mjs'),
  'circle-parking': () => import('lucide-react/dist/esm/icons/circle-parking.mjs'),
  'route': () => import('lucide-react/dist/esm/icons/route.mjs'),
  'signpost': () => import('lucide-react/dist/esm/icons/signpost.mjs'),
  'traffic-cone': () => import('lucide-react/dist/esm/icons/traffic-cone.mjs'),
  'tree-pine': () => import('lucide-react/dist/esm/icons/tree-pine.mjs'),
  'flower-2': () => import('lucide-react/dist/esm/icons/flower-2.mjs'),
  'leaf': () => import('lucide-react/dist/esm/icons/leaf.mjs'),
  'sprout': () => import('lucide-react/dist/esm/icons/sprout.mjs'),
  'sun': () => import('lucide-react/dist/esm/icons/sun.mjs'),
  'cloud-sun': () => import('lucide-react/dist/esm/icons/cloud-sun.mjs'),
  'cloud-rain': () => import('lucide-react/dist/esm/icons/cloud-rain.mjs'),
  'snowflake': () => import('lucide-react/dist/esm/icons/snowflake.mjs'),
  'wind': () => import('lucide-react/dist/esm/icons/wind.mjs'),
  'footprints': () => import('lucide-react/dist/esm/icons/footprints.mjs'),
  'dumbbell': () => import('lucide-react/dist/esm/icons/dumbbell.mjs'),
  'goal': () => import('lucide-react/dist/esm/icons/goal.mjs'),
  'trophy': () => import('lucide-react/dist/esm/icons/trophy.mjs'),
  'medal': () => import('lucide-react/dist/esm/icons/medal.mjs'),
  'gamepad-2': () => import('lucide-react/dist/esm/icons/gamepad-2.mjs'),
  'puzzle': () => import('lucide-react/dist/esm/icons/puzzle.mjs'),
  'dice-5': () => import('lucide-react/dist/esm/icons/dice-5.mjs'),
  'music': () => import('lucide-react/dist/esm/icons/music.mjs'),
  'guitar': () => import('lucide-react/dist/esm/icons/guitar.mjs'),
  'drama': () => import('lucide-react/dist/esm/icons/drama.mjs'),
  'palette': () => import('lucide-react/dist/esm/icons/palette.mjs'),
  'paintbrush': () => import('lucide-react/dist/esm/icons/paintbrush.mjs'),
  'book-open': () => import('lucide-react/dist/esm/icons/book-open.mjs'),
  'library': () => import('lucide-react/dist/esm/icons/library.mjs'),
  'binoculars': () => import('lucide-react/dist/esm/icons/binoculars.mjs'),
  'camera': () => import('lucide-react/dist/esm/icons/camera.mjs'),
  'circle-help': () => import('lucide-react/dist/esm/icons/circle-help.mjs'),
  'info': () => import('lucide-react/dist/esm/icons/info.mjs'),
  'badge-alert': () => import('lucide-react/dist/esm/icons/badge-alert.mjs'),
  'triangle-alert': () => import('lucide-react/dist/esm/icons/triangle-alert.mjs'),
  'shield': () => import('lucide-react/dist/esm/icons/shield.mjs'),
  'lock-keyhole': () => import('lucide-react/dist/esm/icons/lock-keyhole.mjs'),
  'key-round': () => import('lucide-react/dist/esm/icons/key-round.mjs'),
  'flashlight': () => import('lucide-react/dist/esm/icons/flashlight.mjs'),
  'radio': () => import('lucide-react/dist/esm/icons/radio.mjs'),
  'wifi': () => import('lucide-react/dist/esm/icons/wifi.mjs'),
  'phone': () => import('lucide-react/dist/esm/icons/phone.mjs'),
  'battery-charging': () => import('lucide-react/dist/esm/icons/battery-charging.mjs'),
  'clock': () => import('lucide-react/dist/esm/icons/clock.mjs'),
  'calendar-days': () => import('lucide-react/dist/esm/icons/calendar-days.mjs'),
  'sunrise': () => import('lucide-react/dist/esm/icons/sunrise.mjs'),
  'sunset': () => import('lucide-react/dist/esm/icons/sunset.mjs'),
  'moon': () => import('lucide-react/dist/esm/icons/moon.mjs'),
  'star': () => import('lucide-react/dist/esm/icons/star.mjs'),
  'heart': () => import('lucide-react/dist/esm/icons/heart.mjs'),
  'users': () => import('lucide-react/dist/esm/icons/users.mjs'),
  'dog': () => import('lucide-react/dist/esm/icons/dog.mjs'),
  'bird': () => import('lucide-react/dist/esm/icons/bird.mjs'),
  'fish': () => import('lucide-react/dist/esm/icons/fish.mjs'),
  'anchor': () => import('lucide-react/dist/esm/icons/anchor.mjs'),
  'fence': () => import('lucide-react/dist/esm/icons/fence.mjs'),
  'flame-kindling': () => import('lucide-react/dist/esm/icons/flame-kindling.mjs'),
  'person-standing': () => import('lucide-react/dist/esm/icons/person-standing.mjs'),
  'activity': () => import('lucide-react/dist/esm/icons/activity.mjs'),
  'paw-print': () => import('lucide-react/dist/esm/icons/paw-print.mjs'),
  'navigation': () => import('lucide-react/dist/esm/icons/navigation.mjs'),
};

const componentCache = new Map([['map-pin', MapPinIcon]]);

export function loadTagIcon(name) {
  const key = loaders[name] ? name : 'map-pin';
  const cached = componentCache.get(key);
  if (cached) return Promise.resolve(cached);
  return loaders[key]().then(module => {
    componentCache.set(key, module.default);
    return module.default;
  });
}

export async function loadTagIcons(names) {
  const uniqueNames = [...new Set(names)];
  const components = await Promise.all(uniqueNames.map(loadTagIcon));
  return Object.fromEntries(uniqueNames.map((name, index) => [name, components[index]]));
}

export function fallbackTagIcon() {
  return MapPinIcon;
}
