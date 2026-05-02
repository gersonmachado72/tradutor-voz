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
    && rm -rf /var/lib/apt/lists/*

# Atualiza pip e instala ferramentas de build
RUN pip install --no-cache-dir --upgrade pip setuptools wheel cython

# Instala o av primeiro, usando wheel (sem compilar)
RUN pip install --no-cache-dir --prefer-binary av==10.0.0

# Copia e instala os demais requisitos
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "app.py"]
