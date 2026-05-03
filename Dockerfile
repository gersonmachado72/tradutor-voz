FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia os modelos Vosk (já baixados localmente)
COPY models/ models/

COPY . .

ENV PORT=5000
EXPOSE 5000

# Usa waitress (servidor leve)
CMD ["waitress-serve", "--port=5000", "app_vosk_final:app"]
