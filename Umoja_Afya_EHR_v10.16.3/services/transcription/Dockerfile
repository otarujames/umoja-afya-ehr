FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg libgomp1 curl \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /service
COPY requirements.txt /service/requirements.txt
RUN pip install --upgrade pip && pip install -r /service/requirements.txt
COPY app.py /service/app.py
RUN useradd --system --uid 10002 --create-home whisper \
    && mkdir -p /models \
    && chown -R whisper:whisper /models /service
USER whisper
EXPOSE 8090
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8090", "--workers", "1", "--no-access-log"]
