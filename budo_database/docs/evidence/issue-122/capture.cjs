const { chromium } = require('../../../.artifacts/tools/node_modules/playwright');
const fs = require('fs');
const path = require('path');

const baseURL = process.env.BASE_URL || 'http://127.0.0.1:8012';
const username = fs.readFileSync('.artifacts/baseline/username.txt', 'utf8').trim();
const password = 'baseline-only-password';
const evidenceDir = path.resolve('docs/evidence/issue-122');
const screenshotPath = path.join(evidenceDir, 'swp-einteilung-w1--390-after-scroll.png');
const runtimeIssues = [];

function watchRuntime(page, viewport) {
  page.on('pageerror', error => runtimeIssues.push({
    viewport,
    type: 'pageerror',
    message: error.message,
  }));
  page.on('console', message => {
    if (message.type() === 'error') {
      runtimeIssues.push({ viewport, type: 'console', message: message.text() });
    }
  });
  page.on('response', response => {
    if (response.status() >= 400) {
      runtimeIssues.push({
        viewport,
        type: 'response',
        message: `${response.status()} ${response.url()}`,
      });
    }
  });
}

async function layout(page) {
  return page.evaluate(() => {
    const header = document.querySelector('#headermenu');
    const controls = document.querySelector('[data-slot="table-sticky-controls"]');
    const tableScroll = document.querySelector('[data-slot="table-scroll"][data-vertical-scroll]');
    const headerRect = header.getBoundingClientRect();
    const controlsRect = controls.getBoundingClientRect();
    const controlsStyle = getComputedStyle(controls);

    return {
      viewport: { width: innerWidth, height: innerHeight },
      headerBottom: headerRect.bottom,
      headerContract: getComputedStyle(document.documentElement)
        .getPropertyValue('--app-header-height')
        .trim(),
      controlsTop: controlsRect.top,
      controlsBottom: controlsRect.bottom,
      controlsPosition: controlsStyle.position,
      controlsTopProperty: controlsStyle.top,
      controlsZIndex: controlsStyle.zIndex,
      tableScrollTop: tableScroll.scrollTop,
      tableClientHeight: tableScroll.clientHeight,
      tableScrollHeight: tableScroll.scrollHeight,
      windowScrollY: scrollY,
      documentScrollHeight: document.documentElement.scrollHeight,
    };
  });
}

(async () => {
  fs.mkdirSync(evidenceDir, { recursive: true });
  const browser = await chromium.launch({
    executablePath: '/usr/bin/google-chrome',
    headless: true,
  });
  const loginContext = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  const loginPage = await loginContext.newPage();

  await loginPage.goto(`${baseURL}/login`, { waitUntil: 'domcontentloaded' });
  await loginPage.locator('#root input[name="username"]').fill(username);
  await loginPage.locator('#root input[name="password"]').fill(password);
  await Promise.all([
    loginPage.waitForURL(url => !url.pathname.replace(/\/$/, '').endsWith('/login')),
    loginPage.locator('#root input[type="submit"]').click(),
  ]);
  const storageState = await loginContext.storageState();

  const mobileContext = await browser.newContext({
    viewport: { width: 390, height: 844 },
    deviceScaleFactor: 1,
    isMobile: true,
    hasTouch: true,
    storageState,
  });
  const mobilePage = await mobileContext.newPage();
  watchRuntime(mobilePage, '390x844');
  await mobilePage.goto(`${baseURL}/swp-einteilung-w1`, { waitUntil: 'networkidle' });
  await mobilePage.getByRole('searchbox', { name: 'Kinder filtern' }).waitFor();
  const closeToast = mobilePage.getByRole('button', { name: 'Benachrichtigung schließen' });
  await closeToast.waitFor({ state: 'visible', timeout: 2000 }).catch(() => {});
  if (await closeToast.isVisible()) {
    await closeToast.click();
    await mobilePage.locator('.app-toast').waitFor({ state: 'hidden' });
  }
  // Keep the login-success notification from obscuring the measured header in
  // this layout-only artifact.
  await mobilePage.locator('.app-toast-viewport').evaluate(element => element.remove());
  const mobileBefore = await layout(mobilePage);

  await mobilePage.evaluate(() => {
    const tableScroll = document.querySelector('[data-slot="table-scroll"][data-vertical-scroll]');
    tableScroll.scrollTop = tableScroll.scrollHeight - tableScroll.clientHeight;
    window.scrollTo(0, document.documentElement.scrollHeight);
  });
  await mobilePage.waitForTimeout(200);
  const mobileAfter = await layout(mobilePage);
  await mobilePage.screenshot({ path: screenshotPath });

  const desktopContext = await browser.newContext({
    viewport: { width: 1280, height: 900 },
    storageState,
  });
  const desktopPage = await desktopContext.newPage();
  watchRuntime(desktopPage, '1280x900');
  await desktopPage.goto(`${baseURL}/swp-einteilung-w1`, { waitUntil: 'networkidle' });
  await desktopPage.getByRole('searchbox', { name: 'Kinder filtern' }).waitFor();
  const desktop = await layout(desktopPage);

  console.log(JSON.stringify({
    route: '/swp-einteilung-w1',
    screenshot: path.relative(process.cwd(), screenshotPath),
    mobileBefore,
    mobileAfter,
    mobilePinnedBelowHeader: Math.abs(mobileAfter.controlsTop - mobileAfter.headerBottom) <= 1,
    tableActuallyScrolled: mobileAfter.tableScrollTop > mobileBefore.tableScrollTop,
    desktop,
    runtimeIssues,
  }, null, 2));

  await browser.close();
})();
