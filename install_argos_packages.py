#!/usr/bin/env python3
import argostranslate.package
import argostranslate.translate

print("Atualizando índice de pacotes...")
argostranslate.package.update_package_index()

available = argostranslate.package.get_available_packages()

for from_code, to_code in [('en', 'pt'), ('pt', 'en')]:
    pkg = next((p for p in available if p.from_code == from_code and p.to_code == to_code), None)
    if pkg:
        print(f"Baixando e instalando {from_code}->{to_code} ...")
        pkg.install()
        print("OK")
    else:
        print(f"Pacote {from_code}->{to_code} não encontrado.")

print("\nTestando traduções:")
t_en_pt = argostranslate.translate.get_translation_from_codes('en', 'pt')
if t_en_pt:
    print("en -> pt:", t_en_pt.translate("Hello world"))

t_pt_en = argostranslate.translate.get_translation_from_codes('pt', 'en')
if t_pt_en:
    print("pt -> en:", t_pt_en.translate("Olá mundo"))
