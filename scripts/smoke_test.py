import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.models import RecommendationRequest
from app.services.recommendation_handlers import handlers

for file_name in ["web_family_suv.json", "chatbot_booking.json", "iot_maintenance.json"]:
    payload = json.loads(Path(PROJECT_ROOT, "sample_requests", file_name).read_text())
    response = handlers.recommend(RecommendationRequest(**payload), request_id=f"smoke-{file_name}")
    top = response.recommendations[0]
    print(f"{file_name}: {top.candidate.id} | score={top.ai_score.final_hybrid_score}")
