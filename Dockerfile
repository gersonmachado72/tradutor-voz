FROM python:3.10-slim

WORKDIR /app

# Instala dependências de sistema para compilar o PyAV (av) e outras libs
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    pkg-config \
    libavformat-dev \
    libavcodec-dev \
    libavutil-dev \
    libswscale-dev \
    libavdevice-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Ajuste o comando CMD conforme o entrypoint do seu app (exemplo para Flask)
CMD ["python", "app.py"]
