import os
import json
import tempfile
import zipfile
import urllib.request
import subprocess
from flask import Flask, request, render_template, jsonify
import librosa
import numpy as np
from vosk import Model, KaldiRecognizer
import argostranslate.translate

# Tentar importar redução de ruído (falha silenciosa se não disponível)
try:
    import noisereduce as nr
    import soundfile as sf
    NOISE_REDUCTION_AVAILABLE = True
except ImportError:
    NOISE_REDUCTION_AVAILABLE = False
    print("[INFO] noisereduce não instalado. Pule redução de ruído.")

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50 MB

@app.errorhandler(413)
def too_large(e):
    return jsonify({'error': 'Arquivo muito grande. Máximo 50 MB.'}), 413

# ----- MODELOS VOSK GRANDES (melhor qualidade) -----
VOSK_MODELS = {
    'en': 'vosk-model-en-us-0.22',      # ~1.8 GB
    'pt': 'vosk-model-pt-0.22',         # ~1.8 GB
    'es': 'vosk-model-small-es-0.42',   # ainda não tem modelo grande
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
    # Modelos grandes usam o mesmo padrão de URL
    url = f"https://alphacephei.com/vosk/models/{model_name}.zip"
    zip_path = os.path.join(MODELS_DIR, f"{model_name}.zip")
    print(f"Baixando modelo grande {model_name} (pode demorar)...")
    try:
        urllib.request.urlretrieve(url, zip_path)
        print("Extraindo...")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(MODELS_DIR)
        os.remove(zip_path)
        return model_path
    except Exception as e:
        raise Exception(f"Falha ao baixar modelo Vosk para {lang_code}: {e}")

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

def reduce_noise_if_possible(wav_path):
    """Aplica redução de ruído se a biblioteca estiver disponível."""
    if not NOISE_REDUCTION_AVAILABLE:
        return wav_path
    try:
        audio, sr = librosa.load(wav_path, sr=16000)
        # Redução de ruído simples (sample-wise)
        reduced = nr.reduce_noise(y=audio, sr=sr, stationary=True)
        output_path = tempfile.NamedTemporaryFile(suffix='.wav', delete=False).name
        sf.write(output_path, reduced, sr)
        return output_path
    except Exception as e:
        print(f"[WARN] Falha na redução de ruído: {e}")
        return wav_path

def transcribe_audio(file_path, lang_code):
    wav_path = convert_to_wav(file_path)
    # Aplica redução de ruído
    wav_denoised = reduce_noise_if_possible(wav_path)
    try:
        model_path = download_vosk_model(lang_code)
        if not model_path:
            raise Exception(f"Idioma {lang_code} não suportado")
        model = Model(model_path)
        rec = KaldiRecognizer(model, 16000)
        # Melhorias de precisão
        rec.SetWords(True)
        rec.SetPartialWords(True)
        
        audio, sr = librosa.load(wav_denoised, sr=16000, mono=True)
        audio_int16 = (audio * 32767).astype(np.int16).tobytes()
        
        if rec.AcceptWaveform(audio_int16):
            result = json.loads(rec.Result())
            text = result.get('text', '')
        else:
            partial = json.loads(rec.PartialResult())
            text = partial.get('partial', '')
        return text.strip()
    finally:
        for f in [wav_path, wav_denoised]:
            if os.path.exists(f) and f != wav_path:  # não deletar o original duas vezes
                os.unlink(f)
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
        wav_temp = convert_to_wav(original_tmp)
        try:
            duration = librosa.get_duration(path=wav_temp)
        finally:
            os.unlink(wav_temp)
        
        # Limite aumentado para 300 segundos (5 minutos)
        if duration < 0.5:
            return jsonify({'error': 'Áudio muito curto. Fale por pelo menos 1 segundo.'}), 400
        if duration > 300:
            return jsonify({'error': f'Áudio muito longo: {duration:.1f}s (máx 300s / 5 min)'}), 400
        
        recognized_text = transcribe_audio(original_tmp, src_lang)
        if not recognized_text:
            return jsonify({'error': 'Nenhuma fala reconhecida. Tente falar mais claramente.'}), 400
        
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
