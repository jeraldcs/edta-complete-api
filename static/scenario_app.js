let lastScenarioData = null;
let lastParsedScenarioText = "";
let demoReady = false;
let activeScenarioKey = "loyalty";

const DEMO_SCENARIOS = {
  loyalty: {
    label: "Family loyalty (cust-789)",
    text: "cust-789 is a preferred loyalty member booking a family SUV rental at SFO. She checked availability and started booking. Personalization consent is true.",
  },
  winter: {
    label: "Winter Denver AWD",
    text: "I am planning a 500-mile one-way road trip to Denver, Colorado during the winter season. The journey may include mountain roads, snow-covered roads, and icy pavement. I will be traveling with my spouse and luggage. My highest priorities are passenger safety, winter traction, and reliability. Please recommend the most suitable vehicle for this trip.",
  },
  family_vacation: {
    label: "Family vacation (Orlando)",
    text: "I am planning a 1,200-mile family vacation from New Jersey to Orlando, Florida during the summer. We are a family of five with three children, multiple suitcases, a stroller, and sports equipment. Comfort, cargo capacity, fuel efficiency, and advanced driver assistance features are my highest priorities.",
  },
  business: {
    label: "Business executive",
    text: "I travel frequently for business, averaging 35,000 highway miles annually. Most trips involve airport transfers, interstate driving, and meetings with clients. I want a premium vehicle with excellent comfort, advanced technology, outstanding safety, and a professional appearance.",
  },
  no_consent: {
    label: "No consent",
    text: "Known customer cust-789 is booking a family SUV rental at SFO. She checked availability and started booking. Personalization consent is false.",
  },
  fatigue: {
    label: "High fatigue",
    text: "Known customer cust-789 is booking a family SUV rental at SFO. Fatigue count is 8 and she has seen many promotional ads today. Personalization consent is true.",
  },
  // Comparison chips: distinct texts so detectScenarioKey stays unique; same Recommend API as other chips.
  compare_rules: {
    label: "Rules-era upsell",
    text: "Comparison demo — rules-era booking path: preferred member cust-789 searched SUV availability at SFO and started booking a family rental. Personalization consent is true. Traditional rules would always fire an SUV upgrade; EDTA also ranks a fit vehicle but returns TAPL, EDS, and explanation.",
  },
  compare_ranker: {
    label: "ML ranker era",
    text: "Comparison demo — monolithic ranker contrast: planning a long family vacation with five travelers, three children, suitcases, a stroller, and sports gear. A click-optimized ranker might over-weight premium similarity; EDTA blends empathy constraints and expected outcome, not similarity alone.",
  },
  compare_llm: {
    label: "LLM bolt-on risk",
    text: "Comparison demo — ambiguous chatbot request: I need something comfortable for a trip next week, not sure which car. Traditional LLM bolt-ons pick an offer with opaque cost; EDTA exposes inference tier and still applies TAPL governance.",
  },
  compare_edta: {
    label: "EDTA governed",
    text: "Comparison demo — EDTA governed baseline: cust-789 preferred loyalty member booking a family SUV rental at SFO after checking availability. Personalization consent is true. Show trust-aware ranking with empathy fit, outcome simulation, and auditable explanation.",
  },
  hosted_slm: {
    label: "Hosted SLM",
    text: "Hosted SLM demo — I need something comfortable for a trip next week, not sure which car. Maybe family-friendly? Budget is flexible but I care about safety.",
    options: {
      inference_mode: "slm",
      use_slm: true,
      use_llm_explanation: true,
    },
  },
  rules_vs_slm: {
    label: "Rules vs SLM",
    text: "Rules vs hosted SLM demo — I need something comfortable for a trip next week, not sure which car. Maybe family-friendly? Budget is flexible but I care about safety.",
    options: {
      inference_mode: "slm",
      use_slm: true,
      use_llm_explanation: true,
      compare_rules_vs_slm: true,
    },
  },
};

const COMPARE_NARRATIVES = {
  compare_rules: {
    title: "Traditional vs EDTA — Rules-era",
    traditional: "If/then: SUV search → always show upgrade. Fast and auditable, but no EDS/TAPL story in the response.",
    edta: "Same booking intent, plus TAPL action, EDS breakdown, empathy fit, and explanation in the API response.",
  },
  compare_ranker: {
    title: "Traditional vs EDTA — ML ranker era",
    traditional: "One model score (often similarity/CTR) decides the offer; journey and constraints are secondary.",
    edta: "Empathy constraints + OSE outcome scores compete with semantic similarity — check Outcome vs Semantic in the meters.",
  },
  compare_llm: {
    title: "Traditional vs EDTA — LLM bolt-on risk",
    traditional: "Ambiguous text → LLM picks an offer; cost, tier, and governance are hard to audit.",
    edta: "Inference tier is visible; TAPL still governs the final action; LLM remains optional and budget-gated.",
  },
  compare_edta: {
    title: "Traditional vs EDTA — EDTA governed",
    traditional: "Traditional stacks stop at candidate ID + score.",
    edta: "Full stack: consent-aware TAPL, EML trust, empathy profile, OSE outcome, and architecture panels.",
  },
};

const TRY_NEXT = {
  loyalty: [
    { key: "no_consent", label: "Next: No consent" },
    { key: "compare_rules", label: "Compare vs traditional" },
  ],
  winter: [
    { key: "family_vacation", label: "Next: Family vacation" },
    { key: "loyalty", label: "Compare loyalty baseline" },
  ],
  family_vacation: [
    { key: "business", label: "Next: Business executive" },
    { key: "compare_ranker", label: "Compare ML ranker era" },
  ],
  business: [
    { key: "loyalty", label: "Next: Family loyalty" },
    { key: "no_consent", label: "Try No consent" },
  ],
  no_consent: [
    { key: "fatigue", label: "Next: High fatigue" },
    { key: "loyalty", label: "Back to loyalty baseline" },
  ],
  fatigue: [
    { key: "no_consent", label: "Compare No consent" },
    { key: "loyalty", label: "Back to loyalty baseline" },
  ],
  compare_rules: [
    { key: "compare_ranker", label: "Next: ML ranker era" },
    { key: "compare_edta", label: "See EDTA governed" },
  ],
  compare_ranker: [
    { key: "compare_llm", label: "Next: LLM bolt-on risk" },
    { key: "compare_edta", label: "See EDTA governed" },
  ],
  compare_llm: [
    { key: "compare_edta", label: "Next: EDTA governed" },
    { key: "no_consent", label: "Try No consent" },
  ],
  compare_edta: [
    { key: "compare_rules", label: "Replay Rules-era" },
    { key: "fatigue", label: "Try High fatigue" },
  ],
  hosted_slm: [
    { key: "no_consent", label: "Next: No consent (TAPL still wins)" },
    { key: "fatigue", label: "Next: High fatigue" },
  ],
  rules_vs_slm: [
    { key: "hosted_slm", label: "Replay Hosted SLM" },
    { key: "no_consent", label: "Next: No consent" },
  ],
};

let previousRunSnapshot = null;
let lastTaplAction = null;
let lastRulesVsSlmCompare = null;

let scenarioText = null;
let scenarioRunBtn = null;
let scenarioForm = null;
let scenarioRunError = null;
let scenarioColdStart = null;
let scenarioLoading = null;
let scenarioRecommendation = null;
let technicalExplanation = null;
let payloadPreview = null;
let responsePreview = null;
let scenarioArchitecturePanels = null;
let empathyResultsSection = null;
let scenarioEmpathyHiddenNeeds = null;
let scenarioEmpathyEnrichment = null;
let scenarioEmpathyTco = null;
let scenarioEmpathyPitch = null;
let scenarioResultsSection = null;
let demoWakeBanner = null;
let tryNextSuggestions = null;
let copyDemoLinkBtn = null;

const shared = window.DemoShared || {};
const escapeHtml = shared.escapeHtml || ((value) => String(value ?? ""));
const pct = shared.pct || ((value) => `${Math.round(Number(value || 0) * 100)}%`);
const pretty = shared.pretty || ((value) => String(value || "").replaceAll("_", " "));
const taplPlainLabel = shared.taplPlainLabel || ((action) => pretty(action));
const renderArchitecturePanels = shared.renderArchitecturePanels || (() => {});
const renderTaplBadge = shared.renderTaplBadge || ((action) => escapeHtml(pretty(action)));
const scoreMeter = shared.scoreMeter || (() => "");
const vehicleGlyph = shared.vehicleGlyph || (() => "🚗");

function num(value) {
  return Number(value || 0).toFixed(2);
}

function activeScenarioOptions() {
  const key = activeScenarioKey || detectScenarioKey(scenarioText?.value || "");
  return (key && DEMO_SCENARIOS[key]?.options) || {};
}

function buildPayload(overrides = {}) {
  const options = activeScenarioOptions();
  return {
    scenario_text: (scenarioText?.value || "").trim(),
    limit: 3,
    use_ai_models: true,
    use_llm: false,
    use_slm: Boolean(options.use_slm),
    use_llm_explanation: Boolean(options.use_llm_explanation),
    inference_mode: options.inference_mode || "auto",
    rental_days: 3,
    ...overrides,
  };
}

function updatePayloadPreview() {
  if (payloadPreview) {
    payloadPreview.textContent = JSON.stringify(buildPayload(), null, 2);
  }
}

function setWakeBanner(message) {
  if (!demoWakeBanner) {
    return;
  }
  if (message) {
    demoWakeBanner.textContent = message;
    demoWakeBanner.classList.remove("hidden");
  } else {
    demoWakeBanner.classList.add("hidden");
  }
}

function setColdStartMessage(message) {
  if (message) {
    setWakeBanner(message);
    if (scenarioColdStart) {
      scenarioColdStart.textContent = message;
      scenarioColdStart.classList.remove("hidden");
    }
  } else {
    setWakeBanner("");
    if (scenarioColdStart) {
      scenarioColdStart.textContent = "";
      scenarioColdStart.classList.add("hidden");
    }
  }
}

function setRunError(message) {
  if (!scenarioRunError) {
    return;
  }
  if (message) {
    scenarioRunError.textContent = message;
    scenarioRunError.classList.remove("hidden");
  } else {
    scenarioRunError.textContent = "";
    scenarioRunError.classList.add("hidden");
  }
}

function setRunning(isRunning) {
  if (scenarioRunBtn) {
    scenarioRunBtn.disabled = isRunning;
    scenarioRunBtn.textContent = isRunning ? "Running..." : "Recommend";
  }
  const mobileBtn = document.getElementById("scenarioMobileRunBtn");
  if (mobileBtn) {
    mobileBtn.disabled = isRunning;
    mobileBtn.textContent = isRunning ? "Running..." : "Recommend";
  }
  if (scenarioLoading) {
    scenarioLoading.classList.toggle("hidden", !isRunning);
  }
  if (isRunning && !scenarioColdStart?.textContent) {
    setWakeBanner("Waking demo service… first request may take up to a minute.");
  }
  if (!isRunning) {
    setWakeBanner("");
  }
}

function pulseChip(key) {
  if (!key) {
    return;
  }
  const button = document.querySelector(`.scenario-chip-btn[data-scenario-key="${key}"]`);
  if (!button) {
    return;
  }
  button.classList.remove("is-chip-pulse");
  void button.offsetWidth;
  button.classList.add("is-chip-pulse");
}

function syncScenarioUrl(key) {
  if (!key || !window.history?.replaceState) {
    return;
  }
  const url = new URL(window.location.href);
  url.searchParams.set("scenario", key);
  window.history.replaceState({}, "", url);
}

function readScenarioFromUrl() {
  const key = new URLSearchParams(window.location.search).get("scenario");
  if (key && DEMO_SCENARIOS[key]) {
    return key;
  }
  return null;
}

async function copyDemoLink() {
  const key = activeScenarioKey || detectScenarioKey(scenarioText?.value || "") || "loyalty";
  const url = new URL(window.location.href);
  url.searchParams.set("scenario", key);
  const link = url.toString();
  try {
    await navigator.clipboard.writeText(link);
    if (copyDemoLinkBtn) {
      const original = copyDemoLinkBtn.textContent;
      copyDemoLinkBtn.textContent = "Link copied!";
      window.setTimeout(() => {
        copyDemoLinkBtn.textContent = original;
      }, 1800);
    }
  } catch (_error) {
    window.prompt("Copy this demo link:", link);
  }
}

function updateActiveScenarioChip(key) {
  activeScenarioKey = key || null;
  document.querySelectorAll(".scenario-chip-btn").forEach((button) => {
    const matches = key && button.dataset.scenarioKey === key;
    button.classList.toggle("is-active", Boolean(matches));
  });
}

function detectScenarioKey(text) {
  const normalized = String(text || "").trim().replace(/\s+/g, " ");
  for (const [key, scenario] of Object.entries(DEMO_SCENARIOS)) {
    if (normalized === scenario.text.trim().replace(/\s+/g, " ")) {
      return key;
    }
  }
  return null;
}

function applyScenarioChip(key, { autoRun = false } = {}) {
  const scenario = DEMO_SCENARIOS[key];
  if (!scenario || !scenarioText) {
    return;
  }
  scenarioText.value = scenario.text;
  updateActiveScenarioChip(key);
  pulseChip(key);
  syncScenarioUrl(key);
  updatePayloadPreview();
  setRunError("");
  if (autoRun) {
    runScenario();
  }
}

function bindScenarioChips() {
  document.querySelectorAll(".scenario-chip-btn").forEach((button) => {
    button.addEventListener("click", () => {
      const key = button.dataset.scenarioKey;
      if (!key) {
        return;
      }
      applyScenarioChip(key, { autoRun: true });
    });
  });
}

function scrollToResults() {
  if (scenarioResultsSection) {
    scenarioResultsSection.scrollIntoView({ behavior: "smooth", block: "start" });
  }
}

function validateScenarioText(text) {
  const trimmed = (text || "").trim();
  if (!trimmed) {
    return "Enter a scenario description before running Recommend.";
  }
  if (trimmed.length < 10) {
    return "Scenario text must be at least 10 characters.";
  }
  if (trimmed.length > 4000) {
    return "Scenario text must be 4000 characters or fewer.";
  }
  return "";
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

function renderAlternateEmpathyVehicle(summary, topCandidateId) {
  const vehicle = empathyVehicleRecommendation(summary);
  if (!vehicle || vehicle.candidate_id === topCandidateId) {
    return "";
  }
  const constraints = (vehicle.satisfied || []).slice(0, 3).map(item => item.replaceAll("_", " ")).join(", ");
  return `
    <aside class="hero-alt-vehicle">
      <p class="eyebrow">Also considered (empathy fit)</p>
      <p><strong>${escapeHtml(vehicle.title || vehicle.candidate_id)}</strong> — ${pct(vehicle.match_score || 0)} empathy match${constraints ? ` · ${escapeHtml(constraints)}` : ""}</p>
    </aside>
  `;
}

function pulseOfferCard() {
  const card = document.getElementById("scenarioOfferCard");
  if (!card) {
    return;
  }
  card.classList.remove("is-ready");
  void card.offsetWidth;
  card.classList.add("is-ready");
}

function renderEmpathyVehicleCard(_summary) {
  return "";
}

function renderEmpathyPanels(summary, topRec) {
  if (!empathyResultsSection) {
    return;
  }
  if (!hasEmpathyInsights(summary)) {
    empathyResultsSection.classList.add("hidden");
    empathyResultsSection.setAttribute("aria-hidden", "true");
    return;
  }

  const empathy = summary.empathy || {};
  empathyResultsSection.classList.remove("hidden");
  empathyResultsSection.setAttribute("aria-hidden", "false");

  const profile = empathy.hidden_needs || {};
  const enrichment = summary.enrichment || empathy.enrichment || {};
  const constraints = [...(profile.implicit_constraints || [])];
  const seenConstraintIds = new Set(
    constraints.map((item) => item.constraint_id).filter(Boolean),
  );
  for (const constraintId of enrichment.derived_constraints || []) {
    if (!constraintId || seenConstraintIds.has(constraintId)) {
      continue;
    }
    seenConstraintIds.add(constraintId);
    constraints.push({
      constraint_id: constraintId,
      reason: "Derived from weather/route enrichment",
      source: "enrichment",
    });
  }
  const constraintRows = constraints.map(item => `
    <li><strong>${escapeHtml(item.constraint_id.replaceAll("_", " "))}</strong>
    — ${escapeHtml(item.reason || "")}${item.source === "enrichment" ? " <em>(enrichment)</em>" : ""}</li>
  `).join("");
  const vehicle = empathyVehicleRecommendation(summary) || {};
  const personaLabel = (profile.persona_tags || []).join(", ")
    || (constraints.length ? "Weather / route driven" : "None");

  if (scenarioEmpathyHiddenNeeds) {
    scenarioEmpathyHiddenNeeds.innerHTML = `
      <dl class="empathy-facts">
        <div><dt>Persona</dt><dd>${escapeHtml(personaLabel)}</dd></div>
        <div><dt>Standard filter would match</dt><dd>${escapeHtml(profile.standard_filter_match || "Generic category")}</dd></div>
        <div><dt>Confidence</dt><dd>${Math.round(Number(profile.confidence || vehicle.match_score || 0) * 100)}%</dd></div>
        <div><dt>Evidence</dt><dd>${escapeHtml((profile.evidence_phrases || []).join(", ") || (enrichment.weather?.note || "—"))}</dd></div>
        <div><dt>Empathy vehicle</dt><dd>${escapeHtml((vehicle.title || vehicle.candidate_id || "—").toString().replaceAll("_", " "))}</dd></div>
      </dl>
      <h3 class="empathy-subtitle">Implicit constraints</h3>
      <ul class="empathy-constraint-list">${constraintRows || "<li>No constraints extracted.</li>"}</ul>
    `;
  }

  const weather = enrichment.weather || {};
  const route = enrichment.route || {};
  const stops = (empathy.trip?.stops || []).join(" -> ");
  const tripMiles = empathy.trip?.distance_miles ?? route.distance_miles;
  if (scenarioEmpathyEnrichment) {
    scenarioEmpathyEnrichment.innerHTML = `
      <dl class="empathy-facts">
        <div><dt>Route</dt><dd>${escapeHtml(empathy.trip?.route_label || route.source || "—")}</dd></div>
        <div><dt>Stops</dt><dd class="empathy-stops">${escapeHtml(stops || "—")}</dd></div>
        <div><dt>Weather forecast</dt><dd>${escapeHtml(weather.forecast || "clear")} (${escapeHtml(weather.source || "stub")})</dd></div>
        <div><dt>Wind</dt><dd>${escapeHtml(weather.wind_mph ?? 0)} mph</dd></div>
        <div><dt>Weather note</dt><dd>${escapeHtml(weather.note || "—")}</dd></div>
        <div><dt>Max elevation</dt><dd>${escapeHtml(route.max_elevation_ft ?? 0)} ft</dd></div>
        <div><dt>Steep grade</dt><dd>${route.steep_grade ? "Yes" : "No"}</dd></div>
        <div><dt>Route distance</dt><dd>${escapeHtml(tripMiles ?? "—")} mi</dd></div>
        <div><dt>Gas price</dt><dd>$${Number(enrichment.gas_price_usd || 0).toFixed(2)}/gal</dd></div>
        <div><dt>Derived constraints</dt><dd>${escapeHtml((enrichment.derived_constraints || []).join(", ") || "—")}</dd></div>
      </dl>
    `;
  }

  const tco = summary.tco || {};
  const comparisons = [...(tco.comparisons || empathy.tco_comparisons || [])];
  if (!comparisons.length && topRec?.tco) {
    comparisons.push(topRec.tco);
  }
  if (scenarioEmpathyTco) {
    if (!comparisons.length) {
      scenarioEmpathyTco.innerHTML = "<p>Add route miles to see fuel and total trip cost.</p>";
    } else {
      const rows = comparisons.map(item => `
        <tr>
          <td>${escapeHtml(String(item.candidate_id || "").replaceAll("_", " "))}</td>
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
  }

  const match = topRec?.empathy_match || {};
  const pitch = tco.top_pitch || empathy.empathy_pitch || vehicle.pitch || topRec?.explanation || "";
  if (scenarioEmpathyPitch) {
    scenarioEmpathyPitch.innerHTML = `
      <p class="empathy-top-vehicle"><strong>Empathy vehicle:</strong> ${escapeHtml((vehicle.title || topRec?.candidate?.title || "").replaceAll("_", " "))}</p>
      ${(vehicle.satisfied || match.satisfied || []).length ? `<p><strong>Constraints met:</strong> ${escapeHtml((vehicle.satisfied || match.satisfied || []).map(item => item.replaceAll("_", " ")).join(", "))}</p>` : ""}
      ${(topRec?.enrichment_notes || []).length ? `<p><strong>Enrichment:</strong> ${escapeHtml(topRec.enrichment_notes.join(" "))}</p>` : ""}
      <p>${escapeHtml(pitch)}</p>
    `;
  }
}

function parsedContextFromSummary(summary) {
  return summary?.parsed_context || summary?.context || lastScenarioData?.request_summary?.parsed_context || {};
}

function consentLabelFromContext(context) {
  const consent = context?.consent?.personalization;
  if (consent === true) {
    return "On";
  }
  if (consent === false) {
    return "Off";
  }
  return "—";
}

function captureRunSnapshot(data) {
  const rec = data?.recommendations?.[0];
  if (!rec) {
    return null;
  }
  const summary = data.request_summary || {};
  const context = parsedContextFromSummary(summary);
  const ai = rec.ai_score || {};
  return {
    scenarioKey: activeScenarioKey || detectScenarioKey(summary.scenario_text || scenarioText?.value || ""),
    consent: consentLabelFromContext(context),
    taplAction: ai.tapl?.action || "show",
    trust: Number(ai.tapl?.trust_score || 0),
    fatigue: Number(ai.tapl?.fatigue_score || 0),
    finalScore: Number(ai.final_hybrid_score || 0),
    vehicle: rec.candidate?.id || "",
  };
}

function renderHeroContextStrip(summary) {
  const context = parsedContextFromSummary(summary);
  const profile = summary.scenario_profile || {};
  return `
    <div class="hero-context-strip" aria-label="Parsed scenario context">
      <span>Channel <strong>${escapeHtml(pretty(context.channel))}</strong></span>
      <span>Intent <strong>${escapeHtml(pretty(context.current_intent))}</strong></span>
      <span>Journey <strong>${escapeHtml(pretty(context.journey_stage))}</strong></span>
      ${profile.profile_id ? `<span>Profile <strong>${escapeHtml(profile.profile_id.replaceAll("_", " "))}</strong></span>` : ""}
      <span>Consent <strong>${escapeHtml(consentLabelFromContext(context))}</strong></span>
    </div>
  `;
}

function renderCompareNarrative(key) {
  const narrative = COMPARE_NARRATIVES[key];
  if (!narrative) {
    return "";
  }
  return `
    <aside class="compare-narrative-strip" aria-label="Traditional versus EDTA comparison">
      <span class="compare-narrative-title">${escapeHtml(narrative.title)}</span>
      <div class="compare-narrative-grid">
        <div class="compare-narrative-col compare-narrative-traditional">
          <span class="compare-narrative-label">Traditional</span>
          <p>${escapeHtml(narrative.traditional)}</p>
        </div>
        <div class="compare-narrative-col compare-narrative-edta">
          <span class="compare-narrative-label">EDTA</span>
          <p>${escapeHtml(narrative.edta)}</p>
        </div>
      </div>
    </aside>
  `;
}

function isHostedSlmResponse(summary) {
  return (summary?.inference?.sub_source || "") === "slm_endpoint";
}

function inferenceBadgeHtml(summary) {
  const inference = summary?.inference || {};
  const sub = inference.sub_source || "";
  const slmEngine = summary?.llm_status?.slm_engine || {};
  const model = slmEngine.model || slmEngine.remote?.model || "";
  if (sub === "slm_endpoint") {
    return `<span class="hero-badge hero-badge-slm">Hosted SLM${model ? ` · ${escapeHtml(model)}` : ""}</span>`;
  }
  if (sub === "rules_fallback" || summary?.inference_mode === "rules" || inference.tier === "rules") {
    return `<span class="hero-badge hero-badge-rules">Rules tier</span>`;
  }
  if (sub === "distilled_pattern") {
    return `<span class="hero-badge hero-badge-slm">Distilled SLM</span>`;
  }
  return "";
}

function captureInferenceCompareSnapshot(data) {
  const rec = data?.recommendations?.[0];
  if (!rec) {
    return null;
  }
  const summary = data.request_summary || {};
  const inference = summary.inference || {};
  const context = summary.parsed_context || {};
  return {
    intent: context.current_intent || inference.intent?.label || rec.ai_score?.intent?.label || "unknown",
    journey: context.journey_stage || inference.journey_stage?.label || "unknown",
    subSource: inference.sub_source || inference.tier || "unknown",
    vehicle: rec.candidate?.id || "",
    explanationSource: rec.explanation_source || "local",
    finalScore: Number(rec.ai_score?.final_hybrid_score || 0),
    taplAction: rec.ai_score?.tapl?.action || "show",
  };
}

function renderRulesVsSlmStrip(compare) {
  if (!compare?.rules || !compare?.slm) {
    return "";
  }
  const rules = compare.rules;
  const slm = compare.slm;
  return `
    <aside class="slm-compare-strip" aria-label="Rules versus hosted SLM comparison">
      <span class="slm-compare-title">Rules vs Hosted SLM</span>
      <div class="slm-compare-grid">
        <div class="slm-compare-col">
          <span class="slm-compare-label">Rules</span>
          <p><strong>Intent</strong> ${escapeHtml(pretty(rules.intent))}</p>
          <p><strong>Source</strong> ${escapeHtml(pretty(rules.subSource))}</p>
          <p><strong>Vehicle</strong> ${escapeHtml(pretty(rules.vehicle))}</p>
          <p><strong>Explanation</strong> ${escapeHtml(pretty(rules.explanationSource))}</p>
          <p><strong>TAPL</strong> ${escapeHtml(taplPlainLabel(rules.taplAction))}</p>
        </div>
        <div class="slm-compare-col slm-compare-hosted">
          <span class="slm-compare-label">Hosted SLM</span>
          <p><strong>Intent</strong> ${escapeHtml(pretty(slm.intent))}</p>
          <p><strong>Source</strong> ${escapeHtml(pretty(slm.subSource))}</p>
          <p><strong>Vehicle</strong> ${escapeHtml(pretty(slm.vehicle))}</p>
          <p><strong>Explanation</strong> ${escapeHtml(pretty(slm.explanationSource))}</p>
          <p><strong>TAPL</strong> ${escapeHtml(taplPlainLabel(slm.taplAction))}</p>
        </div>
      </div>
      <p class="slm-compare-note">Same scenario text on both legs. Enrichment can change intent parsing; TAPL still owns consent and fatigue.</p>
    </aside>
  `;
}

function renderGovernancePunchline(scenarioKey, summary) {
  if (!["hosted_slm", "rules_vs_slm"].includes(scenarioKey)) {
    return "";
  }
  if (!isHostedSlmResponse(summary)) {
    return `
      <aside class="governance-punchline governance-punchline-soft" aria-label="Hosted SLM status">
        <span class="governance-punchline-title">Hosted SLM not confirmed on this run</span>
        <p>Check Technical details for <code>inference.sub_source</code>. If you see <code>rules_fallback</code>, remote SLM is disabled or unavailable — TAPL still applies.</p>
      </aside>
    `;
  }
  return `
    <aside class="governance-punchline" aria-label="Governance still applies after SLM">
      <span class="governance-punchline-title">SLM enriched the ask — TAPL still owns the offer</span>
      <p>Hosted SLM helped parse intent and explain the pick. Try <strong>No consent</strong> or <strong>High fatigue</strong> next: enrichment does not override trust policy.</p>
    </aside>
  `;
}

function renderGovernanceDiff(previous, current) {
  if (!previous || !current) {
    return "";
  }
  const rows = [];
  if (previous.consent !== current.consent) {
    rows.push({ label: "Consent", from: previous.consent, to: current.consent });
  }
  if (previous.taplAction !== current.taplAction) {
    rows.push({
      label: "Trust policy",
      from: taplPlainLabel(previous.taplAction),
      to: taplPlainLabel(current.taplAction),
    });
  }
  if (previous.vehicle !== current.vehicle && previous.vehicle && current.vehicle) {
    rows.push({
      label: "Top vehicle",
      from: previous.vehicle.replaceAll("_", " "),
      to: current.vehicle.replaceAll("_", " "),
    });
  }
  const scoreDelta = Math.round((current.finalScore - previous.finalScore) * 100);
  if (Math.abs(scoreDelta) >= 1) {
    rows.push({
      label: "Final score",
      from: pct(previous.finalScore),
      to: pct(current.finalScore),
      delta: scoreDelta,
    });
  }
  if (!rows.length) {
    return "";
  }
  const items = rows.map((row) => {
    const delta = row.delta != null
      ? `<span class="governance-diff-delta ${row.delta >= 0 ? "is-up" : "is-down"}">${row.delta >= 0 ? "+" : ""}${row.delta} pts</span>`
      : "";
    return `
      <div class="governance-diff-item">
        <span class="governance-diff-label">${escapeHtml(row.label)}</span>
        <span class="governance-diff-values">${escapeHtml(String(row.from))} → <strong>${escapeHtml(String(row.to))}</strong>${delta}</span>
      </div>
    `;
  }).join("");
  return `
    <aside class="governance-diff-strip" aria-label="Changes since last run">
      <span class="governance-diff-title">What changed</span>
      ${items}
    </aside>
  `;
}

function renderTryNextSuggestions(key) {
  if (!tryNextSuggestions) {
    return;
  }
  const suggestions = TRY_NEXT[key] || [];
  if (!suggestions.length) {
    tryNextSuggestions.classList.add("hidden");
    tryNextSuggestions.innerHTML = "";
    return;
  }
  tryNextSuggestions.classList.remove("hidden");
  tryNextSuggestions.innerHTML = `
    <span class="try-next-label">Try next</span>
    ${suggestions.map((item) => `
      <button type="button" class="try-next-btn" data-scenario-key="${escapeHtml(item.key)}">${escapeHtml(item.label)}</button>
    `).join("")}
  `;
  tryNextSuggestions.querySelectorAll(".try-next-btn").forEach((button) => {
    button.addEventListener("click", () => {
      const nextKey = button.dataset.scenarioKey;
      if (nextKey) {
        applyScenarioChip(nextKey, { autoRun: true });
      }
    });
  });
}

function renderRecommendation(data) {
  const rec = data.recommendations[0];
  const summary = data.request_summary || {};
  const empathyInsights = hasEmpathyInsights(summary);
  const empathyVehicle = empathyVehicleRecommendation(summary);
  const ai = rec.ai_score || {};
  const tapl = ai.tapl || {};
  const outcome = ai.outcome_simulation || {};
  const empathyMatch = rec.empathy_match?.match_score ?? empathyVehicle?.match_score ?? 0;
  const profile = summary.scenario_profile || {};
  const reasonCodes = rec.reason_codes || [];
  const taplAction = tapl.action || "show";
  const taplChanged = lastTaplAction && lastTaplAction !== taplAction;
  lastTaplAction = taplAction;
  const newSnapshot = captureRunSnapshot(data);
  const diffHtml = renderGovernanceDiff(previousRunSnapshot, newSnapshot);
  previousRunSnapshot = newSnapshot;

  if (!scenarioRecommendation) {
    return;
  }

  const scenarioKey = activeScenarioKey
    || detectScenarioKey(summary.scenario_text || lastParsedScenarioText || "");
  const badges = [
    inferenceBadgeHtml(summary),
    empathyInsights ? `<span class="hero-badge hero-badge-empathy">Empathy-aware</span>` : "",
    profile.profile_id ? `<span class="hero-badge hero-badge-profile">${escapeHtml(profile.profile_id.replaceAll("_", " "))}</span>` : "",
  ].filter(Boolean).join("");

  const compareKey = scenarioKey && COMPARE_NARRATIVES[scenarioKey] ? scenarioKey : null;
  const compareHtml = renderCompareNarrative(compareKey);
  const rulesVsSlmHtml = scenarioKey === "rules_vs_slm"
    ? renderRulesVsSlmStrip(lastRulesVsSlmCompare)
    : "";
  const punchlineHtml = renderGovernancePunchline(scenarioKey, summary);

  scenarioRecommendation.innerHTML = `
    ${compareHtml}
    ${rulesVsSlmHtml}
    ${punchlineHtml}
    ${diffHtml}
    ${renderHeroContextStrip(summary)}
    <div class="hero-result-head">
      <div class="hero-result-title">
        <p class="eyebrow">Recommended vehicle ${badges ? `<span class="hero-badge-row">${badges}</span>` : ""}</p>
        <div class="offer-header hero-offer-header">
          <div class="hero-vehicle-title">
            <span class="vehicle-glyph vehicle-glyph-lg" aria-hidden="true">${vehicleGlyph(rec.candidate.id)}</span>
            <div>
              <h2>${escapeHtml(rec.candidate.title)}</h2>
              <p class="hero-vehicle-id">${escapeHtml(rec.candidate.id.replaceAll("_", " "))}</p>
            </div>
          </div>
          <div class="hero-score-stack">
            <strong class="score-badge score-badge-hero">${pct(ai.final_hybrid_score)}</strong>
            <span class="score-badge-caption">Match score</span>
          </div>
        </div>
      </div>
      <div class="hero-policy-row">
        <span class="hero-policy-label">Trust policy <small>(TAPL)</small></span>
        ${renderTaplBadge(taplAction, { animated: taplChanged })}
        <span class="hero-policy-plain">${escapeHtml(taplPlainLabel(taplAction))}</span>
        <span class="hero-policy-reason">${escapeHtml(tapl.reason || "Policy evaluated for this scenario.")}</span>
      </div>
    </div>

    <div class="hero-score-grid">
      ${scoreMeter("Match score", ai.final_hybrid_score, { tone: "primary", band: "score", subtitle: "EDS + rank blend" })}
      ${scoreMeter("Trust", tapl.trust_score, { tone: "trust", band: "trust" })}
      ${scoreMeter("Fatigue", tapl.fatigue_score, { tone: "fatigue", band: "fatigue" })}
      ${scoreMeter("Empathy fit", empathyMatch, { tone: "empathy", band: "empathy" })}
      ${scoreMeter("Expected outcome", outcome.expected_outcome_score, { tone: "outcome", band: "outcome", subtitle: "Conversion sim" })}
    </div>

    <p class="explanation hero-why-line">${escapeHtml(rec.explanation)}</p>
    ${rec.tco?.recommendation_pitch ? `<p class="explanation empathy-inline-tco"><strong>TCO:</strong> ${escapeHtml(rec.tco.recommendation_pitch)}</p>` : ""}
    <div class="pill-row hero-reason-row">${reasonCodes.slice(0, 6).map(reason => `<span>${escapeHtml(reason.replaceAll("_", " "))}</span>`).join("")}</div>
    ${renderAlternateEmpathyVehicle(summary, rec.candidate.id)}
    <div class="hero-meta-row">
      <span>Intent: <strong>${escapeHtml(pretty(ai.intent?.label))}</strong></span>
      <span>Source: <strong>${escapeHtml(pretty(rec.explanation_source || "local"))}</strong></span>
    </div>
  `;

  renderTryNextSuggestions(scenarioKey);
  renderEmpathyPanels(summary, rec);
  pulseOfferCard();
}

function updateRuntimeSectionHeadings(_summary) {
  // Accordion summaries replace the old dynamic section headings.
}

function renderTechnicalExplanation(data) {
  if (!technicalExplanation) {
    return;
  }
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
  const trip = empathy.trip || {};
  const enrichment = summary.enrichment || empathy.enrichment || {};
  const scenarioSnippet = String(summary.scenario_text || scenarioText?.value || "").trim();
  const shortScenario = scenarioSnippet.length > 140
    ? `${scenarioSnippet.slice(0, 139)}…`
    : scenarioSnippet;
  const empathyArticle = empathyInsights ? `
      <article class="technical-span-full">
        <span>5. Empathy Engine</span>
        <p>Scenario-derived hidden needs, route enrichment, and optional TCO for this input.</p>
        <dl>
          <div><dt>Persona</dt><dd>${escapeHtml((empathy.hidden_needs?.persona_tags || []).join(", ") || "none")}</dd></div>
          <div><dt>Route miles</dt><dd>${escapeHtml(trip.distance_miles ?? enrichment.route?.distance_miles ?? "—")}</dd></div>
          <div><dt>Empathy vehicle</dt><dd>${escapeHtml(empathyVehicle?.candidate_id || rec.candidate.id)}</dd></div>
          <div><dt>Empathy match</dt><dd>${num(empathyVehicle?.match_score ?? rec.empathy_match?.match_score ?? 0)}</dd></div>
          <div><dt>Constraints met</dt><dd>${escapeHtml((empathyVehicle?.satisfied || rec.empathy_match?.satisfied || []).join(", ") || "none")}</dd></div>
          <div><dt>Weather</dt><dd>${escapeHtml(enrichment.weather?.forecast || "clear")}</dd></div>
          <div><dt>TCO total</dt><dd>${(empathyVehicle?.tco?.total_trip_cost ?? rec.tco?.total_trip_cost) != null ? `$${Number(empathyVehicle?.tco?.total_trip_cost ?? rec.tco?.total_trip_cost).toFixed(0)}` : "n/a"}</dd></div>
        </dl>
      </article>
  ` : "";

  technicalExplanation.innerHTML = `
    <p class="technical-scenario-lead">${escapeHtml(shortScenario || "Scenario text drives all panels below.")}</p>
    <div class="technical-grid">
      <article>
        <span>1. Scenario NLP</span>
        <p>Free-text input converted into structured context before ranking.</p>
        <dl>
          <div><dt>Domain</dt><dd>${escapeHtml(pretty(nlp.detected_domain || "unknown"))}</dd></div>
          <div><dt>Channel</dt><dd>${escapeHtml(pretty(context.channel))}</dd></div>
          <div><dt>Intent</dt><dd>${escapeHtml(pretty(context.current_intent))}</dd></div>
          <div><dt>Journey</dt><dd>${escapeHtml(pretty(context.journey_stage))}</dd></div>
          <div><dt>Keywords</dt><dd>${escapeHtml((nlp.keywords || []).join(", ") || "none")}</dd></div>
          <div><dt>Parser</dt><dd>${escapeHtml(pretty(nlp.parser || summary.inference?.provider || "rules"))}</dd></div>
        </dl>
      </article>
      <article>
        <span>2. Candidate Filtering</span>
        <p>Catalog narrowed using channel and scenario keyword overlap from your text.</p>
        <dl>
          <div><dt>Candidate selected</dt><dd>${escapeHtml(candidate.id)}</dd></div>
          <div><dt>Candidate count</dt><dd>${escapeHtml(summary.candidate_preselection?.candidate_count ?? "n/a")}</dd></div>
          <div><dt>Empathy vehicle</dt><dd>${escapeHtml(empathyVehicle?.candidate_id || "n/a")}</dd></div>
          <div><dt>Reason codes</dt><dd>${escapeHtml((rec.reason_codes || []).slice(0, 4).join(", ") || "none")}</dd></div>
        </dl>
      </article>
      <article>
        <span>3. Scoring Signals</span>
        <p>EDS relevance, semantic similarity, channel fit, and simulated outcome combined.</p>
        <dl>
          <div><dt>EDS score</dt><dd>${num(eds.final_eds_score)}</dd></div>
          <div><dt>Semantic similarity</dt><dd>${num(ai.semantic_similarity_score)}</dd></div>
          <div><dt>Channel fit</dt><dd>${num(ai.channel_fit_score)}</dd></div>
          <div><dt>Expected outcome</dt><dd>${num(outcome.expected_outcome_score)}</dd></div>
          <div><dt>Conversion prob.</dt><dd>${num(outcome.conversion_probability)}</dd></div>
          <div><dt>Revenue impact</dt><dd>$${Number(outcome.revenue_impact || 0).toFixed(0)}</dd></div>
          <div><dt>Base rank score</dt><dd>${num(ai.ai_rank_score)}</dd></div>
          <div><dt>Final rank score</dt><dd>${num(ai.final_hybrid_score)}</dd></div>
          <div><dt>Explanation source</dt><dd>${escapeHtml(pretty(rec.explanation_source || "local"))}</dd></div>
          <div><dt>Inference tier</dt><dd>${escapeHtml(pretty(summary.inference?.tier || "n/a"))}</dd></div>
          <div><dt>Inference source</dt><dd>${escapeHtml(pretty(summary.inference?.sub_source || "n/a"))}</dd></div>
        </dl>
      </article>
      <article>
        <span>4. Trust And TAPL</span>
        <p>Trust, fatigue, and compliance govern whether to show, soften, delay, or suppress.</p>
        <dl>
          <div><dt>Action</dt><dd>${escapeHtml(pretty(tapl.action))}</dd></div>
          <div><dt>Trust</dt><dd>${num(tapl.trust_score)}</dd></div>
          <div><dt>Fatigue</dt><dd>${num(tapl.fatigue_score)}</dd></div>
          <div><dt>Compliance</dt><dd>${num(tapl.compliance_score)}</dd></div>
          <div><dt>TAPL reason</dt><dd>${escapeHtml(tapl.reason || "none")}</dd></div>
          <div><dt>Policy source</dt><dd>${escapeHtml(pretty((summary.inference || {}).provider || "rules"))}</dd></div>
        </dl>
      </article>
      ${empathyArticle}
      ${renderSlmTelemetryArticle(summary, rec)}
    </div>
  `;
}

function renderSlmTelemetryArticle(summary, rec) {
  const inference = summary.inference || {};
  const telemetry = summary.provider_telemetry || {};
  const slm = summary.llm_status?.slm_engine || {};
  const remote = slm.remote || {};
  const operations = telemetry.operations || {};
  const hasSlmSignal = Boolean(
    inference.sub_source
    || slm.enabled
    || telemetry.call_count
    || summary.use_llm_explanation
    || summary.inference_mode === "slm",
  );
  if (!hasSlmSignal) {
    return "";
  }
  const opLines = Object.entries(operations)
    .filter(([name]) => String(name).startsWith("slm_") || String(name).includes("slm"))
    .map(([name, count]) => `${name}: ${count}`)
    .join(", ");
  return `
      <article class="technical-span-full">
        <span>6. Hosted SLM telemetry</span>
        <p>Remote SLM enrich/explain calls for this process (cumulative) plus current-request inference status.</p>
        <dl>
          <div><dt>Inference source</dt><dd>${escapeHtml(pretty(inference.sub_source || "n/a"))}</dd></div>
          <div><dt>SLM enabled</dt><dd>${slm.enabled ? "yes" : "no"}</dd></div>
          <div><dt>SLM model</dt><dd>${escapeHtml(slm.model || remote.model || "n/a")}</dd></div>
          <div><dt>SLM last status</dt><dd>${escapeHtml(pretty(slm.last_status || "n/a"))}</dd></div>
          <div><dt>Provider calls</dt><dd>${escapeHtml(String(telemetry.call_count ?? 0))}</dd></div>
          <div><dt>Input tokens</dt><dd>${escapeHtml(String(telemetry.input_tokens ?? 0))}</dd></div>
          <div><dt>Output tokens</dt><dd>${escapeHtml(String(telemetry.output_tokens ?? 0))}</dd></div>
          <div><dt>SLM operations</dt><dd>${escapeHtml(opLines || "none yet")}</dd></div>
          <div><dt>Explanation source</dt><dd>${escapeHtml(pretty(rec.explanation_source || "local"))}</dd></div>
          <div><dt>Explanation routing</dt><dd>${escapeHtml(pretty(summary.explanation_routing?.prefer_slm_first ? "prefer SLM first" : "default"))}</dd></div>
        </dl>
      </article>
  `;
}

function renderRuntimeInsights(data) {
  if (!data?.request_summary) {
    return;
  }
  updateRuntimeSectionHeadings(data.request_summary);
  renderTechnicalExplanation(data);
  if (data.recommendations?.length) {
    renderArchitecturePanels(
      scenarioArchitecturePanels,
      data.request_summary,
      data.recommendations[0],
    );
  }
}

function formatApiError(status, body) {
  try {
    const payload = JSON.parse(body);
    if (Array.isArray(payload.detail)) {
      return payload.detail.map(item => item.msg || JSON.stringify(item)).join(" ");
    }
    if (typeof payload.detail === "string") {
      return payload.detail;
    }
  } catch (_error) {
    // fall through to raw body
  }
  return body || `Request failed with status ${status}.`;
}

function showError(error, inlineMessage) {
  const message = inlineMessage || error?.message || String(error);
  setRunError(message);
  if (scenarioRecommendation) {
    scenarioRecommendation.innerHTML = `
      <p class="eyebrow">Error</p>
      <h2>Could not generate recommendation.</h2>
      <p class="explanation">${escapeHtml(message)}</p>
    `;
  }
  if (responsePreview) {
    responsePreview.textContent = String(error?.stack || message);
  }
  if (empathyResultsSection) {
    empathyResultsSection.classList.add("hidden");
    empathyResultsSection.setAttribute("aria-hidden", "true");
  }
  scrollToResults();
}

async function ensureDemoReady() {
  if (!window.DemoApi?.init) {
    throw new Error("Demo API helper failed to load. Refresh the page and try again.");
  }
  if (!demoReady) {
    await window.DemoApi.init();
    demoReady = true;
  }
}

async function fetchScenarioRecommendation(payload) {
  const response = await window.DemoApi.fetch("/recommend-from-scenario", {
    method: "POST",
    body: JSON.stringify(payload),
    onProgress: setColdStartMessage,
  });
  const body = await response.text();
  if (!response.ok) {
    throw new Error(formatApiError(response.status, body));
  }
  const data = JSON.parse(body);
  if (!data.recommendations?.length) {
    throw new Error("The API returned no recommendations for this scenario.");
  }
  return data;
}

async function runRulesVsSlmCompare(basePayload) {
  const [rulesData, slmData] = await Promise.all([
    fetchScenarioRecommendation({
      ...basePayload,
      inference_mode: "rules",
      use_slm: false,
      use_llm_explanation: false,
    }),
    fetchScenarioRecommendation({
      ...basePayload,
      inference_mode: "slm",
      use_slm: true,
      use_llm_explanation: true,
    }),
  ]);
  lastRulesVsSlmCompare = {
    rules: captureInferenceCompareSnapshot(rulesData),
    slm: captureInferenceCompareSnapshot(slmData),
  };
  return slmData;
}

async function runScenario() {
  const validationError = validateScenarioText(scenarioText?.value || "");
  if (validationError) {
    showError(new Error(validationError), validationError);
    return;
  }

  const payload = buildPayload();
  const options = activeScenarioOptions();
  updatePayloadPreview();
  setRunError("");
  setColdStartMessage("");
  setRunning(true);
  scrollToResults();

  try {
    await ensureDemoReady();
    let data;
    if (options.compare_rules_vs_slm) {
      data = await runRulesVsSlmCompare(payload);
    } else {
      lastRulesVsSlmCompare = null;
      data = await fetchScenarioRecommendation(payload);
    }
    lastScenarioData = data;
    lastParsedScenarioText = payload.scenario_text;
    if (responsePreview) {
      const previewPayload = options.compare_rules_vs_slm
        ? { primary: data, rules_vs_slm: lastRulesVsSlmCompare }
        : data;
      responsePreview.textContent = JSON.stringify(previewPayload, null, 2);
    }
    renderRecommendation(data);
    renderRuntimeInsights(data);
    highlightBenchmarkRow(payload.scenario_text);
    setRunError("");
    setColdStartMessage("");
  } catch (error) {
    showError(error);
  } finally {
    setRunning(false);
    setColdStartMessage("");
  }
}

function bindScenarioDemo() {
  scenarioText = document.getElementById("scenarioText");
  scenarioRunBtn = document.getElementById("scenarioRunBtn");
  scenarioForm = document.getElementById("scenarioForm");
  scenarioRunError = document.getElementById("scenarioRunError");
  scenarioColdStart = document.getElementById("scenarioColdStart");
  scenarioLoading = document.getElementById("scenarioLoading");
  scenarioRecommendation = document.getElementById("scenarioRecommendation");
  technicalExplanation = document.getElementById("technicalExplanation");
  payloadPreview = document.getElementById("scenarioPayloadPreview");
  responsePreview = document.getElementById("scenarioResponsePreview");
  scenarioArchitecturePanels = document.getElementById("scenarioArchitecturePanels");
  empathyResultsSection = document.getElementById("empathyResultsSection");
  scenarioEmpathyHiddenNeeds = document.getElementById("scenarioEmpathyHiddenNeeds");
  scenarioEmpathyEnrichment = document.getElementById("scenarioEmpathyEnrichment");
  scenarioEmpathyTco = document.getElementById("scenarioEmpathyTco");
  scenarioEmpathyPitch = document.getElementById("scenarioEmpathyPitch");
  scenarioResultsSection = document.querySelector(".scenario-results");
  demoWakeBanner = document.getElementById("demoWakeBanner");
  tryNextSuggestions = document.getElementById("tryNextSuggestions");
  copyDemoLinkBtn = document.getElementById("copyDemoLinkBtn");

  if (!scenarioText || !scenarioRunBtn || !scenarioForm) {
    console.error("Scenario demo: missing form, textarea, or Recommend button.");
    return;
  }

  const urlScenario = readScenarioFromUrl();
  if (urlScenario) {
    applyScenarioChip(urlScenario, { autoRun: false });
  }

  scenarioText.addEventListener("input", () => {
    updatePayloadPreview();
    const detected = detectScenarioKey(scenarioText.value);
    updateActiveScenarioChip(detected);
    if (detected) {
      syncScenarioUrl(detected);
    }
    if (scenarioRunError && !scenarioRunError.classList.contains("hidden")) {
      setRunError("");
    }
  });

  bindScenarioChips();

  scenarioForm.addEventListener("submit", (event) => {
    event.preventDefault();
    runScenario();
  });

  const mobileRunBtn = document.getElementById("scenarioMobileRunBtn");
  if (mobileRunBtn) {
    mobileRunBtn.addEventListener("click", () => runScenario());
  }

  if (copyDemoLinkBtn) {
    copyDemoLinkBtn.addEventListener("click", () => copyDemoLink());
  }

  scenarioText.addEventListener("keydown", (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
      event.preventDefault();
      runScenario();
    }
  });

  updatePayloadPreview();
  updateActiveScenarioChip(detectScenarioKey(scenarioText.value) || activeScenarioKey);
  bindBenchmarkToggle();
  window.DemoApi?.init?.();
  scheduleInitialDemoRun();
}

function loadScenarioFromBenchmarkRow(row) {
  const text = row?.scenario_text;
  if (!text || !scenarioText) {
    return;
  }
  scenarioText.value = text;
  const detected = detectScenarioKey(text);
  updateActiveScenarioChip(detected);
  if (detected) {
    syncScenarioUrl(detected);
  }
  updatePayloadPreview();
  setRunError("");
  window.scrollTo({ top: 0, behavior: "smooth" });
  runScenario();
}

window.ScenarioDemo = {
  run: () => runScenario(),
};

function fmtScore(value) {
  if (value == null || value === "") {
    return "—";
  }
  const num = Number(value);
  return Number.isFinite(num) ? num.toFixed(3) : String(value);
}

let travelBenchmarkRows = [];
let benchmarkMetricsExpanded = false;
let initialDemoScheduled = false;

function renderBenchmarkMatchCell(row) {
  if (row.top_rank_match && row.empathy_match) {
    return `<span class="benchmark-match benchmark-match-yes" title="Top rank and empathy both match">✓</span>`;
  }
  if (row.vehicle_match) {
    return `<span class="benchmark-match benchmark-match-partial" title="Vehicle aligned via rank or empathy">~</span>`;
  }
  return `<span class="benchmark-match benchmark-match-no" title="No match">✗</span>`;
}

function highlightBenchmarkRow(scenarioText) {
  const normalized = String(scenarioText || "").trim().replace(/\s+/g, " ");
  document.querySelectorAll(".benchmark-row").forEach((rowEl) => {
    const index = Number(rowEl.getAttribute("data-row-index"));
    const row = travelBenchmarkRows[index];
    const same = row?.scenario_text && row.scenario_text.trim().replace(/\s+/g, " ") === normalized;
    rowEl.classList.toggle("is-selected", Boolean(same));
  });
}

function bindBenchmarkToggle() {
  const toggle = document.getElementById("benchmarkToggleMetrics");
  const table = document.getElementById("travelBenchmarkTable");
  if (!toggle || !table) {
    return;
  }
  toggle.addEventListener("click", () => {
    benchmarkMetricsExpanded = !benchmarkMetricsExpanded;
    table.classList.toggle("benchmark-score-table--compact", !benchmarkMetricsExpanded);
    table.classList.toggle("benchmark-score-table--demo", !benchmarkMetricsExpanded);
    toggle.textContent = benchmarkMetricsExpanded ? "Demo view" : "View full 11-scenario matrix";
    toggle.setAttribute("aria-pressed", benchmarkMetricsExpanded ? "true" : "false");
  });
}

function scheduleInitialDemoRun() {
  if (initialDemoScheduled || !scenarioText?.value.trim()) {
    return;
  }
  initialDemoScheduled = true;
  window.setTimeout(() => {
    if (!lastScenarioData) {
      runScenario();
    }
  }, 450);
}

async function loadTravelBenchmark() {
  const meta = document.getElementById("travelBenchmarkMeta");
  const body = document.getElementById("travelBenchmarkBody");
  if (!meta || !body) {
    return;
  }
  try {
    await ensureDemoReady();
    const response = await window.DemoApi.fetch("/travel-scenario-benchmark");
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail || "Could not load travel scenario benchmark.");
    }
    travelBenchmarkRows = payload.scenarios || [];
    const topRate = Math.round((payload.top_rank_match_rate ?? payload.vehicle_match_rate ?? 0) * 100);
    meta.textContent = `${payload.scenario_count} scenarios · ${topRate}% top-rank match · click a row to try it`;
    body.innerHTML = travelBenchmarkRows.map((row, index) => `
      <tr class="benchmark-row" tabindex="0" role="button" data-row-index="${index}" title="Load this scenario">
        <td>${index + 1}</td>
        <td>${escapeHtml(row.title || row.scenario_key || "")}</td>
        <td class="col-profile">${escapeHtml(row.profile_id || "—")}</td>
        <td>${escapeHtml((row.top_vehicle || "—").replaceAll("_", " "))}</td>
        <td class="col-metric">${fmtScore(row.eds_score)}</td>
        <td class="col-metric">${fmtScore(row.semantic_score)}</td>
        <td class="col-metric">${fmtScore(row.expected_outcome)}</td>
        <td class="col-metric">${fmtScore(row.conversion_probability)}</td>
        <td>${renderTaplBadge(row.tapl_action || "show")}</td>
        <td>${fmtScore(row.trust_score)}</td>
        <td class="col-metric">${fmtScore(row.fatigue_score)}</td>
        <td class="col-metric">${fmtScore(row.ai_rank_score)}</td>
        <td class="col-metric">${fmtScore(row.final_hybrid_score)}</td>
        <td>${renderBenchmarkMatchCell(row)}</td>
      </tr>
    `).join("");
    body.querySelectorAll(".benchmark-row").forEach((rowEl) => {
      const activate = () => {
        const index = Number(rowEl.getAttribute("data-row-index"));
        const row = travelBenchmarkRows[index];
        if (!row?.scenario_text) {
          return;
        }
        loadScenarioFromBenchmarkRow(row);
      };
      rowEl.addEventListener("click", activate);
      rowEl.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          activate();
        }
      });
    });
  } catch (error) {
    meta.textContent = "Could not load benchmark scores.";
    body.innerHTML = `<tr><td colspan="14">${escapeHtml(error.message || String(error))}</td></tr>`;
  }
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", () => {
    bindScenarioDemo();
    loadTravelBenchmark();
  });
} else {
  bindScenarioDemo();
  loadTravelBenchmark();
}
