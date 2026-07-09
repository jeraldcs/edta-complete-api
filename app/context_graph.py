from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Set

from app.models import CustomerContext, IntentType, JourneyStage, TemporalKnowledgeGraphSummary


class ContextGraph:
    """Temporal knowledge graph built from live context plus persisted subject timeline."""

    JOURNEY_SEQUENCE_LIMIT = 50
    TIMELINE_LIMIT = 40
    PRIOR_OUTCOME_NODE_LIMIT = 80
    RECENCY_HALF_LIFE_HOURS = 72.0

    def __init__(self, context: CustomerContext, prior_snapshot: Optional[dict[str, Any]] = None):
        self.context = context
        self.nodes: Dict[str, Any] = {}
        self.edges: Dict[str, Set[str]] = {}
        self.temporal_edges: list[dict[str, str]] = []
        self.journey_sequence: list[str] = []
        self.node_timestamps: dict[str, str] = {}
        self.timeline: list[dict[str, Any]] = []
        self._last_temporal_node: str | None = None
        self._merge_prior_snapshot(prior_snapshot)
        self._build()

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _parse_iso(value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None

    def _recency_weight(self, at_iso: str | None, *, now: datetime | None = None) -> float:
        timestamp = self._parse_iso(at_iso)
        if timestamp is None:
            return 1.0
        current = now or datetime.now(timezone.utc)
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        age_hours = max(0.0, (current - timestamp).total_seconds() / 3600.0)
        return math.exp(-age_hours / self.RECENCY_HALF_LIFE_HOURS)

    def _merge_prior_snapshot(self, prior_snapshot: dict[str, Any] | None) -> None:
        if not prior_snapshot:
            return

        self.journey_sequence.extend(prior_snapshot.get("journey_sequence", [])[-self.JOURNEY_SEQUENCE_LIMIT :])
        self.timeline.extend(prior_snapshot.get("timeline", [])[-self.TIMELINE_LIMIT :])

        prior_nodes = prior_snapshot.get("nodes", {})
        prior_timestamps = prior_snapshot.get("node_timestamps", {})
        outcome_nodes = [
            (key, value)
            for key, value in prior_nodes.items()
            if key.startswith(("recommendation:", "feedback:", "outcome:"))
        ][-self.PRIOR_OUTCOME_NODE_LIMIT :]
        for key, value in outcome_nodes:
            self.nodes[key] = value
            if key in prior_timestamps:
                self.node_timestamps[key] = prior_timestamps[key]

        prior_edges = prior_snapshot.get("edges", {})
        for source, targets in prior_edges.items():
            if not (
                source.startswith(("recommendation:", "feedback:", "outcome:"))
                or any(str(target).startswith(("recommendation:", "feedback:", "outcome:")) for target in targets)
            ):
                continue
            self.edges.setdefault(source, set()).update(targets)

        for edge in prior_snapshot.get("temporal_edges", []):
            if isinstance(edge, dict):
                normalized = {
                    "source": edge.get("source", ""),
                    "target": edge.get("target", ""),
                    "at": edge.get("at") or self._now_iso(),
                }
            elif isinstance(edge, (list, tuple)) and len(edge) >= 2:
                normalized = {
                    "source": str(edge[0]),
                    "target": str(edge[1]),
                    "at": self._now_iso(),
                }
            else:
                continue
            if normalized["source"] and normalized["target"]:
                self.temporal_edges.append(normalized)
                self.edges.setdefault(normalized["source"], set()).add(normalized["target"])

        if self.timeline:
            last = self.timeline[-1]
            candidate_id = last.get("candidate_id") or last.get("recommendation_id")
            if candidate_id:
                self._last_temporal_node = self._find_latest_node_for_candidate(candidate_id)

    def _find_latest_node_for_candidate(self, candidate_id: str) -> str | None:
        prefix = f"recommendation:"
        matches = [
            key
            for key, value in self.nodes.items()
            if key.startswith(prefix)
            and isinstance(value, dict)
            and value.get("candidate_id") == candidate_id
        ]
        return matches[-1] if matches else None

    def _add_node(self, key: str, value: Any, *, at: str | None = None) -> None:
        self.nodes[key] = value
        self.edges.setdefault(key, set())
        self.node_timestamps[key] = at or self._now_iso()

    def _connect(self, source: str, target: str) -> None:
        self.edges.setdefault(source, set()).add(target)

    def _connect_temporal(self, source: str, target: str, *, at: str | None = None) -> None:
        timestamp = at or self._now_iso()
        self.temporal_edges.append({"source": source, "target": target, "at": timestamp})
        self._connect(source, target)
        self._last_temporal_node = target

    def _append_timeline(self, event: dict[str, Any]) -> None:
        event.setdefault("at", self._now_iso())
        self.timeline.append(event)
        if len(self.timeline) > self.TIMELINE_LIMIT:
            self.timeline = self.timeline[-self.TIMELINE_LIMIT :]

    def record_recommendation(
        self,
        *,
        candidate_id: str,
        title: str,
        tapl_action: str,
        channel: str,
        at: str | None = None,
    ) -> str:
        timestamp = at or self._now_iso()
        node_key = f"recommendation:{timestamp}:{candidate_id}"
        payload = {
            "candidate_id": candidate_id,
            "title": title,
            "tapl_action": tapl_action,
            "channel": channel,
        }
        self._add_node(node_key, payload, at=timestamp)
        self._connect("channel", node_key)
        if self._last_temporal_node:
            self._connect_temporal(self._last_temporal_node, node_key, at=timestamp)
        elif "channel" in self.nodes:
            self._connect_temporal("channel", node_key, at=timestamp)
        self._append_timeline({
            "type": "recommendation",
            "at": timestamp,
            "candidate_id": candidate_id,
            "title": title,
            "tapl_action": tapl_action,
            "channel": channel,
        })
        self.journey_sequence.append(f"recommendation:{candidate_id}")
        return node_key

    def record_feedback(
        self,
        *,
        recommendation_id: str,
        event_type: str,
        converted: bool,
        revenue: float = 0.0,
        channel: str | None = None,
        at: str | None = None,
    ) -> str:
        timestamp = at or self._now_iso()
        node_key = f"feedback:{timestamp}:{recommendation_id}:{event_type}"
        payload = {
            "recommendation_id": recommendation_id,
            "event_type": event_type,
            "converted": converted,
            "revenue": revenue,
            "channel": channel or self.context.channel.value,
        }
        self._add_node(node_key, payload, at=timestamp)
        anchor = self._find_latest_node_for_candidate(recommendation_id) or self._last_temporal_node or "channel"
        self._connect_temporal(anchor, node_key, at=timestamp)
        self._append_timeline({
            "type": "feedback",
            "at": timestamp,
            "recommendation_id": recommendation_id,
            "event_type": event_type,
            "converted": converted,
            "revenue": revenue,
            "channel": channel or self.context.channel.value,
        })
        self.journey_sequence.append(
            f"feedback:{event_type}:{'converted' if converted else 'recorded'}:{recommendation_id}"
        )
        return node_key

    def _build(self) -> None:
        c = self.context
        now = self._now_iso()
        self._add_node("channel", c.channel.value, at=now)
        self._add_node(
            "journey_stage",
            c.journey_stage.value if c.journey_stage else "unknown",
            at=now,
        )
        self._add_node(
            "current_intent",
            c.current_intent.value if c.current_intent else "unknown",
            at=now,
        )

        previous_event_key = self._last_temporal_node
        for idx, event in enumerate(c.session_events):
            key = f"event:{idx}:{event}"
            self._add_node(key, event, at=now)
            self._connect("channel", key)
            if previous_event_key:
                self._connect_temporal(previous_event_key, key, at=now)
            previous_event_key = key
            self.journey_sequence.append(str(event))

        for idx, term in enumerate(c.search_terms):
            key = f"search:{idx}:{term.lower()}"
            self._add_node(key, term.lower(), at=now)
            self._connect("current_intent", key)
            if previous_event_key:
                self._connect_temporal(previous_event_key, key, at=now)
            previous_event_key = key
            self.journey_sequence.append(f"search:{term.lower()}")

        for group_name, group in [
            ("profile", c.profile_attributes),
            ("business", c.business_context),
            ("channel_context", c.channel_context),
            ("device_context", c.device_context),
        ]:
            for key, value in group.items():
                node_key = f"{group_name}:{key}"
                self._add_node(node_key, value, at=now)
                self._connect("channel", node_key)

        for idx, transaction in enumerate(c.past_transactions):
            transaction_key = f"transaction:{idx}"
            self._add_node(transaction_key, transaction, at=now)
            self._connect("journey_stage", transaction_key)
            if previous_event_key:
                self._connect_temporal(previous_event_key, transaction_key, at=now)
            previous_event_key = transaction_key

        if len(self.journey_sequence) > self.JOURNEY_SEQUENCE_LIMIT:
            self.journey_sequence = self.journey_sequence[-self.JOURNEY_SEQUENCE_LIMIT :]

    def keywords(self) -> Set[str]:
        words: Set[str] = set()

        def add_text(value):
            if isinstance(value, str):
                words.update(value.lower().replace("_", " ").replace("-", " ").split())
            elif isinstance(value, dict):
                for inner in value.values():
                    add_text(inner)
            elif isinstance(value, list):
                for inner in value:
                    add_text(inner)
            else:
                words.add(str(value).lower())

        add_text(self.context.session_events)
        add_text(self.context.search_terms)
        add_text(self.context.past_transactions)
        add_text(self.context.profile_attributes)
        add_text(self.context.business_context)
        add_text(self.context.channel_context)
        add_text(self.context.device_context)
        for event in self.timeline:
            add_text(event)
        return words

    def _weighted_terms(self) -> dict[str, float]:
        weights: dict[str, float] = {}
        now = datetime.now(timezone.utc)

        def add_term(term: str, weight: float) -> None:
            normalized = term.lower().strip()
            if normalized:
                weights[normalized] = weights.get(normalized, 0.0) + weight

        def add_text(text: str, weight: float) -> None:
            for term in text.lower().replace("_", " ").replace("-", " ").split():
                add_term(term, weight)

        for event in self.context.session_events:
            add_text(str(event), 1.2)

        for term in self.context.search_terms:
            add_text(str(term), 1.4)

        for timeline_event in self.timeline:
            recency = self._recency_weight(timeline_event.get("at"), now=now)
            if timeline_event.get("type") == "recommendation":
                add_text(timeline_event.get("candidate_id", ""), 1.8 * recency)
                add_text(timeline_event.get("title", ""), 1.5 * recency)
                add_text(timeline_event.get("tapl_action", ""), 1.2 * recency)
            elif timeline_event.get("type") == "feedback":
                add_text(timeline_event.get("event_type", ""), 2.0 * recency)
                if timeline_event.get("converted"):
                    add_term("converted", 2.5 * recency)
                    add_term("purchase", 1.8 * recency)
                if timeline_event.get("event_type") in {"dismiss", "unsubscribe", "complaint"}:
                    add_term("dismiss", 2.0 * recency)

        return weights

    def to_text(self) -> str:
        return " ".join([
            self.context.channel.value,
            self.context.journey_stage.value if self.context.journey_stage else "unknown",
            self.context.current_intent.value if self.context.current_intent else "unknown",
            " ".join(self.context.session_events),
            " ".join(self.context.search_terms),
            " ".join(
                f"{event.get('type')} {event.get('candidate_id') or event.get('recommendation_id') or ''} {event.get('event_type') or ''}"
                for event in self.timeline[-10:]
            ),
            " ".join(sorted(self.keywords())),
        ])

    def infer_intent(self) -> tuple[str, float]:
        weighted_terms = self._weighted_terms()
        text = self.to_text().lower()
        signal_map = {
            IntentType.purchase.value: ["book", "checkout", "buy", "reserve", "quote", "price", "converted", "purchase"],
            IntentType.support.value: ["help", "issue", "maintenance", "return", "repair", "support"],
            IntentType.upgrade.value: ["upgrade", "premium", "suv", "larger", "better"],
            IntentType.retention.value: ["renew", "loyalty", "churn", "cancel", "retain"],
            IntentType.research.value: ["compare", "research", "browse", "learn", "options", "dismiss"],
        }
        best_label = IntentType.unknown.value
        best_score = 0.0
        for label, signals in signal_map.items():
            score = 0.0
            for signal in signals:
                if signal in text:
                    score += 0.35
                score += weighted_terms.get(signal, 0.0)
            if score > best_score:
                best_label = label
                best_score = score
        confidence = min(0.95, 0.15 + best_score * 0.12) if best_score else 0.1
        return best_label, round(confidence, 4)

    def next_best_journey_stage(self) -> str | None:
        current = self.context.journey_stage
        if current is None:
            recent_feedback = [event for event in self.timeline if event.get("type") == "feedback"]
            if recent_feedback and recent_feedback[-1].get("converted"):
                return JourneyStage.retention.value
            return JourneyStage.research.value
        progression = [
            JourneyStage.awareness,
            JourneyStage.research,
            JourneyStage.consideration,
            JourneyStage.purchase,
            JourneyStage.service,
            JourneyStage.retention,
        ]
        try:
            index = progression.index(current)
        except ValueError:
            return JourneyStage.research.value
        return progression[min(index + 1, len(progression) - 1)].value

    def infer_journey_stage(self) -> tuple[str, float]:
        if self.context.journey_stage:
            return self.context.journey_stage.value, 1.0
        next_stage = self.next_best_journey_stage()
        confidence = 0.65 if self.timeline else 0.55 if self.journey_sequence else 0.35
        return next_stage or JourneyStage.research.value, confidence

    def recent_outcomes(self, limit: int = 5) -> list[dict[str, Any]]:
        return self.timeline[-limit:]

    def export(self) -> dict[str, Any]:
        inferred_intent, intent_confidence = self.infer_intent()
        inferred_journey, journey_confidence = self.infer_journey_stage()
        return {
            "subject_context": {
                "customer_id": self.context.customer_id,
                "anonymous_id": self.context.anonymous_id,
                "channel": self.context.channel.value,
            },
            "nodes": self.nodes,
            "edges": {source: sorted(list(targets)) for source, targets in self.edges.items()},
            "temporal_edges": self.temporal_edges,
            "node_timestamps": self.node_timestamps,
            "timeline": self.timeline[-self.TIMELINE_LIMIT :],
            "journey_sequence": self.journey_sequence[-self.JOURNEY_SEQUENCE_LIMIT :],
            "inferred_intent": inferred_intent,
            "inferred_intent_confidence": intent_confidence,
            "inferred_journey_stage": inferred_journey,
            "inferred_journey_confidence": journey_confidence,
            "next_best_journey_stage": self.next_best_journey_stage(),
            "keywords": sorted(list(self.keywords()))[:30],
            "timeline_event_count": len(self.timeline),
            "recent_outcomes": self.recent_outcomes(),
        }

    def summary(self):
        inferred_intent, confidence = self.infer_intent()
        return TemporalKnowledgeGraphSummary(
            node_count=len(self.nodes),
            edge_count=sum(len(v) for v in self.edges.values()),
            temporal_edge_count=len(self.temporal_edges),
            journey_sequence=self.journey_sequence[-20:],
            inferred_intent=inferred_intent,
            inferred_intent_confidence=confidence,
            next_best_journey_stage=self.next_best_journey_stage(),
            keywords=sorted(list(self.keywords()))[:30],
            timeline_event_count=len(self.timeline),
            recent_outcomes=self.recent_outcomes(),
        ).model_dump()
