"""
Script para exportar mapeamento de fundos do credenciais_bancos.py para JSON
Usado pelo robô TypeScript do Limine Custódia (Fromtis)
"""
import json
import sys
import codecs

# Configurar encoding UTF-8 para Windows
if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

from credenciais_bancos import SANTANDER_FUNDOS

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
