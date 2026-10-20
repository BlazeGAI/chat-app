// The chat window. It talks to /api/chat and keeps the conversation only in this page:
// closing or refreshing the page clears it.

const botId = new URLSearchParams(location.search).get('bot') || '';
const apiUrl = '/api/chat?bot=' + encodeURIComponent(botId);

const els = {
  title: document.getElementById('title'),
  description: document.getElementById('description'),
  log: document.getElementById('log'),
  form: document.getElementById('form'),
  input: document.getElementById('input'),
  send: document.getElementById('send'),
  copy: document.getElementById('copy'),
  reset: document.getElementById('reset'),
  notice: document.getElementById('notice'),
  announcer: document.getElementById('announcer'),
};

let bot = null;
let messages = [];
let busy = false;

init();

async function init() {
  if (!botId) return showFatal('No chatbot was chosen. Check the link, or contact your instructor.');
  try {
    const res = await fetch(apiUrl);
    const data = await res.json();
    if (!res.ok) return showFatal(data.error || 'This chatbot could not be loaded.');
    bot = data;
  } catch {
    return showFatal('This chatbot could not be loaded. Check your connection and refresh the page.');
  }

  els.title.textContent = bot.title;
  document.title = bot.title;
  els.input.maxLength = bot.maxStudentMessageChars;
  if (bot.description) {
    els.description.textContent = bot.description;
    els.description.hidden = false;
  }
  if (bot.notice) {
    els.notice.textContent = bot.notice;
    els.notice.hidden = false;
  }
  startConversation();
  setBusy(false);
}

function startConversation() {
  messages = [];
  els.log.replaceChildren();
  if (bot.welcomeMessage) {
    // The welcome message is part of the conversation, so the bot knows it already said it.
    messages.push({ role: 'assistant', content: bot.welcomeMessage });
    addMessage('assistant', bot.welcomeMessage);
    els.log.scrollTop = 0; // a long welcome should be read from its first line
  }
}

async function send(text) {
  messages.push({ role: 'user', content: text });
  const userBubble = addMessage('user', text);
  els.input.value = '';
  setBusy(true);

  const reply = addMessage('assistant', '');
  reply.body.innerHTML = '<span class="typing" aria-label="Typing">…</span>';

  let replyText = '';
  try {
    const res = await fetch(apiUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ messages }),
    });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      throw new Error(data.error || 'Something went wrong. Please try again.');
    }
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      replyText += decoder.decode(value, { stream: true });
      reply.body.innerHTML = renderMarkdown(replyText);
      scrollToEnd();
    }
    if (!replyText.trim()) throw new Error('The chatbot did not answer. Please try again.');
    messages.push({ role: 'assistant', content: replyText });
    announce(bot.botName + ' says: ' + replyText);
  } catch (err) {
    // Take the failed message back out so the student can retry it.
    messages.pop();
    userBubble.wrapper.remove();
    reply.wrapper.remove();
    els.input.value = text;
    addError(err.message || 'Something went wrong. Please try again.');
  }
  setBusy(false);
  els.input.focus();
}

function addMessage(role, text) {
  const wrapper = document.createElement('div');
  wrapper.className = 'message ' + role;
  const who = document.createElement('div');
  who.className = 'who';
  who.textContent = role === 'user' ? 'You' : bot.botName;
  const body = document.createElement('div');
  body.className = 'body';
  body.innerHTML = renderMarkdown(text);
  wrapper.append(who, body);
  els.log.append(wrapper);
  scrollToEnd();
  return { wrapper, body };
}

function addError(text) {
  const p = document.createElement('p');
  p.className = 'error';
  p.setAttribute('role', 'alert');
  p.textContent = text;
  els.log.append(p);
  scrollToEnd();
  setTimeout(() => p.remove(), 15000);
}

function showFatal(text) {
  els.title.textContent = 'Chatbot unavailable';
  els.log.replaceChildren();
  addError(text);
  els.copy.disabled = true;
  els.reset.disabled = true;
}

function setBusy(value) {
  busy = value;
  els.input.disabled = value;
  els.send.disabled = value;
  els.reset.disabled = value;
}

function scrollToEnd() {
  els.log.scrollTop = els.log.scrollHeight;
}

function announce(text) {
  els.announcer.textContent = '';
  setTimeout(() => { els.announcer.textContent = text; }, 50);
}

els.form.addEventListener('submit', (event) => {
  event.preventDefault();
  const text = els.input.value.trim();
  if (text && !busy) send(text);
});

els.input.addEventListener('keydown', (event) => {
  if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) {
    event.preventDefault();
    els.form.requestSubmit();
  }
});

els.reset.addEventListener('click', () => {
  const hasStudentMessages = messages.some((m) => m.role === 'user');
  if (hasStudentMessages && !confirm('Start over? This conversation will be cleared.')) return;
  startConversation();
  els.input.focus();
});

els.copy.addEventListener('click', async () => {
  const transcript = bot.title + '\n\n' + messages
    .map((m) => (m.role === 'user' ? 'You' : bot.botName) + ':\n' + m.content)
    .join('\n\n');
  const copied = await copyText(transcript);
  const label = els.copy.textContent;
  els.copy.textContent = copied ? 'Copied' : 'Copy failed';
  announce(copied ? 'Conversation copied to the clipboard.' : 'The conversation could not be copied.');
  setTimeout(() => { els.copy.textContent = label; }, 2000);
});

async function copyText(text) {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    // Some Moodle iframes block the clipboard API; this older method usually still works.
    const area = document.createElement('textarea');
    area.value = text;
    area.setAttribute('readonly', '');
    area.style.position = 'fixed';
    area.style.opacity = '0';
    document.body.append(area);
    area.select();
    const ok = document.execCommand('copy');
    area.remove();
    return ok;
  }
}

// A small, safe Markdown renderer for bot replies: paragraphs, headings, lists,
// bold, italics and code. All text is escaped first, so replies can't inject HTML.
function renderMarkdown(text) {
  const lines = escapeHtml(text).split('\n');
  const html = [];
  let paragraph = [];
  let list = null;
  let inCode = false;
  let code = [];

  const closeParagraph = () => {
    if (paragraph.length) html.push('<p>' + paragraph.map(inline).join('<br>') + '</p>');
    paragraph = [];
  };
  const closeList = () => {
    if (list) html.push('<' + list.tag + '>' + list.items.map((item) => '<li>' + inline(item) + '</li>').join('') + '</' + list.tag + '>');
    list = null;
  };

  for (const line of lines) {
    if (line.trim().startsWith('```')) {
      if (inCode) {
        html.push('<pre><code>' + code.join('\n') + '</code></pre>');
        code = [];
        inCode = false;
      } else {
        closeParagraph();
        closeList();
        inCode = true;
      }
      continue;
    }
    if (inCode) { code.push(line); continue; }

    const heading = line.match(/^(#{1,6})\s+(.*)$/);
    const bullet = line.match(/^\s*[-*+]\s+(.*)$/);
    const numbered = line.match(/^\s*\d+[.)]\s+(.*)$/);

    if (!line.trim()) {
      closeParagraph();
      closeList();
    } else if (heading) {
      closeParagraph();
      closeList();
      html.push('<p class="heading"><strong>' + inline(heading[2]) + '</strong></p>');
    } else if (bullet || numbered) {
      closeParagraph();
      const tag = bullet ? 'ul' : 'ol';
      if (list && list.tag !== tag) closeList();
      if (!list) list = { tag, items: [] };
      list.items.push((bullet || numbered)[1]);
    } else if (list && /^\s{2,}/.test(line)) {
      list.items[list.items.length - 1] += ' ' + line.trim();
    } else {
      closeList();
      paragraph.push(line);
    }
  }
  if (inCode) html.push('<pre><code>' + code.join('\n') + '</code></pre>');
  closeParagraph();
  closeList();
  return html.join('');
}

function inline(text) {
  return text
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/(^|[^*])\*([^*\s][^*]*)\*/g, '$1<em>$2</em>')
    .replace(/(^|\W)_([^_\s][^_]*)_(?=\W|$)/g, '$1<em>$2</em>');
}

function escapeHtml(text) {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}
