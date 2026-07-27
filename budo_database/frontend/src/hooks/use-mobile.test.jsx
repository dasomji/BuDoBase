import { cleanup, render } from '@testing-library/react';
import { renderToStaticMarkup } from 'react-dom/server';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { useIsMobile } from './use-mobile';

function MobileProbe({ onRender }) {
  const mobile = useIsMobile();
  onRender?.(mobile);
  return <span>{mobile ? 'mobile' : 'desktop'}</span>;
}

describe('useIsMobile', () => {
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it('resolves a mobile match during the initial render', () => {
    window.matchMedia = vi.fn().mockReturnValue({
      matches: true,
      media: '(max-width: 900px)',
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    });

    expect(renderToStaticMarkup(<MobileProbe />)).toContain('mobile');
    expect(window.matchMedia).toHaveBeenCalledWith('(max-width: 900px)');
  });

  it('does not correct mobile mode after mounting', () => {
    const renderHistory = [];
    vi.spyOn(window, 'innerWidth', 'get').mockReturnValue(390);
    window.matchMedia = vi.fn().mockReturnValue({
      matches: true,
      media: '(max-width: 900px)',
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    });

    render(<MobileProbe onRender={mobile => renderHistory.push(mobile)} />);

    expect(renderHistory).toEqual([true]);
  });

  it('remains safe when rendered without a window', () => {
    vi.stubGlobal('window', undefined);

    expect(() => renderToStaticMarkup(<MobileProbe />)).not.toThrow();
    expect(renderToStaticMarkup(<MobileProbe />)).toContain('desktop');
  });
});
