// @ts-check
import { test, expect } from '@playwright/test';
import { openDashboard } from './helpers.js';

/**
 * 10X-8 Tests. computeParetoAnalysis + computeCustomerMatches + Mail-Drafts.
 * Daten werden direkt im evaluate-Block gesetzt — kein File-Upload nötig.
 */

test.describe('Pareto-Analyse (10X-8)', () => {
    test('Leeres Array → 0 Potenzial', async ({ page }) => {
        await openDashboard(page);
        const out = await page.evaluate(() => window.computeParetoAnalysis([]));
        expect(out.totalPotential).toBe(0);
        expect(out.threshold80Idx).toBe(-1);
    });

    test('Sortiert nach Profit-Potenzial absteigend', async ({ page }) => {
        await openDashboard(page);
        const out = await page.evaluate(() => window.computeParetoAnalysis([
            { bezeichnung: 'klein', maxEK: 100, menge: 1 },
            { bezeichnung: 'gross', maxEK: 1000, menge: 10 },
            { bezeichnung: 'mittel', maxEK: 500, menge: 5 }
        ]));
        // gross hat highest potential = (1000/0.55 - 1000)*10 ≈ 8181 → an erster Stelle
        expect(out.items[0].bezeichnung).toBe('gross');
        expect(out.items[2].bezeichnung).toBe('klein');
    });

    test('80%-Threshold-Index findet Top-Items', async ({ page }) => {
        await openDashboard(page);
        const out = await page.evaluate(() => window.computeParetoAnalysis([
            { bezeichnung: 'A', maxEK: 1000, menge: 100 }, // dominanter Anteil
            { bezeichnung: 'B', maxEK: 50,   menge: 1 },
            { bezeichnung: 'C', maxEK: 50,   menge: 1 },
            { bezeichnung: 'D', maxEK: 50,   menge: 1 },
            { bezeichnung: 'E', maxEK: 50,   menge: 1 }
        ]));
        // Item A allein > 80% → threshold80Idx = 0
        expect(out.threshold80Idx).toBe(0);
        expect(out.top80Count).toBe(1);
    });

    test('Cumulative-% läuft monoton bis 100', async ({ page }) => {
        await openDashboard(page);
        const out = await page.evaluate(() => window.computeParetoAnalysis([
            { maxEK: 200, menge: 5 }, { maxEK: 100, menge: 3 }, { maxEK: 50, menge: 2 }
        ]));
        const cumPcts = out.items.map(i => i._cumPct);
        for (let i = 1; i < cumPcts.length; i++) {
            expect(cumPcts[i]).toBeGreaterThanOrEqual(cumPcts[i-1]);
        }
        expect(cumPcts[cumPcts.length - 1]).toBe(100);
    });
});

test.describe('Customer-Matching (10X-8)', () => {
    test('Aggregiert Kunden über mehrere Items', async ({ page }) => {
        await openDashboard(page);
        const out = await page.evaluate(() => {
            // Setup: kundenWgStats mock
            window.state.portal.kundenWgStats = {
                'Müller GmbH':  { 'waschmaschine': { count: 50, umsatz: 25000 },
                                  'wäschetrockner': { count: 30, umsatz: 15000 } },
                'Schmidt KG':   { 'waschmaschine': { count: 10, umsatz: 5000 } }
            };
            const offers = [
                { bezeichnung: 'WaMa Siemens', artikelgruppe: 'waschmaschine', menge: 10, maxEK: 200 },
                { bezeichnung: 'Trockner Bosch', artikelgruppe: 'wäschetrockner', menge: 5, maxEK: 250 }
            ];
            return window.computeCustomerMatches(offers);
        });
        // Müller hat beide WGs → 2 Items, Schmidt nur 1
        const mueller = out.find(m => m.kunde === 'Müller GmbH');
        const schmidt = out.find(m => m.kunde === 'Schmidt KG');
        expect(mueller).toBeTruthy();
        expect(mueller.itemCount).toBe(2);
        expect(mueller.wgs.sort()).toEqual(['waschmaschine', 'wäschetrockner']);
        expect(schmidt.itemCount).toBe(1);
        // Müller hat höheres Potenzial → früher in der Sortierung
        expect(out.indexOf(mueller)).toBeLessThan(out.indexOf(schmidt));
    });

    test('Keine kundenWgStats → leeres Match-Array', async ({ page }) => {
        await openDashboard(page);
        const out = await page.evaluate(() => {
            window.state.portal.kundenWgStats = {};
            return window.computeCustomerMatches([
                { bezeichnung: 'X', artikelgruppe: 'wama', menge: 1, maxEK: 100 }
            ]);
        });
        expect(out).toEqual([]);
    });
});

test.describe('Mail-Drafts (10X-8)', () => {
    test('buildMailto erstellt korrekten URL mit URL-encoded Body', async ({ page }) => {
        await openDashboard(page);
        const url = await page.evaluate(() =>
            window.buildMailto('test@example.com', 'Hallo', 'Body mit Umlaut äöü & Sonderzeichen')
        );
        expect(url.startsWith('mailto:test%40example.com')).toBe(true);
        expect(url).toContain('subject=Hallo');
        expect(url).toContain('Sonderzeichen');
        expect(url).toContain('%C3%A4'); // ä URL-encoded
    });

    test('openSupplierMailDraft emittiert angebot:mail-draft', async ({ page }) => {
        await openDashboard(page);
        // Hinweis: window.location ist in modernen Chromium nicht mehr per
        // Object.defineProperty stub-bar (TypeError "Cannot redefine property: location").
        // Bug-Fix dafür im Dashboard: openSupplierMailDraft emittiert Bus-Event VOR
        // dem location.href-Setter. Test verlässt sich auf diese Reihenfolge —
        // der echte mailto:-Redirect wird in Headless-Chromium ignoriert (kein Handler).
        const captured = await page.evaluate(async () => {
            window.dashboardState.angebotAnalyseResults = [
                { bezeichnung: 'WaMa', bezeichnungFull: 'Waschmaschine X', menge: 10, maxEK: 200, listenVK: 400, empfehlung: '🟢' },
                { bezeichnung: 'Trockner', bezeichnungFull: 'Wäschetrockner Y', menge: 5, maxEK: 250, listenVK: 500, empfehlung: '🔴' }
            ];
            const events = [];
            window.bus.on('angebot:mail-draft', (p) => events.push(p));
            try { window.openSupplierMailDraft('counter'); } catch (_) { /* mailto-redirect kann scheitern, Event ist trotzdem gefeuert */ }
            return events;
        });
        expect(captured.length).toBe(1);
        expect(captured[0].target).toBe('supplier');
        expect(captured[0].mode).toBe('counter');
    });

    test('openSupplierMailDraft Toast wenn keine Daten', async ({ page }) => {
        await openDashboard(page);
        const out = await page.evaluate(() => {
            window.dashboardState.angebotAnalyseResults = [];
            const toasts = [];
            const orig = window.showToast;
            window.showToast = (type, title, msg) => { toasts.push({ type, title, msg }); };
            window.openSupplierMailDraft('counter');
            window.showToast = orig;
            return toasts;
        });
        expect(out.length).toBe(1);
        expect(out[0].type).toBe('warning');
    });

    test('Customer-MailDraft: Kunde nicht gefunden → Warning', async ({ page }) => {
        await openDashboard(page);
        const out = await page.evaluate(() => {
            window.state.portal.kundenWgStats = {};
            window.dashboardState.angebotAnalyseResults = [
                { bezeichnung: 'X', artikelgruppe: 'wama', menge: 1, maxEK: 100 }
            ];
            const toasts = [];
            const orig = window.showToast;
            window.showToast = (type, title, msg) => { toasts.push({ type, title, msg }); };
            window.openCustomerMailDraft('Phantom GmbH');
            window.showToast = orig;
            return toasts;
        });
        expect(out[0].type).toBe('warning');
    });
});
