# Fully offline-compatible demo after image build; no pip/npm dependencies.
FROM python:3.12.15-slim-bookworm
WORKDIR /app
COPY index.html style.css app.js redesign.js product-rules.js business-data.js passport.js sync.js server.py ./
COPY vendor/ ./vendor/
RUN useradd -r -u 10001 -m appuser && mkdir -p /data && chown appuser:appuser /data
USER appuser
ENV PYTHONDONTWRITEBYTECODE=1 PORT=8080 ALFA_DB_PATH=/data/alfa-bolshe.sqlite
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health', timeout=2)"
CMD ["python", "server.py"]
