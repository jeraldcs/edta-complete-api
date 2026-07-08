@echo off
pip install -r requirements.txt
python scripts\train_all_models.py
uvicorn app.main:app --reload --port 8000
