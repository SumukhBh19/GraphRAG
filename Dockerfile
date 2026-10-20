FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for PyMuPDF and building extensions
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN python -m spacy download en_core_web_sm || true

COPY backend/ ./backend/
COPY data/ ./data/
COPY schema.md .
COPY .env.example .

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
