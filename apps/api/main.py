from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse

from brand_os.workflows.content_draft import build_content_draft
from director_os.workflows.weekly_update import build_weekly_update
from packages.shared.orchestration.chief_of_staff import route_request
from packages.shared.schemas.brand_os import (
    BrandContentDraftRequest,
    BrandContentDraftResponse,
)
from packages.shared.schemas.director_os import (
    ErrorResponse,
    WeeklyUpdateRequest,
    WeeklyUpdateResponse,
)
from packages.shared.schemas.orchestrator import (
    OrchestratorRequest,
    OrchestratorResponse,
)

app = FastAPI(
    title="AI Operating System API",
    version="0.1.0",
    description="Local-first multi-domain AI-OS API for workflow execution and orchestration.",
)

OPERATOR_CONSOLE_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>AI-OS Operator Console</title>
  <style>
    :root {
      --bg: #f5f1e8;
      --panel: #fffdf8;
      --ink: #1f1a14;
      --muted: #6d655b;
      --line: #d8cebf;
      --accent: #0b6e4f;
      --accent-2: #c5622d;
      --shadow: 0 24px 60px rgba(31, 26, 20, 0.08);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: Georgia, "Times New Roman", serif;
      color: var(--ink);
      background:
        radial-gradient(circle at top left, rgba(197, 98, 45, 0.14), transparent 30%),
        radial-gradient(circle at top right, rgba(11, 110, 79, 0.12), transparent 28%),
        linear-gradient(180deg, #f7f3ec 0%, var(--bg) 100%);
    }
    main {
      max-width: 1180px;
      margin: 0 auto;
      padding: 40px 20px 56px;
    }
    .hero {
      display: grid;
      grid-template-columns: 1.2fr 0.8fr;
      gap: 18px;
      margin-bottom: 24px;
    }
    .card {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 20px;
      box-shadow: var(--shadow);
    }
    .hero-copy {
      padding: 28px;
    }
    .hero-copy h1 {
      margin: 0 0 12px;
      font-size: clamp(2rem, 4vw, 3.5rem);
      line-height: 0.95;
      letter-spacing: -0.04em;
    }
    .hero-copy p {
      margin: 0;
      color: var(--muted);
      font-size: 1.05rem;
      line-height: 1.5;
    }
    .hero-stats {
      padding: 22px;
      display: grid;
      gap: 12px;
    }
    .stat {
      padding: 14px 16px;
      border: 1px solid var(--line);
      border-radius: 14px;
      background: rgba(255, 255, 255, 0.72);
    }
    .stat strong {
      display: block;
      font-size: 0.85rem;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: var(--muted);
      margin-bottom: 6px;
    }
    .stat span {
      font-size: 1.05rem;
    }
    .workspace {
      display: grid;
      grid-template-columns: 360px 1fr;
      gap: 18px;
    }
    .guide {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 18px;
      margin-bottom: 18px;
    }
    .panel-header {
      padding: 18px 20px 0;
      display: flex;
      justify-content: space-between;
      align-items: baseline;
      gap: 12px;
    }
    .panel-header h2 {
      margin: 0;
      font-size: 1.05rem;
      letter-spacing: 0.01em;
    }
    .panel-header span {
      color: var(--muted);
      font-size: 0.9rem;
    }
    form {
      padding: 18px 20px 20px;
      display: grid;
      gap: 14px;
    }
    label {
      display: grid;
      gap: 6px;
      font-size: 0.9rem;
      color: var(--muted);
    }
    input, textarea, select {
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 12px 14px;
      font: inherit;
      color: var(--ink);
      background: #fff;
    }
    textarea {
      min-height: 120px;
      resize: vertical;
    }
    .row {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;
    }
    .checkbox {
      display: flex;
      gap: 10px;
      align-items: center;
      color: var(--ink);
    }
    .checkbox input {
      width: auto;
      margin: 0;
    }
    button {
      border: 0;
      border-radius: 999px;
      background: linear-gradient(135deg, var(--accent), #1a8c67);
      color: #fff;
      padding: 12px 18px;
      font: inherit;
      font-weight: 700;
      cursor: pointer;
    }
    button:hover { filter: brightness(1.05); }
    .results {
      padding: 0 20px 20px;
      display: grid;
      gap: 14px;
    }
    .status {
      margin: 0;
      color: var(--muted);
      min-height: 1.5em;
    }
    .sections {
      padding: 0 20px 20px;
      display: grid;
      gap: 16px;
    }
    .trace-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 12px;
    }
    .trace-card, .result-card, .raw-card {
      border: 1px solid var(--line);
      border-radius: 16px;
      padding: 16px;
      background: rgba(255, 255, 255, 0.68);
    }
    .trace-card h3, .result-card h3, .raw-card h3 {
      margin: 0 0 8px;
      font-size: 0.95rem;
    }
    .trace-card dl {
      margin: 0;
      display: grid;
      grid-template-columns: 110px 1fr;
      gap: 8px 10px;
      font-size: 0.92rem;
    }
    .trace-card dt {
      color: var(--muted);
    }
    ul {
      margin: 0;
      padding-left: 18px;
    }
    li + li {
      margin-top: 6px;
    }
    pre {
      margin: 0;
      white-space: pre-wrap;
      word-break: break-word;
      font-size: 0.88rem;
      line-height: 1.45;
    }
    .pill {
      display: inline-block;
      padding: 4px 10px;
      border-radius: 999px;
      background: rgba(11, 110, 79, 0.1);
      color: var(--accent);
      font-size: 0.8rem;
      font-weight: 700;
      letter-spacing: 0.04em;
      text-transform: uppercase;
    }
    .guide-card {
      padding: 20px;
    }
    .guide-card h2 {
      margin: 0 0 10px;
      font-size: 1.05rem;
    }
    .guide-card p,
    .guide-card li {
      color: var(--muted);
      line-height: 1.55;
    }
    .guide-card ul,
    .guide-card ol {
      margin: 0;
      padding-left: 20px;
    }
    .guide-card li + li {
      margin-top: 8px;
    }
    @media (max-width: 960px) {
      .hero, .workspace { grid-template-columns: 1fr; }
      .guide,
      .trace-grid { grid-template-columns: 1fr; }
    }
    @media (max-width: 640px) {
      .row { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <main>
    <section class="hero">
      <div class="card hero-copy">
        <div class="pill">Operator Console</div>
        <h1>Inspect workflow routing before it becomes mystery.</h1>
        <p>
          Submit one AI-OS request, see which workflow was selected, inspect the
          evidence footprint, and review fallback or model-state metadata without
          leaving the local stack.
        </p>
      </div>
      <div class="card hero-stats">
        <div class="stat">
          <strong>Entry Points</strong>
          <span>/director-os/weekly-update, /brand-os/content-draft, /orchestrate</span>
        </div>
        <div class="stat">
          <strong>What To Inspect</strong>
          <span>Workflow rationale, section counts, evidence sources, model flags.</span>
        </div>
        <div class="stat">
          <strong>Default Mode</strong>
          <span>Local-first orchestration with explicit workflow contracts.</span>
        </div>
      </div>
    </section>

    <section class="guide">
      <div class="card guide-card">
        <h2>What This Page Is</h2>
        <p>
          This console is a local inspection view for AI-OS. It lets you send one
          request through the orchestrator and then inspect what happened:
          which workflow ran, why it was selected, which files grounded the
          result, and whether the system used or skipped model-assisted synthesis.
        </p>
      </div>
      <div class="card guide-card">
        <h2>How To Use It</h2>
        <ol>
          <li>Start with a prompt that describes the work you want done.</li>
          <li>
            Leave <strong>Workflow</strong> on <strong>Auto-select</strong> to
            test routing, or choose a workflow explicitly to test a single domain.
          </li>
          <li>
            Use <strong>Data Path</strong> to point at the local notes or files
            you want the workflow to search, then run the request and inspect the
            trace cards on the right.
          </li>
        </ol>
      </div>
    </section>

    <section class="workspace">
      <div class="card">
        <div class="panel-header">
          <h2>Run A Workflow</h2>
          <span>Local API request</span>
        </div>
        <form id="orchestrate-form">
          <label>
            Prompt
            <textarea id="prompt" name="prompt">Prepare my leadership weekly update</textarea>
          </label>
          <div class="row">
            <label>
              Workflow
              <select id="workflow" name="workflow">
                <option value="">Auto-select</option>
                <option value="director_os.weekly_update">director_os.weekly_update</option>
                <option value="brand_os.content_draft">brand_os.content_draft</option>
              </select>
            </label>
            <label>
              Focus
              <input id="focus" name="focus" placeholder="Optional retrieval focus" />
            </label>
          </div>
          <div class="row">
            <label>
              Data Path
              <input id="data_path" name="data_path" value="data/local_only/projects" />
            </label>
            <label>
              Max Documents
              <input
                id="max_documents"
                name="max_documents"
                type="number"
                min="1"
                max="20"
                value="5"
              />
            </label>
          </div>
          <label class="checkbox">
            <input id="use_model" name="use_model" type="checkbox" />
            Request model-assisted synthesis when supported
          </label>
          <button type="submit">Run /orchestrate</button>
        </form>
        <div class="results">
          <p id="status" class="status">Ready. Submit a request to inspect the trace.</p>
        </div>
      </div>

      <div class="card">
        <div class="panel-header">
          <h2>Trace Output</h2>
          <span>Readable operator view</span>
        </div>
        <div class="sections">
          <div class="trace-grid">
            <div class="trace-card">
              <h3>Routing</h3>
              <dl id="routing-meta">
                <dt>Workflow</dt><dd>Not run yet</dd>
                <dt>Rationale</dt><dd>Submit a request to inspect routing.</dd>
              </dl>
            </div>
            <div class="trace-card">
              <h3>Execution Trace</h3>
              <dl id="trace-meta">
                <dt>Evidence</dt><dd>-</dd>
                <dt>Model</dt><dd>-</dd>
                <dt>Fallback</dt><dd>-</dd>
                <dt>Data Path</dt><dd>-</dd>
              </dl>
            </div>
          </div>
          <div class="result-card">
            <h3>Section Counts</h3>
            <p>Shows how much structured output the selected workflow produced.</p>
            <ul id="section-counts">
              <li>Run a request to populate section counts.</li>
            </ul>
          </div>
          <div class="result-card">
            <h3>Evidence Sources</h3>
            <p>Lists the local files that grounded the result.</p>
            <ul id="evidence-sources">
              <li>Run a request to inspect evidence sources.</li>
            </ul>
          </div>
          <div class="result-card">
            <h3>Result Summary</h3>
            <p>A readable summary of the workflow result.</p>
            <pre id="result-summary">No workflow run yet.</pre>
          </div>
          <div class="raw-card">
            <h3>Raw Response</h3>
            <p>The full JSON payload returned by <code>/orchestrate</code>.</p>
            <pre id="raw-response">No workflow run yet.</pre>
          </div>
        </div>
      </div>
    </section>
  </main>
  <script>
    const form = document.getElementById("orchestrate-form");
    const statusNode = document.getElementById("status");
    const routingMeta = document.getElementById("routing-meta");
    const traceMeta = document.getElementById("trace-meta");
    const sectionCounts = document.getElementById("section-counts");
    const evidenceSources = document.getElementById("evidence-sources");
    const resultSummary = document.getElementById("result-summary");
    const rawResponse = document.getElementById("raw-response");
    const dataPathInput = document.getElementById("data_path");
    const promptInput = document.getElementById("prompt");
    const workflowInput = document.getElementById("workflow");

    workflowInput.addEventListener("change", () => {
      if (workflowInput.value === "brand_os.content_draft") {
        dataPathInput.value = "data/local_only/brand";
        if (!promptInput.value.trim()) {
          promptInput.value = "Turn this work into a podcast and LinkedIn content draft";
        }
      } else if (workflowInput.value === "director_os.weekly_update") {
        dataPathInput.value = "data/local_only/projects";
        if (!promptInput.value.trim()) {
          promptInput.value = "Prepare my leadership weekly update";
        }
      }
    });

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      statusNode.textContent = "Running /orchestrate...";

      const payload = {
        prompt: document.getElementById("prompt").value || null,
        workflow: document.getElementById("workflow").value || null,
        focus: document.getElementById("focus").value || null,
        data_path: document.getElementById("data_path").value,
        max_documents: Number(document.getElementById("max_documents").value),
        use_model: document.getElementById("use_model").checked,
      };

      try {
        const response = await fetch("/orchestrate", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        const body = await response.json();

        if (!response.ok) {
          statusNode.textContent = "Request failed. Inspect the raw response below.";
          rawResponse.textContent = JSON.stringify(body, null, 2);
          resultSummary.textContent = body.detail || "The API returned an error.";
          return;
        }

        statusNode.textContent = "Workflow complete. Trace updated below.";
        routingMeta.innerHTML =
          "<dt>Workflow</dt><dd>" + body.selected_workflow + "</dd>" +
          "<dt>Rationale</dt><dd>" + body.rationale + "</dd>";

        traceMeta.innerHTML =
          "<dt>Evidence</dt><dd>" + body.trace.evidence_count + " items</dd>" +
          "<dt>Model</dt><dd>requested=" + body.trace.model_requested +
          ", supported=" + body.trace.model_supported +
          ", used=" + body.trace.model_used + "</dd>" +
          "<dt>Fallback</dt><dd>" + body.trace.fallback_used + "</dd>" +
          "<dt>Data Path</dt><dd>" + body.trace.data_path + "</dd>";

        sectionCounts.innerHTML = Object.entries(body.trace.section_counts)
          .map(([key, value]) => "<li><strong>" + key + "</strong>: " + value + "</li>")
          .join("");

        evidenceSources.innerHTML = body.trace.evidence_sources
          .map((source) => "<li>" + source + "</li>")
          .join("");

        const result = body.result || {};
        resultSummary.textContent =
          result.summary || result.insight_summary || "No summary field returned.";
        rawResponse.textContent = JSON.stringify(body, null, 2);
      } catch (error) {
        statusNode.textContent = "Request failed before the API responded.";
        resultSummary.textContent = String(error);
      }
    });
  </script>
</body>
</html>
"""


@app.get("/health")
def health() -> dict[str, str]:
    """Lightweight health check for local development and smoke tests."""
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
def operator_console() -> HTMLResponse:
    """Serve a minimal operator-facing console for trace-first local workflow inspection."""
    return HTMLResponse(OPERATOR_CONSOLE_HTML)


@app.post(
    "/director-os/weekly-update",
    response_model=WeeklyUpdateResponse,
    responses={400: {"model": ErrorResponse}},
)
def create_weekly_update(request: WeeklyUpdateRequest) -> WeeklyUpdateResponse:
    """Run the Director OS weekly update workflow against local project notes."""
    try:
        # FastAPI handles HTTP parsing and validation for us. After that, the
        # route simply hands the typed request object to the workflow layer.
        # The API layer stays intentionally thin. The real workflow logic lives
        # in Director OS so it can be tested without starting FastAPI.
        return build_weekly_update(request)
    except ValueError as exc:
        # Validation and retrieval failures are returned as client-facing 400 errors.
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post(
    "/brand-os/content-draft",
    response_model=BrandContentDraftResponse,
    responses={400: {"model": ErrorResponse}},
)
def create_brand_content_draft(
    request: BrandContentDraftRequest,
) -> BrandContentDraftResponse:
    """Run the Brand OS content-draft workflow against local brand notes."""
    try:
        return build_content_draft(request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post(
    "/orchestrate",
    response_model=OrchestratorResponse,
    responses={400: {"model": ErrorResponse}},
)
def orchestrate(request: OrchestratorRequest) -> OrchestratorResponse:
    """Route a request through the lightweight Chief of Staff layer."""
    try:
        # This endpoint shows the "AI-OS" idea at a higher level: the caller
        # sends one generic request, and the orchestrator decides which domain
        # workflow should handle it.
        return route_request(request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
