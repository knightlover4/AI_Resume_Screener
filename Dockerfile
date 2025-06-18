# Dockerfile (Optimized to Pre-download ML Model)

# --- Stage 1: Builder ---
FROM python:3.11.8-slim-bullseye AS builder

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

RUN pip install --upgrade pip wheel

COPY requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir=/app/wheels -r requirements.txt


# --- Stage 2: The Final Image ---
FROM python:3.11.8-slim-bullseye

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

# Install dependencies from the pre-compiled wheels
COPY --from=builder /app/wheels /wheels
RUN pip install --no-cache-dir --no-index --find-links=/wheels /wheels/*

# Copy and run the model download script.
COPY download_model.py .
RUN python download_model.py

# Copy the application source code
COPY ./templates ./templates
COPY ./static ./static
COPY main.py .

# Expose the port and run the application
EXPOSE 10000

# --- THE ONLY CHANGE IS ADDING --timeout 120 ---
CMD ["gunicorn", "-w", "1", "-k", "uvicorn.workers.UvicornWorker", "--timeout", "120", "--bind", "0.0.0.0:10000", "main:app"]