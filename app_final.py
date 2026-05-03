import os
import tempfile
import subprocess
from flask import Flask, request, render_template, jsonify
import speech_recognition as sr
from googletrans import Translator

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50 MB (aumentado)

translator = Translator()

def get_audio_duration(file_path):
    """Retorna a duração do áudio em segundos usando ffprobe."""
    cmd = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
           '-of', 'default=noprint_wrappers=1:nokey=1', file_path]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        if result.returncode == 0 and result.stdout.strip():
            return float(result.stdout.strip())
    except Exception:
        pass
    return 0

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/translate', methods=['POST'])
def translate():
    if 'audio' not in request.files:
        return jsonify({'error': 'Nenhum arquivo enviado'}), 400
    audio = request.files['audio']
    if audio.filename == '':
        return jsonify({'error': 'Arquivo vazio'}), 400

    src_lang = request.form.get('src_lang', 'pt')
    tgt_lang = request.form.get('tgt_lang', 'en')

    # Salva o arquivo temporariamente
    with tempfile.NamedTemporaryFile(suffix='.webm', delete=False) as tmp:
        audio.save(tmp.name)
        input_file = tmp.name

    try:
        # Verifica duração ANTES de converter (rápido)
        duration = get_audio_duration(input_file)
        if duration <= 0:
            # Se falhar, tenta após conversão (fallback)
            pass
        elif duration > 300:  # 5 minutos máximo
            return jsonify({'error': f'Áudio muito longo: {duration:.1f}s (máx 300s / 5 min)'}), 400
        elif duration < 0.8:
            return jsonify({'error': f'Áudio muito curto: {duration:.2f}s. Grave por pelo menos 1 segundo.'}), 400

        # Converte para WAV com timeout de 60 segundos (para arquivos grandes)
        wav_file = input_file + ".wav"
        cmd = ['ffmpeg', '-i', input_file, '-ar', '16000', '-ac', '1', '-y',
               '-loglevel', 'error', wav_file]
        try:
            subprocess.run(cmd, check=True, timeout=60, capture_output=True, text=True)
        except subprocess.TimeoutExpired:
            return jsonify({'error': 'Tempo limite excedido na conversão do áudio (arquivo muito grande).'}), 400
        except subprocess.CalledProcessError as e:
            return jsonify({'error': f'Erro na conversão: {e.stderr}'}), 400

        # Reconhecimento de fala
        recognizer = sr.Recognizer()
        with sr.AudioFile(wav_file) as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            audio_data = recognizer.record(source)

        lang_map = {'pt': 'pt-BR', 'en': 'en-US', 'es': 'es-ES', 'fr': 'fr-FR', 'de': 'de-DE'}
        language = lang_map.get(src_lang, 'en-US')
        recognized_text = recognizer.recognize_google(audio_data, language=language)

        if not recognized_text:
            return jsonify({'error': 'Fala não reconhecida'}), 400

        # Tradução via Google Translate (leve, online)
        translated_text = translator.translate(recognized_text, src=src_lang, dest=tgt_lang).text

        return jsonify({'original': recognized_text, 'translated': translated_text})

    except sr.UnknownValueError:
        return jsonify({'error': 'Áudio incompreensível'}), 400
    except sr.RequestError as e:
        return jsonify({'error': f'Erro no reconhecimento: {e}'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        for f in [input_file, wav_file]:
            if os.path.exists(f):
                os.unlink(f)

if __name__ == '__main__':
    import waitress
    port = int(os.environ.get('PORT', 5000))
    waitress.serve(app, host='0.0.0.0', port=port, threads=2, connection_limit=100)
