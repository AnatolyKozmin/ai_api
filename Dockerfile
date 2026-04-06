FROM python:3.12-slim-bookworm

WORKDIR /app

# Медленный/нестабильный канал до pypi.org: увеличен таймаут и число повторов.
# Другое зеркало: docker compose build --build-arg PIP_INDEX_URL=https://...
ARG PIP_INDEX_URL=https://pypi.org/simple

COPY requirements.txt .
RUN pip install --no-cache-dir \
    --default-timeout=300 \
    --retries=20 \
    -i "${PIP_INDEX_URL}" \
    -r requirements.txt

COPY main.py schemas.py sheets.py logging_config.py .

ENV PYTHONUNBUFFERED=1

EXPOSE 8011

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8011"]
