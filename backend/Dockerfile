# Stage 1: Builder
FROM python:3.13-alpine AS builder

# Set locale for consistent behavior and to avoid deprecation warnings
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8

WORKDIR /app

# Install build dependencies for compiling Python packages with C extensions
RUN apk add --no-cache \
    gcc \
    musl-dev \
    linux-headers \
    postgresql-dev \
    libffi-dev \
    openssl-dev \
    cargo \
    rust

# Install uv for faster package management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy requirements and install all dependencies (including dev)
COPY requirements.txt pyproject.toml ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --system -r requirements.txt

# Stage 2: Test
FROM builder AS test

# Copy application code for testing
COPY . .
# ensure config is explicitly included and identifiable
COPY config/ ./config/
# move fallback NAVdata
COPY app/data/NAVAll.txt /data/ || true

COPY start.sh /app
COPY crontab /app/crontab

# Run tests
RUN pytest -v --tb=short --cov=app --cov-report=term-missing

# Stage 3: Runtime
FROM python:3.13-alpine AS runtime

# Set locale for consistent behavior and to avoid deprecation warnings
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8

WORKDIR /app

# Install runtime dependencies
RUN apk add --no-cache \
    curl \
    sqlite \
    libpq \
    bash \
    libffi \
    openssl \
    dcron

# Copy Python packages from builder stage (exclude dev dependencies by copying selectively)
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin/uvicorn /usr/local/bin/
COPY --from=builder /usr/local/bin/casparser /usr/local/bin/
COPY --from=builder /usr/local/bin/alembic /usr/local/bin/

# Copy application code
COPY . .

# Move fallback NAV data
RUN mkdir -p /data && cp /app/app/data/NAVAll.txt /data/ || true

# Make start script executable
RUN chmod +x /app/start.sh && sed -i 's/\r$//' /app/start.sh

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8001/api/health || exit 1

CMD ["/app/start.sh"]
