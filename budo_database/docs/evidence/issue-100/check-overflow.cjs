const { chromium } = require('../../../.artifacts/tools/node_modules/playwright');
const fs = require('fs');

const baseURL = process.env.BASE_URL || 'http://127.0.0.1:8019';
const username = fs.readFileSync('.artifacts/baseline/username.txt', 'utf8').trim();
const hcId = process.env.HC_ID || '1';
const routes = [
  '/dashboard/',
  '/profil/',
  '/team/',
  '/upload/',
  '/all_kids',
  '/kid_details/21',
  '/zugabreise',
  '/zuganreise',
  '/budo_familien/',
  '/spezial_familien/',
  '/murdergame',
  '/serienbrief',
  '/kindergesamtzahl/',
  '/kindergeburtstage/',
  '/swp-dashboard/',
  '/schwerpunkt/1/',
  '/schwerpunkt/1/update',
  '/swpmeals/1',
  '/swp-einteilung-w1',
  '/swp-einteilung-w2',
  '/happy-cleaning/',
  `/happy-cleaning/${hcId}/assignment/`,
  '/happy-cleaning/print/',
  '/kitchen',
  '/auslagerorte-list/',
  '/auslagerorte/1/',
  '/auslagerorte/create',
];

(async () => {
  const browser = await chromium.launch({
    executablePath: '/usr/bin/google-chrome',
    headless: true,
  });
  const auth = await browser.newContext({
    viewport: { width: 1280, height: 900 },
  });
  const loginPage = await auth.newPage();
  await loginPage.goto(`${baseURL}/login`);
  await loginPage.locator('#root input[name="username"]').fill(username);
  await loginPage.locator('#root input[name="password"]').fill('baseline-only-password');
  await Promise.all([
    loginPage.waitForURL(
      url => !url.pathname.replace(/\/$/, '').endsWith('/login'),
      { waitUntil: 'domcontentloaded' },
    ),
    loginPage.locator('#root input[type="submit"]').click(),
  ]);
  const storageState = await auth.storageState();

  const mobile = await browser.newContext({
    viewport: { width: 390, height: 844 },
    isMobile: true,
    hasTouch: true,
    storageState,
  });
  const page = await mobile.newPage();

  const results = [];
  for (const path of routes) {
    const response = await page.goto(`${baseURL}${path}`, {
      waitUntil: 'domcontentloaded',
    });
    await page.waitForTimeout(300);
    results.push(await page.evaluate(({ route, status }) => ({
      path: route,
      status,
      viewportWidth: window.innerWidth,
      documentWidth: document.documentElement.scrollWidth,
      viewportMismatch: window.innerWidth !== 390,
      overflows:
        window.innerWidth !== 390
        || document.documentElement.scrollWidth > window.innerWidth,
    }), { route: path, status: response?.status() }));
  }

  fs.writeFileSync(
    'docs/evidence/issue-100/overflow-report.json',
    `${JSON.stringify(results, null, 2)}\n`,
  );
  await browser.close();

  const failures = results.filter(result => result.status >= 400 || result.overflows);
  if (failures.length) {
    console.error(JSON.stringify(failures, null, 2));
    process.exitCode = 1;
  } else {
    console.log(`checked ${results.length} routes without document-level mobile overflow`);
  }
})();
