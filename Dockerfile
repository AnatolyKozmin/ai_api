FROM python:3.12-slim-bookworm
WORKDIR /app
COPY requirements.txt .
ARG PIP_INDEX_URL=https://pypi.org/simple
RUN pip install --no-cache-dir --default-timeout=300 --retries=25 -i "${PIP_INDEX_URL}" -r requirements.txt
COPY main.py schemas.py sheets.py logging_config.py .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8011"]
