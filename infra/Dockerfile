FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    git curl build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
RUN pip install --no-cache-dir -e .[full]

COPY . .

ENV AEGIS_DATA_DIR=/data
RUN mkdir -p /data

CMD ["python", "run.py"]
