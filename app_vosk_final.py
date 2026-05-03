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

# Usar modelos small (já baixados localmente)
MODELS_DIR = 'models'
# Mapeamento direto para os diretórios dos modelos
VOSK_MODELS_PATHS = {
    'en': os.path.join(MODELS_DIR, 'vosk-model-small-en-us-0.15'),
    'pt': os.path.join(MODELS_DIR, 'vosk-model-small-pt-0.3'),
    'es': os.path.join(MODELS_DIR, 'vosk-model-small-es-0.42'),
    'fr': os.path.join(MODELS_DIR, 'vosk-model-small-fr-0.22'),
    'de': os.path.join(MODELS_DIR, 'vosk-model-small-de-0.15'),
}

# Garante que os diretórios existem
for path in VOSK_MODELS_PATHS.values():
    if path and not os.path.exists(path):
        raise Exception(f"Modelo Vosk não encontrado: {path}")

def translate_text(text, from_lang, to_lang):
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
        model_path = VOSK_MODELS_PATHS.get(lang_code)
        if not model_path or not os.path.exists(model_path):
            raise Exception(f"Modelo para idioma {lang_code} não encontrado")
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
