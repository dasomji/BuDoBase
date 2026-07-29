const { chromium } = require('../../../.artifacts/tools/node_modules/playwright');
const fs = require('fs');

const baseURL = process.env.BASE_URL || 'http://127.0.0.1:8016';
const outputDirectory = 'docs/evidence/issue-97';
const username = fs.readFileSync('.artifacts/baseline/username.txt', 'utf8').trim();
const password = 'baseline-only-password';

async function authenticate(browser) {
  const context = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  const page = await context.newPage();
  await page.goto(`${baseURL}/login`);
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

async function openFirstStation(page) {
  console.log('opening overview');
  await page.goto(`${baseURL}/happy-cleaning/`, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(800);
  console.log('overview loaded');
  const station = page.locator('button[aria-label^="Station "][aria-label$=" öffnen"]').first();
  const eventToggle = page.locator('article .card-toggle').first();
  if (await eventToggle.getAttribute('aria-expanded') === 'false') {
    console.log('expanding event');
    await eventToggle.evaluate(element => element.click());
    await page.waitForFunction(
      element => element.getAttribute('aria-expanded') === 'true',
      await eventToggle.elementHandle(),
    );
  }
  console.log('opening station');
  await Promise.all([
    page.waitForResponse(response => response.url().includes('happy-cleaning-overview-station')),
    station.evaluate(element => element.click()),
  ]);
  console.log('station loaded');
  const detailToggle = page.locator('.happy-cleaning-station-detail-card .card-toggle');
  console.log(`detail initially ${await detailToggle.getAttribute('aria-expanded')}`);
  if (await detailToggle.getAttribute('aria-expanded') === 'false') {
    await detailToggle.evaluate(element => element.click());
  }
  await page.waitForTimeout(500);
  console.log(`detail after click ${await detailToggle.getAttribute('aria-expanded')}`);
  await page.locator('h2', { hasText: 'Aufgaben' }).waitFor({ state: 'attached' });
  console.log('detail expanded');
}

async function capture(browser, storageState, viewport, mobile) {
  console.log(`capturing ${mobile ? 'mobile' : 'desktop'}`);
  const context = await browser.newContext({
    viewport,
    deviceScaleFactor: 1,
    isMobile: mobile,
    hasTouch: mobile,
    storageState,
  });
  const page = await context.newPage();
  await openFirstStation(page);
  await page.screenshot({
    path: `${outputDirectory}/hc-station-detail--${mobile ? 'mobile' : 'desktop'}.png`,
    fullPage: !mobile,
  });
  console.log('read screenshot captured');

  const readMode = await page.evaluate(() => {
    const detail = document.querySelector('.happy-cleaning-overview-detail');
    const tableScroll = document.querySelector('[data-slot="table-scroll"]');
    const header = document.querySelector('#headermenu');
    const close = document.querySelector('[aria-label="Detail schließen"]');
    const yearIndicator = document.querySelector('.transparent .icon');
    return {
      viewportWidth: window.innerWidth,
      documentWidth: document.documentElement.scrollWidth,
      detailTop: detail?.getBoundingClientRect().top ?? null,
      headerBottom: header?.getBoundingClientRect().bottom ?? null,
      tableClientWidth: tableScroll?.clientWidth ?? null,
      tableScrollWidth: tableScroll?.scrollWidth ?? null,
      closeButtonSlot: close?.getAttribute('data-slot') ?? null,
      yearIndicator: yearIndicator?.textContent ?? null,
    };
  });

  const edit = page.getByRole('button', { name: 'Bearbeiten' });
  if (await edit.count()) {
    await edit.click();
    await page.getByLabel('Name der Station').waitFor();
    await page.screenshot({
      path: `${outputDirectory}/hc-station-editor--${mobile ? 'mobile' : 'desktop'}.png`,
      fullPage: !mobile,
    });
    console.log('editor screenshot captured');
  }
  const editorMode = await page.evaluate(() => ({
    viewportWidth: window.innerWidth,
    documentWidth: document.documentElement.scrollWidth,
    saveButtonSlot: document.querySelector('button[type="submit"]')?.getAttribute('data-slot') ?? null,
  }));
  await context.close();
  return { readMode, editorMode };
}

async function capturePrintContract(browser, storageState) {
  const context = await browser.newContext({
    viewport: { width: 1280, height: 900 },
    storageState,
  });
  const page = await context.newPage();
  await page.goto(`${baseURL}/happy-cleaning/print/`, { waitUntil: 'domcontentloaded' });
  await page.emulateMedia({ media: 'print' });
  await page.waitForTimeout(500);
  const contract = await page.evaluate(() => {
    const inspect = selector => {
      const element = document.querySelector(selector);
      const style = getComputedStyle(element);
      const bounds = element.getBoundingClientRect();
      return {
        top: bounds.top,
        bottom: bounds.bottom,
        height: bounds.height,
        fontSize: style.fontSize,
        fontWeight: style.fontWeight,
        marginBottom: style.marginBottom,
        paddingTop: style.paddingTop,
        paddingBottom: style.paddingBottom,
      };
    };
    const main = document.querySelector('.happy-cleaning-print-page');
    const table = document.querySelector('.happy-cleaning-print-table');
    const cell = table?.querySelector('th, td');
    return {
      viewportWidth: window.innerWidth,
      documentWidth: document.documentElement.scrollWidth,
      smallPaddingToken: getComputedStyle(document.documentElement).getPropertyValue('--s-padding'),
      title: inspect('.happy-cleaning-print-title'),
      heading: inspect('.happy-cleaning-print-title h1'),
      sectionHeading: inspect('.happy-cleaning-print-section h2'),
      empty: inspect('.happy-cleaning-print-empty'),
      mainBackgroundImage: getComputedStyle(main).backgroundImage,
      tableFontSize: getComputedStyle(table).fontSize,
      tableCellPadding: cell
        ? `${getComputedStyle(cell).paddingBlock} ${getComputedStyle(cell).paddingInline}`
        : null,
    };
  });
  await context.close();
  return contract;
}

(async () => {
  const browser = await chromium.launch({
    executablePath: '/usr/bin/google-chrome',
    headless: true,
  });
  const storageState = await authenticate(browser);
  const requestedViewport = process.env.CAPTURE_VIEWPORT;
  const existingPath = `${outputDirectory}/browser-contracts.json`;
  const results = fs.existsSync(existingPath)
    ? JSON.parse(fs.readFileSync(existingPath, 'utf8'))
    : {};
  if (!requestedViewport || requestedViewport === 'desktop') {
    results.desktop = await capture(browser, storageState, { width: 1280, height: 900 }, false);
  }
  if (!requestedViewport || requestedViewport === 'mobile') {
    results.mobile = await capture(browser, storageState, { width: 390, height: 844 }, true);
  }
  if (requestedViewport === 'print') {
    results.print = await capturePrintContract(browser, storageState);
  }
  fs.writeFileSync(
    existingPath,
    JSON.stringify(results, null, 2),
  );
  await browser.close();
})();
