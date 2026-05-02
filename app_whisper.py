import os
import json
import tempfile
import subprocess
from flask import Flask, request, render_template, jsonify
import librosa
import argostranslate.translate
from faster_whisper import WhisperModel

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024

@app.errorhandler(413)
def too_large(e):
    return jsonify({'error': 'Arquivo muito grande. Máximo 50 MB.'}), 413

# Carrega modelo Whisper uma vez (escolha 'base', 'small', 'medium', 'large')
# 'base' tem 145 MB e já é muito melhor que Vosk small
whisper_model = WhisperModel("base", device="cpu", compute_type="int8")

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
    cmd = ['ffmpeg', '-i', input_path, '-ar', '16000', '-ac', '1', '-y', output_path]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    return output_path

def transcribe_audio(file_path, lang_code):
    wav_path = convert_to_wav(file_path)
    try:
        segments, _ = whisper_model.transcribe(wav_path, language=lang_code, beam_size=5)
        text = " ".join(segment.text for segment in segments)
        return text.strip()
    finally:
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
        wav_temp = convert_to_wav(original_tmp)
        try:
            duration = librosa.get_duration(path=wav_temp)
        finally:
            os.unlink(wav_temp)
        
        if duration < 0.5:
            return jsonify({'error': 'Áudio muito curto. Fale por pelo menos 1 segundo.'}), 400
        if duration > 300:
            return jsonify({'error': f'Áudio muito longo: {duration:.1f}s (máx 300s)'}), 400
        
        recognized_text = transcribe_audio(original_tmp, src_lang)
        if not recognized_text:
            return jsonify({'error': 'Nenhuma fala reconhecida.'}), 400
        
        translator = get_translator(src_lang, tgt_lang)
        translated_text = translator.translate(recognized_text)
        return jsonify({
            'original': recognized_text,
            'translated': translated_text
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        os.unlink(original_tmp)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
