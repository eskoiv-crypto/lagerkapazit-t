// @ts-check
import { test, expect } from '@playwright/test';
import { openDashboard } from './helpers.js';

/**
 * 10X-5 Tests. Echter Graph-Call kann ohne IT-Setup nicht getestet werden —
 * stattdessen: Config-CRUD, Environment-Check, Scheduler-Start/Stop, Bus-Events.
 */

test.describe('SharePoint-Config (10X-5)', () => {
    test('Default-Config ist deaktiviert und leer', async ({ page }) => {
        await openDashboard(page);
        const cfg = await page.evaluate(() => {
            localStorage.removeItem('elvinci_sharepoint_config');
            return window.loadSharepointConfig();
        });
        expect(cfg.enabled).toBe(false);
        expect(cfg.clientId).toBe('');
        expect(cfg.autoPullMinutes).toBe(0);
    });

    test('saveSharepointConfig schreibt in localStorage und merged mit Default', async ({ page }) => {
        await openDashboard(page);
        const cfg = await page.evaluate(() => {
            localStorage.removeItem('elvinci_sharepoint_config');
            window.saveSharepointConfig({ clientId: 'abc-123', autoPullMinutes: 15 });
            return window.loadSharepointConfig();
        });
        expect(cfg.clientId).toBe('abc-123');
        expect(cfg.autoPullMinutes).toBe(15);
        expect(cfg.enabled).toBe(false);      // nicht gesetzt → Default
        expect(cfg.tenantId).toBe('');
    });

    test('sharepointEnvironmentCheck erkennt file:// als nicht geeignet', async ({ page }) => {
        await openDashboard(page);
        const env = await page.evaluate(() => window.sharepointEnvironmentCheck());
        // Dashboard wird als file:// geladen → protocolOk = false
        expect(env.protocolOk).toBe(false);
        expect(env.protocol).toBe('file:');
    });

    test('sharepointEnvironmentCheck erkennt vollständige Config', async ({ page }) => {
        await openDashboard(page);
        const env = await page.evaluate(() => {
            window.saveSharepointConfig({
                clientId: 'c',
                tenantId: 't',
                siteId: 's',
                bestandFilePath: '/x.csv'
            });
            return window.sharepointEnvironmentCheck();
        });
        expect(env.configComplete).toBe(true);
        expect(env.hasClientId).toBe(true);
    });

    test('saveSharepointConfig emittiert sync:config-changed', async ({ page }) => {
        await openDashboard(page);
        const captured = await page.evaluate(() => new Promise((resolve) => {
            window.bus.once('sync:config-changed', resolve);
            window.saveSharepointConfig({ enabled: true });
        }));
        expect(captured).toHaveProperty('enabled');
    });
});

test.describe('SharePoint-Scheduler (10X-5)', () => {
    test('startAutoPull ist No-Op bei leerer Config', async ({ page }) => {
        await openDashboard(page);
        const out = await page.evaluate(() => {
            localStorage.removeItem('elvinci_sharepoint_config');
            window.stopAutoPull();
            window.startAutoPull();
            // Kein Fehler, kein Timer läuft — einfach fertig
            return true;
        });
        expect(out).toBe(true);
    });

    test('stopAutoPull ist idempotent', async ({ page }) => {
        await openDashboard(page);
        const out = await page.evaluate(() => {
            window.stopAutoPull();
            window.stopAutoPull();
            window.stopAutoPull();
            return true;
        });
        expect(out).toBe(true);
    });
});

test.describe('SharePoint-Errors (10X-5)', () => {
    test('sharepointPull scheitert klar auf file:// und emittiert sync:failed', async ({ page }) => {
        await openDashboard(page);
        const result = await page.evaluate(async () => {
            window.saveSharepointConfig({
                enabled: true, clientId: 'c', tenantId: 't', siteId: 's', bestandFilePath: '/x.csv'
            });
            const events = [];
            window.bus.on('sync:failed', (p) => events.push(p));
            const r = await window.sharepointPull();
            return { r, events };
        });
        expect(result.r.ok).toBe(false);
        expect(result.r.error).toContain('HTTPS');
        expect(result.events.length).toBeGreaterThanOrEqual(1);
        expect(result.events[0].op).toBe('pull');
    });
});
