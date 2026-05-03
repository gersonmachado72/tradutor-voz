FROM python:3.10-slim

WORKDIR /app

# Instala ffmpeg e limpa cache
RUN apt-get update && apt-get install -y ffmpeg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copia os modelos de tradução Argos
RUN mkdir -p /root/.local/share/argos-translate/packages/
COPY translate-en_pt-1_9.argosmodel /root/.local/share/argos-translate/packages/
COPY translate-pt_en-1_9.argosmodel /root/.local/share/argos-translate/packages/

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

CMD ["python", "app_google_streaming.py"]
