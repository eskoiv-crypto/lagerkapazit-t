// @ts-check
import { test, expect } from '@playwright/test';
import { openDashboard } from './helpers.js';

/**
 * Sprint 7: P2-1 + P2-5 Refactor-Schulden.
 * Tests für aggregateEntities() und runUnifiedValidation().
 * Helper sind verfügbar, aber existing call-sites bleiben unverändert —
 * Migration erfolgt file-by-file mit Smoke-Test-Begleitung.
 */

test.describe('aggregateEntities (P2-1)', () => {
    const sampleData = [
        { customer: 'Müller', umsatz: 100, profit: 30, brand: 'Siemens', ordernr: 'O1' },
        { customer: 'Müller', umsatz: 200, profit: 60, brand: 'Bosch',   ordernr: 'O2' },
        { customer: 'Müller', umsatz: 150, profit: 45, brand: 'Siemens', ordernr: 'O1' },
        { customer: 'Schmidt',umsatz: 300, profit: 90, brand: 'Miele',   ordernr: 'O3' }
    ];

    test('Sum + Count aggregieren korrekt', async ({ page }) => {
        await openDashboard(page);
        const result = await page.evaluate((data) => window.aggregateEntities(data, {
            keyField: 'customer',
            metrics: {
                umsatz: { op: 'sum', from: 'umsatz' },
                profit: { op: 'sum', from: 'profit' },
                count:  { op: 'count' }
            }
        }), sampleData);
        const mueller = result.find(g => g._key === 'Müller');
        const schmidt = result.find(g => g._key === 'Schmidt');
        expect(mueller.umsatz).toBe(450);
        expect(mueller.profit).toBe(135);
        expect(mueller.count).toBe(3);
        expect(schmidt.umsatz).toBe(300);
        expect(schmidt.count).toBe(1);
    });

    test('Distinct-Count zählt unique Werte', async ({ page }) => {
        await openDashboard(page);
        const result = await page.evaluate((data) => window.aggregateEntities(data, {
            keyField: 'customer',
            metrics: { uniqueOrders: { op: 'distinct', from: 'ordernr' } }
        }), sampleData);
        const mueller = result.find(g => g._key === 'Müller');
        // 3 Items, 2 unique ordernr (O1 zweimal)
        expect(mueller.uniqueOrders).toBe(2);
    });

    test('Avg berechnet Durchschnitt', async ({ page }) => {
        await openDashboard(page);
        const result = await page.evaluate((data) => window.aggregateEntities(data, {
            keyField: 'customer',
            metrics: { avgOrder: { op: 'avg', from: 'umsatz' } }
        }), sampleData);
        const mueller = result.find(g => g._key === 'Müller');
        // (100+200+150) / 3 = 150
        expect(mueller.avgOrder).toBe(150);
    });

    test('Max + Min funktionieren', async ({ page }) => {
        await openDashboard(page);
        const result = await page.evaluate((data) => window.aggregateEntities(data, {
            keyField: 'customer',
            metrics: {
                maxUmsatz: { op: 'max', from: 'umsatz' },
                minUmsatz: { op: 'min', from: 'umsatz' }
            }
        }), sampleData);
        const mueller = result.find(g => g._key === 'Müller');
        expect(mueller.maxUmsatz).toBe(200);
        expect(mueller.minUmsatz).toBe(100);
    });

    test('SubgroupBy + pickTopSubgroup liefert Top-Brand pro Kunde', async ({ page }) => {
        await openDashboard(page);
        const result = await page.evaluate((data) => {
            const groups = window.aggregateEntities(data, {
                keyField: 'customer',
                metrics: { umsatz: { op: 'sum', from: 'umsatz' } },
                subgroupBy: { brand: 'brand' }
            });
            return groups.map(g => ({
                key: g._key,
                topBrand: window.pickTopSubgroup(g, 'brand', 'umsatz')
            }));
        }, sampleData);
        const mueller = result.find(g => g.key === 'Müller');
        // Siemens: 100+150 = 250, Bosch: 200 → Siemens gewinnt
        expect(mueller.topBrand.key).toBe('Siemens');
        expect(mueller.topBrand.value).toBe(250);
    });

    test('Filter-Option entfernt kleine Gruppen', async ({ page }) => {
        await openDashboard(page);
        const result = await page.evaluate((data) => window.aggregateEntities(data, {
            keyField: 'customer',
            metrics: { count: { op: 'count' } },
            filter: g => g._count >= 2
        }), sampleData);
        // Schmidt hat nur 1 Item → rausgefiltert
        expect(result.length).toBe(1);
        expect(result[0]._key).toBe('Müller');
    });

    test('keyField als Function für Computed-Keys', async ({ page }) => {
        await openDashboard(page);
        const result = await page.evaluate((data) => window.aggregateEntities(data, {
            keyField: (it) => (it.umsatz >= 200 ? 'big' : 'small'),
            metrics: { count: { op: 'count' } }
        }), sampleData);
        const big = result.find(g => g._key === 'big');
        const small = result.find(g => g._key === 'small');
        expect(big._count).toBe(2);   // 200 + 300
        expect(small._count).toBe(2); // 100 + 150
    });

    test('Leeres Array → leeres Result', async ({ page }) => {
        await openDashboard(page);
        const result = await page.evaluate(() =>
            window.aggregateEntities([], { keyField: 'x', metrics: { c: { op: 'count' } } }));
        expect(result).toEqual([]);
    });
});

test.describe('runUnifiedValidation (P2-5)', () => {
    test('Leere Datenbasis → leere Outputs', async ({ page }) => {
        await openDashboard(page);
        const result = await page.evaluate(() => {
            window.resetAllSessionState();
            return window.runUnifiedValidation();
        });
        expect(result.diskrepanzen).toEqual([]);
        expect(result.mismatches).toEqual([]);
        expect(result.fourWayStats.total).toBe(0);
    });

    test('Mengen-Diff zwischen BESTAND und STATUS landet in BEIDEN Schemas', async ({ page }) => {
        await openDashboard(page);
        const result = await page.evaluate(() => {
            window.resetAllSessionState();
            window.state.inventory.bestandAuftragMap = { 'AU1': { count: 5 } };
            window.state.orders.auftragStatusMap = { 'AU1': { status: 'QU', artikel: 3 } };
            return window.runUnifiedValidation();
        });
        // diskrepanzen-Schema (validateAuftraege)
        const d = result.diskrepanzen.find(x => x.auftrag === 'AU1');
        expect(d.typ).toBe('anzahl_diff');
        expect(d.bestand).toBe(5);
        expect(d.status).toBe(3);
        // mismatches-Schema (runValidation)
        const m = result.mismatches.find(x => x.auftrag === 'AU1' && x.typ === 'mengen_diff');
        expect(m).toBeTruthy();
        expect(m.schwere).toBe('info');
    });

    test('Auftrag nur in BESTAND → "nur_bestand" + "bestand_ohne_status"', async ({ page }) => {
        await openDashboard(page);
        const result = await page.evaluate(() => {
            window.resetAllSessionState();
            window.state.inventory.bestandAuftragMap = { 'AU2': { count: 7 } };
            return window.runUnifiedValidation();
        });
        expect(result.diskrepanzen.find(d => d.typ === 'nur_bestand')).toBeTruthy();
        expect(result.mismatches.find(m => m.typ === 'bestand_ohne_status')).toBeTruthy();
    });

    test('🚨 Fulfillment ohne BESTAND wird als warnung markiert', async ({ page }) => {
        await openDashboard(page);
        const result = await page.evaluate(() => {
            window.resetAllSessionState();
            window.state.pipeline.fulfillmentDataMap = {
                'AU3': { versandDatum: '2026-05-01', kunde: 'Test' }
            };
            return window.runUnifiedValidation();
        });
        const mismatch = result.mismatches.find(m => m.typ === 'fulfillment_ohne_bestand');
        expect(mismatch).toBeTruthy();
        expect(mismatch.schwere).toBe('warnung');
    });

    test('4-Way-Stats zählt korrekt', async ({ page }) => {
        await openDashboard(page);
        const result = await page.evaluate(() => {
            window.resetAllSessionState();
            window.state.inventory.bestandAuftragMap = { 'A': {}, 'B': {}, 'C': {}, 'D': {} };
            window.state.orders.auftragStatusMap     = { 'A': {}, 'B': {}, 'C': {} };
            window.state.pipeline.fulfillmentDataMap = { 'A': {}, 'B': {} };
            window.state.orders.plannerDataMap       = { 'A': {} };
            // A in 4 Systemen, B in 3, C in 2, D in 1
            return window.runUnifiedValidation();
        });
        expect(result.fourWayStats.complete).toBe(1);     // A
        expect(result.fourWayStats.threeOfFour).toBe(1);  // B
        expect(result.fourWayStats.twoOfFour).toBe(1);    // C
        expect(result.fourWayStats.oneOfFour).toBe(1);    // D
        expect(result.fourWayStats.total).toBe(4);
    });

    test('Single-Fulfillment-Orphan landet in orphans4Way', async ({ page }) => {
        await openDashboard(page);
        const result = await page.evaluate(() => {
            window.resetAllSessionState();
            window.state.pipeline.fulfillmentDataMap = { 'XYZ': { versandDatum: '?' } };
            return window.runUnifiedValidation();
        });
        expect(result.orphans4Way.length).toBe(1);
        expect(result.orphans4Way[0].auNr).toBe('XYZ');
        expect(result.orphans4Way[0].onlyIn).toBe('Fulfillment');
    });
});
