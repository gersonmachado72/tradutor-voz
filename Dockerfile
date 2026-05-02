FROM python:3.10-slim

WORKDIR /app

# Instala dependências do sistema: ffmpeg e git (necessário para alguns pacotes)
RUN apt-get update && apt-get install -y ffmpeg git && rm -rf /var/lib/apt/lists/*

# Copia o arquivo de dependências e instala os pacotes Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia todo o conteúdo da aplicação
COPY . .

# Expõe a porta que o Render usará
ENV PORT=5000
EXPOSE 5000

# Comando para iniciar o servidor (substitua 'app_whisper_final.py' se seu arquivo tiver outro nome)
CMD ["gunicorn", "app_whisper_final:app", "--bind", "0.0.0.0:5000"]
