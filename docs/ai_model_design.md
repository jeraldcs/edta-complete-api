# Detailed AI Model Design

## Models included

### 1. Intent Classification Model
Predicts current customer intent: research, purchase, support, retention, upgrade, unknown.

### 2. Journey Stage Classification Model
Predicts journey stage: awareness, research, consideration, purchase, service, retention.

### 3. TAPL Trust Model
Predicts governance action: show, soften, delay, suppress, or generic fallback.

### 4. Channel Fit Model
Scores whether the recommendation is suitable for the channel.

### 5. Outcome Simulation Model
Predicts:
- conversion probability
- revenue impact
- trust impact
- journey impact
- compliance risk
- fatigue risk
- expected outcome score

### 6. Final Ranker Model
Combines EDS, semantic similarity, channel fit, trust score, outcome score, business value, and compliance sensitivity.

### 7. Temporal Knowledge Graph Engine
Builds a time-aware graph from channel, journey, intent, session events, searches, profile attributes, device context, business context, and past transactions. It adds temporal edges for event/search/transaction sequence, infers intent from graph signals, and exposes the next likely journey stage.

### 8. Experience Memory Layer
Persists anonymous and known-user memory in a local JSON store. The memory record includes trust score, fatigue score, preferences, recommendation history, impressions, clicks, conversions, revenue, and last event time. This layer enriches the live context before TAPL, OSE, and ranking.

### 9. Outcome Simulation Engine
Simulates recommendation consequences before execution:
- conversion probability
- revenue impact
- trust impact
- journey impact
- compliance risk
- fatigue risk
- expected outcome score

Memory-backed trust and fatigue now influence both TAPL and outcome simulation, so repeated exposure can delay or soften recommendations before they reach the user.

### 10. Hybrid AI Orchestration Engine
Routes each request through the lowest-cost tier that can reasonably answer:
- Rules for explicit inputs and scenario-parser results
- ML for local trained classifiers
- SLM for distilled local pattern memory
- LLM for rich or ambiguous contexts when OpenAI is enabled

Each ranked recommendation includes the route, route reason, estimated latency, estimated cost units, and whether teacher reasoning was used.

### 11. Self-distilling SLM Strategy
High-confidence LLM or local-ML predictions are stored as local pattern memory. Future similar contexts can use the SLM route instead of calling a frontier LLM, reducing cost, latency, and vendor dependency over time.

## Why this is stronger

The engine does not rely on one black-box AI model. It creates modular AI decision responsibilities, which improves explainability, governance, and enterprise readiness. The new TKGE, EML, OSE, HAOE, and self-distillation layers add temporal reasoning, persistent personalization, pre-execution outcome simulation, cost-aware model routing, and a path toward local SLM autonomy.
