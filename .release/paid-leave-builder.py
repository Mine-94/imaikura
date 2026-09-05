from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse
from bs4 import BeautifulSoup
import ast
import datetime as dt
import html
import json
import re
import xml.etree.ElementTree as ET

ROOT = Path('.')
SITE = 'https://imaikura.com'
TODAY = '2026-09-05'
PUBLISHER = 'ca-pub-8602848692420724'

ENGINE = r'''(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  root.ImaikuraPaidLeave = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';

  const GRANT_TABLE = Object.freeze({
    full: Object.freeze([10, 11, 12, 14, 16, 18, 20]),
    4: Object.freeze([7, 8, 9, 10, 12, 13, 15]),
    3: Object.freeze([5, 6, 6, 8, 9, 10, 11]),
    2: Object.freeze([3, 4, 4, 5, 6, 6, 7]),
    1: Object.freeze([1, 2, 2, 2, 3, 3, 3])
  });

  function parseDate(value) {
    if (value instanceof Date && !Number.isNaN(value.getTime())) {
      return new Date(value.getFullYear(), value.getMonth(), value.getDate());
    }
    if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return null;
    const [year, month, day] = value.split('-').map(Number);
    const date = new Date(year, month - 1, day);
    if (date.getFullYear() !== year || date.getMonth() !== month - 1 || date.getDate() !== day) return null;
    return date;
  }

  function formatDate(date) {
    if (!(date instanceof Date) || Number.isNaN(date.getTime())) return '';
    return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
  }

  function addMonths(date, months) {
    const originalDay = date.getDate();
    const result = new Date(date.getFullYear(), date.getMonth(), 1);
    result.setMonth(result.getMonth() + months);
    const lastDay = new Date(result.getFullYear(), result.getMonth() + 1, 0).getDate();
    result.setDate(Math.min(originalDay, lastDay));
    return result;
  }

  function addDays(date, days) {
    const result = new Date(date.getFullYear(), date.getMonth(), date.getDate());
    result.setDate(result.getDate() + days);
    return result;
  }

  function diffDays(later, earlier) {
    const ms = Date.UTC(later.getFullYear(), later.getMonth(), later.getDate()) - Date.UTC(earlier.getFullYear(), earlier.getMonth(), earlier.getDate());
    return Math.floor(ms / 86400000);
  }

  function resolveScheduleGroup(scheduleMode, weeklyDays, annualDays, weeklyHours) {
    if (weeklyHours >= 30) return 'full';
    if (scheduleMode === 'annual') {
      if (annualDays >= 217) return 'full';
      if (annualDays >= 169) return '4';
      if (annualDays >= 121) return '3';
      if (annualDays >= 73) return '2';
      if (annualDays >= 48) return '1';
      return null;
    }
    if (weeklyDays >= 5) return 'full';
    if (weeklyDays >= 1 && weeklyDays <= 4) return String(weeklyDays);
    return null;
  }

  function calculatePaidLeave(input) {
    const hireDate = parseDate(input.hireDate);
    const referenceDate = parseDate(input.referenceDate);
    const scheduleMode = input.scheduleMode === 'annual' ? 'annual' : 'weekly';
    const weeklyDays = Number(input.weeklyDays);
    const annualDays = Number(input.annualDays);
    const weeklyHours = Number(input.weeklyHours);
    const attendanceRate = Number(input.attendanceRate);
    const daysTaken = Math.max(0, Number(input.daysTaken) || 0);

    const errors = [];
    if (!hireDate) errors.push('入社日を正しく入力してください。');
    if (!referenceDate) errors.push('基準日を正しく入力してください。');
    if (hireDate && referenceDate && referenceDate < hireDate) errors.push('基準日は入社日以後にしてください。');
    if (!Number.isFinite(weeklyHours) || weeklyHours < 0 || weeklyHours > 80) errors.push('週の所定労働時間は0〜80時間で入力してください。');
    if (!Number.isFinite(attendanceRate) || attendanceRate < 0 || attendanceRate > 100) errors.push('出勤率は0〜100％で入力してください。');
    if (scheduleMode === 'weekly' && (!Number.isInteger(weeklyDays) || weeklyDays < 1 || weeklyDays > 7)) errors.push('週の所定労働日数を選んでください。');
    if (scheduleMode === 'annual' && (!Number.isFinite(annualDays) || annualDays < 1 || annualDays > 366)) errors.push('年間の所定労働日数は1〜366日で入力してください。');
    if (errors.length) return { ok: false, errors };

    const scheduleGroup = resolveScheduleGroup(scheduleMode, weeklyDays, annualDays, weeklyHours);
    if (!scheduleGroup) {
      return {
        ok: false,
        errors: ['年間所定労働日数が48日未満の場合、この比例付与表では判定できません。勤務先または労働基準監督署へ確認してください。']
      };
    }

    const firstGrantDate = addMonths(hireDate, 6);
    const eligibleByAttendance = attendanceRate >= 80;

    if (referenceDate < firstGrantDate) {
      const statutoryDaysAtFirstGrant = eligibleByAttendance ? GRANT_TABLE[scheduleGroup][0] : 0;
      return {
        ok: true,
        beforeFirstGrant: true,
        scheduleGroup,
        fullTimeEquivalent: scheduleGroup === 'full',
        eligibleByAttendance,
        statutoryGrantDays: 0,
        firstGrantDays: statutoryDaysAtFirstGrant,
        firstGrantDate: formatDate(firstGrantDate),
        nextGrantDate: formatDate(firstGrantDate),
        daysUntilNextGrant: diffDays(firstGrantDate, referenceDate),
        currentGrantDate: '',
        expiryDate: '',
        remainingDays: 0,
        mandatoryFiveApplies: false,
        mandatoryFiveRemaining: 0,
        stage: -1,
        errors: []
      };
    }

    let stage = 0;
    let currentGrantDate = firstGrantDate;
    for (let i = 1; i <= 6; i += 1) {
      const candidate = addMonths(firstGrantDate, i * 12);
      if (candidate <= referenceDate) {
        stage = i;
        currentGrantDate = candidate;
      } else {
        break;
      }
    }
    if (referenceDate >= addMonths(firstGrantDate, 72)) {
      stage = 6;
      const elapsedYears = Math.floor(diffDays(referenceDate, firstGrantDate) / 365.2425);
      currentGrantDate = addMonths(firstGrantDate, Math.max(6, elapsedYears) * 12);
      while (addMonths(currentGrantDate, 12) <= referenceDate) currentGrantDate = addMonths(currentGrantDate, 12);
      while (currentGrantDate > referenceDate) currentGrantDate = addMonths(currentGrantDate, -12);
    }

    const statutoryGrantDays = eligibleByAttendance ? GRANT_TABLE[scheduleGroup][stage] : 0;
    const remainingDays = Math.max(0, statutoryGrantDays - daysTaken);
    const mandatoryFiveApplies = statutoryGrantDays >= 10;
    const mandatoryFiveRemaining = mandatoryFiveApplies ? Math.max(0, 5 - Math.min(daysTaken, 5)) : 0;
    const nextGrantDate = addMonths(currentGrantDate, 12);
    const expiryDate = addDays(addMonths(currentGrantDate, 24), -1);

    return {
      ok: true,
      beforeFirstGrant: false,
      scheduleGroup,
      fullTimeEquivalent: scheduleGroup === 'full',
      eligibleByAttendance,
      statutoryGrantDays,
      firstGrantDays: GRANT_TABLE[scheduleGroup][0],
      firstGrantDate: formatDate(firstGrantDate),
      currentGrantDate: formatDate(currentGrantDate),
      nextGrantDate: formatDate(nextGrantDate),
      daysUntilNextGrant: diffDays(nextGrantDate, referenceDate),
      expiryDate: formatDate(expiryDate),
      remainingDays,
      mandatoryFiveApplies,
      mandatoryFiveRemaining,
      stage,
      errors: []
    };
  }

  return {
    GRANT_TABLE,
    parseDate,
    formatDate,
    addMonths,
    resolveScheduleGroup,
    calculatePaidLeave
  };
});
'''

PAID_LEAVE_SCRIPT = r'''document.addEventListener('DOMContentLoaded', function () {
  'use strict';
  const form = document.getElementById('paid-leave-form');
  if (!form || !window.ImaikuraPaidLeave) return;

  const scheduleMode = document.getElementById('schedule-mode');
  const weeklyWrap = document.getElementById('weekly-days-wrap');
  const annualWrap = document.getElementById('annual-days-wrap');
  const referenceDate = document.getElementById('reference-date');
  const result = document.getElementById('paid-leave-result');
  const errorBox = document.getElementById('paid-leave-errors');
  const nf = new Intl.NumberFormat('ja-JP', { maximumFractionDigits: 1 });

  if (!referenceDate.value) {
    const today = new Date();
    referenceDate.value = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`;
  }

  function updateScheduleMode() {
    const annual = scheduleMode.value === 'annual';
    weeklyWrap.hidden = annual;
    annualWrap.hidden = !annual;
    document.getElementById('weekly-days').disabled = annual;
    document.getElementById('annual-days').disabled = !annual;
  }

  function jpDate(value) {
    if (!value) return '—';
    const parts = value.split('-');
    return `${Number(parts[0])}年${Number(parts[1])}月${Number(parts[2])}日`;
  }

  function showErrors(errors) {
    errorBox.innerHTML = `<strong>入力内容を確認してください</strong><ul>${errors.map((item) => `<li>${item}</li>`).join('')}</ul>`;
    errorBox.hidden = false;
    result.hidden = true;
    errorBox.focus();
  }

  scheduleMode.addEventListener('change', updateScheduleMode);
  updateScheduleMode();

  form.addEventListener('submit', function (event) {
    event.preventDefault();
    errorBox.hidden = true;
    const data = new FormData(form);
    const calculated = window.ImaikuraPaidLeave.calculatePaidLeave({
      hireDate: data.get('hireDate'),
      referenceDate: data.get('referenceDate'),
      scheduleMode: data.get('scheduleMode'),
      weeklyDays: data.get('weeklyDays'),
      annualDays: data.get('annualDays'),
      weeklyHours: data.get('weeklyHours'),
      attendanceRate: data.get('attendanceRate'),
      daysTaken: data.get('daysTaken')
    });

    if (!calculated.ok) {
      showErrors(calculated.errors);
      return;
    }

    const groupLabel = calculated.fullTimeEquivalent
      ? '通常の付与日数（週5日以上または週30時間以上）'
      : `比例付与（週${calculated.scheduleGroup}日相当）`;
    const attendanceText = calculated.eligibleByAttendance
      ? '出勤率80％以上として判定'
      : '出勤率80％未満のため、法定の付与要件を満たさない判定';

    if (calculated.beforeFirstGrant) {
      result.innerHTML = `
        <div class="result-eyebrow">初回付与前</div>
        <h2>次の法定付与日は ${jpDate(calculated.nextGrantDate)}</h2>
        <div class="result-grid paid-leave-result-grid">
          <div><span>初回の法定付与</span><strong>${nf.format(calculated.firstGrantDays)}日</strong></div>
          <div><span>付与日まで</span><strong>${nf.format(calculated.daysUntilNextGrant)}日</strong></div>
          <div><span>判定区分</span><strong class="result-small">${groupLabel}</strong></div>
        </div>
        <p class="result-note">${attendanceText}。会社が基準日を統一している場合や前倒し付与をしている場合は、就業規則・勤怠システムの付与日を優先してください。</p>`;
    } else {
      const mandatory = calculated.mandatoryFiveApplies
        ? `<strong>${nf.format(calculated.mandatoryFiveRemaining)}日</strong><small>年5日取得義務の残り目安</small>`
        : '<strong>対象外</strong><small>今回の法定付与が10日未満</small>';
      result.innerHTML = `
        <div class="result-eyebrow">法定付与日数の目安</div>
        <h2>${nf.format(calculated.statutoryGrantDays)}日</h2>
        <div class="result-grid paid-leave-result-grid">
          <div><span>今回の付与日</span><strong class="result-small">${jpDate(calculated.currentGrantDate)}</strong></div>
          <div><span>取得後の残り</span><strong>${nf.format(calculated.remainingDays)}日</strong></div>
          <div><span>次回付与日</span><strong class="result-small">${jpDate(calculated.nextGrantDate)}</strong></div>
          <div><span>今回分の時効目安</span><strong class="result-small">${jpDate(calculated.expiryDate)}</strong></div>
          <div class="result-wide"><span>年5日取得義務</span>${mandatory}</div>
        </div>
        <p class="result-note">${groupLabel}・${attendanceText}。残日数は「今回の付与分だけ」から入力した取得日数を差し引いた値です。前年繰越分、会社独自の上乗せ、時間単位年休は含みません。</p>`;
    }
    result.hidden = false;
    result.focus();
    if (typeof window.gtag === 'function') window.gtag('event', 'calculate_paid_leave', { schedule_group: calculated.scheduleGroup });
  });
});
'''

CSS_PATCH = r'''

/* layout-quality-v3: shared alignment, clipping and responsive safeguards */
:root {
  --content-max: 1180px;
  --page-gutter: clamp(18px, 3.2vw, 34px);
  --control-height: 48px;
}

*, *::before, *::after { box-sizing: border-box; }
html { overflow-x: clip; }
body {
  min-width: 320px;
  overflow-wrap: break-word;
  word-break: normal;
  line-break: strict;
}
.container,
.header-inner {
  width: min(calc(100% - (var(--page-gutter) * 2)), var(--content-max));
  margin-inline: auto;
}
.header-inner,
.hero-inner,
.section-head,
.brand,
.nav,
.share-actions {
  min-width: 0;
}
.brand { align-items: center; }
.brand > span:last-child { min-width: 0; }
.brand-mark {
  width: 44px;
  height: 44px;
  flex: 0 0 44px;
  padding: 0;
  display: grid;
  place-items: center;
  line-height: 1;
  text-align: center;
}
.hero-inner > *,
.tool-grid > *,
.tips-grid > *,
.comparison-grid > *,
.form-grid > *,
.result-grid > *,
.steps > * { min-width: 0; }
h1, h2, h3 { text-wrap: balance; }
p, li, summary, label { text-wrap: pretty; }
.tool-card {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: stretch;
}
.tool-card .card-link { margin-top: auto; padding-top: 16px; }
.tool-no,
.trust-badge,
.result-eyebrow,
.badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  text-align: center;
  line-height: 1.35;
  overflow-wrap: anywhere;
}
input,
select,
textarea,
button,
.button,
.btn {
  max-width: 100%;
  font: inherit;
}
input,
select,
textarea { width: 100%; }
button,
.button,
.btn {
  min-height: var(--control-height);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  text-align: center;
  white-space: normal;
}
button:focus-visible,
.button:focus-visible,
.btn:focus-visible,
a:focus-visible,
input:focus-visible,
select:focus-visible,
textarea:focus-visible,
summary:focus-visible {
  outline: 3px solid currentColor;
  outline-offset: 3px;
}
.table-wrap {
  max-width: 100%;
  overflow-x: auto;
  overscroll-behavior-inline: contain;
  -webkit-overflow-scrolling: touch;
}
.table-wrap table { min-width: 680px; }
.field-help { margin-top: 7px; font-size: .84rem; color: var(--muted, #5c6670); line-height: 1.65; }
.inline-fields { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; }
.mode-panel[hidden] { display: none !important; }
.error-box {
  margin-top: 18px;
  padding: 18px 20px;
  border: 1px solid #b74a3a;
  border-radius: 12px;
  background: #fff7f5;
  color: #6f2016;
}
.error-box ul { margin: 8px 0 0; padding-left: 1.25em; }
.paid-leave-result-grid .result-small { font-size: clamp(.92rem, 2vw, 1.08rem); line-height: 1.45; }
.paid-leave-result-grid .result-wide { grid-column: 1 / -1; }
.paid-leave-result-grid small { display: block; margin-top: 4px; font-size: .78rem; font-weight: 500; color: var(--muted, #5c6670); }
.result-note { margin-top: 18px; line-height: 1.8; }
.source-list a { overflow-wrap: anywhere; }

@media (max-width: 760px) {
  .header-inner { align-items: flex-start; gap: 12px; }
  .nav { width: 100%; display: flex; flex-wrap: wrap; gap: 8px 12px; }
  .nav a { min-height: 40px; display: inline-flex; align-items: center; }
  .hero-inner { align-items: flex-start; }
  .trust-badge { max-width: 100%; }
  .inline-fields { grid-template-columns: 1fr; }
  .paid-leave-result-grid .result-wide { grid-column: auto; }
}

@media (max-width: 420px) {
  :root { --page-gutter: 16px; }
  .brand-mark { width: 40px; height: 40px; flex-basis: 40px; }
  .tool-card, .content-card { border-radius: 14px; }
  .share-actions > * { width: 100%; }
}

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    scroll-behavior: auto !important;
    animation-duration: .01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: .01ms !important;
  }
}
'''

PACKAGE_JSON = '''{
  "name": "imaikura-quality-checks",
  "private": true,
  "version": "1.0.0",
  "scripts": {
    "test:visual": "playwright test tests/visual-smoke.spec.js --reporter=line"
  },
  "devDependencies": {
    "@playwright/test": "1.55.0"
  }
}
'''

PLAYWRIGHT_CONFIG = '''const { defineConfig } = require('@playwright/test');
module.exports = defineConfig({
  testDir: './tests',
  timeout: 90_000,
  expect: { timeout: 10_000 },
  retries: 1,
  workers: 1,
  use: {
    baseURL: 'http://127.0.0.1:4173',
    locale: 'ja-JP',
    timezoneId: 'Asia/Tokyo',
    reducedMotion: 'reduce'
  },
  reporter: [['line']],
  outputDir: 'test-results'
});
'''

VISUAL_TEST = r'''const { test, expect } = require('@playwright/test');

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
  await page.fill('#hire-date', '2024-04-01');
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
'''


def head(title: str, description: str, canonical: str, og_title: str, og_description: str, schema: list[dict]) -> str:
    scripts = ''.join(f'<script type="application/ld+json">{json.dumps(item, ensure_ascii=False, separators=(",", ":"))}</script>' for item in schema)
    return f'''<head>
<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={PUBLISHER}" crossorigin="anonymous"></script>
<meta name="google-adsense-account" content="{PUBLISHER}">
<script async src="https://www.googletagmanager.com/gtag/js?id=G-CSRJVE9RYK"></script>
<script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments)}}gtag('js',new Date());gtag('config','G-CSRJVE9RYK');</script>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="index,follow,max-image-preview:large">
<title>{html.escape(title)}</title><meta name="description" content="{html.escape(description, quote=True)}">
<link rel="canonical" href="{canonical}"><link rel="icon" type="image/svg+xml" href="../assets/favicon.svg"><link rel="alternate" type="application/rss+xml" title="いまいくら 更新フィード" href="{SITE}/feed.xml">
<meta property="og:site_name" content="いまいくら"><meta property="og:title" content="{html.escape(og_title, quote=True)}"><meta property="og:description" content="{html.escape(og_description, quote=True)}"><meta property="og:type" content="website"><meta property="og:locale" content="ja_JP"><meta property="og:url" content="{canonical}"><meta property="og:image" content="{SITE}/assets/og-default.png"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630"><meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="{html.escape(og_title, quote=True)}"><meta name="twitter:description" content="{html.escape(og_description, quote=True)}"><meta name="twitter:image" content="{SITE}/assets/og-default.png">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500;600;700;800&display=swap" rel="stylesheet"><link rel="stylesheet" href="../assets/site.css">
{scripts}
</head>'''


def header(active: str = '') -> str:
    def current(name: str) -> str:
        return ' aria-current="page"' if active == name else ''
    return f'''<header class="site-header"><div class="header-inner"><a class="brand" href="../" aria-label="いまいくら トップ"><span class="brand-mark">円</span><span>いまいくら <small>お金・税金・仕事の計算</small></span></a><nav class="nav" aria-label="メインナビゲーション"><a href="../"{current('tools')}>ツール一覧</a><a href="../guides/"{current('guides')}>制度ガイド</a><a href="../help/"{current('help')}>使い方・FAQ</a></nav></div></header>'''


def footer() -> str:
    return '''<footer class="site-footer"><div class="container footer-grid"><div><a class="brand footer-brand" href="../"><span class="brand-mark">円</span><span>いまいくら <small>日本のお金と仕事を、数字で確かめる。</small></span></a><p>計算結果は制度理解のための概算です。申告、契約、労務判断では勤務先・所管機関・専門家の確認を優先してください。</p></div><nav aria-label="フッターナビゲーション"><a href="../guides/">制度ガイド</a><a href="../help/">使い方・FAQ</a><a href="../about/">運営者情報</a><a href="../contact/">お問い合わせ</a><a href="../updates/">更新履歴</a><a href="../site-map/">サイトマップ</a><a href="../privacy/">プライバシー</a><a href="../terms/">利用規約</a></nav></div><div class="container footer-bottom"><small>© 2026 いまいくら</small></div></footer><script src="../assets/share.js" defer></script>'''


def breadcrumb(current: str, url: str) -> dict:
    return {'@context':'https://schema.org','@type':'BreadcrumbList','itemListElement':[
        {'@type':'ListItem','position':1,'name':'ホーム','item':f'{SITE}/'},
        {'@type':'ListItem','position':2,'name':current,'item':url}
    ]}


def publisher() -> dict:
    return {'@type':'Organization','name':'いまいくら','url':f'{SITE}/','logo':{'@type':'ImageObject','url':f'{SITE}/assets/logo.svg','contentUrl':f'{SITE}/assets/logo.svg','width':512,'height':512}}


faq_items = [
    ('パートでも週30時間以上なら比例付与ですか？','週の所定労働時間が30時間以上であれば、週の所定労働日数が4日以下でも通常の付与日数で判定します。会社の所定労働時間や契約変更の時期も確認してください。'),
    ('出勤率80％はどう数えますか？','原則として、算定期間の全労働日に対する出勤日の割合です。業務上のけがによる休業、産前産後休業、育児・介護休業などは出勤したものとして扱われる場合があります。個別の勤怠区分は勤務先へ確認してください。'),
    ('有給休暇は翌年に繰り越せますか？','法定年休の請求権は原則2年で時効となるため、未取得分は翌年度へ繰り越せます。ただし会社が法定より有利な保存期間を定めていることもあります。'),
    ('年5日の取得義務はパートにもありますか？','雇用形態ではなく、その年に10日以上の年次有給休暇が付与されるかで決まります。比例付与でも勤続年数が長く10日以上になれば対象です。'),
    ('会社の付与日と計算結果が違います。','基準日を全社員で統一する一斉付与、入社日に前倒しする分割付与、法定を上回る独自制度では日付や日数が異なります。実際の残日数は就業規則、労働条件通知書、勤怠システムを優先してください。')
]
faq_schema = {'@context':'https://schema.org','@type':'FAQPage','mainEntity':[{'@type':'Question','name':q,'acceptedAnswer':{'@type':'Answer','text':a}} for q,a in faq_items]}

calc_url = f'{SITE}/paid-leave/'
calc_title = '有給休暇日数計算 2026｜パートの比例付与・年5日義務｜いまいくら'
calc_description = '入社日、週または年間の所定労働日数、週の労働時間、出勤率から、年次有給休暇の法定付与日数、次回付与日、残日数、年5日取得義務の対象を確認できます。パート・アルバイトの比例付与にも対応します。'
calc_schema = [
    {'@context':'https://schema.org','@type':'WebApplication','name':'有給休暇日数計算','url':calc_url,'applicationCategory':'BusinessApplication','operatingSystem':'Any','inLanguage':'ja','isAccessibleForFree':True,'description':calc_description,'offers':{'@type':'Offer','price':'0','priceCurrency':'JPY'},'publisher':publisher()},
    breadcrumb('有給休暇日数計算', calc_url),
    faq_schema
]

calc_html = f'''<!doctype html><html lang="ja">{head(calc_title,calc_description,calc_url,'有給休暇日数計算 2026','入社日と勤務日数から、法定付与日数・残日数・年5日取得義務を確認。',calc_schema)}<body>{header('tools')}<main>
<section class="hero"><div class="container hero-inner"><div><div class="kicker">PAID LEAVE</div><h1>有給休暇は<br>何日もらえる？</h1><p class="lead">入社日と働き方から、労働基準法上の付与日数を確認します。週5日未満のパート・アルバイトの比例付与にも対応しています。</p></div><div class="trust-badge">労働基準法 第39条</div></div></section>
<nav class="breadcrumbs container" aria-label="パンくずリスト"><a href="../">ホーム</a><span aria-hidden="true">›</span><span aria-current="page">有給休暇日数計算</span></nav>
<div class="container main">
<section class="content-section content-card"><div class="section-head"><div><div class="kicker">CALCULATOR</div><h2>法定付与日数を確認</h2></div><p>入力値は端末内で計算され、保存されません。</p></div>
<form id="paid-leave-form" novalidate>
<div class="form-grid">
<label class="field"><span>入社日</span><input id="hire-date" name="hireDate" type="date" required><small class="field-help">雇用契約が始まった日を入力します。</small></label>
<label class="field"><span>基準日</span><input id="reference-date" name="referenceDate" type="date" required><small class="field-help">現在または確認したい日を入力します。</small></label>
<label class="field"><span>勤務日数の入力方法</span><select id="schedule-mode" name="scheduleMode"><option value="weekly">週の所定労働日数</option><option value="annual">年間の所定労働日数</option></select><small class="field-help">週ごとに日数が決まらない場合は年間日数を選びます。</small></label>
<label class="field" id="weekly-days-wrap"><span>週の所定労働日数</span><select id="weekly-days" name="weeklyDays"><option value="5">週5日以上</option><option value="4">週4日</option><option value="3">週3日</option><option value="2">週2日</option><option value="1">週1日</option></select></label>
<label class="field mode-panel" id="annual-days-wrap" hidden><span>年間の所定労働日数</span><input id="annual-days" name="annualDays" type="number" min="1" max="366" step="1" value="169" disabled><small class="field-help">労働条件通知書や勤務表で確認してください。</small></label>
<label class="field"><span>週の所定労働時間</span><input id="weekly-hours" name="weeklyHours" type="number" min="0" max="80" step="0.5" value="40" required><small class="field-help">30時間以上なら通常の付与日数で判定します。</small></label>
<label class="field"><span>算定期間の出勤率</span><div class="input-with-unit"><input id="attendance-rate" name="attendanceRate" type="number" min="0" max="100" step="0.1" value="100" required><span>％</span></div><small class="field-help">不明なら勤怠担当者へ確認してください。法定要件は原則80％以上です。</small></label>
<label class="field"><span>今回の付与後に取得した日数</span><div class="input-with-unit"><input id="days-taken" name="daysTaken" type="number" min="0" max="40" step="0.5" value="0"><span>日</span></div><small class="field-help">今回分だけの残りを簡易表示します。前年繰越分は含めません。</small></label>
</div>
<button id="calculate-paid-leave" class="primary-button" type="submit">付与日数を計算する</button>
</form>
<div id="paid-leave-errors" class="error-box" role="alert" tabindex="-1" hidden></div>
<div id="paid-leave-result" class="result-box" role="status" aria-live="polite" tabindex="-1" hidden></div>
</section>
<section class="content-section content-card"><h2>この計算で分かること</h2><div class="tips-grid"><div><b>今回の法定付与日数</b><p>勤続期間、所定労働日数、週の所定労働時間、出勤率から最低基準を判定します。</p></div><div><b>次回の付与日</b><p>入社6か月後を初回とし、その後1年ごとの基準日を表示します。</p></div><div><b>年5日取得義務</b><p>今回10日以上付与される場合、使用者による年5日の取得確保が必要か確認します。</p></div><div><b>今回分の時効目安</b><p>法定年休の請求権が原則2年で時効となることを前提に日付を表示します。</p></div></div></section>
<section class="content-section content-card"><h2>最初に確認したい3つの条件</h2><ol class="check-list"><li><strong>入社から6か月継続勤務しているか。</strong>初回は原則として入社6か月後です。</li><li><strong>算定期間の出勤率が8割以上か。</strong>育児休業など、出勤扱いとなる期間があります。</li><li><strong>週30時間以上、週5日以上、または年間217日以上か。</strong>いずれかに当てはまれば通常の付与表を使います。</li></ol><p class="plain-copy">会社が一斉付与や前倒し付与を採用していると、実際の付与日はこの計算と異なります。勤怠画面に残日数が表示されている場合は、そちらを優先してください。</p></section>
<section class="content-section content-card"><h2>比例付与の早見表</h2><p class="plain-copy">週30時間未満かつ週4日以下の人は、所定労働日数に応じて比例付与されます。表は法定の最低日数です。</p><div class="table-wrap"><table><thead><tr><th>週の所定労働日数</th><th>6か月</th><th>1年6か月</th><th>2年6か月</th><th>3年6か月</th><th>4年6か月</th><th>5年6か月</th><th>6年6か月以上</th></tr></thead><tbody><tr><th>5日以上・週30時間以上</th><td>10</td><td>11</td><td>12</td><td>14</td><td>16</td><td>18</td><td>20</td></tr><tr><th>4日</th><td>7</td><td>8</td><td>9</td><td>10</td><td>12</td><td>13</td><td>15</td></tr><tr><th>3日</th><td>5</td><td>6</td><td>6</td><td>8</td><td>9</td><td>10</td><td>11</td></tr><tr><th>2日</th><td>3</td><td>4</td><td>4</td><td>5</td><td>6</td><td>6</td><td>7</td></tr><tr><th>1日</th><td>1</td><td>2</td><td>2</td><td>2</td><td>3</td><td>3</td><td>3</td></tr></tbody></table></div></section>
<section class="content-section content-card"><h2>計算結果に含まれないもの</h2><ul class="check-list"><li>前年から繰り越した残日数と、古い付与分から消化する会社独自の順序</li><li>時間単位年休、半日年休、計画年休、特別休暇</li><li>一斉付与、分割付与、入社時付与など会社独自の基準日</li><li>休職、産前産後休業、育児・介護休業、業務災害休業などの出勤率上の扱い</li><li>退職日までの時季変更権や、長期休暇申請に関する個別判断</li></ul></section>
<section class="content-section"><h2>よくある質問</h2>{''.join(f'<details class="faq"><summary>{html.escape(q)}</summary><p>{html.escape(a)}</p></details>' for q,a in faq_items)}</section>
<section class="content-section content-card"><h2>参照した公的資料</h2><ul class="source-list"><li><a href="https://elaws.e-gov.go.jp/document?lawid=322AC0000000049" rel="noopener noreferrer">e-Gov法令検索「労働基準法」第39条・第115条</a></li><li><a href="https://work-holiday.mhlw.go.jp/" rel="noopener noreferrer">厚生労働省「働き方・休み方改善ポータルサイト」</a></li><li><a href="https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/0000148322.html" rel="noopener noreferrer">厚生労働省「年次有給休暇の取得促進」</a></li></ul><p class="plain-copy">最終確認日：2026年9月5日　作成・編集：いまいくら編集部。制度の読み違い、リンク切れ、計算例の誤りは<a href="../contact/">訂正窓口</a>からお知らせください。</p></section>
<section class="content-section share-box" data-share-box aria-labelledby="share-title"><h2 id="share-title">この計算ツールを共有</h2><p>入社日や勤務日数を送らず、ページURLだけを共有できます。</p><div class="share-actions"><button type="button" data-share-native>共有</button><a data-share-line href="#">LINE</a><a data-share-x href="#">X</a><button type="button" data-share-copy>URLをコピー</button></div><p class="share-status" data-share-status aria-live="polite"></p></section>
</div></main>{footer()}<script src="../assets/paid-leave-engine.js"></script><script src="../assets/paid-leave.js"></script></body></html>'''

guide_url = f'{SITE}/paid-leave-guide/'
guide_title = '有給休暇は何日もらえる？付与日数・比例付与・年5日義務｜いまいくら'
guide_description = '年次有給休暇が入社6か月後に何日付与されるか、パート・アルバイトの比例付与、出勤率8割、年5日の取得義務、2年の時効、一斉付与との違いを具体例と法定表で解説します。'
guide_schema = [
    {'@context':'https://schema.org','@type':'Article','headline':'有給休暇は何日もらえる？付与日数・比例付与・年5日義務','description':guide_description,'url':guide_url,'datePublished':TODAY,'dateModified':TODAY,'inLanguage':'ja','author':publisher(),'publisher':publisher(),'image':{'@type':'ImageObject','url':f'{SITE}/assets/og-default.png','contentUrl':f'{SITE}/assets/og-default.png','width':1200,'height':630},'mainEntityOfPage':guide_url},
    breadcrumb('有給休暇の付与日数ガイド',guide_url),
    faq_schema
]

guide_html = f'''<!doctype html><html lang="ja">{head(guide_title,guide_description,guide_url,'有給休暇は何日もらえる？','通常付与、パートの比例付与、出勤率8割、年5日義務を具体的に解説。',guide_schema)}<body>{header('guides')}<main>
<section class="hero"><div class="container hero-inner"><div><div class="kicker">GUIDE</div><h1>有給休暇は何日もらえる？<br>付与日数を順番に確認</h1><p class="lead">「半年働けば10日」は多くの人に当てはまりますが、週の勤務日数、週30時間、出勤率、一斉付与によって見方が変わります。</p></div><div class="trust-badge">2026年9月確認</div></div></section>
<nav class="breadcrumbs container" aria-label="パンくずリスト"><a href="../">ホーム</a><span aria-hidden="true">›</span><a href="../guides/">制度ガイド</a><span aria-hidden="true">›</span><span aria-current="page">有給休暇</span></nav>
<article class="container main">
<section class="content-section content-card"><div class="article-meta"><span>作成・編集：いまいくら編集部</span><span>最終確認：2026年9月5日</span><span>根拠：労働基準法第39条</span></div><h2>まず結論：週5日勤務なら半年後に10日</h2><p class="plain-copy">入社から6か月継続して勤務し、その期間の全労働日の8割以上を出勤した人には、原則10日の年次有給休暇が付与されます。その後は1年ごとに11日、12日、14日、16日、18日と増え、6年6か月以上では毎年20日です。</p><p class="plain-copy">ここでいう10日は正社員だけの数字ではありません。名称がパートやアルバイトでも、週5日以上働く人、週の所定労働時間が30時間以上の人、年間所定労働日数が217日以上の人は通常の付与表で扱います。</p><p><a class="button" href="../paid-leave/">入社日から付与日数を計算する</a></p></section>
<section class="content-section content-card"><h2>通常の付与日数</h2><div class="table-wrap"><table><thead><tr><th>継続勤務期間</th><th>6か月</th><th>1年6か月</th><th>2年6か月</th><th>3年6か月</th><th>4年6か月</th><th>5年6か月</th><th>6年6か月以上</th></tr></thead><tbody><tr><th>法定付与日数</th><td>10日</td><td>11日</td><td>12日</td><td>14日</td><td>16日</td><td>18日</td><td>20日</td></tr></tbody></table></div><p class="plain-copy">例えば2026年4月1日入社なら、法定上の初回付与日は原則2026年10月1日です。会社が4月1日を全社共通の基準日にしている場合は、入社日に一部を前倒しし、次の基準日で残りを付与することがあります。</p></section>
<section class="content-section content-card"><h2>週4日以下・週30時間未満は比例付与</h2><p class="plain-copy">所定労働日数が少ない人にも年休はあります。ただし週30時間未満で、週4日以下または年間216日以下の場合、日数は比例付与表で決まります。</p><div class="table-wrap"><table><thead><tr><th>週の所定日数<br><small>年間日数の目安</small></th><th>6か月</th><th>1年6か月</th><th>2年6か月</th><th>3年6か月</th><th>4年6か月</th><th>5年6か月</th><th>6年6か月以上</th></tr></thead><tbody><tr><th>4日<br><small>169〜216日</small></th><td>7</td><td>8</td><td>9</td><td>10</td><td>12</td><td>13</td><td>15</td></tr><tr><th>3日<br><small>121〜168日</small></th><td>5</td><td>6</td><td>6</td><td>8</td><td>9</td><td>10</td><td>11</td></tr><tr><th>2日<br><small>73〜120日</small></th><td>3</td><td>4</td><td>4</td><td>5</td><td>6</td><td>6</td><td>7</td></tr><tr><th>1日<br><small>48〜72日</small></th><td>1</td><td>2</td><td>2</td><td>2</td><td>3</td><td>3</td><td>3</td></tr></tbody></table></div><p class="plain-copy">週3日・週18時間の人が6か月間の出勤率を満たした場合は5日です。同じ週3日でも週30時間以上なら比例付与ではなく10日になります。</p></section>
<section class="content-section content-card"><h2>出勤率8割の数え方</h2><p class="plain-copy">出勤率は、付与日前の算定期間における全労働日に対する出勤日の割合です。単純に「暦日から休んだ日を引く」のではありません。会社が労働日と定めた日を分母にし、実際に出勤した日を分子にします。</p><p class="plain-copy">業務上の負傷・疾病による休業、産前産後休業、育児・介護休業などは、法律上出勤したものとして扱われる場面があります。遅刻や早退を欠勤1日として扱えるかも一律ではないため、勤怠システムの表示だけで8割未満と決めつけず、勤務先の算定方法を確認します。</p></section>
<section class="content-section content-card"><h2>10日以上付与された人は「年5日」の対象</h2><p class="plain-copy">法定年休が10日以上付与される労働者について、使用者は付与日から1年以内に5日を取得させる必要があります。正社員かパートかではなく、付与日数で判断します。</p><p class="plain-copy">本人が時季を指定して取得した日、労使協定による計画年休の日は5日に算入できます。すでに5日以上取得していれば、使用者が追加で時季指定する必要はありません。反対に、忙しいことを理由に本人へ取得を諦めさせる運用は制度の趣旨に合いません。</p></section>
<section class="content-section content-card"><h2>残日数は「新しい分だけ」で見ない</h2><p class="plain-copy">未取得の法定年休は原則として翌年度へ繰り越せます。請求権の時効は原則2年です。そのため実際の残日数は、前年からの繰越分と今回の付与分を合計して表示されるのが一般的です。</p><p class="plain-copy">どちらの付与分から先に消化するかは就業規則やシステム設定で異なります。古い分から消化すれば失効を避けやすい一方、会社が新しい分から消化する規定を置く場合もあるため、残日数だけでなく「付与日別の内訳」を確認すると安心です。</p></section>
<section class="content-section content-card"><h2>会社の表示と計算結果が違う主な理由</h2><div class="comparison-grid"><div><h3>一斉付与</h3><p>全社員の付与日を4月1日などにそろえ、入社時期に応じて前倒しや按分を行う制度です。</p></div><div><h3>分割付与</h3><p>入社日に5日、6か月後に5日など、法定日数を分けて先に付与する運用です。</p></div><div><h3>法定以上の制度</h3><p>初日から10日、保存期間3年など、法律より有利な条件を会社が定めることがあります。</p></div><div><h3>勤務条件の変更</h3><p>週3日から週5日へ変わった場合など、どの時点の所定労働日数を使うか確認が必要です。</p></div></div></section>
<section class="content-section"><h2>よくある質問</h2>{''.join(f'<details class="faq"><summary>{html.escape(q)}</summary><p>{html.escape(a)}</p></details>' for q,a in faq_items)}</section>
<section class="content-section content-card"><h2>確認するときの順番</h2><ol class="check-list"><li>労働条件通知書で週の所定労働日数・時間を確認する。</li><li>勤怠システムで付与日別の残日数と失効予定日を見る。</li><li>就業規則で一斉付与、分割付与、時間単位年休の有無を確認する。</li><li>表示が法定表を下回る場合は人事・労務担当へ算定根拠を尋ねる。</li><li>解決しない場合は都道府県労働局の総合労働相談コーナーや労働基準監督署へ相談する。</li></ol></section>
<section class="content-section content-card"><h2>公的資料</h2><ul class="source-list"><li><a href="https://elaws.e-gov.go.jp/document?lawid=322AC0000000049" rel="noopener noreferrer">e-Gov法令検索「労働基準法」</a></li><li><a href="https://work-holiday.mhlw.go.jp/" rel="noopener noreferrer">厚生労働省「働き方・休み方改善ポータルサイト」</a></li><li><a href="https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/0000148322.html" rel="noopener noreferrer">厚生労働省「年次有給休暇の取得促進」</a></li></ul><p class="plain-copy">本記事は一般的な法定最低基準を整理したものです。個別の勤怠認定や就業規則の適法性を判断する法律相談ではありません。誤りを見つけた場合は<a href="../contact/">訂正窓口</a>へお知らせください。</p></section>
<section class="content-section share-box" data-share-box aria-labelledby="share-title"><h2 id="share-title">このガイドを共有</h2><p>勤務条件などの個人情報を含めず、ページURLだけを共有できます。</p><div class="share-actions"><button type="button" data-share-native>共有</button><a data-share-line href="#">LINE</a><a data-share-x href="#">X</a><button type="button" data-share-copy>URLをコピー</button></div><p class="share-status" data-share-status aria-live="polite"></p></section>
</article></main>{footer()}</body></html>'''


def write(path: str, content: str) -> None:
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding='utf-8')


write('assets/paid-leave-engine.js', ENGINE)
write('assets/paid-leave.js', PAID_LEAVE_SCRIPT)
write('paid-leave/index.html', calc_html)
write('paid-leave-guide/index.html', guide_html)
write('package.json', PACKAGE_JSON)
write('playwright.config.js', PLAYWRIGHT_CONFIG)
write('tests/visual-smoke.spec.js', VISUAL_TEST)

css_path = ROOT / 'assets/site.css'
css = css_path.read_text(encoding='utf-8')
if 'layout-quality-v3' not in css:
    css += CSS_PATCH
css_path.write_text(css, encoding='utf-8')


def append_home_card() -> None:
    path = ROOT / 'index.html'
    soup = BeautifulSoup(path.read_text(encoding='utf-8'), 'html.parser')
    if soup.select_one('a[href="paid-leave/"]'):
        return
    grids = [grid for grid in soup.select('.tool-grid') if grid.select('[data-search]')]
    if not grids:
        raise RuntimeError('home tool grid not found')
    card = BeautifulSoup('''<a class="tool-card" data-search="有給休暇 年次有給休暇 付与日数 パート アルバイト 比例付与 年5日 年休 paid leave" href="paid-leave/"><span class="tool-no">16</span><h2>有給休暇日数</h2><p>入社日と勤務日数から、法定付与日数・次回付与日・年5日取得義務を確認。</p><span class="card-link">計算する</span></a>''','html.parser').a
    grids[0].append(card)
    card_count = len(soup.select('[data-search]'))
    text = str(soup)
    text = re.sub(r'現在\s*\d+ツール・\d+ガイド公開中', lambda m: m.group(0), text)
    path.write_text(text, encoding='utf-8')


append_home_card()


def patch_guides() -> int:
    path = ROOT / 'guides/index.html'
    soup = BeautifulSoup(path.read_text(encoding='utf-8'), 'html.parser')
    if not soup.select_one('a[href="../paid-leave-guide/"]'):
        target = None
        for section in soup.select('section'):
            heading = section.find(['h2','h3'])
            if heading and any(key in heading.get_text() for key in ('給与','働き方','社会保険')):
                target = section.select_one('.tool-grid')
                if target: break
        if not target:
            target = soup.select_one('.tool-grid')
        if not target:
            raise RuntimeError('guide grid not found')
        card = BeautifulSoup('''<a class="tool-card" href="../paid-leave-guide/"><h2>有給休暇は何日もらえる？</h2><p>通常付与、パートの比例付与、出勤率8割、年5日取得義務を整理。</p><span class="card-link">ガイドを読む</span></a>''','html.parser').a
        target.append(card)
    scripts = soup.find_all('script', attrs={'type':'application/ld+json'})
    for script in scripts:
        try: data = json.loads(script.string or '')
        except Exception: continue
        if data.get('@type') == 'CollectionPage' and isinstance(data.get('mainEntity'), dict):
            entity = data['mainEntity']
            items = entity.setdefault('itemListElement', [])
            if not any(x.get('url') == guide_url for x in items if isinstance(x,dict)):
                items.append({'@type':'ListItem','position':len(items)+1,'name':'有給休暇は何日もらえる？','url':guide_url})
            for pos,item in enumerate(items,1): item['position']=pos
            entity['numberOfItems']=len(items)
            script.string=json.dumps(data,ensure_ascii=False,separators=(',',':'))
    total = len(soup.select('.tool-grid a.tool-card'))
    content = str(soup)
    content = re.sub(r'14本の制度ガイド', f'{total}本の制度ガイド', content)
    content = re.sub(r'14本のガイド', f'{total}本のガイド', content)
    content = re.sub(r'制度を公的資料から解説する14本', f'制度を公的資料から解説する{total}本', content)
    path.write_text(content, encoding='utf-8')
    return total


guide_count_from_hub = patch_guides()


def patch_site_map() -> None:
    path = ROOT / 'site-map/index.html'
    soup = BeautifulSoup(path.read_text(encoding='utf-8'), 'html.parser')
    main = soup.find('main') or soup.body
    if not soup.select_one('a[href="../paid-leave/"]'):
        section = soup.new_tag('section', attrs={'class':'content-section content-card'})
        h2 = soup.new_tag('h2'); h2.string = '休暇・働き方'
        section.append(h2)
        p1 = soup.new_tag('p'); a1 = soup.new_tag('a', href='../paid-leave/'); a1.string='有給休暇日数計算'; p1.append(a1); p1.append(' — 入社日と勤務日数から法定付与日数を確認')
        p2 = soup.new_tag('p'); a2 = soup.new_tag('a', href='../paid-leave-guide/'); a2.string='有給休暇の付与日数ガイド'; p2.append(a2); p2.append(' — 比例付与・年5日取得義務・時効を解説')
        section.extend([p1,p2])
        container = main.select_one('.container.main') if hasattr(main,'select_one') else None
        (container or main).append(section)
    path.write_text(str(soup), encoding='utf-8')


patch_site_map()


def patch_updates() -> None:
    path = ROOT / 'updates/index.html'
    soup = BeautifulSoup(path.read_text(encoding='utf-8'), 'html.parser')
    if '有給休暇日数計算を公開' in soup.get_text():
        return
    main = soup.select_one('.container.main') or soup.find('main')
    section = BeautifulSoup('''<section class="content-section content-card"><div class="article-meta"><time datetime="2026-09-05">2026年9月5日</time><span>新規公開・品質改善</span></div><h2>有給休暇日数計算と制度ガイドを公開</h2><p class="plain-copy">入社日、勤務日数、週の労働時間、出勤率から、法定付与日数、次回付与日、年5日取得義務を確認できるツールを追加しました。同時に、全ページの左右余白、カード内の文字位置、ボタン・円形マークの中央揃え、モバイルの横はみ出しを継続検査するブラウザテストを導入しました。</p><p><a href="../paid-leave/">有給休暇日数を計算する</a>　<a href="../paid-leave-guide/">制度ガイドを読む</a></p></section>''','html.parser').section
    if main:
        first_section = main.find('section')
        if first_section: first_section.insert_before(section)
        else: main.append(section)
    path.write_text(str(soup), encoding='utf-8')


patch_updates()


def patch_home_counts(guide_count: int) -> tuple[int,int]:
    path = ROOT / 'index.html'
    text = path.read_text(encoding='utf-8')
    soup = BeautifulSoup(text, 'html.parser')
    tool_count = len(soup.select('[data-search]'))
    text = re.sub(r'現在\s*\d+ツール・\d+ガイド公開中', f'現在 {tool_count}ツール・{guide_count}ガイド公開中', text)
    text = re.sub(r'すべての制度ガイドを見る（\d+本）', f'すべての制度ガイドを見る（{guide_count}本）', text)
    path.write_text(text, encoding='utf-8')
    return tool_count,guide_count


tool_count,guide_count = patch_home_counts(guide_count_from_hub)


def patch_feed() -> None:
    path = ROOT / 'feed.xml'
    text = path.read_text(encoding='utf-8')
    if guide_url in text:
        return
    item = f'''\n    <item><title>有給休暇は何日もらえる？付与日数・比例付与・年5日義務</title><link>{guide_url}</link><guid isPermaLink="true">{guide_url}</guid><pubDate>Sat, 05 Sep 2026 15:30:00 +0000</pubDate><description>年次有給休暇の通常付与、パートの比例付与、出勤率8割、年5日取得義務、2年の時効を解説します。</description></item>'''
    pos = text.find('<item>')
    if pos == -1:
        pos = text.find('</channel>')
    text = text[:pos] + item + '\n    ' + text[pos:]
    path.write_text(text, encoding='utf-8')


patch_feed()


def rebuild_sitemap() -> int:
    old = {}
    path = ROOT / 'sitemap.xml'
    if path.exists():
        try:
            ns = {'s':'http://www.sitemaps.org/schemas/sitemap/0.9'}
            tree = ET.parse(path)
            for node in tree.findall('s:url',ns):
                loc = node.find('s:loc',ns)
                lm = node.find('s:lastmod',ns)
                if loc is not None and loc.text:
                    old[loc.text.strip()] = lm.text.strip() if lm is not None and lm.text else TODAY
        except Exception:
            pass
    urls=[]
    for page in sorted(ROOT.rglob('index.html')):
        rel = page.relative_to(ROOT)
        url = f'{SITE}/' if rel.as_posix() == 'index.html' else f'{SITE}/{rel.parent.as_posix()}/'
        urls.append(url)
    lines=['<?xml version="1.0" encoding="UTF-8"?>','<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for url in sorted(urls, key=lambda u:(u != f'{SITE}/',u)):
        lastmod = TODAY if url in (calc_url,guide_url) else old.get(url,TODAY)
        lines.append(f'  <url><loc>{url}</loc><lastmod>{lastmod}</lastmod></url>')
    lines.append('</urlset>')
    path.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    return len(urls)


page_count = rebuild_sitemap()


def update_quality_workflow() -> None:
    path = ROOT / '.github/workflows/site-quality.yml'
    text = path.read_text(encoding='utf-8')

    def update_list(name: str, value: str) -> None:
        nonlocal text
        match = re.search(rf'({name}\s*=\s*)(\[.*?\])', text, re.S)
        if not match:
            raise RuntimeError(f'{name} list not found')
        items = ast.literal_eval(match.group(2))
        if value not in items: items.append(value)
        indent = '          '
        formatted = '[\n' + ''.join(indent + '    ' + repr(item) + ',\n' for item in items) + indent + ']'
        text = text[:match.start(2)] + formatted + text[match.end(2):]

    update_list('calculators','paid-leave')
    update_list('guides','paid-leave-guide')
    text = re.sub(r"assert len\(urls\) == \d+ and len\(urls\) == len\(set\(urls\)\), len\(urls\)", "expected_count = 1 + len(calculators) + len(guides) + len(utility)\n          assert len(urls) == expected_count and len(urls) == len(set(urls)), len(urls)", text)
    text = re.sub(r"assert len\(pages\) == \d+, len\(pages\)", "assert len(pages) == expected_count, len(pages)", text)
    text = re.sub(r"assert len\(items\)==\d+", "assert len(items)==len(guides)", text)
    text = re.sub(r"assert home\.count\('data-search='\) == \d+", "assert home.count('data-search=') == len(calculators)", text)
    text = re.sub(r"assert 'すべての制度ガイドを見る（\d+本）' in home", "assert f'すべての制度ガイドを見る（{len(guides)}本）' in home", text)
    text = re.sub(r"assert '現在 \d+ツール・\d+ガイド公開中' in home", "assert f'現在 {len(calculators)}ツール・{len(guides)}ガイド公開中' in home", text)
    if "'package.json'" not in text.split('permissions:',1)[0]:
        text = text.replace("      - '.github/workflows/site-quality.yml'", "      - '.github/workflows/site-quality.yml'\n      - 'package.json'\n      - 'playwright.config.js'\n      - 'tests/**'")
    if 'browser-smoke:' not in text:
        text += '''\n  browser-smoke:\n    needs: audit\n    runs-on: ubuntu-latest\n    timeout-minutes: 20\n    steps:\n      - uses: actions/checkout@v4\n      - uses: actions/setup-node@v4\n        with:\n          node-version: '22'\n      - name: Install browser test dependencies\n        run: |\n          npm install --no-audit --no-fund\n          npx playwright install --with-deps chromium\n      - name: Start local site\n        run: |\n          python3 -m http.server 4173 --bind 127.0.0.1 > /tmp/imaikura-server.log 2>&1 &\n          echo $! > /tmp/imaikura-server.pid\n          for i in {1..20}; do curl -fsS http://127.0.0.1:4173/ >/dev/null && exit 0; sleep 1; done\n          cat /tmp/imaikura-server.log\n          exit 1\n      - name: Check every page and responsive alignment\n        run: npm run test:visual\n      - name: Upload visual evidence\n        if: always()\n        uses: actions/upload-artifact@v4\n        with:\n          name: visual-smoke-screenshots\n          path: test-results/\n          if-no-files-found: ignore\n          retention-days: 7\n'''
    path.write_text(text,encoding='utf-8')


update_quality_workflow()

# Make the number on the new home card follow the actual order.
home_path=ROOT/'index.html'
soup=BeautifulSoup(home_path.read_text(encoding='utf-8'),'html.parser')
for index,card in enumerate(soup.select('[data-search]'),1):
    number=card.select_one('.tool-no')
    if number: number.string=f'{index:02d}'
home_path.write_text(str(soup),encoding='utf-8')

print(json.dumps({'pages':page_count,'tools':tool_count,'guides':guide_count},ensure_ascii=False))
