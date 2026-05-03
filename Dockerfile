FROM python:3.10-slim

WORKDIR /app

# Instala ffmpeg (inclui ffprobe) e limpa cache
RUN apt-get update && apt-get install -y ffmpeg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

# Threads=1 para evitar concorrência de memória
CMD ["waitress-serve", "--threads=1", "--host=0.0.0.0", "--port=5000", "app_final:app"]
