FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y ffmpeg && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /root/.local/share/argos-translate/packages/
COPY translate-en_pt-1_9.argosmodel /root/.local/share/argos-translate/packages/
COPY translate-pt_en-1_9.argosmodel /root/.local/share/argos-translate/packages/

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

CMD ["waitress-serve", "--threads=1", "--host=0.0.0.0", "--port=5000", "app_google_streaming:app"]
