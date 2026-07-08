#!/bin/sh
set -e

if [ ! -f models/intent_model.joblib ]; then
  echo "Training models (artifacts missing)..."
  python scripts/train_all_models.py
fi

exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --timeout-graceful-shutdown 30
