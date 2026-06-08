// @ts-check
import { test, expect } from '@playwright/test';
import { openDashboard } from './helpers.js';

/**
 * Sprint 7+ Tests (User-Report 2026-04-27): robust parseFulfillmentDate +
 * Lifecycle-Anomalien aus erweitertem wa-pipe-Parser.
 *
 * AMM trägt Versandtermine in mindestens 5 Formaten ein. Vorheriger Parser
 * konnte nur DD.MM.YYYY und ISO. Resultat: "Geplant"-Filter zeigte 0
 * obwohl Aufträge mit Termin existierten.
 *
 * NOTE: Tests verwenden lokale Datums-Komponenten statt toISOString,
 * weil Parser lokale Date-Objekte erzeugt — toISOString shifted auf UTC
 * und liefert falsches Datum bei Berlin-Zeit.
 */

// Helper für die Tests (wird per Hand in jede page.evaluate-Closure injiziert)
const LOCAL_HELPER = `
    function _localISO(d) {
        if (!d) return null;
        return d.getFullYear() + '-' +
            String(d.getMonth()+1).padStart(2,'0') + '-' +
            String(d.getDate()).padStart(2,'0');
    }
`;

test.describe('parseFulfillmentDate (Sprint 7+ User-Report)', () => {
    test('Volle DD.MM.YYYY', async ({ page }) => {
        await openDashboard(page);
        const r = await page.evaluate(() => {
            function _localISO(d) { return d.getFullYear() + '-' + String(d.getMonth()+1).padStart(2,'0') + '-' + String(d.getDate()).padStart(2,'0'); }
            const p = window.parseFulfillmentDate('23.04.2026');
            return { iso: _localISO(p.start), isRange: p.isRange };
        });
        expect(r.iso).toBe('2026-04-23');
        expect(r.isRange).toBe(false);
    });

    test('ISO YYYY-MM-DD', async ({ page }) => {
        await openDashboard(page);
        const r = await page.evaluate(() => {
            function _localISO(d) { return d.getFullYear() + '-' + String(d.getMonth()+1).padStart(2,'0') + '-' + String(d.getDate()).padStart(2,'0'); }
            const p = window.parseFulfillmentDate('2026-04-23');
            return _localISO(p.start);
        });
        expect(r).toBe('2026-04-23');
    });

    test('Abgekürzt deutsch "28. Apr" (Jahr aus Heuristik)', async ({ page }) => {
        await openDashboard(page);
        const r = await page.evaluate(() => {
            const p = window.parseFulfillmentDate('28. Apr');
            return { day: p.start.getDate(), month: p.start.getMonth() };
        });
        expect(r.month).toBe(3);   // April = 3 (0-indexed)
        expect(r.day).toBe(28);
    });

    test('Abgekürzt mit explizitem Jahr "15. Apr 2026"', async ({ page }) => {
        await openDashboard(page);
        const r = await page.evaluate(() => {
            function _localISO(d) { return d.getFullYear() + '-' + String(d.getMonth()+1).padStart(2,'0') + '-' + String(d.getDate()).padStart(2,'0'); }
            const p = window.parseFulfillmentDate('15. Apr 2026');
            return _localISO(p.start);
        });
        expect(r).toBe('2026-04-15');
    });

    test('DD.MM ohne Jahr "23.04"', async ({ page }) => {
        await openDashboard(page);
        const r = await page.evaluate(() => {
            const p = window.parseFulfillmentDate('23.04');
            return { day: p.start.getDate(), month: p.start.getMonth(), isRange: p.isRange };
        });
        expect(r.day).toBe(23);
        expect(r.month).toBe(3);
        expect(r.isRange).toBe(false);
    });

    test('Range "28.04 - 30.04"', async ({ page }) => {
        await openDashboard(page);
        const r = await page.evaluate(() => {
            const p = window.parseFulfillmentDate('28.04 - 30.04');
            return {
                startDay: p.start.getDate(), startMonth: p.start.getMonth(),
                endDay:   p.end.getDate(),   endMonth: p.end.getMonth(),
                isRange: p.isRange
            };
        });
        expect(r.startDay).toBe(28);
        expect(r.endDay).toBe(30);
        expect(r.startMonth).toBe(3);
        expect(r.isRange).toBe(true);
    });

    test('Range mit Voll-Datum "28.04.2026 - 30.04.2026"', async ({ page }) => {
        await openDashboard(page);
        const r = await page.evaluate(() => {
            function _localISO(d) { return d.getFullYear() + '-' + String(d.getMonth()+1).padStart(2,'0') + '-' + String(d.getDate()).padStart(2,'0'); }
            const p = window.parseFulfillmentDate('28.04.2026 - 30.04.2026');
            return { start: _localISO(p.start), end: _localISO(p.end), isRange: p.isRange };
        });
        expect(r.start).toBe('2026-04-28');
        expect(r.end).toBe('2026-04-30');
        expect(r.isRange).toBe(true);
    });

    test('Excel-Serial-Number', async ({ page }) => {
        await openDashboard(page);
        const r = await page.evaluate(() => {
            // 46145 = Mai 2026 (Excel-Serial, getestet: month=4 day=3)
            const p = window.parseFulfillmentDate(46145);
            return { year: p.start.getFullYear(), month: p.start.getMonth(), day: p.start.getDate() };
        });
        expect(r.year).toBe(2026);
        expect(r.month).toBe(4);   // Mai (0-indexed)
        expect([2, 3, 4]).toContain(r.day);  // ±1 Tag-Toleranz wegen UTC-Drift
    });

    test('Date-Objekt direkt', async ({ page }) => {
        await openDashboard(page);
        const r = await page.evaluate(() => {
            function _localISO(d) { return d.getFullYear() + '-' + String(d.getMonth()+1).padStart(2,'0') + '-' + String(d.getDate()).padStart(2,'0'); }
            const d = new Date(2026, 3, 23);
            const p = window.parseFulfillmentDate(d);
            return _localISO(p.start);
        });
        expect(r).toBe('2026-04-23');
    });

    test('Text-Wert "Warte auf Rückmeldung" → null', async ({ page }) => {
        await openDashboard(page);
        const r = await page.evaluate(() => window.parseFulfillmentDate('Warte auf Rückmeldung'));
        expect(r).toBeNull();
    });

    test('Leere/null-Werte → null', async ({ page }) => {
        await openDashboard(page);
        const r = await page.evaluate(() => ({
            empty: window.parseFulfillmentDate(''),
            nullV: window.parseFulfillmentDate(null),
            undef: window.parseFulfillmentDate(undefined),
            blanks: window.parseFulfillmentDate('   ')
        }));
        expect(r.empty).toBeNull();
        expect(r.nullV).toBeNull();
        expect(r.undef).toBeNull();
        expect(r.blanks).toBeNull();
    });

    test('parseExcelDate ist Backward-Compat-Wrapper über parseFulfillmentDate', async ({ page }) => {
        await openDashboard(page);
        const r = await page.evaluate(() => {
            const d = window.parseExcelDate('23.04.2026');
            if (!(d instanceof Date)) return null;
            return d.getFullYear() + '-' + String(d.getMonth()+1).padStart(2,'0') + '-' + String(d.getDate()).padStart(2,'0');
        });
        expect(r).toBe('2026-04-23');
    });
});

test.describe('Lifecycle-Anomalien (Sprint 7+ User-Report)', () => {
    test('Auftrag älter als 14 Tage ohne Termin → warnung', async ({ page }) => {
        await openDashboard(page);
        const result = await page.evaluate(() => {
            window.resetAllSessionState();
            const altDate = new Date(); altDate.setDate(altDate.getDate() - 20); altDate.setHours(0,0,0,0);
            window.state.pipeline.fulfillmentDataMap = {
                'AU_OLD': {
                    auftragAlterTage: 20,
                    versandDatum: null,
                    versandStr: '',
                    istWarteText: false,
                    versandAngemeldet: false,
                    versandAnmeldungStr: '',
                    leadTimeTage: null,
                    anmeldeDatum: altDate
                }
            };
            return window.runUnifiedValidation();
        });
        const m = result.mismatches.find(x => x.typ === 'auftrag_alt_ohne_termin');
        expect(m, 'Alter-Auftrag-Anomalie muss erkannt werden').toBeTruthy();
        expect(m.schwere).toBe('warnung');
    });

    test('Versanddatum gesetzt aber AMM-Anmeldung leer → info', async ({ page }) => {
        await openDashboard(page);
        const result = await page.evaluate(() => {
            window.resetAllSessionState();
            const future = new Date(); future.setDate(future.getDate() + 5); future.setHours(0,0,0,0);
            window.state.pipeline.fulfillmentDataMap = {
                'AU_TERMIN_OHNE_ANMELDUNG': {
                    auftragAlterTage: 5,
                    versandDatum: future,
                    versandStr: '02.05.2026',
                    istWarteText: false,
                    versandAngemeldet: false,
                    versandAnmeldungStr: '',
                    leadTimeTage: null,
                    anmeldeDatum: null
                }
            };
            return window.runUnifiedValidation();
        });
        const m = result.mismatches.find(x => x.typ === 'versand_nicht_angemeldet');
        expect(m).toBeTruthy();
        expect(m.schwere).toBe('info');
    });

    test('Versand bereits angemeldet → keine Anomalie', async ({ page }) => {
        await openDashboard(page);
        const result = await page.evaluate(() => {
            window.resetAllSessionState();
            const future = new Date(); future.setDate(future.getDate() + 5); future.setHours(0,0,0,0);
            window.state.pipeline.fulfillmentDataMap = {
                'AU_OK': {
                    auftragAlterTage: 5,
                    versandDatum: future,
                    versandStr: '02.05.2026',
                    istWarteText: false,
                    versandAngemeldet: true,
                    versandAnmeldungStr: 'angemeldet',
                    leadTimeTage: 5,
                    anmeldeDatum: null
                }
            };
            return window.runUnifiedValidation();
        });
        const m = result.mismatches.find(x =>
            x.typ === 'versand_nicht_angemeldet' && x.auftrag === 'AU_OK');
        expect(m).toBeUndefined();
    });

    test('Lead-Time > 21 Tage → info', async ({ page }) => {
        await openDashboard(page);
        const result = await page.evaluate(() => {
            window.resetAllSessionState();
            window.state.pipeline.fulfillmentDataMap = {
                'AU_SLOW': {
                    auftragAlterTage: 25,
                    versandDatum: new Date(),
                    versandStr: '',
                    istWarteText: false,
                    versandAngemeldet: true,
                    versandAnmeldungStr: 'angemeldet',
                    leadTimeTage: 25,
                    kunde: 'TestKunde',
                    anmeldeDatum: null
                }
            };
            return window.runUnifiedValidation();
        });
        const m = result.mismatches.find(x => x.typ === 'lange_lead_time');
        expect(m).toBeTruthy();
        expect(m.detail).toContain('25');
    });
});
