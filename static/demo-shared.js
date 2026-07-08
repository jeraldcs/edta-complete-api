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
    if (memory.before && memory.after) {
      const before = memory.before;
      const after = memory.after;
      return `
        <dl>
          <div><dt>Subject</dt><dd>${escapeHtml(after.subject_id || before.subject_id || "unknown")}</dd></div>
          <div><dt>Trust</dt><dd>${pct(before.trust_score)} → ${pct(after.trust_score)}</dd></div>
          <div><dt>Fatigue</dt><dd>${pct(before.fatigue_score)} → ${pct(after.fatigue_score)}</dd></div>
          <div><dt>Impressions</dt><dd>${escapeHtml(after.outcomes?.impressions ?? before.outcomes?.impressions ?? 0)}</dd></div>
        </dl>
      `;
    }
    return `
      <dl>
        <div><dt>Subject</dt><dd>${escapeHtml(memory.subject_id || "unknown")}</dd></div>
        <div><dt>Trust</dt><dd>${pct(memory.trust_score)}</dd></div>
        <div><dt>Fatigue</dt><dd>${pct(memory.fatigue_score)}</dd></div>
        <div><dt>Impressions</dt><dd>${escapeHtml(memory.outcomes?.impressions ?? 0)}</dd></div>
      </dl>
    `;
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

    container.innerHTML = `
      <article class="architecture-card">
        <span class="architecture-label">TKGE</span>
        <h3>Temporal Knowledge Graph</h3>
        <dl>
          <div><dt>Nodes / edges</dt><dd>${escapeHtml(graph.node_count ?? 0)} / ${escapeHtml(graph.edge_count ?? 0)}</dd></div>
          <div><dt>Temporal edges</dt><dd>${escapeHtml(graph.temporal_edge_count ?? 0)}</dd></div>
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
          <div><dt>Route tier</dt><dd>${escapeHtml(pretty(orchestration.tier || haoe.distilled_tier_name || "unknown"))}</dd></div>
          <div><dt>Reason</dt><dd>${escapeHtml(orchestration.reason || "Waiting for recommendation.")}</dd></div>
          <div><dt>Est. latency</dt><dd>${escapeHtml(orchestration.estimated_latency_ms ?? "-")} ms</dd></div>
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
