// Chat endpoint for the course chatbots.
//
//   GET  /api/chat?bot=<folder>  -> the public settings the chat window needs (title, welcome message)
//   POST /api/chat?bot=<folder>  -> sends the conversation to OpenAI and streams the reply back as plain text
//
// Each chatbot is a folder in /bots. Nothing is saved: the browser sends the whole
// conversation with every message, and it is gone when the page is closed.
//
// This file deliberately uses no packages, so there are no library updates to break it.

import { readFile, readdir } from 'node:fs/promises';
import path from 'node:path';

// The model used when a bot's settings.txt doesn't name one.
// The OPENAI_MODEL environment variable in Vercel overrides this.
const DEFAULT_MODEL = 'gpt-5-mini';

const OPENAI_URL = (process.env.OPENAI_BASE_URL || 'https://api.openai.com/v1') + '/chat/completions';

const MAX_STUDENT_MESSAGE_CHARS = 4000;
const MAX_BOT_MESSAGE_CHARS = 20000;
const DEFAULT_MAX_TURNS = 40;
const MAX_DOCUMENT_CHARS = 400000; // roughly 100,000 tokens across all of a bot's documents
const BOTS_DIR = path.join(process.cwd(), 'bots');

// Bot folders only change when the site is redeployed, so each one is read once per server instance.
const botCache = new Map();

export default async function handler(req, res) {
  res.setHeader('Cache-Control', 'no-store');
  res.setHeader('X-Robots-Tag', 'noindex');

  const botId = new URL(req.url, 'http://localhost').searchParams.get('bot') || '';
  let bot;
  try {
    bot = await loadBot(botId);
  } catch (err) {
    if (err.notFound) {
      return sendError(res, 404, 'This chatbot could not be found. Check the link, or contact your instructor.');
    }
    console.error(`Bot "${botId}" could not be loaded:`, err.message);
    return sendError(res, 500, 'This chatbot is not set up correctly. Please let your instructor know.');
  }

  if (req.method === 'GET') {
    return sendJson(res, 200, {
      title: bot.settings.title || 'Chatbot',
      botName: bot.settings.bot_name || 'Assistant',
      description: bot.settings.description || '',
      welcomeMessage: bot.welcomeMessage,
      notice: bot.settings.notice || '',
      maxStudentMessageChars: MAX_STUDENT_MESSAGE_CHARS,
    });
  }

  if (req.method !== 'POST') {
    res.setHeader('Allow', 'GET, POST');
    return sendError(res, 405, 'Method not allowed.');
  }

  if (!process.env.OPENAI_API_KEY) {
    console.error('OPENAI_API_KEY is not set in the Vercel environment variables.');
    return sendError(res, 500, 'The chatbot service is not set up yet. Please let your instructor know.');
  }

  let messages;
  try {
    messages = checkMessages((await readJson(req)).messages, bot.maxTurns);
  } catch (err) {
    return sendError(res, 400, err.message);
  }

  const body = {
    model: bot.settings.model || process.env.OPENAI_MODEL || DEFAULT_MODEL,
    messages: [{ role: 'system', content: bot.systemPrompt }, ...messages],
    stream: true,
    store: false,
  };
  if (bot.settings.reasoning_effort) body.reasoning_effort = bot.settings.reasoning_effort;

  let upstream;
  try {
    upstream = await fetch(OPENAI_URL, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${process.env.OPENAI_API_KEY}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(55000),
    });
  } catch (err) {
    console.error('Could not reach OpenAI:', err.message);
    return sendError(res, 502, 'The chatbot could not be reached. Please try again in a moment.');
  }

  if (!upstream.ok) {
    console.error(`OpenAI returned ${upstream.status} for bot "${botId}":`, await upstream.text());
    const message = upstream.status === 429
      ? 'The chatbot is busy right now. Please wait a minute and try again.'
      : 'The chatbot had a problem answering. Please try again, and let your instructor know if it keeps happening.';
    return sendError(res, 502, message);
  }

  res.statusCode = 200;
  res.setHeader('Content-Type', 'text/plain; charset=utf-8');
  res.setHeader('X-Accel-Buffering', 'no');

  // OpenAI streams "server-sent events"; pass only the reply text through to the browser.
  try {
    const reader = upstream.body.getReader();
    const decoder = new TextDecoder();
    let buffered = '';
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffered += decoder.decode(value, { stream: true });
      const lines = buffered.split('\n');
      buffered = lines.pop();
      for (const line of lines) {
        const text = replyTextFromEvent(line);
        if (text) res.write(text);
      }
    }
  } catch (err) {
    console.error('The reply stream was interrupted:', err.message);
    res.write('\n\n[The reply was interrupted. Please try again.]');
  }
  res.end();
}

function replyTextFromEvent(line) {
  const trimmed = line.trim();
  if (!trimmed.startsWith('data:')) return '';
  const data = trimmed.slice(5).trim();
  if (data === '[DONE]') return '';
  try {
    return JSON.parse(data).choices?.[0]?.delta?.content || '';
  } catch {
    return '';
  }
}

async function loadBot(botId) {
  // Folder names: lowercase letters, numbers and dashes. Folders starting with "_" (like _template) are never served.
  if (!/^[a-z0-9][a-z0-9-]{0,99}$/.test(botId)) throw notFound();
  if (botCache.has(botId)) return botCache.get(botId);

  const folder = path.join(BOTS_DIR, botId);
  let instructions;
  try {
    instructions = (await readFile(path.join(folder, 'instructions.md'), 'utf8')).trim();
  } catch {
    throw notFound();
  }
  if (!instructions) throw new Error('instructions.md is empty');

  let welcomeMessage = '';
  try {
    welcomeMessage = (await readFile(path.join(folder, 'welcome.md'), 'utf8')).trim();
  } catch {
    // welcome.md is optional
  }

  let settings = {};
  try {
    settings = parseSettings(await readFile(path.join(folder, 'settings.txt'), 'utf8'));
  } catch {
    // settings.txt is optional
  }

  const documents = await loadDocuments(path.join(folder, 'documents'));
  const totalChars = documents.reduce((sum, doc) => sum + doc.text.length, 0);
  if (totalChars > MAX_DOCUMENT_CHARS) {
    throw new Error(`documents total ${totalChars} characters; the limit is ${MAX_DOCUMENT_CHARS}`);
  }

  let systemPrompt = instructions;
  if (documents.length) {
    systemPrompt += '\n\n# Reference documents\n\nThe following documents are provided for this conversation.\n';
    for (const doc of documents) {
      systemPrompt += `\n<document name="${doc.name}">\n${doc.text}\n</document>\n`;
    }
  }

  const maxTurns = parseInt(settings.max_turns, 10) > 0 ? parseInt(settings.max_turns, 10) : DEFAULT_MAX_TURNS;
  const bot = { settings, welcomeMessage, systemPrompt, maxTurns };
  botCache.set(botId, bot);
  return bot;
}

async function loadDocuments(folder) {
  let names;
  try {
    names = await readdir(folder);
  } catch {
    return [];
  }
  names = names.filter((name) => /\.(md|txt)$/i.test(name) && !name.startsWith('_')).sort();
  const documents = [];
  for (const name of names) {
    const text = (await readFile(path.join(folder, name), 'utf8')).trim();
    if (text) documents.push({ name, text });
  }
  return documents;
}

// settings.txt has one "key: value" per line. Lines starting with # are notes and are ignored.
function parseSettings(text) {
  const settings = {};
  for (const line of text.split(/\r?\n/)) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#')) continue;
    const colon = trimmed.indexOf(':');
    if (colon < 0) continue;
    const key = trimmed.slice(0, colon).trim().toLowerCase();
    const value = trimmed.slice(colon + 1).trim();
    if (value) settings[key] = value;
  }
  return settings;
}

function checkMessages(messages, maxTurns) {
  if (!Array.isArray(messages) || messages.length === 0) throw new Error('No message was sent.');
  if (messages.filter((m) => m && m.role === 'user').length > maxTurns) {
    throw new Error('This conversation has reached its length limit. Use "Start over" to begin a new one.');
  }
  const cleaned = messages.map((m) => {
    if (!m || (m.role !== 'user' && m.role !== 'assistant') || typeof m.content !== 'string') {
      throw new Error('The conversation could not be read. Please use "Start over".');
    }
    const limit = m.role === 'user' ? MAX_STUDENT_MESSAGE_CHARS : MAX_BOT_MESSAGE_CHARS;
    if (m.content.length > limit) {
      throw new Error(`Messages can be at most ${MAX_STUDENT_MESSAGE_CHARS} characters. Please shorten yours.`);
    }
    return { role: m.role, content: m.content };
  });
  if (cleaned[cleaned.length - 1].role !== 'user' || !cleaned[cleaned.length - 1].content.trim()) {
    throw new Error('No message was sent.');
  }
  return cleaned;
}

async function readJson(req) {
  if (req.body !== undefined) return typeof req.body === 'string' ? JSON.parse(req.body) : req.body;
  let raw = '';
  for await (const chunk of req) raw += chunk;
  try {
    return JSON.parse(raw || '{}');
  } catch {
    return {};
  }
}

function notFound() {
  const err = new Error('not found');
  err.notFound = true;
  return err;
}

function sendJson(res, status, data) {
  res.statusCode = status;
  res.setHeader('Content-Type', 'application/json; charset=utf-8');
  res.end(JSON.stringify(data));
}

function sendError(res, status, message) {
  sendJson(res, status, { error: message });
}
