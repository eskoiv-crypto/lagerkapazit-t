// @ts-check
import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright Config für das NH5-Dashboard.
 *
 * Das Dashboard ist eine Single-File-HTML-App und wird als `file://` geladen —
 * kein Dev-Server nötig. Tests decken die Invarianten aus Sprint 1-5 ab.
 *
 * Ausführung:
 *   npm install                # einmalig Playwright + Browsers
 *   npx playwright install     # Browser-Binaries ziehen
 *   npm test                   # alle Tests
 *   npm run test:headed        # mit sichtbarem Browser
 *   npm run test:ui            # interaktiver UI-Mode
 */
export default defineConfig({
    testDir: './tests',
    timeout: 30_000,
    expect: { timeout: 5_000 },
    fullyParallel: false,            // Single-File-Dashboard → sequenziell sicherer
    retries: 0,
    workers: 1,
    reporter: [['list'], ['html', { open: 'never' }]],
    use: {
        actionTimeout: 10_000,
        screenshot: 'only-on-failure',
        trace: 'retain-on-failure',
    },
    projects: [
        {
            name: 'chromium',
            use: { ...devices['Desktop Chrome'] },
        },
    ],
});
