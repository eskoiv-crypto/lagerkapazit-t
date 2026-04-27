// @ts-check
import { test, expect } from '@playwright/test';
import { openDashboard } from './helpers.js';

test.describe('Smoke', () => {
    test('Dashboard lädt ohne JS-Fehler', async ({ page }) => {
        const { consoleErrors } = await openDashboard(page);
        // Ignoriere CDN-Loadfehler (offline ok), aber keine Dashboard-internen Errors
        const realErrors = consoleErrors.filter(e =>
            !e.includes('cdn.') && !e.includes('cdnjs') && !e.includes('Failed to load resource')
        );
        expect(realErrors, 'Keine JS-Runtime-Errors erwartet').toEqual([]);
    });

    test('Alle Core-Helper sind global verfügbar (Sprint 1-5 Oberflächenvertrag)', async ({ page }) => {
        await openDashboard(page);
        const present = await page.evaluate(() => ({
            escapeHtml: typeof window.escapeHtml === 'function',
            calculateMargin: typeof window.calculateMargin === 'function',
            calculateMarginFromEkVk: typeof window.calculateMarginFromEkVk === 'function',
            refreshAllDashboards: typeof window.refreshAllDashboards === 'function',
            enqueueUpload: typeof window.enqueueUpload === 'function',
            resetAllSessionState: typeof window.resetAllSessionState === 'function',
            parseAMMDataRows: typeof window.parseAMMDataRows === 'function',
            renderEmptyState: typeof window.renderEmptyState === 'function',
            initA11y: typeof window.initA11y === 'function',
            detectAnomalies: typeof window.detectAnomalies === 'function',
            renderAnomaliesPanel: typeof window.renderAnomaliesPanel === 'function',
            bus: typeof window.bus === 'object' && typeof window.bus.emit === 'function',
            createEventBus: typeof window.createEventBus === 'function',
            state: typeof window.state === 'object' && typeof window.state.inventory === 'object',
            createDomainView: typeof window.createDomainView === 'function',
            createIDBStore: typeof window.createIDBStore === 'function',
            idbStores: typeof window.idbStores === 'object',
            detectCDNAvailability: typeof window.detectCDNAvailability === 'function',
            persistSnapshotToIDB: typeof window.persistSnapshotToIDB === 'function',
            loadSharepointConfig: typeof window.loadSharepointConfig === 'function',
            saveSharepointConfig: typeof window.saveSharepointConfig === 'function',
            sharepointPull: typeof window.sharepointPull === 'function',
            sharepointPush: typeof window.sharepointPush === 'function',
            startAutoPull: typeof window.startAutoPull === 'function',
            loadAuthConfig: typeof window.loadAuthConfig === 'function',
            authLoginAzure: typeof window.authLoginAzure === 'function',
            authLogout: typeof window.authLogout === 'function',
            renderUserBadge: typeof window.renderUserBadge === 'function',
            authState: typeof window.authState === 'object',
            getDataClassification: typeof window.getDataClassification === 'function',
            maskPII: typeof window.maskPII === 'function',
            maskedH: typeof window.maskedH === 'function',
            auditLog: typeof window.auditLog === 'function',
            getAuditLog: typeof window.getAuditLog === 'function',
            FILE_CLASSIFICATIONS: typeof window.FILE_CLASSIFICATIONS === 'object',
        }));
        for (const [name, ok] of Object.entries(present)) {
            expect(ok, `${name} muss als global function existieren`).toBe(true);
        }
    });
});
