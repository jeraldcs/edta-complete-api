import csv
from pathlib import Path

import pytest

from app.models import Channel, CustomerContext, IntentType, JourneyStage
from app.rules.packs import RulePackRegistry
from app.rules_engine import RulesEngine
from app.rules_audit import RulesAuditLog
from app.scenario_nlp import ScenarioNLPParser


ROOT = Path(__file__).resolve().parents[1]
SCENARIO_CSV = ROOT / "data" / "scenario_training_master.csv"


def _scenario_context(
    domain: str,
    text: str,
    *,
    intent: IntentType = IntentType.purchase,
    journey: JourneyStage = JourneyStage.consideration,
) -> CustomerContext:
    return CustomerContext(
        anonymous_id="anon-rules-pack",
        channel=Channel.web,
        current_intent=intent,
        journey_stage=journey,
        session_events=[text],
        business_context={"detected_domain": domain},
        channel_context={"source": "free_text_scenario", "parser_confidence": 0.85},
        search_terms=text.lower().split()[:8],
    )


@pytest.mark.parametrize(
    ("domain", "text", "expected_rule", "intent", "journey"),
    [
        ("car_rental", "customer started booking airport rental suv", "car_rental.intent.purchase", IntentType.purchase, JourneyStage.purchase),
        ("hotel", "guest ready to reserve hotel room for tonight", "hotel.intent.purchase", IntentType.purchase, JourneyStage.purchase),
        ("restaurant", "visitor scans qr code at restaurant table menu", "restaurant.intent.purchase", IntentType.purchase, JourneyStage.purchase),
        ("healthcare", "doctor reading obesity product hcp education", "healthcare.intent.research", IntentType.research, JourneyStage.research),
        ("banking", "customer comparing credit card rewards application", "banking.intent.research", IntentType.research, JourneyStage.consideration),
    ],
)
def test_domain_rule_packs_fire_expected_rules(domain, text, expected_rule, intent, journey):
    context = _scenario_context(domain, text, intent=intent, journey=journey)
    result = RulesEngine().infer_with_trace(context, parser_confidence=0.85)
    fired_ids = {trace.rule_id for trace in result.rules_fired}
    assert expected_rule in fired_ids
    assert result.provider == f"rules.{domain}"


def test_disabled_pack_can_be_skipped(tmp_path, monkeypatch):
    index_file = tmp_path / "index.yaml"
    packs_dir = tmp_path / "packs"
    packs_dir.mkdir()
    (packs_dir / "car_rental.yaml").write_text(
        "id: car_rental\ndomain: car_rental\nenabled: true\nrules: []\n",
        encoding="utf-8",
    )
    index_file.write_text(
        "packs_dir: packs\npacks:\n"
        "  - id: car_rental\n    file: car_rental.yaml\n    domain: car_rental\n    priority: 20\n    enabled: false\n",
        encoding="utf-8",
    )
    registry = RulePackRegistry(index_file)
    context = _scenario_context("car_rental", "airport rental booking")
    assert registry.active_packs(context) == []


def test_parser_confidence_merged_into_rules_pipeline():
    context = CustomerContext(
        anonymous_id="anon-parser",
        channel=Channel.web,
        current_intent=IntentType.purchase,
        journey_stage=JourneyStage.purchase,
        channel_context={"source": "free_text_scenario", "parser_confidence": 0.62},
        business_context={"detected_domain": "car_rental"},
    )
    result = RulesEngine().infer_with_trace(context, parser_confidence=0.62, tkge_intent_confidence=0.81)
    assert result.confidence >= 0.81
    assert any(trace.rule_id == "scenario_parser" for trace in result.rules_fired)


def test_rules_audit_log_records_inference(tmp_path):
    db_path = tmp_path / "rules_audit.db"
    audit = RulesAuditLog(db=__import__("app.db", fromlist=["Database"]).Database(db_path))
    audit.record(
        subject_id="customer:test",
        domain="car_rental",
        provider="rules.car_rental",
        intent_label="purchase",
        journey_label="purchase",
        confidence=0.88,
        parser_confidence=0.85,
        tkge_confidence=0.4,
        rules_fired=[],
    )
    assert audit.count() == 1
    recent = audit.recent(limit=1)
    assert recent[0]["provider"] == "rules.car_rental"


@pytest.mark.skipif(not SCENARIO_CSV.exists(), reason="scenario training CSV missing")
def test_scenario_csv_parser_confidence_regression():
    parser = ScenarioNLPParser()
    rows = list(csv.DictReader(SCENARIO_CSV.open(encoding="utf-8")))
    assert rows, "scenario CSV should contain rows"
    passing = 0
    for row in rows:
        _, details = parser.parse(row["scenario_text"])
        if details.get("parser_confidence", 0) >= 0.75:
            passing += 1
    rate = passing / len(rows)
    assert rate >= 0.90, f"parser confidence regression: {rate:.1%} >= 0.75"


@pytest.mark.skipif(not SCENARIO_CSV.exists(), reason="scenario training CSV missing")
def test_scenario_csv_rules_use_parser_labels_when_ready():
    parser = ScenarioNLPParser()
    engine = RulesEngine()
    checked = 0
    for row in csv.DictReader(SCENARIO_CSV.open(encoding="utf-8")):
        context, details = parser.parse(row["scenario_text"])
        result = engine.infer_with_trace(context, parser_confidence=details.get("parser_confidence"))
        assert context.channel_context.get("source") == "free_text_scenario"
        if details.get("parser_confidence", 0) >= 0.75:
            assert result.intent.label == context.current_intent.value
            assert result.confidence >= 0.75
        checked += 1
        if checked >= 30:
            break
    assert checked == 30
