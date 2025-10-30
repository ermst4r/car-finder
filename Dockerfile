FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install uv (package manager)
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:${PATH}"

# Copy project metadata first for better layer caching
COPY pyproject.toml /app/
COPY uv.lock /app/

# Install project dependencies with uv (respect lockfile)
RUN uv sync --frozen --no-dev

# Copy application code
COPY . /app

EXPOSE 8000

# Run via uv (uses the synced virtualenv)
CMD ["uv", "run", "uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]


