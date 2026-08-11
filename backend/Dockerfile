FROM python:3.10-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /code

# System deps: build tools for a couple of wheels, plus libs pymupdf/reportlab need
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install python deps first for layer caching
COPY pyproject.toml ./
RUN pip install --upgrade pip && pip install ".[dev]"

# App source (bind-mounted over this in compose for hot reload)
COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
