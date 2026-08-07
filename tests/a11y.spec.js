// @ts-check
import { test, expect } from '@playwright/test';
import { openDashboard } from './helpers.js';

test.describe('Accessibility (Sprint 5)', () => {
    test('P2-13: Alle <button> haben type-Attribut nach initA11y', async ({ page }) => {
        await openDashboard(page);
        const untypedCount = await page.evaluate(() =>
            document.querySelectorAll('button:not([type])').length
        );
        expect(untypedCount, 'Kein <button> ohne type-Attribut').toBe(0);
    });

    test('P2-12: .import-box hat role=button + tabindex=0', async ({ page }) => {
        await openDashboard(page);
        const boxes = await page.evaluate(() => {
            return Array.from(document.querySelectorAll('.import-box')).map(b => ({
                role: b.getAttribute('role'),
                tabindex: b.getAttribute('tabindex'),
                ariaLabel: b.getAttribute('aria-label'),
            }));
        });
        expect(boxes.length).toBeGreaterThan(0);
        for (const b of boxes) {
            expect(b.role, 'role').toBe('button');
            expect(b.tabindex, 'tabindex').toBe('0');
            expect(b.ariaLabel, 'aria-label').toBeTruthy();
        }
    });

    test('P2-16: .filter-btn mit .active bekommt aria-pressed=true', async ({ page }) => {
        await openDashboard(page);
        const filterBtns = await page.evaluate(() => {
            return Array.from(document.querySelectorAll('.filter-btn')).map(b => ({
                active: b.classList.contains('active'),
                pressed: b.getAttribute('aria-pressed'),
            }));
        });
        if (filterBtns.length === 0) test.skip(true, 'Keine filter-btn gefunden');
        for (const b of filterBtns) {
            expect(b.pressed, 'aria-pressed muss gesetzt sein').not.toBeNull();
            if (b.active) expect(b.pressed).toBe('true');
            else expect(b.pressed).toBe('false');
        }
    });

    test('P2-14: <select>-Elemente haben aria-label', async ({ page }) => {
        await openDashboard(page);
        const selects = await page.evaluate(() =>
            Array.from(document.querySelectorAll('select')).map(s => ({
                id: s.id,
                ariaLabel: s.getAttribute('aria-label'),
                hasLabelFor: s.id ? !!document.querySelector(`label[for="${s.id}"]`) : false,
            }))
        );
        for (const s of selects) {
            const labelled = !!s.ariaLabel || s.hasLabelFor;
            expect(labelled, `select#${s.id} braucht aria-label oder <label for>`).toBe(true);
        }
    });

    test('P2-15: Settings-Modal öffnet und ESC schließt via Focus-Trap', async ({ page }) => {
        await openDashboard(page);
        await page.evaluate(() => window.openSettingsPanel());
        let display = await page.$eval('#settings-modal', el => el.style.display);
        expect(display).toBe('flex');
        await page.keyboard.press('Escape');
        display = await page.$eval('#settings-modal', el => el.style.display);
        expect(display).toBe('none');
    });
});
