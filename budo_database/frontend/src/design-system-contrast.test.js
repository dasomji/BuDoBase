import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

import { describe, expect, it } from 'vitest';

const appCss = readFileSync(resolve('src/app.css'), 'utf8');
const buttonSource = readFileSync(
  resolve('src/components/ui/button.jsx'),
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

  it('keeps the documented token table synchronized with the source values', () => {
    for (const [name, exactValue] of [
      ['link', '#725500'],
      ['success', '#54b958'],
      ['destructive', '#b93f3b'],
      ['ring', '#686868'],
    ]) {
      expect(guide).toContain(`| \`${name}\` | \`${exactValue}\``);
    }
  });
});
