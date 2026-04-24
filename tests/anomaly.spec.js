// @ts-check
import { test, expect } from '@playwright/test';
import { openDashboard } from './helpers.js';

/**
 * Regression-Tests für 10X-4 Anomalie-Detektor.
 * Statt echter Upload-Historie → direkt detectAnomalies(fakeSnapshots) aufrufen.
 */
test.describe('Anomalie-Detektor (10X-4)', () => {
    test('Keine Anomalien bei < 2 Snapshots', async ({ page }) => {
        await openDashboard(page);
        const result = await page.evaluate(() => window.detectAnomalies({}));
        expect(result).toEqual([]);
        const oneOnly = await page.evaluate(() => window.detectAnomalies({
            '2026-04-20': { gesamtStueck: 500 }
        }));
        expect(oneOnly).toEqual([]);
    });

    test('Stabile Historie + heute stabil → keine Anomalie', async ({ page }) => {
        await openDashboard(page);
        const snaps = {
            '2026-04-20': { gesamtStueck: 500, lagerStueck: 400, kommStueck: 80, weStueck: 20, auftraege: 40 },
            '2026-04-19': { gesamtStueck: 495, lagerStueck: 395, kommStueck: 80, weStueck: 20, auftraege: 41 },
            '2026-04-18': { gesamtStueck: 510, lagerStueck: 410, kommStueck: 80, weStueck: 20, auftraege: 39 },
            '2026-04-17': { gesamtStueck: 505, lagerStueck: 405, kommStueck: 80, weStueck: 20, auftraege: 40 },
        };
        const result = await page.evaluate((s) => window.detectAnomalies(s), snaps);
        expect(result).toEqual([]);
    });

    test('Gesamtbestand -50% → critical Anomaly', async ({ page }) => {
        await openDashboard(page);
        const snaps = {
            '2026-04-20': { gesamtStueck: 250, lagerStueck: 200, kommStueck: 40, weStueck: 10, auftraege: 20 },
            '2026-04-19': { gesamtStueck: 500, lagerStueck: 400, kommStueck: 80, weStueck: 20, auftraege: 40 },
            '2026-04-18': { gesamtStueck: 510, lagerStueck: 410, kommStueck: 80, weStueck: 20, auftraege: 39 },
            '2026-04-17': { gesamtStueck: 495, lagerStueck: 395, kommStueck: 80, weStueck: 20, auftraege: 41 },
        };
        const result = await page.evaluate((s) => window.detectAnomalies(s), snaps);
        const gesamt = result.find(a => a.metric === 'gesamtStueck');
        expect(gesamt, 'Gesamt-Bestand-Anomalie muss erkannt werden').toBeTruthy();
        expect(gesamt.severity).toBe('critical');
        expect(gesamt.deviationPct).toBeLessThan(-40);
        expect(gesamt.today).toBe(250);
    });

    test('Brand-Level Anomaly (Electrolux -37%)', async ({ page }) => {
        await openDashboard(page);
        const base = { gesamtStueck: 500, lagerStueck: 400, kommStueck: 80, weStueck: 20, auftraege: 40 };
        const snaps = {
            '2026-04-20': { ...base, brandBreakdown: { Electrolux: 63, Bosch: 120 } },  // 63 vs median 100 = -37%
            '2026-04-19': { ...base, brandBreakdown: { Electrolux: 100, Bosch: 120 } },
            '2026-04-18': { ...base, brandBreakdown: { Electrolux: 105, Bosch: 118 } },
            '2026-04-17': { ...base, brandBreakdown: { Electrolux: 95,  Bosch: 122 } },
        };
        const result = await page.evaluate((s) => window.detectAnomalies(s), snaps);
        const elx = result.find(a => a.metric === 'brand:Electrolux');
        expect(elx, 'Electrolux-Anomalie muss entdeckt werden').toBeTruthy();
        expect(elx.severity).toMatch(/info|warning/);
        expect(elx.deviationPct).toBeLessThan(-30);
    });

    test('Kleine Werte (< minAbs) werden ignoriert (Rauschen)', async ({ page }) => {
        await openDashboard(page);
        // auftraege = 3 heute, aber minAbs=5 → soll nicht auslösen
        const snaps = {
            '2026-04-20': { gesamtStueck: 10, lagerStueck: 8,  kommStueck: 2, weStueck: 0, auftraege: 3 },
            '2026-04-19': { gesamtStueck: 20, lagerStueck: 15, kommStueck: 5, weStueck: 0, auftraege: 8 },
            '2026-04-18': { gesamtStueck: 22, lagerStueck: 17, kommStueck: 5, weStueck: 0, auftraege: 9 },
            '2026-04-17': { gesamtStueck: 19, lagerStueck: 14, kommStueck: 5, weStueck: 0, auftraege: 7 },
        };
        const result = await page.evaluate((s) => window.detectAnomalies(s), snaps);
        // Alle Metriken heute < minAbs → keine Anomalien
        expect(result).toEqual([]);
    });
});
