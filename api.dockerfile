FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir flask docker

COPY api.py .

ENTRYPOINT python api.py
