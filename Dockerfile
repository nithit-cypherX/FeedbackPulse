# Multi-stage Dockerfile for FeedbackPulse
# Base images pinned strictly by cryptographic SHA256 digest (no mutable tags).
# CRITICAL SECURITY POLICY:
# - Multi-stage build ensures no build tools or package caches reach the final image.
# - Runs as a non-privileged user (appuser, UID 10001).
# - ZERO CREDENTIALS: No tokens, passwords, or secrets are baked into any layer.
#   All secrets (e.g. SERVICE_TOKEN) arrive strictly at runtime via environment variables.

# --- Stage 1: Build virtual environment ---
FROM python@sha256:bf44cdfcb76cd3b41e879bc058fc37ec5872002ccfde7fcb765e218cde0cd79c AS builder

# Pinned standalone uv binary purely by digest (no tag)
COPY --from=ghcr.io/astral-sh/uv@sha256:61d393e44e249f2e4b526b6c7ddcecce245946826e608e11c93ad4f5bba55b21 /uv /bin/uv

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

# Install only production dependencies (exclude dev and data groups)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-default-groups --no-install-project

# --- Stage 2: Final minimal runtime ---
FROM python@sha256:bf44cdfcb76cd3b41e879bc058fc37ec5872002ccfde7fcb765e218cde0cd79c AS runtime

WORKDIR /app

# Run as non-privileged user for security
RUN groupadd -r appuser && useradd -r -g appuser -u 10001 -m -d /home/appuser appuser

# Copy virtual environment from builder
COPY --from=builder --chown=appuser:appuser /app/.venv /app/.venv

# Environment paths
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/src"

# Default non-sensitive operational configuration
# NOTE: SERVICE_TOKEN is intentionally omitted here — it must be provided at runtime only.
ENV HOST=0.0.0.0
ENV PORT=8000
ENV MODEL_DIR=/app/artifacts/sentiment-6e7ff9fbc17c/model
ENV MODEL_VERSION=sentiment-6e7ff9fbc17c-0110c462

# Copy application source code and verified packaged model artifact
COPY --chown=appuser:appuser src/ /app/src/
COPY --chown=appuser:appuser artifacts/ /app/artifacts/

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=3s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health').read()" || exit 1

CMD ["python", "-m", "uvicorn", "feedbackpulse.api:app", "--host", "0.0.0.0", "--port", "8000"]
