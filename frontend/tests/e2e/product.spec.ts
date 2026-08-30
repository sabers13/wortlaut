import { expect, test } from '@playwright/test';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

test.describe.configure({ mode: 'serial' });

const here = path.dirname(fileURLToPath(import.meta.url));
const replacementDictionary = path.resolve(here, '../../test-results/.e2e-state/replacement.sqlite');
const firstServerTimeout = 60_000;

function tinyWavFixture(): Buffer {
  // 10 ms, mono, 8 kHz, PCM16 silence: a valid browser-local upload fixture.
  const samples = 80;
  const buffer = Buffer.alloc(44 + samples * 2);
  buffer.write('RIFF', 0);
  buffer.writeUInt32LE(buffer.length - 8, 4);
  buffer.write('WAVEfmt ', 8);
  buffer.writeUInt32LE(16, 16);
  buffer.writeUInt16LE(1, 20);
  buffer.writeUInt16LE(1, 22);
  buffer.writeUInt32LE(8000, 24);
  buffer.writeUInt32LE(16000, 28);
  buffer.writeUInt16LE(2, 32);
  buffer.writeUInt16LE(16, 34);
  buffer.write('data', 36);
  buffer.writeUInt32LE(samples * 2, 40);
  return buffer;
}

async function createDeckAndManualCard(page: import('@playwright/test').Page): Promise<void> {
  await page.getByLabel('New deck name').fill('Journey');
  await page.getByRole('button', { name: 'Create deck' }).click();
  await expect(page.getByRole('status')).toContainText('Created and opened “Journey”');
  await page.getByLabel('German word').fill('Haus');
  await page.getByRole('button', { name: 'Look up' }).click();
  await expect(page.getByText('Select vocabulary')).toBeVisible({ timeout: firstServerTimeout });
  await expect(page.getByRole('button', { name: /Haus · NOUN/ })).toBeVisible({ timeout: firstServerTimeout });
  await page.getByRole('button', { name: /Haus · NOUN/ }).click();
  await page.getByLabel('house, building').check();
  await page.getByRole('button', { name: 'Save vocabulary' }).click();
  await expect(page.getByRole('status')).toContainText('Saved “Haus” to “Journey”');
}

async function openStudy(page: import('@playwright/test').Page): Promise<void> {
  await page.locator('.primary-nav').getByRole('button', { name: 'Study due' }).click();
  await expect(page.getByRole('heading', { name: 'All due cards' })).toBeVisible({ timeout: firstServerTimeout });
}

test('FastAPI static product has explicit loading, error, and empty deck states', async ({ page }) => {
  await page.route('**/vocab/decks', async (route) => {
    await new Promise((resolve) => setTimeout(resolve, 150));
    await route.abort();
  });
  const documentResponse = await page.goto('/');
  expect(documentResponse?.headers()['content-type']).toContain('text/html');
  await expect(page.getByRole('status')).toContainText('Loading decks');
  await expect(page.getByText('We could not reach your deck list.')).toBeVisible();
  await page.unroute('**/vocab/decks');
  await page.reload();
  await expect(page.getByText('No decks yet. Create one to begin organizing German vocabulary.')).toBeVisible();
  const openApi = await page.evaluate(async () => (await fetch('/openapi.json')).json());
  expect(openApi.info.title).toBe('Flashcard Vocabulary API');
});

test('manual creation, local audio, review, unavailable fallback, and both exports work through FastAPI', async ({ page }) => {
  await page.goto('/');
  await createDeckAndManualCard(page);

  const tsvDownload = page.waitForEvent('download');
  await page.getByRole('button', { name: /Export “Journey” TSV/ }).click();
  await expect(page.getByRole('status')).toContainText('Prepared a TSV export');
  expect((await tsvDownload).suggestedFilename()).toBe('Journey.tsv');
  const apkgDownload = page.waitForEvent('download');
  await page.getByRole('button', { name: /Export “Journey” APKG/ }).click();
  await expect(page.getByRole('status')).toContainText('Prepared an APKG export');
  expect((await apkgDownload).suggestedFilename()).toBe('Journey.apkg');

  await openStudy(page);
  await expect(page.getByRole('heading', { name: 'Haus' })).toBeVisible({ timeout: firstServerTimeout });
  await page.keyboard.press('Space');
  await expect(page.getByText('How well did you know it?')).toBeVisible();
  await page.getByRole('button', { name: 'Add your pronunciation' }).click();
  await page.locator('input[type=file]').setInputFiles({
    name: 'tiny.wav',
    mimeType: 'audio/wav',
    buffer: tinyWavFixture(),
  });
  await expect(page.locator('audio.audio-preview')).toBeVisible();
  await page.getByRole('button', { name: 'Save recording' }).click();
  await expect(page.locator('.pronunciation').getByRole('status')).toContainText('Custom pronunciation saved.');
  await page.getByRole('button', { name: 'Revert to automatic' }).click();
  await page.getByRole('button', { name: 'Confirm revert to automatic' }).click();
  await expect(page.locator('.pronunciation').getByRole('status')).toContainText('Automatic pronunciation restored.');
  await page.getByRole('button', { name: 'Play pronunciation' }).click();
  await expect(page.getByRole('alert')).toContainText(/Audio for 'Haus' not found|Pronunciation is unavailable/);
  await page.keyboard.press("Space");
  await expect(page.getByText("How well did you know it?")).toBeVisible();
  await page.getByRole('button', { name: /5 Without doubt/ }).click();
  await expect(page.getByRole('heading', { name: 'Nothing due right now' })).toBeVisible({ timeout: firstServerTimeout });
});

test('two-stage capture handles stale dictionary tokens with zero-write recovery and multi-select confirmation', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('button', { name: 'Open Journey' }).click();
  const sentence = page.getByLabel('Sentence text');
  await sentence.fill('Der See ist tief.');
  await sentence.evaluate((element: HTMLTextAreaElement) => {
    element.focus();
    element.setSelectionRange(4, 7);
    element.dispatchEvent(new Event('select', { bubbles: true }));
  });
  await page.getByLabel('Lesson label').fill('Lesson 8');
  await page.getByRole('button', { name: 'Find candidates' }).click();
  await expect(page.getByText('Choose vocabulary')).toBeVisible({ timeout: firstServerTimeout });
  const choices = page.locator('.capture-candidate input[type=checkbox]');
  await expect(choices).toHaveCount(2, { timeout: firstServerTimeout });
  await choices.nth(0).check();
  await choices.nth(1).check();
  const cardsBefore = await page.evaluate(async () => (await (await fetch('/vocab/decks')).json())[0].card_count);
  const activation = await page.evaluate(async (dictionaryPath) => {
    const response = await fetch('/vocab/dictionary/activate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-Flashcards-Request': '1' },
      body: JSON.stringify({ path: dictionaryPath, version: 'e2e-replacement' }),
    });
    return { status: response.status, body: await response.json() };
  }, replacementDictionary);
  expect(activation.status).toBe(200);
  await page.getByRole('button', { name: /Create 2 cards/ }).click();
  await expect(page.getByRole('alert')).toContainText('The dictionary changed while you were choosing cards. Your selections have not been saved.');
  const cardsAfterConflict = await page.evaluate(async () => (await (await fetch('/vocab/decks')).json())[0].card_count);
  expect(cardsAfterConflict).toBe(cardsBefore);
  await page.getByRole('button', { name: 'Find fresh candidates' }).click();
  await expect(choices).toHaveCount(2);
  await choices.nth(0).check();
  await choices.nth(1).check();
  await page.getByRole('button', { name: /Create 2 cards/ }).click();
  await expect(page.getByRole('status')).toContainText('Server confirmed 2 cards created');
});

test('review controls and navigation respond at every required viewport', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('button', { name: 'Open Journey' }).click();
  await page.getByRole('button', { name: 'Study this deck' }).click();
  await expect(page.getByRole('heading', { name: /See/ })).toBeVisible({ timeout: firstServerTimeout });
  await page.keyboard.press('Space');
  const confidence = page.locator('.confidence-grid > button');
  await expect(confidence).toHaveCount(5);
  for (const viewport of [
    { width: 360, height: 800 },
    { width: 768, height: 1024 },
    { width: 1366, height: 768 },
    { width: 1920, height: 1080 },
  ]) {
    await page.setViewportSize(viewport);
    if (viewport.width < 800) {
      await expect(page.locator('.bottom-nav')).toBeVisible();
      const gridColumns = await page.locator('.confidence-grid').evaluate((element) => getComputedStyle(element).gridTemplateColumns.split(' ').length);
      expect(gridColumns).toBe(1);
      const order = await confidence.allTextContents();
      expect(order.map((text) => text.trim().charAt(0))).toEqual(['1', '2', '3', '4', '5']);
      const first = await confidence.first().boundingBox();
      const gridWidth = (await page.locator(".confidence-grid").boundingBox())?.width ?? 0;
      expect(first?.width ?? 0).toBeGreaterThan(gridWidth * 0.8);
    } else {
      await expect(page.locator('.bottom-nav')).toBeHidden();
      const shell = await page.locator('.shell').boundingBox();
      expect(shell?.width ?? 0).toBeLessThan(page.viewportSize()?.width ?? 0);
    }
  }
});
