"""
Analisa todos os cards do Pipe Taxas para identificar quais fundos aparecem com mais frequência
e quais precisam ter credenciais configuradas
"""

import requests
from collections import Counter
import re

# Configurações
PIPEFY_API_TOKEN = "eyJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJQaXBlZnkiLCJpYXQiOjE3NjExMzkxNDcsImp0aSI6ImM1NzhhYzM5LTUwZmUtNGI0NC1iMzYzLWE5ZjNhMzBmNjUwYyIsInN1YiI6MzA2ODY4NTY3LCJ1c2VyIjp7ImlkIjozMDY4Njg1NjcsImVtYWlsIjoiZ3VzdGF2by5wcm9tZXR0aUBrYW5hc3RyYS5jb20uYnIifSwidXNlcl90eXBlIjoiYXV0aGVudGljYXRlZCJ9.hjcPATGMMX1xBcRMHQ7gfjkvqB7Nq9w0Ou9tD33fIlmLoicU928x5sd_T_nmkL04DV37GtxFtF5mCFaFSa4fVQ"
PIPEFY_API_URL = "https://api.pipefy.com/graphql"
PIPE_TAXAS_ID = "303667924"

# Fundos já configurados nas credenciais
FUNDOS_CONFIGURADOS = {
    "911_BANK", "AMPLIC", "CONDOLIVRE", "AUTO X", "AUTO XI", "TEMPUS III",
    "INOVA", "MAKENA", "SEJA", "AKIREDE", "ATICCA", "ALTLEGAL", "NETMONEY",
    "TCG", "DORO", "ORION", "AGA", "PRIME", "ALBATROZ", "TESLA"
}

def fazer_requisicao_graphql(query, variables=None):
    """Faz requisição GraphQL ao Pipefy"""
    headers = {
        "Authorization": f"Bearer {PIPEFY_API_TOKEN}",
        "Content-Type": "application/json"
    }
    
    payload = {"query": query}
    if variables:
        payload["variables"] = variables
    
    try:
        response = requests.post(PIPEFY_API_URL, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"❌ Erro na requisição: {e}")
        return None

def buscar_todas_fases():
    """Busca todas as fases do pipe"""
    print("🔍 Buscando fases do Pipe Taxas...")
    
    query = """
    query GetPipe($pipeId: ID!) {
        pipe(id: $pipeId) {
            phases {
                id
                name
            }
        }
    }
    """
    
    resultado = fazer_requisicao_graphql(query, {"pipeId": PIPE_TAXAS_ID})
    
    if resultado and 'data' in resultado:
        fases = resultado['data']['pipe']['phases']
        print(f"✅ {len(fases)} fases encontradas\n")
        return fases
    
    return []

def buscar_cards_da_fase(fase_id, fase_nome, limite=500):
    """Busca TODOS os cards de uma fase específica usando paginação"""
    print(f"📋 Fase: {fase_nome}")
    
    query = """
    query GetCards($phaseId: ID!, $first: Int!, $after: String) {
        phase(id: $phaseId) {
            cards(first: $first, after: $after) {
                pageInfo {
                    hasNextPage
                    endCursor
                }
                edges {
                    node {
                        id
                        title
                        fields {
                            name
                            value
                        }
                    }
                }
            }
        }
    }
    """
    
    todos_cards = []
    has_next_page = True
    after_cursor = None
    
    while has_next_page:
        variables = {"phaseId": fase_id, "first": limite}
        if after_cursor:
            variables["after"] = after_cursor
        
        resultado = fazer_requisicao_graphql(query, variables)
        
        if resultado and 'data' in resultado:
            cards_data = resultado['data']['phase']['cards']
            edges = cards_data['edges']
            page_info = cards_data['pageInfo']
            
            cards_pagina = [edge['node'] for edge in edges]
            todos_cards.extend(cards_pagina)
            
            has_next_page = page_info.get('hasNextPage', False)
            after_cursor = page_info.get('endCursor')
            
            if len(cards_pagina) > 0:
                print(f"   ➕ {len(cards_pagina)} cards (total: {len(todos_cards)})")
        else:
            break
    
    print(f"   📊 {len(todos_cards)} card(s) encontrado(s)")
    return todos_cards

def extrair_nome_fundo(card):
    """Extrai o nome do fundo de um card"""
    fields = card.get('fields', [])
    
    # Tentar vários campos possíveis
    campos_fundo = [
        'nome_fundo',
        'nome do fundo',
        'fundo',
        'nome do fundo ( segunda validação )',
        'nome_do_fundo_segunda_valida_o'
    ]
    
    for field in fields:
        nome_campo = field.get('name', '').lower()
        valor = field.get('value')
        
        if valor and any(campo in nome_campo for campo in campos_fundo):
            # Limpar o nome do fundo
            fundo_nome = str(valor).strip().upper()
            
            # Se for uma lista, pegar o primeiro elemento
            if isinstance(valor, list) and len(valor) > 0:
                fundo_nome = str(valor[0]).strip().upper()
            
            return fundo_nome
    
    return None

def extrair_cnpj_fundo(card):
    """Extrai o CNPJ do fundo de um card"""
    fields = card.get('fields', [])
    
    campos_cnpj = [
        'cnpj_fundo',
        'cnpj do fundo',
        'cnpj do fundo ( segunda validação )'
    ]
    
    for field in fields:
        nome_campo = field.get('name', '').lower()
        valor = field.get('value')
        
        if valor and any(campo in nome_campo for campo in campos_cnpj):
            cnpj = str(valor)
            # Remover formatação
            cnpj_limpo = re.sub(r'\D', '', cnpj)
            if len(cnpj_limpo) == 14:
                return cnpj_limpo
    
    return None

def normalizar_nome_fundo(nome):
    """Normaliza o nome do fundo para comparação"""
    if not nome:
        return None
    
    # Remover palavras comuns que variam
    nome = nome.upper().strip()
    
    # Remover variações de FIDC, FIC, etc
    palavras_remover = [
        'FIDC', 'FIC', 'FIM', 'FIP', 'FUNDO DE INVESTIMENTO',
        'EM DIREITOS CREDITORIOS', 'MULTISSETORIAL', 'NP',
        'SEGMENTO MULTICARTEIRA', 'DE RESPONSABILIDADE LIMITADA'
    ]
    
    for palavra in palavras_remover:
        nome = nome.replace(palavra, '')
    
    # Limpar espaços extras
    nome = ' '.join(nome.split())
    
    return nome

def analisar_fundos():
    """Analisa os fundos da fase Aguardando Comprovante"""
    print("="*80)
    print("📊 ANÁLISE DE FUNDOS - PIPE TAXAS")
    print("Fase: AGUARDANDO COMPROVANTE")
    print("="*80)
    print()
    
    # Buscar todas as fases
    fases = buscar_todas_fases()
    
    if not fases:
        print("❌ Nenhuma fase encontrada")
        return
    
    # Encontrar a fase "Aguardando Comprovante"
    fase_aguardando = None
    for fase in fases:
        if 'aguardando comprovante' in fase['name'].lower():
            fase_aguardando = fase
            break
    
    if not fase_aguardando:
        print("❌ Fase 'Aguardando Comprovante' não encontrada")
        return
    
    # Coletar cards APENAS da fase Aguardando Comprovante
    todos_fundos = []
    fundos_com_cnpj = {}  # {nome_fundo: cnpj}
    
    print("="*80)
    print("📥 COLETANDO CARDS DA FASE 'AGUARDANDO COMPROVANTE'")
    print("="*80)
    print()
    
    cards = buscar_cards_da_fase(fase_aguardando['id'], fase_aguardando['name'])
    total_cards = len(cards)
    
    for card in cards:
        nome_fundo = extrair_nome_fundo(card)
        cnpj_fundo = extrair_cnpj_fundo(card)
        
        if nome_fundo:
            todos_fundos.append(nome_fundo)
            
            # Associar CNPJ ao fundo
            if cnpj_fundo and nome_fundo not in fundos_com_cnpj:
                fundos_com_cnpj[nome_fundo] = cnpj_fundo
    
    print()
    
    print("="*80)
    print("📈 RESULTADOS DA ANÁLISE")
    print("="*80)
    print()
    
    print(f"📊 Total de cards analisados: {total_cards}")
    print(f"📦 Total de fundos identificados: {len(set(todos_fundos))}")
    print()
    
    # Contar frequência dos fundos
    contador_fundos = Counter(todos_fundos)
    
    # Ordenar por frequência
    fundos_ordenados = contador_fundos.most_common()
    
    print("="*80)
    print("🏆 TOP 30 FUNDOS MAIS FREQUENTES")
    print("="*80)
    print()
    
    for idx, (fundo, quantidade) in enumerate(fundos_ordenados[:30], 1):
        cnpj = fundos_com_cnpj.get(fundo, 'CNPJ não encontrado')
        
        # Verificar se está configurado
        fundo_normalizado = normalizar_nome_fundo(fundo)
        esta_configurado = False
        
        for fundo_config in FUNDOS_CONFIGURADOS:
            if fundo_normalizado and normalizar_nome_fundo(fundo_config) in fundo_normalizado:
                esta_configurado = True
                break
        
        status = "✅ CONFIGURADO" if esta_configurado else "❌ NÃO CONFIGURADO"
        
        print(f"[{idx:2d}] {fundo}")
        print(f"     📊 Quantidade: {quantidade} card(s)")
        print(f"     🆔 CNPJ: {cnpj}")
        print(f"     {status}")
        print()
    
    # Fundos não configurados
    print("="*80)
    print("⚠️  FUNDOS NÃO CONFIGURADOS (Precisam de credenciais)")
    print("="*80)
    print()
    
    fundos_sem_config = []
    
    for fundo, quantidade in fundos_ordenados:
        fundo_normalizado = normalizar_nome_fundo(fundo)
        esta_configurado = False
        
        for fundo_config in FUNDOS_CONFIGURADOS:
            if fundo_normalizado and normalizar_nome_fundo(fundo_config) in fundo_normalizado:
                esta_configurado = True
                break
        
        if not esta_configurado:
            cnpj = fundos_com_cnpj.get(fundo, 'CNPJ não encontrado')
            fundos_sem_config.append((fundo, quantidade, cnpj))
    
    print(f"Total: {len(fundos_sem_config)} fundo(s) sem configuração")
    print()
    
    for idx, (fundo, quantidade, cnpj) in enumerate(fundos_sem_config, 1):
        print(f"[{idx:2d}] {fundo}")
        print(f"     📊 Cards: {quantidade}")
        print(f"     🆔 CNPJ: {cnpj}")
        print()
    
    # Estatísticas finais
    print("="*80)
    print("📊 ESTATÍSTICAS FINAIS")
    print("="*80)
    print()
    
    total_fundos_unicos = len(set(todos_fundos))
    fundos_configurados_encontrados = total_fundos_unicos - len(fundos_sem_config)
    
    print(f"📦 Total de fundos únicos: {total_fundos_unicos}")
    print(f"✅ Fundos configurados: {fundos_configurados_encontrados}")
    print(f"❌ Fundos não configurados: {len(fundos_sem_config)}")
    print(f"📈 Cobertura: {(fundos_configurados_encontrados/total_fundos_unicos*100):.1f}%")
    print()
    
    print("="*80)

if __name__ == "__main__":
    analisar_fundos()
