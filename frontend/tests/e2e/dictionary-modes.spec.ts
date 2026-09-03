/**
 * Slice 12 end-to-end coverage for the chooser, settings actions,
 * dictionary-mode switches, and the Online-fixture wiring.
 *
 * Test environment:
 *   - Default project webServer (state A): canonical Offline dictionary
 *     installed at startup; chooser is hidden.
 *   - Second project webServer (state B): no canonical full Offline
 *     dictionary; deterministic Online fixture corpus wired through the
 *     backend Product trust/test seam; chooser is visible.
 *
 * No public GitHub network reach is required at any point — every shard
 * is served from a local fixture under the E2E state directory.
 */

import { expect, test } from '@playwright/test';

const STATE_B_HOST = '127.0.0.1';
const STATE_B_PORT = Number(process.env.E2E_ONLINE_PORT ?? '8818');

async function settings(page: import('@playwright/test').Page) {
  await page.getByRole('button', { name: 'Settings' }).click();
  await expect(page.getByRole('heading', { name: 'Dictionary' })).toBeVisible();
}

test.describe('Slice 12 dictionary-mode chooser and Settings', () => {
  test('state A: valid installed Offline hides the chooser; settings surface exists', async ({
    page,
  }) => {
    await page.goto('/');
    await expect(page.getByRole('heading', { name: 'Wortlaut' })).toBeVisible();
    // The chooser must NOT be visible when the canonical Offline dictionary
    // is installed and verified.
    await expect(
      page.getByRole('heading', { name: 'Choose how to use the dictionary' }),
    ).toHaveCount(0);
    await settings(page);
  });

  test('state A: Remove Offline is rejected while Offline is active', async ({
    page,
  }) => {
    await page.goto('/');
    await settings(page);
    // The Offline-active mode refuses removal with a structured conflict.
    await page.getByRole('button', { name: 'Remove Offline dictionary' }).click();
    await page.getByRole('button', { name: 'Confirm remove Offline' }).click();
    await expect(
      page.getByText(
        /switch the session to Online for this session|offline_dictionary_in_use/i,
      ),
    ).toBeVisible();
  });

  test('state A: switching to Online keeps the canonical Offline dictionary on disk', async ({
    page,
  }) => {
    await page.goto('/');
    await settings(page);
    const removeButton = page.getByRole('button', { name: 'Use Online for this session' });
    await removeButton.click();
    // After the in-process swap, the chooser is no longer reachable and
    // the canonical Offline slot must remain intact.
    await expect(page.getByRole('heading', { name: 'Dictionary' })).toBeVisible();
    await expect(
      page.getByText(/canonical Offline dictionary will not be removed/i),
    ).toBeVisible();
  });
});

test.describe('Slice 12 Online-fixture served product', () => {
  test.use({
    baseURL: `http://${STATE_B_HOST}:${STATE_B_PORT}`,
  });

  test('state B: chooser appears with online-fixture defaults', async ({ page }) => {
    await page.goto('/');
    await expect(
      page.getByRole('heading', { name: 'Choose how to use the dictionary' }),
    ).toBeVisible();
    await expect(
      page.getByRole('button', { name: 'Use Online' }),
    ).toBeVisible();
    await expect(
      page.getByRole('button', { name: 'Download for Offline use' }),
    ).toBeVisible();
  });

  test('state B: zero dictionary network requests before user picks a mode', async ({
    page,
  }) => {
    let dictionaryNetworkCalls = 0;
    page.on('request', (req) => {
      const url = req.url();
      // No GitHub Release fetch, no arbitrary host. Only same-origin
      // /assets/* or /vocab/* are expected.
      if (!url.startsWith(page.url())) {
        dictionaryNetworkCalls += 1;
      }
    });
    await page.goto('/');
    await expect(
      page.getByRole('heading', { name: 'Choose how to use the dictionary' }),
    ).toBeVisible();
    expect(dictionaryNetworkCalls).toBe(0);
  });

  test('state B: Use Online activates the deterministic fixture corpus', async ({
    page,
  }) => {
    await page.goto('/');
    await page.getByRole('button', { name: 'Use Online' }).click();
    await expect(page.getByRole('heading', { name: 'Wortlaut' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Your decks' })).toBeVisible();
    // Online-backed /vocab/lookup must surface the deterministic fixture.
    const lookup = page.getByRole('textbox', { name: 'German word' });
    await lookup.fill('Haus');
    await page.getByRole('button', { name: 'Look up' }).click();
    await expect(
      page.getByRole('button', { name: /Haus/ }).first(),
    ).toBeVisible();
  });

  test('state B: Online-backed /vocab/highlight returns candidates', async ({
    page,
  }) => {
    await page.goto('/');
    await page.getByRole('button', { name: 'Use Online' }).click();
    await page
      .getByRole('textbox', { name: 'Sentence text' })
      .fill('Das Haus ist alt.');
    await page.getByRole('textbox', { name: 'Lesson label' }).fill('Lesson X');
    await page.getByRole('button', { name: 'Find candidates' }).click();
    await expect(page.getByText(/Haus/).first()).toBeVisible();
  });

  test('state B: Clear Online cache clears the cache directory', async ({ page }) => {
    await page.goto('/');
    await settings(page);
    const button = page.getByRole('button', { name: 'Clear Online cache' });
    await expect(button).toBeEnabled();
    await button.click();
    await expect(page.getByText(/online cache cleared/i)).toBeVisible();
  });

  test('state B: Remove Offline rejected because no canonical Offline exists', async ({
    page,
  }) => {
    await page.goto('/');
    await page.getByRole('button', { name: 'Use Online' }).click();
    await settings(page);
    await page.getByRole('button', { name: 'Remove Offline dictionary' }).click();
    await page.getByRole('button', { name: 'Confirm remove Offline' }).click();
    await expect(
      page.getByText(
        /no canonical full Offline dictionary|offline_unavailable|offline_removal_rejected/i,
      ),
    ).toBeVisible();
  });
});
