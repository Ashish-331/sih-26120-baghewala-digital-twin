FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY ml/ /app/ml/
COPY backend/ /app/backend/

WORKDIR /app/backend

# Automatically train model if missing
RUN python /app/ml/train_classifier.py

EXPOSE 8000

CMD ["./run.sh"]
