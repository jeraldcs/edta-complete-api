# EDTA Complete Package

This package contains the complete end-to-end implementation of the Experience Digital Twin Architecture demo.

## Included

1. FastAPI backend API
2. Detailed AI model layer
3. Training datasets
4. Model training script
5. Web frontend demo with loading spinner
6. Swagger/OpenAPI documentation
7. Architecture documentation

## Main API endpoints

- `GET /` — health check
- `GET /demo` — web demo
- `POST /recommend` — main recommendation API
- `POST /simulate` — simulate all candidate outcomes
- `POST /feedback` — capture user feedback

## AI models included

- Intent Classification Model
- Journey Stage Classification Model
- TAPL Trust/Governance Model
- Channel Fit Model
- Semantic Similarity Model
- Outcome Simulation Model
- Final Recommendation Ranker

## Run locally

```bash
pip install -r requirements.txt
python scripts/train_all_models.py
uvicorn app.main:app --reload --port 8000
```

Open:

```text
http://localhost:8000/demo
http://localhost:8000/docs
```
