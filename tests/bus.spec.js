// @ts-check
import { test, expect } from '@playwright/test';
import { openDashboard } from './helpers.js';

/**
 * Regression-Tests für 10X-2 EventBus.
 * Wir testen gegen eine FRISCHE Bus-Instanz (createEventBus()), nicht die globale window.bus
 * — sonst würden unsere Handler mit den Legacy-Subscribers kollidieren.
 */
test.describe('EventBus (10X-2)', () => {
    test('on + emit liefert Payload an Handler', async ({ page }) => {
        await openDashboard(page);
        const out = await page.evaluate(() => {
            const b = window.createEventBus();
            const got = [];
            b.on('foo', (p) => got.push(p));
            const delivered1 = b.emit('foo', { x: 1 });
            const delivered2 = b.emit('foo', { x: 2 });
            return { got, delivered1, delivered2 };
        });
        expect(out.got).toEqual([{ x: 1 }, { x: 2 }]);
        expect(out.delivered1).toBe(1);
        expect(out.delivered2).toBe(1);
    });

    test('off entfernt Handler', async ({ page }) => {
        await openDashboard(page);
        const out = await page.evaluate(() => {
            const b = window.createEventBus();
            const got = [];
            const h = (p) => got.push(p);
            b.on('bar', h);
            b.emit('bar', 1);
            b.off('bar', h);
            b.emit('bar', 2);
            return got;
        });
        expect(out).toEqual([1]);
    });

    test('once feuert genau einmal', async ({ page }) => {
        await openDashboard(page);
        const out = await page.evaluate(() => {
            const b = window.createEventBus();
            let n = 0;
            b.once('ping', () => n++);
            b.emit('ping');
            b.emit('ping');
            b.emit('ping');
            return n;
        });
        expect(out).toBe(1);
    });

    test('unsubscribe-Token aus on() funktioniert', async ({ page }) => {
        await openDashboard(page);
        const out = await page.evaluate(() => {
            const b = window.createEventBus();
            let n = 0;
            const unsub = b.on('tick', () => n++);
            b.emit('tick');
            b.emit('tick');
            unsub();
            b.emit('tick');
            return n;
        });
        expect(out).toBe(2);
    });

    test('Ein kaputter Handler stoppt nicht die Kette (Error-Isolation)', async ({ page }) => {
        await openDashboard(page);
        const out = await page.evaluate(() => {
            const b = window.createEventBus();
            const got = [];
            b.on('boom', () => got.push('a'));
            b.on('boom', () => { throw new Error('intentional'); });
            b.on('boom', () => got.push('c'));
            const delivered = b.emit('boom');
            return { got, delivered };
        });
        expect(out.got).toEqual(['a', 'c']);
        expect(out.delivered).toBe(2); // 2 erfolgreiche Handler, 1 crashed
    });

    test('Globaler bus hat Legacy-Subscribers nach DOMContentLoaded', async ({ page }) => {
        await openDashboard(page);
        const count = await page.evaluate(() => window.bus.listenerCount('data:refresh'));
        // mindestens updateStats, updateGauge, updateChart, renderAnomaliesPanel ...
        expect(count).toBeGreaterThanOrEqual(8);
    });

    test('data:reset wird beim resetAllSessionState emittiert', async ({ page }) => {
        await openDashboard(page);
        const got = await page.evaluate(() => {
            const received = [];
            window.bus.on('data:reset', (p) => received.push(p));
            window.resetAllSessionState();
            return received;
        });
        expect(got.length).toBeGreaterThanOrEqual(1);
        expect(got[0].source).toBe('resetAllSessionState');
    });

    test('refreshAllDashboards emittiert data:refresh mit reason', async ({ page }) => {
        await openDashboard(page);
        const captured = await page.evaluate(() => new Promise((resolve) => {
            window.bus.once('data:refresh', (p) => resolve(p));
            window.refreshAllDashboards('test-reason');
        }));
        expect(captured.reason).toBe('test-reason');
        expect(captured.source).toBe('refreshAllDashboards');
    });
});
