import os
import json
import tempfile
import subprocess
from flask import Flask, request, render_template, jsonify
import numpy as np
from scipy.io import wavfile
from vosk import Model, KaldiRecognizer
from deep_translator import GoogleTranslator

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024

@app.errorhandler(413)
def too_large(e):
    return jsonify({'error': 'Arquivo muito grande. Máximo 100 MB.'}), 413

# Dicionário com modelos Vosk grandes (melhor qualidade)
VOSK_MODELS = {
    'en': 'vosk-model-en-us-0.22',
    'pt': 'vosk-model-pt-0.22',
    'es': 'vosk-model-small-es-0.42',
    'fr': 'vosk-model-small-fr-0.22',
    'de': 'vosk-model-small-de-0.15',
}
MODELS_DIR = 'models'
os.makedirs(MODELS_DIR, exist_ok=True)

def download_vosk_model(lang_code):
    model_name = VOSK_MODELS.get(lang_code)
    if not model_name:
        return None
    model_path = os.path.join(MODELS_DIR, model_name)
    if os.path.exists(model_path):
        return model_path
    url = f"https://alphacephei.com/vosk/models/{model_name}.zip"
    zip_path = os.path.join(MODELS_DIR, f"{model_name}.zip")
    print(f"Baixando modelo {model_name} (pode demorar)...")
    import urllib.request
    import zipfile
    urllib.request.urlretrieve(url, zip_path)
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(MODELS_DIR)
    os.remove(zip_path)
    return model_path

def translate_text(text, from_lang, to_lang):
    """Traduz texto usando Google Tradutor online."""
    try:
        translator = GoogleTranslator(source=from_lang, target=to_lang)
        return translator.translate(text)
    except Exception as e:
        raise Exception(f"Erro na tradução: {e}")

def convert_to_wav(input_path):
    output_path = tempfile.NamedTemporaryFile(suffix='.wav', delete=False).name
    cmd = ['ffmpeg', '-i', input_path, '-ar', '16000', '-ac', '1', '-y', '-loglevel', 'error', output_path]
    subprocess.run(cmd, check=True, capture_output=True, text=True)
    return output_path

def get_audio_duration(file_path):
    try:
        cmd = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', file_path]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            return float(result.stdout.strip())
    except Exception:
        pass
    return 0

def transcribe_audio(file_path, lang_code):
    wav_path = convert_to_wav(file_path)
    try:
        duration = get_audio_duration(wav_path)
        if duration < 0.3:
            return ""
        print(f"[INFO] Transcrevendo {duration:.2f}s com Vosk...")
        model_path = download_vosk_model(lang_code)
        model = Model(model_path)
        rec = KaldiRecognizer(model, 16000)
        rec.SetWords(True)
        sr, audio = wavfile.read(wav_path)
        if sr != 16000:
            print(f"[WARN] Taxa de amostragem inesperada: {sr}")
        audio_int16 = audio.astype(np.int16).tobytes()
        if rec.AcceptWaveform(audio_int16):
            result = json.loads(rec.Result())
            text = result.get('text', '')
        else:
            partial = json.loads(rec.PartialResult())
            text = partial.get('partial', '')
        return text.strip()
    except Exception as e:
        print(f"[ERROR] Falha na transcrição: {e}")
        return ""
    finally:
        if os.path.exists(wav_path):
            os.unlink(wav_path)

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
        if duration < 0.3:
            return jsonify({'error': f'Áudio muito curto: {duration:.2f}s. Fale pelo menos 1 segundo.'}), 400
        if duration > 600:
            return jsonify({'error': f'Áudio muito longo: {duration:.1f}s (máx 600s / 10 min)'}), 400

        recognized_text = transcribe_audio(original_tmp, src_lang)
        if not recognized_text or len(recognized_text) < 2:
            return jsonify({'error': 'Nenhuma fala reconhecida. Tente falar mais próximo ao microfone.'}), 400

        translated_text = translate_text(recognized_text, src_lang, tgt_lang)
        return jsonify({
            'original': recognized_text,
            'translated': translated_text,
            'duration': duration
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if os.path.exists(original_tmp):
            os.unlink(original_tmp)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
