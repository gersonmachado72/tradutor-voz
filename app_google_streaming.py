import os, tempfile, subprocess, sys
from flask import Flask, request, render_template, jsonify
import speech_recognition as sr
import argostranslate.translate

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 30 * 1024 * 1024

# Cache de tradutores
translators = {}

def get_translator(from_code, to_code):
    key = f"{from_code}_{to_code}"
    if key in translators:
        return translators[key]
    translator = argostranslate.translate.get_translation_from_codes(from_code, to_code)
    if translator is None:
        raise Exception(f"Tradutor {from_code}->{to_code} não encontrado")
    translators[key] = translator
    # Limita o cache a 2 tradutores para não acumular memória
    if len(translators) > 2:
        translators.clear()
    return translator

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/translate', methods=['POST'])
def translate():
    if 'audio' not in request.files:
        return jsonify({'error': 'Nenhum arquivo'}), 400
    audio = request.files['audio']
    if audio.filename == '':
        return jsonify({'error': 'Arquivo vazio'}), 400

    src_lang = request.form.get('src_lang', 'pt')
    tgt_lang = request.form.get('tgt_lang', 'en')

    with tempfile.NamedTemporaryFile(suffix='.webm', delete=False) as tmp:
        audio.save(tmp.name)
        input_file = tmp.name

    try:
        # Converte para WAV
        wav_file = input_file + ".wav"
        subprocess.run(['ffmpeg', '-i', input_file, '-ar', '16000', '-ac', '1',
                       '-y', '-loglevel', 'error', wav_file], check=True, timeout=10)

        # Reconhecimento
        recognizer = sr.Recognizer()
        with sr.AudioFile(wav_file) as source:
            # Ajusta para ruído ambiente
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            audio_data = recognizer.record(source)

        lang_map = {'pt': 'pt-BR', 'en': 'en-US', 'es': 'es-ES', 'fr': 'fr-FR', 'de': 'de-DE'}
        language = lang_map.get(src_lang, 'en-US')

        recognized_text = recognizer.recognize_google(audio_data, language=language, show_all=False)
        if not recognized_text:
            return jsonify({'error': 'Fala não reconhecida'}), 400

        translator = get_translator(src_lang, tgt_lang)
        translated_text = translator.translate(recognized_text)
        return jsonify({'original': recognized_text, 'translated': translated_text})

    except sr.UnknownValueError:
        return jsonify({'error': 'Áudio incompreensível'}), 400
    except sr.RequestError as e:
        return jsonify({'error': f'Erro na API do Google: {e}'}), 500
    except subprocess.TimeoutExpired:
        return jsonify({'error': 'Tempo limite na conversão'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        for f in [input_file, wav_file]:
            if os.path.exists(f):
                os.unlink(f)

if __name__ == '__main__':
    import waitress
    port = int(os.environ.get('PORT', 5000))
    waitress.serve(app, host='0.0.0.0', port=port, threads=1)
