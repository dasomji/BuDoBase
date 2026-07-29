const playwrightModule = process.env.PLAYWRIGHT_MODULE
  || '../../../.artifacts/tools/node_modules/playwright';
const { chromium } = require(playwrightModule);
const fs = require('fs');

const baseURL = process.env.BASE_URL || 'http://127.0.0.1:8024';
const outputDirectory = 'docs/evidence/issue-124';
const usernameFile = process.env.REVIEW_USERNAME_FILE
  || '/home/dev/Development/BuDoBase/budo_database/.artifacts/baseline/username.txt';
const username = fs.readFileSync(usernameFile, 'utf8').trim();
const password = 'baseline-only-password';

function assert(condition, message) {
  if (!condition) throw new Error(message);
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

async function openPage(browser, storageState, viewport, path) {
  const context = await browser.newContext({
    viewport,
    deviceScaleFactor: 1,
    isMobile: viewport.width <= 900,
    hasTouch: viewport.width <= 900,
    storageState,
  });
  const page = await context.newPage();
  const response = await page.goto(`${baseURL}${path}`, { waitUntil: 'networkidle' });
  assert(response?.status() === 200, `${path} returned HTTP ${response?.status()}`);
  return { context, page };
}

async function inspectNumberCells(browser, storageState) {
  const { context, page } = await openPage(
    browser,
    storageState,
    { width: 1280, height: 900 },
    '/all_kids',
  );
  const numberCells = page.locator('.number-cell');
  assert(await numberCells.count() > 1, 'All Kids did not render age cells');
  const contract = await numberCells.evaluateAll(cells => cells.slice(0, 8).map(cell => {
    const contents = document.createRange();
    contents.selectNodeContents(cell);
    return {
      value: cell.textContent.trim(),
      textAlign: getComputedStyle(cell).textAlign,
      contentRight: contents.getBoundingClientRect().right,
      cellRight: cell.getBoundingClientRect().right,
    };
  }));
  assert(contract.every(cell => cell.textAlign === 'right'), 'All Kids age cells were not right-aligned');
  assert(
    new Set(contract.map(cell => cell.contentRight)).size === 1,
    'All Kids age values did not share a right edge',
  );
  await page.locator('[data-slot="table-scroll"]').screenshot({
    path: `${outputDirectory}/all-kids-number-cells--desktop.png`,
  });
  await context.close();

  const focusPage = await openPage(
    browser,
    storageState,
    { width: 1280, height: 900 },
    '/schwerpunkt/1/',
  );
  const focusAgeHeader = focusPage.page.getByRole('columnheader', { name: /Alter/ });
  assert(await focusAgeHeader.count() === 1, 'Focus detail lost its age column');
  const focusContract = {
    ageHeader: (await focusAgeHeader.textContent()).trim(),
    renderedAgeCells: await focusPage.page.locator('.number-cell').count(),
    emptyState: await focusPage.page.getByText('Keine Einträge').count() === 1,
  };
  await focusPage.context.close();
  return { allKids: contract, focus: focusContract };
}

async function inspectLongEmail(browser, storageState) {
  const { context, page } = await openPage(
    browser,
    storageState,
    { width: 390, height: 844 },
    '/team/',
  );
  const card = page.locator('.card').filter({ has: page.locator('a[href^="mailto:"]') }).first();
  const toggle = card.locator('.card-toggle');
  if (await toggle.getAttribute('aria-expanded') === 'false') await toggle.click();
  await page.waitForTimeout(350);
  const contract = await card.locator('a[href^="mailto:"]').evaluate(email => {
    const cardElement = email.closest('.card');
    const content = email.closest('.card-info-content');
    return {
      value: email.textContent,
      viewportWidth: window.innerWidth,
      documentWidth: document.documentElement.scrollWidth,
      bodyWidth: document.body.scrollWidth,
      overflowWrap: getComputedStyle(email).overflowWrap,
      cardWidth: cardElement.getBoundingClientRect().width,
      cardMinWidth: getComputedStyle(cardElement).minWidth,
      contentMinWidth: getComputedStyle(content).minWidth,
    };
  });
  assert(contract.value.length > 100, 'Disposable QA database did not contain the long email');
  assert(contract.documentWidth === 390, `Long email forced ${contract.documentWidth}px page width`);
  assert(contract.bodyWidth === 390, `Long email forced ${contract.bodyWidth}px body width`);
  assert(contract.overflowWrap === 'anywhere', 'Long email did not use anywhere wrapping');
  assert(contract.cardMinWidth === '0px', 'Card was not allowed to shrink');
  assert(contract.contentMinWidth === '0px', 'Card content was not allowed to shrink');
  await card.screenshot({ path: `${outputDirectory}/team-long-email--390px.png` });
  await context.close();
  return contract;
}

async function openFirstStation(page) {
  await page.goto(`${baseURL}/happy-cleaning/`, { waitUntil: 'networkidle' });
  const eventToggle = page.locator('article .card-toggle').first();
  if (await eventToggle.getAttribute('aria-expanded') === 'false') await eventToggle.click();
  const station = page.locator('button[aria-label^="Station "][aria-label$=" öffnen"]').first();
  await station.click();
  await page.locator('.happy-cleaning-station-detail-card').waitFor();
}

async function inspectStationDetail(browser, storageState) {
  const { context, page } = await openPage(
    browser,
    storageState,
    { width: 1280, height: 900 },
    '/happy-cleaning/',
  );
  await openFirstStation(page);
  const card = page.locator('.happy-cleaning-station-detail-card');
  const header = card.locator('.card-toggle');
  const action = card.locator('.card-header-action');
  const close = card.getByRole('button', { name: 'Detail schließen' });
  const actionContract = await action.evaluate(element => {
    const headerElement = element.closest('.card-toggle');
    const bounds = element.getBoundingClientRect();
    const headerBounds = headerElement.getBoundingClientRect();
    return {
      marginRight: getComputedStyle(element).marginRight,
      right: bounds.right,
      headerRight: headerBounds.right,
      headerPaddingRight: getComputedStyle(headerElement).paddingRight,
      hasToggleIcon: Boolean(headerElement.querySelector(':scope > .icon')),
    };
  });
  assert(actionContract.marginRight === '0px', 'Station-detail action retained an extra right margin');
  assert(!actionContract.hasToggleIcon, 'Station-detail unexpectedly rendered a Card toggle icon');
  await header.screenshot({ path: `${outputDirectory}/station-detail-header--desktop.png` });

  await card.getByRole('button', { name: 'Bearbeiten' }).click();
  const name = page.getByLabel('Name der Station');
  await name.fill(`${await name.inputValue()} Entwurf`);
  await close.click();
  const dirtyDialog = page.getByRole('dialog', { name: 'Ungespeicherte Änderungen' });
  await dirtyDialog.waitFor();
  const dirtyContract = await dirtyDialog.getByRole('heading', {
    level: 2,
    name: 'Ungespeicherte Änderungen',
  }).evaluate(heading => {
    const popup = heading.closest('[role="dialog"]');
    const headingBounds = heading.getBoundingClientRect();
    const popupBounds = popup.getBoundingClientRect();
    return {
      marginTop: getComputedStyle(heading).marginTop,
      headingTop: headingBounds.top,
      popupTop: popupBounds.top,
      popupPaddingTop: getComputedStyle(popup).paddingTop,
      gap: headingBounds.top - popupBounds.top,
    };
  });
  assert(dirtyContract.marginTop === '0px', 'Dirty-dialog heading retained a top margin');
  assert(
    dirtyContract.gap === Number.parseFloat(dirtyContract.popupPaddingTop),
    'Dirty-dialog heading had space beyond the popup padding',
  );
  await dirtyDialog.screenshot({ path: `${outputDirectory}/dirty-dialog--desktop.png` });
  await context.close();
  return { action: actionContract, dirtyDialog: dirtyContract };
}

async function inspectAssignmentAt(browser, storageState, width) {
  const { context, page } = await openPage(
    browser,
    storageState,
    { width, height: 900 },
    '/happy-cleaning/1/assignment/',
  );
  const table = page.getByRole('table', { name: 'Happy Cleaning Stationen' });
  const toggle = table.getByRole('button', { name: 'Kindernamen verbergen' });
  const rowHeader = table.getByRole('rowheader').first();
  const columnHeader = table.getByRole('columnheader').first();
  const contract = await page.evaluate(() => {
    const tableElement = document.querySelector('table[aria-label="Happy Cleaning Stationen"]');
    const toggleElement = tableElement.querySelector('[aria-label="Kindernamen verbergen"]');
    const childrenHeader = toggleElement.closest('th');
    const row = tableElement.querySelector('tbody th[scope="row"]');
    const column = tableElement.querySelector('thead th[scope="col"]');
    return {
      viewportWidth: window.innerWidth,
      toggleVisible: Boolean(toggleElement.offsetParent),
      childrenHeaderDisplay: getComputedStyle(childrenHeader).display,
      rowHeader: {
        value: row.textContent.trim(),
        background: getComputedStyle(row).backgroundColor,
        whiteSpace: getComputedStyle(row).whiteSpace,
      },
      columnHeader: {
        background: getComputedStyle(column).backgroundColor,
        whiteSpace: getComputedStyle(column).whiteSpace,
      },
    };
  });
  assert(contract.toggleVisible, `Child-name toggle was not reachable at ${width}px`);
  assert(contract.rowHeader.whiteSpace === 'normal', `Station row header did not wrap at ${width}px`);
  assert(
    contract.rowHeader.background !== contract.columnHeader.background,
    `Station row header retained column-header chrome at ${width}px`,
  );

  if (width === 800) {
    await table.screenshot({ path: `${outputDirectory}/assignment-table--800px.png` });

    const ghost = toggle;
    const fixture = await ghost.evaluate(button => {
      const clone = button.cloneNode(true);
      clone.id = 'issue-124-active-option-fixture';
      clone.setAttribute('aria-selected', 'true');
      clone.classList.add('bg-white');
      clone.style.position = 'fixed';
      clone.style.left = '8px';
      clone.style.top = '8px';
      clone.style.zIndex = '99999';
      document.body.append(clone);
      return clone.id;
    });
    const active = page.locator(`#${fixture}`);
    const selectedBackground = await active.evaluate(element => getComputedStyle(element).backgroundColor);
    await active.hover();
    const hoveredBackground = await active.evaluate(element => getComputedStyle(element).backgroundColor);
    assert(
      selectedBackground === 'rgb(169, 207, 239)',
      `Selected ghost Button background was ${selectedBackground}`,
    );
    assert(
      hoveredBackground === selectedBackground,
      `Hover changed the selected Button background to ${hoveredBackground}`,
    );
    contract.activeOption = { selectedBackground, hoveredBackground };
  }

  await context.close();
  return contract;
}

async function inspectAssignment(browser, storageState) {
  const contracts = {};
  for (const width of [639, 640, 800, 900]) {
    contracts[width] = await inspectAssignmentAt(browser, storageState, width);
  }
  return contracts;
}

let browser;

(async () => {
  browser = await chromium.launch({
    executablePath: '/usr/bin/google-chrome',
    headless: true,
  });
  const storageState = await authenticate(browser);
  const contracts = {
    numberCells: await inspectNumberCells(browser, storageState),
    longEmail: await inspectLongEmail(browser, storageState),
    stationDetail: await inspectStationDetail(browser, storageState),
    assignment: await inspectAssignment(browser, storageState),
  };
  fs.writeFileSync(
    `${outputDirectory}/browser-contracts.json`,
    `${JSON.stringify(contracts, null, 2)}\n`,
  );
})().catch(error => {
  console.error(error);
  process.exitCode = 1;
}).finally(async () => {
  await browser?.close();
});
