# ── Build stage ──────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt


# ── Runtime stage ────────────────────────────────────────────────
FROM python:3.11-slim

# Non-root user for security
RUN useradd --create-home appuser
WORKDIR /app
USER appuser

# Copy installed packages from builder
COPY --from=builder /root/.local /home/appuser/.local
ENV PATH=/home/appuser/.local/bin:$PATH

# Copy project source
COPY scripts/ ./scripts/
COPY data/     ./data/

# Matplotlib backend — headless
ENV MPLBACKEND=Agg

# Create output directories
RUN mkdir -p output/charts output/reports

# Default command: generate data then run the full pipeline
CMD ["sh", "-c", "python scripts/generate_data.py && python scripts/pipeline.py"]
