from datetime import datetime, timedelta, timezone

import pytest

from app.catalog import DEFAULT_CANDIDATES
from app.eml_policy import EMLPolicyEngine
from app.eml_scoring import preference_adjustment
from app.experience_memory import ExperienceMemoryLayer
from app.models import (
    AIModelBreakdown,
    Channel,
    CustomerContext,
    FeedbackEvent,
    ModelPrediction,
    OrchestrationDecision,
    OutcomeSimulation,
    TAPLAction,
    TAPLDecision,
)


def _candidate(candidate_id: str = "vehicle_upgrade_suv"):
    return next(item for item in DEFAULT_CANDIDATES if item.id == candidate_id)


@pytest.fixture
def eml_temp_db(tmp_path, monkeypatch):
    db_path = tmp_path / "edta.test.db"
    legacy_memory = tmp_path / "experience_memory.json"
    monkeypatch.setenv("EDTA_DB_PATH", str(db_path))
    monkeypatch.setenv("EXPERIENCE_MEMORY_FILE", str(legacy_memory))
    return db_path


def test_preference_adjustment_boosts_preferred_candidate():
    preferences = {
        "candidate:vehicle_upgrade_suv": {"weight": 2.5},
        "channel:web": {"weight": 1.0},
    }
    adjustment, reasons = preference_adjustment(preferences, _candidate(), Channel.web)
    assert adjustment > 0
    assert "eml_candidate_preference" in reasons


def test_preference_adjustment_penalizes_dismissed_candidate():
    preferences = {"candidate:vehicle_upgrade_suv": {"weight": -2.0}}
    adjustment, reasons = preference_adjustment(preferences, _candidate(), Channel.web)
    assert adjustment < 0
    assert "eml_candidate_preference" in reasons


def test_eml_decay_reduces_fatigue_over_time(eml_temp_db):
    memory = ExperienceMemoryLayer(db_path=str(eml_temp_db))
    store = memory.store
    subject_id = "anonymous:decay-test"
    stale_time = (datetime.now(timezone.utc) - timedelta(hours=96)).isoformat()

    with store.db.transaction() as connection:
        store._upsert_subject(connection, subject_id, "anonymous", {"trust_score": 0.65, "fatigue_score": 0.8})
        store._ensure_outcomes_row(connection, subject_id)
        connection.execute(
            "UPDATE eml_subjects SET updated_at = ? WHERE subject_id = ?",
            (stale_time, subject_id),
        )

    snapshot = memory.get_snapshot(CustomerContext(anonymous_id="decay-test"))
    assert snapshot.fatigue_score < 0.8


def test_eml_learns_category_and_type_preferences_on_convert(eml_temp_db):
    memory = ExperienceMemoryLayer(db_path=str(eml_temp_db))
    memory.record_feedback(
        FeedbackEvent(
            anonymous_id="anon-category-1",
            recommendation_id="vehicle_upgrade_suv",
            event_type="click",
            converted=True,
            revenue=120.0,
        )
    )
    snapshot = memory.get_snapshot(CustomerContext(anonymous_id="anon-category-1"))
    assert "candidate:vehicle_upgrade_suv" in snapshot.preferences
    assert "channel:web" in snapshot.preferences
    assert "type:offer" in snapshot.preferences
    assert any(key.startswith("category:") for key in snapshot.preferences)


def test_eml_delivery_aware_impressions_and_fatigue(eml_temp_db):
    memory = ExperienceMemoryLayer(db_path=str(eml_temp_db))
    store = memory.store
    context = CustomerContext(anonymous_id="anon-exposure-1")

    class StubRecommendation:
        def __init__(self, action: str, candidate_id: str = "vehicle_upgrade_suv"):
            self.candidate = _candidate(candidate_id)
            self.ai_score = AIModelBreakdown(
                intent=ModelPrediction(label="purchase", confidence=0.9, source="test"),
                journey_stage=ModelPrediction(label="consideration", confidence=0.9, source="test"),
                orchestration=OrchestrationDecision(
                    tier="rules",
                    reason="test",
                    estimated_latency_ms=5,
                    estimated_cost_units=0.0,
                ),
                tapl=TAPLDecision(
                    action=TAPLAction(action),
                    trust_score=0.7,
                    fatigue_score=0.2,
                    sensitivity_score=0.1,
                    compliance_score=0.9,
                    reason="test",
                ),
                semantic_similarity_score=0.8,
                channel_fit_score=0.8,
                outcome_simulation=OutcomeSimulation(
                    conversion_probability=0.5,
                    revenue_impact=100.0,
                    trust_impact=0.0,
                    journey_impact=0.0,
                    compliance_risk=0.0,
                    fatigue_risk=0.0,
                    expected_outcome_score=0.5,
                ),
                ai_rank_score=0.7,
                final_hybrid_score=0.7,
            )

    delivered = StubRecommendation("show")
    delayed = StubRecommendation("delay")
    suppressed = StubRecommendation("suppress")

    before = memory.get_snapshot(context)
    memory.record_recommendations(context, [delivered, delayed, suppressed])
    after = memory.get_snapshot(context)

    assert after.outcomes["impressions"] == before.outcomes["impressions"] + 1
    assert after.fatigue_score > before.fatigue_score
    assert len(after.recommendation_history) == 1


def test_preference_enrichment_exposes_learned_preferences(eml_temp_db):
    memory = ExperienceMemoryLayer(db_path=str(eml_temp_db))
    memory.record_feedback(
        FeedbackEvent(
            anonymous_id="anon-rank-1",
            recommendation_id="vehicle_upgrade_suv",
            event_type="click",
            converted=True,
            revenue=100.0,
        )
    )

    context = CustomerContext(anonymous_id="anon-rank-1", channel=Channel.web)
    enriched, snapshot = memory.enrich_context(context)
    preferences = enriched.profile_attributes.get("experience_preferences", {})
    adjustment, reasons = preference_adjustment(preferences, _candidate(), Channel.web)

    assert snapshot.preferences
    assert adjustment > 0
    assert "eml_candidate_preference" in reasons


def test_eml_policy_loads_yaml(tmp_path):
    policy_file = tmp_path / "eml.yaml"
    policy_file.write_text(
        "feedback:\n  click_trust_delta: 0.08\nranking:\n  max_preference_boost: 0.2\n",
        encoding="utf-8",
    )
    engine = EMLPolicyEngine(str(policy_file))
    assert engine.section("feedback")["click_trust_delta"] == 0.08
    assert engine.section("ranking")["max_preference_boost"] == 0.2
