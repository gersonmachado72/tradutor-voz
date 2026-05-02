FROM python:3.10-slim

WORKDIR /app

# Instala dependências do sistema: ffmpeg + bibliotecas de desenvolvimento (necessárias para PyAV)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    pkg-config \
    libavcodec-dev \
    libavformat-dev \
    libavutil-dev \
    libswresample-dev \
    libavdevice-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copia o arquivo de dependências e instala os pacotes Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia todo o conteúdo da aplicação
COPY . .

ENV PORT=5000
EXPOSE 5000

CMD ["gunicorn", "app_whisper_final:app", "--bind", "0.0.0.0:5000"]
