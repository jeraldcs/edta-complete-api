const scenarios = {
  vehicle_upgrade_suv: {
    label: "Family SUV airport rental",
    group: "Car & travel",
    trip: "Premium SUV upgrade at SFO",
    context: {
      anonymous_id: "anon-web-123",
      customer_id: "cust-789",
      channel: "web",
      session_events: ["viewed_vehicle_page", "searched_suv", "checked_location_availability", "started_booking"],
      search_terms: ["family SUV airport rental"],
      past_transactions: [{ category: "car_rental", vehicle_class: "SUV", location: "SFO airport" }],
      profile_attributes: { loyalty_tier: "preferred", trip_type: "family", fatigue_count: 1 },
      business_context: { inventory_suv: "available", season: "summer" },
      channel_context: { page_type: "vehicle_detail", placement: "hero_banner" },
      device_context: { device_type: "desktop" },
      consent: { personalization: true }
    }
  },
  early_booking_discount: {
    label: "Early booking discount shopper",
    group: "Car & travel",
    trip: "Comparing rental dates for summer travel",
    context: {
      anonymous_id: "anon-web-456",
      channel: "web",
      session_events: ["viewed_rental_dates", "compared_prices", "saved_trip"],
      search_terms: ["early booking discount rental"],
      profile_attributes: { trip_type: "leisure", fatigue_count: 0 },
      business_context: { season: "summer", inventory_pressure: "medium" },
      channel_context: { page_type: "search_results" },
      consent: { personalization: true }
    }
  },
  hotel_reservation_assist: {
    label: "Hotel availability research",
    group: "Hotel",
    trip: "Weekend stay availability lookup",
    context: {
      anonymous_id: "anon-hotel-001",
      channel: "web",
      session_events: ["searched_hotel_dates", "viewed_room_types", "checked_availability"],
      search_terms: ["hotel room availability this weekend"],
      profile_attributes: { trip_type: "weekend", fatigue_count: 1 },
      business_context: { destination: "downtown", occupancy: "high" },
      channel_context: { page_type: "hotel_search" },
      consent: { personalization: true }
    }
  },
  hotel_room_offer: {
    label: "Hotel room offer browse",
    group: "Hotel",
    trip: "Selecting a room category for business travel",
    context: {
      anonymous_id: "anon-hotel-002",
      customer_id: "cust-hotel-101",
      channel: "web",
      session_events: ["viewed_room_gallery", "compared_rates", "added_dates"],
      search_terms: ["business hotel room offer"],
      profile_attributes: { loyalty_tier: "gold", fatigue_count: 0 },
      business_context: { stay_length_nights: 3 },
      channel_context: { page_type: "room_detail" },
      consent: { personalization: true }
    }
  },
  banking_credit_card_offer: {
    label: "Credit card research",
    group: "Banking",
    trip: "Comparing rewards credit cards",
    context: {
      anonymous_id: "anon-bank-001",
      customer_id: "cust-bank-55",
      channel: "web",
      session_events: ["viewed_credit_cards", "compared_rewards", "read_terms"],
      search_terms: ["travel rewards credit card"],
      profile_attributes: { segment: "affluent", fatigue_count: 2 },
      business_context: { product_category: "credit_card" },
      channel_context: { page_type: "product_comparison" },
      consent: { personalization: true }
    }
  },
  banking_loan_next_step: {
    label: "Mortgage eligibility research",
    group: "Banking",
    trip: "Exploring loan rates and application steps",
    context: {
      anonymous_id: "anon-bank-002",
      channel: "web",
      session_events: ["viewed_mortgage_rates", "used_calculator", "saved_application"],
      search_terms: ["mortgage eligibility application"],
      profile_attributes: { home_buyer: true, fatigue_count: 1 },
      business_context: { loan_type: "mortgage" },
      channel_context: { page_type: "loan_hub" },
      consent: { personalization: true }
    }
  },
  restaurant_reservation_assist: {
    label: "Restaurant table booking",
    group: "Restaurant",
    trip: "Finding dinner reservation availability",
    context: {
      anonymous_id: "anon-rest-001",
      channel: "web",
      session_events: ["searched_restaurants", "checked_table_times", "viewed_cuisine"],
      search_terms: ["restaurant reservation tonight"],
      profile_attributes: { party_size: 4, fatigue_count: 0 },
      business_context: { cuisine_preference: "italian" },
      channel_context: { page_type: "reservation_flow" },
      consent: { personalization: true }
    }
  },
  restaurant_menu_recommendation: {
    label: "Menu browsing visitor",
    group: "Restaurant",
    trip: "Reviewing menu before ordering",
    context: {
      anonymous_id: "anon-rest-002",
      channel: "web",
      session_events: ["viewed_menu", "filtered_cuisine", "saved_dish"],
      search_terms: ["restaurant menu recommendation"],
      profile_attributes: { dietary: "none", fatigue_count: 1 },
      business_context: { location: "downtown" },
      channel_context: { page_type: "menu" },
      consent: { personalization: true }
    }
  },
  mobile_restaurant_qr_menu: {
    label: "QR menu at table",
    group: "Mobile dining",
    trip: "Scanned QR code at restaurant table",
    context: {
      anonymous_id: "anon-mobile-001",
      channel: "mobile",
      session_events: ["scanned_qr", "opened_mobile_menu", "browsed_categories"],
      search_terms: ["qr menu table"],
      profile_attributes: { device: "phone", fatigue_count: 0 },
      business_context: { table_number: 12 },
      channel_context: { entry: "qr_scan", placement: "table" },
      device_context: { device_type: "mobile" },
      consent: { personalization: true }
    }
  },
  mobile_restaurant_dish_promo: {
    label: "Chef special promotion",
    group: "Mobile dining",
    trip: "Mobile diner reviewing specials",
    context: {
      anonymous_id: "anon-mobile-002",
      channel: "mobile",
      session_events: ["opened_qr_menu", "viewed_specials", "added_item"],
      search_terms: ["new dish promotion combo"],
      profile_attributes: { repeat_visitor: true, fatigue_count: 2 },
      business_context: { promo_window: "limited_time" },
      channel_context: { entry: "qr_scan" },
      device_context: { device_type: "mobile" },
      consent: { personalization: true }
    }
  },
  hcp_education_content: {
    label: "HCP clinical education",
    group: "Healthcare",
    trip: "Physician researching diabetes therapy content",
    context: {
      anonymous_id: "anon-hcp-001",
      customer_id: "hcp-4421",
      channel: "web",
      session_events: ["viewed_clinical_content", "downloaded_summary", "saved_article"],
      search_terms: ["diabetes hcp education"],
      profile_attributes: { role: "physician", specialty: "endocrinology", fatigue_count: 0 },
      business_context: { content_type: "clinical_education" },
      channel_context: { audience: "hcp" },
      consent: { personalization: true }
    }
  },
  obesity_product_hcp_education: {
    label: "Obesity therapy education",
    group: "Healthcare",
    trip: "Doctor reviewing obesity product information",
    context: {
      anonymous_id: "anon-hcp-002",
      customer_id: "hcp-8830",
      channel: "web",
      session_events: ["viewed_obesity_product", "read_clinical_data", "saved_reference"],
      search_terms: ["obesity product hcp education"],
      profile_attributes: { role: "physician", fatigue_count: 1 },
      business_context: { therapy_area: "obesity" },
      channel_context: { audience: "hcp" },
      consent: { personalization: true }
    }
  },
  chatbot_booking_assist: {
    label: "Chatbot booking help",
    group: "Conversational",
    trip: "Reservation support conversation",
    context: {
      anonymous_id: "chat-001",
      customer_id: "cust-chat-789",
      channel: "chatbot",
      session_events: ["opened_chatbot", "asked_about_booking", "asked_availability"],
      search_terms: ["can I change my reservation to SUV"],
      profile_attributes: { loyalty_tier: "preferred", fatigue_count: 0 },
      business_context: { inventory_suv: "available" },
      channel_context: { conversation_turn: 3, bot_intent: "booking_change" },
      device_context: { device: "web_chat" },
      consent: { personalization: true }
    }
  },
  iot_device_service_alert: {
    label: "IoT maintenance alert",
    group: "Connected devices",
    trip: "Connected device service moment",
    context: {
      anonymous_id: "iot-001",
      channel: "iot",
      session_events: ["device_low_battery", "sensor_status_warning", "maintenance_due"],
      search_terms: [],
      profile_attributes: { device_type: "connected_device", fatigue_count: 1 },
      business_context: { service_window: "available" },
      channel_context: { signal_type: "maintenance", urgency: "medium" },
      device_context: { battery_level: 12, firmware_version: "1.2.9" },
      consent: { personalization: true }
    }
  },
  connected_car_location_assist: {
    label: "Connected car trip assist",
    group: "Connected devices",
    trip: "Driver nearing rental return location",
    context: {
      anonymous_id: "car-001",
      customer_id: "cust-car-220",
      channel: "connected_car",
      session_events: ["approaching_return_zone", "navigation_active", "fuel_low"],
      search_terms: ["return location assist"],
      profile_attributes: { trip_type: "rental_return", fatigue_count: 0 },
      business_context: { rental_location: "SFO" },
      channel_context: { vehicle_state: "in_trip" },
      device_context: { vehicle_id: "fleet-9081" },
      consent: { personalization: true }
    }
  },
  wearable_health_nudge: {
    label: "Wearable wellness nudge",
    group: "Connected devices",
    trip: "Short wearable notification window",
    context: {
      anonymous_id: "wear-001",
      channel: "wearable",
      session_events: ["reminder_due", "user_active", "short_notification_window"],
      search_terms: ["wellness reminder"],
      profile_attributes: { audience_type: "consumer", fatigue_count: 8 },
      business_context: { content_sensitivity: "medium" },
      channel_context: { max_notification_length: 80 },
      device_context: { device: "smart_watch" },
      consent: { personalization: true }
    }
  }
};

const scenarioSelect = document.getElementById("scenario");
const runBtn = document.getElementById("runBtn");
const useLlm = document.getElementById("useLlm");
const useLlmExplanation = document.getElementById("useLlmExplanation");
const llmStatus = document.getElementById("llmStatus");
const payloadPreview = document.getElementById("payloadPreview");
const responsePreview = document.getElementById("responsePreview");
const loading = document.getElementById("loading");
const emptyState = document.getElementById("emptyState");
const topRecommendation = document.getElementById("topRecommendation");
const recommendationList = document.getElementById("recommendationList");
const signalGrid = document.getElementById("signalGrid");
const architecturePanels = document.getElementById("architecturePanels");
const activeChannel = document.getElementById("activeChannel");
const heroTitle = document.getElementById("heroTitle");
const heroSubtitle = document.getElementById("heroSubtitle");
const heroPersonalization = document.getElementById("heroPersonalization");
const bannerTitle = document.getElementById("bannerTitle");
const bannerCopy = document.getElementById("bannerCopy");
const bannerCta = document.getElementById("bannerCta");
const visitorSignals = document.getElementById("visitorSignals");
const experienceChanges = document.getElementById("experienceChanges");

const { escapeHtml, pct, pretty, renderArchitecturePanels } = window.DemoShared;

let lastResponse = null;

function money(value) {
  return `$${Number(value || 0).toFixed(0)}`;
}

function populateScenarioSelect() {
  const groups = new Map();
  Object.entries(scenarios).forEach(([key, scenario]) => {
    const groupName = scenario.group || "Other";
    if (!groups.has(groupName)) {
      groups.set(groupName, []);
    }
    groups.get(groupName).push({ key, scenario });
  });

  scenarioSelect.innerHTML = "";
  groups.forEach((items, groupName) => {
    const group = document.createElement("optgroup");
    group.label = groupName;
    items.forEach(({ key, scenario }) => {
      const option = document.createElement("option");
      option.value = key;
      option.textContent = scenario.label;
      group.appendChild(option);
    });
    scenarioSelect.appendChild(group);
  });
}

function buildPayload() {
  const scenario = scenarios[scenarioSelect.value];
  return {
    context: scenario.context,
    limit: 3,
    use_ai_models: true,
    use_llm: useLlm.checked,
    use_llm_explanation: useLlmExplanation.checked
  };
}

function updatePreview() {
  const payload = buildPayload();
  const scenario = scenarios[scenarioSelect.value];
  payloadPreview.textContent = JSON.stringify(payload, null, 2);
  activeChannel.textContent = pretty(payload.context.channel);
  visitorSignals.innerHTML = [
    ["Scenario", scenario.label],
    ["Channel", pretty(payload.context.channel)],
    ["Trip context", scenario.trip],
    ["Session events", payload.context.session_events.join(", ")],
    ["Search terms", payload.context.search_terms.join(", ") || "None"]
  ].map(([label, value]) => `<li><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></li>`).join("");
}

function reasonPills(reasons) {
  return reasons.map(reason => `<span>${escapeHtml(reason.replaceAll("_", " "))}</span>`).join("");
}

function renderSignals(rec) {
  signalGrid.innerHTML = `
    <div><span>Intent</span><strong>${escapeHtml(rec.ai_score.intent.label)}</strong><small>${escapeHtml(rec.ai_score.intent.source)}</small></div>
    <div><span>Journey</span><strong>${escapeHtml(rec.ai_score.journey_stage.label)}</strong><small>${escapeHtml(rec.ai_score.journey_stage.source)}</small></div>
    <div><span>TAPL action</span><strong>${escapeHtml(rec.ai_score.tapl.action)}</strong><small>${escapeHtml(rec.ai_score.tapl.reason)}</small></div>
    <div><span>Outcome score</span><strong>${pct(rec.ai_score.outcome_simulation.expected_outcome_score)}</strong><small>Predicted impact</small></div>
  `;
}

function renderPersonalizedPage(rec, responseSummary) {
  const scenario = scenarios[scenarioSelect.value];
  const action = rec.ai_score.tapl.action;
  const title = rec.candidate.title;
  const score = pct(rec.ai_score.final_hybrid_score);
  const profile = responseSummary.profile || {};
  const profileLabel = profile.profile_lookup === "enriched" ? "Known profile enriched" : pretty(profile.profile_lookup || "profile not used");

  heroTitle.textContent = title;
  heroSubtitle.textContent = rec.candidate.description;
  heroPersonalization.innerHTML = `
    <span>${escapeHtml(pretty(responseSummary.channel))} visitor personalized in real time</span>
    <strong>${escapeHtml(title)} ranked #1 with ${score} final hybrid score. ${escapeHtml(profileLabel)}.</strong>
  `;

  bannerTitle.textContent = `Recommended for this ${pretty(responseSummary.channel)} moment`;
  bannerCopy.textContent = rec.explanation;
  bannerCta.textContent = action === "delay" ? "Save for later" : action === "soften" ? "View gentle recommendation" : "Continue with this recommendation";

  experienceChanges.innerHTML = `
    <article><span>Hero</span><strong>${escapeHtml(title)}</strong><p>${escapeHtml(rec.candidate.description)}</p></article>
    <article><span>CTA</span><strong>${escapeHtml(bannerCta.textContent)}</strong><p>TAPL governance selected action: ${escapeHtml(action)}.</p></article>
    <article><span>Reason</span><strong>${escapeHtml(pretty(rec.ai_score.intent.label))}</strong><p>${escapeHtml(rec.explanation)}</p></article>
  `;

  visitorSignals.innerHTML += `
    <li><span>Detected intent</span><strong>${escapeHtml(pretty(rec.ai_score.intent.label))}</strong></li>
    <li><span>Detected journey</span><strong>${escapeHtml(pretty(rec.ai_score.journey_stage.label))}</strong></li>
    <li><span>Profile lookup</span><strong>${escapeHtml(profileLabel)}</strong></li>
    <li><span>LLM requested</span><strong>${responseSummary.use_llm ? "Yes" : "No"}</strong></li>
    <li><span>LLM enabled</span><strong>${responseSummary.llm_enabled ? "Yes" : "No"}</strong></li>
  `;
}

function renderTopRecommendation(rec) {
  const outcome = rec.ai_score.outcome_simulation;
  topRecommendation.innerHTML = `
    <p class="eyebrow">Personalized next best action</p>
    <div class="offer-header">
      <div>
        <h2>${escapeHtml(rec.candidate.title)}</h2>
        <p>${escapeHtml(rec.candidate.description)}</p>
      </div>
      <strong class="score-badge">${pct(rec.ai_score.final_hybrid_score)}</strong>
    </div>

    <div class="offer-metrics">
      <div><span>Conversion probability</span><strong>${pct(outcome.conversion_probability)}</strong></div>
      <div><span>Revenue impact</span><strong>${money(outcome.revenue_impact)}</strong></div>
      <div><span>Trust score</span><strong>${pct(rec.ai_score.tapl.trust_score)}</strong></div>
    </div>

    <p class="explanation">${escapeHtml(rec.explanation)}</p>
    <div class="pill-row">${reasonPills(rec.reason_codes)}</div>
    <button type="button" class="offer-button">${escapeHtml(bannerCta.textContent)}</button>
    <div class="feedback-row">
      <span class="feedback-label">Capture feedback to EML</span>
      <div class="feedback-actions">
        <button type="button" class="feedback-btn" data-feedback="click">Click</button>
        <button type="button" class="feedback-btn is-positive" data-feedback="convert">Convert</button>
        <button type="button" class="feedback-btn is-muted" data-feedback="dismiss">Dismiss</button>
      </div>
      <p id="feedbackStatus" class="feedback-status">Send feedback to update trust, fatigue, and outcomes.</p>
    </div>
  `;

  topRecommendation.querySelectorAll("[data-feedback]").forEach(button => {
    button.addEventListener("click", () => submitFeedback(button.dataset.feedback));
  });
}

function renderList(recommendations) {
  recommendationList.innerHTML = recommendations.map((rec, index) => `
    <article class="mini-card">
      <div>
        <span class="rank">#${index + 1}</span>
        <h3>${escapeHtml(rec.candidate.title)}</h3>
        <p>${escapeHtml(rec.explanation)}</p>
      </div>
      <strong>${pct(rec.ai_score.final_hybrid_score)}</strong>
    </article>
  `).join("");
}

function updateLlmStatus(summary) {
  if (!summary) {
    llmStatus.textContent = "LLM status: waiting";
    llmStatus.className = "status-pill";
    return;
  }

  if (summary.llm_enabled) {
    llmStatus.textContent = "LLM status: enabled";
    llmStatus.className = "status-pill is-on";
  } else if (summary.use_llm || summary.use_llm_explanation) {
    llmStatus.textContent = "LLM status: fallback to local models";
    llmStatus.className = "status-pill is-fallback";
  } else {
    llmStatus.textContent = "LLM status: off";
    llmStatus.className = "status-pill";
  }
}

function showError(error) {
  emptyState.classList.add("hidden");
  topRecommendation.classList.remove("hidden");
  topRecommendation.innerHTML = `
    <p class="eyebrow">API error</p>
    <h2>Personalization could not load.</h2>
    <p class="explanation">${escapeHtml(error.message || "Check that the FastAPI server is running on port 8000.")}</p>
  `;
  responsePreview.textContent = String(error.stack || error.message || error);
}

async function submitFeedback(kind) {
  if (!lastResponse?.recommendations?.length) {
    return;
  }

  const rec = lastResponse.recommendations[0];
  const context = buildPayload().context;
  const statusEl = document.getElementById("feedbackStatus");
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
    context_snapshot: { scenario: scenarioSelect.value }
  };

  if (statusEl) {
    statusEl.textContent = "Sending feedback...";
  }

  try {
    const response = await DemoApi.fetch("/feedback", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    if (!response.ok) {
      throw new Error(`POST /feedback returned ${response.status}`);
    }
    const data = await response.json();
    if (statusEl) {
      statusEl.textContent = `Feedback recorded (${eventType}${converted ? ", converted" : ""}). Total events: ${data.feedback_count}.`;
    }
    renderArchitecturePanels(architecturePanels, lastResponse.request_summary, rec);
  } catch (error) {
    if (statusEl) {
      statusEl.textContent = error.message || "Feedback failed.";
    }
  }
}

async function runPersonalization() {
  const payload = buildPayload();
  updatePreview();
  updateLlmStatus();
  loading.classList.remove("hidden");
  emptyState.classList.add("hidden");
  topRecommendation.classList.add("hidden");
  recommendationList.innerHTML = "";

  try {
    const response = await DemoApi.fetch("/recommend", {
      method: "POST",
      body: JSON.stringify(payload)
    });

    if (!response.ok) {
      throw new Error(`POST /recommend returned ${response.status}`);
    }

    const data = await response.json();
    lastResponse = data;
    responsePreview.textContent = JSON.stringify(data, null, 2);
    updateLlmStatus(data.request_summary);

    if (!data.recommendations.length) {
      throw new Error("The API returned no recommendations for this scenario.");
    }

    const top = data.recommendations[0];
    renderPersonalizedPage(top, data.request_summary);
    renderTopRecommendation(top);
    renderSignals(top);
    renderList(data.recommendations);
    renderArchitecturePanels(architecturePanels, data.request_summary, top);
    topRecommendation.classList.remove("hidden");
  } catch (error) {
    showError(error);
  } finally {
    loading.classList.add("hidden");
  }
}

populateScenarioSelect();
scenarioSelect.addEventListener("change", runPersonalization);
useLlm.addEventListener("change", runPersonalization);
useLlmExplanation.addEventListener("change", runPersonalization);
runBtn.addEventListener("click", runPersonalization);
bannerCta.addEventListener("click", () => document.getElementById("personalized-offer").scrollIntoView({ behavior: "smooth" }));

updatePreview();
runPersonalization();
