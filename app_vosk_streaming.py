import os
import json
import tempfile
import subprocess
from flask import Flask, request, render_template, jsonify
import numpy as np
from scipy.io import wavfile
import argostranslate.translate
from vosk import Model, KaldiRecognizer

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024

@app.errorhandler(413)
def too_large(e):
    return jsonify({'error': 'Arquivo muito grande. Máximo 100 MB.'}), 413

# Dicionário com modelos Vosk small (leves, ~40 MB cada)
VOSK_MODELS = {
    'en': 'vosk-model-small-en-us-0.15',
    'pt': 'vosk-model-small-pt-0.3',
    'es': 'vosk-model-small-es-0.42',
    'fr': 'vosk-model-small-fr-0.22',
    'de': 'vosk-model-small-de-0.15',
}
MODELS_DIR = 'models'
os.makedirs(MODELS_DIR, exist_ok=True)

translators = {}

def download_vosk_model(lang_code):
    model_name = VOSK_MODELS.get(lang_code)
    if not model_name:
        return None
    model_path = os.path.join(MODELS_DIR, model_name)
    if os.path.exists(model_path):
        return model_path
    # Download automático (ocorre na primeira execução)
    import urllib.request
    import zipfile
    url = f"https://alphacephei.com/vosk/models/{model_name}.zip"
    zip_path = os.path.join(MODELS_DIR, f"{model_name}.zip")
    print(f"Baixando modelo {model_name}...")
    urllib.request.urlretrieve(url, zip_path)
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(MODELS_DIR)
    os.remove(zip_path)
    return model_path

def get_translator(from_code, to_code):
    key = f"{from_code}_{to_code}"
    if key in translators:
        return translators[key]
    translator = argostranslate.translate.get_translation_from_codes(from_code, to_code)
    if translator is None:
        raise Exception(f"Pacote de tradução {from_code}->{to_code} não encontrado. Verifique se os arquivos .argosmodel foram copiados.")
    translators[key] = translator
    return translator

def convert_to_wav(input_path):
    output_path = tempfile.NamedTemporaryFile(suffix='.wav', delete=False).name
    cmd = ['ffmpeg', '-i', input_path, '-ar', '16000', '-ac', '1', '-y', '-loglevel', 'error', output_path]
    subprocess.run(cmd, check=True, capture_output=True, text=True)
    return output_path

def get_audio_duration(file_path):
    """Usa ffprobe para obter duração em segundos."""
    cmd = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', file_path]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
    if result.returncode == 0 and result.stdout.strip():
        try:
            return float(result.stdout.strip())
        except:
            pass
    return 0

def transcribe_audio_streaming(wav_path, lang_code):
    """Transcrição usando Vosk com leitura por chunks (4 KB) para reduzir pico de memória."""
    model_path = download_vosk_model(lang_code)
    model = Model(model_path)
    rec = KaldiRecognizer(model, 16000)
    rec.SetWords(True)
    text_parts = []
    with open(wav_path, 'rb') as f:
        while True:
            data = f.read(4000)  # 4 KB chunks
            if not data:
                break
            if rec.AcceptWaveform(data):
                result = json.loads(rec.Result())
                part = result.get('text', '')
                if part:
                    text_parts.append(part)
    # Resultado final
    final_result = json.loads(rec.FinalResult())
    final_text = final_result.get('text', '')
    if final_text:
        text_parts.append(final_text)
    return ' '.join(text_parts).strip()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/translate', methods=['POST'])
def translate_audio():
    if 'audio' not in request.files:
        return jsonify({'error': 'Nenhum arquivo enviado'}), 400
    file = request.files['audio']
    if file.filename == '':
        return jsonify({'error': 'Nome de arquivo vazio'}), 400

    src_lang = request.form.get('src_lang', 'en')
    tgt_lang = request.form.get('tgt_lang', 'pt')

    with tempfile.NamedTemporaryFile(suffix='.webm', delete=False) as tmp:
        file.save(tmp.name)
        original_tmp = tmp.name

    try:
        duration = get_audio_duration(original_tmp)
        if duration < 0.5:
            return jsonify({'error': f'Áudio muito curto: {duration:.2f}s. Fale pelo menos 1 segundo.'}), 400
        if duration > 600:
            return jsonify({'error': f'Áudio muito longo: {duration:.1f}s (máx 600s / 10 min)'}), 400

        # Converte para WAV mono 16kHz
        wav_path = convert_to_wav(original_tmp)
        try:
            recognized_text = transcribe_audio_streaming(wav_path, src_lang)
        finally:
            if os.path.exists(wav_path):
                os.unlink(wav_path)

        if not recognized_text or len(recognized_text) < 2:
            return jsonify({'error': 'Nenhuma fala reconhecida. Fale mais próximo ao microfone.'}), 400

        translator = get_translator(src_lang, tgt_lang)
        translated_text = translator.translate(recognized_text)
        return jsonify({
            'original': recognized_text,
            'translated': translated_text,
            'duration': duration
        })
    except Exception as e:
        print(f"Erro: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        if os.path.exists(original_tmp):
            os.unlink(original_tmp)

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)
