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

# Copy dependency file first (layer caching)
COPY pyproject.toml .

# Install python dependencies using uv
RUN uv sync --no-dev

# Copy source code
COPY . .

# Expose FASTAPI port
EXPOSE 8000

# Run the app
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
