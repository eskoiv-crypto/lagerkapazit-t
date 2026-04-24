// @ts-check
import { pathToFileURL } from 'node:url';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

export const DASHBOARD_PATH = path.resolve(__dirname, '..', 'elvinci_lagerkapazitaet_dashboard_v2026-04-20.html');
export const DASHBOARD_URL = pathToFileURL(DASHBOARD_PATH).href;
export const FIXTURES_DIR = path.resolve(__dirname, 'fixtures');

/**
 * Öffnet das Dashboard und wartet bis DOM ready + initA11y durch ist.
 * Sammelt Console-Errors für spätere Assertions.
 */
export async function openDashboard(page) {
    const consoleErrors = [];
    page.on('console', (msg) => {
        if (msg.type() === 'error') consoleErrors.push(msg.text());
    });
    page.on('pageerror', (err) => {
        consoleErrors.push('PAGEERROR: ' + err.message);
    });
    await page.goto(DASHBOARD_URL);
    await page.waitForLoadState('domcontentloaded');
    // Gib dem DOMContentLoaded-Handler + initA11y Zeit
    await page.waitForFunction(() => typeof window.initA11y === 'function');
    return { consoleErrors };
}

/**
 * Lädt eine Fixture-Datei in einen File-Input.
 */
export async function uploadFixture(page, inputSelector, fixtureFilename) {
    const filePath = path.resolve(FIXTURES_DIR, fixtureFilename);
    await page.setInputFiles(inputSelector, filePath);
}
