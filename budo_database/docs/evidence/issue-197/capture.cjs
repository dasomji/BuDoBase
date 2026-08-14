const { chromium } = require('../../../.artifacts/tools/node_modules/playwright');
const fs = require('fs');
const path = require('path');

const baseURL = process.env.BASE_URL || 'http://budobase.test';
const outputDirectory = path.resolve(__dirname);
const bundleDirectory = path.resolve(__dirname, '../../../budo_app/static/frontend');

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

const warning = 'Bitte prüfe außerhalb von BuDoBase persönlich oder über einen bekannten Kontaktweg, ob diese E-Mail-Adresse wirklich zur Person gehört und sie selbst den Beitritt angefragt hat.';
const turnuses = [{
  id: 1,
  label: 'T1-2027',
  number: 1,
  start: '2027-07-05',
  end: '2027-07-18',
  request_summary: { pending: 2 },
  pending_requests: [
    { id: 101, user_id: 201, name: 'Sofia Hofer', email: 'sofia.hofer@mail.at' },
    { id: 102, user_id: 202, name: 'Paul Auer', email: 'paul.auer@mail.at' },
  ],
  members: [
    { id: 1, user_id: 1, name: 'Mara Sommer', functional_role: 'leitung', role_label: 'Leitung', team_label: '' },
    { id: 2, user_id: 2, name: 'Jonas Berger', functional_role: 'leitung', role_label: 'Leitung', team_label: '' },
    { id: 3, user_id: 3, name: 'Amira König', functional_role: 'teamer', role_label: 'Teamer', team_label: 'Betreuer:in' },
    { id: 4, user_id: 4, name: 'David Steiner', functional_role: 'teamer', role_label: 'Teamer', team_label: 'Küche' },
    { id: 5, user_id: 5, name: 'Elif Yılmaz', functional_role: 'teamer', role_label: 'Teamer', team_label: 'Freiwillige:r' },
    { id: 6, user_id: 6, name: 'Leo Berger', functional_role: 'teamer', role_label: 'Teamer', team_label: 'Betreuer:in' },
    { id: 7, user_id: 7, name: 'Nora Weiss', functional_role: 'teamer', role_label: 'Teamer', team_label: 'Küche' },
  ],
}, {
  id: 2,
  label: 'T2-2027',
  number: 2,
  start: '2027-08-02',
  end: '2027-08-15',
  request_summary: { pending: 1 },
  pending_requests: [{ id: 103, user_id: 203, name: 'Lina Wolf', email: 'lina.wolf@mail.at' }],
  members: [
    { id: 8, user_id: 8, name: 'Clara Lang', functional_role: 'leitung', role_label: 'Leitung', team_label: '' },
    { id: 9, user_id: 9, name: 'Ben Wagner', functional_role: 'teamer', role_label: 'Teamer', team_label: 'Betreuer:in' },
    { id: 10, user_id: 10, name: 'Derya Kaya', functional_role: 'teamer', role_label: 'Teamer', team_label: 'Küche' },
  ],
}, {
  id: 3,
  label: 'T2-2026',
  number: 2,
  start: '2026-08-03',
  end: '2026-08-16',
  request_summary: { pending: 0 },
  pending_requests: [],
  members: [
    { id: 11, user_id: 11, name: 'Selma Graf', functional_role: 'leitung', role_label: 'Leitung', team_label: '' },
    { id: 12, user_id: 12, name: 'Anna Mayr', functional_role: 'teamer', role_label: 'Teamer', team_label: 'Betreuer:in' },
  ],
}, {
  id: 4,
  label: 'T1-2026',
  number: 1,
  start: '2026-07-06',
  end: '2026-07-19',
  request_summary: { pending: 0 },
  pending_requests: [],
  members: [{ id: 13, user_id: 13, name: 'Ida Schwarz', functional_role: 'leitung', role_label: 'Leitung', team_label: '' }],
}];

const years = [
  { year: 2027, turnuses: turnuses.slice(0, 2) },
  { year: 2026, turnuses: turnuses.slice(2) },
];

function bootstrap(role) {
  return {
    authenticated: true,
    csrf_token: 'deterministic-browser-token',
    messages: [],
    permissions: { manage_teams: true },
    profile: { id: role === 'admin' ? 900 : 901, rufname: role === 'admin' ? 'Alex Admin' : 'Lena Leitung' },
    turnus: { id: 1, label: 'T1-2027' },
    turnus_selection: { selected_id: 1, options: [{ id: 1, label: 'T1-2027' }] },
    search_index: { kids: [], focuses: [], places: [] },
    happy_cleaning_events: [],
  };
}

function routeData(role) {
  return {
    years,
    people: [
      { id: 301, name: 'Kim Bauer', relationships: [], turnus_ids: [], available: true },
      { id: 302, name: 'Noah Graf mit einem sehr langen Namen', relationships: ['T2-2026'], turnus_ids: [3], available: false },
    ],
    can_manage_leitung: role === 'admin',
    can_manage_memberships: true,
    identity_verification_warning: warning,
  };
}

async function mockApi(page, role) {
  await page.route('**/api/**', async route => {
    const pathname = new URL(route.request().url()).pathname;
    if (pathname === '/api/bootstrap/') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(bootstrap(role)) });
      return;
    }
    if (pathname.startsWith('/api/route-data/')) {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(routeData(role)) });
      return;
    }
    await route.fulfill({ status: 200, contentType: 'application/json', body: '{}' });
  });
}

async function mockProductionBundle(page) {
  await page.route('**/static/frontend/**', async route => {
    const relativePath = new URL(route.request().url()).pathname.replace('/static/frontend/', '');
    const filePath = path.resolve(bundleDirectory, relativePath);
    assert(filePath.startsWith(`${bundleDirectory}${path.sep}`), `Unsafe bundle path: ${relativePath}`);
    assert(fs.existsSync(filePath), `Production bundle asset is missing: ${relativePath}`);
    const extension = path.extname(filePath);
    const contentType = {
      '.css': 'text/css',
      '.js': 'text/javascript',
      '.png': 'image/png',
      '.woff2': 'font/woff2',
    }[extension] || 'application/octet-stream';
    await route.fulfill({ status: 200, contentType, path: filePath });
  });
}

async function inspect(browser, role, viewport) {
  const routePath = role === 'admin' ? '/admin/teams/' : '/teams/';
  const context = await browser.newContext({
    viewport,
    deviceScaleFactor: 1,
    isMobile: viewport.width <= 900,
    hasTouch: viewport.width <= 900,
  });
  const page = await context.newPage();
  page.on('pageerror', error => console.error(`[${role} ${viewport.width}px]`, error));
  page.on('console', message => {
    if (message.type() === 'error') console.error(`[${role} ${viewport.width}px]`, message.text());
  });
  await page.route(`**${routePath}`, async route => {
    if (route.request().resourceType() !== 'document') {
      await route.continue();
      return;
    }
    await route.fulfill({
      status: 200,
      contentType: 'text/html',
      body: '<!doctype html><html lang="de"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><link rel="stylesheet" href="/static/frontend/app.css"></head><body><div id="root"></div><script type="module" src="/static/frontend/app.js"></script></body></html>',
    });
  });
  await mockProductionBundle(page);
  await mockApi(page, role);
  const response = await page.goto(`${baseURL}${routePath}`, { waitUntil: 'networkidle' });
  assert(response?.status() === 200, `${routePath} returned HTTP ${response?.status()}`);
  await page.getByRole('heading', { name: 'T1-2027', level: 2 }).waitFor();
  await page.evaluate(() => document.fonts.ready);

  const contract = await page.evaluate(() => {
    const master = document.querySelector('.team-master-detail');
    const rail = document.querySelector('.team-turnus-rail');
    const detail = document.querySelector('.team-detail');
    const requests = document.querySelector('.team-request-panel');
    const memberList = document.querySelector('.team-member-list');
    const memberTiles = [...document.querySelectorAll('.team-member-tile')];
    const yearGroups = [...document.querySelectorAll('.team-year-group')];
    const turnusRows = [...document.querySelectorAll('.team-year-turnuses')];
    const masterStyle = getComputedStyle(master);
    const memberStyle = getComputedStyle(memberList);
    const requestStyle = getComputedStyle(requests);
    return {
      viewport: { width: innerWidth, height: innerHeight },
      documentWidth: document.documentElement.scrollWidth,
      master: {
        display: masterStyle.display,
        columns: masterStyle.gridTemplateColumns,
        borderRadius: masterStyle.borderRadius,
        railWidth: rail.getBoundingClientRect().width,
        railTop: rail.getBoundingClientRect().top,
        detailTop: detail.getBoundingClientRect().top,
      },
      requests: {
        background: requestStyle.backgroundColor,
        borderStyle: requestStyle.borderStyle,
        insideDetail: detail.contains(requests),
        warningInside: requests.contains(document.querySelector('[role="alert"]')),
      },
      members: {
        columns: memberStyle.gridTemplateColumns,
        tileCount: memberTiles.length,
        distinctLeftEdges: new Set(memberTiles.map(tile => Math.round(tile.getBoundingClientRect().left))).size,
      },
      selector: {
        yearGroupCount: yearGroups.length,
        yearGroupDisplays: yearGroups.map(group => getComputedStyle(group).display),
        rowOverflow: turnusRows.map(row => getComputedStyle(row).overflowX),
        rowWidths: turnusRows.map(row => ({ client: row.clientWidth, scroll: row.scrollWidth })),
      },
    };
  });

  assert(contract.requests.insideDetail, `${role} request panel escaped the selected detail`);
  assert(contract.requests.warningInside, `${role} identity warning is not attached to the request panel`);
  assert(contract.requests.background === 'rgb(255, 248, 229)', `${role} request panel lost its warm surface (${contract.requests.background})`);
  assert(contract.requests.borderStyle === 'solid', `${role} request panel lost its border`);
  assert(contract.members.tileCount === 7, `${role} populated member panel did not render seven members`);
  assert(await page.getByRole('button', { name: 'Person hinzufügen' }).count() === 1, `${role} page-level add-person action is missing`);
  assert(await page.getByRole('button', { name: 'Sofia Hofer annehmen' }).count() === 1, `${role} approval action is missing`);
  assert(await page.getByRole('button', { name: 'Sofia Hofer ablehnen' }).count() === 1, `${role} rejection action is missing`);
  assert(await page.getByRole('button', { name: 'Amira König bearbeiten' }).count() === 1, `${role} person-specific pencil action is missing`);
  if (role === 'leitung') {
    assert(await page.getByRole('button', { name: 'Mara Sommer bearbeiten' }).count() === 0, 'Leitung can edit another Leitung');
  } else {
    assert(await page.getByRole('button', { name: 'Mara Sommer bearbeiten' }).count() === 1, 'Admin cannot edit a Leitung');
  }

  if (viewport.width > 900) {
    assert(contract.master.display === 'grid', `${role} desktop master-detail is not one grid surface`);
    assert(contract.master.borderRadius !== '0px', `${role} desktop master-detail lost its rounded surface`);
    assert(contract.master.railWidth >= 280 && contract.master.railWidth <= 320, `${role} desktop rail is ${contract.master.railWidth}px instead of approximately 300px`);
    assert(contract.master.railTop === contract.master.detailTop, `${role} rail and detail no longer share one surface`);
    assert(contract.members.distinctLeftEdges === 2, `${role} desktop member tiles are not two columns`);
  } else {
    assert(contract.documentWidth === viewport.width, `${role} mobile page overflows to ${contract.documentWidth}px`);
    assert(contract.master.display === 'block', `${role} mobile master-detail did not stack`);
    assert(contract.members.distinctLeftEdges === 1, `${role} mobile member tiles are not one column`);
    assert(contract.selector.yearGroupCount === 2, `${role} mobile selector lost a year group`);
    assert(contract.selector.yearGroupDisplays.every(display => display === 'grid'), `${role} mobile year grouping disappeared`);
    assert(contract.selector.rowOverflow.every(overflow => overflow === 'auto'), `${role} mobile Turnus rows are not horizontally scrollable`);
    assert(contract.selector.rowWidths.every(({ client, scroll }) => scroll > client), `${role} mobile Turnus rows do not expose horizontal overflow`);
  }

  const viewportName = viewport.width > 900 ? 'desktop' : 'mobile';
  await page.screenshot({
    path: path.join(outputDirectory, `${role}--${viewportName}.png`),
    animations: 'disabled',
  });

  await page.getByRole('button', { name: 'Person hinzufügen' }).click();
  await page.getByRole('heading', { name: 'Registrierte Personen' }).waitFor();
  assert(await page.getByRole('button', { name: 'Kim Bauer als Teamer zu T1-2027 hinzufügen' }).count() === 1, `${role} cannot add an available Teamer`);
  assert(
    await page.getByRole('button', { name: 'Kim Bauer als Leitung zu T1-2027 hinzufügen' }).count() === (role === 'admin' ? 1 : 0),
    `${role} add-person controls do not match its capability scope`,
  );

  if (viewport.width <= 900) {
    await page.getByRole('button', { name: 'T1-2026 auswählen' }).scrollIntoViewIfNeeded();
    await page.getByRole('button', { name: 'T1-2026 auswählen' }).click();
    await page.getByRole('heading', { name: 'T1-2026', level: 2 }).waitFor();
  }
  await context.close();
  return contract;
}

async function main() {
  fs.mkdirSync(outputDirectory, { recursive: true });
  const browser = await chromium.launch({ executablePath: '/usr/bin/google-chrome', headless: true });
  try {
    const results = {};
    for (const role of ['admin', 'leitung']) {
      results[role] = {
        desktop: await inspect(browser, role, { width: 1440, height: 1050 }),
        mobile: await inspect(browser, role, { width: 390, height: 844 }),
      };
    }
    fs.writeFileSync(path.join(outputDirectory, 'browser-contracts.json'), `${JSON.stringify(results, null, 2)}\n`);
  } finally {
    await browser.close();
  }
}

main().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
