# --- Stage 1: Development ---
FROM python:3.12-slim AS development

WORKDIR /app
ENV PYTHONPATH=/app

RUN pip install --no-cache-dir uv

COPY requirements.txt .
RUN uv pip install --system --no-cache -r requirements.txt

COPY . .

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload", "--reload-dir", "/app/src"]

# --- Stage 2: Production ---
FROM python:3.12-slim AS production

WORKDIR /app
ENV PYTHONPATH=/app

RUN pip install --no-cache-dir uv

COPY requirements.txt .
RUN uv pip install --system --no-cache -r requirements.txt

COPY . .

# Run Alembic migrations then start the server (single worker for in-process scheduler)
CMD ["sh", "-c", "alembic upgrade head && uvicorn src.main:app --host 0.0.0.0 --port 8000"]
