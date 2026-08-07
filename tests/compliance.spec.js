// @ts-check
import { test, expect } from '@playwright/test';
import { openDashboard } from './helpers.js';

/**
 * 10X-6 Compliance-Layer Tests.
 * Decken Klassifizierung, PII-Maskierung, Audit-Logger und Bus-Verdrahtung ab.
 */

test.describe('Daten-Klassifizierung (10X-6)', () => {
    test('FILE_CLASSIFICATIONS deckt alle Upload-Typen ab', async ({ page }) => {
        await openDashboard(page);
        const result = await page.evaluate(() => {
            const types = ['bestand', 'we-ist', 'wa-ist', 'we-pipe', 'wa-pipe',
                'auftrag-status', 'planner', 'jtl-sales', 'all-sold', 'stock-analysis', 'angebot'];
            return types.map(t => ({ t, cls: window.getDataClassification(t) }));
        });
        for (const { t, cls } of result) {
            expect(['green', 'yellow', 'red'], `${t} muss klassifiziert sein`).toContain(cls.tier);
        }
    });

    test('Sensible Typen sind als rot eingestuft', async ({ page }) => {
        await openDashboard(page);
        const tiers = await page.evaluate(() => ({
            allSold: window.getDataClassification('all-sold').tier,
            stock: window.getDataClassification('stock-analysis').tier,
            jtl: window.getDataClassification('jtl-sales').tier,
            bestand: window.getDataClassification('bestand').tier
        }));
        expect(tiers.allSold).toBe('red');
        expect(tiers.stock).toBe('red');
        expect(tiers.jtl).toBe('red');
        expect(tiers.bestand).toBe('green');
    });

    test('Unbekannter Typ → tier=unknown', async ({ page }) => {
        await openDashboard(page);
        const cls = await page.evaluate(() => window.getDataClassification('xyz-unknown'));
        expect(cls.tier).toBe('unknown');
    });
});

test.describe('PII-Maskierung (10X-6)', () => {
    test('maskPII Heuristiken: Name, Email, Phone, Lager', async ({ page }) => {
        await openDashboard(page);
        const masked = await page.evaluate(() => ({
            name: window.maskPII('Müller GmbH', 'name'),
            email: window.maskPII('max@firma.de', 'email'),
            phone: window.maskPII('+49 911 12345', 'phone'),
            lager: window.maskPII('9001234567', 'lager'),
            empty: window.maskPII('', 'name'),
            nullV: window.maskPII(null),
        }));
        expect(masked.name.startsWith('Kunde_M')).toBe(true);
        expect(masked.email).toContain('@');
        expect(masked.email.length).toBeLessThan('max@firma.de'.length + 5);
        expect(masked.phone).toContain('+');
        expect(masked.lager.startsWith('9')).toBe(true);
        expect(masked.lager.endsWith('67')).toBe(true);
        expect(masked.empty).toBe('');
        expect(masked.nullV).toBe('');
    });

    test('Auto-Detection: erkennt Email/Lager/Phone', async ({ page }) => {
        await openDashboard(page);
        const masked = await page.evaluate(() => ({
            email: window.maskPII('foo@bar.com'),
            lager: window.maskPII('9001234567'),
            phone: window.maskPII('+49 911 5544'),
            name: window.maskPII('Schmidt AG'),
        }));
        expect(masked.email).toContain('@');
        expect(masked.lager.endsWith('67')).toBe(true);
        expect(masked.phone).toContain('+');
        expect(masked.name.startsWith('Kunde_')).toBe(true);
    });

    test('PII-Toggle: maskedH respektiert Config', async ({ page }) => {
        await openDashboard(page);
        const out = await page.evaluate(() => {
            window.setPIIMaskingEnabled(false);
            const off = window.maskedH('Müller GmbH', 'name');
            window.setPIIMaskingEnabled(true);
            const on = window.maskedH('Müller GmbH', 'name');
            window.setPIIMaskingEnabled(false);
            return { off, on };
        });
        expect(out.off).toBe('Müller GmbH');
        expect(out.on.startsWith('Kunde_M')).toBe(true);
    });
});

test.describe('Audit-Logger (10X-6)', () => {
    test('auditLog persistiert Eintrag in IDB', async ({ page }) => {
        await openDashboard(page);
        const result = await page.evaluate(async () => {
            // Audit-Store leeren für deterministischen Test
            await window.idbStores.auditLog().clear();
            await window.auditLog('test.action', { foo: 'bar', n: 42 });
            const events = await window.getAuditLog();
            return events;
        });
        expect(result.length).toBe(1);
        expect(result[0].action).toBe('test.action');
        expect(result[0].payload.foo).toBe('bar');
        expect(result[0].payload.n).toBe(42);
        expect(result[0]).toHaveProperty('timestamp');
        expect(result[0]).toHaveProperty('actor');
    });

    test('Bus-Event auth:logged-in löst Audit-Eintrag aus', async ({ page }) => {
        await openDashboard(page);
        const result = await page.evaluate(async () => {
            await window.idbStores.auditLog().clear();
            window.bus.emit('auth:logged-in', { mode: 'password', user: { displayName: 'Tester' } });
            // Wait for async _auditQueue to flush
            await new Promise(r => setTimeout(r, 200));
            return await window.getAuditLog();
        });
        const loginEvent = result.find(e => e.action === 'auth.login');
        expect(loginEvent).toBeTruthy();
        expect(loginEvent.payload.mode).toBe('password');
    });

    test('Bus-Event data:bestand-loaded → audit mit tier=green', async ({ page }) => {
        await openDashboard(page);
        const result = await page.evaluate(async () => {
            await window.idbStores.auditLog().clear();
            window.bus.emit('data:bestand-loaded', { stueck: 500, auftraege: 40 });
            await new Promise(r => setTimeout(r, 200));
            return await window.getAuditLog();
        });
        const evt = result.find(e => e.action === 'data.upload');
        expect(evt).toBeTruthy();
        expect(evt.payload.tier).toBe('green');
        expect(evt.payload.type).toBe('bestand');
        expect(evt.payload.stueck).toBe(500);
    });

    test('Audit aus wenn auditLogEnabled=false', async ({ page }) => {
        await openDashboard(page);
        const result = await page.evaluate(async () => {
            await window.idbStores.auditLog().clear();
            window.saveComplianceConfig({ auditLogEnabled: false });
            await window.auditLog('test.skipped', {});
            const events = await window.getAuditLog();
            window.saveComplianceConfig({ auditLogEnabled: true });
            return events;
        });
        expect(result.length).toBe(0);
    });

    test('Actor-Info aus authState wird mitgeloggt', async ({ page }) => {
        await openDashboard(page);
        const result = await page.evaluate(async () => {
            await window.idbStores.auditLog().clear();
            window.authState.user = { displayName: 'Dustin', email: 'd@e.de', id: 'u1' };
            window.authState.mode = 'azure-ad';
            await window.auditLog('test.actor', {});
            const evts = await window.getAuditLog();
            return evts[0].actor;
        });
        expect(result.displayName).toBe('Dustin');
        expect(result.email).toBe('d@e.de');
        expect(result.mode).toBe('azure-ad');
    });
});

test.describe('Compliance-Config (10X-6)', () => {
    test('Default: pii=off, audit=on, retention=365', async ({ page }) => {
        await openDashboard(page);
        const cfg = await page.evaluate(() => {
            localStorage.removeItem('elvinci_compliance_config');
            return window.loadComplianceConfig();
        });
        expect(cfg.piiMaskingEnabled).toBe(false);
        expect(cfg.auditLogEnabled).toBe(true);
        expect(cfg.auditRetentionDays).toBe(365);
    });

    test('saveComplianceConfig emittiert compliance:config-changed', async ({ page }) => {
        await openDashboard(page);
        const captured = await page.evaluate(() => new Promise((resolve) => {
            window.bus.once('compliance:config-changed', resolve);
            window.saveComplianceConfig({ piiMaskingEnabled: true });
        }));
        expect(captured.piiMaskingEnabled).toBe(true);
    });
});
