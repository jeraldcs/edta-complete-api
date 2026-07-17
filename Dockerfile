FROM python:3.12-slim

WORKDIR /app

ARG INSTALL_OTEL=false

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY requirements.txt requirements-observability.txt ./
RUN pip install --no-cache-dir -r requirements.txt \
    && if [ "$INSTALL_OTEL" = "true" ]; then pip install --no-cache-dir -r requirements-observability.txt; fi

COPY app ./app
COPY config ./config
COPY data ./data
COPY scripts ./scripts
COPY static ./static
COPY sample_requests ./sample_requests
COPY pyproject.toml ./

RUN python scripts/train_all_models.py

COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
