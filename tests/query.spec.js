// @ts-check
import { test, expect } from '@playwright/test';
import { openDashboard } from './helpers.js';

/**
 * 10X-7 Tests. LLM-Backends sind in Playwright-Chromium nicht verfügbar
 * (kein chrome://flags-Toggle aktiv) → Tests fokussieren auf Regex-Parser,
 * applyQuery, Schema-Validation, Backend-Detection-Fallback.
 */

test.describe('parseNaturalQuery (10X-7)', () => {
    test('Lagertage-Filter: "älter 180 tage"', async ({ page }) => {
        await openDashboard(page);
        const q = await page.evaluate(() => window.parseNaturalQuery('älter 180 tage'));
        const f = q.filters.find(x => x.field === 'lifeDays');
        expect(f).toBeTruthy();
        expect(f.value).toBe(180);
        expect(['gt', 'gte']).toContain(f.op);
    });

    test('Marge-Filter: "marge unter 10%"', async ({ page }) => {
        await openDashboard(page);
        const q = await page.evaluate(() => window.parseNaturalQuery('marge unter 10%'));
        const f = q.filters.find(x => x.field === 'margePct');
        expect(f).toBeTruthy();
        expect(f.value).toBe(10);
        expect(f.op).toBe('lt');
    });

    test('Marken-Erkennung: "Siemens"', async ({ page }) => {
        await openDashboard(page);
        const q = await page.evaluate(() => window.parseNaturalQuery('Siemens Paletten'));
        const f = q.filters.find(x => x.field === 'brand');
        expect(f).toBeTruthy();
        expect(f.value).toBe('siemens');
    });

    test('Status-Filter: "QU"', async ({ page }) => {
        await openDashboard(page);
        const q = await page.evaluate(() => window.parseNaturalQuery('aufträge im status QU'));
        const f = q.filters.find(x => x.field === 'status');
        expect(f).toBeTruthy();
        expect(f.value).toBe('QU');
    });

    test('Kombi-Query: Marke + Lagertage + Marge', async ({ page }) => {
        await openDashboard(page);
        const q = await page.evaluate(() =>
            window.parseNaturalQuery('Siemens älter 180 tage marge unter 10%'));
        const fields = q.filters.map(f => f.field).sort();
        expect(fields).toEqual(['brand', 'lifeDays', 'margePct']);
    });

    test('Lager-Nr-Erkennung: "9001234567"', async ({ page }) => {
        await openDashboard(page);
        const q = await page.evaluate(() => window.parseNaturalQuery('lager 9001234567'));
        const f = q.filters.find(x => x.field === 'lagerNr');
        expect(f).toBeTruthy();
        expect(f.value).toBe('9001234567');
    });

    test('Leere Query → 0 Filter + Note', async ({ page }) => {
        await openDashboard(page);
        const q = await page.evaluate(() => window.parseNaturalQuery(''));
        expect(q.filters).toEqual([]);
    });
});

test.describe('applyQuery (10X-7)', () => {
    test('Brand-Filter trifft case-insensitive', async ({ page }) => {
        await openDashboard(page);
        const out = await page.evaluate(() => {
            window.state.portal.stockAnalysisRaw = [
                { lager_number: '9001', brand: 'Siemens',  product_life_days: 200, Buying_Price: 100, Selling_Price: 110 },
                { lager_number: '9002', brand: 'Bosch',    product_life_days: 100, Buying_Price: 100, Selling_Price: 200 },
                { lager_number: '9003', brand: 'siemens',  product_life_days: 300, Buying_Price: 100, Selling_Price: 90 },
            ];
            const q = { filters: [{ field: 'brand', op: 'contains', value: 'siemens' }] };
            return window.applyQuery(q);
        });
        expect(out.items.length).toBe(2);
        expect(out.applied).toBe(1);
        expect(out.total).toBe(3);
    });

    test('LifeDays-Filter (gt) funktioniert', async ({ page }) => {
        await openDashboard(page);
        const out = await page.evaluate(() => {
            window.state.portal.stockAnalysisRaw = [
                { lager_number: '1', product_life_days: 50 },
                { lager_number: '2', product_life_days: 200 },
                { lager_number: '3', product_life_days: 300 },
            ];
            return window.applyQuery({ filters: [{ field: 'lifeDays', op: 'gt', value: 180 }] });
        });
        expect(out.items.length).toBe(2);
    });

    test('Marge-Filter rechnet ek/vk korrekt', async ({ page }) => {
        await openDashboard(page);
        const out = await page.evaluate(() => {
            window.state.portal.stockAnalysisRaw = [
                { lager_number: '1', Buying_Price: 100, Selling_Price: 200 },  // 100% Marge
                { lager_number: '2', Buying_Price: 100, Selling_Price: 105 },  // 5% Marge
                { lager_number: '3', Buying_Price: 100, Selling_Price: 90 },   // -10% Marge
            ];
            return window.applyQuery({ filters: [{ field: 'margePct', op: 'lt', value: 10 }] });
        });
        // 5% und -10% sind unter 10
        expect(out.items.length).toBe(2);
        expect(out.items.map(i => i.lager_number).sort()).toEqual(['2', '3']);
    });

    test('Mehrere Filter werden mit AND verknüpft', async ({ page }) => {
        await openDashboard(page);
        const out = await page.evaluate(() => {
            window.state.portal.stockAnalysisRaw = [
                { lager_number: '1', brand: 'Siemens', product_life_days: 200 },
                { lager_number: '2', brand: 'Bosch',   product_life_days: 200 },
                { lager_number: '3', brand: 'Siemens', product_life_days: 50 },
            ];
            return window.applyQuery({ filters: [
                { field: 'brand', op: 'contains', value: 'siemens' },
                { field: 'lifeDays', op: 'gt', value: 100 }
            ]});
        });
        expect(out.items.length).toBe(1);
        expect(out.items[0].lager_number).toBe('1');
    });
});

test.describe('LLM-Backend-Detection + Schema-Validation (10X-7)', () => {
    test('getLLMBackend liefert "none" in Test-Browser', async ({ page }) => {
        await openDashboard(page);
        const backend = await page.evaluate(() => window.getLLMBackend());
        expect(backend).toBe('none');
    });

    test('validateQuerySchema verwirft unbekannte Felder', async ({ page }) => {
        await openDashboard(page);
        const out = await page.evaluate(() => window.validateQuerySchema({
            filters: [
                { field: 'brand',  op: 'eq', value: 'siemens' },     // ok
                { field: 'pwntag', op: 'eq', value: 'xyz' },          // unbekanntes Feld
                { field: 'ek',     op: 'pwn', value: 100 }             // unbekannte Op
            ]
        }));
        expect(out.filters.length).toBe(1);
        expect(out.filters[0].field).toBe('brand');
        expect(out.note).toContain('verworfen');
    });

    test('validateQuerySchema akzeptiert leeres Schema', async ({ page }) => {
        await openDashboard(page);
        const out = await page.evaluate(() => window.validateQuerySchema({ filters: [] }));
        expect(out.filters).toEqual([]);
    });

    test('validateQuerySchema robust gegen Müll', async ({ page }) => {
        await openDashboard(page);
        const out = await page.evaluate(() => window.validateQuerySchema(null));
        expect(out.filters).toEqual([]);
        expect(out.note).toContain('invalid');
    });
});

test.describe('askDashboard E2E (10X-7)', () => {
    test('Regex-Hit returnt source=regex, ohne LLM', async ({ page }) => {
        await openDashboard(page);
        const out = await page.evaluate(async () => {
            window.state.portal.stockAnalysisRaw = [
                { lager_number: '1', brand: 'Siemens', product_life_days: 200 },
            ];
            return await window.askDashboard('siemens', { tryLLM: false });
        });
        expect(out.source).toBe('regex');
        expect(out.items.length).toBe(1);
    });

    test('Regex-Miss + tryLLM=false → hint "LLM nutzen"', async ({ page }) => {
        await openDashboard(page);
        const out = await page.evaluate(async () => {
            return await window.askDashboard('zeig mir alles relevante über q4', { tryLLM: false });
        });
        expect(out.source).toBe('regex');
        expect(out.applied).toBe(0);
        expect(out.hint).toContain('LLM');
    });

    test('Regex-Miss + tryLLM=true ohne Backend → source=error', async ({ page }) => {
        await openDashboard(page);
        const out = await page.evaluate(async () => {
            return await window.askDashboard('xyz fancy nlp', { tryLLM: true });
        });
        expect(out.source).toBe('error');
        expect(out.error).toContain('LLM');
    });
});
