// @ts-check
import { test, expect } from '@playwright/test';
import { openDashboard } from './helpers.js';

/**
 * "Unit-Tests" direkt im Browser-Context. Laden das Dashboard einmal und rufen
 * die Helper mit festen Inputs auf. Verhindert Regression der Sprint-1-bis-4-Fixes.
 */
test.describe('Unit-Helpers', () => {
    test('Sprint 1 P0-2/P0-3: calculateMargin hat Division-by-Zero-Guard', async ({ page }) => {
        await openDashboard(page);
        const cases = await page.evaluate(() => [
            window.calculateMargin(50, 200),   // 25%
            window.calculateMargin(0, 100),    // 0%
            window.calculateMargin(50, 0),     // guard → 0
            window.calculateMargin(10, -5),    // guard → 0
        ]);
        expect(cases).toEqual([25, 0, 0, 0]);
    });

    test('Sprint 4 P2-2: calculateMarginFromEkVk stimmt + guard', async ({ page }) => {
        await openDashboard(page);
        const cases = await page.evaluate(() => [
            window.calculateMarginFromEkVk(100, 150), // 50
            window.calculateMarginFromEkVk(100, 100), // 0
            window.calculateMarginFromEkVk(0, 100),   // guard → 0
        ]);
        expect(cases).toEqual([50, 0, 0]);
    });

    test('Sprint 3 P1-9: escapeHtml neutralisiert XSS-Payloads', async ({ page }) => {
        await openDashboard(page);
        const out = await page.evaluate(() => [
            window.escapeHtml('<script>alert(1)</script>'),
            window.escapeHtml("'; drop table kunden; --"),
            window.escapeHtml(null),
            window.escapeHtml(undefined),
            window.escapeHtml('A & B < C > D'),
        ]);
        expect(out[0]).toBe('&lt;script&gt;alert(1)&lt;/script&gt;');
        expect(out[1]).toContain('&#39;');
        expect(out[2]).toBe('');
        expect(out[3]).toBe('');
        expect(out[4]).toBe('A &amp; B &lt; C &gt; D');
    });

    // NOTE: getArtikelFaktorLocal ist in processCSV genested, nicht direkt test-zugänglich.
    // Regression erfolgt indirekt über upload.spec.js (BESTAND-Upload → Gewichtung berechnet korrekt).

    test('Sprint 2 P1-1: resetAllSessionState leert alle Maps + Flags', async ({ page }) => {
        await openDashboard(page);
        const snapshot = await page.evaluate(() => {
            window.dashboardState.bestandLoaded = true;
            window.dashboardState.pipelineWE = { '2026-04-18': 50 };
            window.dashboardState.stockAnalysisData = { '9001': { ek: 100 } };
            window.dashboardState.kundenStats = { 'Foo GmbH': { umsatz: 999 } };
            window.resetAllSessionState();
            return {
                bestandLoaded: window.dashboardState.bestandLoaded,
                pipelineWEKeys: Object.keys(window.dashboardState.pipelineWE).length,
                stockKeys: Object.keys(window.dashboardState.stockAnalysisData).length,
                kundenKeys: Object.keys(window.dashboardState.kundenStats).length,
            };
        });
        expect(snapshot.bestandLoaded).toBe(false);
        expect(snapshot.pipelineWEKeys).toBe(0);
        expect(snapshot.stockKeys).toBe(0);
        expect(snapshot.kundenKeys).toBe(0);
    });
});
