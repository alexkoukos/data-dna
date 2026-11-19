// Tiny ChatGPT-like page for the offline demo and the end-to-end tests. No dependencies.
import { createServer } from 'node:http';
import { readFileSync } from 'node:fs';

const PORT = Number(process.env.PORT ?? 3100);
const page = readFileSync(new URL('./index.html', import.meta.url));
/** What the "AI" actually received, newest last. Tests read this to prove masking happened. */
const received = [];

createServer((req, res) => {
  const url = new URL(req.url ?? '/', 'http://localhost');
  if (req.method === 'GET' && url.pathname === '/healthz') {
    res.writeHead(200, { 'Content-Type': 'text/plain' }).end('ok');
  } else if (req.method === 'GET' && url.pathname === '/api/received') {
    res.writeHead(200, { 'Content-Type': 'application/json' }).end(JSON.stringify(received));
  } else if (req.method === 'DELETE' && url.pathname === '/api/received') {
    received.length = 0;
    res.writeHead(204).end();
  } else if (req.method === 'POST' && url.pathname === '/api/chat') {
    let body = '';
    req.on('data', (c) => (body += c));
    req.on('end', () => {
      const { message = '' } = JSON.parse(body || '{}');
      received.push(message);
      const answer = `Got it. You wrote: "${message}". I will work with exactly that text.`;
      res.writeHead(200, { 'Content-Type': 'application/json' }).end(JSON.stringify({ answer }));
    });
  } else if (req.method === 'GET' && (url.pathname === '/' || url.pathname === '/index.html')) {
    res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' }).end(page);
  } else {
    res.writeHead(404).end();
  }
}).listen(PORT, '0.0.0.0', () => console.log(`mock-ai on :${PORT}`));
