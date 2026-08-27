# One-command reproducible environment for SIH judges.
# Build:  docker build -t ewsmart .
# Run:    docker run -p 8000:8000 ewsmart
# Then open http://localhost:8000  (React command centre; /docs = OpenAPI)

# ---- stage 1: build the React frontend -------------------------------------
FROM node:22-slim AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install --no-audit --no-fund
COPY frontend ./
RUN npm run build

# ---- stage 2: python runtime serving API + built SPA ------------------------
FROM python:3.11-slim
WORKDIR /app

COPY pyproject.toml README.md ./
COPY ewsmart ./ewsmart
COPY server ./server
COPY dashboard.py ./
COPY results ./results
COPY figures ./figures
COPY scenarios ./scenarios
COPY --from=web /web/dist ./frontend/dist

RUN python -m pip install --no-cache-dir ".[dash,api]"

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "server.api:app", "--host", "0.0.0.0", "--port", "8000"]
