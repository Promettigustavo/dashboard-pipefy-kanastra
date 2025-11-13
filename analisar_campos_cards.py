import json

def analisar_campos_cards(arquivo_json):
    """
    Analisa todos os campos disponíveis nos cards
    """
    
    print("🔍 ANALISANDO CAMPOS DOS CARDS")
    print("=" * 80)
    
    # Carregar o JSON
    with open(arquivo_json, 'r', encoding='utf-8') as f:
        cards = json.load(f)
    
    print(f"✅ {len(cards)} cards carregados\n")
    
    # Coletar todos os nomes de campos únicos
    campos_unicos = set()
    
    for card in cards:
        for field in card.get('fields', []):
            if field.get('name'):
                campos_unicos.add(field['name'])
    
    # Ordenar alfabeticamente
    campos_ordenados = sorted(campos_unicos)
    
    print(f"📋 TOTAL DE CAMPOS ÚNICOS: {len(campos_ordenados)}")
    print("=" * 80)
    print("\nLISTA DE TODOS OS CAMPOS:\n")
    
    for i, campo in enumerate(campos_ordenados, 1):
        print(f"{i:2d}. {campo}")
    
    print("\n" + "=" * 80)
    
    # Campos que estão na tabela atual
    campos_na_tabela = [
        'Nome do Fundo',
        'Razão Social do Beneficiário',
        'CNPJ',
        'Seu email',
        'E-mail Creditas(liquidação)',
        'Valor',
        'Prazo para pagamento',
        'Forma de Pagamento'
    ]
    
    print("\n✅ CAMPOS JÁ NA TABELA:")
    for campo in campos_na_tabela:
        if campo in campos_ordenados:
            print(f"   • {campo}")
    
    print("\n❌ CAMPOS QUE FALTAM NA TABELA:")
    campos_faltantes = [c for c in campos_ordenados if c not in campos_na_tabela]
    for campo in campos_faltantes:
        print(f"   • {campo}")
    
    return campos_ordenados, campos_faltantes


if __name__ == "__main__":
    arquivo_json = "cards_concluido_prestadores_20251111_110029.json"
    analisar_campos_cards(arquivo_json)
