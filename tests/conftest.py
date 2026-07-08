import json
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session", autouse=True)
def ensure_models():
    model_path = ROOT / "models" / "intent_model.joblib"
    if not model_path.exists():
        subprocess.run(
            [sys.executable, "scripts/train_all_models.py"],
            cwd=ROOT,
            check=True,
        )


@pytest.fixture
def temp_data_dir(tmp_path, monkeypatch):
    db_path = tmp_path / "edta.test.db"
    feedback_file = tmp_path / "feedback_events.json"
    distilled_file = tmp_path / "distilled_slm_memory.json"
    legacy_memory = tmp_path / "experience_memory.json"

    monkeypatch.setenv("EDTA_DB_PATH", str(db_path))
    monkeypatch.setenv("EXPERIENCE_MEMORY_FILE", str(legacy_memory))
    monkeypatch.setenv("FEEDBACK_STORE_FILE", str(feedback_file))
    monkeypatch.setenv("DISTILLED_SLM_FILE", str(distilled_file))
    monkeypatch.setenv("EDTA_RATE_LIMIT_PER_MINUTE", "0")
    monkeypatch.delenv("EDTA_API_KEY", raising=False)

    import app.config
    import app.container
    import app.feedback_store
    import app.graph_store
    import app.self_distillation
    import app.services.recommendation_handlers as recommendation_handlers
    import app.tapl_audit
    from app.container import ServiceContainer
    from app.db import Database
    from app.experience_memory import ExperienceMemoryLayer
    from app.profile.adapters.json_file import JsonFileProfileAdapter
    from app.profile_service import ProfileLookupService
    from app.recommender import RecommendationEngine

    app.config.settings = app.config.Settings()
    database = Database(str(db_path))
    test_container = ServiceContainer()
    test_container.database = database
    test_container.graph_store = app.graph_store.GraphStore(database)
    test_container.tapl_audit = app.tapl_audit.TAPLAuditLog(database)
    test_container.engine = RecommendationEngine(tapl_audit=test_container.tapl_audit)
    test_container.experience_memory = ExperienceMemoryLayer(
        memory_path=str(legacy_memory),
        db_path=str(db_path),
    )
    test_container.feedback_store = app.feedback_store.FeedbackStore(str(feedback_file))
    test_container.engine.distillation = app.self_distillation.SelfDistillationStore(str(distilled_file))
    test_container.profile_service = ProfileLookupService(
        JsonFileProfileAdapter(app.config.settings.profile_lookup_file)
    )
    test_container.event_bus.db = database
    test_container.job_store.db = database

    app.container.container = test_container
    recommendation_handlers.handlers = recommendation_handlers.RecommendationHandlers(test_container)

    return {
        "db_path": db_path,
        "feedback_file": feedback_file,
        "distilled_file": distilled_file,
    }


@pytest.fixture
def client(temp_data_dir):
    from app.main import app

    return TestClient(app)


@pytest.fixture
def sample_recommend_payload():
    path = ROOT / "sample_requests" / "web_family_suv.json"
    return json.loads(path.read_text(encoding="utf-8"))
