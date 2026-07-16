const EMPATHY_PRESETS = {
  family: {
    scenario_text: "Traveling with my 80-year-old grandmother and toddler. Need a rental car for a week-long family trip.",
    destination: "",
    routeMiles: "",
    rentalDays: 7,
  },
  pch: {
    scenario_text: "Road trip along the Pacific Coast Highway, just me and my partner. We want something special for the scenic drive.",
    destination: "Pacific Coast Highway",
    routeMiles: 450,
    rentalDays: 5,
  },
  dorm: {
    scenario_text: "Moving my kid into their college dorm 3 hours away. Need space for boxes, bins, and a mini-fridge.",
    destination: "",
    routeMiles: 180,
    rentalDays: 2,
  },
  denver: {
    scenario_text: "500-mile road trip driving to Denver in winter. Need a safe vehicle for mountain driving.",
    destination: "Denver, CO",
    routeMiles: 500,
    rentalDays: 4,
  },
};
let lastScenarioData = null;
let lastParsedScenarioText = "";
let activeMode = "recommend";

const scenarioText = document.getElementById("scenarioText");
const scenarioUseLlm = document.getElementById("scenarioUseLlm");
const scenarioUseLlmExplanation = document.getElementById("scenarioUseLlmExplanation");
const scenarioRunBtn = document.getElementById("scenarioRunBtn");
const scenarioStatus = document.getElementById("scenarioStatus");
const scenarioLoading = document.getElementById("scenarioLoading");
const scenarioRecommendation = document.getElementById("scenarioRecommendation");
const parsedContext = document.getElementById("parsedContext");
const technicalExplanation = document.getElementById("technicalExplanation");
const payloadPreview = document.getElementById("scenarioPayloadPreview");
const responsePreview = document.getElementById("scenarioResponsePreview");
const scenarioArchitecturePanels = document.getElementById("scenarioArchitecturePanels");
const scenarioModeTabs = document.querySelectorAll(".scenario-mode-tab");
const empathyControls = document.getElementById("empathyControls");
const empathyResultsSection = document.getElementById("empathyResultsSection");
const empathyDestination = document.getElementById("empathyDestination");
const empathyRouteMiles = document.getElementById("empathyRouteMiles");
const empathyRentalDays = document.getElementById("empathyRentalDays");
const scenarioEmpathyHiddenNeeds = document.getElementById("scenarioEmpathyHiddenNeeds");
const scenarioEmpathyEnrichment = document.getElementById("scenarioEmpathyEnrichment");
const scenarioEmpathyTco = document.getElementById("scenarioEmpathyTco");
const scenarioEmpathyPitch = document.getElementById("scenarioEmpathyPitch");

const { escapeHtml, pct, pretty, renderArchitecturePanels } = window.DemoShared;

function num(value) {
  return Number(value || 0).toFixed(2);
}

function buildPayload() {
  const payload = {
    scenario_text: scenarioText.value.trim(),
    limit: 3,
    use_ai_models: true,
    use_llm: scenarioUseLlm.checked,
    use_llm_explanation: scenarioUseLlmExplanation.checked,
    rental_days: Number(empathyRentalDays.value || 3),
  };
  const destination = empathyDestination.value.trim();
  const routeMiles = empathyRouteMiles.value.trim();
  if (destination) {
    payload.destination = destination;
  }
  if (routeMiles) {
    payload.route_miles = Number(routeMiles);
  }
  return payload;
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
    memory: "Load experience memory",
  };
  scenarioRunBtn.textContent = labels[mode] || "Run";
}

function hasEmpathyInsights(summary) {
  const empathy = summary?.empathy;
  if (!empathy) {
    return false;
  }
  if (empathy.vehicle_recommendation || empathy.active || empathy.insights_available) {
    return true;
  }
  const profile = empathy.hidden_needs || {};
  return Boolean((profile.persona_tags || []).length || (profile.implicit_constraints || []).length);
}

function empathyVehicleRecommendation(summary) {
  return summary?.empathy?.vehicle_recommendation || null;
}

function renderEmpathyVehicleCard(summary) {
  const vehicle = empathyVehicleRecommendation(summary);
  if (!vehicle) {
    return "";
  }
  const tco = vehicle.tco || {};
  const tcoLine = tco.total_trip_cost != null
    ? `<p class="explanation empathy-inline-tco"><strong>TCO:</strong> $${Number(tco.total_trip_cost).toFixed(0)} total`
      + (tco.estimated_fuel_cost ? ` ($${Number(tco.daily_rate_total || 0).toFixed(0)} rental + $${Number(tco.estimated_fuel_cost).toFixed(0)} fuel)` : "")
      + `</p>`
    : "";
  const constraints = (vehicle.satisfied || []).slice(0, 4).map(item => item.replaceAll("_", " ")).join(", ");
  return `
    <article class="empathy-vehicle-rec">
      <p class="eyebrow">Empathy Engine vehicle recommendation</p>
      <div class="offer-header">
        <div>
          <h3>${escapeHtml(vehicle.title || vehicle.candidate_id)}</h3>
          <p>${escapeHtml(vehicle.description || "")}</p>
        </div>
        <strong class="score-badge">${pct(vehicle.match_score || 0)}</strong>
      </div>
      <div class="offer-metrics">
        <div><span>Vehicle ID</span><strong>${escapeHtml(vehicle.candidate_id)}</strong></div>
        <div><span>Empathy match</span><strong>${pct(vehicle.match_score || 0)}</strong>${constraints ? `<small>${escapeHtml(constraints)}</small>` : ""}</div>
      </div>
      <p class="explanation">${escapeHtml(vehicle.pitch || "")}</p>
      ${tcoLine}
    </article>
  `;
}

function applyEmpathyPreset(name) {
  const preset = EMPATHY_PRESETS[name];
  if (!preset) {
    return;
  }
  scenarioText.value = preset.scenario_text;
  empathyDestination.value = preset.destination || "";
  empathyRouteMiles.value = preset.routeMiles === "" ? "" : String(preset.routeMiles);
  empathyRentalDays.value = String(preset.rentalDays);
  updatePayloadPreview();
}

function renderEmpathyPanels(summary, topRec) {
  if (!hasEmpathyInsights(summary)) {
    empathyResultsSection.classList.add("hidden");
    empathyResultsSection.setAttribute("aria-hidden", "true");
    return;
  }

  const empathy = summary.empathy || {};
  empathyResultsSection.classList.remove("hidden");
  empathyResultsSection.setAttribute("aria-hidden", "false");

  const profile = empathy.hidden_needs || {};
  const constraints = profile.implicit_constraints || [];
  const constraintRows = constraints.map(item => `
    <li><strong>${escapeHtml(item.constraint_id.replaceAll("_", " "))}</strong>
    — ${escapeHtml(item.reason || "")}</li>
  `).join("");

  scenarioEmpathyHiddenNeeds.innerHTML = `
    <dl class="empathy-facts">
      <div><dt>Persona</dt><dd>${escapeHtml((profile.persona_tags || []).join(", ") || "None")}</dd></div>
      <div><dt>Standard filter would match</dt><dd>${escapeHtml(profile.standard_filter_match || "Generic category")}</dd></div>
      <div><dt>Confidence</dt><dd>${Math.round(Number(profile.confidence || 0) * 100)}%</dd></div>
      <div><dt>Evidence</dt><dd>${escapeHtml((profile.evidence_phrases || []).join(", ") || "—")}</dd></div>
    </dl>
    <h3 class="empathy-subtitle">Implicit constraints</h3>
    <ul class="empathy-constraint-list">${constraintRows || "<li>No constraints extracted.</li>"}</ul>
  `;

  const enrichment = summary.enrichment || empathy.enrichment || {};
  const weather = enrichment.weather || {};
  const route = enrichment.route || {};
  const stops = (empathy.trip?.stops || []).join(" -> ");
  scenarioEmpathyEnrichment.innerHTML = `
    <dl class="empathy-facts">
      <div><dt>Route</dt><dd>${escapeHtml(empathy.trip?.route_label || route.source || "—")}</dd></div>
      <div><dt>Stops</dt><dd class="empathy-stops">${escapeHtml(stops || "—")}</dd></div>
      <div><dt>Weather forecast</dt><dd>${escapeHtml(weather.forecast || "clear")} (${escapeHtml(weather.source || "stub")})</dd></div>
      <div><dt>Wind</dt><dd>${escapeHtml(weather.wind_mph ?? 0)} mph</dd></div>
      <div><dt>Weather note</dt><dd>${escapeHtml(weather.note || "—")}</dd></div>
      <div><dt>Max elevation</dt><dd>${escapeHtml(route.max_elevation_ft ?? 0)} ft</dd></div>
      <div><dt>Steep grade</dt><dd>${route.steep_grade ? "Yes" : "No"}</dd></div>
      <div><dt>Route distance</dt><dd>${escapeHtml(route.distance_miles ?? empathy.trip?.distance_miles ?? "—")} mi</dd></div>
      <div><dt>Gas price</dt><dd>$${Number(enrichment.gas_price_usd || 0).toFixed(2)}/gal</dd></div>
      <div><dt>Derived constraints</dt><dd>${escapeHtml((enrichment.derived_constraints || []).join(", ") || "—")}</dd></div>
    </dl>
  `;

  const tco = summary.tco || {};
  const comparisons = tco.comparisons || empathy.tco_comparisons || [];
  if (!comparisons.length && topRec?.tco) {
    comparisons.push(topRec.tco);
  }
  if (!comparisons.length) {
    scenarioEmpathyTco.innerHTML = "<p>Add route miles to see fuel and total trip cost.</p>";
  } else {
    const rows = comparisons.map(item => `
      <tr>
        <td>${escapeHtml(item.candidate_id.replaceAll("_", " "))}</td>
        <td>$${Number(item.daily_rate_total || 0).toFixed(0)}</td>
        <td>$${Number(item.estimated_fuel_cost || 0).toFixed(0)}</td>
        <td>$${Number(item.total_trip_cost || 0).toFixed(0)}</td>
        <td>${item.net_savings != null ? `$${Number(item.net_savings).toFixed(0)}` : "—"}</td>
      </tr>
    `).join("");
    scenarioEmpathyTco.innerHTML = `
      <div class="empathy-tco-scroll" tabindex="0" aria-label="Trip cost comparison table">
        <table class="empathy-tco-table">
          <thead>
            <tr>
              <th>Vehicle</th>
              <th>Rental</th>
              <th>Fuel</th>
              <th>Total</th>
              <th>Net vs compact</th>
            </tr>
          </thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
    `;
  }

  const match = topRec?.empathy_match || {};
  const vehicle = empathyVehicleRecommendation(summary) || {};
  const pitch = tco.top_pitch || empathy.empathy_pitch || vehicle.pitch || topRec?.explanation || "";
  scenarioEmpathyPitch.innerHTML = `
    <p class="empathy-top-vehicle"><strong>Empathy vehicle:</strong> ${escapeHtml((vehicle.title || topRec?.candidate?.title || "").replaceAll("_", " "))}</p>
    ${(vehicle.satisfied || match.satisfied || []).length ? `<p><strong>Constraints met:</strong> ${escapeHtml((vehicle.satisfied || match.satisfied || []).map(item => item.replaceAll("_", " ")).join(", "))}</p>` : ""}
    ${(topRec?.enrichment_notes || []).length ? `<p><strong>Enrichment:</strong> ${escapeHtml(topRec.enrichment_notes.join(" "))}</p>` : ""}
    <p>${escapeHtml(pitch)}</p>
  `;
}

function clearEmpathyTripFields() {
  empathyDestination.value = "";
  empathyRouteMiles.value = "";
  empathyRentalDays.value = "3";
}

async function parseScenarioContext() {
  const payload = buildPayload();
  const response = await DemoApi.fetch("/recommend-from-scenario", {
    method: "POST",
    body: JSON.stringify({ ...payload, limit: 1 }),
  });
  if (!response.ok) {
    const body = await response.text();
    throw new Error(`Could not parse scenario (${response.status}): ${body}`);
  }
  const parsed = await response.json();
  lastScenarioData = parsed;
  lastParsedScenarioText = scenarioText.value.trim();
  renderParsedContext(parsed.request_summary);
  return parsed.request_summary.parsed_context;
}

async function ensureParsedContext() {
  const currentText = scenarioText.value.trim();
  const cached = parsedContextFromSummary(lastScenarioData?.request_summary || {});
  if (cached.channel && lastParsedScenarioText === currentText) {
    return cached;
  }
  return parseScenarioContext();
}

function parsedContextFromSummary(summary) {
  return summary?.parsed_context || summary?.context || lastScenarioData?.request_summary?.parsed_context || {};
}

function renderParsedContext(summary) {
  const context = parsedContextFromSummary(summary);
  const nlp = summary.nlp || {};
  const llmStatus = nlp.llm_status || {};
  parsedContext.innerHTML = `
    <div><span>Parser</span><strong>${escapeHtml(pretty(nlp.parser || "unknown"))}</strong></div>
    <div><span>LLM status</span><strong>${escapeHtml(pretty(llmStatus.last_status || (summary.llm_enabled ? "ready" : "not_configured")))}</strong></div>
    <div><span>Channel</span><strong>${escapeHtml(pretty(context.channel))}</strong></div>
    <div><span>Intent</span><strong>${escapeHtml(pretty(context.current_intent))}</strong></div>
    <div><span>Journey</span><strong>${escapeHtml(pretty(context.journey_stage))}</strong></div>
    <div><span>Customer</span><strong>${escapeHtml(context.customer_id || "anonymous")}</strong></div>
    <div><span>Channel fallback</span><strong>${escapeHtml(nlp.demo_channel_fallback ? `${nlp.demo_channel_fallback.from} → ${nlp.demo_channel_fallback.to}` : (nlp.empathy_channel_override ? `${nlp.empathy_channel_override.from} → ${nlp.empathy_channel_override.to}` : "None"))}</strong></div>
    <div><span>LLM fallback</span><strong>${escapeHtml(nlp.llm_fallback ? (nlp.llm_fallback_reason || "Yes") : "No")}</strong></div>
    <div><span>Profile lookup</span><strong>${escapeHtml(pretty((summary.profile || {}).profile_lookup || "not used"))}</strong></div>
    <div><span>Events</span><strong>${escapeHtml((context.session_events || []).join(", "))}</strong></div>
    <div><span>Search terms</span><strong>${escapeHtml((context.search_terms || []).join(", "))}</strong></div>
  `;
}

function renderRecommendation(data) {
  const rec = data.recommendations[0];
  const summary = data.request_summary || {};
  const empathyInsights = hasEmpathyInsights(summary);
  const empathyBadge = empathyInsights
    ? `<span class="example-chip">Empathy-aware</span>`
    : "";
  const empathyMetrics = rec.empathy_match
    ? `<div><span>Empathy match</span><strong>${pct(rec.empathy_match.match_score || 0)}</strong><small>${escapeHtml((rec.empathy_match.satisfied || []).slice(0, 3).join(", ").replaceAll("_", " "))}</small></div>`
    : "";
  const tcoLine = rec.tco?.recommendation_pitch
    ? `<p class="explanation empathy-inline-tco"><strong>TCO:</strong> ${escapeHtml(rec.tco.recommendation_pitch)}</p>`
    : "";

  scenarioRecommendation.innerHTML = `
    <p class="eyebrow">Top recommendation ${empathyBadge}</p>
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
      ${empathyMetrics}
    </div>
    <p class="explanation">${escapeHtml(rec.explanation)}</p>
    ${tcoLine}
    <div class="pill-row">${rec.reason_codes.map(reason => `<span>${escapeHtml(reason.replaceAll("_", " "))}</span>`).join("")}</div>
    ${renderEmpathyVehicleCard(summary)}
    <div class="feedback-row">
      <span class="feedback-label">Capture feedback to EML + TKGE timeline</span>
      <div class="feedback-actions">
        <button type="button" class="feedback-btn" data-feedback="click">Click</button>
        <button type="button" class="feedback-btn is-positive" data-feedback="convert">Convert</button>
        <button type="button" class="feedback-btn is-muted" data-feedback="dismiss">Dismiss</button>
      </div>
      <p id="scenarioFeedbackStatus" class="feedback-status">Send feedback to update trust, fatigue, and the TKGE timeline.</p>
    </div>
  `;

  renderEmpathyPanels(summary, rec);

  scenarioRecommendation.querySelectorAll("[data-feedback]").forEach(button => {
    button.addEventListener("click", () => submitScenarioFeedback(button.dataset.feedback));
  });
}

async function submitScenarioFeedback(kind) {
  if (!lastScenarioData?.recommendations?.length) {
    return;
  }

  const rec = lastScenarioData.recommendations[0];
  const context = parsedContextFromSummary(lastScenarioData.request_summary);
  const statusEl = document.getElementById("scenarioFeedbackStatus");
  const converted = kind === "convert";
  const eventType = kind === "dismiss" ? "dismiss" : "click";

  const payload = {
    anonymous_id: context.anonymous_id,
    customer_id: context.customer_id,
    recommendation_id: rec.candidate.id,
    channel: context.channel,
    event_type: eventType,
    converted,
    revenue: converted ? Number(rec.ai_score.outcome_simulation.revenue_impact || 0) : 0,
    context_snapshot: {
      scenario_text: scenarioText.value.trim(),
      mode: "scenario-demo",
    },
  };

  if (statusEl) {
    statusEl.textContent = "Sending feedback...";
  }

  try {
    const response = await DemoApi.fetch("/feedback", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    if (!response.ok) {
      throw new Error(`POST /feedback returned ${response.status}`);
    }
    const data = await response.json();
    const updatedSummary = {
      ...lastScenarioData.request_summary,
      context_graph: data.context_graph || lastScenarioData.request_summary.context_graph,
      experience_memory: {
        before: lastScenarioData.request_summary.experience_memory?.after
          || lastScenarioData.request_summary.experience_memory?.before
          || {},
        after: data.experience_memory || {},
      },
    };
    lastScenarioData = {
      ...lastScenarioData,
      request_summary: updatedSummary,
    };
    if (statusEl) {
      statusEl.textContent = `Feedback recorded (${eventType}${converted ? ", converted" : ""}). Total events: ${data.feedback_count}.`;
    }
    renderArchitecturePanels(scenarioArchitecturePanels, updatedSummary, rec);
    scenarioStatus.textContent = "Feedback captured. TKGE timeline updated.";
  } catch (error) {
    if (statusEl) {
      statusEl.textContent = error.message || "Feedback failed.";
    }
  }
}

function renderTechnicalExplanation(data) {
  const summary = data.request_summary || {};
  const context = summary.parsed_context || {};
  const nlp = summary.nlp || {};
  const rec = data.recommendations?.[0];
  if (!rec) {
    technicalExplanation.textContent = "No recommendation was returned for this scenario.";
    return;
  }
  const candidate = rec.candidate;
  const eds = rec.eds_score;
  const ai = rec.ai_score;
  const tapl = ai.tapl;
  const outcome = ai.outcome_simulation;
  const empathy = summary.empathy || {};
  const empathyVehicle = empathyVehicleRecommendation(summary);
  const empathyInsights = hasEmpathyInsights(summary);
  const empathyArticle = empathyInsights ? `
      <article>
        <span>5. Empathy Engine</span>
        <p>Every scenario includes an empathy vehicle recommendation with hidden needs, enrichment, and optional TCO.</p>
        <dl>
          <div><dt>Persona</dt><dd>${escapeHtml((empathy.hidden_needs?.persona_tags || []).join(", ") || "none")}</dd></div>
          <div><dt>Standard filter</dt><dd>${escapeHtml(empathy.hidden_needs?.standard_filter_match || "n/a")}</dd></div>
          <div><dt>Empathy vehicle</dt><dd>${escapeHtml(empathyVehicle?.candidate_id || rec.candidate.id)}</dd></div>
          <div><dt>Empathy match</dt><dd>${num(empathyVehicle?.match_score ?? rec.empathy_match?.match_score ?? 0)}</dd></div>
          <div><dt>Constraints met</dt><dd>${escapeHtml((empathyVehicle?.satisfied || rec.empathy_match?.satisfied || []).join(", ") || "none")}</dd></div>
          <div><dt>Weather</dt><dd>${escapeHtml(summary.enrichment?.weather?.forecast || "clear")}</dd></div>
          <div><dt>TCO total</dt><dd>${(empathyVehicle?.tco?.total_trip_cost ?? rec.tco?.total_trip_cost) != null ? `$${Number(empathyVehicle?.tco?.total_trip_cost ?? rec.tco?.total_trip_cost).toFixed(0)}` : "n/a"}</dd></div>
        </dl>
      </article>
  ` : "";

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
      ${empathyArticle}
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
  empathyResultsSection.classList.add("hidden");
  empathyResultsSection.setAttribute("aria-hidden", "true");
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
  scenarioStatus.textContent = "Parsing scenario and building unified recommendation...";

  try {
    const response = await DemoApi.fetch("/recommend-from-scenario", {
      method: "POST",
      body: JSON.stringify(payload)
    });
    if (!response.ok) {
      const body = await response.text();
      throw new Error(`POST /recommend-from-scenario returned ${response.status}: ${body}`);
    }
    const data = await response.json();
    lastScenarioData = data;
    lastParsedScenarioText = scenarioText.value.trim();
    responsePreview.textContent = JSON.stringify(data, null, 2);
    renderParsedContext(data.request_summary);
    if (!data.recommendations.length) {
      throw new Error("The API returned no recommendations for this scenario.");
    }
    renderRecommendation(data);
    renderTechnicalExplanation(data);
    renderArchitecturePanels(scenarioArchitecturePanels, data.request_summary, data.recommendations[0]);
    const parser = pretty((data.request_summary.nlp || {}).parser || "unknown");
    if (hasEmpathyInsights(data.request_summary)) {
      scenarioStatus.textContent = `Unified recommendation ready (${parser} + empathy vehicle).`;
    } else {
      scenarioStatus.textContent = `Done. Parsed with ${parser}.`;
    }
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
    const context = await ensureParsedContext();

    const payload = { context };
    payloadPreview.textContent = JSON.stringify(payload, null, 2);
    scenarioStatus.textContent = "Simulating all candidate outcomes...";

    const response = await DemoApi.fetch("/simulate", {
      method: "POST",
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
    const context = await ensureParsedContext();

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

scenarioText.addEventListener("input", updatePayloadPreview);
scenarioUseLlm.addEventListener("change", updatePayloadPreview);
scenarioUseLlmExplanation.addEventListener("change", updatePayloadPreview);
[empathyDestination, empathyRouteMiles, empathyRentalDays].forEach(input => {
  input.addEventListener("input", updatePayloadPreview);
});
document.querySelectorAll(".empathy-preset").forEach(button => {
  button.addEventListener("click", () => {
    applyEmpathyPreset(button.dataset.preset);
    runScenario();
  });
});
scenarioRunBtn.addEventListener("click", runScenario);
scenarioModeTabs.forEach(tab => {
  tab.addEventListener("click", () => {
    setActiveMode(tab.dataset.mode);
    updatePayloadPreview();
  });
});

const initialMode = new URLSearchParams(window.location.search).get("mode");
if (initialMode === "empathy") {
  applyEmpathyPreset("family");
}
setActiveMode("recommend");
updatePayloadPreview();
runScenario();
