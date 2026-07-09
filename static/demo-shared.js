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
    const outcome = topRecommendation?.ai_score?.outcome_simulation || {};
    const orchestration = topRecommendation?.ai_score?.orchestration || {};
    const inference = summary.inference || {};
    const intentSource = inference.intent_source || topRecommendation?.ai_score?.intent?.source || "unknown";
    const journeySource = inference.journey_source || topRecommendation?.ai_score?.journey_stage?.source || "unknown";
    const parserConfidence = summary.nlp?.parser_confidence ?? inference.confidence;
    const routeTier = inference.tier || orchestration.tier || haoe.slm_tier_name || "unknown";
    const publicTiers = (haoe.public_tiers || ["rules", "slm", "ml", "llm"]).join(", ");

    container.innerHTML = `
      <article class="architecture-card">
        <span class="architecture-label">TKGE</span>
        <h3>Temporal Knowledge Graph</h3>
        <dl>
          <div><dt>Nodes / edges</dt><dd>${escapeHtml(graph.node_count ?? 0)} / ${escapeHtml(graph.edge_count ?? 0)}</dd></div>
          <div><dt>Temporal edges</dt><dd>${escapeHtml(graph.temporal_edge_count ?? 0)}</dd></div>
          <div><dt>Timeline events</dt><dd>${escapeHtml(graph.timeline_event_count ?? 0)}</dd></div>
          <div><dt>Recent outcomes</dt><dd>${escapeHtml((graph.recent_outcomes || []).slice(-2).map(item => item.type + (item.candidate_id ? `:${item.candidate_id}` : item.recommendation_id ? `:${item.recommendation_id}` : "")).join(", ") || "None")}</dd></div>
          <div><dt>Inferred intent</dt><dd>${escapeHtml(pretty(graph.inferred_intent))} (${pct(graph.inferred_intent_confidence)})</dd></div>
          <div><dt>Next journey stage</dt><dd>${escapeHtml(pretty(graph.next_best_journey_stage || "unknown"))}</dd></div>
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
          <div><dt>Public tiers</dt><dd>${escapeHtml(publicTiers)}</dd></div>
          <div><dt>Sub-source</dt><dd>${escapeHtml(pretty(inference.sub_source || "n/a"))}</dd></div>
          <div><dt>Inference confidence</dt><dd>${inference.confidence != null ? pct(inference.confidence) : "n/a"}</dd></div>
          <div><dt>Rules provider</dt><dd>${escapeHtml(pretty(inference.provider || "n/a"))}</dd></div>
          <div><dt>Rules fired</dt><dd>${escapeHtml((inference.rules_fired || []).slice(0, 4).map(item => item.rule_id).join(", ") || "None yet")}</dd></div>
          <div><dt>ML catalog warmed</dt><dd>${escapeHtml(String(summary.ml_inference?.catalog_warmed ?? "n/a"))}</dd></div>
          <div><dt>SLM mode</dt><dd>${escapeHtml(pretty(summary.llm_status?.slm_engine?.mode || "n/a"))}</dd></div>
          <div><dt>Reason</dt><dd>${escapeHtml(orchestration.reason || "Waiting for recommendation.")}</dd></div>
          <div><dt>Intent / journey source</dt><dd>${escapeHtml(pretty(intentSource))} / ${escapeHtml(pretty(journeySource))}</dd></div>
          <div><dt>Parser confidence</dt><dd>${parserConfidence != null ? pct(parserConfidence) : "n/a"}</dd></div>
          <div><dt>Est. latency</dt><dd>${escapeHtml(orchestration.estimated_latency_ms ?? "-")} ms</dd></div>
          <div><dt>Session cost</dt><dd>${escapeHtml(haoe.session_cost_units ?? 0)} / ${escapeHtml(haoe.cost_budget ?? "-")}</dd></div>
          <div><dt>Circuit breaker</dt><dd>${escapeHtml(haoe.llm_circuit_open ? "Open" : "Closed")}</dd></div>
          <div><dt>Route mix</dt><dd>${formatTierMix(haoe.telemetry?.tiers)}</dd></div>
        </dl>
      </article>
      <article class="architecture-card">
        <span class="architecture-label">OSE</span>
        <h3>Outcome Simulation Engine</h3>
        <dl>
          <div><dt>Conversion prob.</dt><dd>${pct(outcome.conversion_probability)}</dd></div>
          <div><dt>Revenue impact</dt><dd>$${Number(outcome.revenue_impact || 0).toFixed(0)}</dd></div>
          <div><dt>Expected outcome</dt><dd>${pct(outcome.expected_outcome_score)}</dd></div>
          <div><dt>Historical CVR</dt><dd>${pct(oseCalibration.historical_cvr)}</dd></div>
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
