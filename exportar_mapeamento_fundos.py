"""
Script para exportar mapeamento de fundos para JSON
Usado pelo robô TypeScript do Limine Custódia (Fromtis)

Funciona em 2 modos:
1. Local: Importa de credenciais_bancos.py
2. GitHub Actions: Lê do arquivo temporário santander_fundos.json
"""
import json
import sys
import codecs
import os

# Configurar encoding UTF-8 para Windows
if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

def obter_fundos_santander():
    """
    Obtém dados dos fundos Santander de forma inteligente:
    - GitHub Actions: lê de santander_fundos.json (criado pelo workflow)
    - Local: importa de credenciais_bancos.py
    """
    # Verifica se está rodando no GitHub Actions
    fundos_json_path = "santander_fundos.json"
    
    if os.path.exists(fundos_json_path):
        print(f"🔧 Modo GitHub Actions: lendo fundos de {fundos_json_path}")
        with open(fundos_json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        print("🔧 Modo Local: importando de credenciais_bancos.py")
        try:
            from credenciais_bancos import SANTANDER_FUNDOS
            return SANTANDER_FUNDOS
        except ImportError:
            print("❌ Erro: credenciais_bancos.py não encontrado e santander_fundos.json não existe")
            sys.exit(1)

SANTANDER_FUNDOS = obter_fundos_santander()

def exportar_mapeamento():
    """
    Exporta mapeamento { nome_fromtis: cnpj } para JSON
    """
    mapeamento = {}
    
    for fundo_id, config in SANTANDER_FUNDOS.items():
        nome_fromtis = config.get("nome_fromtis", "")
        cnpj = config.get("cnpj", "")
        
        # Só adiciona se tiver ambos os campos preenchidos
        if nome_fromtis and cnpj:
            mapeamento[nome_fromtis] = cnpj
    
    # Salvar em JSON
    output_file = "mapeamento_fundos_fromtis.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(mapeamento, f, ensure_ascii=False, indent=2)
    
    print("[OK] Mapeamento exportado com sucesso!")
    print(f"Arquivo: {output_file}")
    print(f"Total de fundos: {len(mapeamento)}")
    
    # Mostrar alguns exemplos
    print("\nExemplos de mapeamento:")
    for i, (nome, cnpj) in enumerate(list(mapeamento.items())[:5]):
        print(f"   {nome} -> {cnpj}")
    
    return mapeamento

if __name__ == "__main__":
    exportar_mapeamento()
