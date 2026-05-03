FROM python:3.10-slim

WORKDIR /app

# Instala ffmpeg, limpa cache e instala dependências Python numa única camada
RUN apt-get update && apt-get install -y ffmpeg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu \
        Flask==2.3.3 \
        vosk==0.3.45 \
        torch==2.0.1 \
        sentencepiece==0.1.99 \
        argostranslate==1.10.0 \
        numpy==1.24.3 \
        scipy==1.10.1

# Cria diretório para os modelos de tradução Argos
RUN mkdir -p /root/.local/share/argos-translate/packages/

# Copia os modelos de tradução (certifique-se de que os arquivos existem na mesma pasta)
COPY translate-en_pt-1_9.argosmodel /root/.local/share/argos-translate/packages/
COPY translate-pt_en-1_9.argosmodel /root/.local/share/argos-translate/packages/

# Copia o restante do código
COPY . .

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app_vosk_streaming:app"]
