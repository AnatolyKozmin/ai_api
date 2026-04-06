FROM python:3.12-slim-bookworm
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY main.py schemas.py sheets.py logging_config.py .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8011"]
