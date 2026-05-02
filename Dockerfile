FROM python:3.10-slim

WORKDIR /app

# Instala FFmpeg e headers de desenvolvimento
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    pkg-config \
    ffmpeg \
    libavformat-dev \
    libavcodec-dev \
    libavutil-dev \
    libswscale-dev \
    libavdevice-dev \
    libavfilter-dev \
    libswresample-dev \
    && rm -rf /var/lib/apt/lists/*

# Atualiza pip e ferramentas de build
RUN pip install --no-cache-dir --upgrade pip setuptools wheel cython

# Instala av sem forçar versão, permitindo que o pip escolha a melhor wheel/compilação
RUN pip install --no-cache-dir --prefer-binary av

# Copia requirements (sem av) e instala
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "app.py"]
