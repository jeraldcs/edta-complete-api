from typing import Dict, Any, Set, Optional
from app.models import CustomerContext, IntentType, JourneyStage, TemporalKnowledgeGraphSummary


class ContextGraph:
    def __init__(self, context: CustomerContext, prior_snapshot: Optional[dict[str, Any]] = None):
        self.context = context
        self.nodes: Dict[str, Any] = {}
        self.edges: Dict[str, Set[str]] = {}
        self.temporal_edges: list[tuple[str, str]] = []
        self.journey_sequence: list[str] = []
        if prior_snapshot:
            self.journey_sequence.extend(prior_snapshot.get("journey_sequence", [])[-20:])
        self._build()

    def _add_node(self, key: str, value: Any):
        self.nodes[key] = value
        self.edges.setdefault(key, set())

    def _connect(self, source: str, target: str):
        self.edges.setdefault(source, set()).add(target)

    def _connect_temporal(self, source: str, target: str):
        self.temporal_edges.append((source, target))
        self._connect(source, target)

    def _build(self):
        c = self.context
        self._add_node("channel", c.channel.value)
        self._add_node("journey_stage", c.journey_stage.value if c.journey_stage else "unknown")
        self._add_node("current_intent", c.current_intent.value if c.current_intent else "unknown")

        previous_event_key = None
        for idx, event in enumerate(c.session_events):
            key = f"event:{idx}:{event}"
            self._add_node(key, event)
            self._connect("channel", key)
            if previous_event_key:
                self._connect_temporal(previous_event_key, key)
            previous_event_key = key
            self.journey_sequence.append(str(event))

        for idx, term in enumerate(c.search_terms):
            key = f"search:{idx}:{term.lower()}"
            self._add_node(key, term.lower())
            self._connect("current_intent", key)
            if previous_event_key:
                self._connect_temporal(previous_event_key, key)
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
                self._add_node(node_key, value)
                self._connect("channel", node_key)

        for idx, transaction in enumerate(c.past_transactions):
            transaction_key = f"transaction:{idx}"
            self._add_node(transaction_key, transaction)
            self._connect("journey_stage", transaction_key)
            if previous_event_key:
                self._connect_temporal(previous_event_key, transaction_key)
            previous_event_key = transaction_key

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
        return words

    def to_text(self) -> str:
        return " ".join([
            self.context.channel.value,
            self.context.journey_stage.value if self.context.journey_stage else "unknown",
            self.context.current_intent.value if self.context.current_intent else "unknown",
            " ".join(self.context.session_events),
            " ".join(self.context.search_terms),
            " ".join(sorted(self.keywords())),
        ])

    def infer_intent(self) -> tuple[str, float]:
        text = self.to_text().lower()
        signal_map = {
            IntentType.purchase.value: ["book", "checkout", "buy", "reserve", "quote", "price"],
            IntentType.support.value: ["help", "issue", "maintenance", "return", "repair", "support"],
            IntentType.upgrade.value: ["upgrade", "premium", "suv", "larger", "better"],
            IntentType.retention.value: ["renew", "loyalty", "churn", "cancel", "retain"],
            IntentType.research.value: ["compare", "research", "browse", "learn", "options"],
        }
        best_label = IntentType.unknown.value
        best_hits = 0
        for label, signals in signal_map.items():
            hits = sum(1 for signal in signals if signal in text)
            if hits > best_hits:
                best_label = label
                best_hits = hits
        confidence = min(0.9, 0.25 + best_hits * 0.2) if best_hits else 0.1
        return best_label, round(confidence, 4)

    def next_best_journey_stage(self) -> str | None:
        current = self.context.journey_stage
        if current is None:
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
        confidence = 0.55 if self.journey_sequence else 0.35
        return next_stage or JourneyStage.research.value, confidence

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
            "journey_sequence": self.journey_sequence[-50:],
            "inferred_intent": inferred_intent,
            "inferred_intent_confidence": intent_confidence,
            "inferred_journey_stage": inferred_journey,
            "inferred_journey_confidence": journey_confidence,
            "next_best_journey_stage": self.next_best_journey_stage(),
            "keywords": sorted(list(self.keywords()))[:30],
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
        ).model_dump()
