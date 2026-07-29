const { chromium } = require('../../../.artifacts/tools/node_modules/playwright');
const fs = require('fs');
const path = require('path');

const baseURL = process.env.BASE_URL || 'http://127.0.0.1:8018';
const outputDirectory = __dirname;
const username = fs.readFileSync('.artifacts/baseline/username.txt', 'utf8').trim();
const password = 'baseline-only-password';

const printRoutes = [
  ['hc-nummernliste', '/happy-cleaning/print/'],
  ['swp-einteilung-w1', '/swp-einteilung-w1'],
  ['kitchen', '/kitchen'],
];

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
  const storageState = await context.storageState();
  await context.close();
  return storageState;
}

async function capturePrintDocuments(browser, storageState) {
  const context = await browser.newContext({
    viewport: { width: 1280, height: 900 },
    storageState,
  });
  const page = await context.newPage();
  const results = {};

  for (const [slug, route] of printRoutes) {
    const response = await page.goto(`${baseURL}${route}`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(500);
    await page.evaluate(() => document.fonts.ready);
    await page.emulateMedia({ media: 'print' });

    const layout = await page.evaluate(currentSlug => {
      const bounds = selector => {
        const element = document.querySelector(selector);
        if (!element) return null;
        const rect = element.getBoundingClientRect();
        const style = getComputedStyle(element);
        return {
          display: style.display,
          left: rect.left,
          top: rect.top,
          width: rect.width,
          minWidth: style.minWidth,
          paddingInline: style.paddingInline,
        };
      };
      if (currentSlug === 'hc-nummernliste') {
        return {
          page: bounds('.happy-cleaning-print-page'),
          firstSection: bounds('.happy-cleaning-print-section'),
        };
      }
      if (currentSlug === 'swp-einteilung-w1') {
        return {
          page: bounds('.allocation-page'),
          printPage: bounds('.allocation-print-page'),
          heading: bounds('.allocation-print-page h1'),
        };
      }
      return {
        printPages: bounds('.kitchen-print-pages'),
        tableScroll: bounds('.kitchen-print-page .kitchen-meal-table-scroll'),
        table: bounds('.kitchen-print-page .meal-table'),
      };
    }, slug);

    await page.pdf({
      path: path.join(outputDirectory, `${slug}--print.pdf`),
      format: 'A4',
      printBackground: true,
    });
    results[slug] = {
      route,
      status: response?.status(),
      heading: await page.locator('h1, h2').first().textContent().catch(() => null),
      layout,
    };
    await page.emulateMedia({ media: 'screen' });
  }

  await context.close();
  return results;
}

async function verifyCascadeAndCard(browser, storageState) {
  const context = await browser.newContext({
    viewport: { width: 1280, height: 900 },
    storageState,
  });
  const page = await context.newPage();
  await page.goto(`${baseURL}/dashboard/`, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(500);

  const cardToggle = page.locator('.card .card-toggle').first();
  if (await cardToggle.getAttribute('aria-expanded') === 'true') {
    await cardToggle.click();
  }
  const collapsedBeforePrint = await cardToggle.getAttribute('aria-expanded');
  await page.emulateMedia({ media: 'print' });
  const card = await page.evaluate(() => {
    const container = document.querySelector('.card > .card-info-container');
    const style = getComputedStyle(container);
    return {
      collapsedBeforePrint: document.querySelector('.card .card-toggle')?.getAttribute('aria-expanded'),
      display: style.display,
      paddingInlineStart: style.paddingInlineStart,
      paddingInlineEnd: style.paddingInlineEnd,
      expectedPadding: getComputedStyle(document.documentElement).getPropertyValue('--str-padding').trim(),
    };
  });
  card.collapsedBeforePrint = collapsedBeforePrint;

  const cascade = await page.evaluate(async () => {
    const stylesheet = [...document.styleSheets].find(sheet => sheet.href?.endsWith('/static/frontend/app.css'));
    const matches = [];
    const walk = (rules, ancestors = []) => {
      for (const rule of rules) {
        const descriptor = `${rule.constructor.name}:${rule.name || rule.conditionText || ''}`;
        if (
          rule.constructor.name === 'CSSMediaRule'
          && rule.conditionText === 'print'
          && rule.cssText.includes('.allocation-page#body-container')
        ) {
          matches.push({ ancestors, descriptor });
        }
        if (rule.cssRules) walk(rule.cssRules, [...ancestors, descriptor]);
      }
    };
    walk(stylesheet.cssRules);
    return {
      stylesheet: stylesheet.href,
      globalPrintRules: matches,
    };
  });

  await context.close();
  return { card, cascade };
}

async function verifyTodoPortalReset(browser, storageState) {
  const context = await browser.newContext({
    viewport: { width: 1280, height: 900 },
    storageState,
  });
  const page = await context.newPage();
  await page.goto(`${baseURL}/happy-cleaning/`, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(500);
  await page.evaluate(() => {
    window.__issue118PrintViews = [];
    window.print = () => {
      window.__issue118PrintViews.push({
        overview: Boolean(document.querySelector('.happy-cleaning-overview-layout')),
        todoPrintPages: Boolean(document.querySelector('.happy-cleaning-todo-print-pages')),
      });
    };
  });

  await page.getByRole('button', { name: /To-Dos für Happy Cleaning .* drucken/ }).first().click();
  await page.waitForFunction(() => window.__issue118PrintViews.length === 1);
  const portalBeforeAfterPrint = await page.locator('.happy-cleaning-todo-print-pages').count();
  await page.evaluate(() => window.dispatchEvent(new Event('afterprint')));
  await page.locator('.happy-cleaning-todo-print-pages').waitFor({ state: 'detached' });
  await page.evaluate(() => window.print());

  const result = await page.evaluate(countBeforeAfterPrint => ({
    portalBeforeAfterPrint: countBeforeAfterPrint,
    portalAfterAfterPrint: document.querySelectorAll('.happy-cleaning-todo-print-pages').length,
    printViews: window.__issue118PrintViews,
  }), portalBeforeAfterPrint);
  await context.close();
  return result;
}

(async () => {
  const browser = await chromium.launch({
    executablePath: '/usr/bin/google-chrome',
    headless: true,
  });
  const storageState = await authenticate(browser);
  const report = {
    baseURL,
    printDocuments: await capturePrintDocuments(browser, storageState),
    browserContracts: await verifyCascadeAndCard(browser, storageState),
    todoPortal: await verifyTodoPortalReset(browser, storageState),
  };
  fs.writeFileSync(
    path.join(outputDirectory, 'browser-report.json'),
    `${JSON.stringify(report, null, 2)}\n`,
  );
  await browser.close();

  const cascadeRules = report.browserContracts.cascade.globalPrintRules;
  if (cascadeRules.length !== 1 || cascadeRules[0].ancestors.length !== 0) {
    throw new Error(`Expected one unlayered global print rule, got ${JSON.stringify(cascadeRules)}`);
  }
  const { card } = report.browserContracts;
  if (
    card.display !== 'block'
    || card.paddingInlineStart !== card.expectedPadding
    || card.paddingInlineEnd !== card.expectedPadding
  ) {
    throw new Error(`Collapsed Card print contract failed: ${JSON.stringify(card)}`);
  }
  const views = report.todoPortal.printViews;
  if (
    report.todoPortal.portalAfterAfterPrint !== 0
    || views.length !== 2
    || !views[0].todoPrintPages
    || views[1].todoPrintPages
    || !views[1].overview
  ) {
    throw new Error(`To-do portal reset failed: ${JSON.stringify(report.todoPortal)}`);
  }
})();
