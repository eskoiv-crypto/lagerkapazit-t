// @ts-check
import { test, expect } from '@playwright/test';
import { openDashboard } from './helpers.js';

/**
 * 10X-10 Auth-Layer Tests. Echter Azure-AD-Login nicht testbar ohne IT-Setup
 * → Tests covern Config-CRUD, Mode-Switching, Environment-Diagnostik, Logout,
 * Bus-Events und Backward-Compat zur Passwort-Auth.
 */

test.describe('Auth-Config (10X-10)', () => {
    test('Default-Config: mode=password, leere Felder', async ({ page }) => {
        await openDashboard(page);
        const cfg = await page.evaluate(() => {
            localStorage.removeItem('elvinci_auth_config');
            return window.loadAuthConfig();
        });
        expect(cfg.mode).toBe('password');
        expect(cfg.adClientId).toBe('');
        expect(cfg.allowedGroups).toEqual([]);
        expect(cfg.requirePasswordOverride).toBe(false);
    });

    test('saveAuthConfig merged + persistiert + emittiert auth:config-changed', async ({ page }) => {
        await openDashboard(page);
        const out = await page.evaluate(async () => {
            const events = [];
            window.bus.on('auth:config-changed', (p) => events.push(p));
            window.saveAuthConfig({ mode: 'hybrid', adClientId: 'test-client' });
            const reloaded = window.loadAuthConfig();
            return { reloaded, events };
        });
        expect(out.reloaded.mode).toBe('hybrid');
        expect(out.reloaded.adClientId).toBe('test-client');
        expect(out.reloaded.allowedGroups).toEqual([]); // Default beibehalten
        expect(out.events.length).toBeGreaterThanOrEqual(1);
        expect(out.events[0].mode).toBe('hybrid');
    });

    test('authEnvironmentCheck erkennt file:// als nicht AD-tauglich', async ({ page }) => {
        await openDashboard(page);
        const env = await page.evaluate(() => window.authEnvironmentCheck());
        expect(env.protocolOk).toBe(false);
        expect(env.adReady).toBe(false);
    });

    test('authEnvironmentCheck erkennt fehlende AD-Credentials', async ({ page }) => {
        await openDashboard(page);
        const env = await page.evaluate(() => {
            localStorage.removeItem('elvinci_auth_config');
            localStorage.removeItem('elvinci_sharepoint_config');
            return window.authEnvironmentCheck();
        });
        expect(env.hasADCreds).toBe(false);
        expect(env.adReady).toBe(false);
    });

    test('authEnvironmentCheck zieht SharePoint-Credentials als Fallback', async ({ page }) => {
        await openDashboard(page);
        const env = await page.evaluate(() => {
            localStorage.removeItem('elvinci_auth_config');
            // SharePoint-Config liefert Credentials
            window.saveSharepointConfig({ clientId: 'sp-client', tenantId: 'sp-tenant' });
            return window.authEnvironmentCheck();
        });
        expect(env.hasADCreds).toBe(true);
    });
});

test.describe('Auth-Flow (10X-10)', () => {
    test('authLoginAzure scheitert klar auf file://', async ({ page }) => {
        await openDashboard(page);
        const result = await page.evaluate(async () => {
            window.saveAuthConfig({ mode: 'azure-ad', adClientId: 'c', adTenantId: 't' });
            try {
                await window.authLoginAzure();
                return { ok: true };
            } catch (e) {
                return { ok: false, msg: e.message };
            }
        });
        expect(result.ok).toBe(false);
        expect(result.msg).toContain('HTTPS');
    });

    test('authLogout setzt isAuthenticated auf false und emittiert Event', async ({ page }) => {
        await openDashboard(page);
        const out = await page.evaluate(() => {
            const events = [];
            window.bus.on('auth:logged-out', (p) => events.push(p));
            // Fake-Login simulieren
            window.authState.isAuthenticated = true;
            window.authState.user = { displayName: 'Test User', email: 't@e.de' };
            window.authLogout();
            return { isAuth: window.authState.isAuthenticated, events };
        });
        expect(out.isAuth).toBe(false);
        expect(out.events.length).toBeGreaterThanOrEqual(1);
    });

    test('renderUserBadge zeigt Initialen + DisplayName wenn eingeloggt', async ({ page }) => {
        await openDashboard(page);
        const html = await page.evaluate(() => {
            window.authState.isAuthenticated = true;
            window.authState.user = { displayName: 'Dustin Eskofier', email: 'd@e.de' };
            window.renderUserBadge();
            return document.getElementById('user-badge').innerHTML;
        });
        expect(html).toContain('DE');                // Initialen
        expect(html).toContain('Dustin Eskofier');
    });

    test('renderUserBadge zeigt "Gast" wenn nicht eingeloggt', async ({ page }) => {
        await openDashboard(page);
        const html = await page.evaluate(() => {
            window.authLogout();
            window.renderUserBadge();
            return document.getElementById('user-badge').innerHTML;
        });
        expect(html).toContain('Gast');
    });
});

test.describe('Auth-Backward-Compat (10X-10)', () => {
    test('checkPassword (legacy) emittiert auth:logged-in mit mode=password', async ({ page }) => {
        await openDashboard(page);
        const out = await page.evaluate(() => new Promise((resolve) => {
            // Vorbedingungen: Mode darf nicht azure-ad-only sein
            window.saveAuthConfig({ mode: 'password' });
            window.bus.once('auth:logged-in', resolve);
            // ADMIN_PASSWORD ist der harte Wert ('elvinci2026' im Code)
            const input = document.getElementById('admin-password');
            input.value = 'elvinci2026';
            window.checkPassword();
        }));
        expect(out.mode).toBe('password');
        expect(out.user.displayName).toContain('Passwort');
    });

    test('checkPassword wird in azure-ad-only blockiert (ohne Override)', async ({ page }) => {
        await openDashboard(page);
        const out = await page.evaluate(() => {
            window.saveAuthConfig({ mode: 'azure-ad', requirePasswordOverride: false });
            window.authState.isAuthenticated = false;
            const input = document.getElementById('admin-password');
            input.value = 'elvinci2026';
            window.checkPassword();
            return window.authState.isAuthenticated;
        });
        expect(out).toBe(false);
    });

    test('Override-Flag erlaubt Passwort-Login auch in azure-ad-Mode', async ({ page }) => {
        await openDashboard(page);
        const out = await page.evaluate(() => {
            window.saveAuthConfig({ mode: 'azure-ad', requirePasswordOverride: true });
            const input = document.getElementById('admin-password');
            input.value = 'elvinci2026';
            window.checkPassword();
            return window.authState.isAuthenticated;
        });
        expect(out).toBe(true);
    });
});
