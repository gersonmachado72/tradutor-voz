FROM python:3.10-slim

WORKDIR /app

# Instala apenas ffmpeg e ferramentas básicas (nenhuma compilação)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT=5000
EXPOSE 5000

CMD ["gunicorn", "app_whisper_final:app", "--bind", "0.0.0.0:5000"]
