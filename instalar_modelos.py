import argostranslate.package
import argostranslate.translate
import os

packages_dir = os.path.expanduser("~/.local/share/argos-translate/packages/")
arquivos = ["translate-en_pt-1_9.argosmodel", "translate-pt_en-1_9.argosmodel"]

for arquivo in arquivos:
    caminho = os.path.join(packages_dir, arquivo)
    if os.path.exists(caminho):
        print(f"Instalando {arquivo}...")
        argostranslate.package.install_from_path(caminho)
        print("✅ OK")
    else:
        print(f"❌ Arquivo não encontrado: {caminho}")

print("\n--- Teste de tradução Inglês -> Português ---")
tradutor_en_pt = argostranslate.translate.get_translation_from_codes('en', 'pt')
if tradutor_en_pt:
    print("'Hello world' →", tradutor_en_pt.translate("Hello world"))
else:
    print("Falha no tradutor EN→PT")

print("\n--- Teste de tradução Português -> Inglês ---")
tradutor_pt_en = argostranslate.translate.get_translation_from_codes('pt', 'en')
if tradutor_pt_en:
    print("'Olá mundo' →", tradutor_pt_en.translate("Olá mundo"))
else:
    print("Falha no tradutor PT→EN")
