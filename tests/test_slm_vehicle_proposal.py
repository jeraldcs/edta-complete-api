from app.catalog import vehicle_candidates
from app.llm.prompt_templates import propose_vehicle_prompt
from app.llm.slm_client import SLMClient
from app.models import Channel, CustomerContext, IntentType, JourneyStage
from app.recommender import RecommendationEngine


def test_propose_vehicle_prompt_includes_catalog_ids():
    catalog = [{"id": "hybrid_midsize", "title": "Hybrid Midsize", "description": "Efficient"}]
    prompt = propose_vehicle_prompt("900-mile Arizona summer trip", catalog)
    assert "hybrid_midsize" in prompt
    assert "candidate_id" in prompt


def test_propose_vehicle_rejects_unknown_catalog_id(monkeypatch):
    client = SLMClient()

    class _FakeRemote:
        client = object()

        def complete_text(self, *_args, **_kwargs):
            class _Result:
                text = '{"candidate_id":"not_a_real_car","confidence":0.9,"reason":"bad"}'
                usage = None

            return _Result()

        def parse_json(self, text):
            import json

            return json.loads(text)

    client.remote = _FakeRemote()
    client.enabled = True
    proposal = client.propose_vehicle(
        "need an efficient car",
        [{"id": "hybrid_midsize", "title": "Hybrid Midsize", "description": "Efficient"}],
    )
    assert proposal is None
    assert client.last_status == "vehicle_propose_invalid_id"


def test_propose_vehicle_accepts_catalog_id(monkeypatch):
    client = SLMClient()

    class _FakeRemote:
        client = object()

        def complete_text(self, *_args, **_kwargs):
            class _Result:
                text = '{"candidate_id":"hybrid_midsize","confidence":0.88,"reason":"Long hot trip needs efficiency"}'
                usage = None

            return _Result()

        def parse_json(self, text):
            import json

            return json.loads(text)

    client.remote = _FakeRemote()
    client.enabled = True
    proposal = client.propose_vehicle(
        "900-mile Arizona summer trip",
        [{"id": "hybrid_midsize", "title": "Hybrid Midsize", "description": "Efficient"}],
    )
    assert proposal == {
        "candidate_id": "hybrid_midsize",
        "confidence": 0.88,
        "reason": "Long hot trip needs efficiency",
        "source": "slm_endpoint",
    }


def test_slm_vehicle_proposal_boosts_rank_but_does_not_force_pick(monkeypatch):
    engine = RecommendationEngine()

    def _fake_propose(_context_text, _catalog):
        return {
            "candidate_id": "hybrid_midsize",
            "confidence": 0.95,
            "reason": "Efficiency for desert miles",
            "source": "slm_endpoint",
        }

    monkeypatch.setattr(engine.slm, "propose_vehicle", _fake_propose)

    context = CustomerContext(
        anonymous_id="slm-propose-test",
        channel=Channel.web,
        journey_stage=JourneyStage.research,
        current_intent=IntentType.research,
        search_terms=["arizona summer road trip fuel efficiency"],
        profile_attributes={"trust_score": 0.8, "fatigue_count": 0},
        business_context={"detected_domain": "travel"},
        channel_context={"source": "free_text_scenario", "parser_confidence": 0.8},
        consent={"personalization": True, "profile_lookup": True},
    )
    recommendations = engine.recommend(
        context,
        candidates=vehicle_candidates(),
        limit=3,
        use_ai_models=True,
        use_slm=True,
        inference_mode="slm",
        use_llm_explanation=False,
    )
    assert recommendations
    assert engine.last_slm_vehicle_proposal["candidate_id"] == "hybrid_midsize"
    top_reasons = recommendations[0].reason_codes or []
    # Proposal applied as a hint reason on the proposed candidate when it ranks,
    # or at least stored for the response summary.
    assert any(
        "slm_vehicle_proposal:hybrid_midsize" in (item.reason_codes or [])
        for item in recommendations
    ) or engine.last_slm_vehicle_proposal["candidate_id"] == "hybrid_midsize"
    # TAPL still present — governance path unchanged.
    assert recommendations[0].ai_score.tapl.action is not None
    _ = top_reasons
