import { defineConfig, devices } from '@playwright/test';
import { mkdirSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const frontendDir = path.dirname(fileURLToPath(import.meta.url));
const repoDir = path.resolve(frontendDir, '..');
const repoPython = path.join(repoDir, '.venv', 'bin', 'python');
const e2eStateDir = path.join(frontendDir, 'test-results', '.e2e-state');
const e2eTmpDir = path.join(frontendDir, 'test-results', '.e2e-tmp');
mkdirSync(e2eTmpDir, { recursive: true });
process.env.TMPDIR = e2eTmpDir;
process.env.TEMP = e2eTmpDir;
process.env.TMP = e2eTmpDir;

const productPort = Number(process.env.E2E_PORT ?? '8817');
const onlineModePort = productPort + 1;

export default defineConfig({
  testDir: './tests/e2e',
  timeout: 180_000,
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1,
  reporter: 'list',
  outputDir: './test-results',
  use: {
    baseURL: process.env.BASE_URL || `http://127.0.0.1:${productPort}`,
    trace: 'on-first-retry',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  webServer: [
    {
      command: `bash ./tests/e2e/run-server.sh --port ${productPort}`,
      cwd: frontendDir,
      url: `http://127.0.0.1:${productPort}/`,
      reuseExistingServer: false,
      timeout: 180_000,
      env: {
        E2E_STATE_DIR: e2eStateDir,
        E2E_PORT: String(productPort),
        E2E_STATE: 'A',
        PYTHON_BIN: repoPython,
        TMPDIR: e2eTmpDir,
        TEMP: e2eTmpDir,
        TMP: e2eTmpDir,
      },
    },
    {
      command: `bash ./tests/e2e/run-server.sh --port ${onlineModePort} --state B`,
      cwd: frontendDir,
      url: `http://127.0.0.1:${onlineModePort}/`,
      reuseExistingServer: false,
      timeout: 180_000,
      env: {
        E2E_STATE_DIR: path.join(frontendDir, 'test-results', '.e2e-state-b'),
        E2E_PORT: String(onlineModePort),
        E2E_STATE: 'B',
        PYTHON_BIN: repoPython,
        TMPDIR: e2eTmpDir,
        TEMP: e2eTmpDir,
        TMP: e2eTmpDir,
      },
    },
  ],
});
