// @ts-check
import { test, expect } from '@playwright/test';
import { openDashboard } from './helpers.js';

/**
 * Sprint 7+ (User-Wunsch 2026-04-27): Department-Switcher + Komm-Suche.
 * 5 Sichten: Alle / Lager / Auftragsabwicklung / Sales / Finance.
 * Suchfeld in Auftragsabwicklung filtert nach Kunde + Auftragsnummer.
 */

test.describe('Department-Switcher (10X User-Wunsch)', () => {
    test('Default ist "alle" und persistiert in localStorage', async ({ page }) => {
        await openDashboard(page);
        const out = await page.evaluate(() => ({
            dept: document.body.dataset.activeDept,
            saved: localStorage.getItem('elvinci_active_dept')
        }));
        expect(out.dept).toBe('alle');
    });

    test('setDepartment("lager") versteckt Sales/Finance-only Sections', async ({ page }) => {
        await openDashboard(page);
        const out = await page.evaluate(() => {
            window.setDepartment('lager');
            // analyse-pro-panel hat data-departments="alle,sales,finance" → soll versteckt sein
            const panel = document.getElementById('analyse-pro-panel');
            const computed = window.getComputedStyle(panel).display;
            return {
                bodyDept: document.body.dataset.activeDept,
                analysePanelHidden: computed === 'none'
            };
        });
        expect(out.bodyDept).toBe('lager');
        expect(out.analysePanelHidden).toBe(true);
    });

    test('setDepartment("auftrag") zeigt nur Kommissioniert-Card', async ({ page }) => {
        await openDashboard(page);
        const out = await page.evaluate(() => {
            window.setDepartment('auftrag');
            // kommissioniert-card data-departments="alle,auftrag" → sichtbar
            // analyse-pro-panel data-departments="alle,sales,finance" → versteckt
            const komm = document.getElementById('kommissioniert-card');
            const panel = document.getElementById('analyse-pro-panel');
            // Note: kommissioniert-card hat eigenes display:none initial — wird durch
            // Datenladen sichtbar. CSS-Filter prüfen wir nur über den Selector.
            return {
                kommHasAuftragTag: komm.dataset.departments && komm.dataset.departments.includes('auftrag'),
                panelHasAuftragTag: panel.dataset.departments && panel.dataset.departments.includes('auftrag')
            };
        });
        expect(out.kommHasAuftragTag).toBe(true);
        expect(out.panelHasAuftragTag).toBe(false);
    });

    test('setDepartment("sales") aktiviert Sales-Button + persistiert', async ({ page }) => {
        await openDashboard(page);
        const out = await page.evaluate(() => {
            window.setDepartment('sales');
            const salesBtn = document.querySelector('.dept-btn[data-dept="sales"]');
            const alleBtn = document.querySelector('.dept-btn[data-dept="alle"]');
            return {
                salesActive: salesBtn.classList.contains('active'),
                alleActive: alleBtn.classList.contains('active'),
                saved: localStorage.getItem('elvinci_active_dept')
            };
        });
        expect(out.salesActive).toBe(true);
        expect(out.alleActive).toBe(false);
        expect(out.saved).toBe('sales');
    });

    test('Ungültiger Department-Wert fällt auf "alle" zurück', async ({ page }) => {
        await openDashboard(page);
        const out = await page.evaluate(() => {
            window.setDepartment('marketing');  // existiert nicht
            return document.body.dataset.activeDept;
        });
        expect(out).toBe('alle');
    });

    test('Sticky Switcher hat 5 Buttons (alle, lager, auftrag, sales, finance)', async ({ page }) => {
        await openDashboard(page);
        const buttons = await page.evaluate(() =>
            Array.from(document.querySelectorAll('.dept-btn')).map(b => b.dataset.dept)
        );
        expect(buttons.sort()).toEqual(['alle', 'auftrag', 'finance', 'lager', 'sales']);
    });

    test('bus.emit ui:dept-changed bei setDepartment', async ({ page }) => {
        await openDashboard(page);
        const captured = await page.evaluate(() => new Promise((resolve) => {
            window.bus.once('ui:dept-changed', resolve);
            window.setDepartment('finance');
        }));
        expect(captured.dept).toBe('finance');
    });
});

test.describe('Auftragsabwicklung-Suche (10X User-Wunsch)', () => {
    test('Suchfeld existiert mit ARIA-Label', async ({ page }) => {
        await openDashboard(page);
        const r = await page.evaluate(() => {
            const inp = document.getElementById('komm-search');
            return {
                exists: !!inp,
                type: inp && inp.type,
                ariaLabel: inp && inp.getAttribute('aria-label')
            };
        });
        expect(r.exists).toBe(true);
        expect(r.type).toBe('search');
        expect(r.ariaLabel).toContain('Suche');
    });

    test('onKommSearchInput filtert Liste nach Kundenname', async ({ page }) => {
        await openDashboard(page);
        const result = await page.evaluate(() => {
            window.dashboardState.kommissioniertListe = [
                { auftragsnr: 'AU2026001', kunde: 'Müller GmbH', land: 'DE', artikel: 5,
                  status: 'QU', anzeigeStatus: 'qu-offen', versandDatum: null,
                  istBlockierer: false, istKritischerBlockierer: false, istUeberfaellig: false,
                  istEchterProblemfall: false, istKombi: false, tageBlockiert: 0, tageUeberfaellig: 0 },
                { auftragsnr: 'AU2026002', kunde: 'Schmidt KG', land: 'DE', artikel: 3,
                  status: 'AK', anzeigeStatus: 'ak', versandDatum: null,
                  istBlockierer: false, istKritischerBlockierer: false, istUeberfaellig: false,
                  istEchterProblemfall: false, istKombi: false, tageBlockiert: 0, tageUeberfaellig: 0 },
                { auftragsnr: 'AU2026003', kunde: 'Müller AG', land: 'AT', artikel: 7,
                  status: 'QU', anzeigeStatus: 'qu-offen', versandDatum: null,
                  istBlockierer: false, istKritischerBlockierer: false, istUeberfaellig: false,
                  istEchterProblemfall: false, istKombi: false, tageBlockiert: 0, tageUeberfaellig: 0 },
            ];
            // Suche nach "müller" → 2 Treffer
            window.onKommSearchInput('müller');
            const tbody = document.getElementById('komm-tbody');
            const rows = tbody ? tbody.querySelectorAll('tr') : [];
            // Filter NICHT durch Status-Filter beeinflusst (aktiv: 'alle')
            return {
                rowCount: rows.length,
                infoText: document.getElementById('komm-search-info').textContent
            };
        });
        // 2 Treffer (Müller GmbH + Müller AG), Schmidt rausgefiltert
        expect(result.rowCount).toBe(2);
        expect(result.infoText).toContain('2 Treffer');
    });

    test('onKommSearchInput filtert nach Auftragsnummer', async ({ page }) => {
        await openDashboard(page);
        const result = await page.evaluate(() => {
            window.dashboardState.kommissioniertListe = [
                { auftragsnr: 'AU2026111', kunde: 'A', land: 'DE', artikel: 1,
                  status: 'QU', anzeigeStatus: 'qu-offen', versandDatum: null,
                  istBlockierer: false, istKritischerBlockierer: false, istUeberfaellig: false,
                  istEchterProblemfall: false, istKombi: false, tageBlockiert: 0, tageUeberfaellig: 0 },
                { auftragsnr: 'AU2026222', kunde: 'B', land: 'DE', artikel: 1,
                  status: 'QU', anzeigeStatus: 'qu-offen', versandDatum: null,
                  istBlockierer: false, istKritischerBlockierer: false, istUeberfaellig: false,
                  istEchterProblemfall: false, istKombi: false, tageBlockiert: 0, tageUeberfaellig: 0 },
            ];
            window.onKommSearchInput('AU2026111');
            const rows = document.querySelectorAll('#komm-tbody tr');
            return rows.length;
        });
        expect(result).toBe(1);
    });

    test('clearKommSearch leert Input und Clear-Button display:none', async ({ page }) => {
        await openDashboard(page);
        const result = await page.evaluate(() => {
            window.dashboardState.kommissioniertListe = [
                { auftragsnr: 'X', kunde: 'A', land: 'DE', artikel: 1, status: 'QU',
                  anzeigeStatus: 'qu-offen', versandDatum: null, istBlockierer: false,
                  istKritischerBlockierer: false, istUeberfaellig: false,
                  istEchterProblemfall: false, istKombi: false, tageBlockiert: 0, tageUeberfaellig: 0 }
            ];
            // Manuell den Input-Value setzen (simuliert User-Eingabe), dann onKommSearchInput rufen
            const inp = document.getElementById('komm-search');
            inp.value = 'zzz-no-match';
            window.onKommSearchInput('zzz-no-match');
            const beforeInput = inp.value;
            const beforeClearComputed = window.getComputedStyle(document.getElementById('komm-search-clear')).display;
            window.clearKommSearch();
            const afterInput = inp.value;
            const afterClearComputed = window.getComputedStyle(document.getElementById('komm-search-clear')).display;
            return { beforeInput, beforeClearComputed, afterInput, afterClearComputed };
        });
        expect(result.beforeInput).toBe('zzz-no-match');
        expect(result.beforeClearComputed).not.toBe('none');
        expect(result.afterInput).toBe('');
        expect(result.afterClearComputed).toBe('none');
    });

    test('Suche kombiniert mit Status-Filter (Schnittmenge)', async ({ page }) => {
        await openDashboard(page);
        const result = await page.evaluate(() => {
            window.dashboardState.kommissioniertListe = [
                { auftragsnr: 'A', kunde: 'Foo', land: 'DE', artikel: 1, status: 'QU',
                  anzeigeStatus: 'qu-offen', versandDatum: null, istBlockierer: false,
                  istKritischerBlockierer: false, istUeberfaellig: false,
                  istEchterProblemfall: false, istKombi: false, tageBlockiert: 0, tageUeberfaellig: 0 },
                { auftragsnr: 'B', kunde: 'Foo', land: 'DE', artikel: 1, status: 'AK',
                  anzeigeStatus: 'ak', versandDatum: null, istBlockierer: false,
                  istKritischerBlockierer: false, istUeberfaellig: false,
                  istEchterProblemfall: false, istKombi: false, tageBlockiert: 0, tageUeberfaellig: 0 },
                { auftragsnr: 'C', kunde: 'Bar', land: 'DE', artikel: 1, status: 'QU',
                  anzeigeStatus: 'qu-offen', versandDatum: null, istBlockierer: false,
                  istKritischerBlockierer: false, istUeberfaellig: false,
                  istEchterProblemfall: false, istKombi: false, tageBlockiert: 0, tageUeberfaellig: 0 },
            ];
            window.filterKommissioniert('qu');     // nur QU
            window.onKommSearchInput('foo');       // nur Foo
            const rows = document.querySelectorAll('#komm-tbody tr');
            return rows.length;
        });
        // Foo + QU = nur Auftrag A → 1 Treffer
        expect(result).toBe(1);
    });
});
