from datetime import datetime, timezone

from app.context_graph import ContextGraph
from app.models import Channel, CustomerContext, IntentType


def _base_context(**overrides):
    payload = {
        "anonymous_id": "anon-tkge-1",
        "customer_id": "cust-tkge-1",
        "channel": Channel.web,
        "session_events": ["viewed_vehicle_page", "searched_suv"],
        "search_terms": ["family suv rental"],
    }
    payload.update(overrides)
    return CustomerContext(**payload)


def test_record_recommendation_adds_timeline_and_temporal_edges():
    graph = ContextGraph(_base_context())
    node_key = graph.record_recommendation(
        candidate_id="vehicle_upgrade_suv",
        title="Premium SUV upgrade",
        tapl_action="show",
        channel="web",
        at="2026-07-08T10:00:00+00:00",
    )

    exported = graph.export()
    assert node_key in exported["nodes"]
    assert exported["timeline_event_count"] == 1
    assert exported["timeline"][0]["type"] == "recommendation"
    assert exported["temporal_edges"]
    assert exported["temporal_edges"][-1]["at"] == "2026-07-08T10:00:00+00:00"


def test_record_feedback_links_to_prior_recommendation():
    graph = ContextGraph(_base_context())
    graph.record_recommendation(
        candidate_id="vehicle_upgrade_suv",
        title="Premium SUV upgrade",
        tapl_action="show",
        channel="web",
        at="2026-07-08T10:00:00+00:00",
    )
    graph.record_feedback(
        recommendation_id="vehicle_upgrade_suv",
        event_type="click",
        converted=True,
        revenue=120.0,
        at="2026-07-08T10:05:00+00:00",
    )

    exported = graph.export()
    assert exported["timeline_event_count"] == 2
    assert exported["timeline"][-1]["type"] == "feedback"
    assert exported["timeline"][-1]["converted"] is True
    assert any(edge["target"].startswith("feedback:") for edge in exported["temporal_edges"])


def test_merge_prior_snapshot_keeps_outcome_timeline():
    first = ContextGraph(_base_context(session_events=["searched_suv"]))
    first.record_recommendation(
        candidate_id="vehicle_upgrade_suv",
        title="Premium SUV upgrade",
        tapl_action="show",
        channel="web",
        at="2026-07-08T09:00:00+00:00",
    )
    snapshot = first.export()

    second = ContextGraph(_base_context(session_events=["started_booking"]), prior_snapshot=snapshot)
    exported = second.export()

    assert exported["timeline_event_count"] >= 1
    assert any(item["type"] == "recommendation" for item in exported["timeline"])
    assert any(key.startswith("recommendation:") for key in exported["nodes"])


def test_recent_feedback_convert_biases_intent_toward_purchase():
    graph = ContextGraph(_base_context(current_intent=None, journey_stage=None))
    graph.record_recommendation(
        candidate_id="early_booking_discount",
        title="Early booking discount",
        tapl_action="show",
        channel="web",
        at=datetime.now(timezone.utc).isoformat(),
    )
    graph.record_feedback(
        recommendation_id="early_booking_discount",
        event_type="click",
        converted=True,
        revenue=150.0,
        at=datetime.now(timezone.utc).isoformat(),
    )

    intent, confidence = graph.infer_intent()
    assert intent == IntentType.purchase.value
    assert confidence > 0.3


def test_old_snapshot_temporal_edge_tuples_are_supported():
    prior = {
        "journey_sequence": ["searched_suv"],
        "timeline": [],
        "nodes": {
            "recommendation:old:vehicle_upgrade_suv": {
                "candidate_id": "vehicle_upgrade_suv",
                "title": "Premium SUV upgrade",
                "tapl_action": "show",
                "channel": "web",
            }
        },
        "edges": {"channel": ["recommendation:old:vehicle_upgrade_suv"]},
        "temporal_edges": [("channel", "recommendation:old:vehicle_upgrade_suv")],
        "node_timestamps": {"recommendation:old:vehicle_upgrade_suv": "2026-07-07T12:00:00+00:00"},
    }
    graph = ContextGraph(_base_context(), prior_snapshot=prior)
    exported = graph.export()
    assert "recommendation:old:vehicle_upgrade_suv" in exported["nodes"]
    assert exported["temporal_edges"]


def test_feedback_endpoint_updates_context_graph(client, sample_recommend_payload):
    recommend = client.post("/recommend", json=sample_recommend_payload)
    top_id = recommend.json()["recommendations"][0]["candidate"]["id"]

    response = client.post(
        "/feedback",
        json={
            "anonymous_id": sample_recommend_payload["context"]["anonymous_id"],
            "customer_id": sample_recommend_payload["context"]["customer_id"],
            "recommendation_id": top_id,
            "channel": sample_recommend_payload["context"]["channel"],
            "event_type": "click",
            "converted": True,
            "revenue": 88.0,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["context_graph"]["timeline_event_count"] >= 1
    assert any(item.get("type") == "feedback" for item in payload["context_graph"]["recent_outcomes"])


def test_context_graph_stored_snapshot_includes_timeline(client, sample_recommend_payload):
    client.post("/recommend", json=sample_recommend_payload)
    context = sample_recommend_payload["context"]
    response = client.get(
        "/v1/context-graph",
        params={
            "customer_id": context["customer_id"],
            "anonymous_id": context["anonymous_id"],
        },
    )
    stored = response.json()["stored_snapshot"]
    assert stored["timeline_event_count"] >= 1
    assert stored["recent_outcomes"]
