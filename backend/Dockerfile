FROM python:3.9-slim
WORKDIR /app

ENV PIP_NO_CACHE_DIR=1 PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

# system deps for psycopg2/pdf tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc libpq-dev poppler-utils \
 && rm -rf /var/lib/apt/lists/*

# install deps first (better layer caching)
COPY backend/requirements.txt .
RUN pip install --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

# add app code
COPY backend/. .

ENV PORT=8000
EXPOSE 8000
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
