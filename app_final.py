import os
import tempfile
import subprocess
import sys
from flask import Flask, request, render_template, jsonify
import speech_recognition as sr
from googletrans import Translator

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 30 * 1024 * 1024  # 30 MB (limite seguro)

translator = Translator()

def get_audio_duration(file_path):
    """Retorna a duração em segundos usando ffprobe."""
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

    # Verifica o tamanho do arquivo (já limitado pelo Flask)
    # Salva temporariamente
    with tempfile.NamedTemporaryFile(suffix='.webm', delete=False) as tmp:
        audio.save(tmp.name)
        input_file = tmp.name

    try:
        # Obtém duração (rápido)
        duration = get_audio_duration(input_file)
        print(f"Duração: {duration}s", file=sys.stderr)
        
        if duration <= 0:
            # Não conseguiu ler duração, mas prossegue (pode ser formato estranho)
            pass
        elif duration > 180:  # Máximo 3 minutos (seguro para 512 MB RAM)
            return jsonify({'error': f'Áudio muito longo: {duration:.1f}s. Limite máximo é 180s (3 minutos).'}), 400
        elif duration < 0.8:
            return jsonify({'error': f'Áudio muito curto ({duration:.2f}s). Grave pelo menos 1 segundo.'}), 400

        # Converte para WAV com timeout de 45 segundos
        wav_file = input_file + ".wav"
        cmd = ['ffmpeg', '-i', input_file, '-ar', '16000', '-ac', '1', '-y',
               '-loglevel', 'error', wav_file]
        try:
            subprocess.run(cmd, check=True, timeout=45, capture_output=True, text=True)
        except subprocess.TimeoutExpired:
            return jsonify({'error': 'Conversão do áudio demorou muito (arquivo muito grande ou complexo).'}), 400
        except subprocess.CalledProcessError as e:
            return jsonify({'error': f'Erro na conversão: {e.stderr[:200]}'}), 400

        # Reconhecimento de fala (Google Speech) – consome pouca memória
        recognizer = sr.Recognizer()
        with sr.AudioFile(wav_file) as source:
            # Só ajusta ruído se o áudio for longo o suficiente
            if duration > 2:
                recognizer.adjust_for_ambient_noise(source, duration=0.5)
            audio_data = recognizer.record(source)

        lang_map = {'pt': 'pt-BR', 'en': 'en-US', 'es': 'es-ES', 'fr': 'fr-FR', 'de': 'de-DE'}
        language = lang_map.get(src_lang, 'en-US')
        recognized_text = recognizer.recognize_google(audio_data, language=language)

        if not recognized_text:
            return jsonify({'error': 'Fala não reconhecida'}), 400

        # Tradução (Google Translate)
        translated_text = translator.translate(recognized_text, src=src_lang, dest=tgt_lang).text

        return jsonify({'original': recognized_text, 'translated': translated_text})

    except sr.UnknownValueError:
        return jsonify({'error': 'Não foi possível entender o áudio'}), 400
    except sr.RequestError as e:
        return jsonify({'error': f'Erro no serviço de reconhecimento: {e}'}), 500
    except Exception as e:
        print(f"Exceção: {e}", file=sys.stderr)
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500
    finally:
        # Limpeza dos arquivos temporários
        for f in [input_file, wav_file]:
            if os.path.exists(f):
                try:
                    os.unlink(f)
                except:
                    pass

if __name__ == '__main__':
    import waitress
    port = int(os.environ.get('PORT', 5000))
    waitress.serve(app, host='0.0.0.0', port=port, threads=1, connection_limit=10)
