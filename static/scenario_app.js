const fallbackExamples = [
  {
    scenario_text: "Known customer cust-789 is on the web vehicle page. She is a preferred loyalty member searching for a family SUV airport rental at SFO, checked availability, and started booking for a summer trip. Personalization consent is true.",
    domain: "car_rental",
    channel: "web",
    intent: "purchase",
    journey_stage: "purchase",
    tapl_action: "show",
    expected_candidate_id: "vehicle_upgrade_suv",
    purpose: "Identify an anonymous family airport-rental shopper comparing SUV options and recommend a relevant SUV upgrade before booking."
  },
  {
    scenario_text: "guest looking for hotel room availability this weekend",
    domain: "hotel",
    channel: "web",
    intent: "research",
    journey_stage: "consideration",
    tapl_action: "show",
    expected_candidate_id: "hotel_reservation_assist",
    purpose: "Help a hotel shopper move from availability research to reservation completion."
  },
  {
    scenario_text: "person sitting in restaurant viewing menu from website",
    domain: "restaurant",
    channel: "web",
    intent: "purchase",
    journey_stage: "purchase",
    tapl_action: "show",
    expected_candidate_id: "restaurant_menu_recommendation",
    purpose: "Personalize menu or cuisine content for a restaurant visitor preparing to order."
  },
  {
    scenario_text: "doctor reading obesity product information on healthcare website",
    domain: "healthcare",
    channel: "web",
    intent: "research",
    journey_stage: "research",
    tapl_action: "show",
    expected_candidate_id: "obesity_product_hcp_education",
    purpose: "Recommend approved obesity product education for a healthcare professional."
  }
];
let scenarioExamples = fallbackExamples;
let lastScenarioData = null;
let activeMode = "recommend";

const scenarioText = document.getElementById("scenarioText");
const scenarioUseLlm = document.getElementById("scenarioUseLlm");
const scenarioUseLlmExplanation = document.getElementById("scenarioUseLlmExplanation");
const scenarioRunBtn = document.getElementById("scenarioRunBtn");
const scenarioExampleSelect = document.getElementById("scenarioExampleSelect");
const scenarioExampleMeta = document.getElementById("scenarioExampleMeta");
const scenarioLoadExampleBtn = document.getElementById("scenarioLoadExampleBtn");
const scenarioStatus = document.getElementById("scenarioStatus");
const scenarioLoading = document.getElementById("scenarioLoading");
const scenarioRecommendation = document.getElementById("scenarioRecommendation");
const parsedContext = document.getElementById("parsedContext");
const technicalExplanation = document.getElementById("technicalExplanation");
const payloadPreview = document.getElementById("scenarioPayloadPreview");
const responsePreview = document.getElementById("scenarioResponsePreview");
const scenarioArchitecturePanels = document.getElementById("scenarioArchitecturePanels");
const scenarioModeTabs = document.querySelectorAll(".scenario-mode-tab");

const { escapeHtml, pct, pretty, renderArchitecturePanels } = window.DemoShared;

function num(value) {
  return Number(value || 0).toFixed(2);
}

function truncate(value, maxLength = 82) {
  const text = String(value || "");
  return text.length > maxLength ? `${text.slice(0, maxLength - 1)}...` : text;
}

function compactScenarioLabel(example) {
  return truncate(example.scenario_text, 58);
}

function selectedExample() {
  const index = Number(scenarioExampleSelect.value || 0);
  return scenarioExamples[index] || scenarioExamples[0];
}

function renderExampleMeta(example) {
  if (!example) {
    scenarioExampleMeta.textContent = "No scenario selected.";
    return;
  }
  scenarioExampleMeta.innerHTML = `
    <div class="scenario-summary-card">
      <span>Purpose</span>
      <strong>${escapeHtml(example.purpose || truncate(example.scenario_text, 92))}</strong>
    </div>
    <div class="scenario-chip-row">
      <span>${escapeHtml(pretty(example.domain))}</span>
      <span>${escapeHtml(pretty(example.channel))}</span>
      <span>${escapeHtml(pretty(example.journey_stage))}</span>
      <span>${escapeHtml(pretty(example.expected_candidate_id))}</span>
    </div>
  `;
}

function renderExampleOptions() {
  scenarioExampleSelect.innerHTML = "";
  const groups = new Map();
  scenarioExamples.forEach((example, index) => {
    const domain = example.domain || "general";
    if (!groups.has(domain)) {
      groups.set(domain, []);
    }
    groups.get(domain).push({ example, index });
  });

  groups.forEach((items, domain) => {
    const group = document.createElement("optgroup");
    group.label = pretty(domain);
    items.forEach(({ example, index }) => {
      const option = document.createElement("option");
      option.value = String(index);
      option.textContent = compactScenarioLabel(example);
      group.appendChild(option);
    });
    scenarioExampleSelect.appendChild(group);
  });
  renderExampleMeta(selectedExample());
}

async function loadScenarioExamples() {
  try {
    const response = await fetch("/scenario-examples");
    if (!response.ok) {
      throw new Error(`GET /scenario-examples returned ${response.status}`);
    }
    const data = await response.json();
    if (Array.isArray(data.records) && data.records.length) {
      scenarioExamples = data.records;
      scenarioStatus.textContent = `Loaded ${data.records.length} training scenarios.`;
    }
  } catch (error) {
    scenarioExamples = fallbackExamples;
    scenarioStatus.textContent = "Loaded fallback scenarios.";
  }
  renderExampleOptions();
  if (selectedExample()) {
    scenarioText.value = selectedExample().scenario_text;
    updatePayloadPreview();
  }
}

function buildPayload() {
  return {
    scenario_text: scenarioText.value.trim(),
    limit: 3,
    use_ai_models: true,
    use_llm: scenarioUseLlm.checked,
    use_llm_explanation: scenarioUseLlmExplanation.checked
  };
}

function updatePayloadPreview() {
  payloadPreview.textContent = JSON.stringify(buildPayload(), null, 2);
}

function setActiveMode(mode) {
  activeMode = mode;
  scenarioModeTabs.forEach(tab => {
    const selected = tab.dataset.mode === mode;
    tab.classList.toggle("is-active", selected);
    tab.setAttribute("aria-selected", selected ? "true" : "false");
  });
  const labels = {
    recommend: "Run recommendation",
    simulate: "Simulate all outcomes",
    memory: "Load experience memory"
  };
  scenarioRunBtn.textContent = labels[mode] || "Run";
}

function parsedContextFromSummary(summary) {
  return summary?.parsed_context || summary?.context || lastScenarioData?.request_summary?.parsed_context || {};
}

function renderParsedContext(summary) {
  const context = parsedContextFromSummary(summary);
  const nlp = summary.nlp || {};
  const llmStatus = nlp.llm_status || {};
  const training = nlp.training_reference || {};
  parsedContext.innerHTML = `
    <div><span>Parser</span><strong>${escapeHtml(pretty(nlp.parser || "unknown"))}</strong></div>
    <div><span>LLM status</span><strong>${escapeHtml(pretty(llmStatus.last_status || (summary.llm_enabled ? "ready" : "not_configured")))}</strong></div>
    <div><span>Channel</span><strong>${escapeHtml(pretty(context.channel))}</strong></div>
    <div><span>Intent</span><strong>${escapeHtml(pretty(context.current_intent))}</strong></div>
    <div><span>Journey</span><strong>${escapeHtml(pretty(context.journey_stage))}</strong></div>
    <div><span>Customer</span><strong>${escapeHtml(context.customer_id || "anonymous")}</strong></div>
    <div><span>Training reference</span><strong>${training.matched ? `Matched (${training.expected_candidate_id || "unknown"})` : "None"}</strong></div>
    <div><span>LLM fallback</span><strong>${escapeHtml(nlp.llm_fallback ? (nlp.llm_fallback_reason || "Yes") : "No")}</strong></div>
    <div><span>Profile lookup</span><strong>${escapeHtml(pretty((summary.profile || {}).profile_lookup || "not used"))}</strong></div>
    <div><span>Events</span><strong>${escapeHtml((context.session_events || []).join(", "))}</strong></div>
    <div><span>Search terms</span><strong>${escapeHtml((context.search_terms || []).join(", "))}</strong></div>
  `;
}

function renderRecommendation(data) {
  const rec = data.recommendations[0];
  const outcome = rec.ai_score.outcome_simulation;
  scenarioRecommendation.innerHTML = `
    <p class="eyebrow">Top recommendation</p>
    <div class="offer-header">
      <div>
        <h2>${escapeHtml(rec.candidate.title)}</h2>
        <p>${escapeHtml(rec.candidate.description)}</p>
      </div>
      <strong class="score-badge">${pct(rec.ai_score.final_hybrid_score)}</strong>
    </div>
    <div class="offer-metrics">
      <div><span>Intent</span><strong>${escapeHtml(pretty(rec.ai_score.intent.label))}</strong><small>${escapeHtml(pretty(rec.ai_score.intent.source))}</small></div>
      <div><span>TAPL action</span><strong>${escapeHtml(pretty(rec.ai_score.tapl.action))}</strong></div>
      <div><span>Explanation</span><strong>${escapeHtml(pretty(rec.explanation_source || "local"))}</strong></div>
    </div>
    <p class="explanation">${escapeHtml(rec.explanation)}</p>
    <div class="pill-row">${rec.reason_codes.map(reason => `<span>${escapeHtml(reason.replaceAll("_", " "))}</span>`).join("")}</div>
  `;
}

function renderTechnicalExplanation(data) {
  const summary = data.request_summary || {};
  const context = summary.parsed_context || {};
  const nlp = summary.nlp || {};
  const rec = data.recommendations[0];
  const candidate = rec.candidate;
  const eds = rec.eds_score;
  const ai = rec.ai_score;
  const tapl = ai.tapl;
  const outcome = ai.outcome_simulation;
  const example = selectedExample();
  const training = summary.training_alignment || {};
  const expected = training.expected_candidate_id || example?.expected_candidate_id || "not provided";
  const matchedExpected = expected === candidate.id;

  technicalExplanation.innerHTML = `
    <div class="technical-grid">
      <article>
        <span>1. Scenario NLP</span>
        <p>The free-text scenario was converted into structured context before ranking.</p>
        <dl>
          <div><dt>Domain</dt><dd>${escapeHtml(pretty(nlp.detected_domain || "unknown"))}</dd></div>
          <div><dt>Channel</dt><dd>${escapeHtml(pretty(context.channel))}</dd></div>
          <div><dt>Intent</dt><dd>${escapeHtml(pretty(context.current_intent))}</dd></div>
          <div><dt>Journey</dt><dd>${escapeHtml(pretty(context.journey_stage))}</dd></div>
          <div><dt>Keywords</dt><dd>${escapeHtml((nlp.keywords || []).join(", ") || "none")}</dd></div>
          <div><dt>LLM status</dt><dd>${escapeHtml(pretty((nlp.llm_status || {}).last_status || "not requested"))}</dd></div>
        </dl>
      </article>
      <article>
        <span>2. Candidate Filtering</span>
        <p>The API first narrowed the catalog using channel and scenario keyword overlap.</p>
        <dl>
          <div><dt>Candidate selected</dt><dd>${escapeHtml(candidate.id)}</dd></div>
          <div><dt>Candidate count</dt><dd>${escapeHtml(summary.candidate_preselection?.candidate_count ?? "n/a")}</dd></div>
          <div><dt>Expected from training row</dt><dd>${escapeHtml(expected)}</dd></div>
          <div><dt>Training alignment</dt><dd>${matchedExpected ? "Top rank matches training label" : "Exploratory / NLP-driven ranking"}</dd></div>
          <div><dt>Override mode</dt><dd>${escapeHtml(training.matched ? "Metadata only (no CSV override)" : "NLP-only parse")}</dd></div>
          <div><dt>Purpose</dt><dd>${escapeHtml(training.purpose || example?.purpose || "not provided")}</dd></div>
        </dl>
      </article>
      <article>
        <span>3. Scoring Signals</span>
        <p>The ranker combines EDS relevance, semantic similarity, channel fit, and simulated outcome.</p>
        <dl>
          <div><dt>EDS score</dt><dd>${num(eds.final_eds_score)}</dd></div>
          <div><dt>Semantic similarity</dt><dd>${num(ai.semantic_similarity_score)}</dd></div>
          <div><dt>Channel fit</dt><dd>${num(ai.channel_fit_score)}</dd></div>
          <div><dt>Expected outcome</dt><dd>${num(outcome.expected_outcome_score)}</dd></div>
          <div><dt>Final rank score</dt><dd>${num(ai.final_hybrid_score)}</dd></div>
          <div><dt>Explanation source</dt><dd>${escapeHtml(pretty(rec.explanation_source || "local"))}</dd></div>
        </dl>
      </article>
      <article>
        <span>4. Trust And TAPL</span>
        <p>TAPL decides whether to show, soften, delay, suppress, or fallback based on sensitivity, fatigue, and trust.</p>
        <dl>
          <div><dt>Action</dt><dd>${escapeHtml(pretty(tapl.action))}</dd></div>
          <div><dt>Trust</dt><dd>${num(tapl.trust_score)}</dd></div>
          <div><dt>Fatigue</dt><dd>${num(tapl.fatigue_score)}</dd></div>
          <div><dt>Compliance</dt><dd>${num(tapl.compliance_score)}</dd></div>
          <div><dt>Reason codes</dt><dd>${escapeHtml((rec.reason_codes || []).join(", "))}</dd></div>
        </dl>
      </article>
    </div>
  `;
}

function showError(error) {
  scenarioRecommendation.innerHTML = `
    <p class="eyebrow">Error</p>
    <h2>Could not generate recommendation.</h2>
    <p class="explanation">${escapeHtml(error.message || String(error))}</p>
  `;
  responsePreview.textContent = String(error.stack || error.message || error);
  scenarioStatus.textContent = "Error";
}

async function runScenario() {
  if (activeMode === "simulate") {
    return runSimulate();
  }
  if (activeMode === "memory") {
    return runExperienceMemory();
  }

  const payload = buildPayload();
  updatePayloadPreview();
  scenarioLoading.classList.remove("hidden");
  scenarioStatus.textContent = "Parsing scenario...";

  try {
    const response = await fetch("/recommend-from-scenario", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    if (!response.ok) {
      const body = await response.text();
      throw new Error(`POST /recommend-from-scenario returned ${response.status}: ${body}`);
    }
    const data = await response.json();
    lastScenarioData = data;
    responsePreview.textContent = JSON.stringify(data, null, 2);
    renderParsedContext(data.request_summary);
    if (!data.recommendations.length) {
      throw new Error("The API returned no recommendations for this scenario.");
    }
    renderRecommendation(data);
    renderTechnicalExplanation(data);
    renderArchitecturePanels(scenarioArchitecturePanels, data.request_summary, data.recommendations[0]);
    const parser = pretty((data.request_summary.nlp || {}).parser || "unknown");
    scenarioStatus.textContent = `Done. Parsed with ${parser}.`;
  } catch (error) {
    showError(error);
  } finally {
    scenarioLoading.classList.add("hidden");
  }
}

async function runSimulate() {
  scenarioLoading.classList.remove("hidden");
  scenarioStatus.textContent = "Parsing scenario for simulation...";

  try {
    let context = parsedContextFromSummary(lastScenarioData?.request_summary || {});
    if (!context.channel) {
      const parseResponse = await fetch("/recommend-from-scenario", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(buildPayload())
      });
      if (!parseResponse.ok) {
        throw new Error(`Could not parse scenario before simulate (${parseResponse.status}).`);
      }
      const parsed = await parseResponse.json();
      lastScenarioData = parsed;
      context = parsed.request_summary.parsed_context;
    }

    const payload = { context };
    payloadPreview.textContent = JSON.stringify(payload, null, 2);
    scenarioStatus.textContent = "Simulating all candidate outcomes...";

    const response = await fetch("/simulate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    if (!response.ok) {
      const body = await response.text();
      throw new Error(`POST /simulate returned ${response.status}: ${body}`);
    }
    const data = await response.json();
    responsePreview.textContent = JSON.stringify(data, null, 2);
    renderParsedContext(data.request_summary);
    if (!data.recommendations.length) {
      throw new Error("Simulate returned no recommendations.");
    }
    scenarioRecommendation.innerHTML = `
      <p class="eyebrow">Simulated outcomes</p>
      <h2>${data.recommendations.length} candidates ranked for this context</h2>
      <div class="recommendation-list">
        ${data.recommendations.map((rec, index) => `
          <article class="mini-card">
            <div>
              <span class="rank">#${index + 1}</span>
              <h3>${escapeHtml(rec.candidate.title)}</h3>
              <p>${escapeHtml(rec.explanation)}</p>
            </div>
            <strong>${pct(rec.ai_score.final_hybrid_score)}</strong>
          </article>
        `).join("")}
      </div>
    `;
    technicalExplanation.textContent = "Simulate ranks every catalog candidate for the parsed context without TAPL delivery filtering.";
    renderArchitecturePanels(scenarioArchitecturePanels, data.request_summary, data.recommendations[0]);
    scenarioStatus.textContent = "Simulation complete.";
  } catch (error) {
    showError(error);
  } finally {
    scenarioLoading.classList.add("hidden");
  }
}

async function runExperienceMemory() {
  scenarioLoading.classList.remove("hidden");
  scenarioStatus.textContent = "Resolving subject for experience memory...";

  try {
    let context = parsedContextFromSummary(lastScenarioData?.request_summary || {});
    if (!context.channel) {
      const parseResponse = await fetch("/recommend-from-scenario", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(buildPayload())
      });
      if (!parseResponse.ok) {
        throw new Error(`Could not parse scenario before memory lookup (${parseResponse.status}).`);
      }
      const parsed = await parseResponse.json();
      lastScenarioData = parsed;
      context = parsed.request_summary.parsed_context;
      renderParsedContext(parsed.request_summary);
    }

    const params = new URLSearchParams();
    if (context.customer_id) {
      params.set("customer_id", context.customer_id);
    }
    if (context.anonymous_id) {
      params.set("anonymous_id", context.anonymous_id);
    }
    const url = `/experience-memory?${params.toString()}`;
    payloadPreview.textContent = url;
    scenarioStatus.textContent = "Loading EML snapshot...";

    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(`GET /experience-memory returned ${response.status}`);
    }
    const memory = await response.json();
    responsePreview.textContent = JSON.stringify(memory, null, 2);
    scenarioRecommendation.innerHTML = `
      <p class="eyebrow">Experience memory snapshot</p>
      <h2>${escapeHtml(memory.subject_id || "Unknown subject")}</h2>
      ${window.DemoShared.memoryBlock(memory)}
    `;
    technicalExplanation.textContent = "Experience memory stores trust, fatigue, preferences, and outcome history for the parsed subject.";
    renderArchitecturePanels(scenarioArchitecturePanels, {
      experience_memory: { before: memory, after: memory },
      haoe: lastScenarioData?.request_summary?.haoe || {},
      ose_calibration: lastScenarioData?.request_summary?.ose_calibration || {},
      context_graph: lastScenarioData?.request_summary?.context_graph || {},
    }, lastScenarioData?.recommendations?.[0]);
    scenarioStatus.textContent = "Experience memory loaded.";
  } catch (error) {
    showError(error);
  } finally {
    scenarioLoading.classList.add("hidden");
  }
}

scenarioExampleSelect.addEventListener("change", () => {
  const example = selectedExample();
  renderExampleMeta(example);
  scenarioText.value = example.scenario_text;
  updatePayloadPreview();
});

scenarioLoadExampleBtn.addEventListener("click", () => {
  const example = selectedExample();
  scenarioText.value = example.scenario_text;
  updatePayloadPreview();
  runScenario();
});

scenarioText.addEventListener("input", updatePayloadPreview);
scenarioUseLlm.addEventListener("change", updatePayloadPreview);
scenarioUseLlmExplanation.addEventListener("change", updatePayloadPreview);
scenarioRunBtn.addEventListener("click", runScenario);
scenarioModeTabs.forEach(tab => {
  tab.addEventListener("click", () => {
    setActiveMode(tab.dataset.mode);
  });
});

setActiveMode("recommend");
updatePayloadPreview();
loadScenarioExamples().then(() => runScenario());
