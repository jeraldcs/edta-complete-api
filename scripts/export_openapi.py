import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import json

from app.main import app

output = ROOT / "openapi.json"
output.write_text(json.dumps(app.openapi(), indent=2, sort_keys=True), encoding="utf-8")
print(f"Wrote {output}")
