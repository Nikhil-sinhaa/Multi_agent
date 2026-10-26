# =============================================================================
# Stage 1 — Builder
#   Install all Python dependencies in an isolated layer.
#   This keeps the final image clean and small (no build tools leak in).
# =============================================================================
FROM python:3.11-slim AS builder

WORKDIR /build

# Copy ONLY requirements first — Docker caches this layer.
# If requirements.txt hasn't changed, pip install is skipped on rebuild.
COPY requirements.txt .

RUN pip install --upgrade pip --quiet && \
    pip install --no-cache-dir --prefix=/install -r requirements.txt


# =============================================================================
# Stage 2 — Final (production image)
#   Only the runtime essentials — no build tools, no pip cache.
# =============================================================================
FROM python:3.11-slim AS final

# -- Security: run as a non-root user -----------------------------------------
# Running as root inside a container is a security anti-pattern.
RUN groupadd --system appuser && useradd --system --gid appuser appuser

# -- Copy installed packages from the builder stage ---------------------------
COPY --from=builder /install /usr/local

# -- App directory -------------------------------------------------------------
WORKDIR /app
COPY . .

# Create output dir and hand ownership to the non-root user
RUN mkdir -p travel_plans && chown -R appuser:appuser /app

USER appuser

# -- Runtime environment variables --------------------------------------------
# Real secrets (API keys, DB URL) are injected at runtime via --env-file .env
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

EXPOSE 8501

# -- Health check -------------------------------------------------------------
# Docker (and orchestrators like K8s/ECS) mark the container "unhealthy"
# if Streamlit stops responding, and will auto-restart it.
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health')"

# -- Entrypoint ---------------------------------------------------------------
CMD ["python", "-m", "streamlit", "run", "frontend.py", \
     "--server.headless=true", \
     "--server.fileWatcherType=none", \
     "--server.port=8501", \
     "--server.address=0.0.0.0"]
