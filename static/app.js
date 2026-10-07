/* Wires the six checks to this server's /api/* routes. No framework.
 *
 * Results are shown as raw JSON on purpose. What becomes of them is yours to
 * design, not this kit's.
 */

const $ = (id) => document.getElementById(id);

function show(id, text) {
  const el = $(id);
  el.hidden = false;
  el.textContent = text;
}

// state: running | ok | error — style.css turns it into the ✓ / ✗ you read first.
function status(id, text, state = 'running') {
  $(id).textContent = text;
  $(id).dataset.state = state;
}

// The raw response, folded, with its size — shown as-is on purpose.
function showRaw(prefix, data) {
  const json = JSON.stringify(data, null, 2);
  $(`${prefix}-result`).textContent = json;
  $(`${prefix}-raw`).querySelector('summary').textContent =
    `Raw JSON · ${(json.length / 1024).toFixed(1)} KB`;
  $(`${prefix}-raw`).hidden = false;
}

const secs = (t0) => ((performance.now() - t0) / 1000).toFixed(2);

// ── Progress strip ───────────────────────────────────────────────────────
// Only what actually passed in this browser session. Nothing is stored.
function mark(step, state) {
  document.querySelector(`#progress [data-step="${step}"]`).dataset.state = state;
}
const mcpPassed = new Set();
function mcpOk(panel) {
  mcpPassed.add(panel);
  mark('mcp', mcpPassed.size === 4 ? 'done' : 'partial');
}
window.addEventListener('authchange', (e) => mark('signin', e.detail.user ? 'done' : 'todo'));
if (window.__auth?.user) mark('signin', 'done');
// Served from anywhere but your laptop means it is deployed.
if (!['localhost', '127.0.0.1'].includes(location.hostname)) mark('deploy', 'done');

// Every /api/* call carries the signed-in user's Firebase ID token; the server
// checks it (src/auth.py). window.__auth comes from auth.js.
async function authHeaders() {
  const token = await window.__auth?.token();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function readJSON(r) {
  const data = await r.json();
  if (!r.ok) {
    // FastAPI puts its own errors (401 from src/auth.py) in `detail`.
    const e = new Error(data.error || data.detail || `HTTP ${r.status}`);
    e.data = data;
    throw e;
  }
  return data;
}

async function postJSON(url, body) {
  return readJSON(await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...(await authHeaders()) },
    body: JSON.stringify(body),
  }));
}

async function getJSON(url) {
  return readJSON(await fetch(url, { headers: await authHeaders() }));
}

// ── 1. Text search — single call ─────────────────────────────────────────
$('text-run').addEventListener('click', async () => {
  const query = $('text-query').value;
  status('text-status', 'Calling search_products_by_text…');
  const t0 = performance.now();
  try {
    const result = await postJSON('/api/search/text', { query });
    status('text-status', `Done in ${secs(t0)} s (browser → this app → MCP → back).`, 'ok');
    showRaw('text', result);
    mcpOk('text');
  } catch (e) {
    status('text-status', `Error after ${secs(t0)} s: ${e.message}`, 'error');
  }
});

// ── 2. Image search — single call ────────────────────────────────────────
$('image-run').addEventListener('click', async () => {
  const image_url = $('image-url').value;
  status('image-status', 'Calling search_products_by_image…');
  const t0 = performance.now();
  try {
    const result = await postJSON('/api/search/image', { image_url });
    status('image-status', `Done in ${secs(t0)} s.`, 'ok');
    showRaw('image', result);
    mcpOk('image');
  } catch (e) {
    status('image-status', `Error after ${secs(t0)} s: ${e.message}`, 'error');
  }
});

// ── 3–4. Scene and video match — two steps, explicit polling loop ─────────
// This is the pattern students get stuck on: start the job once, get a task_id,
// then poll with that SAME task_id until it's no longer pending. Never resubmit.
async function startThenPoll(prefix, kind, body, maxWaitMs) {
  $(`${prefix}-raw`).hidden = true;
  status(`${prefix}-status`, `Calling start_${kind}_match…`);
  const t0 = performance.now();

  let task_id;
  try {
    const started = await postJSON(`/api/${kind}/start`, body);
    task_id = started.task_id;
    if (!task_id) throw new Error('No task_id in response: ' + JSON.stringify(started));
  } catch (e) {
    status(`${prefix}-status`, `Error starting: ${e.message}`, 'error');
    return;
  }

  status(`${prefix}-status`,
    `Got task_id ${task_id} in ${secs(t0)} s. Polling get_${kind}_match_result…`);
  let polls = 0;

  while (true) {
    let result;
    try {
      result = await getJSON(`/api/${kind}/result/${encodeURIComponent(task_id)}`);
      polls += 1;
    } catch (e) {
      status(`${prefix}-status`, `Error polling: ${e.message}`, 'error');
      return;
    }
    if (result.status === 'pending') {
      status(`${prefix}-status`,
        `Still pending — same task_id (${task_id}), ${secs(t0)} s since start, `
        + `poll #${polls}. Asking again, not resubmitting.`);
      if (performance.now() - t0 > maxWaitMs) {
        status(`${prefix}-status`,
          `Gave up after ${secs(t0)} s. The job is not lost — task_id ${task_id} still works.`,
          'error');
        return;
      }
      await new Promise((r) => setTimeout(r, 3000));
      continue;
    }
    status(`${prefix}-status`, `Done in ${secs(t0)} s from start, after ${polls} poll(s).`, 'ok');
    showRaw(prefix, result);
    mcpOk(prefix);
    return;
  }
}

$('scene-run').addEventListener('click', () => startThenPoll('scene', 'scene',
  { title: $('scene-title').value, image_url: $('scene-image').value }, 120_000));

// A video nobody has run before takes minutes, so the wait limit is longer.
$('video-run').addEventListener('click', () => startThenPoll('video', 'video',
  { video_url: $('video-url').value }, 600_000));

// ── 5. LLM gateway check — one call, no agent loop ───────────────────────
$('llm-run').addEventListener('click', async () => {
  const prompt = $('llm-prompt').value;
  status('llm-status', 'Calling the LLM gateway once…');
  const t0 = performance.now();
  try {
    const { text, finish_reason } = await postJSON('/api/llm/check', { prompt });
    // 200 OK with nothing in it: the reasoning used up max_tokens (docs/troubleshooting.md).
    const empty = text === '' && finish_reason === 'length';
    status('llm-status', `Done in ${secs(t0)} s. finish_reason: ${finish_reason}`
      + (empty ? ' — empty answer: max_tokens was used up by reasoning. Raise it; '
               + 'retrying the same request comes back empty again.' : ''),
      empty ? 'error' : 'ok');
    show('llm-result', text);
    if (!empty) mark('llm', 'done');
  } catch (e) {
    status('llm-status', `Error after ${secs(t0)} s: ${e.message}`, 'error');
  }
});

// ── 6. One tool call, end to end ─────────────────────────────────────────
// The server does the four steps and reports each one. This only prints them, so
// what the model asked for, what MCP returned, and what went back are all visible.
const stepSecs = (s) => (s.seconds === undefined ? '' : `${s.seconds} s`);

function renderStep(s) {
  $(`tc-s${s.step}`).closest('li').hidden = false;
  if (s.step === 1) {
    $('tc-s1-secs').textContent = stepSecs(s);
    const parse = (a) => { try { return JSON.parse(a); } catch { return a; } };
    const calls = s.tool_calls.map((c) => ({
      id: c.id, name: c.name, arguments: parse(c.arguments),
    }));
    show('tc-s1', `finish_reason: ${s.finish_reason}\n`
      + `tool_calls: ${JSON.stringify(calls, null, 2)}`
      + (s.content ? `\ncontent: ${s.content}` : ''));
  } else if (s.step === 2) {
    $('tc-s2-secs').textContent = stepSecs(s);
    show('tc-s2', `${s.tool}(${JSON.stringify(s.arguments)})\n\n`
      + JSON.stringify(s.result, null, 2));
  } else if (s.step === 3) {
    show('tc-s3', `messages: ${JSON.stringify(s.messages_sent, null, 2)}\n`
      + `the role:"tool" message carries ${s.tool_content_chars} characters of JSON`);
  } else if (s.step === 4) {
    $('tc-s4-secs').textContent = stepSecs(s);
    show('tc-s4', `finish_reason: ${s.finish_reason}\n\n${s.content}`
      + (s.asked_for_another_call
        ? '\n\n(The model asked for another tool call. A loop would run it; this demo stops here.)'
        : ''));
  }
}

$('tc-run').addEventListener('click', async () => {
  const question = $('tc-question').value;
  for (const id of ['tc-s1', 'tc-s2', 'tc-s3', 'tc-s4']) $(id).hidden = true;
  for (const id of ['tc-s1-secs', 'tc-s2-secs', 'tc-s4-secs']) $(id).textContent = '';
  $('tc-steps').hidden = false;
  // A step that never ran shows nothing, not an empty heading.
  for (const li of $('tc-steps').children) li.hidden = true;
  status('tc-status', 'Running: model → MCP → model…');
  const t0 = performance.now();
  try {
    const data = await postJSON('/api/tool-call', { question });
    data.steps.forEach(renderStep);
    status('tc-status', data.note
      ? `Done in ${secs(t0)} s. ${data.note}`
      : `Done in ${secs(t0)} s — two LLM calls and one MCP call.`, 'ok');
    // Done only when all four steps ran; answering without the tool proves less.
    mark('toolcall', data.steps.length === 4 ? 'done' : 'partial');
  } catch (e) {
    // Show the steps that did finish — where it stopped is the useful part.
    (e.data?.steps || []).forEach(renderStep);
    status('tc-status', `Error after ${secs(t0)} s: ${e.message}`, 'error');
  }
});
