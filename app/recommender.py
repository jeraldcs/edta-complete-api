from app.models import RankedRecommendation, AIModelBreakdown, ModelPrediction, IntentType, JourneyStage
from app.context_graph import ContextGraph
from app.catalog import DEFAULT_CANDIDATES
from app.ai.intent_model import IntentModel
from app.ai.journey_model import JourneyStageModel
from app.ai.tapl_model import TAPLModel
from app.ai.channel_model import ChannelFitModel
from app.ai.semantic_similarity import SemanticSimilarityModel
from app.ai.outcome_model import OutcomeSimulationModel
from app.ai.ranker_model import FinalRankerModel
from app.eml_scoring import preference_adjustment
from app.eds import EDSScoringEngine
from app.inference.contracts import InferenceResult, RuleTrace
from app.inference.providers.distilled_slm_provider import DistilledSLMProvider
from app.llm.llm_client import LLMClient
from app.llm.slm_client import SLMClient
from app.orchestration import HybridAIOrchestrationEngine
from app.rules.confidence import combined_rules_confidence, rules_signals_used, scenario_rules_ready
from app.rules_engine import RulesEngine
from app.self_distillation import SelfDistillationStore
from app.tapl_audit import TAPLAuditLog


class RecommendationEngine:
    def __init__(self, tapl_audit: TAPLAuditLog | None = None):
        self.intent_model = IntentModel()
        self.journey_model = JourneyStageModel()
        self.tapl_model = TAPLModel()
        self.channel_model = ChannelFitModel()
        self.semantic_model = SemanticSimilarityModel()
        self.outcome_model = OutcomeSimulationModel()
        self.ranker_model = FinalRankerModel()
        self.eds_engine = EDSScoringEngine()
        self.rules = RulesEngine()
        self.distillation = SelfDistillationStore()
        self.slm = SLMClient(rules=self.rules, distillation=self.distillation)
        self.distilled_slm = DistilledSLMProvider(
            distillation=self.distillation,
            rules=self.rules,
            remote_enricher=self.slm.remote_enrich_intent if self.slm.client is not None else None,
        )
        self.llm = LLMClient()
        self.orchestrator = HybridAIOrchestrationEngine()
        self.tapl_audit = tapl_audit
        self.last_inference: InferenceResult | None = None

    def _apply_tkge_context(self, context, graph: ContextGraph):
        updates = {}
        if context.current_intent is None:
            inferred_intent, _ = graph.infer_intent()
            if inferred_intent != IntentType.unknown.value:
                updates["current_intent"] = IntentType(inferred_intent)
        if context.journey_stage is None:
            inferred_journey, _ = graph.infer_journey_stage()
            try:
                updates["journey_stage"] = JourneyStage(inferred_journey)
            except ValueError:
                pass
        if updates:
            return context.model_copy(update=updates)
        return context

    def _prediction_from_enrichment(self, enriched: dict, source: str, context, distill_min_confidence: float, context_text: str):
        intent_label = enriched.get("intent", IntentType.unknown.value)
        journey_label = enriched.get(
            "journey_stage",
            (context.journey_stage or JourneyStage.research).value,
        )
        try:
            intent_label = IntentType(intent_label).value
        except ValueError:
            intent_label = IntentType.unknown.value
        try:
            journey_label = JourneyStage(journey_label).value
        except ValueError:
            journey_label = (context.journey_stage or JourneyStage.research).value
        try:
            confidence = float(enriched.get("confidence", 0.0))
        except (TypeError, ValueError):
            confidence = 0.0
        confidence = max(0.0, min(1.0, confidence))
        intent = ModelPrediction(label=intent_label, confidence=round(confidence, 4), source=source)
        journey = ModelPrediction(label=journey_label, confidence=round(confidence, 4), source=source)
        teacher = "llm" if source == "llm" else "slm"
        self.distillation.learn(context_text, intent, journey, teacher=teacher, min_confidence=distill_min_confidence)
        return intent, journey

    def _resolve_predictions(
        self,
        context,
        context_text: str,
        use_ai_models: bool,
        use_llm: bool,
        use_slm: bool,
        inference_mode: str,
        graph: ContextGraph,
    ):
        policy = self.orchestrator.policy
        distilled_cfg = policy.section("distilled")
        min_overlap = float(distilled_cfg.get("min_token_overlap", 0.35))
        distill_min_confidence = float(distilled_cfg.get("distill_min_confidence", 0.75))

        self.last_inference = None
        distilled_prediction = self.distillation.predict(context_text, min_overlap=min_overlap)
        tkge_intent, tkge_intent_confidence = graph.infer_intent()
        _, _, rules_engine_confidence = self.rules.infer_from_context(context)
        parser_confidence = None
        if isinstance(getattr(context, "channel_context", None), dict):
            stored = context.channel_context.get("parser_confidence")
            if stored is not None:
                parser_confidence = float(stored)

        route = self.orchestrator.choose_route(
            context=context,
            context_text=context_text,
            use_ai_models=use_ai_models,
            use_llm=use_llm,
            use_slm=use_slm,
            llm_enabled=self.llm.enabled,
            slm_enabled=self.slm.enabled,
            distilled_pattern_available=distilled_prediction is not None,
            parser_confidence=parser_confidence,
            tkge_intent_confidence=tkge_intent_confidence,
            tkge_inferred_intent=tkge_intent,
            rules_engine_confidence=rules_engine_confidence,
            inference_mode=inference_mode,
        )

        if route.tier == "llm":
            enriched = self.llm.enrich_intent(context_text)
            if enriched:
                self.orchestrator.record_llm_success()
                intent, journey = self._prediction_from_enrichment(
                    enriched, "llm", context, distill_min_confidence, context_text
                )
                confidence = max(intent.confidence, journey.confidence)
                self.last_inference = InferenceResult(
                    tier="llm",
                    provider="llm_client",
                    intent=intent,
                    journey_stage=journey,
                    confidence=confidence,
                    signals=["llm_teacher"],
                )
                return intent, journey, route
            self.orchestrator.record_llm_failure()

        if route.tier == HybridAIOrchestrationEngine.SLM_TIER:
            intent, journey, inference = self.distilled_slm.infer(context_text, min_overlap=min_overlap)
            self.last_inference = inference
            if inference.sub_source in {"slm_endpoint", "distilled_pattern"}:
                teacher = "slm" if inference.sub_source == "slm_endpoint" else "slm"
                self.distillation.learn(
                    context_text,
                    intent,
                    journey,
                    teacher=teacher,
                    min_confidence=distill_min_confidence,
                )
            return intent, journey, route

        if route.tier == "rules":
            if scenario_rules_ready(context):
                parser_score = float(context.channel_context.get("parser_confidence", 0.9))
                combined = combined_rules_confidence(
                    parser_confidence=parser_score,
                    tkge_intent_confidence=tkge_intent_confidence,
                    rules_engine_confidence=rules_engine_confidence,
                )
                signals = rules_signals_used(
                    parser_confidence=parser_score,
                    tkge_intent_confidence=tkge_intent_confidence,
                    rules_engine_confidence=rules_engine_confidence,
                )
                intent = ModelPrediction(
                    label=context.current_intent.value,
                    confidence=combined,
                    source="rules",
                )
                journey = ModelPrediction(
                    label=context.journey_stage.value,
                    confidence=combined,
                    source="rules",
                )
                self.last_inference = InferenceResult(
                    tier="rules",
                    provider="rules_engine",
                    intent=intent,
                    journey_stage=journey,
                    confidence=combined,
                    signals=signals,
                    rules_fired=[
                        RuleTrace(rule_id="scenario_parser", contribution=parser_score, reason="Scenario NLP parser"),
                        RuleTrace(rule_id="rules_engine", contribution=rules_engine_confidence, reason="Deterministic rules"),
                        RuleTrace(rule_id="tkge_timeline", contribution=tkge_intent_confidence or 0.0, reason="TKGE timeline boost"),
                    ],
                )
                return intent, journey, route

            intent, journey, confidence = self.rules.infer_from_context(context)
            combined = combined_rules_confidence(
                parser_confidence=0.0,
                tkge_intent_confidence=tkge_intent_confidence,
                rules_engine_confidence=confidence,
            )
            intent = intent.model_copy(update={"confidence": combined, "source": "rules"})
            journey = journey.model_copy(update={"confidence": combined, "source": "rules"})
            self.last_inference = InferenceResult(
                tier="rules",
                provider="rules_engine",
                intent=intent,
                journey_stage=journey,
                confidence=combined,
                signals=rules_signals_used(
                    parser_confidence=0.0,
                    tkge_intent_confidence=tkge_intent_confidence,
                    rules_engine_confidence=confidence,
                ),
                rules_fired=[RuleTrace(rule_id="rules_engine", contribution=confidence, reason="Deterministic rules")],
            )
            return intent, journey, route

        if use_ai_models:
            intent, journey = self.intent_model.predict(context_text), self.journey_model.predict(context_text)
            if intent.label == IntentType.unknown.value:
                inferred_intent, inferred_confidence = graph.infer_intent()
                if inferred_intent != IntentType.unknown.value:
                    intent = ModelPrediction(label=inferred_intent, confidence=inferred_confidence, source="ml+tkge")
            if journey.confidence < 0.5 or journey.label == JourneyStage.research.value:
                inferred_journey, inferred_confidence = graph.infer_journey_stage()
                if inferred_confidence >= journey.confidence:
                    journey = ModelPrediction(label=inferred_journey, confidence=inferred_confidence, source="ml+tkge")
            self.distillation.learn(context_text, intent, journey, teacher="local_ml", min_confidence=distill_min_confidence)
            confidence = max(intent.confidence, journey.confidence)
            self.last_inference = InferenceResult(
                tier="ml",
                provider="local_ml",
                intent=intent,
                journey_stage=journey,
                confidence=confidence,
                signals=["local_classifiers", "tkge_timeline"],
            )
            return intent, journey, route

        inferred_intent, inferred_confidence = graph.infer_intent()
        inferred_journey, journey_confidence = graph.infer_journey_stage()
        intent_label = context.current_intent.value if context.current_intent else inferred_intent
        journey_label = context.journey_stage.value if context.journey_stage else inferred_journey
        confidence = 1.0 if context.current_intent or context.journey_stage else max(inferred_confidence, journey_confidence)
        intent = ModelPrediction(label=intent_label, confidence=confidence, source="rules")
        journey = ModelPrediction(label=journey_label, confidence=confidence, source="rules")
        self.last_inference = InferenceResult(
            tier="rules",
            provider="rules_engine",
            intent=intent,
            journey_stage=journey,
            confidence=confidence,
            signals=["input_or_tkge"],
        )
        return intent, journey, route

    def _explain(self, candidate, eds_score, ai_breakdown, reasons, context, context_text: str, use_llm_explanation: bool):
        if use_llm_explanation:
            llm_text = self.llm.explain_recommendation(
                context_text=context_text,
                recommendation_payload={
                    "candidate_id": candidate.id,
                    "candidate_title": candidate.title,
                    "candidate_type": candidate.type,
                    "eds_score": eds_score.model_dump(),
                    "ai_score": ai_breakdown.model_dump(mode="json"),
                    "reason_codes": reasons,
                    "intent": ai_breakdown.intent.label,
                    "journey_stage": ai_breakdown.journey_stage.label,
                    "tapl_action": ai_breakdown.tapl.action.value,
                    "expected_outcome": ai_breakdown.outcome_simulation.expected_outcome_score,
                },
            )
            if llm_text:
                return llm_text, "llm"
            slm_text = self.slm.explain_recommendation(
                context_text=context_text,
                recommendation_payload={
                    "candidate_title": candidate.title,
                    "intent": ai_breakdown.intent.label,
                    "journey_stage": ai_breakdown.journey_stage.label,
                    "tapl_action": ai_breakdown.tapl.action.value,
                    "expected_outcome": ai_breakdown.outcome_simulation.expected_outcome_score,
                },
            )
            if slm_text:
                return slm_text, "slm"

        scenario_keywords = []
        for source in [context.profile_attributes, context.business_context, context.channel_context]:
            keywords = source.get("scenario_keywords") if isinstance(source, dict) else None
            if isinstance(keywords, list):
                scenario_keywords.extend(str(keyword) for keyword in keywords)

        candidate_words = set()
        candidate_words.update(candidate.title.lower().replace("_", " ").split())
        candidate_words.update(candidate.description.lower().replace("_", " ").split())
        for tag in candidate.content_tags:
            candidate_words.update(tag.lower().replace("_", " ").split())

        matched_keywords = []
        for keyword in scenario_keywords:
            normalized = keyword.lower().replace("_", " ")
            if normalized in candidate_words and normalized not in matched_keywords:
                matched_keywords.append(normalized)

        overlap_reasons = [
            reason.replace("context_overlap:", "").replace(",", ", ")
            for reason in reasons
            if reason.startswith("context_overlap:")
        ]
        match_text = ""
        if matched_keywords:
            match_text = f" It matched scenario keywords: {', '.join(matched_keywords[:6])}."
        elif overlap_reasons:
            match_text = f" It matched context terms: {overlap_reasons[0]}."

        domain = context.business_context.get("detected_domain") if isinstance(context.business_context, dict) else None
        domain_text = f" for the {domain} context" if domain else ""

        return (
            f"{candidate.title} was selected{domain_text} because the parsed scenario indicates "
            f"intent={ai_breakdown.intent.label} and journey={ai_breakdown.journey_stage.label}."
            f"{match_text} TAPL action={ai_breakdown.tapl.action.value}, "
            f"expected outcome={ai_breakdown.outcome_simulation.expected_outcome_score:.2f}, "
            f"final score={ai_breakdown.final_hybrid_score:.2f}."
        ), "local_fallback" if use_llm_explanation else "local"

    def _rank_candidate(
        self,
        context,
        candidate,
        graph: ContextGraph,
        context_text: str,
        intent_prediction,
        journey_prediction,
        orchestration,
        use_ai_models: bool,
        use_llm_explanation: bool,
        calibration=None,
    ) -> RankedRecommendation | None:
        if candidate.channel != context.channel:
            return None

        scoring_context = context.model_copy(
            update={"journey_stage": JourneyStage(journey_prediction.label)}
        )
        eds_score, reasons = self.eds_engine.score(
            scoring_context,
            candidate,
            graph,
            intent_prediction.label,
            journey_prediction.label,
        )

        candidate_text = " ".join([
            candidate.title,
            candidate.description,
            " ".join(candidate.content_tags),
        ])

        semantic_score = (
            self.semantic_model.score(context_text, candidate_text)
            if use_ai_models
            else eds_score.context_relevance_score
        )
        tapl = self.tapl_model.evaluate(context, candidate, context_text)
        if self.tapl_audit:
            self.tapl_audit.record(
                subject_id=context.profile_attributes.get("experience_memory_subject"),
                candidate_id=candidate.id,
                channel=context.channel.value,
                decision=tapl,
                policy_source=self.tapl_model.last_policy_source,
            )
        channel_fit = self.channel_model.score(context.channel, candidate.type, candidate.compliance_sensitivity)
        outcome = self.outcome_model.simulate(
            eds_score,
            semantic_score,
            channel_fit,
            tapl,
            candidate,
            calibration=calibration,
        )
        ai_rank_score = (
            self.ranker_model.score(eds_score, semantic_score, channel_fit, tapl, outcome, candidate)
            if use_ai_models
            else eds_score.final_eds_score
        )

        preferences = context.profile_attributes.get("experience_preferences", {})
        preference_delta, preference_reasons = preference_adjustment(
            preferences if isinstance(preferences, dict) else {},
            candidate,
            context.channel,
        )
        if preference_delta:
            ai_rank_score = round(max(0.0, min(1.0, ai_rank_score + preference_delta)), 4)
            reasons.extend(preference_reasons)

        if tapl.action.value in {"suppress", "generic_fallback"}:
            final_hybrid = min(ai_rank_score, 0.15)
            reasons.append("tapl_governance_block_or_fallback")
        elif tapl.action.value == "delay":
            final_hybrid = ai_rank_score * 0.55
            reasons.append("tapl_delay_due_to_fatigue")
        elif tapl.action.value == "soften":
            final_hybrid = ai_rank_score * 0.85
            reasons.append("tapl_soften_recommendation")
        else:
            final_hybrid = ai_rank_score

        ai_breakdown = AIModelBreakdown(
            intent=intent_prediction,
            journey_stage=journey_prediction,
            orchestration=orchestration,
            tapl=tapl,
            semantic_similarity_score=round(semantic_score, 4),
            channel_fit_score=round(channel_fit, 4),
            outcome_simulation=outcome,
            ai_rank_score=round(ai_rank_score, 4),
            final_hybrid_score=round(final_hybrid, 4),
        )

        explanation, explanation_source = self._explain(
            candidate,
            eds_score,
            ai_breakdown,
            reasons,
            context,
            context_text,
            use_llm_explanation,
        )

        return RankedRecommendation(
            candidate=candidate,
            eds_score=eds_score,
            ai_score=ai_breakdown,
            reason_codes=reasons,
            explanation=explanation,
            explanation_source=explanation_source,
        )

    def recommend(
        self,
        context,
        candidates=None,
        limit=3,
        use_ai_models=True,
        use_llm=False,
        use_slm=False,
        use_llm_explanation=False,
        inference_mode="auto",
        calibration=None,
        prior_graph_snapshot=None,
    ):
        candidates = candidates or DEFAULT_CANDIDATES
        graph = ContextGraph(context, prior_snapshot=prior_graph_snapshot)
        context = self._apply_tkge_context(context, graph)
        context_text = graph.to_text()

        intent_prediction, journey_prediction, orchestration = self._resolve_predictions(
            context,
            context_text,
            use_ai_models,
            use_llm,
            use_slm,
            inference_mode,
            graph,
        )

        ranked = []
        for candidate in candidates:
            item = self._rank_candidate(
                context,
                candidate,
                graph,
                context_text,
                intent_prediction,
                journey_prediction,
                orchestration,
                use_ai_models,
                use_llm_explanation,
                calibration=calibration,
            )
            if item:
                ranked.append(item)

        ranked.sort(
            key=lambda r: (
                r.ai_score.final_hybrid_score,
                r.candidate.business_value,
                r.ai_score.semantic_similarity_score,
                r.eds_score.final_eds_score,
            ),
            reverse=True,
        )
        return ranked[:limit]

    def compare_candidates(
        self,
        context,
        candidate_id_a: str,
        candidate_id_b: str,
        use_ai_models=True,
        calibration=None,
        prior_graph_snapshot=None,
    ):
        candidate_a = next((item for item in DEFAULT_CANDIDATES if item.id == candidate_id_a), None)
        candidate_b = next((item for item in DEFAULT_CANDIDATES if item.id == candidate_id_b), None)
        if candidate_a is None or candidate_b is None:
            raise ValueError("Both candidate IDs must exist in the catalog.")

        graph = ContextGraph(context, prior_snapshot=prior_graph_snapshot)
        context = self._apply_tkge_context(context, graph)
        context_text = graph.to_text()
        intent_prediction, journey_prediction, orchestration = self._resolve_predictions(
            context,
            context_text,
            use_ai_models,
            use_llm=False,
            use_slm=False,
            inference_mode="auto",
            graph=graph,
        )

        ranked_a = self._rank_candidate(
            context, candidate_a, graph, context_text,
            intent_prediction, journey_prediction, orchestration,
            use_ai_models, False, calibration,
        )
        ranked_b = self._rank_candidate(
            context, candidate_b, graph, context_text,
            intent_prediction, journey_prediction, orchestration,
            use_ai_models, False, calibration,
        )
        return ranked_a, ranked_b, graph

    def simulate(self, context, candidates=None, calibration=None, prior_graph_snapshot=None):
        return self.recommend(
            context,
            candidates,
            limit=20,
            use_ai_models=True,
            calibration=calibration,
            prior_graph_snapshot=prior_graph_snapshot,
        )
