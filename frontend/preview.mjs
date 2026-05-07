#!/usr/bin/env node
/**
 * Multi-app static preview server.
 * Routes: / → explorer, /workbench → workbench, /monitor → monitor, /admin → admin
 * Assets are resolved directly from dist/{app}/assets/ via the file-first lookup.
 */
import { createServer } from 'node:http';
import { readFile, stat } from 'node:fs/promises';
import { resolve, extname } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = fileURLToPath(new URL('.', import.meta.url));
const DIST = resolve(__dirname, 'dist');

const argv = process.argv.slice(2);
function arg(flag, fallback) {
  const i = argv.indexOf(flag);
  return i !== -1 ? argv[i + 1] : fallback;
}
const PORT = Number(arg('--port', '4173'));
const HOST = arg('--host', '127.0.0.1');

const MIME = {
  '.html':  'text/html; charset=utf-8',
  '.js':    'text/javascript; charset=utf-8',
  '.mjs':   'text/javascript; charset=utf-8',
  '.css':   'text/css; charset=utf-8',
  '.json':  'application/json',
  '.svg':   'image/svg+xml',
  '.png':   'image/png',
  '.jpg':   'image/jpeg',
  '.webp':  'image/webp',
  '.ico':   'image/x-icon',
  '.woff2': 'font/woff2',
  '.woff':  'font/woff',
  '.ttf':   'font/ttf',
  '.txt':   'text/plain; charset=utf-8',
};

// Longest-prefix-first so /workbench doesn't match /
const APPS = [
  ['/workbench', 'workbench'],
  ['/monitor',   'monitor'],
  ['/admin',     'admin'],
  ['/',          'explorer'],
];

function resolveApp(pathname) {
  for (const [prefix, dir] of APPS) {
    if (prefix === '/' || pathname === prefix || pathname.startsWith(prefix + '/')) {
      return dir;
    }
  }
  return 'explorer';
}

createServer(async (req, res) => {
  const url = new URL(req.url, `http://${HOST}:${PORT}`);
  const pathname = url.pathname;

  // Try to serve an existing file from dist/
  const filePath = resolve(DIST, pathname.replace(/^\//, ''));
  try {
    const s = await stat(filePath);
    if (s.isFile()) {
      const body = await readFile(filePath);
      const mime = MIME[extname(filePath).toLowerCase()] ?? 'application/octet-stream';
      res.writeHead(200, { 'Content-Type': mime, 'Cache-Control': 'no-store' });
      return res.end(body);
    }
  } catch { /* not a file — fall through to SPA fallback */ }

  // SPA fallback: serve the app's index.html
  const appDir = resolveApp(pathname);
  try {
    const body = await readFile(resolve(DIST, appDir, 'index.html'));
    res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8', 'Cache-Control': 'no-store' });
    res.end(body);
  } catch {
    res.writeHead(404);
    res.end('Not found');
  }
}).listen(PORT, HOST, () => {
  console.log(`\n  Preview  http://${HOST}:${PORT}/\n`);
  for (const [prefix, dir] of APPS) {
    console.log(`    ${(prefix + '/').padEnd(14)} → ${dir}`);
  }
  console.log();
});
