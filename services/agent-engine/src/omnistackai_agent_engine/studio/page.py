"""The OmniStackAI Studio page: a self-contained, dependency-free chat-to-create UI.

Served verbatim by ``studio.server`` at ``GET /``. Static and diff-invariant: inline CSS
and JS only, no external requests, no npm/pnpm, no framework. It POSTs the description to
``/api/build`` and renders the resulting generated app.
"""

from __future__ import annotations

STUDIO_HTML = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>OmniStackAI Studio</title>
<style>
  :root { color-scheme: dark; }
  * { box-sizing: border-box; }
  body {
    margin: 0; min-height: 100vh;
    font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
    color: #e6edf3;
    background: radial-gradient(1200px 600px at 50% -10%, #10213f 0%, #070b16 55%, #05070e 100%);
  }
  .wrap { max-width: 860px; margin: 0 auto; padding: 40px 20px 80px; }
  header { text-align: center; margin-bottom: 28px; }
  .brand { font-weight: 700; letter-spacing: .5px; font-size: 14px; color: #6ee7ff; text-transform: uppercase; }
  h1 { margin: 8px 0 6px; font-size: 30px; line-height: 1.2; }
  .sub { color: #9fb0c3; margin: 0; font-size: 15px; }
  form {
    background: rgba(18, 28, 48, 0.72);
    border: 1px solid rgba(110, 231, 255, 0.22);
    border-radius: 16px; padding: 18px;
    box-shadow: 0 12px 40px rgba(0,0,0,0.4);
  }
  textarea {
    width: 100%; min-height: 110px; resize: vertical;
    background: #0b1220; color: #e6edf3;
    border: 1px solid #223148; border-radius: 10px;
    padding: 12px 14px; font-size: 15px; font-family: inherit; outline: none;
  }
  textarea:focus { border-color: #6ee7ff; box-shadow: 0 0 0 3px rgba(110,231,255,0.15); }
  .row { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-top: 12px; flex-wrap: wrap; }
  .examples { display: flex; gap: 8px; flex-wrap: wrap; }
  .ex {
    background: rgba(110,231,255,0.08); color: #bfe9f5;
    border: 1px solid rgba(110,231,255,0.25); border-radius: 999px;
    padding: 6px 12px; font-size: 12.5px; cursor: pointer;
  }
  .ex:hover { background: rgba(110,231,255,0.16); }
  button {
    background: linear-gradient(135deg, #22d3ee, #6366f1); color: #06121f;
    border: 0; border-radius: 10px; padding: 12px 22px;
    font-size: 15px; font-weight: 700; cursor: pointer;
  }
  button:disabled { opacity: .55; cursor: default; }
  .status { margin-top: 18px; padding: 12px 14px; border-radius: 10px; font-size: 14px; }
  .status.building { background: rgba(99,102,241,0.14); border: 1px solid rgba(99,102,241,0.4); color: #c7d2fe; }
  .status.error { background: rgba(244,63,94,0.12); border: 1px solid rgba(244,63,94,0.4); color: #fecdd3; }
  .result {
    margin-top: 22px; background: rgba(18, 28, 48, 0.6);
    border: 1px solid rgba(110,231,255,0.18); border-radius: 16px; padding: 20px;
  }
  .result h2 { margin: 0 0 4px; font-size: 22px; }
  .result .desc { color: #9fb0c3; margin: 0 0 14px; }
  .chips { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 14px; }
  .chip { background: rgba(34,211,238,0.12); border: 1px solid rgba(34,211,238,0.35); color: #a5f3fc; border-radius: 8px; padding: 4px 10px; font-size: 13px; }
  .meta { display: flex; gap: 20px; flex-wrap: wrap; font-size: 13px; color: #9fb0c3; margin-bottom: 12px; }
  .meta b { color: #e6edf3; }
  .path { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; word-break: break-all; }
  .preview { margin: 18px 0; border: 1px solid #223148; border-radius: 12px; overflow: hidden; background: #080e19; }
  .preview-head { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 11px 14px; border-bottom: 1px solid #223148; }
  .preview-head h3 { margin: 0; font-size: 15px; }
  .preview-status { margin: 0; padding: 12px 14px; color: #9fb0c3; font-size: 13px; }
  .preview-open { color: #6ee7ff; font-size: 13px; font-weight: 650; text-decoration: none; }
  .preview-open:hover { text-decoration: underline; }
  .preview-frame { display: block; width: 100%; height: 540px; border: 0; background: #fff; }
  .files { max-height: 320px; overflow: auto; background: #0b1220; border: 1px solid #223148; border-radius: 10px; padding: 10px 14px; }
  .files ul { margin: 0; padding-left: 18px; }
  .files li { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 12.5px; color: #bcd; line-height: 1.55; }
  [hidden] { display: none !important; }
  footer { text-align: center; color: #62748c; font-size: 12px; margin-top: 30px; }
</style>
</head>
<body>
<div class="wrap">
  <header>
    <div class="brand">OmniStackAI Studio</div>
    <h1>Describe your app. We'll build it.</h1>
    <p class="sub">Type what you want in plain English. A real, owned full-stack app is generated locally.</p>
  </header>

  <form id="build-form">
    <textarea id="prompt" placeholder="e.g. Build a recipe box where users save recipes, each recipe has ingredients and cooking steps"></textarea>
    <div class="row">
      <div class="examples" id="examples">
        <span class="ex">A blog with posts and comments</span>
        <span class="ex">A task tracker with projects and tasks</span>
        <span class="ex">A bookstore with books, authors and orders</span>
      </div>
      <button id="build-btn" type="submit">Build app</button>
    </div>
    <div id="status" class="status" hidden></div>
  </form>

  <section id="result" class="result" hidden>
    <h2 id="r-name">App</h2>
    <p class="desc" id="r-desc"></p>
    <div class="chips" id="r-entities"></div>
    <div class="meta">
      <div><b id="r-count">0 files</b> generated</div>
      <div>commit <b id="r-commit"></b></div>
    </div>
    <div class="meta">repo:&nbsp;<span class="path" id="r-path"></span></div>
    <div class="preview" id="preview-panel">
      <div class="preview-head">
        <h3>Live application preview</h3>
        <a id="preview-open" class="preview-open" target="_blank" rel="noreferrer" hidden>Open in new tab</a>
      </div>
      <p id="preview-status" class="preview-status" role="status" aria-live="polite">Preview has not started.</p>
      <iframe
        id="preview-frame"
        class="preview-frame"
        title="Generated application preview"
        sandbox="allow-forms allow-modals allow-popups allow-same-origin allow-scripts"
        referrerpolicy="no-referrer"
        hidden
      ></iframe>
    </div>
    <div class="files"><ul id="r-files"></ul></div>
  </section>

  <footer>Runs on your machine via the local model. No cloud, no account.</footer>
</div>

<script>
(function () {
  var form = document.getElementById('build-form');
  var promptEl = document.getElementById('prompt');
  var btn = document.getElementById('build-btn');
  var statusEl = document.getElementById('status');
  var result = document.getElementById('result');

  function localPreviewUrl(value) {
    if (typeof value !== 'string' || !value) { return null; }
    try {
      var url = new URL(value);
      var localHost = url.hostname === '127.0.0.1' || url.hostname === 'localhost' || url.hostname === '[::1]';
      return url.protocol === 'http:' && localHost ? url.href : null;
    } catch (_) {
      return null;
    }
  }

  function renderPreview(preview) {
    var frame = document.getElementById('preview-frame');
    var open = document.getElementById('preview-open');
    var previewStatus = document.getElementById('preview-status');
    var url = preview && preview.status === 'ready' ? localPreviewUrl(preview.web_url) : null;
    frame.hidden = true;
    frame.removeAttribute('src');
    open.hidden = true;
    open.removeAttribute('href');
    if (url) {
      previewStatus.textContent = preview.message || 'The generated application is running locally.';
      frame.src = url;
      frame.hidden = false;
      open.href = url;
      open.hidden = false;
      return;
    }
    previewStatus.textContent = (preview && preview.message) || 'No browser preview is available for this build.';
  }

  document.getElementById('examples').addEventListener('click', function (e) {
    if (e.target && e.target.classList.contains('ex')) {
      promptEl.value = 'Build ' + e.target.textContent.replace(/^A /, 'a ');
      promptEl.focus();
    }
  });

  function renderResult(data) {
    document.getElementById('r-name').textContent = data.name || 'App';
    document.getElementById('r-desc').textContent = data.description || '';
    var ents = document.getElementById('r-entities');
    ents.innerHTML = '';
    (data.entities || []).forEach(function (name) {
      var chip = document.createElement('span');
      chip.className = 'chip';
      chip.textContent = name;
      ents.appendChild(chip);
    });
    document.getElementById('r-count').textContent = (data.file_count || 0) + ' files';
    document.getElementById('r-path').textContent = data.target_dir || '';
    document.getElementById('r-commit').textContent = (data.commit_sha || '').slice(0, 12);
    renderPreview(data.preview || null);
    var list = document.getElementById('r-files');
    list.innerHTML = '';
    (data.files || []).forEach(function (f) {
      var li = document.createElement('li');
      li.textContent = f;
      list.appendChild(li);
    });
    result.hidden = false;
  }

  form.addEventListener('submit', function (e) {
    e.preventDefault();
    var prompt = promptEl.value.trim();
    if (!prompt) { promptEl.focus(); return; }
    btn.disabled = true;
    result.hidden = true;
    statusEl.hidden = false;
    statusEl.className = 'status building';
    statusEl.textContent = 'Building your app - this runs a local model and can take a moment...';
    fetch('/api/build', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ prompt: prompt })
    }).then(function (res) {
      return res.json().then(function (data) { return { ok: res.ok, status: res.status, data: data }; });
    }).then(function (out) {
      if (!out.ok) { throw new Error((out.data && out.data.error) || ('HTTP ' + out.status)); }
      renderResult(out.data);
      statusEl.hidden = true;
    }).catch(function (err) {
      statusEl.className = 'status error';
      statusEl.textContent = 'Build failed: ' + err.message;
    }).then(function () {
      btn.disabled = false;
    });
  });
})();
</script>
</body>
</html>
"""
