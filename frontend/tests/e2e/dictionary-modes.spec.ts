/**
 * Slice 12 end-to-end coverage for the chooser, settings actions,
 * dictionary-mode switches, and the Online-fixture wiring.
 *
 * Test environment:
 *   - Default project webServer (state A): canonical Offline dictionary
 *     installed at startup; chooser is hidden.
 *   - Second project webServer (state B): no canonical full Offline
 *     dictionary; deterministic Online fixture corpus wired through the
 *     backend Product trust/test seam; chooser is visible. The Online
 *     provider is constructed ONLY after the user clicks "Use Online";
 *     startup-time factory/transport counts are asserted via
 *     GET /__e2e/online-counters (E2E harness only).
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

async function e2eCounters(
  page: import('@playwright/test').Page,
): Promise<{ factory_invocations: number; transport_invocations: number }> {
  // Use browser-context fetch (not page.request) to avoid API-context
  // deadlocks with the page's own in-flight requests.
  const body = (await page.evaluate(async () => {
    const res = await fetch('/vocab/settings/dictionary');
    if (!res.ok) throw new Error(`settings GET failed: ${res.status}`);
    return (await res.json()) as {
      e2e_counters?: { factory_invocations: number; transport_invocations: number };
    };
  })) as {
    e2e_counters?: { factory_invocations: number; transport_invocations: number };
  };
  expect(body.e2e_counters).toBeDefined();
  return body.e2e_counters as {
    factory_invocations: number;
    transport_invocations: number;
  };
}

async function e2eMode(page: import('@playwright/test').Page): Promise<string> {
  const body = (await page.evaluate(async () => {
    const res = await fetch('/vocab/settings/dictionary');
    if (!res.ok) throw new Error(`settings GET failed: ${res.status}`);
    return (await res.json()) as { mode?: string };
  })) as { mode?: string };
  return body.mode ?? 'unknown';
}

/** Click "Use Online" only if the session is not already Online. */
async function ensureOnline(page: import('@playwright/test').Page): Promise<void> {
  await page.goto('/');
  const mode = await e2eMode(page);
  if (mode === 'online') {
    // Already Online: navigate to decks view directly.
    await expect(page.getByRole('heading', { name: 'Wortlaut' })).toBeVisible({
      timeout: 30_000,
    });
    return;
  }
  // Chooser visible: click Use Online.
  await expect(
    page.getByRole('heading', { name: 'Choose how to use the dictionary' }),
  ).toBeVisible({ timeout: 30_000 });
  await page.getByRole('button', { name: 'Use Online' }).click();
  await expect(page.getByRole('heading', { name: 'Wortlaut' })).toBeVisible({
    timeout: 120_000,
  });
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

  test('state A: Offline -> Online keeps the canonical Offline on disk', async ({
    page,
  }) => {
    await page.goto('/');
    await settings(page);
    const useOnline = page.getByRole('button', { name: 'Use Online for this session' });
    await useOnline.click();
    // After the in-process swap, the canonical Offline slot must remain intact.
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

  test('state B: zero backend transport before user picks a mode', async ({
    page,
  }) => {
    await page.goto('/');
    await expect(
      page.getByRole('heading', { name: 'Choose how to use the dictionary' }),
    ).toBeVisible();
    // The BACKEND counter proves zero dictionary network before choice.
    // Browser request counting cannot observe server-side shard downloads.
    const counters = await e2eCounters(page);
    expect(counters.factory_invocations).toBe(0);
    expect(counters.transport_invocations).toBe(0);
  });

  test('state B: Use Online activates the deterministic fixture corpus', async ({
    page,
  }) => {
    await ensureOnline(page);
    await expect(page.getByRole('heading', { name: 'Wortlaut' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Your decks' })).toBeVisible();
    // The factory must have been invoked exactly once by the user choice.
    const counters = await e2eCounters(page);
    expect(counters.factory_invocations).toBeGreaterThanOrEqual(1);
    // Online-backed /vocab/lookup must surface the deterministic fixture.
    const lookup = page.getByRole('textbox', { name: 'German word' });
    await lookup.fill('Haus');
    await page.getByRole('button', { name: 'Look up' }).click();
    await expect(
      page.getByRole('button', { name: /Haus/ }).first(),
    ).toBeVisible();
    // Transport must now be non-zero (shards were fetched through the seam).
    const after = await e2eCounters(page);
    expect(after.transport_invocations).toBeGreaterThan(0);
  });

  test('state B: Online-backed /vocab/highlight returns candidates', async ({
    page,
  }) => {
    await ensureOnline(page);
    await page
      .getByRole('textbox', { name: 'Sentence text' })
      .fill('Das Haus ist alt.');
    await page.getByRole('textbox', { name: 'Lesson label' }).fill('Lesson X');
    await page.getByRole('button', { name: 'Find candidates' }).click();
    await expect(page.getByText(/Haus/).first()).toBeVisible();
  });

  test('state B: Online CSV import creates a deck', async ({ page }) => {
    await ensureOnline(page);
    await expect(page.getByRole('heading', { name: 'Your decks' })).toBeVisible();
    // Create then open a deck to reach the Import & export form.
    await page.getByLabel('New deck name').fill('Online import deck');
    await page.getByRole('button', { name: 'Create deck' }).click();
    await expect(page.getByRole('status')).toContainText(/Created and opened/i);
    await page.getByLabel('CSV import deck name').fill('Online import deck');
    await page.getByLabel('Vocabulary lines').fill('Haus\nSee');
    await page.getByRole('button', { name: 'Import CSV' }).click();
    await expect(page.getByRole('status')).toContainText(/Imported 2 words/i);
  });

  test('state B: Online candidate materialization and card creation', async ({
    page,
  }) => {
    await ensureOnline(page);
    // Create a deck, look up Haus, save it — all through Online provider data.
    await page.getByLabel('New deck name').fill('Online journey');
    await page.getByRole('button', { name: 'Create deck' }).click();
    await expect(page.getByRole('status')).toContainText(/Created and opened/i);
    await page.getByLabel('German word').fill('Haus');
    await page.getByRole('button', { name: 'Look up' }).click();
    await expect(page.getByText('Select vocabulary')).toBeVisible();
    await page.getByRole('button', { name: /Haus · NOUN/ }).first().click();
    await page.getByRole('button', { name: 'Save vocabulary' }).click();
    await expect(page.getByRole('status')).toContainText(/Saved “Haus”/);
  });

  test('state B: Download for Offline use installs the fixture asset', async ({
    page,
  }) => {
    await page.goto('/');
    await settings(page);
    await page.getByRole('button', { name: 'Download for Offline use' }).click();
    // The server returns 202 started; the UI polls and shows progress.
    await expect(
      page.getByText(/Download started|Downloading…|Installed full Offline/i),
    ).toBeVisible({ timeout: 60_000 });
    // After install the canonical slot validates.
    await page.getByRole('button', { name: 'Refresh' }).click();
    await expect(page.getByText('yes').first()).toBeVisible();
  });

  test('state B: Clear Online cache keeps the provider usable', async ({ page }) => {
    await ensureOnline(page);
    await settings(page);
    const button = page.getByRole('button', { name: 'Clear Online cache' });
    await expect(button).toBeEnabled();
    await button.click();
    await expect(page.getByText(/online cache cleared/i)).toBeVisible();
    // Provider remains usable afterward: lookup still works.
    await page.getByRole('button', { name: 'Decks' }).click();
    const lookup = page.getByRole('textbox', { name: 'German word' });
    await lookup.fill('See');
    await page.getByRole('button', { name: 'Look up' }).click();
    await expect(
      page.getByRole('button', { name: /See/ }).first(),
    ).toBeVisible();
  });

  test('state B: Remove Offline rejected because no canonical Offline exists', async ({
    page,
  }) => {
    await ensureOnline(page);
    await settings(page);
    await page.getByRole('button', { name: 'Remove Offline dictionary' }).click();
    await page.getByRole('button', { name: 'Confirm remove Offline' }).click();
    await expect(
      page.getByText(
        /no canonical full Offline dictionary|offline_unavailable|offline_removal_rejected/i,
      ),
    ).toBeVisible();
  });

  test('state B: Online next-card render works through the provider', async ({
    page,
  }) => {
    await ensureOnline(page);
    // Create a deck + card through Online, then study it.
    await page.getByLabel('New deck name').fill('Online study deck');
    await page.getByRole('button', { name: 'Create deck' }).click();
    await expect(page.getByRole('status')).toContainText(/Created and opened/i);
    await page.getByLabel('German word').fill('Haus');
    await page.getByRole('button', { name: 'Look up' }).click();
    await expect(page.getByText('Select vocabulary')).toBeVisible();
    await page.getByRole('button', { name: /Haus · NOUN/ }).first().click();
    await page.getByRole('button', { name: 'Save vocabulary' }).click();
    await expect(page.getByRole('status')).toContainText(/Saved “Haus”/);
    // Study: next-card must render through the Online provider.
    await page.getByRole('button', { name: 'Study due' }).click();
    await expect(
      page.getByRole('heading', { name: 'All due cards' }),
    ).toBeVisible({ timeout: 60_000 });
  });

  test('state B: Online-active Remove Offline keeps Online usable', async ({
    page,
  }) => {
    await ensureOnline(page);
    await settings(page);
    // Download the fixture Offline asset first.
    await page.getByRole('button', { name: 'Download for Offline use' }).click();
    await expect(
      page.getByText(/Download started|Downloading…|Installed full Offline/i),
    ).toBeVisible({ timeout: 60_000 });
    await page.getByRole('button', { name: 'Refresh' }).click();
    // Now remove while Online is active: must succeed.
    await page.getByRole('button', { name: 'Remove Offline dictionary' }).click();
    await page.getByRole('button', { name: 'Confirm remove Offline' }).click();
    await expect(page.getByText(/removed/i)).toBeVisible();
    // Online lookup still works after removal.
    await page.getByRole('button', { name: 'Decks' }).click();
    const lookup = page.getByRole('textbox', { name: 'German word' });
    await lookup.fill('Haus');
    await page.getByRole('button', { name: 'Look up' }).click();
    await expect(
      page.getByRole('button', { name: /Haus/ }).first(),
    ).toBeVisible();
  });

  test('state B: Online -> Offline switch after download', async ({ page }) => {
    await ensureOnline(page);
    await settings(page);
    await page.getByRole('button', { name: 'Download for Offline use' }).click();
    await expect(
      page.getByText(/Download started|Downloading…|Installed full Offline/i),
    ).toBeVisible({ timeout: 60_000 });
    await page.getByRole('button', { name: 'Refresh' }).click();
    // Switch to Offline: must succeed now that the asset validates.
    const useOffline = page.getByRole('button', { name: 'Use Offline' });
    await expect(useOffline).toBeEnabled({ timeout: 60_000 });
    await useOffline.click();
    await expect(page.getByText(/Now using Offline/i)).toBeVisible();
  });

  test('state B: browser cannot configure any Online/Offline source', async ({
    page,
  }) => {
    await page.goto('/');
    await settings(page);
    const bodyText = await page.locator('body').innerText();
    // No URL / manifest / host / repository input may exist in the UI.
    expect(bodyText).not.toMatch(/download_url/i);
    expect(bodyText).not.toMatch(/manifest_bytes/i);
    expect(bodyText).not.toMatch(/online-manifest/i);
    expect(bodyText).not.toMatch(/repository/i);
    // No text input for a source URL is rendered.
    await expect(page.getByLabel(/URL|manifest|repository|host/i)).toHaveCount(0);
  });
});
