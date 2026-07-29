// Screenshot capture for the design-system refactor review page (review.html).
// Adapted from .artifacts/capture-baseline.cjs — same QA login, same tooling.
//
// Usage (from repo root):
//   CAPTURE_DIR=docs/evidence/design-system-refactor/before node docs/evidence/design-system-refactor/capture.cjs
//   CAPTURE_DIR=docs/evidence/design-system-refactor/after  node docs/evidence/design-system-refactor/capture.cjs
//
// Env: BASE_URL (default http://localhost:8000), HC_ID (happy-cleaning event id, default 1),
//      CAPTURE_ONLY (comma-separated slugs to re-capture selectively).
// Print PDFs are written as <slug>--print.pdf; convert page 1 for review.html with PyMuPDF:
//   cd <capture dir> && python3 -c "import fitz,glob
//   [fitz.open(p)[0].get_pixmap(dpi=100).save(p.replace('.pdf','.png')) for p in glob.glob('*--print.pdf')]"
const { chromium } = require('../../../.artifacts/tools/node_modules/playwright');
const fs = require('fs');

const baseURL = process.env.BASE_URL || 'http://localhost:8000';
const outDir = process.env.CAPTURE_DIR;
if (!outDir) throw new Error('Set CAPTURE_DIR to the before/ or after/ directory');
fs.mkdirSync(outDir, { recursive: true });
const hcId = process.env.HC_ID || '1';
const only = process.env.CAPTURE_ONLY ? new Set(process.env.CAPTURE_ONLY.split(',')) : null;

const username = fs.readFileSync('.artifacts/baseline/username.txt', 'utf8').trim();
const password = 'baseline-only-password';

// Keep slugs in sync with the MANIFEST in review.html.
const routes = [
  ['login', '/login', { public: true }],
  ['dashboard', '/dashboard/', { print: true }],
  ['profil', '/profil/'],
  ['team', '/team/'],
  ['upload', '/upload/'],
  ['all-kids', '/all_kids', { print: true }],
  ['kid-detail', '/kid_details/21'],
  ['zugabreise', '/zugabreise'],
  ['zuganreise', '/zuganreise'],
  ['budo-familien', '/budo_familien/'],
  ['spezial-familien', '/spezial_familien/'],
  ['murdergame', '/murdergame'],
  ['serienbrief', '/serienbrief'],
  ['kindergesamtzahl', '/kindergesamtzahl/'],
  ['kindergeburtstage', '/kindergeburtstage/'],
  ['swp-dashboard', '/swp-dashboard/'],
  ['schwerpunkt-detail', '/schwerpunkt/1/'],
  ['schwerpunkt-update', '/schwerpunkt/1/update'],
  ['swpmeals', '/swpmeals/1'],
  ['swp-einteilung-w1', '/swp-einteilung-w1', { print: true }],
  ['swp-einteilung-w2', '/swp-einteilung-w2'],
  ['happy-cleaning', '/happy-cleaning/'],
  ['hc-assignment', `/happy-cleaning/${hcId}/assignment/`],
  ['hc-nummernliste', '/happy-cleaning/print/', { print: true }],
  ['kitchen', '/kitchen', { print: true }],
  ['auslagerorte', '/auslagerorte-list/'],
  ['auslagerort-detail', '/auslagerorte/1/'],
  ['auslagerort-create', '/auslagerorte/create'],
];

const results = [];

async function capture(page, slug, path, viewport) {
  const response = await page.goto(`${baseURL}${path}`, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(1200);
  results.push({
    slug,
    path,
    viewport,
    status: response?.status(),
    url: page.url(),
    heading: await page.locator('h1, h2').first().textContent().catch(() => null),
  });
  await page.screenshot({ path: `${outDir}/${slug}--${viewport}.png`, fullPage: true });
}

(async () => {
  const browser = await chromium.launch({ executablePath: '/usr/bin/google-chrome', headless: true });

  const desktop = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  const desktopPage = await desktop.newPage();

  await desktopPage.goto(`${baseURL}/login`);
  await desktopPage.locator('#root input[name="username"]').fill(username);
  await desktopPage.locator('#root input[name="password"]').fill(password);
  await Promise.all([
    desktopPage.waitForURL(url => !url.pathname.replace(/\/$/, '').endsWith('/login')),
    desktopPage.locator('#root input[type="submit"]').click(),
  ]);
  const state = await desktop.storageState();

  const publicDesktop = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  const mobile = await browser.newContext({
    viewport: { width: 390, height: 844 },
    deviceScaleFactor: 1,
    isMobile: true,
    hasTouch: true,
    storageState: state,
  });
  const publicMobile = await browser.newContext({
    viewport: { width: 390, height: 844 },
    deviceScaleFactor: 1,
    isMobile: true,
    hasTouch: true,
  });
  const mobilePage = await mobile.newPage();
  const publicDesktopPage = await publicDesktop.newPage();
  const publicMobilePage = await publicMobile.newPage();

  for (const [slug, path, opts = {}] of routes) {
    if (only && !only.has(slug)) continue;
    const dPage = opts.public ? publicDesktopPage : desktopPage;
    const mPage = opts.public ? publicMobilePage : mobilePage;
    await capture(dPage, slug, path, 'desktop');
    if (opts.print) {
      await dPage.pdf({
        path: `${outDir}/${slug}--print.pdf`,
        format: 'A4',
        printBackground: true,
      });
    }
    await capture(mPage, slug, path, 'mobile');
  }

  fs.writeFileSync(`${outDir}/report.json`, JSON.stringify(results, null, 2));
  await browser.close();

  const bad = results.filter(r => r.status && r.status >= 400);
  console.log(`captured ${results.length} shots to ${outDir}`);
  if (bad.length) console.log('NON-OK ROUTES:', bad.map(r => `${r.slug} (${r.status})`).join(', '));
})();
