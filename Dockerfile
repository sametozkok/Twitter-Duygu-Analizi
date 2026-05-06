FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Sistem bağımlılıkları (curl healthcheck için, build-essential bazı paketler için)
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Bağımlılıkları önce yükle (kod değişse de bu layer cache'lenir)
COPY requirements.txt .
RUN pip install -r requirements.txt

# Backend kaynak kodu
COPY backend/ ./backend/
COPY config.py .

# Veri klasörü (volume mount edilecek)
RUN mkdir -p /app/data/analysis_runs

EXPOSE 8000

CMD ["uvicorn", "backend.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
