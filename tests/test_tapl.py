from app.ai.tapl_model import TAPLModel
from app.catalog import DEFAULT_CANDIDATES
from app.models import Channel, CustomerContext


def _candidate(candidate_id: str):
    return next(item for item in DEFAULT_CANDIDATES if item.id == candidate_id)


def test_tapl_suppresses_sensitive_content_on_constrained_channel():
    tapl = TAPLModel()
    context = CustomerContext(
        channel=Channel.wearable,
        profile_attributes={"fatigue_count": 1, "trust_score": 0.7},
        consent={"personalization": True},
    )
    candidate = _candidate("obesity_product_hcp_education")
    decision = tapl.evaluate(context, candidate, "healthcare professional education")

    assert decision.action.value == "suppress"
    assert "constrained channel" in decision.reason.lower()


def test_tapl_generic_fallback_without_consent():
    tapl = TAPLModel()
    context = CustomerContext(
        channel=Channel.web,
        consent={"personalization": False},
    )
    candidate = _candidate("vehicle_upgrade_suv")
    decision = tapl.evaluate(context, candidate, "family suv rental")

    assert decision.action.value == "generic_fallback"
    assert "consent" in decision.reason.lower()


def test_tapl_delays_on_high_fatigue():
    tapl = TAPLModel()
    context = CustomerContext(
        channel=Channel.web,
        profile_attributes={"fatigue_count": 8, "trust_score": 0.6},
        consent={"personalization": True},
    )
    candidate = _candidate("vehicle_upgrade_suv")
    decision = tapl.evaluate(context, candidate, "family suv rental")

    assert decision.action.value == "delay"
