"""The complete HTML/CSS/JS payload for the OmniStackAI Studio web page.

Zero external assets: no CDNs, no web fonts, no external JS/CSS, no analytics.
Self-contained, fully functional offline. Served directly by ``omnistackai_agent_engine.studio.server``.
"""

STUDIO_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>OmniStackAI Studio - Chat to App</title>
<style>
  *, *::before, *::after { box-sizing: border-box; }
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
  .pack-panel {
    margin-top: 14px;
    padding: 12px 14px;
    background: rgba(11, 18, 32, 0.7);
    border: 1px solid #223148;
    border-radius: 10px;
  }
  .pack-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    margin-bottom: 8px;
  }
  .pack-title {
    font-size: 13px;
    font-weight: 600;
    color: #9fb0c3;
    text-transform: uppercase;
    letter-spacing: .4px;
  }
  .pack-banner {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-size: 12px;
    font-weight: 600;
    color: #6ee7ff;
    background: rgba(110, 231, 255, 0.12);
    border: 1px solid rgba(110, 231, 255, 0.3);
    border-radius: 999px;
    padding: 3px 10px;
  }
  .pack-row {
    display: flex;
    gap: 10px;
    align-items: center;
    flex-wrap: wrap;
  }
  .pack-select {
    flex: 1;
    min-width: 220px;
    background: #080e19;
    color: #e6edf3;
    border: 1px solid #223148;
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 13.5px;
    font-family: inherit;
    outline: none;
  }
  .pack-select:focus { border-color: #6ee7ff; }
  .pack-details {
    font-size: 12.5px;
    color: #9fb0c3;
    width: 100%;
    margin-top: 4px;
  }
  .pack-customization {
    margin-top: 10px;
    padding-top: 10px;
    border-top: 1px solid #1a2638;
    display: flex;
    gap: 12px;
    flex-wrap: wrap;
  }
  .pack-input-group {
    flex: 1;
    min-width: 180px;
  }
  .pack-input-group.full-width {
    flex: 1 1 100%;
  }
  .pack-input-group label {
    display: block;
    font-size: 11.5px;
    color: #7d90a9;
    margin-bottom: 4px;
  }
  .pack-input-group input {
    width: 100%;
    background: #080e19;
    color: #e6edf3;
    border: 1px solid #223148;
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 13px;
    font-family: inherit;
    outline: none;
  }
  .pack-input-group input:focus { border-color: #6ee7ff; }
  .badge-pack {
    display: inline-block;
    background: rgba(99, 102, 241, 0.2);
    border: 1px solid rgba(99, 102, 241, 0.45);
    color: #c7d2fe;
    border-radius: 6px;
    padding: 4px 10px;
    font-size: 12.5px;
    font-weight: 600;
    margin-bottom: 12px;
  }
  .prov-box {
    margin: 8px 0 14px;
    padding: 10px 12px;
    background: rgba(8, 14, 25, 0.85);
    border: 1px solid #223148;
    border-radius: 8px;
    font-size: 12px;
    color: #8fa0b5;
    line-height: 1.6;
    word-break: break-word;
  }
  .pack-chip {
    display: inline-block;
    margin-left: 6px;
    background: rgba(34, 211, 238, 0.15);
    border: 1px solid rgba(34, 211, 238, 0.35);
    color: #6ee7ff;
    font-size: 11px;
    border-radius: 4px;
    padding: 1px 5px;
  }
  .ai-delta-chip {
    display: inline-block;
    margin-left: 6px;
    background: rgba(168, 85, 247, 0.15);
    border: 1px solid rgba(168, 85, 247, 0.35);
    color: #d8b4fe;
    font-size: 11px;
    border-radius: 4px;
    padding: 1px 5px;
  }
  .eco-chip {
    display: inline-block;
    margin-left: 6px;
    background: rgba(34, 197, 94, 0.15);
    border: 1px solid rgba(34, 197, 94, 0.35);
    color: #4ade80;
    font-size: 11px;
    border-radius: 4px;
    padding: 1px 5px;
  }
  .surface-chip {
    display: inline-block;
    margin-left: 6px;
    background: rgba(245, 158, 11, 0.15);
    border: 1px solid rgba(245, 158, 11, 0.35);
    color: #fbbf24;
    font-size: 11px;
    border-radius: 4px;
    padding: 1px 5px;
  }
  .tab-group {
    display: flex;
    gap: 8px;
    margin-bottom: 12px;
  }
  .tab-btn {
    background: rgba(8, 14, 25, 0.8);
    color: #9fb0c3;
    border: 1px solid #223148;
    border-radius: 6px;
    padding: 6px 14px;
    font-size: 12.5px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s;
  }
  .tab-btn.active {
    background: rgba(110, 231, 255, 0.15);
    border-color: #6ee7ff;
    color: #6ee7ff;
  }
  .surface-cards {
    display: flex;
    gap: 8px;
    margin-top: 10px;
    flex-wrap: wrap;
    width: 100%;
  }
  .surface-card {
    flex: 1;
    min-width: 160px;
    background: #080e19;
    border: 1px solid #223148;
    border-radius: 6px;
    padding: 8px 10px;
    font-size: 11.5px;
  }
  .surface-card-title {
    font-weight: 600;
    color: #e6edf3;
    margin-bottom: 2px;
  }
  .surface-card-kind {
    color: #6ee7ff;
    font-size: 10.5px;
  }
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
  .preview-actions { display: flex; align-items: center; gap: 10px; }
  .preview-btn {
    background: transparent; color: #cbd5e1;
    border: 1px solid #33465f; border-radius: 8px;
    padding: 5px 12px; font-size: 12.5px; font-weight: 600; cursor: pointer;
  }
  .preview-btn:hover { border-color: #6ee7ff; color: #e6edf3; }
  .preview-surface-tabs {
    display: flex;
    gap: 6px;
    padding: 8px 14px;
    background: #0d1527;
    border-bottom: 1px solid #223148;
    overflow-x: auto;
  }
  .surface-tab-btn {
    display: flex;
    align-items: center;
    gap: 6px;
    background: rgba(8, 14, 25, 0.6);
    color: #9fb0c3;
    border: 1px solid #223148;
    border-radius: 6px;
    padding: 4px 10px;
    font-size: 11.5px;
    cursor: pointer;
    white-space: nowrap;
    transition: all 0.15s;
  }
  .surface-tab-btn:hover {
    border-color: #6ee7ff;
    color: #e6edf3;
  }
  .surface-tab-btn.active {
    background: rgba(110, 231, 255, 0.12);
    border-color: #6ee7ff;
    color: #6ee7ff;
    font-weight: 600;
  }
  .surface-dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: #64748b;
  }
  .surface-dot.ready {
    background: #34d399;
    box-shadow: 0 0 6px rgba(52, 211, 153, 0.6);
  }
  .history { margin-top: 26px; }
  .history-title { font-size: 15px; color: #9fb0c3; margin: 0 0 10px; }
  .history-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 8px; }
  .history-item { display: flex; align-items: center; justify-content: space-between; gap: 12px; background: rgba(18,28,48,0.55); border: 1px solid #223148; border-radius: 10px; padding: 10px 14px; }
  .history-item .h-name { font-weight: 650; color: #e6edf3; font-size: 14px; }
  .history-item .h-prompt { color: #9fb0c3; font-size: 12.5px; word-break: break-word; }
  .history-actions { display: flex; gap: 8px; flex-wrap: wrap; flex-shrink: 0; }
  .history-empty { color: #62748c; font-size: 13px; }
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
    <div class="pack-panel">
      <div class="tab-group">
        <button type="button" id="tab-single" class="tab-btn active">Single App</button>
        <button type="button" id="tab-ecosystem" class="tab-btn">Multi-Surface Ecosystem</button>
      </div>
      <div id="single-pack-section">
        <div class="pack-header">
          <label for="pack-select" class="pack-title">Solution Pack</label>
          <span id="pack-banner" class="pack-banner" hidden></span>
        </div>
        <div class="pack-row">
          <select id="pack-select" class="pack-select">
            <option value="auto">Auto-detect from prompt (Recommended)</option>
            <option value="none">AI Model Build (No pack)</option>
          </select>
          <div id="pack-details" class="pack-details" hidden></div>
        </div>
        <div id="pack-customization" class="pack-customization" hidden>
          <div class="pack-input-group">
            <label for="custom-name">Custom App Name (optional)</label>
            <input type="text" id="custom-name" placeholder="e.g. My Custom App">
          </div>
          <div class="pack-input-group">
            <label for="custom-desc">Custom Description (optional)</label>
            <input type="text" id="custom-desc" placeholder="e.g. A fast responsive application">
          </div>
          <div class="pack-input-group full-width">
            <label for="ai-features">AI Feature Modifications (optional)</label>
            <input type="text" id="ai-features" placeholder="e.g. Add newsletter subscribers with email and signup endpoint">
          </div>
        </div>
      </div>
      <div id="ecosystem-pack-section" hidden>
        <div class="pack-header">
          <label for="eco-select" class="pack-title">Ecosystem Pack</label>
          <span id="eco-banner" class="pack-banner" hidden></span>
        </div>
        <div class="pack-row">
          <select id="eco-select" class="pack-select">
            <option value="auto">Auto-detect from prompt (Recommended)</option>
          </select>
          <div id="eco-details" class="pack-details" hidden></div>
        </div>
        <div id="surface-selector-group" class="pack-customization">
          <div class="pack-input-group full-width">
            <label for="surface-select">Target Surface</label>
            <select id="surface-select" class="pack-select">
              <option value="all">All Surfaces (Complete Multi-App Platform)</option>
            </select>
          </div>
          <div id="surface-cards" class="surface-cards"></div>
        </div>
      </div>
    </div>
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
    <div id="r-pack-badge" class="badge-pack" hidden></div>
    <h2 id="r-name">App</h2>
    <p class="desc" id="r-desc"></p>
    <div class="chips" id="r-entities"></div>
    <div id="r-provenance" class="prov-box" hidden></div>
    <div class="meta">
      <div><b id="r-count">0 files</b> generated</div>
      <div>commit <b id="r-commit"></b></div>
    </div>
    <div class="meta">repo:&nbsp;<span class="path" id="r-path"></span></div>
    <div class="preview" id="preview-panel">
      <div class="preview-head">
        <h3>Live application preview</h3>
        <div class="preview-actions">
          <button type="button" id="preview-restart" class="preview-btn" hidden>Restart</button>
          <button type="button" id="preview-stop" class="preview-btn" hidden>Stop</button>
          <a id="preview-open" class="preview-open" target="_blank" rel="noreferrer" hidden>Open in new tab</a>
        </div>
      </div>
      <div id="preview-surface-tabs" class="preview-surface-tabs" hidden></div>
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

  <section id="history" class="history">
    <h3 class="history-title">Recent builds</h3>
    <ul id="history-list" class="history-list"></ul>
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

  var tabSingle = document.getElementById('tab-single');
  var tabEco = document.getElementById('tab-ecosystem');
  var singleSection = document.getElementById('single-pack-section');
  var ecoSection = document.getElementById('ecosystem-pack-section');

  var packSelect = document.getElementById('pack-select');
  var packBanner = document.getElementById('pack-banner');
  var packDetails = document.getElementById('pack-details');
  var packCustomization = document.getElementById('pack-customization');
  var customNameInput = document.getElementById('custom-name');
  var customDescInput = document.getElementById('custom-desc');
  var aiFeaturesInput = document.getElementById('ai-features');

  var ecoSelect = document.getElementById('eco-select');
  var ecoBanner = document.getElementById('eco-banner');
  var ecoDetails = document.getElementById('eco-details');
  var surfaceSelect = document.getElementById('surface-select');
  var surfaceCards = document.getElementById('surface-cards');

  var activeMode = 'single';
  var availablePacks = [];
  var recommendedPackId = null;
  var availableEcosystems = [];
  var recommendedEcoId = null;
  var recommendDebounceTimer = null;

  tabSingle.addEventListener('click', function () {
    activeMode = 'single';
    tabSingle.classList.add('active');
    tabEco.classList.remove('active');
    singleSection.hidden = false;
    ecoSection.hidden = true;
  });

  tabEco.addEventListener('click', function () {
    activeMode = 'ecosystem';
    tabEco.classList.add('active');
    tabSingle.classList.remove('active');
    singleSection.hidden = true;
    ecoSection.hidden = false;
    updateEcoUi();
  });

  function loadSolutionPacks() {
    fetch('/api/solution-packs')
      .then(function (res) { return res.ok ? res.json() : { packs: [] }; })
      .then(function (data) {
        availablePacks = (data && data.packs) || [];
        availablePacks.forEach(function (p) {
          var opt = document.createElement('option');
          opt.value = p.pack_id;
          opt.textContent = (p.display_name || p.pack_id) + ' (' + p.pack_id + '@' + (p.version || '1.0.0') + ')';
          packSelect.appendChild(opt);
        });
        updatePackUi();
      })
      .catch(function () {});
  }

  function loadEcosystemPacks() {
    fetch('/api/ecosystem-packs')
      .then(function (res) { return res.ok ? res.json() : { ecosystems: [] }; })
      .then(function (data) {
        availableEcosystems = (data && data.ecosystems) || [];
        availableEcosystems.forEach(function (e) {
          var opt = document.createElement('option');
          opt.value = e.ecosystem_id;
          opt.textContent = (e.display_name || e.ecosystem_id) + ' (' + (e.surface_count || (e.surfaces && e.surfaces.length) || 0) + ' surfaces)';
          ecoSelect.appendChild(opt);
        });
        updateEcoUi();
      })
      .catch(function () {});
  }

  function getSelectedOrRecommendedPack() {
    var val = packSelect.value;
    if (val === 'none') { return null; }
    var targetId = val === 'auto' ? recommendedPackId : val;
    if (!targetId) { return null; }
    for (var i = 0; i < availablePacks.length; i++) {
      if (availablePacks[i].pack_id === targetId) { return availablePacks[i]; }
    }
    return null;
  }

  function getSelectedOrRecommendedEco() {
    var val = ecoSelect.value;
    var targetId = val === 'auto' ? recommendedEcoId : val;
    if (!targetId && availableEcosystems.length > 0) {
      targetId = availableEcosystems[0].ecosystem_id;
    }
    for (var i = 0; i < availableEcosystems.length; i++) {
      if (availableEcosystems[i].ecosystem_id === targetId) { return availableEcosystems[i]; }
    }
    return null;
  }

  function updatePackUi() {
    var pack = getSelectedOrRecommendedPack();
    if (pack) {
      packDetails.hidden = false;
      packDetails.textContent = (pack.description || '') + ' - Targets: ' + (pack.targets || pack.verify_targets || []).join(', ');
      packCustomization.hidden = false;
    } else {
      packDetails.hidden = true;
      packCustomization.hidden = true;
    }
  }

  function updateEcoUi() {
    var eco = getSelectedOrRecommendedEco();
    surfaceSelect.innerHTML = '';
    var optAll = document.createElement('option');
    optAll.value = 'all';
    optAll.textContent = 'All Surfaces (Complete Multi-App Platform)';
    surfaceSelect.appendChild(optAll);

    surfaceCards.innerHTML = '';
    if (eco) {
      ecoDetails.hidden = false;
      ecoDetails.textContent = (eco.description || '') + ' [Domain: ' + eco.domain + ']';
      (eco.surfaces || []).forEach(function (s) {
        var opt = document.createElement('option');
        opt.value = s.slug;
        opt.textContent = s.app_name + ' [' + s.surface_kind + ']';
        surfaceSelect.appendChild(opt);

        var card = document.createElement('div');
        card.className = 'surface-card';
        var cardTitle = document.createElement('div');
        cardTitle.className = 'surface-card-title';
        cardTitle.textContent = s.app_name;
        var cardKind = document.createElement('div');
        cardKind.className = 'surface-card-kind';
        cardKind.textContent = s.surface_kind + ' (' + (s.verify_targets || []).join(', ') + ')';
        card.appendChild(cardTitle);
        card.appendChild(cardKind);
        surfaceCards.appendChild(card);
      });
    } else {
      ecoDetails.hidden = true;
    }
  }

  function checkPackRecommendation(prompt) {
    if (!prompt) {
      recommendedPackId = null;
      packBanner.hidden = true;
      updatePackUi();
      return;
    }
    fetch('/api/solution-packs/recommend', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ prompt: prompt })
    })
      .then(function (res) { return res.ok ? res.json() : null; })
      .then(function (data) {
        if (data && data.recommendation && data.recommendation.status === 'selected' && data.recommendation.selection) {
          recommendedPackId = data.recommendation.selection.pack_id;
          packBanner.textContent = 'Solution Pack: ' + recommendedPackId;
          packBanner.hidden = false;
        } else {
          recommendedPackId = null;
          packBanner.hidden = true;
        }
        updatePackUi();
      })
      .catch(function () {});
  }

  function checkEcoRecommendation(prompt) {
    if (!prompt) {
      recommendedEcoId = null;
      ecoBanner.hidden = true;
      updateEcoUi();
      return;
    }
    fetch('/api/ecosystem-packs/recommend', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ prompt: prompt })
    })
      .then(function (res) { return res.ok ? res.json() : null; })
      .then(function (data) {
        if (data && data.recommendation && data.recommendation.status === 'selected' && data.recommendation.ecosystem) {
          recommendedEcoId = data.recommendation.ecosystem.ecosystem_id;
          ecoBanner.textContent = 'Ecosystem: ' + recommendedEcoId;
          ecoBanner.hidden = false;
        } else {
          recommendedEcoId = null;
          ecoBanner.hidden = true;
        }
        updateEcoUi();
      })
      .catch(function () {});
  }

  packSelect.addEventListener('change', function () {
    if (packSelect.value === 'none') {
      packBanner.hidden = true;
    } else if (packSelect.value === 'auto' && recommendedPackId) {
      packBanner.hidden = false;
    }
    updatePackUi();
  });

  ecoSelect.addEventListener('change', function () {
    if (ecoSelect.value === 'auto' && recommendedEcoId) {
      ecoBanner.hidden = false;
    } else {
      ecoBanner.hidden = true;
    }
    updateEcoUi();
  });

  promptEl.addEventListener('input', function () {
    clearTimeout(recommendDebounceTimer);
    recommendDebounceTimer = setTimeout(function () {
      var text = promptEl.value.trim();
      if (packSelect.value === 'auto') {
        checkPackRecommendation(text);
      }
      if (ecoSelect.value === 'auto') {
        checkEcoRecommendation(text);
      }
    }, 350);
  });

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

  var currentPreviewUrl = null;
  var previewPollTimer = null;

  function stopPreviewPolling() {
    if (previewPollTimer !== null) { clearInterval(previewPollTimer); previewPollTimer = null; }
  }

  function startPreviewPolling() {
    if (previewPollTimer !== null) { return; }
    previewPollTimer = setInterval(function () {
      fetch('/api/preview')
        .then(function (res) { return res.ok ? res.json() : null; })
        .then(function (data) { if (data) { renderPreview(data); } })
        .catch(function () {});
    }, 5000);
  }

  function switchSurface(slug) {
    var previewStatus = document.getElementById('preview-status');
    previewStatus.textContent = 'Switching to surface ' + slug + '...';
    fetch('/api/preview/switch', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ surface_slug: slug })
    })
      .then(function (res) { return res.json(); })
      .then(function (data) { renderPreview(data); })
      .catch(function (err) { previewStatus.textContent = 'Switch failed: ' + err.message; });
  }

  function renderPreview(preview) {
    var frame = document.getElementById('preview-frame');
    var open = document.getElementById('preview-open');
    var previewStatus = document.getElementById('preview-status');
    var stopBtn = document.getElementById('preview-stop');
    var restartBtn = document.getElementById('preview-restart');
    var surfaceTabs = document.getElementById('preview-surface-tabs');
    var state = (preview && preview.status) || null;
    var url = state === 'ready' ? localPreviewUrl(preview.web_url) : null;
    stopBtn.hidden = state !== 'ready';
    restartBtn.hidden = !(state === 'ready' || state === 'stopped' || state === 'error');

    if (surfaceTabs) {
      if (preview && preview.is_ecosystem && preview.surfaces && preview.surfaces.length > 0) {
        surfaceTabs.innerHTML = '';
        surfaceTabs.hidden = false;
        preview.surfaces.forEach(function (s) {
          var tabBtn = document.createElement('button');
          tabBtn.type = 'button';
          tabBtn.className = 'surface-tab-btn' + (s.is_active ? ' active' : '');
          var dot = document.createElement('span');
          dot.className = 'surface-dot' + (s.status === 'ready' ? ' ready' : '');
          tabBtn.appendChild(dot);
          var label = document.createElement('span');
          label.textContent = s.app_name + ' [' + s.surface_kind + ']';
          tabBtn.appendChild(label);
          tabBtn.addEventListener('click', function () {
            switchSurface(s.slug);
          });
          surfaceTabs.appendChild(tabBtn);
        });
      } else {
        surfaceTabs.hidden = true;
      }
    }

    if (url) {
      previewStatus.textContent = preview.message || 'The generated application is running locally.';
      if (currentPreviewUrl !== url) {
        frame.src = url;
        currentPreviewUrl = url;
      }
      frame.hidden = false;
      open.href = url;
      open.hidden = false;
      startPreviewPolling();
      return;
    }
    stopPreviewPolling();
    currentPreviewUrl = null;
    frame.hidden = true;
    frame.removeAttribute('src');
    open.hidden = true;
    open.removeAttribute('href');
    previewStatus.textContent = (preview && preview.message) || 'No browser preview is available for this build.';
  }

  function control(path, pending) {
    var previewStatus = document.getElementById('preview-status');
    var stopBtn = document.getElementById('preview-stop');
    var restartBtn = document.getElementById('preview-restart');
    stopBtn.disabled = true;
    restartBtn.disabled = true;
    previewStatus.textContent = pending;
    fetch(path, { method: 'POST', headers: { 'Content-Type': 'application/json' } })
      .then(function (res) { return res.json(); })
      .then(function (data) { renderPreview(data); })
      .catch(function (err) {
        previewStatus.textContent = 'Preview control failed: ' + err.message;
      })
      .then(function () {
        stopBtn.disabled = false;
        restartBtn.disabled = false;
      });
  }

  document.getElementById('preview-stop').addEventListener('click', function () {
    control('/api/preview/stop', 'Stopping preview...');
  });
  document.getElementById('preview-restart').addEventListener('click', function () {
    control('/api/preview/restart', 'Restarting preview...');
  });

  function previewBuild(build, surface_slug) {
    renderResult({
      name: build.name,
      description: build.prompt,
      entities: build.entities || [],
      file_count: build.file_count,
      target_dir: build.target_dir,
      commit_sha: build.commit_sha,
      pack_id: build.pack_id,
      pack_version: build.pack_version,
      ecosystem_id: build.ecosystem_id,
      ecosystem_version: build.ecosystem_version,
      surface_slug: surface_slug || build.surface_slug,
      surface_kind: build.surface_kind,
      is_ecosystem: build.is_ecosystem,
      surface_count: build.surface_count,
      surfaces: build.surfaces || [],
      base_ir_sha256: build.base_ir_sha256,
      derived_ir_sha256: build.derived_ir_sha256,
      applied_configuration_change_ids: build.applied_configuration_change_ids || [],
      applied_ai_delta_change_ids: build.applied_ai_delta_change_ids || [],
      files: []
    });
    var previewStatus = document.getElementById('preview-status');
    previewStatus.textContent = 'Starting preview...';
    var payload = { id: build.id };
    if (surface_slug) {
      payload.surface_slug = surface_slug;
    }
    fetch('/api/history/preview', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    }).then(function (res) { return res.json(); })
      .then(function (data) { renderPreview(data); })
      .catch(function (err) { previewStatus.textContent = 'Preview failed: ' + err.message; });
  }

  function flashButton(btn, label) {
    if (!btn.getAttribute('data-label')) { btn.setAttribute('data-label', btn.textContent); }
    btn.textContent = label;
    setTimeout(function () { btn.textContent = btn.getAttribute('data-label'); }, 1500);
  }

  function actionButton(label, handler) {
    var btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'preview-btn';
    btn.textContent = label;
    btn.addEventListener('click', function () { handler(btn); });
    return btn;
  }

  function fallbackCopy(path, btn) {
    try {
      var ta = document.createElement('textarea');
      ta.value = path;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand('copy');
      document.body.removeChild(ta);
      flashButton(btn, 'Copied');
    } catch (_) {
      flashButton(btn, 'Copy failed');
    }
  }

  function copyPath(path, btn) {
    if (!path) { return; }
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(path)
        .then(function () { flashButton(btn, 'Copied'); })
        .catch(function () { fallbackCopy(path, btn); });
    } else {
      fallbackCopy(path, btn);
    }
  }

  function openBuild(id, btn) {
    btn.disabled = true;
    fetch('/api/history/open', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id: id })
    }).then(function (res) { return res.ok ? res.json() : { status: 'error' }; })
      .then(function (data) { flashButton(btn, data && data.status === 'opened' ? 'Opened' : 'Unavailable'); })
      .catch(function () { flashButton(btn, 'Unavailable'); })
      .then(function () { btn.disabled = false; });
  }

  function deleteBuild(id, btn) {
    btn.disabled = true;
    fetch('/api/history/delete', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id: id })
    }).then(function (res) { return res.ok ? res.json() : null; })
      .then(function (data) {
        if (data && data.builds) { renderHistory(data.builds); } else { loadHistory(); }
      })
      .catch(function () { btn.disabled = false; });
  }

  function renderHistory(builds) {
    var list = document.getElementById('history-list');
    list.innerHTML = '';
    if (!builds || !builds.length) {
      var empty = document.createElement('li');
      empty.className = 'history-empty';
      empty.textContent = 'No builds yet in this session.';
      list.appendChild(empty);
      return;
    }
    builds.forEach(function (b) {
      var li = document.createElement('li');
      li.className = 'history-item';
      var meta = document.createElement('div');
      var name = document.createElement('div');
      name.className = 'h-name';
      name.textContent = b.name || 'App';
      if (b.is_ecosystem) {
        var ecoBadge = document.createElement('span');
        ecoBadge.className = 'eco-chip';
        ecoBadge.textContent = 'Ecosystem (' + (b.surface_count || 3) + ' apps)';
        name.appendChild(ecoBadge);
      } else if (b.ecosystem_id) {
        var ecoChip = document.createElement('span');
        ecoChip.className = 'eco-chip';
        ecoChip.textContent = b.ecosystem_id;
        name.appendChild(ecoChip);
        if (b.surface_slug) {
          var surfChip = document.createElement('span');
          surfChip.className = 'surface-chip';
          surfChip.textContent = b.surface_slug;
          name.appendChild(surfChip);
        }
      } else if (b.pack_id) {
        var chip = document.createElement('span');
        chip.className = 'pack-chip';
        chip.textContent = b.pack_id;
        name.appendChild(chip);
      }
      if (b.applied_ai_delta_change_ids && b.applied_ai_delta_change_ids.length) {
        var deltaChip = document.createElement('span');
        deltaChip.className = 'ai-delta-chip';
        deltaChip.textContent = 'AI delta (' + b.applied_ai_delta_change_ids.length + ')';
        name.appendChild(deltaChip);
      }
      var prompt = document.createElement('div');
      prompt.className = 'h-prompt';
      prompt.textContent = (b.prompt || '') + '  -  ' + (b.file_count || 0) + ' files';
      meta.appendChild(name);
      meta.appendChild(prompt);
      var actions = document.createElement('div');
      actions.className = 'history-actions';
      if (b.is_ecosystem && b.surfaces && b.surfaces.length) {
        b.surfaces.forEach(function (surf) {
          actions.appendChild(actionButton('Preview: ' + (surf.app_name || surf.slug), function () { previewBuild(b, surf.slug); }));
        });
      } else {
        actions.appendChild(actionButton('Preview', function () { previewBuild(b); }));
      }
      actions.appendChild(actionButton('Copy path', function (btn) { copyPath(b.target_dir, btn); }));
      actions.appendChild(actionButton('Open folder', function (btn) { openBuild(b.id, btn); }));
      actions.appendChild(actionButton('Remove', function (btn) { deleteBuild(b.id, btn); }));
      li.appendChild(meta);
      li.appendChild(actions);
      list.appendChild(li);
    });
  }

  function loadHistory() {
    fetch('/api/history')
      .then(function (res) { return res.ok ? res.json() : { builds: [] }; })
      .then(function (data) { renderHistory((data && data.builds) || []); })
      .catch(function () {});
  }

  document.getElementById('examples').addEventListener('click', function (e) {
    if (e.target && e.target.classList.contains('ex')) {
      promptEl.value = 'Build ' + e.target.textContent.replace(/^A /, 'a ');
      promptEl.focus();
      var text = promptEl.value.trim();
      if (packSelect.value === 'auto') {
        checkPackRecommendation(text);
      }
      if (ecoSelect.value === 'auto') {
        checkEcoRecommendation(text);
      }
    }
  });

  function renderResult(data) {
    var packBadge = document.getElementById('r-pack-badge');
    var provBox = document.getElementById('r-provenance');
    if (data.is_ecosystem) {
      packBadge.textContent = 'Verified Ecosystem: ' + (data.name || data.ecosystem_id) + ' (' + (data.surface_count || 3) + ' surface apps)';
      packBadge.hidden = false;
      var provText = 'Ecosystem: ' + data.ecosystem_id + '@' + (data.ecosystem_version || '1.0.0') +
                     ' | Domain: ' + (data.domain || 'n/a') +
                     ' | Base Pack: ' + (data.base_pack_id || 'n/a');
      if (data.surfaces && data.surfaces.length) {
        provText += ' | Surfaces: ' + data.surfaces.map(function (s) { return s.app_name + ' [' + s.surface_kind + ']'; }).join(', ');
      }
      provBox.textContent = provText;
      provBox.hidden = false;
    } else if (data.ecosystem_id) {
      packBadge.textContent = 'Verified Ecosystem Surface: ' + (data.name || 'App') + ' [' + (data.surface_kind || 'surface') + ']';
      packBadge.hidden = false;
      var provText = 'Ecosystem: ' + data.ecosystem_id + '@' + (data.ecosystem_version || '1.0.0') +
                     ' | Surface: ' + (data.surface_slug || 'n/a') +
                     ' | Base Pack: ' + (data.base_pack_id || 'n/a') +
                     ' | IR: ' + (data.ir_sha256 ? data.ir_sha256.slice(0, 12) : 'n/a');
      provBox.textContent = provText;
      provBox.hidden = false;
    } else if (data.pack_id) {
      packBadge.textContent = 'Verified Solution Pack: ' + data.pack_id + (data.pack_version ? '@' + data.pack_version : '');
      packBadge.hidden = false;
      var provText = 'Provenance: Base IR: ' + (data.base_ir_sha256 ? data.base_ir_sha256.slice(0, 12) : 'n/a') +
                     ' | Derived IR: ' + (data.derived_ir_sha256 ? data.derived_ir_sha256.slice(0, 12) : 'n/a');
      if (data.applied_configuration_change_ids && data.applied_configuration_change_ids.length) {
        provText += ' | Applied Config: ' + data.applied_configuration_change_ids.join(', ');
      }
      if (data.applied_ai_delta_change_ids && data.applied_ai_delta_change_ids.length) {
        provText += ' | Applied AI Deltas: ' + data.applied_ai_delta_change_ids.join(', ');
      }
      provBox.textContent = provText;
      provBox.hidden = false;
    } else {
      packBadge.hidden = true;
      provBox.hidden = true;
    }

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

    var payload = { prompt: prompt };

    if (activeMode === 'ecosystem') {
      var eco = getSelectedOrRecommendedEco();
      if (eco) {
        payload.ecosystem_id = eco.ecosystem_id;
        payload.ecosystem_version = eco.version;
        var surfVal = surfaceSelect.value;
        if (surfVal && surfVal !== 'all') {
          payload.surface_slug = surfVal;
          statusEl.textContent = 'Building ecosystem surface (' + surfVal + ') from ' + eco.ecosystem_id + '...';
        } else {
          statusEl.textContent = 'Materializing complete multi-surface platform (' + (eco.surface_count || 3) + ' applications)...';
        }
      } else {
        statusEl.textContent = 'Building your app - this runs a local model and can take a moment...';
      }
    } else {
      var selectedPack = getSelectedOrRecommendedPack();
      if (selectedPack) {
        payload.pack_id = selectedPack.pack_id;
        payload.pack_version = selectedPack.version;
        var cName = (customNameInput.value || '').trim();
        if (cName) { payload.custom_name = cName; }
        var cDesc = (customDescInput.value || '').trim();
        if (cDesc) { payload.custom_description = cDesc; }
        var aiFeat = (aiFeaturesInput.value || '').trim();
        if (aiFeat) {
          payload.ai_features = [aiFeat];
          payload.ai_delta_prompt = aiFeat;
          statusEl.textContent = 'Synthesizing feature additions with AI and compiling with ' + selectedPack.pack_id + '...';
        } else {
          statusEl.textContent = 'Building app from verified Solution Pack (' + selectedPack.pack_id + ')...';
        }
      } else {
        statusEl.textContent = 'Building your app - this runs a local model and can take a moment...';
      }
    }

    fetch('/api/build', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    }).then(function (res) {
      return res.json().then(function (data) { return { ok: res.ok, status: res.status, data: data }; });
    }).then(function (out) {
      if (!out.ok) { throw new Error((out.data && out.data.error) || ('HTTP ' + out.status)); }
      renderResult(out.data);
      statusEl.hidden = true;
      loadHistory();
    }).catch(function (err) {
      statusEl.className = 'status error';
      statusEl.textContent = 'Build failed: ' + err.message;
    }).then(function () {
      btn.disabled = false;
    });
  });

  loadSolutionPacks();
  loadEcosystemPacks();
  loadHistory();
})();
</script>
</body>
</html>
"""
