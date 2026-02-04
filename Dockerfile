FROM python:3.11-slim

# System deps required by ocrmypdf pipeline
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-spa \
    tesseract-ocr-eng \
    ghostscript \
    qpdf \
    poppler-utils \
    unpaper \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Render sets $PORT
CMD ["bash", "-lc", "gunicorn app:app --bind 0.0.0.0:${PORT:-10000} --timeout 600 --workers 2 --threads 4 --worker-class gthread"]
