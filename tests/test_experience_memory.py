from app.experience_memory import ExperienceMemoryLayer
from app.models import CustomerContext, FeedbackEvent


def test_eml_enriches_context_with_defaults(temp_data_dir):
    memory = ExperienceMemoryLayer(db_path=str(temp_data_dir["db_path"]))
    context = CustomerContext(anonymous_id="anon-test-1")
    enriched, snapshot = memory.enrich_context(context)

    assert snapshot.subject_id == "anonymous:anon-test-1"
    assert enriched.profile_attributes["trust_score"] == snapshot.trust_score


def test_eml_identity_resolution_merges_anonymous_into_customer(temp_data_dir):
    memory = ExperienceMemoryLayer(db_path=str(temp_data_dir["db_path"]))

    anonymous_context = CustomerContext(anonymous_id="anon-merge-1")
    memory.record_recommendations(anonymous_context, [])
    memory.record_feedback(
        FeedbackEvent(
            anonymous_id="anon-merge-1",
            recommendation_id="vehicle_upgrade_suv",
            event_type="click",
            converted=True,
            revenue=50.0,
        )
    )

    linked_context = CustomerContext(customer_id="cust-merge-1", anonymous_id="anon-merge-1")
    snapshot = memory.get_snapshot(linked_context)

    assert snapshot.subject_id == "customer:cust-merge-1"
    assert snapshot.outcomes["clicks"] == 1
    assert snapshot.outcomes["conversions"] == 1


def test_eml_learns_preferences_from_feedback(temp_data_dir):
    memory = ExperienceMemoryLayer(db_path=str(temp_data_dir["db_path"]))
    memory.record_feedback(
        FeedbackEvent(
            anonymous_id="anon-pref-1",
            recommendation_id="vehicle_upgrade_suv",
            event_type="click",
            converted=True,
            revenue=75.0,
        )
    )
    snapshot = memory.get_snapshot(CustomerContext(anonymous_id="anon-pref-1"))
    assert "candidate:vehicle_upgrade_suv" in snapshot.preferences
    assert snapshot.preferences["candidate:vehicle_upgrade_suv"]["weight"] > 0
