(function () {
  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function pct(value) {
    return `${Math.round(Number(value || 0) * 100)}%`;
  }

  function pretty(value) {
    return String(value || "")
      .replaceAll("_", " ")
      .replace(/\b\w/g, letter => letter.toUpperCase());
  }

  function memoryBlock(memory) {
    if (!memory) {
      return "<p>No experience memory snapshot yet.</p>";
    }

    function preferenceSummary(preferences) {
      if (!preferences || !Object.keys(preferences).length) {
        return "None yet";
      }
      return Object.entries(preferences)
        .sort((left, right) => (right[1]?.weight || 0) - (left[1]?.weight || 0))
        .slice(0, 3)
        .map(([key, value]) => `${escapeHtml(key.replace(/^candidate:|^channel:|^type:|^category:/, ""))} (${Number(value?.weight || 0).toFixed(2)})`)
        .join(", ");
    }

    function historySummary(history) {
      if (!Array.isArray(history) || !history.length) {
        return "None yet";
      }
      return history.slice(-2).map(item => {
        const outcome = item.outcome?.event_type || "shown";
        return `${escapeHtml(item.candidate_id || item.title || "item")}:${escapeHtml(outcome)}`;
      }).join(", ");
    }

    if (memory.before && memory.after) {
      const before = memory.before;
      const after = memory.after;
      return `
        <dl>
          <div><dt>Subject</dt><dd>${escapeHtml(after.subject_id || before.subject_id || "unknown")}</dd></div>
          <div><dt>Trust</dt><dd>${pct(before.trust_score)} → ${pct(after.trust_score)}</dd></div>
          <div><dt>Fatigue</dt><dd>${pct(before.fatigue_score)} → ${pct(after.fatigue_score)}</dd></div>
          <div><dt>Impressions</dt><dd>${escapeHtml(after.outcomes?.impressions ?? before.outcomes?.impressions ?? 0)}</dd></div>
          <div><dt>Top preferences</dt><dd>${preferenceSummary(after.preferences || before.preferences)}</dd></div>
          <div><dt>Recent history</dt><dd>${historySummary(after.recommendation_history || before.recommendation_history)}</dd></div>
        </dl>
      `;
    }
    return `
      <dl>
        <div><dt>Subject</dt><dd>${escapeHtml(memory.subject_id || "unknown")}</dd></div>
        <div><dt>Trust</dt><dd>${pct(memory.trust_score)}</dd></div>
        <div><dt>Fatigue</dt><dd>${pct(memory.fatigue_score)}</dd></div>
        <div><dt>Impressions</dt><dd>${escapeHtml(memory.outcomes?.impressions ?? 0)}</dd></div>
        <div><dt>Top preferences</dt><dd>${preferenceSummary(memory.preferences)}</dd></div>
        <div><dt>Recent history</dt><dd>${historySummary(memory.recommendation_history)}</dd></div>
      </dl>
    `;
  }

  function formatTierMix(tiers) {
    if (!tiers || !Object.keys(tiers).length) {
      return "No routes yet";
    }
    return Object.entries(tiers)
      .map(([tier, count]) => `${escapeHtml(pretty(tier))}: ${escapeHtml(count)}`)
      .join(", ");
  }

  function renderArchitecturePanels(container, summary, topRecommendation) {
    if (!container) {
      return;
    }
    const graph = summary.context_graph || {};
    const memory = summary.experience_memory || {};
    const haoe = summary.haoe || {};
    const oseCalibration = summary.ose_calibration || {};
    const nlp = summary.nlp || {};
    const empathy = summary.empathy || {};
    const trip = empathy.trip || {};
    const enrichment = summary.enrichment || empathy.enrichment || {};
    const scenarioProfile = summary.scenario_profile || {};
    const outcome = topRecommendation?.ai_score?.outcome_simulation || {};
    const orchestration = topRecommendation?.ai_score?.orchestration || {};
    const inference = summary.inference || {};
    const intentSource = inference.intent_source || topRecommendation?.ai_score?.intent?.source || "unknown";
    const journeySource = inference.journey_source || topRecommendation?.ai_score?.journey_stage?.source || "unknown";
    const parserConfidence = nlp.parser_confidence ?? inference.confidence;
    const routeTier = inference.tier || orchestration.tier || haoe.slm_tier_name || "unknown";
    const publicTiers = (haoe.public_tiers || ["rules", "slm", "ml", "llm"]).join(", ");
    const scenarioSnippet = String(summary.scenario_text || "").trim();
    const shortScenario = scenarioSnippet.length > 96
      ? `${scenarioSnippet.slice(0, 95)}…`
      : (scenarioSnippet || "No scenario text");
    const empathyVehicle = empathy.vehicle_recommendation || {};
    const empathyTco = empathyVehicle.tco || {};
    const subjectId = memory.after?.subject_id || memory.before?.subject_id || memory.subject_id || nlp.scenario_subject_id || "unknown";
    const recentOutcomes = (graph.recent_outcomes || []).slice(-3).map(item => {
      const id = item.candidate_id || item.recommendation_id || item.type || "event";
      return `${item.type || "event"}:${id}`;
    }).join(", ") || "None yet";
    const liveJourney = (graph.live_journey_sequence || []).slice(-6);
    const journeyEvents = (liveJourney.length ? liveJourney : (graph.journey_sequence || []).slice(-4))
      .map(item => escapeHtml(String(item)))
      .join(", ") || "None yet";
    const keywords = (nlp.keywords || []).slice(0, 6).join(", ") || "none";
    const personaTags = (graph.empathy_personas || empathy.hidden_needs?.persona_tags || []).join(", ") || "none";
    const routeLabel = trip.route_label || scenarioProfile.objective || (trip.stops?.length ? `${trip.stops.length} stops` : "not inferred");
    const routeMiles = graph.trip_miles ?? trip.distance_miles ?? enrichment.route?.distance_miles ?? "—";
    const parsedIntent = pretty(graph.parsed_intent || nlp.detected_intent || inference.intent_label || "unknown");
    const tkgeIntent = pretty(graph.inferred_intent || inference.intent_label || "unknown");
    const parsedJourney = pretty(graph.parsed_journey_stage || nlp.detected_journey_stage || inference.journey_label || "unknown");
    const tkgeJourney = pretty(graph.next_best_journey_stage || inference.journey_label || "unknown");
    const historicalCvr = oseCalibration.historical_cvr;
    const historicalCvrLabel = historicalCvr > 0 ? pct(historicalCvr) : "No prior conversions for this subject";
    const empathyRanking = empathy.active ? "Active for this scenario" : (empathy.insights_available ? "Insights + vehicle recommendation" : "Insights only");

    container.innerHTML = `
      <article class="architecture-card architecture-card-wide">
        <span class="architecture-label">Scenario context</span>
        <h3>Input driving this run</h3>
        <p class="architecture-scenario-text">${escapeHtml(shortScenario)}</p>
        <dl>
          <div><dt>Detected domain</dt><dd>${escapeHtml(pretty(nlp.detected_domain || inference.domain || "unknown"))}</dd></div>
          <div><dt>Trained profile</dt><dd>${escapeHtml(scenarioProfile.profile_id || graph.scenario_profile_id || "none")}</dd></div>
          <div><dt>EML subject</dt><dd>${escapeHtml(subjectId)}</dd></div>
          <div><dt>Parser</dt><dd>${escapeHtml(pretty(nlp.parser || inference.provider || "rules"))}</dd></div>
          <div><dt>Keywords</dt><dd>${escapeHtml(keywords)}</dd></div>
          <div><dt>Empathy personas</dt><dd>${escapeHtml(personaTags)}</dd></div>
          <div><dt>Route / miles</dt><dd>${escapeHtml(String(routeLabel))} · ${escapeHtml(String(routeMiles))} mi</dd></div>
          <div><dt>Top recommendation</dt><dd>${escapeHtml(topRecommendation?.candidate?.id || empathyVehicle.candidate_id || "pending")}</dd></div>
        </dl>
      </article>
      <article class="architecture-card">
        <span class="architecture-label">TKGE</span>
        <h3>Temporal Knowledge Graph</h3>
        <dl>
          <div><dt>Nodes / edges</dt><dd>${escapeHtml(graph.node_count ?? 0)} / ${escapeHtml(graph.edge_count ?? 0)}</dd></div>
          <div><dt>Temporal edges</dt><dd>${escapeHtml(graph.temporal_edge_count ?? 0)}</dd></div>
          <div><dt>Timeline events</dt><dd>${escapeHtml(graph.timeline_event_count ?? 0)}</dd></div>
          <div><dt>This run journey</dt><dd>${journeyEvents}</dd></div>
          <div><dt>Recent outcomes</dt><dd>${escapeHtml(recentOutcomes)}</dd></div>
          <div><dt>Parsed intent</dt><dd>${escapeHtml(parsedIntent)}</dd></div>
          <div><dt>TKGE inferred intent</dt><dd>${escapeHtml(tkgeIntent)} (${pct(graph.inferred_intent_confidence ?? inference.confidence)})</dd></div>
          <div><dt>Parsed journey</dt><dd>${escapeHtml(parsedJourney)}</dd></div>
          <div><dt>Next TKGE stage</dt><dd>${escapeHtml(tkgeJourney)}</dd></div>
        </dl>
      </article>
      <article class="architecture-card">
        <span class="architecture-label">EML</span>
        <h3>Experience Memory Layer</h3>
        ${memoryBlock(memory)}
      </article>
      <article class="architecture-card">
        <span class="architecture-label">HAOE</span>
        <h3>Hybrid AI Orchestration</h3>
        <dl>
          <div><dt>Route tier</dt><dd>${escapeHtml(pretty(routeTier))}</dd></div>
          <div><dt>Empathy ranking</dt><dd>${escapeHtml(empathyRanking)}</dd></div>
          <div><dt>Public tiers</dt><dd>${escapeHtml(publicTiers)}</dd></div>
          <div><dt>Inference confidence</dt><dd>${inference.confidence != null ? pct(inference.confidence) : "n/a"}</dd></div>
          <div><dt>Rules provider</dt><dd>${escapeHtml(pretty(inference.provider || "n/a"))}</dd></div>
          <div><dt>Rules fired</dt><dd>${escapeHtml((inference.rules_fired || []).slice(0, 4).map(item => item.rule_id).join(", ") || "None for this route tier")}</dd></div>
          <div><dt>Intent / journey source</dt><dd>${escapeHtml(pretty(intentSource))} / ${escapeHtml(pretty(journeySource))}</dd></div>
          <div><dt>Parser confidence</dt><dd>${parserConfidence != null ? pct(parserConfidence) : "n/a"}</dd></div>
          <div><dt>Reason</dt><dd>${escapeHtml(orchestration.reason || inference.signals?.join(", ") || "Scenario parsed and ranked for this travel profile.")}</dd></div>
          <div><dt>Session cost</dt><dd>${escapeHtml(haoe.session_cost_units ?? 0)} / ${escapeHtml(haoe.cost_budget ?? "-")}</dd></div>
        </dl>
      </article>
      <article class="architecture-card">
        <span class="architecture-label">OSE</span>
        <h3>Outcome Simulation Engine</h3>
        <dl>
          <div><dt>Conversion prob.</dt><dd>${pct(outcome.conversion_probability)}</dd></div>
          <div><dt>Revenue impact</dt><dd>$${Number(outcome.revenue_impact || 0).toFixed(0)}</dd></div>
          <div><dt>Expected outcome</dt><dd>${pct(outcome.expected_outcome_score)}</dd></div>
          <div><dt>Historical CVR</dt><dd>${escapeHtml(historicalCvrLabel)}</dd></div>
          <div><dt>Empathy vehicle TCO</dt><dd>${empathyTco.total_trip_cost != null ? `$${Number(empathyTco.total_trip_cost).toFixed(0)}` : "Add route miles for TCO"}</dd></div>
          <div><dt>Hybrid rank score</dt><dd>${pct(topRecommendation?.ai_score?.final_hybrid_score)}</dd></div>
        </dl>
      </article>
    `;
  }

  window.DemoShared = {
    escapeHtml,
    pct,
    pretty,
    renderArchitecturePanels,
    memoryBlock,
  };
})();
