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
ENV PATH="/root/.local/bin:$PATH"

# Tell Python to look inside src/ for packages (src layout)
ENV PYTHONPATH=/app/src

# Copy dependency and package metadata first (layer caching)
COPY pyproject.toml uv.lock ./

# Install third-party dependencies without installing this project yet.
# This keeps the expensive dependency layer cached when application code changes.
RUN uv sync --no-group dev --no-install-project

# Copy the rest of the project, including src/
COPY . .

# Install the local src-layout package after code is present.
RUN uv sync --no-group dev

# Expose FASTAPI port
EXPOSE 8000

# Run the app
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
