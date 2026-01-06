# Backend Dockerfile
FROM python:3.10-slim

WORKDIR /app

# Install system dependencies (sound libraries if needed, but for server side just processing)
# libsndfile1 might be needed for some audio libs, though wave/scipy use pure python or numpy
RUN apt-get update && apt-get install -y gcc curl

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
