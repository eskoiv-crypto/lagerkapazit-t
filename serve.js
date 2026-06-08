// Tiny localhost server für Dashboard — kein npm install nötig (nur Node-Built-Ins).
// Aufruf:  node serve.js
//          node serve.js 9000     (anderer Port)
//
// Pfad: http://localhost:8080/elvinci_lagerkapazitaet_dashboard_v2026-04-20.html
// Default-Route /  → leitet auf Dashboard um
//
// MSAL/Azure-AD akzeptiert http://localhost als Redirect-URI per Default-RFC-8252,
// damit funktionieren OAuth-Login (10X-10) und SharePoint-Sync (10X-5) lokal
// ohne HTTPS-Zertifikat.
//
// Falls echtes HTTPS gebraucht wird (production-like, externe Hosts):
//   npm install -g local-ssl-proxy
//   local-ssl-proxy --source 8443 --target 8080
//   → https://localhost:8443/...

import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const port = parseInt(process.argv[2]) || 8080;
const DASHBOARD = 'elvinci_lagerkapazitaet_dashboard_v2026-04-20.html';

const MIME = {
    '.html': 'text/html; charset=utf-8',
    '.js':   'application/javascript; charset=utf-8',
    '.json': 'application/json; charset=utf-8',
    '.css':  'text/css; charset=utf-8',
    '.csv':  'text/csv; charset=utf-8',
    '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    '.png':  'image/png',
    '.svg':  'image/svg+xml; charset=utf-8',
    '.ico':  'image/x-icon',
    '.md':   'text/markdown; charset=utf-8'
};

const server = http.createServer((req, res) => {
    let url = decodeURIComponent(req.url.split('?')[0]);
    if (url === '/' || url === '') url = '/' + DASHBOARD;
    const filePath = path.resolve(__dirname, '.' + url);
    // Security: kein Pfad-Traversal raus aus dem Projekt-Root
    if (!filePath.startsWith(__dirname)) {
        res.writeHead(403); res.end('Forbidden'); return;
    }
    fs.stat(filePath, (err, stat) => {
        if (err || !stat.isFile()) {
            res.writeHead(404, { 'Content-Type': 'text/plain; charset=utf-8' });
            res.end(`404 — ${url}\n\nDashboard:  http://localhost:${port}/${DASHBOARD}\nMaster-TODO: http://localhost:${port}/MASTER_TODO_2026-04-20.md\n`);
            return;
        }
        const ext = path.extname(filePath).toLowerCase();
        res.writeHead(200, {
            'Content-Type': MIME[ext] || 'application/octet-stream',
            'Cache-Control': 'no-cache',
            // Permissions für Browser-APIs die das Dashboard nutzt
            'Permissions-Policy': 'clipboard-read=(), clipboard-write=(self)'
        });
        fs.createReadStream(filePath).pipe(res);
    });
});

server.listen(port, '127.0.0.1', () => {
    console.log('');
    console.log('═══════════════════════════════════════════════════════════════');
    console.log('  NH5 Dashboard — lokaler Server läuft');
    console.log('═══════════════════════════════════════════════════════════════');
    console.log('');
    console.log(`  Dashboard:    http://localhost:${port}/${DASHBOARD}`);
    console.log(`  Master-TODO:  http://localhost:${port}/MASTER_TODO_2026-04-20.md`);
    console.log(`  Tests-Fixtures: http://localhost:${port}/tests/fixtures/`);
    console.log('');
    console.log('  Stop:  Ctrl+C in dieser Konsole');
    console.log('');
    console.log('  10X-5 SharePoint-Sync + 10X-10 Azure-AD-Login werden auf');
    console.log(`  http://localhost:${port}/... funktionieren — sobald elvinci-IT die`);
    console.log('  Azure-AD-App-Registrierung mit dieser URL als Redirect-URI');
    console.log('  freigeschaltet hat.');
    console.log('');
});
