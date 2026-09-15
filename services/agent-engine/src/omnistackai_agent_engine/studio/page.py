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
  .preview-auth-info {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 6px 14px;
    background: #080e1a;
    border-bottom: 1px solid #1e293b;
    font-size: 11px;
    color: #94a3b8;
  }
  .preview-events-info {
    display: flex;
    flex-direction: column;
    gap: 8px;
    padding: 8px 14px;
    background: #060a14;
    border-bottom: 1px solid #1e293b;
    font-size: 11.5px;
    color: #94a3b8;
  }
  .preview-telemetry-info {
    display: flex;
    flex-direction: column;
    gap: 8px;
    padding: 8px 14px;
    background: #060d18;
    border-bottom: 1px solid #1e293b;
    font-size: 11.5px;
    color: #94a3b8;
  }
  .telemetry-header-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    flex-wrap: wrap;
  }
  .telemetry-meta-group {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
  }
  .telemetry-badge {
    background: rgba(16, 185, 129, 0.15);
    border: 1px solid #10b981;
    color: #6ee7b7;
    border-radius: 4px;
    padding: 2px 7px;
    font-size: 10.5px;
    font-weight: 600;
    letter-spacing: 0.03em;
  }
  .telemetry-count-badge {
    background: rgba(15, 23, 42, 0.6);
    border: 1px solid #1e293b;
    color: #64748b;
    border-radius: 4px;
    padding: 2px 6px;
    font-size: 10px;
  }
  .telemetry-action-btn {
    background: rgba(16, 185, 129, 0.12);
    border: 1px solid #10b981;
    color: #6ee7b7;
    border-radius: 5px;
    padding: 3px 10px;
    font-size: 10.5px;
    cursor: pointer;
    transition: background 0.15s;
  }
  .telemetry-action-btn:hover { background: rgba(16, 185, 129, 0.25); }
  .telemetry-surfaces-list {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin-top: 2px;
  }
  .telemetry-surface-chip {
    background: rgba(15, 23, 42, 0.8);
    border: 1px solid #1e293b;
    border-radius: 4px;
    padding: 2px 8px;
    font-size: 10px;
    color: #94a3b8;
  }
  .preview-deployment-info {
    margin-top: 10px;
    padding: 10px 12px;
    background: rgba(15, 23, 42, 0.6);
    border: 1px solid rgba(59, 130, 246, 0.25);
    border-radius: 8px;
    font-size: 11px;
    color: #cbd5e1;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
  .deployment-header-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    flex-wrap: wrap;
  }
  .deployment-meta-group {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
  }
  .deployment-badge {
    background: rgba(59, 130, 246, 0.2);
    color: #60a5fa;
    padding: 2px 8px;
    border-radius: 999px;
    font-size: 10px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }
  .deployment-count-badge {
    background: #1e293b;
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 10px;
    color: #94a3b8;
  }
  .deployment-action-btn {
    background: rgba(59, 130, 246, 0.15);
    border: 1px solid rgba(59, 130, 246, 0.35);
    border-radius: 4px;
    color: #93c5fd;
    font-size: 10px;
    padding: 3px 8px;
    cursor: pointer;
    transition: background 0.15s;
  }
  .deployment-action-btn:hover { background: rgba(59, 130, 246, 0.25); }
  .deployment-routes-list {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin-top: 2px;
  }
  .deployment-route-chip {
    background: rgba(15, 23, 42, 0.8);
    border: 1px solid #1e293b;
    border-radius: 4px;
    padding: 2px 8px;
    font-size: 10px;
    color: #94a3b8;
    font-family: monospace;
  }
  .preview-sync-info {
    margin-top: 10px;
    padding: 10px 12px;
    background: rgba(15, 23, 42, 0.6);
    border: 1px solid rgba(16, 185, 129, 0.25);
    border-radius: 8px;
    font-size: 11px;
    color: #cbd5e1;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
  .sync-header-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    flex-wrap: wrap;
  }
  .sync-meta-group {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
  }
  .sync-badge {
    background: rgba(16, 185, 129, 0.2);
    color: #34d399;
    padding: 2px 8px;
    border-radius: 999px;
    font-size: 10px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }
  .sync-count-badge {
    background: #1e293b;
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 10px;
    color: #94a3b8;
  }
  .sync-action-btn {
    background: rgba(16, 185, 129, 0.15);
    border: 1px solid rgba(16, 185, 129, 0.35);
    border-radius: 4px;
    color: #a7f3d0;
    font-size: 10px;
    padding: 3px 8px;
    cursor: pointer;
    transition: background 0.15s;
  }
  .sync-action-btn:hover { background: rgba(16, 185, 129, 0.25); }
  .sync-entities-list {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin-top: 2px;
  }
  .sync-entity-chip {
    background: rgba(15, 23, 42, 0.8);
    border: 1px solid #1e293b;
    border-radius: 4px;
    padding: 2px 8px;
    font-size: 10px;
    color: #94a3b8;
    font-family: monospace;
  }
  .preview-cicd-info {
    margin-top: 10px;
    padding: 10px 12px;
    background: rgba(15, 23, 42, 0.6);
    border: 1px solid rgba(59, 130, 246, 0.25);
    border-radius: 8px;
    font-size: 11px;
    color: #cbd5e1;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
  .cicd-header-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    flex-wrap: wrap;
  }
  .cicd-meta-group {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
  }
  .cicd-badge {
    background: rgba(59, 130, 246, 0.2);
    color: #60a5fa;
    padding: 2px 8px;
    border-radius: 999px;
    font-size: 10px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }
  .cicd-count-badge {
    background: #1e293b;
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 10px;
    color: #94a3b8;
  }
  .cicd-action-btn {
    background: rgba(59, 130, 246, 0.15);
    border: 1px solid rgba(59, 130, 246, 0.35);
    border-radius: 4px;
    color: #93c5fd;
    font-size: 10px;
    padding: 3px 8px;
    cursor: pointer;
    transition: background 0.15s;
  }
  .cicd-action-btn:hover { background: rgba(59, 130, 246, 0.25); }
  .cicd-jobs-list {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin-top: 2px;
  }
  .cicd-job-chip {
    background: rgba(15, 23, 42, 0.8);
    border: 1px solid #1e293b;
    border-radius: 4px;
    padding: 2px 8px;
    font-size: 10px;
    color: #94a3b8;
    font-family: monospace;
  }
  .preview-verification-info {
    margin-top: 10px;
    padding: 10px 12px;
    background: rgba(15, 23, 42, 0.6);
    border: 1px solid rgba(16, 185, 129, 0.25);
    border-radius: 8px;
    font-size: 11px;
    color: #cbd5e1;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
  .verification-header-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    flex-wrap: wrap;
  }
  .verification-meta-group {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
  }
  .verification-badge {
    background: rgba(16, 185, 129, 0.2);
    color: #34d399;
    padding: 2px 8px;
    border-radius: 999px;
    font-size: 10px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }
  .verification-count-badge {
    background: #1e293b;
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 10px;
    color: #94a3b8;
  }
  .verification-action-btn {
    background: rgba(16, 185, 129, 0.15);
    border: 1px solid rgba(16, 185, 129, 0.35);
    border-radius: 4px;
    color: #6ee7b7;
    font-size: 10px;
    padding: 3px 8px;
    cursor: pointer;
    transition: background 0.15s;
  }
  .verification-action-btn:hover { background: rgba(16, 185, 129, 0.25); }
  .preview-recovery-info {
    margin-top: 10px;
    padding: 10px 12px;
    background: rgba(15, 23, 42, 0.6);
    border: 1px solid rgba(245, 158, 11, 0.25);
    border-radius: 8px;
    font-size: 11px;
    color: #cbd5e1;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
  .recovery-header-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    flex-wrap: wrap;
  }
  .recovery-meta-group {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
  }
  .recovery-badge {
    background: rgba(245, 158, 11, 0.2);
    color: #fbbf24;
    padding: 2px 8px;
    border-radius: 999px;
    font-size: 10px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }
  .recovery-count-badge {
    background: #1e293b;
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 10px;
    color: #94a3b8;
  }
  .recovery-action-btn {
    background: rgba(245, 158, 11, 0.15);
    border: 1px solid rgba(245, 158, 11, 0.35);
    border-radius: 4px;
    color: #fcd34d;
    font-size: 10px;
    padding: 3px 8px;
    cursor: pointer;
    transition: background 0.15s;
  }
  .recovery-action-btn:hover { background: rgba(245, 158, 11, 0.25); }
  .preview-capacity-info {
    margin-top: 10px;
    padding: 10px 12px;
    background: rgba(15, 23, 42, 0.6);
    border: 1px solid rgba(14, 165, 233, 0.3);
    border-radius: 8px;
    font-size: 11px;
    color: #cbd5e1;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
  .capacity-header-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    flex-wrap: wrap;
  }
  .capacity-meta-group {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
  }
  .capacity-badge {
    background: rgba(14, 165, 233, 0.2);
    color: #38bdf8;
    padding: 2px 8px;
    border-radius: 999px;
    font-size: 10px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }
  .capacity-count-badge {
    background: #1e293b;
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 10px;
    color: #94a3b8;
  }
  .capacity-action-btn {
    background: rgba(14, 165, 233, 0.15);
    border: 1px solid rgba(14, 165, 233, 0.35);
    border-radius: 4px;
    color: #7dd3fc;
    font-size: 10px;
    padding: 3px 8px;
    cursor: pointer;
    transition: background 0.15s;
  }
  .capacity-action-btn:hover { background: rgba(14, 165, 233, 0.25); }
  .preview-alerting-info {
    margin-top: 10px;
    padding: 10px 12px;
    background: rgba(15, 23, 42, 0.6);
    border: 1px solid rgba(244, 63, 94, 0.3);
    border-radius: 8px;
    font-size: 11px;
    color: #cbd5e1;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
  .alerting-header-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    flex-wrap: wrap;
  }
  .alerting-meta-group {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
  }
  .alerting-badge {
    background: rgba(244, 63, 94, 0.2);
    color: #fb7185;
    padding: 2px 8px;
    border-radius: 999px;
    font-size: 10px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }
  .alerting-count-badge {
    background: #1e293b;
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 10px;
    color: #94a3b8;
  }
  .alerting-action-btn {
    background: rgba(244, 63, 94, 0.15);
    border: 1px solid rgba(244, 63, 94, 0.35);
    border-radius: 4px;
    color: #fda4af;
    font-size: 10px;
    padding: 3px 8px;
    cursor: pointer;
    transition: background 0.15s;
  }
  .alerting-action-btn:hover { background: rgba(244, 63, 94, 0.25); }
  .preview-sla-info {
    margin-top: 10px;
    padding: 10px 12px;
    background: rgba(15, 23, 42, 0.6);
    border: 1px solid rgba(16, 185, 129, 0.3);
    border-radius: 8px;
    font-size: 11px;
    color: #cbd5e1;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
  .sla-header-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    flex-wrap: wrap;
  }
  .sla-meta-group {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
  }
  .sla-badge {
    background: rgba(16, 185, 129, 0.2);
    color: #34d399;
    padding: 2px 8px;
    border-radius: 999px;
    font-size: 10px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }
  .sla-count-badge {
    background: #1e293b;
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 10px;
    color: #94a3b8;
  }
  .sla-action-btn {
    background: rgba(16, 185, 129, 0.15);
    border: 1px solid rgba(16, 185, 129, 0.35);
    border-radius: 4px;
    color: #6ee7b7;
    font-size: 10px;
    padding: 3px 8px;
    cursor: pointer;
    transition: background 0.15s;
  }
  .sla-action-btn:hover { background: rgba(16, 185, 129, 0.25); }
  .preview-governance-info {
    margin-top: 10px;
    padding: 10px 12px;
    background: rgba(15, 23, 42, 0.6);
    border: 1px solid rgba(99, 102, 241, 0.3);
    border-radius: 8px;
    font-size: 11px;
    color: #cbd5e1;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
  .governance-header-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    flex-wrap: wrap;
  }
  .governance-meta-group {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
  }
  .governance-badge {
    background: rgba(99, 102, 241, 0.2);
    color: #a5b4fc;
    padding: 2px 8px;
    border-radius: 999px;
    font-size: 10px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }
  .governance-count-badge {
    background: #1e293b;
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 10px;
    color: #94a3b8;
  }
  .governance-action-btn {
    background: rgba(99, 102, 241, 0.15);
    border: 1px solid rgba(99, 102, 241, 0.35);
    border-radius: 4px;
    color: #c7d2fe;
    font-size: 10px;
    padding: 3px 8px;
    cursor: pointer;
    transition: background 0.15s;
  }
  .governance-action-btn:hover { background: rgba(99, 102, 241, 0.25); }
  .preview-docs-info {
    margin-top: 10px;
    padding: 10px 12px;
    background: rgba(15, 23, 42, 0.6);
    border: 1px solid rgba(14, 165, 233, 0.3);
    border-radius: 8px;
    font-size: 11px;
    color: #cbd5e1;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
  .docs-header-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    flex-wrap: wrap;
  }
  .docs-meta-group {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
  }
  .docs-badge {
    background: rgba(14, 165, 233, 0.2);
    color: #38bdf8;
    padding: 2px 8px;
    border-radius: 999px;
    font-size: 10px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }
  .docs-count-badge {
    background: #1e293b;
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 10px;
    color: #94a3b8;
  }
  .docs-action-btn {
    background: rgba(14, 165, 233, 0.15);
    border: 1px solid rgba(14, 165, 233, 0.35);
    border-radius: 4px;
    color: #7dd3fc;
    font-size: 10px;
    padding: 3px 8px;
    cursor: pointer;
    transition: background 0.15s;
  }
  .docs-action-btn:hover { background: rgba(14, 165, 233, 0.25); }
  .events-header-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    flex-wrap: wrap;
  }
  .events-meta-group {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
  }
  .events-badge {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 2px 7px;
    background: rgba(168, 85, 247, 0.12);
    border: 1px solid #a855f7;
    border-radius: 4px;
    color: #c084fc;
    font-weight: 600;
  }
  .events-count-badge {
    display: inline-flex;
    align-items: center;
    padding: 2px 6px;
    background: rgba(34, 211, 238, 0.1);
    border: 1px solid #22d3ee;
    border-radius: 4px;
    color: #22d3ee;
  }
  .events-action-btn {
    background: transparent;
    border: 1px solid #6366f1;
    color: #a5b4fc;
    border-radius: 4px;
    padding: 3px 8px;
    font-size: 11px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.15s;
  }
  .events-action-btn:hover {
    background: rgba(99, 102, 241, 0.2);
    color: #ffffff;
  }
  .events-sim-panel {
    display: flex;
    gap: 8px;
    align-items: center;
    flex-wrap: wrap;
    padding: 8px 10px;
    background: rgba(15, 23, 42, 0.85);
    border: 1px solid #334155;
    border-radius: 6px;
    margin-top: 4px;
  }
  .events-sim-input {
    background: #0b1220;
    border: 1px solid #334155;
    color: #e2e8f0;
    border-radius: 4px;
    padding: 4px 8px;
    font-size: 11px;
  }
  .events-log-container {
    max-height: 140px;
    overflow-y: auto;
    border: 1px solid #1e293b;
    border-radius: 4px;
    background: #030712;
    padding: 4px 6px;
    font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
    font-size: 10.5px;
  }
  .events-log-entry {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    padding: 2px 4px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.04);
  }
  .events-log-entry:last-child { border-bottom: none; }
  .status-tag {
    padding: 1px 4px;
    border-radius: 3px;
    font-size: 9.5px;
    font-weight: 600;
    text-transform: uppercase;
  }
  .status-tag.simulated { background: rgba(56, 189, 248, 0.2); color: #38bdf8; }
  .status-tag.delivered { background: rgba(34, 197, 94, 0.2); color: #4ade80; }
  .status-tag.failed { background: rgba(239, 68, 68, 0.2); color: #f87171; }
  .auth-role-badge {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 2px 7px;
    background: rgba(56, 189, 248, 0.1);
    border: 1px solid #38bdf8;
    border-radius: 4px;
    color: #38bdf8;
    font-weight: 600;
  }
  .auth-token-btn {
    background: transparent;
    border: 1px solid #334155;
    color: #94a3b8;
    border-radius: 4px;
    padding: 2px 6px;
    font-size: 11px;
    cursor: pointer;
    transition: all 0.15s;
  }
  .auth-token-btn:hover {
    border-color: #38bdf8;
    color: #f1f5f9;
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
      <div id="preview-auth-info" class="preview-auth-info" hidden></div>
      <div id="preview-events-info" class="preview-events-info" hidden>
        <div class="events-header-row">
          <div class="events-meta-group">
            <span class="events-badge">Event Bridge</span>
            <span id="events-subscriptions-count" class="events-count-badge">0 subscriptions</span>
            <span id="events-deliveries-count" class="events-count-badge">0 deliveries</span>
          </div>
          <div class="events-meta-group">
            <button type="button" id="events-toggle-sim" class="events-action-btn">Simulate Event</button>
            <button type="button" id="events-refresh-log" class="events-action-btn">Refresh Events</button>
          </div>
        </div>
        <div id="events-sim-panel" class="events-sim-panel" hidden>
          <input type="text" id="sim-event-type" class="events-sim-input" placeholder="Event Type (e.g. post.created)" style="flex: 1; min-width: 140px;" />
          <input type="text" id="sim-entity-name" class="events-sim-input" placeholder="Entity Name (e.g. Post)" style="width: 100px;" />
          <input type="text" id="sim-entity-id" class="events-sim-input" placeholder="Entity ID" style="width: 80px;" />
          <button type="button" id="sim-dispatch-btn" class="events-action-btn" style="background: rgba(99, 102, 241, 0.3); border-color: #818cf8; color: #fff;">Dispatch</button>
        </div>
        <div id="events-log-container" class="events-log-container" hidden>
          <div id="events-log-list"></div>
        </div>
      </div>
      <div id="preview-telemetry-info" class="preview-telemetry-info" hidden>
        <div class="telemetry-header-row">
          <div class="telemetry-meta-group">
            <span class="telemetry-badge">Telemetry</span>
            <span id="telemetry-surfaces-count" class="telemetry-count-badge">0 surfaces</span>
            <span id="telemetry-spans-count" class="telemetry-count-badge">0 spans</span>
          </div>
          <div class="telemetry-meta-group">
            <button type="button" id="telemetry-refresh-btn" class="telemetry-action-btn">Refresh Telemetry</button>
          </div>
        </div>
        <div id="telemetry-surfaces-list" class="telemetry-surfaces-list"></div>
      </div>
      <div id="preview-deployment-info" class="preview-deployment-info" hidden>
        <div class="deployment-header-row">
          <div class="deployment-meta-group">
            <span class="deployment-badge">Deployment</span>
            <span id="deployment-surfaces-count" class="deployment-count-badge">0 surfaces</span>
            <span id="deployment-routes-count" class="deployment-count-badge">0 routes</span>
          </div>
          <div class="deployment-meta-group">
            <button type="button" id="deployment-compose-btn" class="deployment-action-btn">Copy Compose YAML</button>
            <button type="button" id="deployment-refresh-btn" class="deployment-action-btn">Refresh Deployment</button>
          </div>
        </div>
        <div id="deployment-routes-list" class="deployment-routes-list"></div>
      </div>
      <div id="preview-sync-info" class="preview-sync-info" hidden>
        <div class="sync-header-row">
          <div class="sync-meta-group">
            <span class="sync-badge">Data Sync</span>
            <span id="sync-entities-count" class="sync-count-badge">0 entities</span>
            <span id="sync-version-badge" class="sync-count-badge">v0</span>
            <span id="sync-conflicts-count" class="sync-count-badge">0 conflicts</span>
          </div>
          <div class="sync-meta-group">
            <button type="button" id="sync-simulate-btn" class="sync-action-btn">Simulate Conflict</button>
            <button type="button" id="sync-refresh-btn" class="sync-action-btn">Refresh Sync</button>
          </div>
        </div>
        <div id="sync-entities-list" class="sync-entities-list"></div>
      </div>
      <div id="preview-cicd-info" class="preview-cicd-info" hidden>
        <div class="cicd-header-row">
          <div class="cicd-meta-group">
            <span class="cicd-badge">CI/CD Orchestration</span>
            <span id="cicd-workflows-count" class="cicd-count-badge">0 workflows</span>
            <span id="cicd-jobs-count" class="cicd-count-badge">0 jobs</span>
            <span id="cicd-status-badge" class="cicd-count-badge">configured</span>
          </div>
          <div class="cicd-meta-group">
            <button type="button" id="cicd-yaml-btn" class="cicd-action-btn">Copy GitHub Actions YAML</button>
            <button type="button" id="cicd-simulate-btn" class="cicd-action-btn">Simulate Pipeline</button>
            <button type="button" id="cicd-refresh-btn" class="cicd-action-btn">Refresh CI/CD</button>
          </div>
        </div>
        <div id="cicd-jobs-list" class="cicd-jobs-list"></div>
      </div>
      <div id="preview-verification-info" class="preview-verification-info" hidden>
        <div class="verification-header-row">
          <div class="verification-meta-group">
            <span class="verification-badge">Health &amp; Verification</span>
            <span id="verification-probe-count" class="verification-count-badge">0 probes</span>
            <span id="verification-smoke-count" class="verification-count-badge">0 smoke tests</span>
            <span id="verification-canary-count" class="verification-count-badge">0 canary rules</span>
          </div>
          <div class="verification-meta-group">
            <button type="button" id="verification-simulate-btn" class="verification-action-btn">Simulate Verification</button>
            <button type="button" id="verification-refresh-btn" class="verification-action-btn">Refresh</button>
          </div>
        </div>
      </div>
      <div id="preview-recovery-info" class="preview-recovery-info" hidden>
        <div class="recovery-header-row">
          <div class="recovery-meta-group">
            <span class="recovery-badge">Disaster Recovery &amp; Rollback</span>
            <span id="recovery-target-count" class="recovery-count-badge">0 backup targets</span>
            <span id="recovery-step-count" class="recovery-count-badge">0 recovery steps</span>
            <span id="recovery-trigger-count" class="recovery-count-badge">0 rollback triggers</span>
          </div>
          <div class="recovery-meta-group">
            <button type="button" id="recovery-simulate-btn" class="recovery-action-btn">Simulate DR Exercise</button>
            <button type="button" id="recovery-refresh-btn" class="recovery-action-btn">Refresh</button>
          </div>
        </div>
      </div>
      <div id="preview-capacity-info" class="preview-capacity-info" hidden>
        <div class="capacity-header-row">
          <div class="capacity-meta-group">
            <span class="capacity-badge">Capacity &amp; Unit Economics</span>
            <span id="capacity-spec-count" class="capacity-count-badge">0 capacity specs</span>
            <span id="capacity-quota-count" class="capacity-count-badge">0 resource quotas</span>
            <span id="capacity-budget-badge" class="capacity-count-badge">$0/mo budget</span>
          </div>
          <div class="capacity-meta-group">
            <button type="button" id="capacity-simulate-btn" class="capacity-action-btn">Simulate Capacity</button>
            <button type="button" id="capacity-refresh-btn" class="capacity-action-btn">Refresh</button>
          </div>
        </div>
      </div>
      <div id="preview-alerting-info" class="preview-alerting-info" hidden>
        <div class="alerting-header-row">
          <div class="alerting-meta-group">
            <span class="alerting-badge">Alerting &amp; Runbooks</span>
            <span id="alerting-rule-count" class="alerting-count-badge">0 alert rules</span>
            <span id="alerting-runbook-count" class="alerting-count-badge">0 runbooks</span>
            <span id="alerting-policy-count" class="alerting-count-badge">0 escalation policies</span>
          </div>
          <div class="alerting-meta-group">
            <button type="button" id="alerting-simulate-btn" class="alerting-action-btn">Simulate Alert</button>
            <button type="button" id="alerting-refresh-btn" class="alerting-action-btn">Refresh</button>
          </div>
        </div>
      </div>
      <div id="preview-sla-info" class="preview-sla-info" hidden>
        <div class="sla-header-row">
          <div class="sla-meta-group">
            <span class="sla-badge">SLA &amp; SLO</span>
            <span id="sla-sli-count" class="sla-count-badge">0 SLIs</span>
            <span id="sla-slo-count" class="sla-count-badge">0 SLOs</span>
            <span id="sla-contract-count" class="sla-count-badge">0 SLAs</span>
          </div>
          <div class="sla-meta-group">
            <button type="button" id="sla-simulate-btn" class="sla-action-btn">Simulate SLA</button>
            <button type="button" id="sla-refresh-btn" class="sla-action-btn">Refresh</button>
          </div>
        </div>
      </div>
      <div id="preview-governance-info" class="preview-governance-info" hidden>
        <div class="governance-header-row">
          <div class="governance-meta-group">
            <span class="governance-badge">Governance &amp; Audit</span>
            <span id="gov-standard-count" class="governance-count-badge">0 Standards</span>
            <span id="gov-policy-count" class="governance-count-badge">0 Policies</span>
            <span id="gov-evidence-count" class="governance-count-badge">0 Evidence Items</span>
          </div>
          <div class="governance-meta-group">
            <button type="button" id="gov-simulate-btn" class="governance-action-btn">Simulate Audit</button>
            <button type="button" id="gov-refresh-btn" class="governance-action-btn">Refresh</button>
          </div>
        </div>
      </div>
      <div id="preview-docs-info" class="preview-docs-info" hidden>
        <div class="docs-header-row">
          <div class="docs-meta-group">
            <span class="docs-badge">Docs &amp; OpenAPI</span>
            <span id="docs-page-count" class="docs-count-badge">0 Pages</span>
            <span id="docs-runbook-count" class="docs-count-badge">0 Runbooks</span>
            <span id="docs-endpoint-count" class="docs-count-badge">0 Endpoints</span>
          </div>
          <div class="docs-meta-group">
            <button type="button" id="docs-export-btn" class="docs-action-btn">Export Docs</button>
            <button type="button" id="docs-refresh-btn" class="docs-action-btn">Refresh</button>
          </div>
        </div>
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

    var authInfo = document.getElementById('preview-auth-info');
    if (authInfo) {
      if (preview && preview.is_ecosystem && preview.active_role) {
        authInfo.innerHTML = '';
        authInfo.hidden = false;
        var roleBadge = document.createElement('span');
        roleBadge.className = 'auth-role-badge';
        roleBadge.textContent = 'Role: ' + preview.active_role;
        authInfo.appendChild(roleBadge);

        if (preview.active_token) {
          var copyTokenBtn = document.createElement('button');
          copyTokenBtn.type = 'button';
          copyTokenBtn.className = 'auth-token-btn';
          copyTokenBtn.textContent = 'Copy Demo JWT';
          copyTokenBtn.title = 'Copy surface demo bearer token for API testing';
          copyTokenBtn.addEventListener('click', function () {
            copyTextToClipboard(preview.active_token);
            flashButton(copyTokenBtn, 'Copied!');
          });
          authInfo.appendChild(copyTokenBtn);
        }
      } else {
        authInfo.hidden = true;
      }
    }

    var eventsInfo = document.getElementById('preview-events-info');
    if (eventsInfo) {
      if (preview && preview.is_ecosystem && (preview.has_events || preview.subscription_count > 0)) {
        eventsInfo.hidden = false;
        var subBadge = document.getElementById('events-subscriptions-count');
        if (subBadge) {
          subBadge.textContent = (preview.subscription_count || 0) + ' subscriptions';
        }
        var delBadge = document.getElementById('events-deliveries-count');
        if (delBadge) {
          delBadge.textContent = (preview.event_count || 0) + ' deliveries';
        }
        loadEcosystemEventsLog();
      } else {
        eventsInfo.hidden = true;
      }
    }

    var telemetryInfo = document.getElementById('preview-telemetry-info');
    if (telemetryInfo) {
      if (preview && preview.is_ecosystem && preview.has_telemetry) {
        telemetryInfo.hidden = false;
        var surfaceCountBadge = document.getElementById('telemetry-surfaces-count');
        if (surfaceCountBadge) {
          surfaceCountBadge.textContent = (preview.telemetry_surface_count || 0) + ' surfaces';
        }
      } else {
        telemetryInfo.hidden = true;
      }
    }

    var deploymentInfo = document.getElementById('preview-deployment-info');
    if (deploymentInfo) {
      if (preview && preview.is_ecosystem && preview.has_deployment) {
        deploymentInfo.hidden = false;
        var depSurfaceBadge = document.getElementById('deployment-surfaces-count');
        if (depSurfaceBadge) {
          depSurfaceBadge.textContent = (preview.deployment_surface_count || 0) + ' surfaces';
        }
        var depRouteBadge = document.getElementById('deployment-routes-count');
        if (depRouteBadge) {
          var rCount = (preview.gateway_routes && preview.gateway_routes.length) || 0;
          depRouteBadge.textContent = rCount + ' routes';
        }
        var depRoutesList = document.getElementById('deployment-routes-list');
        if (depRoutesList && Array.isArray(preview.gateway_routes)) {
          depRoutesList.innerHTML = '';
          preview.gateway_routes.forEach(function (r) {
            var chip = document.createElement('span');
            chip.className = 'deployment-route-chip';
            chip.textContent = r.path_prefix + ' \u2192 :' + r.target_port + ' (' + r.target_surface + ')';
            depRoutesList.appendChild(chip);
          });
        }
      } else {
        deploymentInfo.hidden = true;
      }
    }

    var syncInfo = document.getElementById('preview-sync-info');
    if (syncInfo) {
      if (preview && preview.is_ecosystem && preview.has_sync) {
        syncInfo.hidden = false;
        var syncEntitiesBadge = document.getElementById('sync-entities-count');
        if (syncEntitiesBadge) {
          syncEntitiesBadge.textContent = (preview.sync_entity_count || 0) + ' entities';
        }
        var syncVersionBadge = document.getElementById('sync-version-badge');
        if (syncVersionBadge) {
          syncVersionBadge.textContent = 'v' + (preview.sync_version || 0);
        }
        var syncConflictsBadge = document.getElementById('sync-conflicts-count');
        if (syncConflictsBadge) {
          syncConflictsBadge.textContent = (preview.sync_conflict_count || 0) + ' conflicts';
        }
      } else {
        syncInfo.hidden = true;
      }
    }

    var cicdInfo = document.getElementById('preview-cicd-info');
    if (cicdInfo) {
      if (preview && preview.is_ecosystem && preview.has_cicd) {
        cicdInfo.hidden = false;
        var cicdWorkflowsBadge = document.getElementById('cicd-workflows-count');
        if (cicdWorkflowsBadge) {
          cicdWorkflowsBadge.textContent = (preview.cicd_workflow_count || 1) + ' workflow' + ((preview.cicd_workflow_count || 1) > 1 ? 's' : '');
        }
        var cicdJobsBadge = document.getElementById('cicd-jobs-count');
        if (cicdJobsBadge) {
          cicdJobsBadge.textContent = (preview.cicd_job_count || 0) + ' jobs';
        }
        var cicdStatusBadge = document.getElementById('cicd-status-badge');
        if (cicdStatusBadge) {
          cicdStatusBadge.textContent = preview.cicd_status || 'configured';
        }
      } else {
        cicdInfo.hidden = true;
      }
    }

    var verificationInfo = document.getElementById('preview-verification-info');
    if (verificationInfo) {
      if (preview && preview.is_ecosystem && preview.has_verification) {
        verificationInfo.hidden = false;
        var vProbeCount = document.getElementById('verification-probe-count');
        if (vProbeCount) {
          vProbeCount.textContent = (preview.probe_count || 0) + ' probe' + ((preview.probe_count || 0) !== 1 ? 's' : '');
        }
        var vSmokeCount = document.getElementById('verification-smoke-count');
        if (vSmokeCount) {
          vSmokeCount.textContent = (preview.smoke_test_count || 0) + ' smoke test' + ((preview.smoke_test_count || 0) !== 1 ? 's' : '');
        }
        var vCanaryCount = document.getElementById('verification-canary-count');
        if (vCanaryCount) {
          vCanaryCount.textContent = (preview.canary_rule_count || 0) + ' canary rule' + ((preview.canary_rule_count || 0) !== 1 ? 's' : '');
        }
      } else {
        verificationInfo.hidden = true;
      }
    }

    var recoveryInfo = document.getElementById('preview-recovery-info');
    if (recoveryInfo) {
      if (preview && preview.is_ecosystem && preview.has_recovery) {
        recoveryInfo.hidden = false;
        var rTargetCount = document.getElementById('recovery-target-count');
        if (rTargetCount) {
          rTargetCount.textContent = (preview.backup_target_count || 0) + ' backup target' + ((preview.backup_target_count || 0) !== 1 ? 's' : '');
        }
        var rStepCount = document.getElementById('recovery-step-count');
        if (rStepCount) {
          rStepCount.textContent = (preview.recovery_step_count || 0) + ' recovery step' + ((preview.recovery_step_count || 0) !== 1 ? 's' : '');
        }
        var rTriggerCount = document.getElementById('recovery-trigger-count');
        if (rTriggerCount) {
          rTriggerCount.textContent = (preview.rollback_trigger_count || 0) + ' rollback trigger' + ((preview.rollback_trigger_count || 0) !== 1 ? 's' : '');
        }
      } else {
        recoveryInfo.hidden = true;
      }
    }

    var capacityInfo = document.getElementById('preview-capacity-info');
    if (capacityInfo) {
      if (preview && preview.is_ecosystem && preview.has_capacity) {
        capacityInfo.hidden = false;
        var capSpecCount = document.getElementById('capacity-spec-count');
        if (capSpecCount) {
          capSpecCount.textContent = (preview.capacity_spec_count || 0) + ' capacity spec' + ((preview.capacity_spec_count || 0) !== 1 ? 's' : '');
        }
        var capQuotaCount = document.getElementById('capacity-quota-count');
        if (capQuotaCount) {
          capQuotaCount.textContent = (preview.quota_count || 0) + ' resource quota' + ((preview.quota_count || 0) !== 1 ? 's' : '');
        }
        var capBudgetBadge = document.getElementById('capacity-budget-badge');
        if (capBudgetBadge) {
          capBudgetBadge.textContent = '$' + (preview.monthly_budget_usd || 0) + '/mo budget';
        }
      } else {
        capacityInfo.hidden = true;
      }
    }

    var alertingInfo = document.getElementById('preview-alerting-info');
    if (alertingInfo) {
      if (preview && preview.is_ecosystem && preview.has_alerting) {
        alertingInfo.hidden = false;
        var alertRuleCount = document.getElementById('alerting-rule-count');
        if (alertRuleCount) {
          alertRuleCount.textContent = (preview.alert_rule_count || 0) + ' alert rule' + ((preview.alert_rule_count || 0) !== 1 ? 's' : '');
        }
        var alertRbCount = document.getElementById('alerting-runbook-count');
        if (alertRbCount) {
          alertRbCount.textContent = (preview.runbook_count || 0) + ' runbook' + ((preview.runbook_count || 0) !== 1 ? 's' : '');
        }
        var alertEpCount = document.getElementById('alerting-policy-count');
        if (alertEpCount) {
          alertEpCount.textContent = (preview.escalation_policy_count || 0) + ' escalation polic' + ((preview.escalation_policy_count || 0) !== 1 ? 'ies' : 'y');
        }
      } else {
        alertingInfo.hidden = true;
      }
    }

    var slaInfo = document.getElementById('preview-sla-info');
    if (slaInfo) {
      if (preview && preview.is_ecosystem && preview.has_sla) {
        slaInfo.hidden = false;
        var sliCount = document.getElementById('sla-sli-count');
        if (sliCount) {
          sliCount.textContent = (preview.sli_count || 0) + ' SLI' + ((preview.sli_count || 0) !== 1 ? 's' : '');
        }
        var sloCount = document.getElementById('sla-slo-count');
        if (sloCount) {
          sloCount.textContent = (preview.slo_count || 0) + ' SLO' + ((preview.slo_count || 0) !== 1 ? 's' : '');
        }
        var slaCount = document.getElementById('sla-contract-count');
        if (slaCount) {
          slaCount.textContent = (preview.sla_count || 0) + ' SLA' + ((preview.sla_count || 0) !== 1 ? 's' : '');
        }
      } else {
        slaInfo.hidden = true;
      }
    }

    var govInfo = document.getElementById('preview-governance-info');
    if (govInfo) {
      if (preview && preview.is_ecosystem && preview.has_governance) {
        govInfo.hidden = false;
        var stdCount = document.getElementById('gov-standard-count');
        if (stdCount) {
          stdCount.textContent = (preview.standard_count || 0) + ' Standard' + ((preview.standard_count || 0) !== 1 ? 's' : '');
        }
        var polCount = document.getElementById('gov-policy-count');
        if (polCount) {
          polCount.textContent = (preview.policy_count || 0) + ' Polic' + ((preview.policy_count || 0) !== 1 ? 'ies' : 'y');
        }
        var evCount = document.getElementById('gov-evidence-count');
        if (evCount) {
          evCount.textContent = (preview.evidence_count || 0) + ' Evidence Item' + ((preview.evidence_count || 0) !== 1 ? 's' : '');
        }
      } else {
        govInfo.hidden = true;
      }
    }

    var docsInfo = document.getElementById('preview-docs-info');
    if (docsInfo) {
      if (preview && preview.is_ecosystem && preview.has_docs) {
        docsInfo.hidden = false;
        var pageCount = document.getElementById('docs-page-count');
        if (pageCount) {
          pageCount.textContent = (preview.page_count || 0) + ' Page' + ((preview.page_count || 0) !== 1 ? 's' : '');
        }
        var rbCount = document.getElementById('docs-runbook-count');
        if (rbCount) {
          rbCount.textContent = (preview.runbook_count || 0) + ' Runbook' + ((preview.runbook_count || 0) !== 1 ? 's' : '');
        }
        var epCount = document.getElementById('docs-endpoint-count');
        if (epCount) {
          epCount.textContent = (preview.api_endpoint_count || 0) + ' Endpoint' + ((preview.api_endpoint_count || 0) !== 1 ? 's' : '');
        }
      } else {
        docsInfo.hidden = true;
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

  function loadEcosystemEventsLog() {
    var listContainer = document.getElementById('events-log-container');
    var listEl = document.getElementById('events-log-list');
    if (!listContainer || !listEl) { return; }

    fetch('/api/ecosystem/events')
      .then(function (res) { return res.ok ? res.json() : null; })
      .then(function (data) {
        if (!data || !data.deliveries) { return; }
        renderEventsLog(data.deliveries);
      })
      .catch(function () {});
  }

  function renderEventsLog(deliveries) {
    var listContainer = document.getElementById('events-log-container');
    var listEl = document.getElementById('events-log-list');
    var delBadge = document.getElementById('events-deliveries-count');
    if (!listContainer || !listEl) { return; }

    if (delBadge && deliveries) {
      delBadge.textContent = deliveries.length + ' deliveries';
    }

    if (!deliveries || !deliveries.length) {
      listContainer.hidden = true;
      listEl.innerHTML = '';
      return;
    }

    listContainer.hidden = false;
    listEl.innerHTML = '';

    deliveries.slice(-20).reverse().forEach(function (d) {
      var row = document.createElement('div');
      row.className = 'events-log-entry';

      var left = document.createElement('div');
      left.style.display = 'flex';
      left.style.gap = '6px';
      left.style.alignItems = 'center';

      var tag = document.createElement('span');
      tag.className = 'status-tag ' + (d.status === 'delivered' ? 'delivered' : (d.status === 'failed' ? 'failed' : 'simulated'));
      tag.textContent = d.status || 'event';
      left.appendChild(tag);

      var desc = document.createElement('span');
      desc.textContent = (d.event_id || '').slice(0, 10) + ' -> ' + (d.target_surface || 'surface');
      left.appendChild(desc);

      var right = document.createElement('div');
      right.style.color = '#64748b';
      right.textContent = (d.duration_ms ? d.duration_ms.toFixed(1) + 'ms' : '') + ' (' + (d.status_code || 200) + ')';

      row.appendChild(left);
      row.appendChild(right);
      listEl.appendChild(row);
    });
  }

  var toggleSimBtn = document.getElementById('events-toggle-sim');
  if (toggleSimBtn) {
    toggleSimBtn.addEventListener('click', function () {
      var panel = document.getElementById('events-sim-panel');
      if (panel) {
        panel.hidden = !panel.hidden;
      }
    });
  }

  var refreshLogBtn = document.getElementById('events-refresh-log');
  if (refreshLogBtn) {
    refreshLogBtn.addEventListener('click', function () {
      loadEcosystemEventsLog();
      flashButton(refreshLogBtn, 'Refreshed!');
    });
  }

  var telemetryRefreshBtn = document.getElementById('telemetry-refresh-btn');
  if (telemetryRefreshBtn) {
    telemetryRefreshBtn.addEventListener('click', function () {
      flashButton(telemetryRefreshBtn, 'Loading...');
      fetch('/api/ecosystem/telemetry')
        .then(function (res) { return res.json(); })
        .then(function (data) {
          var spansCount = document.getElementById('telemetry-spans-count');
          if (spansCount) {
            spansCount.textContent = (data.span_count || 0) + ' spans';
          }
          var surfacesList = document.getElementById('telemetry-surfaces-list');
          if (surfacesList && Array.isArray(data.traced_surfaces)) {
            surfacesList.innerHTML = '';
            data.traced_surfaces.forEach(function (ts) {
              var chip = document.createElement('span');
              chip.className = 'telemetry-surface-chip';
              chip.textContent = ts.display_name || ts.surface_slug;
              surfacesList.appendChild(chip);
            });
          }
          flashButton(telemetryRefreshBtn, 'Refreshed!');
        })
        .catch(function () {
          flashButton(telemetryRefreshBtn, 'Error');
        });
    });
  }

  var deploymentComposeBtn = document.getElementById('deployment-compose-btn');
  if (deploymentComposeBtn) {
    deploymentComposeBtn.addEventListener('click', function () {
      flashButton(deploymentComposeBtn, 'Fetching...');
      fetch('/api/ecosystem/deployment/compose')
        .then(function (res) {
          if (!res.ok) throw new Error('status ' + res.status);
          return res.text();
        })
        .then(function (yamlText) {
          if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(yamlText).then(function () {
              flashButton(deploymentComposeBtn, 'Copied Compose YAML!');
            });
          } else {
            flashButton(deploymentComposeBtn, 'YAML Ready');
          }
        })
        .catch(function () {
          flashButton(deploymentComposeBtn, 'Failed');
        });
    });
  }

  var deploymentRefreshBtn = document.getElementById('deployment-refresh-btn');
  if (deploymentRefreshBtn) {
    deploymentRefreshBtn.addEventListener('click', function () {
      flashButton(deploymentRefreshBtn, 'Loading...');
      fetch('/api/ecosystem/deployment')
        .then(function (res) {
          if (!res.ok) throw new Error('status ' + res.status);
          return res.json();
        })
        .then(function (data) {
          var depRoutesList = document.getElementById('deployment-routes-list');
          if (depRoutesList && Array.isArray(data.gateway_routes)) {
            depRoutesList.innerHTML = '';
            data.gateway_routes.forEach(function (r) {
              var chip = document.createElement('span');
              chip.className = 'deployment-route-chip';
              chip.textContent = r.path_prefix + ' \u2192 :' + r.target_port + ' (' + r.target_surface + ')';
              depRoutesList.appendChild(chip);
            });
          }
          var routeCountBadge = document.getElementById('deployment-routes-count');
          if (routeCountBadge && Array.isArray(data.gateway_routes)) {
            routeCountBadge.textContent = data.gateway_routes.length + ' routes';
          }
          flashButton(deploymentRefreshBtn, 'Refreshed!');
        })
        .catch(function () {
          flashButton(deploymentRefreshBtn, 'Error');
        });
    });
  }

  var syncSimulateBtn = document.getElementById('sync-simulate-btn');
  if (syncSimulateBtn) {
    syncSimulateBtn.addEventListener('click', function () {
      flashButton(syncSimulateBtn, 'Simulating...');
      fetch('/api/ecosystem/sync/simulate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          entity_name: 'Post',
          record_id: 'post-demo-1',
          local_surface: 'author-studio',
          remote_surface: 'cms-admin',
          local_updates: { title: 'Draft title by Author', content: 'Author content' },
          remote_updates: { title: 'Editorial Title by Editor', tags: ['news'] },
          strategy: 'field_merge'
        })
      })
        .then(function (res) {
          if (!res.ok) throw new Error('status ' + res.status);
          return res.json();
        })
        .then(function (data) {
          flashButton(syncSimulateBtn, 'Resolved: ' + data.conflict.winning_surface);
          var syncConflictsBadge = document.getElementById('sync-conflicts-count');
          if (syncConflictsBadge) {
            syncConflictsBadge.textContent = (data.conflict_count || 1) + ' conflicts';
          }
        })
        .catch(function () {
          flashButton(syncSimulateBtn, 'Failed');
        });
    });
  }

  var syncRefreshBtn = document.getElementById('sync-refresh-btn');
  if (syncRefreshBtn) {
    syncRefreshBtn.addEventListener('click', function () {
      flashButton(syncRefreshBtn, 'Loading...');
      fetch('/api/ecosystem/sync')
        .then(function (res) {
          if (!res.ok) throw new Error('status ' + res.status);
          return res.json();
        })
        .then(function (data) {
          var syncEntitiesList = document.getElementById('sync-entities-list');
          if (syncEntitiesList && data.sync_contract && Array.isArray(data.sync_contract.sync_entities)) {
            syncEntitiesList.innerHTML = '';
            data.sync_contract.sync_entities.forEach(function (e) {
              var chip = document.createElement('span');
              chip.className = 'sync-entity-chip';
              chip.textContent = e.entity_name + ' (' + e.conflict_strategy + ')';
              syncEntitiesList.appendChild(chip);
            });
          }
          var syncVersionBadge = document.getElementById('sync-version-badge');
          if (syncVersionBadge) {
            syncVersionBadge.textContent = 'v' + (data.current_version || 0);
          }
          var syncConflictsBadge = document.getElementById('sync-conflicts-count');
          if (syncConflictsBadge) {
            syncConflictsBadge.textContent = (data.conflict_count || 0) + ' conflicts';
          }
          flashButton(syncRefreshBtn, 'Refreshed!');
        })
        .catch(function () {
          flashButton(syncRefreshBtn, 'Error');
        });
    });
  }

  var cicdYamlBtn = document.getElementById('cicd-yaml-btn');
  if (cicdYamlBtn) {
    cicdYamlBtn.addEventListener('click', function () {
      flashButton(cicdYamlBtn, 'Fetching YAML...');
      fetch('/api/ecosystem/cicd/yaml')
        .then(function (res) {
          if (!res.ok) throw new Error('status ' + res.status);
          return res.text();
        })
        .then(function (yamlText) {
          if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(yamlText).then(function () {
              flashButton(cicdYamlBtn, 'YAML Copied!');
            }).catch(function () {
              flashButton(cicdYamlBtn, 'Loaded (' + yamlText.length + ' chars)');
            });
          } else {
            flashButton(cicdYamlBtn, 'Loaded (' + yamlText.length + ' chars)');
          }
        })
        .catch(function () {
          flashButton(cicdYamlBtn, 'Failed');
        });
    });
  }

  var cicdSimulateBtn = document.getElementById('cicd-simulate-btn');
  if (cicdSimulateBtn) {
    cicdSimulateBtn.addEventListener('click', function () {
      flashButton(cicdSimulateBtn, 'Simulating...');
      fetch('/api/ecosystem/cicd/simulate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({})
      })
        .then(function (res) {
          if (!res.ok) throw new Error('status ' + res.status);
          return res.json();
        })
        .then(function (data) {
          if (data && data.simulation) {
            var sim = data.simulation;
            flashButton(cicdSimulateBtn, sim.status === 'success' ? 'Sim Passed (' + sim.executed_jobs.length + ' jobs)' : 'Sim Failed');
          } else {
            flashButton(cicdSimulateBtn, 'Done');
          }
        })
        .catch(function () {
          flashButton(cicdSimulateBtn, 'Failed');
        });
    });
  }

  var cicdRefreshBtn = document.getElementById('cicd-refresh-btn');
  if (cicdRefreshBtn) {
    cicdRefreshBtn.addEventListener('click', function () {
      flashButton(cicdRefreshBtn, 'Loading...');
      fetch('/api/ecosystem/cicd')
        .then(function (res) {
          if (!res.ok) throw new Error('status ' + res.status);
          return res.json();
        })
        .then(function (data) {
          var cicdJobsList = document.getElementById('cicd-jobs-list');
          if (cicdJobsList && data.cicd_contract && Array.isArray(data.cicd_contract.workflows)) {
            cicdJobsList.innerHTML = '';
            data.cicd_contract.workflows.forEach(function (wf) {
              if (Array.isArray(wf.jobs)) {
                wf.jobs.forEach(function (jb) {
                  var chip = document.createElement('span');
                  chip.className = 'cicd-job-chip';
                  var deps = jb.needs && jb.needs.length ? ' [needs: ' + jb.needs.join(', ') + ']' : '';
                  chip.textContent = jb.job_id + deps;
                  cicdJobsList.appendChild(chip);
                });
              }
            });
          }
          var cicdWorkflowsBadge = document.getElementById('cicd-workflows-count');
          if (cicdWorkflowsBadge) {
            cicdWorkflowsBadge.textContent = (data.workflow_count || 1) + ' workflows';
          }
          var cicdJobsBadge = document.getElementById('cicd-jobs-count');
          if (cicdJobsBadge) {
            cicdJobsBadge.textContent = (data.job_count || 0) + ' jobs';
          }
          flashButton(cicdRefreshBtn, 'Refreshed!');
        })
        .catch(function () {
          flashButton(cicdRefreshBtn, 'Error');
        });
    });
  }

  var verificationSimulateBtn = document.getElementById('verification-simulate-btn');
  if (verificationSimulateBtn) {
    verificationSimulateBtn.addEventListener('click', function () {
      flashButton(verificationSimulateBtn, 'Simulating...');
      fetch('/api/ecosystem/verification/simulate', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: '{}' })
        .then(function (r) { return r.json(); })
        .then(function (data) {
          var s = data.summary || {};
          var pass = (s.probe_pass || 0) + (s.smoke_pass || 0) + (s.canary_pass || 0);
          var fail = (s.probe_fail || 0) + (s.smoke_fail || 0) + (s.canary_fail || 0);
          flashButton(verificationSimulateBtn, fail === 0 ? 'All Pass (' + pass + ')' : 'Failures: ' + fail);
        })
        .catch(function () {
          flashButton(verificationSimulateBtn, 'Error');
        });
    });
  }

  var verificationRefreshBtn = document.getElementById('verification-refresh-btn');
  if (verificationRefreshBtn) {
    verificationRefreshBtn.addEventListener('click', function () {
      flashButton(verificationRefreshBtn, 'Loading...');
      fetch('/api/ecosystem/verification')
        .then(function (r) { return r.json(); })
        .then(function (data) {
          var vProbeCount = document.getElementById('verification-probe-count');
          if (vProbeCount && data.probe_count != null) {
            vProbeCount.textContent = data.probe_count + ' probe' + (data.probe_count !== 1 ? 's' : '');
          }
          var vSmokeCount = document.getElementById('verification-smoke-count');
          if (vSmokeCount && data.smoke_test_count != null) {
            vSmokeCount.textContent = data.smoke_test_count + ' smoke test' + (data.smoke_test_count !== 1 ? 's' : '');
          }
          var vCanaryCount = document.getElementById('verification-canary-count');
          if (vCanaryCount && data.canary_rule_count != null) {
            vCanaryCount.textContent = data.canary_rule_count + ' canary rule' + (data.canary_rule_count !== 1 ? 's' : '');
          }
          flashButton(verificationRefreshBtn, 'Refreshed!');
        })
        .catch(function () {
          flashButton(verificationRefreshBtn, 'Error');
        });
    });
  }

  var recoverySimulateBtn = document.getElementById('recovery-simulate-btn');
  if (recoverySimulateBtn) {
    recoverySimulateBtn.addEventListener('click', function () {
      flashButton(recoverySimulateBtn, 'Simulating...');
      fetch('/api/ecosystem/recovery/simulate', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: '{}' })
        .then(function (r) { return r.json(); })
        .then(function (data) {
          var s = (data.result && data.result.summary) || data.summary || {};
          var pass = (s.snapshots_pass || 0) + (s.steps_pass || 0) + (s.triggers_pass || 0);
          var fail = (s.snapshots_fail || 0) + (s.steps_fail || 0) + (s.triggers_fail || 0);
          flashButton(recoverySimulateBtn, fail === 0 ? 'All Pass (' + pass + ')' : 'Failures: ' + fail);
        })
        .catch(function () {
          flashButton(recoverySimulateBtn, 'Error');
        });
    });
  }

  var recoveryRefreshBtn = document.getElementById('recovery-refresh-btn');
  if (recoveryRefreshBtn) {
    recoveryRefreshBtn.addEventListener('click', function () {
      flashButton(recoveryRefreshBtn, 'Loading...');
      fetch('/api/ecosystem/recovery')
        .then(function (r) { return r.json(); })
        .then(function (data) {
          var rTargetCount = document.getElementById('recovery-target-count');
          if (rTargetCount && data.backup_target_count != null) {
            rTargetCount.textContent = data.backup_target_count + ' backup target' + (data.backup_target_count !== 1 ? 's' : '');
          }
          var rStepCount = document.getElementById('recovery-step-count');
          if (rStepCount && data.recovery_step_count != null) {
            rStepCount.textContent = data.recovery_step_count + ' recovery step' + (data.recovery_step_count !== 1 ? 's' : '');
          }
          var rTriggerCount = document.getElementById('recovery-trigger-count');
          if (rTriggerCount && data.rollback_trigger_count != null) {
            rTriggerCount.textContent = data.rollback_trigger_count + ' rollback trigger' + (data.rollback_trigger_count !== 1 ? 's' : '');
          }
          flashButton(recoveryRefreshBtn, 'Refreshed!');
        })
        .catch(function () {
          flashButton(recoveryRefreshBtn, 'Error');
        });
    });
  }

  var capacitySimulateBtn = document.getElementById('capacity-simulate-btn');
  if (capacitySimulateBtn) {
    capacitySimulateBtn.addEventListener('click', function () {
      flashButton(capacitySimulateBtn, 'Simulating...');
      fetch('/api/ecosystem/capacity/simulate', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({tier: 'base'}) })
        .then(function (r) { return r.json(); })
        .then(function (data) {
          var rep = data.report || data;
          var status = (rep.status || 'pass').toUpperCase();
          var cost = rep.total_monthly_cost_usd != null ? '$' + rep.total_monthly_cost_usd : '';
          flashButton(capacitySimulateBtn, status + ' (' + cost + ')');
        })
        .catch(function () {
          flashButton(capacitySimulateBtn, 'Error');
        });
    });
  }

  var capacityRefreshBtn = document.getElementById('capacity-refresh-btn');
  if (capacityRefreshBtn) {
    capacityRefreshBtn.addEventListener('click', function () {
      flashButton(capacityRefreshBtn, 'Loading...');
      fetch('/api/ecosystem/capacity')
        .then(function (r) { return r.json(); })
        .then(function (data) {
          var capSpecCount = document.getElementById('capacity-spec-count');
          if (capSpecCount && data.capacity_spec_count != null) {
            capSpecCount.textContent = data.capacity_spec_count + ' capacity spec' + (data.capacity_spec_count !== 1 ? 's' : '');
          }
          var capQuotaCount = document.getElementById('capacity-quota-count');
          if (capQuotaCount && data.quota_count != null) {
            capQuotaCount.textContent = data.quota_count + ' resource quota' + (data.quota_count !== 1 ? 's' : '');
          }
          var capBudgetBadge = document.getElementById('capacity-budget-badge');
          if (capBudgetBadge && data.monthly_budget_usd != null) {
            capBudgetBadge.textContent = '$' + data.monthly_budget_usd + '/mo budget';
          }
          flashButton(capacityRefreshBtn, 'Refreshed!');
        })
        .catch(function () {
          flashButton(capacityRefreshBtn, 'Error');
        });
    });
  }

  var alertingSimulateBtn = document.getElementById('alerting-simulate-btn');
  if (alertingSimulateBtn) {
    alertingSimulateBtn.addEventListener('click', function () {
      flashButton(alertingSimulateBtn, 'Simulating...');
      fetch('/api/ecosystem/alerting/simulate', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({scenario: 'api_error_spike'}) })
        .then(function (r) { return r.json(); })
        .then(function (data) {
          var rep = data.report || data;
          var status = (rep.status || 'pass').toUpperCase();
          flashButton(alertingSimulateBtn, status);
        })
        .catch(function () {
          flashButton(alertingSimulateBtn, 'Error');
        });
    });
  }

  var alertingRefreshBtn = document.getElementById('alerting-refresh-btn');
  if (alertingRefreshBtn) {
    alertingRefreshBtn.addEventListener('click', function () {
      flashButton(alertingRefreshBtn, 'Loading...');
      fetch('/api/ecosystem/alerting')
        .then(function (r) { return r.json(); })
        .then(function (data) {
          var rCount = document.getElementById('alerting-rule-count');
          if (rCount && data.alert_rule_count != null) {
            rCount.textContent = data.alert_rule_count + ' alert rule' + (data.alert_rule_count !== 1 ? 's' : '');
          }
          var rbCount = document.getElementById('alerting-runbook-count');
          if (rbCount && data.runbook_count != null) {
            rbCount.textContent = data.runbook_count + ' runbook' + (data.runbook_count !== 1 ? 's' : '');
          }
          var epCount = document.getElementById('alerting-policy-count');
          if (epCount && data.escalation_policy_count != null) {
            epCount.textContent = data.escalation_policy_count + ' escalation polic' + (data.escalation_policy_count !== 1 ? 'ies' : 'y');
          }
          flashButton(alertingRefreshBtn, 'Refreshed!');
        })
        .catch(function () {
          flashButton(alertingRefreshBtn, 'Error');
        });
    });
  }

  var slaSimulateBtn = document.getElementById('sla-simulate-btn');
  if (slaSimulateBtn) {
    slaSimulateBtn.addEventListener('click', function () {
      flashButton(slaSimulateBtn, 'Simulating...');
      fetch('/api/ecosystem/sla/simulate', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({scenario: 'normal_operations'}) })
        .then(function (res) { return res.json(); })
        .then(function (data) {
          var status = data.sla_status || (data.report && data.report.sla_status) || 'Simulated!';
          flashButton(slaSimulateBtn, status);
        })
        .catch(function () {
          flashButton(slaSimulateBtn, 'Error');
        });
    });
  }

  var slaRefreshBtn = document.getElementById('sla-refresh-btn');
  if (slaRefreshBtn) {
    slaRefreshBtn.addEventListener('click', function () {
      flashButton(slaRefreshBtn, 'Loading...');
      fetch('/api/ecosystem/sla')
        .then(function (res) { return res.json(); })
        .then(function (data) {
          var sliCount = document.getElementById('sla-sli-count');
          if (sliCount && data.sli_count != null) {
            sliCount.textContent = data.sli_count + ' SLI' + (data.sli_count !== 1 ? 's' : '');
          }
          var sloCount = document.getElementById('sla-slo-count');
          if (sloCount && data.slo_count != null) {
            sloCount.textContent = data.slo_count + ' SLO' + (data.slo_count !== 1 ? 's' : '');
          }
          var slaCount = document.getElementById('sla-contract-count');
          if (slaCount && data.sla_count != null) {
            slaCount.textContent = data.sla_count + ' SLA' + (data.sla_count !== 1 ? 's' : '');
          }
          flashButton(slaRefreshBtn, 'Refreshed!');
        })
        .catch(function () {
          flashButton(slaRefreshBtn, 'Error');
        });
    });
  }

  var govSimulateBtn = document.getElementById('gov-simulate-btn');
  if (govSimulateBtn) {
    govSimulateBtn.addEventListener('click', function () {
      flashButton(govSimulateBtn, 'Simulating...');
      fetch('/api/ecosystem/governance/simulate', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({scenario: 'standard_audit'}) })
        .then(function (res) { return res.json(); })
        .then(function (data) {
          var status = data.governance_status || (data.report && data.report.overall_audit_passed ? 'Audit Passed' : 'Audit Failed') || 'Simulated!';
          flashButton(govSimulateBtn, status);
        })
        .catch(function () {
          flashButton(govSimulateBtn, 'Error');
        });
    });
  }

  var govRefreshBtn = document.getElementById('gov-refresh-btn');
  if (govRefreshBtn) {
    govRefreshBtn.addEventListener('click', function () {
      flashButton(govRefreshBtn, 'Loading...');
      fetch('/api/ecosystem/governance')
        .then(function (res) { return res.json(); })
        .then(function (data) {
          var stdCount = document.getElementById('gov-standard-count');
          if (stdCount && data.standard_count != null) {
            stdCount.textContent = data.standard_count + ' Standard' + (data.standard_count !== 1 ? 's' : '');
          }
          var polCount = document.getElementById('gov-policy-count');
          if (polCount && data.policy_count != null) {
            polCount.textContent = data.policy_count + ' Polic' + (data.policy_count !== 1 ? 'ies' : 'y');
          }
          var evCount = document.getElementById('gov-evidence-count');
          if (evCount && data.evidence_count != null) {
            evCount.textContent = data.evidence_count + ' Evidence Item' + (data.evidence_count !== 1 ? 's' : '');
          }
          flashButton(govRefreshBtn, 'Refreshed!');
        })
        .catch(function () {
          flashButton(govRefreshBtn, 'Error');
        });
    });
  }

  var docsExportBtn = document.getElementById('docs-export-btn');
  if (docsExportBtn) {
    docsExportBtn.addEventListener('click', function () {
      flashButton(docsExportBtn, 'Exporting...');
      fetch('/api/ecosystem/docs/export', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({format: 'markdown'}) })
        .then(function (res) { return res.json(); })
        .then(function (data) {
          var msg = data.file_count != null ? (data.file_count + ' Files!') : 'Exported!';
          flashButton(docsExportBtn, msg);
        })
        .catch(function () {
          flashButton(docsExportBtn, 'Error');
        });
    });
  }

  var docsRefreshBtn = document.getElementById('docs-refresh-btn');
  if (docsRefreshBtn) {
    docsRefreshBtn.addEventListener('click', function () {
      flashButton(docsRefreshBtn, 'Loading...');
      fetch('/api/ecosystem/docs')
        .then(function (res) { return res.json(); })
        .then(function (data) {
          var pageCount = document.getElementById('docs-page-count');
          if (pageCount && data.page_count != null) {
            pageCount.textContent = data.page_count + ' Page' + (data.page_count !== 1 ? 's' : '');
          }
          var rbCount = document.getElementById('docs-runbook-count');
          if (rbCount && data.runbook_count != null) {
            rbCount.textContent = data.runbook_count + ' Runbook' + (data.runbook_count !== 1 ? 's' : '');
          }
          var epCount = document.getElementById('docs-endpoint-count');
          if (epCount && data.api_endpoint_count != null) {
            epCount.textContent = data.api_endpoint_count + ' Endpoint' + (data.api_endpoint_count !== 1 ? 's' : '');
          }
          flashButton(docsRefreshBtn, 'Refreshed!');
        })
        .catch(function () {
          flashButton(docsRefreshBtn, 'Error');
        });
    });
  }

  var dispatchSimBtn = document.getElementById('sim-dispatch-btn');
  if (dispatchSimBtn) {
    dispatchSimBtn.addEventListener('click', function () {
      var eventTypeInput = document.getElementById('sim-event-type');
      var entityNameInput = document.getElementById('sim-entity-name');
      var entityIdInput = document.getElementById('sim-entity-id');

      var eventType = eventTypeInput ? eventTypeInput.value.trim() : '';
      if (!eventType) {
        eventType = 'test.event';
      }
      var entityName = entityNameInput ? entityNameInput.value.trim() : 'TestEntity';
      var entityId = entityIdInput ? entityIdInput.value.trim() : '1';

      dispatchSimBtn.disabled = true;
      fetch('/api/ecosystem/events/dispatch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          event_type: eventType,
          entity_name: entityName,
          entity_id: entityId,
          action: 'create',
          data: { simulated: true, timestamp: Date.now() }
        })
      })
      .then(function (res) { return res.json(); })
      .then(function (data) {
        flashButton(dispatchSimBtn, 'Dispatched (' + (data.dispatched_count || 0) + ')');
        loadEcosystemEventsLog();
      })
      .catch(function (err) {
        flashButton(dispatchSimBtn, 'Error');
      })
      .then(function () {
        dispatchSimBtn.disabled = false;
      });
    });
  }

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
