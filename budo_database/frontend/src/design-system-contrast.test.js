import { readFileSync, readdirSync } from 'node:fs';
import { resolve } from 'node:path';

import { describe, expect, it } from 'vitest';

const appCss = readFileSync(resolve('src/app.css'), 'utf8');
const buttonSource = readFileSync(
  resolve('src/components/ui/button.jsx'),
  'utf8',
);
const inputSource = readFileSync(
  resolve('src/components/ui/input.jsx'),
  'utf8',
);
const happyCleaningSource = readFileSync(
  resolve('src/domains/happyCleaning.jsx'),
  'utf8',
);
const guide = readFileSync(
  resolve('../docs/design-system.md'),
  'utf8',
);

function token(name) {
  const match = appCss.match(new RegExp(`--color-${name}:\\s*([^;]+);`));
  if (!match) throw new Error(`Missing --color-${name} token`);
  return parseColor(match[1]);
}

function parseColor(value) {
  const normalized = value.trim();
  if (normalized.startsWith('#')) {
    const hex = normalized.slice(1);
    const channels = hex.length === 3
      ? [...hex].map(channel => Number.parseInt(channel.repeat(2), 16))
      : [0, 2, 4].map(index => Number.parseInt(hex.slice(index, index + 2), 16));
    return { channels, alpha: 1 };
  }

  const match = normalized.match(
    /^rgb\(\s*(\d+)\s+(\d+)\s+(\d+)(?:\s*\/\s*([\d.]+)%?)?\s*\)$/,
  );
  if (!match) throw new Error(`Unsupported test color: ${value}`);
  const alphaValue = match[4] ?? '1';
  const alpha = normalized.includes('%')
    ? Number.parseFloat(alphaValue) / 100
    : Number.parseFloat(alphaValue);
  return {
    channels: match.slice(1, 4).map(Number),
    alpha,
  };
}

function composite(foreground, background) {
  const alpha = foreground.alpha;
  return {
    channels: foreground.channels.map(
      (channel, index) => channel * alpha + background.channels[index] * (1 - alpha),
    ),
    alpha: 1,
  };
}

function withOpacity(color, alpha) {
  return { ...color, alpha };
}

function relativeLuminance(color) {
  return color.channels
    .map(channel => {
      const value = channel / 255;
      return value <= 0.04045
        ? value / 12.92
        : ((value + 0.055) / 1.055) ** 2.4;
    })
    .reduce(
      (sum, value, index) => sum + value * [0.2126, 0.7152, 0.0722][index],
      0,
    );
}

function contrastRatio(first, second) {
  const firstLuminance = relativeLuminance(first);
  const secondLuminance = relativeLuminance(second);
  return (
    (Math.max(firstLuminance, secondLuminance) + 0.05)
    / (Math.min(firstLuminance, secondLuminance) + 0.05)
  );
}

function expectContrast(first, second, minimum) {
  expect(contrastRatio(first, second)).toBeGreaterThanOrEqual(minimum);
}

function expectMeasuredContrast(first, second, expected) {
  expectContrast(first, second, 3);
  expect(contrastRatio(first, second)).toBeCloseTo(expected, 2);
}

function cssBlock(source, marker) {
  const markerIndex = source.indexOf(marker);
  if (markerIndex === -1) throw new Error(`Missing CSS block: ${marker}`);

  const openingBrace = source.indexOf('{', markerIndex);
  let depth = 0;
  for (let index = openingBrace; index < source.length; index += 1) {
    if (source[index] === '{') depth += 1;
    if (source[index] === '}') depth -= 1;
    if (depth === 0) return source.slice(openingBrace + 1, index);
  }

  throw new Error(`Unclosed CSS block: ${marker}`);
}

function countTopLevelLayerBlocks(source, layerName) {
  let blockDepth = 0;
  let quote = null;
  let inComment = false;
  let count = 0;

  for (let index = 0; index < source.length; index += 1) {
    const character = source[index];
    const nextCharacter = source[index + 1];

    if (inComment) {
      if (character === '*' && nextCharacter === '/') {
        inComment = false;
        index += 1;
      }
      continue;
    }
    if (quote) {
      if (character === '\\') {
        index += 1;
      } else if (character === quote) {
        quote = null;
      }
      continue;
    }
    if (character === '/' && nextCharacter === '*') {
      inComment = true;
      index += 1;
      continue;
    }
    if (character === '"' || character === "'") {
      quote = character;
      continue;
    }

    if (
      blockDepth === 0
      && source.slice(index).match(
        new RegExp(`^@layer\\s+${layerName}\\s*\\{`),
      )
    ) {
      count += 1;
    }
    if (character === '{') blockDepth += 1;
    if (character === '}') blockDepth -= 1;
  }

  return count;
}

describe('design-system contrast contracts', () => {
  const page = token('background');
  const card = composite(token('card'), page);

  it('keeps semantic action labels at WCAG AA contrast, including opacity hover states', () => {
    const foreground = token('foreground');
    const success = token('success');
    const destructive = token('destructive');
    const destructiveForeground = token('destructive-foreground');

    expectContrast(token('success-foreground'), success, 4.5);
    expectContrast(destructiveForeground, destructive, 4.5);

    for (const surface of [page, card]) {
      expectContrast(foreground, composite(withOpacity(success, 0.9), surface), 4.5);
      expectContrast(
        destructiveForeground,
        composite(withOpacity(destructive, 0.9), surface),
        4.5,
      );
    }
  });

  it('keeps the shared link treatment readable on page and card surfaces', () => {
    const link = token('link');
    const linkCallSite = happyCleaningSource.match(
      /<Button(?=[\s\S]{0,300}variant="link")[\s\S]{0,300}>/,
    )?.[0];

    expectContrast(link, page, 4.5);
    expectContrast(link, card, 4.5);
    expect(buttonSource).toMatch(/link:\s*"text-link\b/);
    expect(linkCallSite).toBeDefined();
    expect(linkCallSite).not.toMatch(/\btext-inherit\b/);
  });

  it('keeps card-header and table-sort focus outlines distinct from adjacent colors', () => {
    const ring = token('ring');
    const headerOnPage = composite(token('surface-header'), page);
    const headerOnCard = composite(token('surface-header'), card);

    expectContrast(ring, page, 3);
    expectContrast(ring, headerOnPage, 3);
    expectContrast(ring, headerOnCard, 3);
    expect(appCss).toMatch(
      /\.info-header-container\.card-toggle:focus-visible\s*\{[^}]*outline:\s*2px solid var\(--color-ring\)/s,
    );
    expect(appCss).toMatch(
      /\.table-sort-button:focus-visible\s*\{[^}]*outline:\s*2px solid var\(--color-ring\)/s,
    );
  });

  it('keeps one shared Button focus treatment visible on every supported surface', () => {
    const ring = token('ring');
    const solidSurface = token('surface-solid');
    const header = token('surface-header');
    const headerOnPage = composite(header, page);
    const headerOnCard = composite(header, card);

    for (const surface of [page, card, solidSurface, headerOnPage, headerOnCard]) {
      expectContrast(ring, surface, 3);
    }

    const baseClasses = buttonSource
      .match(/cva\(\s*"([^"]*)"/)?.[1]
      .split(/\s+/);
    expect(baseClasses, 'Could not parse the shared Button base classes').toBeDefined();
    expect(baseClasses).toContain('focus-visible:ring-ring');
    expect(
      baseClasses.some(className => /^focus-visible:ring-ring\//.test(className)),
      'The shared Button focus ring must use the ring token at full opacity',
    ).toBe(false);

    const variantMapSource = buttonSource.match(
      /variants:\s*\{\s*variant:\s*\{([\s\S]*?)\n\s*\},\s*size:\s*\{/,
    )?.[1];
    expect(variantMapSource, 'Could not parse the Button variant map').toBeDefined();

    const variants = [...variantMapSource.matchAll(
      /(?:^|\n)\s*(?:"([^"]+)"|([\w-]+)):\s*"([^"]*)"/g,
    )].map(match => [match[1] ?? match[2], match[3]]);
    expect(variants.length, 'The parsed Button variant map was empty').toBeGreaterThan(0);

    for (const [variant, classes] of variants) {
      expect(
        classes,
        `Button variant "${variant}" declares focus-visible: classes; keep focus treatment in the shared base so tailwind-merge cannot drop it`,
      ).not.toContain('focus-visible:');
    }
  });

  it('keeps the input boundary distinct from its fill and every supported surface', () => {
    const boundary = token('input');
    const ring = token('ring');
    const fieldFill = token('popover');
    const pageSurface = composite(token('surface'), page);
    const solidSurface = token('surface-solid');
    const headerSurface = composite(token('surface-header'), page);
    const subtleSurface = composite(token('surface-subtle'), page);

    expect(boundary).toEqual(ring);
    expectMeasuredContrast(boundary, fieldFill, 5.57);
    expectMeasuredContrast(boundary, pageSurface, 5.01);
    expectMeasuredContrast(boundary, solidSurface, 4.78);
    expectMeasuredContrast(boundary, headerSurface, 3.38);
    expectMeasuredContrast(boundary, subtleSurface, 4.95);
  });

  it('keeps one full-opacity focus ring on every shared native control', () => {
    const sharedClasses = inputSource
      .match(/nativeControlClassName\s*=\s*"([^"]*)"/)?.[1]
      .split(/\s+/);

    expect(sharedClasses, 'Could not parse shared native control classes').toBeDefined();
    expect(sharedClasses).toContain('border');
    expect(sharedClasses).not.toContain('border-2');
    expect(sharedClasses).toContain('focus-visible:ring-ring');
    expect(
      sharedClasses.some(className => /^focus-visible:ring-ring\//.test(className)),
      'The shared native-control focus ring must use the ring token at full opacity',
    ).toBe(false);
  });

  it('keeps the shared control disabled fill separate from its boundary token', () => {
    const sharedClasses = inputSource
      .match(/nativeControlClassName\s*=\s*"([^"]*)"/)?.[1]
      .split(/\s+/);

    expect(sharedClasses).toContain('disabled:bg-muted');
    expect(sharedClasses.some(className => /^disabled:bg-input(?:\/|$)/.test(className))).toBe(false);
  });

  it('keeps the sidebar ring linked to the shared ring token', () => {
    expect(appCss).toMatch(/--sidebar-ring:\s*var\(--color-ring\);/);
  });

  it('keeps table surfaces opaque so readability does not depend on what is behind them', () => {
    // The page paints a white-to-#999999 radial gradient plus a fixed
    // illustration behind every table. A translucent row composites over
    // whatever it happens to sit on, so its contrast changes with scroll
    // position, and a sticky cell lets the columns underneath show through.
    const foreground = token('foreground');
    const link = token('link');

    for (const name of ['table-row', 'table-row-excused', 'table-header']) {
      const surface = token(name);
      expect(surface.alpha, `--color-${name} must be fully opaque`).toBe(1);
      expectContrast(foreground, surface, 4.5);
    }

    // Links render in body cells, and also on the header tint: the pinned
    // first column carries it, and that column is the kid-name link on All
    // Kids and on Schwerpunkt-Einteilung.
    for (const name of ['table-row', 'table-row-excused', 'table-header']) {
      expectContrast(link, token(name), 4.5);
    }

    // Row tints must stay distinguishable from one another, or the excused
    // state silently stops reading as a state at all.
    expect(
      contrastRatio(token('table-row'), token('table-row-excused')),
    ).toBeGreaterThan(1.1);

    expect(appCss).toMatch(
      /\[data-slot="table-row"\]\s*\{[^}]*--table-row-background:\s*var\(--color-table-row\)/s,
    );
  });

  it('keeps the documented token table synchronized with the source values', () => {
    for (const [name, exactValue] of [
      ['link', '#373737'],
      ['success', '#54b958'],
      ['destructive', '#b93f3b'],
      ['input', '#686868'],
      ['ring', '#686868'],
    ]) {
      expect(guide).toContain(`| \`${name}\` | \`${exactValue}\``);
    }
  });
});

describe('native form control ownership', () => {
  const domainSources = readdirSync(resolve('src/domains'), { withFileTypes: true })
    .filter(entry => entry.isFile() && entry.name.endsWith('.jsx'))
    .map(entry => ({
      fileName: entry.name,
      source: readFileSync(resolve('src/domains', entry.name), 'utf8'),
    }));

  function isStylesheetOwnedClassName(className) {
    if (className.trim().split(/\s+/).length !== 1) return false;
    return appCss.includes(`.${className} {`);
  }

  function isVisuallyHiddenPlaceCommentAttachmentInput(control) {
    return control.fileName === 'places.jsx'
      && control.element === 'input'
      && control.className === 'absolute size-px overflow-hidden [clip-path:inset(50%)]';
  }

  it('keeps page utility strings out of raw text-like controls', () => {
    const controls = domainSources.flatMap(({ fileName, source }) => (
      [...source.matchAll(/<(input|textarea|select)\b[^<>]*?\bclassName="([^"]+)"/g)]
        .map(match => ({
          fileName,
          element: match[1],
          className: match[2],
        }))
    ));
    const attachmentExceptions = controls.filter(
      isVisuallyHiddenPlaceCommentAttachmentInput,
    );
    const utilityOwnedControls = controls.filter(control => (
      !isStylesheetOwnedClassName(control.className)
      && !isVisuallyHiddenPlaceCommentAttachmentInput(control)
    ));

    expect(attachmentExceptions).toEqual([]);
    expect(utilityOwnedControls).toEqual([]);
  });
});

describe('stylesheet structure contracts', () => {
  it('declares the components layer in exactly one top-level block', () => {
    expect(countTopLevelLayerBlocks(appCss, 'components')).toBe(1);
  });
});

describe('print stylesheet contracts', () => {
  it('keeps transparent-card inline padding after the general card print rule', () => {
    const printCss = cssBlock(appCss, '@media print');
    const generalRule = printCss.match(
      /\.card > \.card-info-container\s*\{[^}]*padding-inline:\s*var\(--str-padding\);[^}]*\}/s,
    );
    const transparentRule = printCss.match(
      /\.card\.transparent > \.card-info-container\s*\{[^}]*padding-inline:\s*0;[^}]*\}/s,
    );

    expect(generalRule, 'Missing the general card print rule').not.toBeNull();
    expect(transparentRule, 'Missing the transparent-card print override').not.toBeNull();
    expect(transparentRule.index).toBeGreaterThan(generalRule.index);
    expect(
      printCss.slice(
        generalRule.index + generalRule[0].length,
        transparentRule.index,
      ).trim(),
      'Keep the transparent-card override immediately after the general rule',
    ).toBe('');
  });
});
