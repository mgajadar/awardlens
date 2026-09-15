FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    AWARDLENS_DATABASE_PATH=/app/data/awardlens.duckdb

WORKDIR /app

COPY pyproject.toml README.md LICENSE ./
COPY src ./src
COPY app.py ./app.py
COPY data ./data

RUN pip install --no-cache-dir .

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health')"

CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.port=8501"]

