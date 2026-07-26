const { chromium } = require('../../../.artifacts/tools/node_modules/playwright');
const fs = require('fs');

const baseURL = process.env.BASE_URL || 'http://127.0.0.1:8018';
const username = fs.readFileSync('.artifacts/baseline/username.txt', 'utf8').trim();
const routes = [
  '/dashboard/',
  '/profil/',
  '/team/',
  '/upload/',
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
  '/kitchen',
  '/auslagerorte-list/',
  '/auslagerorte/1/',
  '/auslagerorte/create',
];

(async () => {
  const browser = await chromium.launch({ executablePath: '/usr/bin/google-chrome', headless: true });
  const page = await browser.newPage({
    viewport: { width: 390, height: 844 },
    isMobile: true,
    hasTouch: true,
  });
  await page.goto(`${baseURL}/login`);
  await page.waitForTimeout(500);
  const loginCardToggle = page.getByRole('button', { name: 'Login öffnen' });
  if (await loginCardToggle.count()) await loginCardToggle.click();
  await page.locator('#root input[name="username"]').fill(username);
  await page.locator('#root input[name="password"]').fill('baseline-only-password');
  await page.locator('#root input[type="submit"]').click();
  await page.waitForURL(url => !url.pathname.replace(/\/$/, '').endsWith('/login'), {
    waitUntil: 'domcontentloaded',
  });

  const results = [];
  for (const path of routes) {
    const response = await page.goto(`${baseURL}${path}`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(300);
    results.push(await page.evaluate(({ path, status }) => ({
      path,
      status,
      viewportWidth: window.innerWidth,
      documentWidth: document.documentElement.scrollWidth,
      overflows: document.documentElement.scrollWidth > window.innerWidth,
      headerControls: Array.from(
        document.querySelectorAll('#header-content > *'),
        element => ({
          id: element.id,
          display: getComputedStyle(element).display,
          left: Math.round(element.getBoundingClientRect().left),
          right: Math.round(element.getBoundingClientRect().right),
        }),
      ),
    }), { path, status: response?.status() }));
  }
  fs.writeFileSync(
    'docs/evidence/issue-98/overflow-report.json',
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
