FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Sistem bağımlılıkları + pip install tek RUN'da:
# build-essential pip install için gerek, sonra purge → image ~400 MB küçülür.
# curl healthcheck için runtime'da kalır.
COPY requirements.txt .
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential curl \
    && pip install -r requirements.txt \
    && apt-get purge -y --auto-remove build-essential \
    && rm -rf /var/lib/apt/lists/* /root/.cache/pip

# Backend kaynak kodu
COPY backend/ ./backend/
COPY config.py .

# Veri klasörü (volume mount edilecek)
RUN mkdir -p /app/data/analysis_runs

EXPOSE 8000

CMD ["uvicorn", "backend.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
