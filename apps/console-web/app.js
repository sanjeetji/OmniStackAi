"use strict";

// Zero-dependency console. Reads the committed, metadata-only snapshot and renders it with safe DOM
// APIs (textContent only — never innerHTML). Same-origin fetch only; no external requests.

function el(tag, opts, children) {
  const node = document.createElement(tag);
  if (opts && opts.class) node.className = opts.class;
  if (opts && opts.text != null) node.textContent = String(opts.text);
  for (const child of children || []) node.appendChild(child);
  return node;
}

function badge(kind, text) {
  return el("span", { class: "badge " + kind, text: text });
}

function stat(label, value) {
  return el("div", { class: "stat" }, [
    el("div", { class: "label", text: label }),
    el("div", { class: "value", text: value }),
  ]);
}

function table(headers, rows) {
  const thead = el("thead", null, [
    el(
      "tr",
      null,
      headers.map((h) => el("th", { class: h.num ? "num" : null, text: h.label }))
    ),
  ]);
  const tbody = el("tbody", null, rows);
  return el("div", { class: "overflow" }, [el("table", null, [thead, tbody])]);
}

function td(text, opts) {
  return el("td", { class: opts && opts.class, text: text });
}

function tdNode(node, opts) {
  const cell = el("td", { class: opts && opts.class });
  cell.appendChild(node);
  return cell;
}

function panel(title, body) {
  return el("section", { class: "panel" }, [el("h2", { text: title }), body]);
}

function sectionTitle(kicker, title, description) {
  return el("header", { class: "section-title" }, [
    el("p", { class: "eyebrow", text: kicker }),
    el("h2", { text: title }),
    el("p", { text: description }),
  ]);
}

function commandList(items) {
  return el(
    "ul",
    { class: "commands" },
    items.map((item) => el("li", null, [el("code", { text: item })]))
  );
}

function renderBuilderShowcase(showcase) {
  const section = el("section", { class: "product-section" });
  section.appendChild(
    sectionTitle(
      "Builder proof",
      "From intent to an engineering-ready project",
      "This view is produced from the real planner and edit engine. Commands are plans only; nothing is executed."
    )
  );

  const plan = showcase.projectPlan;
  const planBody = el("div", null, [
    el("div", { class: "panel-head" }, [
      el("div", null, [
        el("p", { class: "overline", text: "R-245 · combined project plan" }),
        el("h3", { text: plan.appName }),
      ]),
      badge("on", plan.apps.length + " generated apps"),
    ]),
  ]);

  planBody.appendChild(
    el(
      "div",
      { class: "app-grid" },
      plan.apps.map((app) => {
        const preview = app.preview || { url: "not available", steps: [] };
        const verify = app.verify || { gates: [], steps: [] };
        return el("article", { class: "app-card" }, [
          el("div", { class: "app-title" }, [
            el("div", null, [
              el("h4", { text: app.label }),
              el("p", { class: "mono muted", text: app.appDir }),
            ]),
            badge("target", app.target),
          ]),
          el("div", { class: "preview-url" }, [
            el("span", { text: "Preview" }),
            el("code", { text: preview.url }),
          ]),
          el(
            "div",
            { class: "gate-row" },
            verify.gates.map((gate) => badge("gate", gate))
          ),
          el("div", { class: "step-group" }, [
            el("p", { class: "overline", text: "Preview commands" }),
            commandList(preview.steps),
          ]),
          el("div", { class: "step-group" }, [
            el("p", { class: "overline", text: "Verification ladder" }),
            commandList(verify.steps.map((step) => step.kind + " · " + step.command)),
          ]),
        ]);
      })
    )
  );
  section.appendChild(el("section", { class: "panel builder-panel" }, [planBody]));

  const edit = showcase.editPreview;
  section.appendChild(
    el("section", { class: "panel patch-panel" }, [
      el("div", { class: "panel-head" }, [
        el("div", null, [
          el("p", { class: "overline", text: "R-246 · review-ready edit" }),
          el("h3", { text: edit.requestedChange }),
          el("p", { class: "muted", text: "Base example: " + edit.baseExample }),
        ]),
        badge("local", edit.changes.length + " files changed"),
      ]),
      el(
        "div",
        { class: "change-list" },
        edit.changes.map((change) =>
          el("div", { class: "change" }, [
            badge(change.kind === "renamed" ? "cloud" : "gate", change.kind),
            el("code", { text: change.oldPath ? change.oldPath + " → " + change.path : change.path }),
          ])
        )
      ),
      el("pre", { class: "patch", text: edit.unifiedPatch }),
    ])
  );
  section.appendChild(el("p", { class: "note", text: showcase.note }));
  return section;
}

function requireSnapshot(overview) {
  if (!overview || !Array.isArray(overview.providers) || !overview.builderShowcase) {
    throw new Error("Snapshot is missing required console data");
  }
}

function render(overview) {
  requireSnapshot(overview);
  const content = document.getElementById("content");
  content.textContent = "";

  content.appendChild(renderBuilderShowcase(overview.builderShowcase));
  content.appendChild(
    sectionTitle(
      "Model fabric",
      "Balanced routing with cost visibility",
      "Local Ollama is the default below L3; every cloud provider stays inactive until its key is configured."
    )
  );

  const activeCloud = overview.providers.filter((p) => p.tier === "cloud" && p.active).length;
  content.appendChild(
    el("div", { class: "grid" }, [
      stat("Routing mode", overview.routingMode),
      stat("Providers registered", overview.providers.length),
      stat("Cloud tier", overview.cloudTierSelected || "none"),
      stat("Active cloud keys", activeCloud),
    ])
  );

  content.appendChild(
    panel(
      "Balanced routing ladder",
      el(
        "ul",
        { class: "ladder" },
        overview.routingLadder.map((step) =>
          el("li", null, [
            el("span", { class: "lvl", text: step.level }),
            step.tier ? badge(step.tier, step.tier) : badge("off", "deterministic"),
            el("span", { text: step.action }),
          ])
        )
      )
    )
  );

  content.appendChild(
    panel(
      "Providers",
      table(
        [{ label: "Provider" }, { label: "Tier" }, { label: "Default model" }, { label: "Status" }],
        overview.providers.map((p) =>
          el("tr", null, [
            td(p.providerId, { class: "mono" }),
            tdNode(badge(p.tier, p.tier)),
            td(p.defaultModel, { class: "mono" }),
            tdNode(p.active ? badge("on", "active") : badge("off", "inactive · set " + p.keyEnv)),
          ])
        )
      )
    )
  );

  content.appendChild(
    panel(
      "Price book (USD per 1M tokens)",
      table(
        [{ label: "Provider" }, { label: "Model" }, { label: "Input", num: true }, { label: "Output", num: true }],
        overview.priceBook.map((row) =>
          el("tr", null, [
            td(row.providerId, { class: "mono" }),
            td(row.modelId, { class: "mono" }),
            td("$" + row.inputPerMTokUsd, { class: "num" }),
            td("$" + row.outputPerMTokUsd, { class: "num" }),
          ])
        )
      )
    )
  );

  const r = overview.resilience || { fallbackChain: [], circuitBreaker: { enabled: false } };
  content.appendChild(
    panel(
      "Resilience",
      el("div", { class: "grid" }, [
        stat("Fallback chain", r.fallbackChain.length ? r.fallbackChain.join(" → ") : "none"),
        stat("Circuit breaker", r.circuitBreaker.enabled ? "enabled" : "off"),
        stat("Failure threshold", r.circuitBreaker.failureThreshold != null ? r.circuitBreaker.failureThreshold : "—"),
        stat("Cooldown (s)", r.circuitBreaker.cooldownSeconds != null ? r.circuitBreaker.cooldownSeconds : "—"),
      ])
    )
  );

  const u = overview.usage;
  const usageBody = el("div", null, [
    el("div", { class: "grid" }, [
      stat("Total calls", u.totalCalls),
      stat("Successful", u.successfulCalls),
      stat("Total cost", "$" + u.totalCostUsd),
      stat("p95 latency", u.latencyP95Ms + " ms"),
    ]),
  ]);
  if (u.breakdowns.length > 0) {
    usageBody.appendChild(
      table(
        [
          { label: "Provider" }, { label: "Model" }, { label: "Calls", num: true },
          { label: "In", num: true }, { label: "Out", num: true }, { label: "Cost", num: true },
        ],
        u.breakdowns.map((b) =>
          el("tr", null, [
            td(b.providerId, { class: "mono" }),
            td(b.modelId, { class: "mono" }),
            td(b.calls, { class: "num" }),
            td(b.inputTokens, { class: "num" }),
            td(b.outputTokens, { class: "num" }),
            td("$" + b.costUsd, { class: "num" }),
          ])
        )
      )
    );
  }
  content.appendChild(panel("Usage & cost", usageBody));
  content.appendChild(el("p", { class: "note", text: overview.note }));
}

function showError(message) {
  const content = document.getElementById("content");
  content.textContent = "";
  content.appendChild(el("p", { class: "note error", text: message }));
}

fetch("data/overview.json", { cache: "no-store" })
  .then((response) => {
    if (!response.ok) throw new Error("HTTP " + response.status);
    return response.json();
  })
  .then(render)
  .catch(() => {
    showError(
      "Could not load data/overview.json. Serve this folder over HTTP (task console:serve) and " +
        "run task console:snapshot to refresh the data."
    );
  });
