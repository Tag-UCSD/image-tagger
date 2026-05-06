import { test, expect } from '@playwright/test';

/**
 * Verifies no horizontal scrollbar appears on the primary screen of each app
 * at a 360px viewport (common small-phone width).
 *
 * Build with VITE_USE_MOCKS=true before running so pages render without a
 * live backend:
 *   VITE_USE_MOCKS=true npm --prefix frontend run build
 *   npx playwright test frontend/tests/responsive.spec.ts
 */

const ROUTES: { name: string; path: string }[] = [
  { name: 'explorer',  path: '/' },
  { name: 'workbench', path: '/workbench/' },
  { name: 'monitor',   path: '/monitor/' },
  { name: 'admin',     path: '/admin/' },
];

for (const { name, path } of ROUTES) {
  test(`no horizontal scroll at 360 px — ${name}`, async ({ page }) => {
    await page.goto(path);
    // Wait for the app shell to paint (avoids false-positives during loading).
    await page.waitForLoadState('domcontentloaded');

    const overflows = await page.evaluate(() => {
      // Check every element for overflow that would cause a horizontal scrollbar.
      const offenders: string[] = [];
      document.querySelectorAll('*').forEach((el) => {
        const rect = el.getBoundingClientRect();
        if (rect.width > document.documentElement.clientWidth + 1) {
          offenders.push(`${el.tagName.toLowerCase()}${el.id ? '#' + el.id : ''}${el.className ? '.' + String(el.className).trim().split(/\s+/).join('.') : ''}`);
        }
      });
      return offenders.slice(0, 5); // return up to 5 for diagnostics
    });

    expect(
      overflows,
      `Elements wider than viewport on ${name}: ${overflows.join(', ')}`,
    ).toHaveLength(0);
  });
}
