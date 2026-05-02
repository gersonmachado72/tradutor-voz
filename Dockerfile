FROM python:3.10-slim

WORKDIR /app

# Instala ffmpeg (necessário para conversão) e git (para instalar alguns pacotes)
RUN apt-get update && apt-get install -y ffmpeg git && rm -rf /var/lib/apt/lists/*

# Copia os modelos de tradução (baixados manualmente) para a pasta correta
RUN mkdir -p /root/.local/share/argos-translate/packages/
COPY translate-en_pt-1_9.argosmodel /root/.local/share/argos-translate/packages/
COPY translate-pt_en-1_9.argosmodel /root/.local/share/argos-translate/packages/

# Instala as dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia o resto do código
COPY . .

ENV PORT=5000
EXPOSE 5000

CMD ["gunicorn", "app_vosk_final:app", "--bind", "0.0.0.0:5000"]
