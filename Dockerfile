FROM python:3.11-slim

# Set the working directory
WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && curl -Ls https://astral.sh/uv/install.sh | sh

# Add uv to PATH
ENV VIRTUAL_ENV=/app/.venv
ENV PATH="/app/.venv/bin:/root/.local/bin:$PATH"

# Tell Python to look inside src/ for packages (src layout)
ENV PYTHONPATH=/app/src

# Copy dependency and package metadata first (layer caching)
COPY pyproject.toml uv.lock ./

# Install third-party dependencies without installing this project yet.
# This keeps the expensive dependency layer cached when application code changes.
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-group dev --no-install-project

# Copy the rest of the project, including src/
COPY . .

# Install only the local src-layout package after code is present.
# Source edits should invalidate only this cheap layer, not dependency install.
RUN uv pip install --no-deps -e .

# Expose FASTAPI port
EXPOSE 8000

# Run the app from the already-created virtualenv. Do not run uv sync at startup.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
