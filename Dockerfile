FROM python:3.10-slim

WORKDIR /app

# Instala o av via sistema e demais dependências
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    pkg-config \
    ffmpeg \
    python3-av \
    && rm -rf /var/lib/apt/lists/*

# Atualiza pip
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Copia e instala os requisitos (sem av)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "app.py"]
