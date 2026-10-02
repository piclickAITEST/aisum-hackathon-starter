/* Wires the four panels to this server's /api/* routes. No framework. */

function show(id, text) {
  const el = document.getElementById(id);
  el.hidden = false;
  el.textContent = text;
}

function status(id, text) {
  document.getElementById(id).textContent = text;
}

async function postJSON(url, body) {
  const r = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  const data = await r.json();
  if (!r.ok) throw new Error(data.error || `HTTP ${r.status}`);
  return data;
}

async function getJSON(url) {
  const r = await fetch(url);
  const data = await r.json();
  if (!r.ok) throw new Error(data.error || `HTTP ${r.status}`);
  return data;
}

// ── 1. Text search — single call ─────────────────────────────────────────
document.getElementById('text-run').addEventListener('click', async () => {
  const query = document.getElementById('text-query').value;
  status('text-status', 'Calling search_products_by_text…');
  try {
    const result = await postJSON('/api/search/text', { query });
    status('text-status', 'Done.');
    show('text-result', JSON.stringify(result, null, 2));
  } catch (e) {
    status('text-status', `Error: ${e.message}`);
  }
});

// ── 2. Image search — single call, slower ───────────────────────────────
document.getElementById('image-run').addEventListener('click', async () => {
  const image_url = document.getElementById('image-url').value;
  status('image-status', 'Calling search_products_by_image… (this one takes a few seconds)');
  try {
    const result = await postJSON('/api/search/image', { image_url });
    status('image-status', 'Done.');
    show('image-result', JSON.stringify(result, null, 2));
  } catch (e) {
    status('image-status', `Error: ${e.message}`);
  }
});

// ── 3. Scene match — two steps, explicit polling loop ────────────────────
// This is the pattern students get stuck on: start the job once, get a task_id,
// then poll with that SAME task_id until it's no longer pending. Never resubmit.
document.getElementById('scene-run').addEventListener('click', async () => {
  const title = document.getElementById('scene-title').value;
  const image_url = document.getElementById('scene-image').value;
  document.getElementById('scene-result').hidden = true;
  status('scene-status', 'Calling start_scene_match…');

  let task_id;
  try {
    const started = await postJSON('/api/scene/start', { title, image_url });
    task_id = started.task_id;
    if (!task_id) throw new Error('No task_id in response: ' + JSON.stringify(started));
  } catch (e) {
    status('scene-status', `Error starting: ${e.message}`);
    return;
  }

  status('scene-status', `Got task_id ${task_id}. Polling get_scene_match_result…`);
  const startedAt = Date.now();
  const maxWaitMs = 120_000;

  while (true) {
    let result;
    try {
      result = await getJSON(`/api/scene/result/${task_id}`);
    } catch (e) {
      status('scene-status', `Error polling: ${e.message}`);
      return;
    }
    const elapsed = Math.round((Date.now() - startedAt) / 1000);
    if (result.status === 'pending') {
      status('scene-status',
        `Still pending — same task_id (${task_id}), ${elapsed}s elapsed. Asking again, not resubmitting.`);
      if (Date.now() - startedAt > maxWaitMs) {
        status('scene-status', `Gave up after ${elapsed}s. The job is not lost — task_id ${task_id} still works.`);
        return;
      }
      await new Promise((r) => setTimeout(r, 3000));
      continue;
    }
    status('scene-status', `Done after ${elapsed}s.`);
    show('scene-result', JSON.stringify(result, null, 2));
    return;
  }
});

// ── 4. LLM gateway check — one call, no agent loop ───────────────────────
document.getElementById('llm-run').addEventListener('click', async () => {
  const prompt = document.getElementById('llm-prompt').value;
  status('llm-status', 'Calling the LLM gateway once…');
  try {
    const result = await postJSON('/api/llm/check', { prompt });
    status('llm-status', 'Done.');
    show('llm-result', result.text);
  } catch (e) {
    status('llm-status', `Error: ${e.message}`);
  }
});
