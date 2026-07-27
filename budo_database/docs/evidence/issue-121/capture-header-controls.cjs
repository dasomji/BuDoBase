const { chromium } = require('../../../.artifacts/tools/node_modules/playwright');
const fs = require('fs');

const baseURL = process.env.BASE_URL || 'http://127.0.0.1:8021';
const outputDirectory = 'docs/evidence/issue-121';
const username = fs.readFileSync('.artifacts/baseline/username.txt', 'utf8').trim();
const password = 'baseline-only-password';

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

function assertControl(control) {
  assert(control.width === 32, `${control.name} width was ${control.width}px, expected 32px`);
  assert(control.height === 32, `${control.name} height was ${control.height}px, expected 32px`);
  assert(control.borderRadius >= 16, `${control.name} was not circular`);
  assert(control.glyphWidth === 16, `${control.name} glyph width was ${control.glyphWidth}px, expected 16px`);
  assert(control.glyphHeight === 16, `${control.name} glyph height was ${control.glyphHeight}px, expected 16px`);
}

async function authenticate(browser) {
  const context = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  const page = await context.newPage();

  await page.goto(`${baseURL}/login`, { waitUntil: 'domcontentloaded' });
  await page.locator('#root input[name="username"]').fill(username);
  await page.locator('#root input[name="password"]').fill(password);
  await Promise.all([
    page.waitForURL(url => !url.pathname.replace(/\/$/, '').endsWith('/login')),
    page.locator('#root input[type="submit"]').click(),
  ]);
  const state = await context.storageState();
  await context.close();
  return state;
}

let browser;

(async () => {
  browser = await chromium.launch({
    executablePath: '/usr/bin/google-chrome',
    headless: true,
  });
  const storageState = await authenticate(browser);
  const context = await browser.newContext({
    viewport: { width: 390, height: 844 },
    deviceScaleFactor: 1,
    isMobile: true,
    hasTouch: true,
    storageState,
  });
  const page = await context.newPage();

  const response = await page.goto(`${baseURL}/kitchen`, { waitUntil: 'networkidle' });
  assert(response?.status() === 200, `Küche returned HTTP ${response?.status()}`);
  await page.locator('#menu-button').waitFor();
  const toastClose = page.getByRole('button', { name: 'Benachrichtigung schließen' });
  if (await toastClose.count()) {
    await toastClose.click();
    await page.locator('.app-toast').waitFor({ state: 'hidden' });
  }
  await page.locator('.app-toast-viewport').evaluate(element => element.remove());

  const controls = await page.evaluate(() => {
    const inspect = (name, selector) => {
      const element = document.querySelector(selector);
      const glyph = element?.querySelector('svg');
      if (!element || !glyph) return { name, missing: true };
      const bounds = element.getBoundingClientRect();
      const glyphBounds = glyph.getBoundingClientRect();
      return {
        name,
        x: bounds.x,
        y: bounds.y,
        width: bounds.width,
        height: bounds.height,
        borderRadius: Number.parseFloat(getComputedStyle(element).borderRadius),
        glyphWidth: glyphBounds.width,
        glyphHeight: glyphBounds.height,
        ariaLabel: element.getAttribute('aria-label'),
      };
    };
    return [
      inspect('page action', '#headerbutton [aria-label="Drucken"]'),
      inspect('search toggle', '#search-button'),
      inspect('burger', '#menu-button'),
    ];
  });
  const headerBounds = await page.locator('#headermenu').evaluate(element => {
    const bounds = element.getBoundingClientRect();
    return {
      x: bounds.x,
      y: bounds.y,
      width: bounds.width,
      height: bounds.height,
      scrollY: window.scrollY,
    };
  });

  assert(page.viewportSize()?.width === 390, 'Browser viewport was not 390px wide');
  controls.forEach(assertControl);
  assert(
    new Set(controls.map(control => `${control.glyphWidth}x${control.glyphHeight}`)).size === 1,
    'Header glyph sizes were not uniform',
  );

  await page.locator('#headermenu').screenshot({
    path: `${outputDirectory}/kitchen-header-controls--390px.png`,
  });

  await page.evaluate(() => {
    window.print = () => {
      document.documentElement.dataset.printInvoked = 'true';
    };
  });
  await page.getByRole('button', { name: 'Drucken' }).click();
  const pageActionInvoked = await page.evaluate(() => document.documentElement.dataset.printInvoked === 'true');

  const search = page.getByRole('button', { name: 'Suche öffnen' });
  await search.click();
  const searchExpanded = await page.getByRole('button', { name: 'Suche schließen' })
    .getAttribute('aria-expanded') === 'true';

  await page.getByRole('button', { name: 'Sidebar ein- oder ausklappen' }).click();
  const sidebarOpened = await page.getByRole('dialog', { name: 'Sidebar' }).isVisible();

  assert(pageActionInvoked, 'Page action did not invoke print');
  assert(searchExpanded, 'Search toggle did not expand search');
  assert(sidebarOpened, 'Burger did not open the sidebar');

  fs.writeFileSync(
    `${outputDirectory}/browser-contracts.json`,
    `${JSON.stringify({
      route: '/kitchen',
      viewport: { width: 390, height: 844 },
      status: response.status(),
      headerBounds,
      controls,
      behavior: {
        pageActionInvoked,
        searchExpanded,
        sidebarOpened,
      },
    }, null, 2)}\n`,
  );

})().catch(error => {
  console.error(error);
  process.exitCode = 1;
}).finally(async () => {
  await browser?.close();
});
