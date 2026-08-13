import { useEffect, useState } from 'react';

import { fallbackTagIcon, loadTagIcon } from './tag-icon-loader';

export function TagIcon({ name, ...props }) {
  const [Icon, setIcon] = useState(() => fallbackTagIcon());

  useEffect(() => {
    let active = true;
    loadTagIcon(name).then(component => {
      if (active) setIcon(() => component);
    });
    return () => { active = false; };
  }, [name]);

  return <Icon {...props} />;
}

export function tagIconForName(catalog, tagName) {
  return catalog?.find(tag => tag.name === tagName)?.icon || 'map-pin';
}
