import os
import json
import tempfile
import subprocess
import time
from flask import Flask, request, render_template, jsonify
import argostranslate.translate
from faster_whisper import WhisperModel

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024

@app.errorhandler(413)
def too_large(e):
    return jsonify({'error': 'Arquivo muito grande. Máximo 100 MB.'}), 413

print("[INFO] Carregando modelo Whisper 'tiny'...")
whisper_model = WhisperModel("tiny", device="cpu", compute_type="int8")
print("[INFO] Modelo Whisper pronto.")

translators = {}

def get_translator(from_code, to_code):
    key = f"{from_code}_{to_code}"
    if key in translators:
        return translators[key]
    translator = argostranslate.translate.get_translation_from_codes(from_code, to_code)
    if translator is None:
        raise Exception(f"Pacote de tradução {from_code}->{to_code} não encontrado.")
    translators[key] = translator
    return translator

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
        print(f"[INFO] Transcrevendo {duration:.2f}s...")
        segments, _ = whisper_model.transcribe(wav_path, language=lang_code, beam_size=5, vad_filter=True)
        text = " ".join(segment.text for segment in segments)
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
            return jsonify({'error': f'Áudio muito longo: {duration:.1f}s (máx 600s)'}), 400

        recognized_text = transcribe_audio(original_tmp, src_lang)
        if not recognized_text or len(recognized_text) < 2:
            return jsonify({'error': 'Nenhuma fala reconhecida. Tente falar mais próximo ao microfone.'}), 400

        translator = get_translator(src_lang, tgt_lang)
        translated_text = translator.translate(recognized_text)
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
