// @ts-check
import { test, expect } from '@playwright/test';
import { openDashboard } from './helpers.js';

/**
 * Regression-Tests für 10X-3 Offline-Pfeiler (IndexedDB + CDN-Health).
 * Tests laufen isoliert in einer eigenen DB (elvinci_test_idb), damit echte
 * User-Daten nicht berührt werden.
 */
test.describe('IndexedDB Store (10X-3)', () => {
    test('createIDBStore ist global verfügbar', async ({ page }) => {
        await openDashboard(page);
        const ok = await page.evaluate(() => typeof window.createIDBStore === 'function');
        expect(ok).toBe(true);
    });

    test('put → get → delete Roundtrip', async ({ page }) => {
        await openDashboard(page);
        const out = await page.evaluate(async () => {
            const store = window.createIDBStore('elvinci_test_idb', 'kv', 1, 'id');
            await store.clear();
            await store.put({ id: 'foo', value: 42 });
            const got = await store.get('foo');
            await store.delete('foo');
            const gone = await store.get('foo');
            return { got, gone };
        });
        expect(out.got).toEqual({ id: 'foo', value: 42 });
        expect(out.gone).toBeUndefined();
    });

    test('getAll returniert Array, count zählt Einträge', async ({ page }) => {
        await openDashboard(page);
        const out = await page.evaluate(async () => {
            const store = window.createIDBStore('elvinci_test_idb', 'kv', 1, 'id');
            await store.clear();
            await store.put({ id: 'a', n: 1 });
            await store.put({ id: 'b', n: 2 });
            await store.put({ id: 'c', n: 3 });
            const all = await store.getAll();
            const count = await store.count();
            await store.clear();
            return { allLen: all.length, count, sum: all.reduce((s, r) => s + r.n, 0) };
        });
        expect(out.allLen).toBe(3);
        expect(out.count).toBe(3);
        expect(out.sum).toBe(6);
    });

    test('clear leert Store vollständig', async ({ page }) => {
        await openDashboard(page);
        const out = await page.evaluate(async () => {
            const store = window.createIDBStore('elvinci_test_idb', 'kv', 1, 'id');
            await store.put({ id: 'x', v: 1 });
            await store.put({ id: 'y', v: 2 });
            await store.clear();
            const count = await store.count();
            return count;
        });
        expect(out).toBe(0);
    });

    test('persistSnapshotToIDB speichert Rich-Snapshot', async ({ page }) => {
        await openDashboard(page);
        const out = await page.evaluate(async () => {
            // Setup minimal dashboardState
            window.state.inventory.bestandLoaded = true;
            window.state.inventory.bestandGesamtStueck = 500;
            window.state.inventory.bestandLagerStueck = 400;
            window.state.inventory.bestandKommStueck = 80;
            window.state.inventory.bestandWEStueck = 20;
            window.state.inventory.bestandAuftragMap = { 'AU1': {}, 'AU2': {} };

            await window.persistSnapshotToIDB();
            const today = new Date().toISOString().split('T')[0];
            const snap = await window.idbStores.snapshots().get(today);
            return snap;
        });
        expect(out).toBeTruthy();
        expect(out.inventory.bestandLoaded).toBe(true);
        expect(out.inventory.bestandGesamtStueck).toBe(500);
        expect(out.inventory.auftraegeCount).toBe(2);
        expect(out.portal.stockAnalysisLoaded).toBe(false);
        expect(out.portal.brandBreakdown).toBeNull();
    });
});

test.describe('CDN-Health-Check (10X-3)', () => {
    test('detectCDNAvailability liefert alle 6 Flags', async ({ page }) => {
        await openDashboard(page);
        const result = await page.evaluate(() => window.detectCDNAvailability());
        expect(result).toHaveProperty('chartJs');
        expect(result).toHaveProperty('papaParse');
        expect(result).toHaveProperty('xlsx');
        expect(result).toHaveProperty('jsPDF');
        expect(result).toHaveProperty('online');
        expect(result).toHaveProperty('indexedDB');
        expect(result.indexedDB).toBe(true); // Playwright-Chromium hat immer IDB
    });

    test('renderOfflineBanner fügt Banner hinzu wenn offline', async ({ page }) => {
        await openDashboard(page);
        await page.evaluate(() => {
            // Fake offline-Status
            Object.defineProperty(navigator, 'onLine', { configurable: true, get: () => false });
            window.renderOfflineBanner();
        });
        const banner = await page.$('#offline-banner');
        expect(banner, 'Offline-Banner sollte existieren').not.toBeNull();
        const html = await page.evaluate(() => document.getElementById('offline-banner')?.innerHTML || '');
        expect(html).toContain('Offline');
    });
});
