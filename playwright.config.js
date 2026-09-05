const { defineConfig } = require('@playwright/test');
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
