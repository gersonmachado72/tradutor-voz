FROM python:3.10-slim

WORKDIR /app

# Instala ffmpeg (necessário para conversão de áudio)
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

# Cria diretório e copia os modelos de tradução Argos (já baixados localmente)
RUN mkdir -p /root/.local/share/argos-translate/packages/
COPY translate-en_pt-1_9.argosmodel /root/.local/share/argos-translate/packages/
COPY translate-pt_en-1_9.argosmodel /root/.local/share/argos-translate/packages/

# Copia requirements e instala dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia todo o código
COPY . .

ENV PORT=5000
EXPOSE 5000

# Comando para iniciar o servidor (usar gunicorn é melhor para produção)
CMD ["gunicorn", "app_vosk_streaming:app", "--bind", "0.0.0.0:5000", "--workers=2", "--threads=2", "--timeout=120"]
