#!/usr/bin/env python3
"""
Script auxiliar para converter credenciais_bancos.py para formato JSON
Usado para configurar o secret SANTANDER_FUNDOS no GitHub Actions
"""

import json
from credenciais_bancos import SANTANDER_FUNDOS

def main():
    print("="*80)
    print("CONVERSOR DE CREDENCIAIS PARA GITHUB ACTIONS")
    print("="*80)
    print()
    print(f"📊 Total de fundos: {len(SANTANDER_FUNDOS)}")
    print()
    
    # Converter para JSON
    json_output = json.dumps(SANTANDER_FUNDOS, indent=2, ensure_ascii=False)
    
    # Salvar em arquivo
    output_file = "santander_fundos_secret.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(json_output)
    
    print(f"✅ Arquivo gerado: {output_file}")
    print()
    print("📋 INSTRUÇÕES:")
    print()
    print("1. Abra o arquivo gerado:")
    print(f"   {output_file}")
    print()
    print("2. Copie TODO o conteúdo")
    print()
    print("3. Acesse GitHub:")
    print("   https://github.com/promettigustavo/dashboard-pipefy-kanastra/settings/secrets/actions")
    print()
    print("4. Clique em 'New repository secret'")
    print()
    print("5. Nome do secret: SANTANDER_FUNDOS")
    print()
    print("6. Cole o conteúdo copiado")
    print()
    print("7. Clique em 'Add secret'")
    print()
    print("="*80)
    
    # Também exibir preview
    print()
    print("📄 PREVIEW (primeiras 30 linhas):")
    print("="*80)
    lines = json_output.split('\n')[:30]
    for line in lines:
        print(line)
    if len(json_output.split('\n')) > 30:
        print("... (restante omitido)")
    print("="*80)

if __name__ == "__main__":
    main()
