import { test, expect } from '@playwright/test';

/**
 * C2-10: Workplan 2 GUI state tests.
 *
 * Requires a mock-enabled build before running:
 *   VITE_USE_MOCKS=true npm --prefix frontend run build
 *   npm --prefix frontend run test:wp2
 *
 * All tests run against the static preview server at :4173.
 */

const VALID_MANIFEST = JSON.stringify(
  {
    name: 'Test Collection',
    slug: 'test-collection-2026',
    images: [{ filename: 'room-01.jpg', url: 'https://example.com/room-01.jpg' }],
  },
  null,
  2,
);

// ─── Explorer – Workplan 2 filters ──────────────────────────────────────────

test.describe('Explorer – Workplan 2 filters', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    // Wait until the image-set select is rendered (populated by listImageSets mock)
    await expect(
      page.locator('#image-set-filter option', { hasText: 'Atlas Living Rooms 2024' }),
    ).toBeAttached({ timeout: 10_000 });
  });

  test('image-set selector is populated from mock', async ({ page }) => {
    const options = await page.locator('#image-set-filter option').allTextContents();
    expect(options[0]).toBe('All image sets');
    expect(options).toContain('Atlas Living Rooms 2024');
    expect(options).toContain('Studio Cafes 2024');
  });

  test('latent-tag selector has all 6 tags plus "all" option', async ({ page }) => {
    const options = await page.locator('#latent-tag-filter option').allTextContents();
    expect(options.length).toBe(7);
    expect(options[0]).toBe('All latent tags');
    expect(options).toContain('Sociopetal Seating');
    expect(options).toContain('Prospect');
    expect(options).toContain('Disengagement Ease');
  });

  test('effect-domain selector has all 7 domains plus "all" option', async ({ page }) => {
    const options = await page.locator('#effect-domain-filter option').allTextContents();
    expect(options.length).toBe(8);
    expect(options[0]).toBe('All effect domains');
    expect(options).toContain('Cognitive');
    expect(options).toContain('Social');
    expect(options).toContain('Health');
  });

  test('threshold input is hidden by default and appears when latent-tag is selected', async ({ page }) => {
    await expect(page.locator('#min-value-filter')).not.toBeVisible();
    await page.locator('#latent-tag-filter').selectOption('spatial.prospect');
    await expect(page.locator('#min-value-filter')).toBeVisible();
  });

  test('threshold input appears when effect-domain is selected', async ({ page }) => {
    await expect(page.locator('#min-value-filter')).not.toBeVisible();
    await page.locator('#effect-domain-filter').selectOption('social');
    await expect(page.locator('#min-value-filter')).toBeVisible();
  });

  test('selecting image-set filter updates URL param', async ({ page }) => {
    await page.locator('#image-set-filter').selectOption('atlas-living-rooms-2024');
    const url = new URL(page.url());
    expect(url.searchParams.get('image_set')).toBe('atlas-living-rooms-2024');
  });

  test('selecting latent-tag filter updates URL param', async ({ page }) => {
    await page.locator('#latent-tag-filter').selectOption('spatial.prospect');
    const url = new URL(page.url());
    expect(url.searchParams.get('latent_tag')).toBe('spatial.prospect');
  });

  test('URL params restore filter state on reload', async ({ page }) => {
    await page.goto('/?latent_tag=spatial.prospect&image_set=atlas-living-rooms-2024');
    await expect(
      page.locator('#image-set-filter option', { hasText: 'Atlas Living Rooms 2024' }),
    ).toBeAttached({ timeout: 10_000 });
    expect(await page.locator('#image-set-filter').inputValue()).toBe('atlas-living-rooms-2024');
    expect(await page.locator('#latent-tag-filter').inputValue()).toBe('spatial.prospect');
    // Threshold should be visible since latent_tag is set
    await expect(page.locator('#min-value-filter')).toBeVisible();
  });
});

// ─── Explorer – detail modal latents ────────────────────────────────────────

test.describe('Explorer – detail modal latents', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    // Wait for the image grid to populate (mock search returns image 101)
    await expect(
      page.locator('[aria-label^="Image 101"]'),
    ).toBeVisible({ timeout: 10_000 });
  });

  test('opens modal with Latents tab for image with observations', async ({ page }) => {
    await page.locator('[aria-label^="Image 101"]').click();
    await expect(page.locator('[role="dialog"]')).toBeVisible({ timeout: 5_000 });
    // Image 101 has 6 latent observations — Latents tab must be visible
    await expect(page.locator('[role="tab"]', { hasText: 'Latents' })).toBeVisible();
  });

  test('Latents tab shows all 6 observations', async ({ page }) => {
    await page.locator('[aria-label^="Image 101"]').click();
    await page.locator('[role="tab"]', { hasText: 'Latents' }).click();
    // The section header reads "Latent Observations (6)"
    await expect(page.locator('text=Latent Observations (6)')).toBeVisible({ timeout: 5_000 });
  });

  test('evidence keys render when toggled open', async ({ page }) => {
    await page.locator('[aria-label^="Image 101"]').click();
    await page.locator('[role="tab"]', { hasText: 'Latents' }).click();
    // Click "Show evidence" for the first observation
    const firstToggle = page.locator('button', { hasText: /Show evidence/ }).first();
    await expect(firstToggle).toBeVisible({ timeout: 5_000 });
    await firstToggle.click();
    await expect(page.locator('text=openness_score')).toBeVisible();
  });

  test('Overview tab shows provenance with set name, photographer, and license', async ({ page }) => {
    await page.locator('[aria-label^="Image 101"]').click();
    const dialog = page.locator('[role="dialog"]');
    await expect(dialog).toBeVisible({ timeout: 5_000 });
    // Overview tab is active by default — provenance section is there
    await expect(dialog.locator('text=Provenance')).toBeVisible();
    // Scope inside dialog to avoid matching the image-set filter <option>
    await expect(dialog.getByText('Atlas Living Rooms 2024').first()).toBeVisible();
    await expect(dialog.locator('text=A. Renner')).toBeVisible();
    await expect(dialog.locator('text=CC BY 4.0')).toBeVisible();
  });

  test('Latents tab shows linked effects with domain and mechanism', async ({ page }) => {
    await page.locator('[aria-label^="Image 101"]').click();
    await page.locator('[role="tab"]', { hasText: 'Latents' }).click();
    await expect(page.locator('text=Linked Effects')).toBeVisible({ timeout: 5_000 });
    // Check a domain badge and mechanism text from the mock
    await expect(page.locator('text=Face-to-face seating supports conversation initiation.')).toBeVisible();
  });

  test('modal closes on Escape', async ({ page }) => {
    await page.locator('[aria-label^="Image 101"]').click();
    await expect(page.locator('[role="dialog"]')).toBeVisible({ timeout: 5_000 });
    await page.keyboard.press('Escape');
    await expect(page.locator('[role="dialog"]')).not.toBeVisible({ timeout: 3_000 });
  });
});

// ─── Admin – image-set import panel ─────────────────────────────────────────

test.describe('Admin – image-set import panel', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/admin/');
    await expect(page.locator('text=Import Image Set')).toBeVisible({ timeout: 10_000 });
  });

  test('invalid JSON triggers client-side error and no success state appears', async ({ page }) => {
    await page.locator('#manifest-input').fill('{ not valid json }');
    await page.locator('button', { hasText: 'Import Set' }).click();
    await expect(page.locator('[role="alert"]').first()).toBeVisible();
    await expect(page.locator('text=Invalid JSON')).toBeVisible();
    await expect(page.locator('text=Import complete')).not.toBeVisible();
  });

  test('empty images array triggers client-side validation error', async ({ page }) => {
    await page.locator('#manifest-input').fill('{"name":"t","slug":"t","images":[]}');
    await page.locator('button', { hasText: 'Import Set' }).click();
    await expect(page.locator('text=Image list must not be empty')).toBeVisible();
    await expect(page.locator('text=Import complete')).not.toBeVisible();
  });

  test('valid manifest shows import success with set ID, slug, and counts', async ({ page }) => {
    await page.locator('#manifest-input').fill(VALID_MANIFEST);
    await page.locator('button', { hasText: 'Import Set' }).click();
    await expect(page.locator('text=Import complete')).toBeVisible({ timeout: 5_000 });
    // Slug from mock (importImageSetResponse uses manifest slug when provided)
    await expect(page.locator('text=test-collection-2026')).toBeVisible();
    // Counts table
    await expect(page.locator('text=Created images')).toBeVisible();
    await expect(page.locator('text=In file')).toBeVisible();
  });

  test('run latent detectors after import shows run summary', async ({ page }) => {
    await page.locator('#manifest-input').fill(VALID_MANIFEST);
    await page.locator('button', { hasText: 'Import Set' }).click();
    await expect(page.locator('text=Import complete')).toBeVisible({ timeout: 5_000 });
    await page.locator('button', { hasText: 'Run latent detectors' }).click();
    await expect(page.locator('text=Latent run queued')).toBeVisible({ timeout: 5_000 });
    // Use exact match to avoid matching "Latent run queued" for the "Queued" row label
    await expect(page.getByText('Queued', { exact: true })).toBeVisible();
    await expect(page.getByText('Already complete', { exact: true })).toBeVisible();
  });
});

// ─── Workbench – latent validation mode ─────────────────────────────────────

test.describe('Workbench – latent validation mode', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/workbench/');
    // Wait for the assignment to load (mode toggle appears in AssignmentView)
    await expect(page.locator('button', { hasText: 'Attribute' })).toBeVisible({ timeout: 10_000 });
  });

  test('switching to Latent mode renders the latent label and correction buttons', async ({ page }) => {
    await page.locator('button', { hasText: 'Latent' }).click();
    // Mock nextLatent label is "Prospect" — use exact to avoid matching "spatial.prospect"
    await expect(page.getByText('Prospect', { exact: true })).toBeVisible({ timeout: 5_000 });
    // Ordinal correction buttons 0–4
    await expect(page.locator('[aria-label="0 out of 4"]')).toBeVisible();
    await expect(page.locator('[aria-label="4 out of 4"]')).toBeVisible();
  });

  test('evidence toggle shows evidence key-value pairs', async ({ page }) => {
    await page.locator('button', { hasText: 'Latent' }).click();
    const toggle = page.locator('button', { hasText: /Show evidence/ });
    await expect(toggle).toBeVisible({ timeout: 5_000 });
    await toggle.click();
    await expect(page.locator('text=openness_score')).toBeVisible();
    await expect(page.locator('text=depth_source')).toBeVisible();
  });

  test('submit button is disabled until a correction value is selected', async ({ page }) => {
    await page.locator('button', { hasText: 'Latent' }).click();
    const submitBtn = page.locator('button', { hasText: /Submit correction/ });
    await expect(submitBtn).toBeVisible({ timeout: 5_000 });
    await expect(submitBtn).toBeDisabled();
    await page.locator('[aria-label="3 out of 4"]').click();
    await expect(submitBtn).toBeEnabled();
  });

  test('submitting a valid correction advances to the next state', async ({ page }) => {
    await page.locator('button', { hasText: 'Latent' }).click();
    await expect(page.locator('[aria-label="2 out of 4"]')).toBeVisible({ timeout: 5_000 });
    await page.locator('[aria-label="2 out of 4"]').click();
    await page.locator('button', { hasText: /Submit correction/ }).click();
    // After submission the app reloads: either a new assignment (Prospect again)
    // or the empty-queue message. Use exact to avoid matching "spatial.prospect".
    await expect(
      page.getByText('Prospect', { exact: true }).or(page.getByText('No items available')),
    ).toBeVisible({ timeout: 8_000 });
  });
});

// ─── Monitor – latent status warnings ───────────────────────────────────────

test.describe('Monitor – latent status warnings', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/monitor/');
    // Use role selector — the h2 heading, not the paragraph that also mentions "latent detector status"
    await expect(page.getByRole('heading', { name: 'Latent Detector Status' })).toBeVisible({ timeout: 10_000 });
  });

  test('normal latent status has no distribution warnings', async ({ page }) => {
    // Select the first image set option (index 1 = "Atlas Living Rooms 2024", id=1)
    await page.locator('#latent-set-select').selectOption({ index: 1 });
    await expect(page.locator('text=Total images')).toBeVisible({ timeout: 5_000 });
    await expect(page.locator('text=distribution warning')).not.toBeVisible();
  });

  test('suspicious latent status shows distribution warning rows', async ({ page }) => {
    // Set mock flag before triggering the request
    await page.evaluate(() => {
      (window as any).__MOCK_FLAGS = { latentStatus: 'suspicious' };
    });
    await page.locator('#latent-set-select').selectOption({ index: 1 });
    await expect(page.locator('text=distribution warning')).toBeVisible({ timeout: 5_000 });
    // Warning code labels from LatentStatusPanel's WARNING_LABELS map
    await expect(page.locator('text=Skew high')).toBeVisible();
    await expect(page.locator('text=Skew low')).toBeVisible();
    await expect(page.locator('text=Low confidence')).toBeVisible();
  });
});

// ─── Explorer – mobile-width layout (360 px) ────────────────────────────────

test.describe('Explorer – mobile-width layout', () => {
  test.use({ viewport: { width: 360, height: 800 } });

  test('filter bar has no horizontal overflow at 360 px', async ({ page }) => {
    await page.goto('/');
    await expect(
      page.locator('#image-set-filter option', { hasText: 'Atlas Living Rooms 2024' }),
    ).toBeAttached({ timeout: 10_000 });

    const overflows = await page.evaluate(() => {
      const offenders: string[] = [];
      document.querySelectorAll('*').forEach((el) => {
        const rect = el.getBoundingClientRect();
        if (rect.width > document.documentElement.clientWidth + 1) {
          offenders.push(
            `${el.tagName.toLowerCase()}${el.id ? '#' + el.id : ''}`,
          );
        }
      });
      return offenders.slice(0, 5);
    });
    expect(
      overflows,
      `Elements overflowing viewport: ${overflows.join(', ')}`,
    ).toHaveLength(0);
  });

  test('detail modal fits within 360 px viewport', async ({ page }) => {
    await page.goto('/');
    await expect(
      page.locator('[aria-label^="Image 101"]'),
    ).toBeVisible({ timeout: 10_000 });
    await page.locator('[aria-label^="Image 101"]').click();
    const modal = page.locator('[role="dialog"]');
    await expect(modal).toBeVisible({ timeout: 5_000 });
    const box = await modal.boundingBox();
    expect(box).not.toBeNull();
    expect(box!.width).toBeLessThanOrEqual(361); // 1 px tolerance
  });
});
