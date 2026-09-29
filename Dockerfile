# Convenience container: builds the React command centre, then serves the
# API + built SPA from the Python runtime.
# Build:  docker build -t astra .
# Run:    docker run -p 8000:8000 astra
# Then open http://localhost:8000  (React command centre; /api-docs = OpenAPI)

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
COPY docs ./docs
COPY scenarios ./scenarios
COPY --from=web /web/dist ./frontend/dist

# results/ and figures/ are git-ignored build products, so a fresh clone carries
# neither and a `COPY results ./results` would abort the build outright.  The API
# degrades gracefully on empty directories; mount local artifacts for real data:
#   docker run -p 8000:8000 -v "$PWD/results:/app/results" \
#                          -v "$PWD/figures:/app/figures" astra
RUN mkdir -p results figures

RUN python -m pip install --no-cache-dir .

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "server.api:app", "--host", "0.0.0.0", "--port", "8000"]
