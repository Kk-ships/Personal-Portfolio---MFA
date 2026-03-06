# Stage 1: Builder
FROM python:3.11-alpine AS builder

# Set locale for consistent behavior and to avoid deprecation warnings
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8

WORKDIR /app

# Install build dependencies for compiling Python packages with C extensions
RUN apk add --no-cache gcc musl-dev linux-headers postgresql-dev

# Install dependencies in a virtual environment with cache mount for faster rebuilds
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip wheel && \
    pip wheel --wheel-dir=/tmp/wheels -r requirements.txt && \
    pip install --user --no-index --find-links=/tmp/wheels -r requirements.txt

# Stage 2: Runtime
FROM python:3.11-alpine

# Set locale for consistent behavior and to avoid deprecation warnings
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8

WORKDIR /app

# Install only runtime dependencies (curl for healthcheck, sqlite for database)
RUN apk add --no-cache curl sqlite libpq bash

# Copy Python packages from builder stage
COPY --from=builder /root/.local /root/.local

# Copy application code
COPY . .
# move fallback NAVdata
COPY /app/data/NAVAll.txt /data/

COPY start.sh /app

RUN chmod +x /app/start.sh && sed -i 's/\r$//' /app/start.sh

# Make sure scripts in .local are usable
ENV PATH=/root/.local/bin:$PATH

CMD ["/app/start.sh"]
