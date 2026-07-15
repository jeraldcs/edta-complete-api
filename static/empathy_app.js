(function () {
  const PRESETS = {
    family: {
      text: "Traveling with my 80-year-old grandmother and toddler. Need a rental car for a week-long family trip.",
      destination: "",
      routeMiles: "",
      rentalDays: 7,
    },
    pch: {
      text: "Road trip along the Pacific Coast Highway, just me and my partner. We want something special for the scenic drive.",
      destination: "Pacific Coast Highway",
      routeMiles: 450,
      rentalDays: 5,
    },
    dorm: {
      text: "Moving my kid into their college dorm 3 hours away. Need space for boxes, bins, and a mini-fridge.",
      destination: "",
      routeMiles: 180,
      rentalDays: 2,
    },
    denver: {
      text: "500-mile road trip driving to Denver in winter. Need a safe vehicle for mountain driving.",
      destination: "Denver, CO",
      routeMiles: 500,
      rentalDays: 4,
    },
  };

  const scenarioText = document.getElementById("empathyScenarioText");
  const destinationInput = document.getElementById("empathyDestination");
  const routeMilesInput = document.getElementById("empathyRouteMiles");
  const rentalDaysInput = document.getElementById("empathyRentalDays");
  const runBtn = document.getElementById("empathyRunBtn");
  const statusEl = document.getElementById("empathyStatus");
  const loadingEl = document.getElementById("empathyLoading");
  const hiddenNeedsEl = document.getElementById("empathyHiddenNeeds");
  const enrichmentEl = document.getElementById("empathyEnrichment");
  const tcoEl = document.getElementById("empathyTco");
  const pitchEl = document.getElementById("empathyPitch");

  function setStatus(message, isError) {
    statusEl.textContent = message;
    statusEl.classList.toggle("error", Boolean(isError));
  }

  function setLoading(active) {
    loadingEl.classList.toggle("hidden", !active);
    runBtn.disabled = active;
  }

  function applyPreset(name) {
    const preset = PRESETS[name];
    if (!preset) {
      return;
    }
    scenarioText.value = preset.text;
    destinationInput.value = preset.destination || "";
    routeMilesInput.value = preset.routeMiles === "" ? "" : String(preset.routeMiles);
    rentalDaysInput.value = String(preset.rentalDays);
  }

  function buildPayload() {
    const payload = {
      scenario_text: scenarioText.value.trim(),
      rental_days: Number(rentalDaysInput.value || 3),
    };
    const destination = destinationInput.value.trim();
    const routeMiles = routeMilesInput.value.trim();
    if (destination) {
      payload.destination = destination;
    }
    if (routeMiles) {
      payload.route_miles = Number(routeMiles);
    }
    return payload;
  }

  function renderHiddenNeeds(empathy) {
    const profile = empathy.hidden_needs || {};
    const constraints = profile.implicit_constraints || [];
    const rows = constraints.map(item => `
      <li><strong>${DemoShared.escapeHtml(item.constraint_id.replaceAll("_", " "))}</strong>
      — ${DemoShared.escapeHtml(item.reason || "")}</li>
    `).join("");
    hiddenNeedsEl.innerHTML = `
      <dl>
        <div><dt>Persona</dt><dd>${DemoShared.escapeHtml((profile.persona_tags || []).join(", ") || "None")}</dd></div>
        <div><dt>Standard filter would match</dt><dd>${DemoShared.escapeHtml(profile.standard_filter_match || "Generic category")}</dd></div>
        <div><dt>Confidence</dt><dd>${Math.round(Number(profile.confidence || 0) * 100)}%</dd></div>
        <div><dt>Evidence</dt><dd>${DemoShared.escapeHtml((profile.evidence_phrases || []).join(", ") || "—")}</dd></div>
      </dl>
      <h3>Implicit constraints</h3>
      <ul class="empathy-constraint-list">${rows || "<li>No constraints extracted.</li>"}</ul>
    `;
  }

  function renderEnrichment(empathy) {
    const enrichment = empathy.enrichment || {};
    const weather = enrichment.weather || {};
    const route = enrichment.route || {};
    enrichmentEl.innerHTML = `
      <dl>
        <div><dt>Weather forecast</dt><dd>${DemoShared.escapeHtml(weather.forecast || "clear")} (${DemoShared.escapeHtml(weather.source || "stub")})</dd></div>
        <div><dt>Wind</dt><dd>${DemoShared.escapeHtml(weather.wind_mph ?? 0)} mph</dd></div>
        <div><dt>Weather note</dt><dd>${DemoShared.escapeHtml(weather.note || "—")}</dd></div>
        <div><dt>Max elevation</dt><dd>${DemoShared.escapeHtml(route.max_elevation_ft ?? 0)} ft</dd></div>
        <div><dt>Steep grade</dt><dd>${route.steep_grade ? "Yes" : "No"}</dd></div>
        <div><dt>Route distance</dt><dd>${DemoShared.escapeHtml(route.distance_miles ?? empathy.trip?.distance_miles ?? "—")} mi</dd></div>
        <div><dt>Gas price</dt><dd>$${Number(enrichment.gas_price_usd || 0).toFixed(2)}/gal</dd></div>
        <div><dt>Derived constraints</dt><dd>${DemoShared.escapeHtml((enrichment.derived_constraints || []).join(", ") || "—")}</dd></div>
      </dl>
    `;
  }

  function renderTco(empathy) {
    const comparisons = empathy.tco_comparisons || [];
    if (!comparisons.length) {
      tcoEl.innerHTML = "<p>Add route miles to see fuel and total trip cost.</p>";
      return;
    }
    const rows = comparisons.map(item => `
      <tr>
        <td>${DemoShared.escapeHtml(item.candidate_id.replaceAll("_", " "))}</td>
        <td>$${Number(item.daily_rate_total || 0).toFixed(0)}</td>
        <td>$${Number(item.estimated_fuel_cost || 0).toFixed(0)}</td>
        <td>$${Number(item.total_trip_cost || 0).toFixed(0)}</td>
        <td>${item.net_savings != null ? `$${Number(item.net_savings).toFixed(0)}` : "—"}</td>
      </tr>
    `).join("");
    tcoEl.innerHTML = `
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
    `;
  }

  function renderPitch(data) {
    const empathy = data.empathy || {};
    const topId = (data.top_vehicle_id || "").replaceAll("_", " ");
    const pitch = empathy.empathy_pitch || "No pitch generated.";
    pitchEl.innerHTML = `
      <p class="empathy-top-vehicle"><strong>Top match:</strong> ${DemoShared.escapeHtml(topId || "—")}</p>
      <p>${DemoShared.escapeHtml(pitch)}</p>
    `;
  }

  async function runEmpathy() {
    setLoading(true);
    setStatus("Running empathy engine...");
    try {
      const response = await DemoApi.fetch("/empathy/simulate", {
        method: "POST",
        body: JSON.stringify(buildPayload()),
      });
      if (!response.ok) {
        const detail = await response.text();
        throw new Error(detail || `HTTP ${response.status}`);
      }
      const data = await response.json();
      renderHiddenNeeds(data.empathy || {});
      renderEnrichment(data.empathy || {});
      renderTco(data.empathy || {});
      renderPitch(data);
      setStatus("Empathy engine complete.");
    } catch (error) {
      setStatus(error.message || "Empathy simulation failed.", true);
    } finally {
      setLoading(false);
    }
  }

  document.querySelectorAll(".empathy-preset").forEach(button => {
    button.addEventListener("click", () => {
      applyPreset(button.dataset.preset);
      runEmpathy();
    });
  });

  runBtn.addEventListener("click", runEmpathy);
  applyPreset("family");
  runEmpathy();
})();
