// @ts-check
import { test, expect } from '@playwright/test';
import { openDashboard } from './helpers.js';

/**
 * Regression-Tests für 10X-1 Domain-View (Data-Model-Split).
 * Stellt sicher: state.inventory.X und dashboardState.X sind immer dieselbe Storage.
 * Bidirektional — schreiben über A liest über B und umgekehrt.
 */
test.describe('Domain-Views (10X-1)', () => {
    test('Alle 6 Domains sind unter window.state verfügbar', async ({ page }) => {
        await openDashboard(page);
        const domains = await page.evaluate(() => ({
            inventory: typeof window.state.inventory === 'object',
            pipeline:  typeof window.state.pipeline === 'object',
            portal:    typeof window.state.portal === 'object',
            orders:    typeof window.state.orders === 'object',
            analysis:  typeof window.state.analysis === 'object',
            config:    typeof window.state.config === 'object',
        }));
        expect(domains).toEqual({
            inventory: true, pipeline: true, portal: true,
            orders: true, analysis: true, config: true,
        });
    });

    test('Write via state.X reflected in dashboardState (bidirectional)', async ({ page }) => {
        await openDashboard(page);
        const out = await page.evaluate(() => {
            window.state.inventory.bestandLoaded = true;
            window.state.inventory.bestandLager = 4200;
            window.state.inventory.avgPktProGeraet = 0.88;
            return {
                bestandLoadedFromOld: window.dashboardState.bestandLoaded,
                bestandLagerFromOld:  window.dashboardState.bestandLager,
                avgPktFromOld:        window.dashboardState.avgPktProGeraet,
            };
        });
        expect(out.bestandLoadedFromOld).toBe(true);
        expect(out.bestandLagerFromOld).toBe(4200);
        expect(out.avgPktFromOld).toBe(0.88);
    });

    test('Write via dashboardState reflected in state.X (bidirectional)', async ({ page }) => {
        await openDashboard(page);
        const out = await page.evaluate(() => {
            window.dashboardState.stockAnalysisLoaded = true;
            window.dashboardState.stockAnalysisCount = 789;
            window.dashboardState.allSoldCount = 1234;
            return {
                stockLoadedFromNew: window.state.portal.stockAnalysisLoaded,
                stockCountFromNew:  window.state.portal.stockAnalysisCount,
                allSoldCountFromNew: window.state.portal.allSoldCount,
            };
        });
        expect(out.stockLoadedFromNew).toBe(true);
        expect(out.stockCountFromNew).toBe(789);
        expect(out.allSoldCountFromNew).toBe(1234);
    });

    test('Config-Domain exponiert Kapazitäts-Felder', async ({ page }) => {
        await openDashboard(page);
        const cfg = await page.evaluate(() => ({
            kapazitaet: window.state.config.kapazitaet,
            quKapazitaet: window.state.config.quKapazitaet,
            flaecheQm: window.state.config.flaecheQm,
            palettenProQm: window.state.config.palettenProQm,
        }));
        expect(cfg.kapazitaet).toBeGreaterThan(1000);
        expect(cfg.quKapazitaet).toBe(2350);
        expect(cfg.flaecheQm).toBe(2766);
        expect(cfg.palettenProQm).toBeCloseTo(0.565, 3);
    });

    test('Maps/Objects bleiben dieselbe Referenz — Mutation funktioniert', async ({ page }) => {
        await openDashboard(page);
        const out = await page.evaluate(() => {
            // Mutation auf dem geteilten Map — muss über beide Views sichtbar sein
            window.state.orders.auftragStatusMap['AU999'] = { status: 'QU', kunde: 'TestCo' };
            const viaOld = window.dashboardState.auftragStatusMap['AU999'];
            const viaNew = window.state.orders.auftragStatusMap['AU999'];
            return {
                sameReference: viaOld === viaNew,
                viaOldStatus: viaOld && viaOld.status,
                viaNewKunde:  viaNew && viaNew.kunde,
            };
        });
        expect(out.sameReference).toBe(true);
        expect(out.viaOldStatus).toBe('QU');
        expect(out.viaNewKunde).toBe('TestCo');
    });

    test('resetAllSessionState leert Domain-Views (Sprint 2 Regression)', async ({ page }) => {
        await openDashboard(page);
        const out = await page.evaluate(() => {
            window.state.inventory.bestandLoaded = true;
            window.state.inventory.bestandLager = 5000;
            window.state.portal.stockAnalysisLoaded = true;
            window.state.portal.kundenStats = { 'Foo GmbH': { umsatz: 999 } };
            window.state.analysis.anomalies = [{ metric: 'x' }];

            window.resetAllSessionState();

            return {
                invLoaded: window.state.inventory.bestandLoaded,
                invLager: window.state.inventory.bestandLager,
                portalLoaded: window.state.portal.stockAnalysisLoaded,
                kundenKeys: Object.keys(window.state.portal.kundenStats).length,
            };
        });
        expect(out.invLoaded).toBe(false);
        expect(out.invLager).toBe(0);
        expect(out.portalLoaded).toBe(false);
        expect(out.kundenKeys).toBe(0);
    });

    test('createDomainView-Factory liefert isolierte Views für neue Zwecke', async ({ page }) => {
        await openDashboard(page);
        const out = await page.evaluate(() => {
            const backing = { foo: 1, bar: 'hello' };
            const view = window.createDomainView(backing, ['foo', 'bar']);
            view.foo = 42;
            view.bar = 'world';
            return { backing, enumerable: Object.keys(view) };
        });
        expect(out.backing).toEqual({ foo: 42, bar: 'world' });
        expect(out.enumerable.sort()).toEqual(['bar', 'foo']);
    });
});
