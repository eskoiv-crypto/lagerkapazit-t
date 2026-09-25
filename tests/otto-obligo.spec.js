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
        // Fälligkeit aus dem PDF-Pfad = Rechnungsdatum + ZAHLZIEL (28 Tage, Otto-Standard).
        // Belegt am Agicap-Export: von 24 Zeilen tragen 20 genau 28 Tage Zahlungsziel, 3 haben 29, eine 30.
        // Vorher galt pauschal +30 -> Belege ohne Agicap-Fälligkeitsdatum landeten 2 Tage zu spät im Zahlungsplan.
        expect(it).toEqual({ ref: '1001E026990001', rd: '2026-09-08', fa: '2026-10-06', src: 'pdf', plombe: null });
        expect(errors).toEqual([]);
    });

    test('mehrere PDFs auf einmal + Plombe + Rückfall ohne Anker wird markiert', async ({ page }) => {
        await open(page);
        await payInput(page).setInputFiles(fx('otto_test_invoice.pdf', 'otto_test_invoice_plombe.pdf', 'otto_test_invoice_no_anchor.pdf'));
        await expect(status(page)).toContainText('Σ 3 offen (11.735 €)');       // 1.234,91 + 10.000,00 + 500,00
        const log = page.locator('#payLog');
        await expect(log).toContainText('1001E026990002 · 10.000,00 €');
        await expect(log).toContainText('1001E026990003 · 500,00 €');
        await expect(log).toContainText('⚠️ Brutto aus netto + USt rekonstruiert');
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

    test('CID-Beleg (Type0/Identity-H mit ToUnicode) wird gelesen — Betrag, Rechnungsnr, Datum, Plombe', async ({ page }) => {
        // Otto bettet Mailverläufe und Artikel-Aufstellungen in CID-Fonts ein; ohne CMap-Dekodierung ist so ein Beleg unlesbar.
        const errors = await open(page);
        await payInput(page).setInputFiles(fx('otto_test_invoice_cid.pdf'));
        await expect(status(page)).toContainText('Σ 1 offen (2.500 €)');
        await expect(page.locator('#payLog')).toContainText('1001E026990004 · 2.500,00 €');
        await expect(page.locator('#payLog')).toContainText('Gegenprobe ✓ netto 2.100,84 € + USt 399,16 €');
        const it = await page.evaluate(() => { const i = window.__obligoState.agicap.items[0];
            return { ref: i.ref, brutto: i.brutto, rd: i.rd?.toISOString().slice(0, 10), plombe: i.plombe, via: i.via, check: i.check }; });
        expect(it).toEqual({ ref: '1001E026990004', brutto: 2500, rd: '2026-09-15', plombe: '4473126', via: 'anker', check: 'ok' });
        expect(errors).toEqual([]);
    });

    test('Rückfall ohne Anker nimmt NICHT den letzten Betrag des Dokuments (Anlage-Seite mit höherem Betrag)', async ({ page }) => {
        // Die Anlage endet mit 767.003,48 € — ein dokumentweiter "letzter Betrag" wäre um Faktor 1500 daneben.
        await open(page);
        await payInput(page).setInputFiles(fx('otto_test_invoice_no_anchor.pdf'));
        await expect(status(page)).toContainText('Σ 1 offen (500 €)');
        const it = await page.evaluate(() => { const i = window.__obligoState.agicap.items[0]; return { brutto: i.brutto, via: i.via, check: i.check }; });
        expect(it).toEqual({ brutto: 500, via: 'summe', check: 'ok' });
    });

    test('Retouren-Abzug wird in BEIDEN Otto-Schreibweisen erkannt — Vergütung und Abschlag', async ({ page }) => {
        // Derselbe prozentuale Abzug steht auf den Belegen mal als "Retourenvergütung", mal als "Retourenabschlag".
        // Wird eine Variante nicht erkannt, fällt die Gegenprobe auf die Zwischensumme zurück (hier 10.000,00
        // statt 2.500,00) und meldet fälschlich eine Abweichung. Fixture-Zahlen sind synthetisch.
        for (const suf of ['verguetung', 'abschlag']) {
            const errors = await open(page);
            await payInput(page).setInputFiles(fx(`otto_test_invoice_retoure_${suf}.pdf`));
            await expect(status(page)).toContainText('Σ 1 offen (2.975 €)');
            const it = await page.evaluate(() => { const i = window.__obligoState.agicap.items[0];
                return { brutto: i.brutto, verg: i.verg, vergPct: i.vergPct, zwischen: i.zwischen, nettoBasis: i.nettoBasis, check: i.check }; });
            expect(it, `Schreibweise ${suf}`).toEqual({ brutto: 2975, verg: -7500, vergPct: '75,00',
                zwischen: 10000, nettoBasis: 2500, check: 'ok' });
            expect(errors).toEqual([]);
        }
    });

    test('mehrere Rechnungen in einer Datei werden abgewiesen statt still nur eine zu zählen', async ({ page }) => {
        await open(page);
        await payInput(page).setInputFiles(fx('otto_test_multi_invoice.pdf'));
        await expect(page.locator('#loaderr .warn.bad')).toContainText('enthält mehrere Otto-Rechnungen');
        await expect(page.locator('#loaderr .warn.bad')).toContainText('1001E026990007, 1001E026990008');
        expect(await page.evaluate(() => window.__obligoState.agicap)).toBeNull();
    });

    test('Kontinuitätsprüfung: Abfluss über verschwundene Rechnungen, Topfwechsel bleibt neutral', async ({ page }) => {
        // Zwischen zwei Auswertungen darf sich das Obligo NUR durch neue Anlieferungen (+) und Abfluss (−) ändern.
        // Wandert ein LKW von "warten" nach Agicap, ist das derselbe LKW in einem anderen Topf -> muss neutral sein.
        // Der Abfluss wird NICHT aus dem Zahlungsdatum gelesen: der Agicap-Export führt nur offene Rechnungen,
        // eine bezahlte verschwindet daraus schlicht. Über das Zahlungsdatum wäre der Abfluss immer 0 und die
        // Prüfung schlüge an jedem Zahltag falschen Alarm.
        await open(page);
        await page.evaluate(() => {
            const tag = 86400000, gestern = new Date(midnight(new Date()).getTime() - tag);
            localStorage.setItem('ottoObligo.snapshot.v2', JSON.stringify({
                iso: gestern.toISOString().slice(0, 10), obligo: 100000, agiOpen: 80000, wartenSum: 20000,
                hasBe: true, refs: ['P1', 'P2'],
                invKeys: [['1001E026990101', 5000], ['1001E026990102', 30000]],   // gestern offen
            }));
        });
        await page.reload();                                   // PREV_SNAP wird beim Laden einmalig eingelesen
        const out = await page.evaluate(() => {
            const heute = midnight(new Date());
            const mkR = obligo => ({
                asof: heute, obligo,
                // 1001E026990101 ist heute NICHT mehr offen -> 5.000 abgeflossen (bezahlt oder storniert)
                agi: { items: [{ ref: '1001E026990102', brutto: 30000, rd: heute, zd: null, paid: false }] },
                be: { orders: [ { ref: 'P1', gross: 10000, stat: 'Bestellung' }, { ref: 'P2', gross: 10000, stat: 'Bestellung' },
                                { ref: 'P3', gross: 20000, stat: 'Bestellung' } ] },   // P3 ist neu
            });
            const pick = k => ({ neuN: k.neuN, neuSum: k.neuSum, abfluss: k.zahlung, abflussN: k.zahlN,
                                 erwartet: k.erwartet, diff: Math.round(k.diff), ok: k.ok });
            return { sauber: pick(kontinuitaet(mkR(115000))),   // 100.000 + 20.000 neu − 5.000 Abfluss
                     luecke: pick(kontinuitaet(mkR(155000))) }; // 40.000 mehr als erklärbar
        });
        expect(out.sauber).toEqual({ neuN: 1, neuSum: 20000, abfluss: 5000, abflussN: 1, erwartet: 115000, diff: 0, ok: true });
        expect(out.luecke).toEqual({ neuN: 1, neuSum: 20000, abfluss: 5000, abflussN: 1, erwartet: 115000, diff: 40000, ok: false });
    });

    test('Verlaufskurve wird nicht als Obligo-Historie ausgegeben, wenn der Export nur Offenes enthält', async ({ page }) => {
        // Der Standard-Agicap-Export ("Ausstehende Rechnungen") führt ausschließlich Rechnungen mit Status
        // "Zu zahlen". Bezahlte verschwinden daraus. Eine Rückrechnung über solche Daten startet zwangsläufig
        // bei 0, kann nie fallen und ist KEIN historisches Obligo — das muss die Karte auch so sagen.
        const errors = await open(page);
        await payInput(page).setInputFiles(fx('otto_test_agicap_geprueft.csv'));
        const karte = page.locator('.card').filter({ hasText: 'Aufbau des offenen Bestands' });
        await expect(karte).toBeVisible();
        await expect(karte).toContainText('kein historisches Obligo');
        await expect(karte).toContainText('nur offene Rechnungen');
        await expect(page.locator('.card').filter({ hasText: 'Limit gerissen' })).toHaveCount(0);
        expect(errors).toEqual([]);
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
