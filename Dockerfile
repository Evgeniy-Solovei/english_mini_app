FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install -r requirements.txt

RUN useradd --create-home --uid 10001 appuser

COPY --chown=appuser:appuser . .

RUN DB_PASSWORD=build-only SECRET_KEY=build-only python manage.py collectstatic --noinput
RUN chmod +x /app/docker/entrypoint.sh && mkdir -p /app/media && chown -R appuser:appuser /app/media

USER appuser

EXPOSE 8000

ENTRYPOINT ["/app/docker/entrypoint.sh"]
CMD ["uvicorn", "config.asgi:application", "--host", "0.0.0.0", "--port", "8000", "--workers", "2", "--proxy-headers", "--forwarded-allow-ips", "*"]
