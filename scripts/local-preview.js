// Runs the chatbots on your own computer for testing, without Vercel.
//
//   OPENAI_API_KEY=sk-... node scripts/local-preview.js
//   then open http://localhost:3000/?bot=example-patient-roleplay

import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import path from 'node:path';
import handler from '../api/chat.js';

const PORT = process.env.PORT || 3000;
const PUBLIC_DIR = path.join(process.cwd(), 'public');
const TYPES = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css' };

createServer(async (req, res) => {
  const { pathname } = new URL(req.url, 'http://localhost');
  if (pathname === '/api/chat') return handler(req, res);

  const file = path.join(PUBLIC_DIR, pathname === '/' ? 'index.html' : pathname);
  if (!file.startsWith(PUBLIC_DIR)) return res.writeHead(404).end();
  try {
    const content = await readFile(file);
    res.writeHead(200, { 'Content-Type': (TYPES[path.extname(file)] || 'text/plain') + '; charset=utf-8' });
    res.end(content);
  } catch {
    res.writeHead(404).end('Not found');
  }
}).listen(PORT, () => {
  console.log(`Preview running at http://localhost:${PORT}/?bot=example-patient-roleplay`);
});
