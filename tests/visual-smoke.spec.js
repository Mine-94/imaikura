const { test, expect } = require('@playwright/test');

const representativePages = [
  '/',
  '/paid-leave/',
  '/salary-take-home/',
  '/income-wall/',
  '/minimum-wage-2026/',
  '/guides/',
  '/help/'
];

async function prepare(page) {
  const pageErrors = [];
  page.on('pageerror', error => pageErrors.push(String(error)));
  await page.route('https://**', route => route.abort());
  await page.addInitScript(() => {
    window.adsbygoogle = window.adsbygoogle || [];
    window.gtag = window.gtag || function () {};
  });
  return pageErrors;
}

async function assertLayout(page, path) {
  const state = await page.evaluate(() => {
    const root = document.documentElement;
    const body = document.body;
    const visible = element => {
      const style = getComputedStyle(element);
      const rect = element.getBoundingClientRect();
      return style.display !== 'none' && style.visibility !== 'hidden' && rect.width > 0 && rect.height > 0;
    };
    const clipped = [...document.querySelectorAll('.brand-mark,.tool-no,.trust-badge,.badge,button,.button,.btn')]
      .filter(visible)
      .filter(el => el.scrollWidth > el.clientWidth + 2 || el.scrollHeight > el.clientHeight + 2)
      .map(el => ({ cls: el.className, text: (el.textContent || '').trim().slice(0, 80), sw: el.scrollWidth, cw: el.clientWidth, sh: el.scrollHeight, ch: el.clientHeight }));
    const outside = [...document.querySelectorAll('.container,.header-inner,.content-card,.tool-card,form,.result-box,.share-box')]
      .filter(visible)
      .map(el => ({ el, rect: el.getBoundingClientRect() }))
      .filter(({ rect }) => rect.left < -1 || rect.right > root.clientWidth + 1)
      .map(({ el, rect }) => ({ cls: el.className, left: rect.left, right: rect.right, viewport: root.clientWidth }));
    const mark = document.querySelector('.brand-mark');
    const markRect = mark ? mark.getBoundingClientRect() : null;
    return {
      viewport: root.clientWidth,
      scrollWidth: Math.max(root.scrollWidth, body.scrollWidth),
      h1: document.querySelectorAll('h1').length,
      main: Boolean(document.querySelector('main')),
      clipped,
      outside,
      brandMarkDelta: markRect ? Math.abs(markRect.width - markRect.height) : 0
    };
  });
  expect(state.h1, `${path}: one h1`).toBe(1);
  expect(state.main, `${path}: main exists`).toBeTruthy();
  expect(state.scrollWidth, `${path}: no horizontal overflow`).toBeLessThanOrEqual(state.viewport + 1);
  expect(state.clipped, `${path}: no clipped label/button text`).toEqual([]);
  expect(state.outside, `${path}: key blocks stay inside viewport`).toEqual([]);
  expect(state.brandMarkDelta, `${path}: brand mark remains square`).toBeLessThanOrEqual(2);
}

test('all sitemap pages load and keep the document width', async ({ page }) => {
  const errors = await prepare(page);
  const response = await page.request.get('/sitemap.xml');
  expect(response.ok()).toBeTruthy();
  const xml = await response.text();
  const paths = [...xml.matchAll(/<loc>https:\/\/imaikura\.com([^<]*)<\/loc>/g)].map(match => match[1] || '/');
  expect(paths.length).toBeGreaterThanOrEqual(40);
  for (const path of paths) {
    const loaded = await page.goto(path, { waitUntil: 'domcontentloaded' });
    expect(loaded && loaded.ok(), path).toBeTruthy();
    await assertLayout(page, path);
  }
  expect(errors).toEqual([]);
});

for (const viewport of [
  { name: 'mobile', width: 390, height: 844 },
  { name: 'tablet', width: 768, height: 1024 },
  { name: 'desktop', width: 1440, height: 1000 }
]) {
  for (const path of representativePages) {
    test(`${viewport.name} layout ${path}`, async ({ page }) => {
      const errors = await prepare(page);
      await page.setViewportSize({ width: viewport.width, height: viewport.height });
      const response = await page.goto(path, { waitUntil: 'domcontentloaded' });
      expect(response && response.ok()).toBeTruthy();
      await assertLayout(page, path);
      const name = path === '/' ? 'home' : path.replaceAll('/', '-').replace(/^-|-$/g, '');
      await page.screenshot({ path: `test-results/screenshots/${viewport.name}-${name}.png`, fullPage: true });
      expect(errors).toEqual([]);
    });
  }
}

test('paid leave calculator returns the statutory grant result', async ({ page }) => {
  const errors = await prepare(page);
  await page.goto('/paid-leave/', { waitUntil: 'domcontentloaded' });
  await page.fill('#hire-date', '2023-04-01');
  await page.fill('#reference-date', '2026-09-05');
  await page.selectOption('#schedule-mode', 'weekly');
  await page.selectOption('#weekly-days', '5');
  await page.fill('#weekly-hours', '40');
  await page.fill('#attendance-rate', '95');
  await page.fill('#days-taken', '4');
  await page.click('#calculate-paid-leave');
  const result = page.locator('#paid-leave-result');
  await expect(result).toBeVisible();
  await expect(result).toContainText('12日');
  await expect(result).toContainText('8日');
  expect(errors).toEqual([]);
});
