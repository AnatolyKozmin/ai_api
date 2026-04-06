FROM python:3.12-slim-bookworm

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py schemas.py sheets.py logging_config.py telethon_jobs_collector.py .

ENV PYTHONUNBUFFERED=1

EXPOSE 8011

# По умолчанию — коллектор; сервис api в docker-compose переопределяет команду на uvicorn.
CMD ["python", "-u", "telethon_jobs_collector.py"]
