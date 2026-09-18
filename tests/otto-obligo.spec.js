// @ts-check
// Otto-Obligo-Cockpit: PDF-Belege lesen (einzeln, mehrfach, in ZIP), Dedup gegen Agicap-CSV, Fehlerfälle.
// Testobjekt: wird vor den Tests frisch gebaut -> otto-obligo/dist/Otto-Obligo-Cockpit.test.html (git-ignoriert, OHNE Historie).
// Fixtures sind SYNTHETISCH (tests/fixtures/make_otto_fixture.cjs) — keine echten Otto-Daten im Repo.
import { test, expect } from '@playwright/test';
import path from 'node:path';
import { pathToFileURL, fileURLToPath } from 'node:url';
import { execFileSync } from 'node:child_process';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const KIT = path.resolve(__dirname, '..', 'otto-obligo', '_build-kit');
const COCKPIT = path.resolve(__dirname, '..', 'otto-obligo', 'dist', 'Otto-Obligo-Cockpit.test.html');
test.beforeAll(() => {
    execFileSync(process.execPath, [path.join(KIT, 'build.cjs'), '--out', COCKPIT, '--no-hist'],
        { env: { ...process.env, OTTO_CFG_PW: 'test-pw' }, stdio: 'inherit' });
});
const FIX = path.resolve(__dirname, 'fixtures');
const fx = (...n) => n.map(f => path.join(FIX, f));

async function open(page) {
    const errors = [];
    page.on('pageerror', e => errors.push('PAGEERROR: ' + e.message));
    page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
    await page.goto(pathToFileURL(COCKPIT).href);
    await page.waitForLoadState('domcontentloaded');
    await expect(page.locator('#d_pay')).toBeVisible();
    return errors;
}
const payInput = page => page.locator('#d_pay input[type=file]');
const status = page => page.locator('#d_pay .st');
const openSum = page => page.locator('#out .kpi.flat .val').first();   // Kachel "Offene Rechnungen (Agicap)"

test.describe('Otto-Obligo-Cockpit · PDF-Belege', () => {

    test('Bibliotheken eingebettet, Drop-Zone akzeptiert PDF + Mehrfachauswahl', async ({ page }) => {
        const errors = await open(page);
        await expect(page.locator('h1')).toHaveText('Otto-Obligo-Cockpit');
        const libs = await page.evaluate(() => ({
            xlsx: typeof window.XLSX, pako: typeof window.pako, inflate: typeof window.pako?.inflateRaw, jspdf: typeof window.jspdf?.jsPDF,
        }));
        expect(libs).toEqual({ xlsx: 'object', pako: 'object', inflate: 'function', jspdf: 'function' });
        await expect(payInput(page)).toHaveAttribute('accept', /\.pdf/);
        await expect(payInput(page)).toHaveAttribute('multiple', '');
        expect(errors).toEqual([]);
    });

    test('einzelnes Otto-PDF (mit Anlage-Seiten): Betrag aus "Gesamt Rechnungsbetrag", Rechnungsnummer aus dem Text', async ({ page }) => {
        const errors = await open(page);
        await payInput(page).setInputFiles(fx('otto_test_invoice.pdf'));
        await expect(status(page)).toContainText('Σ 1 offen (1.235 €)');
        await expect(page.locator('#payLog')).toContainText('1001E026990001 · 1.234,91 €');   // Anlage endet mit 17,99 € -> "letzter Betrag" wäre falsch
        await expect(page.locator('#payLog')).not.toContainText('Anker');
        await expect(openSum(page)).toHaveText('1.235 €');
        // Rechnungsdatum aus dem PDF -> Fälligkeit +30 Tage vorhanden (intern)
        const it = await page.evaluate(() => window.__obligoState?.agicap?.items?.[0] && {
            ref: window.__obligoState.agicap.items[0].ref, rd: window.__obligoState.agicap.items[0].rd?.toISOString().slice(0, 10),
            fa: window.__obligoState.agicap.items[0].faellig?.toISOString().slice(0, 10), src: window.__obligoState.agicap.items[0].src, plombe: window.__obligoState.agicap.items[0].plombe,
        });
        expect(it).toEqual({ ref: '1001E026990001', rd: '2026-09-08', fa: '2026-10-08', src: 'pdf', plombe: null });
        expect(errors).toEqual([]);
    });

    test('mehrere PDFs auf einmal + Plombe + Rückfall ohne Anker wird markiert', async ({ page }) => {
        await open(page);
        await payInput(page).setInputFiles(fx('otto_test_invoice.pdf', 'otto_test_invoice_plombe.pdf', 'otto_test_invoice_no_anchor.pdf'));
        await expect(status(page)).toContainText('Σ 3 offen (11.735 €)');       // 1.234,91 + 10.000,00 + 500,00
        const log = page.locator('#payLog');
        await expect(log).toContainText('1001E026990002 · 10.000,00 €');
        await expect(log).toContainText('1001E026990003 · 500,00 € ⚠️ Betrag ohne „Gesamt Rechnungsbetrag“-Anker');
        const plombe = await page.evaluate(() => window.__obligoState.agicap.items.map(i => i.plombe));
        expect(plombe).toEqual([null, '4473125', null]);
    });

    test('dasselbe PDF zweimal -> nicht doppelt gezählt', async ({ page }) => {
        await open(page);
        await payInput(page).setInputFiles(fx('otto_test_invoice.pdf'));
        await expect(status(page)).toContainText('Σ 1 offen');
        await payInput(page).setInputFiles(fx('Otto GmbH Co. KGaA - 1001EO26990001 Purchase Otto Mix.pdf'));   // gleiche Rechnung, anderer Dateiname
        await expect(status(page)).toContainText('Σ 1 offen (1.235 €)');
        await expect(page.locator('#payLog')).toContainText('bereits geladen — nicht doppelt gezählt');
    });

    test('Agicap-CSV (Geprüft) + PDF derselben Rechnung -> Dedup über Rechnungsnummer, AEG ignoriert', async ({ page }) => {
        await open(page);
        await payInput(page).setInputFiles(fx('otto_test_agicap_geprueft.csv'));
        await expect(status(page)).toContainText('Σ 2 offen (6.235 €)');        // 1.234,91 + 5.000,00 (AEG-Zeile raus)
        await payInput(page).setInputFiles(fx('otto_test_invoice.pdf'));
        await expect(status(page)).toContainText('Σ 2 offen (6.235 €)');        // PDF = Rechnung aus CSV -> kein Zuwachs
        await payInput(page).setInputFiles(fx('otto_test_invoice_plombe.pdf'));
        await expect(status(page)).toContainText('Σ 3 offen (16.235 €)');
    });

    test('ZIP ("Zu prüfen") liest weiterhin alle PDF-Belege, Rechnungsnr aus Text/Dateiname, Warenart aus Dateiname', async ({ page }) => {
        await open(page);
        await payInput(page).setInputFiles(fx('otto_test_zupruefen.zip'));
        await expect(status(page)).toContainText('Σ 2 offen (10.500 €)');
        const items = await page.evaluate(() => window.__obligoState.agicap.items.map(i => ({ ref: i.ref, art: i.art, src: i.src, brutto: i.brutto })));
        expect(items).toEqual([
            { ref: '1001E026990002', art: 'OTTO_Mix', src: 'zip', brutto: 10000 },
            { ref: '1001E026990003', art: 'OTTO_Hanseatic', src: 'zip', brutto: 500 },
        ]);
    });

    test('Fremd-PDF und Nicht-PDF werden mit klarer Meldung abgewiesen, gültige Dateien im selben Drop zählen', async ({ page }) => {
        await open(page);
        await payInput(page).setInputFiles(fx('fremd_test_invoice.pdf', 'otto_test_invoice.pdf'));
        await expect(status(page)).toContainText('Σ 1 offen (1.235 €)');
        await expect(status(page)).toContainText('1 Datei(en) mit Fehler');
        await expect(page.locator('#loaderr .warn.bad')).toContainText('kein Otto-Beleg');
        // Textdatei mit .pdf-Endung
        await payInput(page).setInputFiles({ name: 'kaputt.pdf', mimeType: 'application/pdf', buffer: Buffer.from('das ist kein pdf') });
        await expect(page.locator('#loaderr .warn.bad')).toContainText('ist keine PDF-Datei');
        await expect(status(page)).toContainText('Σ 1 offen (1.235 €)');
    });

    test('PDF-Auswertung (jsPDF) läuft nach PDF-Import ohne Fehler', async ({ page }) => {
        const errors = await open(page);
        await payInput(page).setInputFiles(fx('otto_test_invoice.pdf'));
        await expect(status(page)).toContainText('Σ 1 offen');
        const dl = page.waitForEvent('download');
        await page.click('#btnPdf');
        const d = await dl;
        expect(d.suggestedFilename()).toMatch(/^Otto-Obligo_\d{4}-\d{2}-\d{2}\.pdf$/);
        expect(errors).toEqual([]);
    });
});
