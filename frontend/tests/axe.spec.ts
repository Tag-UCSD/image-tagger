import { test } from '@playwright/test';
import { injectAxe, checkA11y } from 'axe-playwright';

const routes = [
  { name: 'explorer', path: '/' },
  { name: 'workbench', path: '/workbench/' },
  { name: 'monitor', path: '/monitor/' },
  { name: 'admin', path: '/admin/' },
];

for (const { name, path } of routes) {
  test(`zero critical/serious violations — ${name}`, async ({ page }) => {
    await page.goto(path);
    await page.waitForLoadState('networkidle');
    await injectAxe(page);
    await checkA11y(page, undefined, {
      includedImpacts: ['critical', 'serious'],
    });
  });
}
