FROM python:3.10-slim

WORKDIR /app

# Instala FFmpeg e headers de desenvolvimento (necessários para pkg-config)
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
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Instala o av usando apenas wheel (evita compilação)
RUN pip install --no-cache-dir --only-binary=av av==10.0.0

# Copia e instala os demais requisitos (o av já está instalado, pip não vai recompilar)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "app.py"]
