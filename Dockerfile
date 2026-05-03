FROM python:3.10-slim

WORKDIR /app

# Instala ffmpeg (necessário para conversão de áudio)
RUN apt-get update && apt-get install -y ffmpeg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copia os modelos de tradução Argos (já baixados)
RUN mkdir -p /root/.local/share/argos-translate/packages/
COPY translate-en_pt-1_9.argosmodel /root/.local/share/argos-translate/packages/
COPY translate-pt_en-1_9.argosmodel /root/.local/share/argos-translate/packages/

# Copia requirements e instala dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia o resto do código
COPY . .

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app_vosk_streaming:app"]
