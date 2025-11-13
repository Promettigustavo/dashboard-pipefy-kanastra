"""
Anexar Comprovantes Pipe TAXAS (não Anbima)
Versão adaptada para o Pipe de Taxas normal (ID: 303667924)
Baseado na mesma lógica do Anexarcomprovantespipe.py
"""

import requests
import json
import re
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# Configurar encoding UTF-8 para suportar emojis no Windows
if sys.platform == 'win32':
    import codecs
    # Verificar se stdout tem buffer (pode não ter se já foi reconfigurado)
    if hasattr(sys.stdout, 'buffer'):
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Importar credenciais e classe de autenticação
try:
    from credenciais_bancos import SantanderAuth, criar_auth_para_todos_fundos, listar_fundos_configurados
    from buscar_comprovantes_santander import SantanderComprovantes
    HAS_CREDENCIAIS = True
except ImportError as e:
    # Em ambiente cloud, não temos credenciais_bancos - isso é esperado
    HAS_CREDENCIAIS = False
    SantanderAuth = None
    criar_auth_para_todos_fundos = None
    listar_fundos_configurados = None
    SantanderComprovantes = None
    # Não fazer sys.exit() para permitir que o módulo seja importado no Streamlit Cloud

# ==================== CONFIGURAÇÃO ====================

# Configurações Pipefy
PIPEFY_API_TOKEN = "eyJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJQaXBlZnkiLCJpYXQiOjE3NjExMzkxNDcsImp0aSI6ImM1NzhhYzM5LTUwZmUtNGI0NC1iMzYzLWE5ZjNhMzBmNjUwYyIsInN1YiI6MzA2ODY4NTY3LCJ1c2VyIjp7ImlkIjozMDY4Njg1NjcsImVtYWlsIjoiZ3VzdGF2by5wcm9tZXR0aUBrYW5hc3RyYS5jb20uYnIifSwidXNlcl90eXBlIjoiYXV0aGVudGljYXRlZCJ9.hjcPATGMMX1xBcRMHQ7gfjkvqB7Nq9w0Ou9tD33fIlmLoicU928x5sd_T_nmkL04DV37GtxFtF5mCFaFSa4fVQ"
PIPEFY_API_URL = "https://api.pipefy.com/graphql"
PIPE_TAXAS_ID = "303667924"  # ID do Pipe de Taxas

# IDs das Fases do Pipe Taxas
FASE_TAXAS_AGUARDANDO_COMPROVANTE = "322673487"
FASE_TAXAS_SOLICITACAO_PAGA = "322618269"

# Configurações API Santander
SANTANDER_API_URL = "https://trust-open.api.santander.com.br"
SANTANDER_VOUCHERS_ENDPOINT = "/consult_payment_receipts/v1/payment_receipts"

# Nível de logging: 'minimal' ou 'detailed'
LOG_LEVEL = 'minimal'  # Mudar para 'detailed' para ver todos os logs

# ==================== FUNÇÕES AUXILIARES ====================

def log(msg, level='normal'):
    """Log com timestamp - respeitando nível de logging"""
    if LOG_LEVEL == 'minimal' and level == 'debug':
        return  # Não mostrar logs de debug no modo minimal
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {msg}")


# Inicializar clientes Santander para todos os fundos (após definição da função log)
santander_clients = {}

def inicializar_clientes_santander():
    """
    Inicializa clientes Santander - compatível com Streamlit Cloud
    Tenta primeiro usar credenciais_bancos local, depois tenta Streamlit secrets
    """
    global santander_clients
    
    try:
        # Tentativa 1: Usar credenciais_bancos (ambiente local)
        if HAS_CREDENCIAIS and criar_auth_para_todos_fundos:
            log("🔐 Inicializando clientes Santander (credenciais locais)...")
            auth_clients = criar_auth_para_todos_fundos()
            
            for fundo_id, auth in auth_clients.items():
                santander_clients[fundo_id] = SantanderComprovantes(auth)
            
            log(f"✅ {len(santander_clients)} cliente(s) Santander inicializado(s)")
            for fundo_id in santander_clients.keys():
                log(f"   - {fundo_id}")
            return
    except Exception as e:
        log(f"⚠️ Credenciais locais não disponíveis: {e}")
    
    # Tentativa 2: Usar Streamlit secrets
    try:
        import streamlit as st
        if "santander_fundos" in st.secrets:
            log("🔐 Inicializando clientes Santander (Streamlit secrets)...")
            
            # Importar função de criar auth do secrets
            import sys
            from pathlib import Path
            
            # Importar app_streamlit para usar a função criar_santander_auth_do_secrets
            app_path = Path(__file__).parent / "app_streamlit.py"
            if app_path.exists():
                import importlib.util
                spec = importlib.util.spec_from_file_location("app_streamlit_module", app_path)
                app_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(app_module)
                
                # Criar cliente para cada fundo nos secrets
                for fundo_id in st.secrets["santander_fundos"].keys():
                    if fundo_id not in ["cert_pem", "key_pem"]:
                        try:
                            auth = app_module.criar_santander_auth_do_secrets(fundo_id, ambiente="producao")
                            santander_clients[fundo_id] = SantanderComprovantes(auth)
                        except Exception as e_fundo:
                            log(f"⚠️ Erro ao criar cliente para {fundo_id}: {e_fundo}")
                
                log(f"✅ {len(santander_clients)} cliente(s) Santander inicializado(s) via secrets")
                return
    except Exception as e:
        log(f"⚠️ Streamlit secrets não disponíveis: {e}")
    
    log("❌ Nenhum cliente Santander foi inicializado")
    santander_clients = {}

# Tentar inicializar na importação do módulo
try:
    inicializar_clientes_santander()
except Exception as e:
    log(f"❌ Erro ao inicializar clientes Santander: {e}")
    santander_clients = {}


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
        response = requests.post(PIPEFY_API_URL, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        log(f"❌ Erro na requisição GraphQL: {e}")
        return None


# ==================== FUNÇÕES PRINCIPAIS ====================

def buscar_fase_por_nome(pipe_id, nome_fase):
    """Busca o ID de uma fase pelo nome"""
    log(f"🔍 Buscando fase '{nome_fase}' no pipe {pipe_id}...")
    
    query = """
    query GetPhases($pipeId: ID!) {
        pipe(id: $pipeId) {
            phases {
                id
                name
            }
        }
    }
    """
    
    variables = {"pipeId": pipe_id}
    resultado = fazer_requisicao_graphql(query, variables)
    
    if not resultado or 'data' not in resultado:
        log("❌ Erro ao buscar fases")
        return None
    
    fases = resultado['data']['pipe']['phases']
    
    # Procurar fase pelo nome
    for fase in fases:
        if fase['name'].lower() == nome_fase.lower():
            log(f"✅ Fase encontrada: {fase['name']} (ID: {fase['id']})")
            return fase['id']
    
    log(f"❌ Fase '{nome_fase}' não encontrada")
    log(f"📋 Fases disponíveis:")
    for fase in fases:
        log(f"   - {fase['name']} (ID: {fase['id']})")
    
    return None


def buscar_cards_da_fase(fase_id, limite=50):
    """Busca todos os cards de uma fase específica (com paginação)"""
    log(f"🔍 Buscando cards da fase {fase_id}...")
    
    query = """
    query GetCards($phaseId: ID!, $first: Int!, $after: String) {
        phase(id: $phaseId) {
            cards(first: $first, after: $after) {
                edges {
                    node {
                        id
                        title
                        createdAt
                        finished_at
                        fields {
                            name
                            value
                            field {
                                id
                                type
                            }
                        }
                        assignees {
                            id
                            name
                        }
                    }
                }
                pageInfo {
                    hasNextPage
                    endCursor
                }
            }
        }
    }
    """
    
    all_cards = []
    has_next_page = True
    after_cursor = None
    page = 1
    
    while has_next_page:
        variables = {
            "phaseId": fase_id,
            "first": min(limite, 50),  # Pipefy limita a 50 por página
            "after": after_cursor
        }
        
        resultado = fazer_requisicao_graphql(query, variables)
        
        if not resultado or 'data' not in resultado:
            log("❌ Erro ao buscar cards")
            break
        
        cards_data = resultado['data']['phase']['cards']
        edges = cards_data['edges']
        page_info = cards_data['pageInfo']
        
        cards = [edge['node'] for edge in edges]
        all_cards.extend(cards)
        
        log(f"   Página {page}: {len(cards)} cards")
        
        has_next_page = page_info['hasNextPage']
        after_cursor = page_info['endCursor']
        page += 1
        
        # Limitar total de cards se necessário
        if len(all_cards) >= limite:
            all_cards = all_cards[:limite]
            break
    
    log(f"✅ {len(all_cards)} cards encontrados no total")
    return all_cards


def extrair_dados_para_matching(card):
    """
    Extrai os dados necessários do card para fazer matching com API do Santander
    ADAPTADO PARA PIPE DE TAXAS
    
    Retorna dict com:
    - cnpj_beneficiario: CNPJ ou CPF do beneficiário (usado como filtro na API)
    - valor: Valor do pagamento
    - nome_beneficiario: Nome do beneficiário (para validação extra)
    - data_pagamento: Data do pagamento
    """
    dados = {
        'cnpj_beneficiario': '',
        'cpf_beneficiario': '',
        'documento_beneficiario': '',  # CNPJ ou CPF sem formatação
        'valor': 0.0,
        'cnpj_fundo': '',
        'nome_beneficiario': '',
        'data_pagamento': '',
        'nome_fundo': '',
        'descricao': ''
    }
    
    fields = card.get('fields', [])
    
    # Converter lista de fields para dict por nome
    fields_dict = {}
    for field in fields:
        nome = field.get('name', '').lower()
        valor = field.get('value')
        fields_dict[nome] = valor
    
    # 1. EXTRAIR CNPJ DO FAVORECIDO (beneficiário no pipe de taxas)
    # Tentar múltiplas variações de campos
    cnpj_fields = [
        'cnpj do favorecido',
        'cnpj_favorecido', 
        'cnpj',
        'cnpj do prestador ( segunda validação )',
        'copy_of_cnpj_do_fundo_segunda_valida_o'
    ]
    
    for campo in cnpj_fields:
        if campo in fields_dict and fields_dict[campo]:
            cnpj = re.sub(r'\D', '', str(fields_dict[campo]))
            if len(cnpj) == 14:
                dados['cnpj_beneficiario'] = cnpj
                dados['documento_beneficiario'] = cnpj
                break
    
    # 2. EXTRAIR CPF DO FAVORECIDO (se não tiver CNPJ)
    if not dados['documento_beneficiario']:
        cpf_fields = ['cpf do favorecido', 'cpf_favorecido', 'cpf']
        for campo in cpf_fields:
            if campo in fields_dict and fields_dict[campo]:
                cpf = re.sub(r'\D', '', str(fields_dict[campo]))
                if len(cpf) == 11:
                    dados['cpf_beneficiario'] = cpf
                    dados['documento_beneficiario'] = cpf
                    break
    
    # 3. EXTRAIR VALOR DO FAVORECIDO
    valor_fields = ['valor_favorecido', 'valor', 'valor do favorecido']
    
    for campo in valor_fields:
        if campo in fields_dict and fields_dict[campo]:
            # Formato brasileiro: 1.345,50 → remover pontos de milhar, trocar vírgula por ponto
            valor_str = str(fields_dict[campo]).replace('R$', '').strip()
            # Remover pontos (separador de milhar)
            valor_str = valor_str.replace('.', '')
            # Trocar vírgula por ponto (decimal)
            valor_str = valor_str.replace(',', '.')
            try:
                dados['valor'] = float(valor_str)
                break
            except:
                continue
    
    # 4. EXTRAIR NOME DO FAVORECIDO (beneficiário)
    nome_fields = [
        'nome do favorecido',
        'nome_favorecido',
        'razão social do favorecido',
        'nome do prestador ( segunda validação )',
        'beneficiário'
    ]
    
    for campo in nome_fields:
        if campo in fields_dict and fields_dict[campo]:
            dados['nome_beneficiario'] = str(fields_dict[campo])
            break
    
    # 5. DATA DE BUSCA DO COMPROVANTE
    # Não precisa definir aqui, será buscado do dia de hoje no cache
    # Deixar vazio para usar o cache do dia
    dados['data_pagamento'] = ''
    
    # 6. EXTRAIR NOME DO FUNDO
    fundo_fields = ['nome_fundo', 'nome do fundo', 'fundo', 'nome do fundo ( segunda validação )']
    
    for campo in fundo_fields:
        if campo in fields_dict and fields_dict[campo]:
            dados['nome_fundo'] = str(fields_dict[campo])
            break
    
    # 7. EXTRAIR CNPJ DO FUNDO
    cnpj_fundo_fields = ['cnpj_fundo', 'cnpj do fundo', 'cnpj do fundo ( segunda validação )']
    
    for campo in cnpj_fundo_fields:
        if campo in fields_dict and fields_dict[campo]:
            cnpj_fundo = re.sub(r'\D', '', str(fields_dict[campo]))
            if len(cnpj_fundo) == 14:
                dados['cnpj_fundo'] = cnpj_fundo
                break
    
    # 8. EXTRAIR DESCRIÇÃO/TIPO DE TAXA
    if 'tipo de taxa' in fields_dict:
        dados['descricao'] = str(fields_dict['tipo de taxa'])
    elif 'tipo de taxa ( segunda validação )' in fields_dict:
        dados['descricao'] = str(fields_dict['tipo de taxa ( segunda validação )'])
    
    return dados


# ==================== API SANTANDER - FUNÇÕES ADAPTADAS ====================

def listar_comprovantes_todos_fundos(data_inicio: str, data_fim: str):
    """
    Lista comprovantes de todos os fundos Santander configurados
    
    Args:
        data_inicio: Data inicial no formato YYYY-MM-DD
        data_fim: Data final no formato YYYY-MM-DD
    
    Returns:
        dict: {fundo_id: lista_de_comprovantes}
    """
    log(f"🔍 Listando comprovantes de todos os fundos ({data_inicio} até {data_fim})...")
    
    if not santander_clients:
        log("❌ Nenhum cliente Santander configurado")
        return {}
    
    todos_comprovantes = {}
    
    for fundo_id, cliente in santander_clients.items():
        try:
            log(f"\n📋 Buscando em: {fundo_id}")
            result = cliente.listar_comprovantes(data_inicio, data_fim)
            comprovantes_raw = result.get('paymentsReceipts', [])
            
            # Processar comprovantes
            comprovantes = []
            for item in comprovantes_raw:
                payment = item.get('payment', {})
                
                # Obter amount e garantir que é float
                amount_raw = payment.get('paymentAmountInfo', {}).get('direct', {}).get('amount')
                try:
                    amount_float = float(amount_raw) if amount_raw else 0.0
                except (ValueError, TypeError):
                    amount_float = 0.0
                
                comprovante = {
                    'payment_id': payment.get('paymentId'),
                    'fundo_id': fundo_id,
                    'fundo_nome': cliente.auth.fundo_nome,
                    'commitment_number': payment.get('commitmentNumber'),
                    'payer_document': payment.get('payer', {}).get('person', {}).get('document', {}).get('documentNumber'),
                    'payer_document_type': payment.get('payer', {}).get('person', {}).get('document', {}).get('documentTypeCode'),
                    'payee_name': payment.get('payee', {}).get('name'),
                    'payee_document': payment.get('payee', {}).get('person', {}).get('document', {}).get('documentNumber'),
                    'payee_document_type': payment.get('payee', {}).get('person', {}).get('document', {}).get('documentTypeCode'),
                    'amount': amount_float,  # Garantir que é float
                    'request_date': payment.get('requestValueDate'),
                    'category': item.get('category', {}).get('code'),
                    'channel': item.get('channel', {}).get('code'),
                    'raw_data': item,
                    'cliente': cliente  # Referência ao cliente para download posterior
                }
                comprovantes.append(comprovante)
            
            todos_comprovantes[fundo_id] = comprovantes
            log(f"   ✅ {len(comprovantes)} comprovante(s) encontrado(s)")
            
        except Exception as e:
            log(f"   ❌ Erro ao listar comprovantes de {fundo_id}: {e}")
            todos_comprovantes[fundo_id] = []
    
    # Totalizar
    total = sum(len(comps) for comps in todos_comprovantes.values())
    log(f"\n📊 Total geral: {total} comprovante(s) em {len(todos_comprovantes)} fundo(s)")
    
    return todos_comprovantes


def buscar_comprovante_por_documento(documento_beneficiario, data_pagamento, cache_comprovantes=None):
    """
    Busca comprovantes em TODOS os fundos filtrados por documento do beneficiário e data
    
    NOTA: A API Santander NÃO retorna o documento do beneficiário (payee_document),
    então esta função agora busca TODOS os comprovantes da data e o matching
    deve ser feito apenas por valor.
    
    Args:
        documento_beneficiario: CNPJ ou CPF do beneficiário (NÃO USADO - API não fornece)
        data_pagamento: Data no formato YYYY-MM-DD
        cache_comprovantes: Dicionário com comprovantes já buscados (opcional, evita consultas repetidas)
    
    Retorna:
        list: Lista de comprovantes encontrados (com info do fundo), ou None se erro
    """
    
    if not santander_clients:
        log("❌ Nenhum cliente Santander configurado")
        return None
    
    try:
        # Se cache foi fornecido, usar ele ao invés de buscar novamente
        if cache_comprovantes is not None:
            todos_comprovantes = cache_comprovantes
        else:
            # Sem cache: buscar na API (modo antigo - para compatibilidade)
            log(f"🔍 Buscando comprovante em todos os fundos...")
            log(f"   ⚠️  API Santander não fornece documento do beneficiário")
            log(f"   Buscando TODOS os comprovantes da data: {data_pagamento}")
            todos_comprovantes = listar_comprovantes_todos_fundos(data_pagamento, data_pagamento)
        
        # Como a API não fornece documento do beneficiário, retornar TODOS os comprovantes
        # O matching será feito apenas por VALOR
        comprovantes_filtrados = []
        
        for fundo_id, comprovantes in todos_comprovantes.items():
            for comp in comprovantes:
                comprovantes_filtrados.append(comp)
        
        return comprovantes_filtrados
        
    except Exception as e:
        log(f"   ❌ Erro ao buscar comprovantes: {e}")
        return None


def fazer_match_por_valor(comprovantes, valor_esperado, nome_beneficiario=None, nome_fundo=None, cnpj_fundo=None):
    """
    Faz match de comprovantes por CNPJ FUNDO + BENEFICIÁRIO + VALOR
    
    Args:
        comprovantes: Lista de comprovantes da API Santander (pode ser dict {fundo: [comps]} ou lista)
        valor_esperado: Valor do card (float)
        nome_beneficiario: Nome do beneficiário do card (opcional)
        nome_fundo: Nome do fundo do card (fallback se não tiver CNPJ)
        cnpj_fundo: CNPJ do fundo do card (match mais preciso)
    
    Retorna:
        dict: Comprovante que fez match, ou None
    """
    # Se comprovantes é um dict (cache por fundo), converter para lista única
    if isinstance(comprovantes, dict):
        # Flatten: juntar todos os comprovantes de todos os fundos
        lista_comprovantes = []
        for fundo_id, comps in comprovantes.items():
            lista_comprovantes.extend(comps)
        comprovantes = lista_comprovantes
    
    if not comprovantes:
        return None
    
    log(f"🎯 Fazendo match por CNPJ FUNDO + BENEFICIÁRIO + VALOR")
    log(f"   📊 CNPJ Fundo: {cnpj_fundo if cnpj_fundo else 'NÃO INFORMADO'}")
    log(f"   📊 Nome Fundo: {nome_fundo if nome_fundo else 'NÃO INFORMADO'}")
    log(f"   👤 Beneficiário: {nome_beneficiario if nome_beneficiario else 'NÃO INFORMADO'}")
    log(f"   💰 Valor: R$ {valor_esperado:,.2f}")
    log(f"   📦 Total de comprovantes disponíveis: {len(comprovantes)}")
    
    # ETAPA 1: Filtrar por CNPJ DO FUNDO (mais preciso)
    if cnpj_fundo:
        cnpj_fundo_limpo = re.sub(r'\D', '', cnpj_fundo)
        matches_fundo = []
        
        for comp in comprovantes:
            payer_doc = comp.get('payer_document', '')
            payer_doc_limpo = re.sub(r'\D', '', str(payer_doc)) if payer_doc else ''
            
            if cnpj_fundo_limpo == payer_doc_limpo:
                matches_fundo.append(comp)
        
        log(f"   ✅ Match por CNPJ FUNDO: {len(matches_fundo)} comprovante(s)")
        
        if len(matches_fundo) == 0:
            log(f"   ❌ Nenhum comprovante do CNPJ fundo '{cnpj_fundo}'")
            return None
        
        comprovantes = matches_fundo
    else:
        log(f"   ⚠️  Fundo não informado (nem CNPJ nem nome) - pulando filtro")
    
    # ETAPA 2: Filtrar por VALOR (obrigatório)
    matches_valor = []
    for comp in comprovantes:
        valor_comp = float(comp['amount'])
        if abs(valor_comp - valor_esperado) < 0.01:  # Tolerância de 1 centavo
            matches_valor.append(comp)
    
    log(f"   ✅ Match por VALOR: {len(matches_valor)} comprovante(s)")
    
    if len(matches_valor) == 0:
        log(f"   ❌ Nenhum comprovante com valor R$ {valor_esperado:,.2f} no fundo")
        return None
    
    if len(matches_valor) == 1:
        log(f"   🎯 Match ÚNICO encontrado!")
        log(f"      Payment ID: {matches_valor[0]['payment_id']}")
        log(f"      Fundo: {matches_valor[0].get('fundo_nome', 'N/A')}")
        log(f"      Beneficiário: {matches_valor[0].get('payee_name', 'N/A')}")
        return matches_valor[0]
    
    # ETAPA 3: Se múltiplos, filtrar por BENEFICIÁRIO
    if nome_beneficiario and len(matches_valor) > 1:
        log(f"   ⚠️  {len(matches_valor)} comprovantes - refinando por BENEFICIÁRIO...")
        
        nome_card_norm = nome_beneficiario.upper().strip()
        matches_beneficiario = []
        
        for comp in matches_valor:
            nome_comp = comp.get('payee_name', '').upper().strip()
            
            if nome_card_norm in nome_comp or nome_comp in nome_card_norm:
                matches_beneficiario.append(comp)
                log(f"      ✅ Match: {comp.get('payee_name')}")
        
        if len(matches_beneficiario) == 1:
            log(f"   🎯 Match ÚNICO após filtro por beneficiário!")
            return matches_beneficiario[0]
        elif len(matches_beneficiario) > 1:
            log(f"   ⚠️  Ainda há {len(matches_beneficiario)} matches - usando o primeiro")
            return matches_beneficiario[0]
        else:
            log(f"   ⚠️  Nenhum match por beneficiário - usando primeiro por fundo+valor")
            return matches_valor[0]
    
    # Se chegou aqui, usar primeiro match
    log(f"   ⚠️  Múltiplos matches - usando o primeiro")
    return matches_valor[0]


def processar_card_com_santander(card, cache_comprovantes=None):
    """
    Processa um card: extrai dados, busca na API Santander e faz match
    
    Args:
        card: Card do Pipefy
        cache_comprovantes: Dicionário com comprovantes já buscados (opcional, evita consultas repetidas)
    
    Retorna:
        dict: Resultado com status e dados do match
    """
    resultado = {
        'card_id': card['id'],
        'card_title': card['title'],
        'sucesso': False,
        'motivo': '',
        'comprovante': None,
        'dados_card': None
    }
    
    # 1. Extrair dados do card
    dados = extrair_dados_para_matching(card)
    resultado['dados_card'] = dados
    
    # 2. Validar se tem dados necessários
    if not dados['documento_beneficiario']:
        resultado['motivo'] = 'Card sem documento do beneficiário'
        log(f"⚠️ {card['title']}: {resultado['motivo']}")
        return resultado
    
    # Nota: Não validamos data_pagamento porque buscamos apenas do dia de hoje
    # O match será feito por valor + nome do beneficiário
    
    # 3. Buscar na API Santander (usando cache se disponível)
    comprovantes = buscar_comprovante_por_documento(
        dados['documento_beneficiario'],
        dados['data_pagamento'],
        cache_comprovantes=cache_comprovantes
    )
    
    if comprovantes is None:
        resultado['motivo'] = 'Erro ao buscar na API Santander'
        return resultado
    
    if len(comprovantes) == 0:
        resultado['motivo'] = 'Nenhum comprovante encontrado'
        log(f"   ℹ️ Nenhum comprovante para documento {dados['documento_beneficiario']} em {dados['data_pagamento']}")
        return resultado
    
    # 4. Fazer match por valor + nome do beneficiário (se disponível)
    nome_beneficiario = dados.get('nome_beneficiario')
    
    # DEBUG: Mostrar comprovantes encontrados
    log(f"🔍 {card['title']}: Encontrados {len(comprovantes)} comprovante(s)")
    log(f"   Valor procurado: R$ {dados['valor']:,.2f}")
    if len(comprovantes) <= 5:  # Mostrar apenas se tem poucos comprovantes
        for i, comp in enumerate(comprovantes, 1):
            valor_comp = float(comp['amount']) if isinstance(comp['amount'], str) else comp['amount']
            log(f"   [{i}] R$ {valor_comp:,.2f} - {comp.get('payee_name', 'N/A')}")
    
    # Fazer match por CNPJ FUNDO + BENEFICIÁRIO + VALOR
    nome_fundo = dados.get('nome_fundo')
    cnpj_fundo = dados.get('cnpj_fundo')
    comprovante_match = fazer_match_por_valor(
        comprovantes, 
        dados['valor'], 
        nome_beneficiario=nome_beneficiario,
        nome_fundo=nome_fundo,
        cnpj_fundo=cnpj_fundo
    )
    
    if not comprovante_match:
        resultado['motivo'] = f'Nenhum match encontrado (Fundo: {nome_fundo}, Valor: R$ {dados["valor"]:,.2f})'
        return resultado
    
    # 5. Match bem-sucedido!
    resultado['sucesso'] = True
    resultado['motivo'] = 'Match encontrado com sucesso'
    resultado['comprovante'] = comprovante_match
    
    log(f"✅ {card['title']}: Match bem-sucedido!")
    log(f"   Payment ID: {comprovante_match['payment_id']}")
    
    # Converter amount para float se for string
    valor_match = comprovante_match['amount']
    if isinstance(valor_match, str):
        valor_match = float(valor_match)
    log(f"   Valor: R$ {valor_match:,.2f}")
    
    return resultado


# ==================== SANTANDER - GERAÇÃO E DOWNLOAD DE PDF ====================

def obter_pdf_comprovante(payment_id, fundo_id=None, cliente_santander=None):
    """
    Fluxo completo para obter o PDF do comprovante usando SantanderComprovantes
    
    Args:
        payment_id: ID do pagamento
        fundo_id: ID do fundo (usado para buscar o cliente correto)
        cliente_santander: Cliente SantanderComprovantes já inicializado (opcional)
    
    Retorna:
        str: Caminho do PDF salvo, ou None se erro
    """
    # Determinar qual cliente usar
    if cliente_santander:
        cliente = cliente_santander
    elif fundo_id and fundo_id in santander_clients:
        cliente = santander_clients[fundo_id]
    else:
        log("❌ Cliente Santander não especificado e nenhum fundo_id fornecido")
        return None
    
    try:
        log(f"\n📄 Obtendo PDF do comprovante {payment_id}")
        if fundo_id:
            log(f"   Fundo: {fundo_id}")
        
        # Usar método buscar_e_baixar_comprovante do SantanderComprovantes
        log(f"   🔄 Chamando buscar_e_baixar_comprovante...")
        caminho_pdf = cliente.buscar_e_baixar_comprovante(payment_id)
        
        if caminho_pdf:
            log(f"✅ PDF salvo em: {caminho_pdf}")
            return str(caminho_pdf)
        else:
            log(f"❌ Falha ao baixar PDF - caminho_pdf retornou None")
            return None
            
    except Exception as e:
        log(f"❌ Erro ao obter PDF: {e}")
        import traceback
        log(f"   Traceback: {traceback.format_exc()}")
        return None


# ==================== PIPEFY - ANEXAR ARQUIVO ====================

def fazer_upload_arquivo_pipefy(caminho_arquivo):
    """
    Faz upload de um arquivo para o storage do Pipefy
    
    Args:
        caminho_arquivo: Caminho completo do arquivo PDF
    
    Retorna:
        str: URL do arquivo no Pipefy, ou None se erro
    """
    log(f"📤 Fazendo upload do arquivo para o Pipefy...")
    
    if not os.path.exists(caminho_arquivo):
        log(f"   ❌ Arquivo não encontrado: {caminho_arquivo}")
        return None
    
    try:
        nome_arquivo = os.path.basename(caminho_arquivo)
        
        # Mutation GraphQL para criar signed upload URL
        query = """
        mutation($organizationId: ID!, $fileName: String!) {
            createPresignedUrl(
                input: {
                    organizationId: $organizationId
                    fileName: $fileName
                }
            ) {
                url
                clientMutationId
            }
        }
        """
        
        variables = {
            "organizationId": "300891416",
            "fileName": nome_arquivo
        }
        
        headers = {
            "Authorization": f"Bearer {PIPEFY_API_TOKEN}",
            "Content-Type": "application/json"
        }
        
        # Passo 1: Obter URL assinada para upload
        response = requests.post(
            PIPEFY_API_URL,
            headers=headers,
            json={
                "query": query,
                "variables": variables
            },
            timeout=10
        )
        
        if response.status_code != 200:
            log(f"   ❌ Erro ao obter URL de upload: HTTP {response.status_code}")
            return None
        
        data = response.json()
        
        if 'errors' in data:
            log(f"   ❌ Erro GraphQL: {data['errors']}")
            log(f"   ❌ Falha ao fazer upload do arquivo")
            return None
        
        upload_url = data['data']['createPresignedUrl']['url']
        
        log(f"   ✅ URL de upload obtida")
        
        # Passo 2: Fazer upload do arquivo
        with open(caminho_arquivo, 'rb') as f:
            arquivo_bytes = f.read()
        
        upload_response = requests.put(
            upload_url,
            data=arquivo_bytes,
            headers={
                'Content-Type': 'application/pdf'
            },
            timeout=60
        )
        
        if upload_response.status_code not in [200, 201, 204]:
            log(f"   ❌ Erro no upload: HTTP {upload_response.status_code}")
            return None
        
        log(f"   ✅ Upload concluído!")
        
        # Retornar a URL completa do S3 (sem query params de assinatura)
        from urllib.parse import urlparse
        parsed_url = urlparse(upload_url)
        file_url = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}"
        
        return file_url
        
    except Exception as e:
        log(f"   ❌ Erro ao fazer upload: {e}")
        return None


def buscar_field_id_comprovante(card_id):
    """
    Busca o ID do campo de comprovante no card (PHASE FIELDS - formulário da fase)
    
    Args:
        card_id: ID do card
    
    Retorna:
        str: ID do campo de comprovante, ou None se não encontrado
    """
    log(f"🔍 Buscando ID do campo de comprovante no card {card_id} (phase fields)...")
    
    query = """
    query GetCard($cardId: ID!) {
        card(id: $cardId) {
            current_phase {
                id
                name
                fields {
                    id
                    label
                    type
                }
            }
        }
    }
    """
    
    variables = {"cardId": str(card_id)}
    resultado = fazer_requisicao_graphql(query, variables)
    
    if not resultado or 'data' not in resultado:
        log("❌ Erro ao buscar campos do card")
        return None
    
    phase_fields = resultado['data']['card']['current_phase']['fields']
    
    # Procurar campo de anexo de comprovante
    nomes_possiveis = [
        'anexo do comprovante de pagamento',  # Nome exato do campo no Pipefy
        'anexo do comprovante',
        'anexo comprovante',
        'comprovante de pagamento',
        'comprovante'
    ]
    
    for field in phase_fields:
        label = field.get('label', '').lower()
        field_type = field.get('type', '')
        field_id = field.get('id', '')
        
        # Verificar se é campo de attachment
        if field_type == 'attachment':
            log(f"   📎 Campo encontrado: '{field.get('label')}' (ID: {field_id}, Tipo: {field_type})")
            
            # Se o label bate com algum nome possível, retornar (prioriza match exato)
            for nome_possivel in nomes_possiveis:
                if nome_possivel in label:
                    log(f"   ✅ Campo de comprovante identificado: '{field.get('label')}' -> {field_id}")
                    return field_id
    
    # Se não encontrou por nome, retornar o primeiro campo de attachment
    for field in phase_fields:
        field_type = field.get('type', '')
        if field_type == 'attachment':
            field_id = field.get('id', '')
            log(f"   ⚠️ Usando primeiro campo de attachment encontrado: {field_id}")
            return field_id
    
    log("❌ Nenhum campo de attachment encontrado nos phase fields")
    return None


def buscar_anexos_existentes(card_id, field_id):
    """
    Busca anexos já existentes no campo de attachment do card
    
    Args:
        card_id: ID do card
        field_id: ID do campo de attachment
    
    Retorna:
        list: Lista de caminhos relativos dos arquivos existentes
    """
    log(f"🔍 Verificando anexos existentes no card {card_id}...")
    
    try:
        query = """
        query GetCardField($cardId: ID!) {
            card(id: $cardId) {
                id
                fields {
                    name
                    value
                    field {
                        id
                        type
                    }
                }
            }
        }
        """
        
        variables = {"cardId": str(card_id)}
        resultado = fazer_requisicao_graphql(query, variables)
        
        if not resultado or 'data' not in resultado:
            log("❌ Erro ao buscar campos do card")
            return []
        
        # Buscar o campo específico nos dados
        fields = resultado['data']['card']['fields']
        
        for field in fields:
            if field.get('field', {}).get('id') == field_id:
                existing_value = field.get('value')
                
                if existing_value:
                    # O valor pode ser string ou array
                    if isinstance(existing_value, list):
                        anexos_existentes = existing_value
                    elif isinstance(existing_value, str):
                        anexos_existentes = [existing_value]
                    else:
                        anexos_existentes = []
                    
                    log(f"   📎 {len(anexos_existentes)} anexo(s) existente(s) encontrado(s)")
                    for i, anexo in enumerate(anexos_existentes, 1):
                        # Extrair apenas o nome do arquivo para log
                        nome_arquivo = anexo.split('/')[-1] if '/' in anexo else anexo
                        log(f"      {i}. {nome_arquivo}")
                    
                    return anexos_existentes
                else:
                    log("   ✅ Nenhum anexo existente no campo")
                    return []
        
        log("   ⚠️ Campo de attachment não encontrado nos dados do card")
        return []
        
    except Exception as e:
        log(f"   ❌ Erro ao verificar anexos existentes: {e}")
        return []


def anexar_pdf_ao_card(card_id, arquivo_url):
    """
    Anexa o PDF ao campo de attachment do card PRESERVANDO arquivos existentes
    
    Args:
        card_id: ID do card no Pipefy
        arquivo_url: URL do arquivo no S3 do Pipefy
    
    Retorna:
        bool: True se sucesso, False se erro
    """
    log(f"📎 Anexando PDF ao card {card_id} (preservando anexos existentes)...")
    
    try:
        # Buscar o ID correto do campo de comprovante
        field_id = buscar_field_id_comprovante(card_id)
        
        if not field_id:
            log("❌ Não foi possível encontrar o campo de comprovante")
            return False
        
        # PASSO 1: Buscar anexos existentes
        anexos_existentes = buscar_anexos_existentes(card_id, field_id)
        
        # Extrair apenas o caminho relativo da URL do S3
        from urllib.parse import urlparse
        parsed = urlparse(arquivo_url)
        
        # Pegar apenas o path sem a barra inicial
        caminho_relativo = parsed.path.lstrip('/')
        
        log(f"   📄 Novo arquivo: {arquivo_url}")
        log(f"   📁 Caminho relativo: {caminho_relativo}")
        
        # PASSO 2: Verificar se o arquivo já existe (evitar duplicatas)
        nome_novo_arquivo = caminho_relativo.split('/')[-1]
        
        for anexo_existente in anexos_existentes:
            nome_existente = anexo_existente.split('/')[-1]
            if nome_existente == nome_novo_arquivo:
                log(f"   ⚠️ Arquivo '{nome_novo_arquivo}' já existe, substituindo...")
                # Remove o arquivo duplicado da lista
                anexos_existentes = [a for a in anexos_existentes if a.split('/')[-1] != nome_novo_arquivo]
                break
        
        # PASSO 3: Criar lista final com anexos existentes + novo arquivo
        anexos_finais = anexos_existentes + [caminho_relativo]
        
        log(f"   📊 Total de anexos após adição: {len(anexos_finais)}")
        for i, anexo in enumerate(anexos_finais, 1):
            nome_arquivo = anexo.split('/')[-1]
            status = "🆕 NOVO" if anexo == caminho_relativo else "📎 existente"
            log(f"      {i}. {nome_arquivo} ({status})")
        
        # Para campos de attachment, usar updateCardField com o field_id correto
        query = """
        mutation UpdateCardField($cardId: ID!, $fieldId: ID!, $value: [UndefinedInput]) {
            updateCardField(
                input: {
                    card_id: $cardId
                    field_id: $fieldId
                    new_value: $value
                }
            ) {
                success
                clientMutationId
            }
        }
        """
        
        variables = {
            "cardId": str(card_id),
            "fieldId": str(field_id),
            "value": anexos_finais  # Array com TODOS os anexos (existentes + novo)
        }
        
        headers = {
            "Authorization": f"Bearer {PIPEFY_API_TOKEN}",
            "Content-Type": "application/json"
        }
        
        response = requests.post(
            PIPEFY_API_URL,
            headers=headers,
            json={
                "query": query,
                "variables": variables
            },
            timeout=10
        )
        
        if response.status_code != 200:
            log(f"   ❌ Erro ao anexar: HTTP {response.status_code}")
            log(f"   Resposta: {response.text}")
            return False
        
        data = response.json()
        
        if 'errors' in data:
            log(f"   ❌ Erro GraphQL: {data['errors']}")
            return False
        
        success = data.get('data', {}).get('updateCardField', {}).get('success', False)
        
        if success:
            log(f"   ✅ PDF anexado com sucesso ao card!")
            return True
        else:
            log(f"   ❌ Falha ao anexar PDF")
            return False
        
    except Exception as e:
        log(f"   ❌ Erro ao anexar PDF: {e}")
        return False


def marcar_comprovante_anexado_corretamente(card_id):
    """
    Marca o campo "Comprovante anexado corretamente?" como "Sim" (PHASE FIELDS)
    
    Args:
        card_id: ID do card no Pipefy
    
    Retorna:
        bool: True se sucesso, False se erro
    """
    log(f"✅ Marcando 'Comprovante anexado corretamente?' como SIM (phase fields)...")
    
    try:
        # Buscar o card para encontrar o field_id do checkbox nos PHASE FIELDS
        query_card = """
        query GetCard($cardId: ID!) {
            card(id: $cardId) {
                current_phase {
                    id
                    name
                    fields {
                        id
                        label
                        type
                    }
                }
            }
        }
        """
        
        headers = {
            "Authorization": f"Bearer {PIPEFY_API_TOKEN}",
            "Content-Type": "application/json"
        }
        
        response = requests.post(
            PIPEFY_API_URL,
            headers=headers,
            json={
                "query": query_card,
                "variables": {"cardId": str(card_id)}
            },
            timeout=10
        )
        
        if response.status_code != 200:
            log(f"   ❌ Erro ao buscar card: HTTP {response.status_code}")
            return False
        
        data = response.json()
        card_data = data.get('data', {}).get('card', {})
        phase_fields = card_data.get('current_phase', {}).get('fields', [])
        
        # Procurar o campo do checkbox
        field_id = None
        for field in phase_fields:
            field_label = field.get('label', '').lower()
            if 'comprovante anexado corretamente' in field_label:
                field_id = field['id']
                log(f"   Campo encontrado: {field['label']} (ID: {field_id})")
                break
        
        if not field_id:
            log(f"   ❌ Campo 'Comprovante anexado corretamente?' não encontrado")
            return False
        
        # Atualizar o campo para "Sim"
        # IMPORTANTE: Usar [UndefinedInput] (array) para campos radio_vertical
        mutation = """
        mutation UpdateCardField($cardId: ID!, $fieldId: ID!, $value: [UndefinedInput]) {
            updateCardField(
                input: {
                    card_id: $cardId
                    field_id: $fieldId
                    new_value: $value
                }
            ) {
                success
            }
        }
        """
        
        variables = {
            "cardId": str(card_id),
            "fieldId": str(field_id),
            "value": ["Sim"]  # Array com string "Sim"
        }
        
        response = requests.post(
            PIPEFY_API_URL,
            headers=headers,
            json={
                "query": mutation,
                "variables": variables
            },
            timeout=10
        )
        
        if response.status_code != 200:
            log(f"   ❌ Erro ao atualizar campo: HTTP {response.status_code}")
            return False
        
        data = response.json()
        
        if 'errors' in data:
            log(f"   ❌ Erro GraphQL: {data['errors']}")
            return False
        
        success = data.get('data', {}).get('updateCardField', {}).get('success', False)
        
        if success:
            log(f"   ✅ Campo marcado como SIM com sucesso!")
            return True
        else:
            log(f"   ❌ Falha ao marcar campo")
            return False
        
    except Exception as e:
        log(f"   ❌ Erro ao marcar campo: {e}")
        return False


def mover_card_para_fase(card_id, fase_id_destino):
    """
    Move um card para uma fase específica usando o ID da fase diretamente
    
    Args:
        card_id: ID do card a ser movido
        fase_id_destino: ID da fase de destino (usar constantes FASE_TAXAS_*)
    
    Retorna:
        bool: True se sucesso, False se erro
    """
    log(f"🔄 Movendo card {card_id} para fase ID: {fase_id_destino}...")
    
    try:
        # Mutation para mover o card
        log(f"   � Executando mutation moveCardToPhase...")
        
        query = """
        mutation MoveCardToPhase($cardId: ID!, $phaseId: ID!) {
            moveCardToPhase(
                input: {
                    card_id: $cardId
                    destination_phase_id: $phaseId
                }
            ) {
                card {
                    id
                    title
                }
                success
            }
        }
        """
        
        variables = {
            "cardId": str(card_id),
            "phaseId": str(fase_id_destino)
        }
        
        headers = {
            "Authorization": f"Bearer {PIPEFY_API_TOKEN}",
            "Content-Type": "application/json"
        }
        
        log(f"   📡 Enviando requisição para Pipefy API...")
        response = requests.post(
            PIPEFY_API_URL,
            headers=headers,
            json={
                "query": query,
                "variables": variables
            },
            timeout=10
        )
        
        if response.status_code != 200:
            log(f"   ❌ ERRO HTTP: Status {response.status_code}")
            log(f"   📄 Resposta: {response.text}")
            return False
        
        data = response.json()
        log(f"   📦 Resposta recebida: {data}")
        
        if 'errors' in data:
            log(f"   ❌ ERRO GraphQL: {data['errors']}")
            return False
        
        success = data.get('data', {}).get('moveCardToPhase', {}).get('success', False)
        
        if success:
            log(f"   ✅ SUCCESS! Card movido para fase ID {fase_id_destino}")
            return True
        else:
            log(f"   ❌ FALHA: success=False na resposta")
            log(f"   📋 Resposta completa: {data}")
            return False
        
    except Exception as e:
        log(f"   ❌ EXCEÇÃO ao mover card: {type(e).__name__}: {e}")
        import traceback
        log(f"   📋 Traceback: {traceback.format_exc()}")
        return False


# ==================== FLUXO COMPLETO - BUSCAR E ANEXAR ====================

def card_ja_possui_comprovante(card):
    """
    Verifica se o card já possui comprovante de pagamento anexado
    
    Args:
        card: Dicionário com dados do card do Pipefy
    
    Retorna:
        bool: True se já possui comprovante, False caso contrário
    """
    fields = card.get('fields', [])
    
    for field in fields:
        nome = field.get('name', '').lower()
        valor = field.get('value')
        tipo = field.get('field', {}).get('type', '')
        
        # Verificar campos de anexo que contenham "comprovante" ou "pagamento"
        if tipo == 'attachment' and valor:
            if 'comprovante' in nome or 'pagamento' in nome:
                # Se o campo tem valor (URL ou lista de URLs), tem comprovante
                if isinstance(valor, list) and len(valor) > 0:
                    return True
                elif isinstance(valor, str) and valor.strip():
                    return True
    
    return False


def processar_card_completo(card, cache_comprovantes=None):
    """
    Fluxo completo: busca comprovante do Santander e anexa no card do Pipefy
    
    Args:
        card: Dicionário com dados do card do Pipefy
        cache_comprovantes: Dicionário com comprovantes já buscados (opcional, evita consultas repetidas)
    
    Retorna:
        dict: Resultado do processamento com status e detalhes
    """
    log(f"\n{'='*80}")
    log(f"🔄 Processando card: {card['title']}")
    log(f"   Card ID: {card['id']}")
    
    # Verificar se o card já possui comprovante anexado
    if card_ja_possui_comprovante(card):
        log(f"⏭️  Pulando card {card['title']} - já possui comprovante anexado")
        return {
            'card_id': card['id'],
            'card_title': card['title'],
            'sucesso': False,
            'etapa': 'verificacao',
            'motivo': 'Card já possui comprovante anexado',
            'pulado': True
        }
    
    # Extrair dados do card para o resultado
    dados_card = extrair_dados_para_matching(card)
    
    resultado = {
        'card_id': card['id'],
        'card_title': card['title'],
        'card_dados': dados_card,  # Adicionar dados do card
        'sucesso': False,
        'etapa': '',
        'motivo': ''
    }
    
    # 1. Verificar se há clientes Santander configurados
    if not santander_clients:
        resultado['etapa'] = 'autenticacao'
        resultado['motivo'] = 'Nenhum cliente Santander configurado'
        log(f"❌ {card['title']}: {resultado['motivo']}")
        return resultado
    
    # 2. Buscar match do comprovante em todos os fundos (usando cache)
    resultado['etapa'] = 'matching'
    match_result = processar_card_com_santander(card, cache_comprovantes=cache_comprovantes)
    
    if not match_result['sucesso']:
        resultado['motivo'] = match_result['motivo']
        log(f"❌ {card['title']}: {resultado['motivo']}")
        return resultado
    
    comprovante = match_result['comprovante']
    payment_id = comprovante['payment_id']
    fundo_id = comprovante.get('fundo_id')
    fundo_nome = comprovante.get('fundo_nome', 'N/A')
    cliente = comprovante.get('cliente')
    
    log(f"✅ Match encontrado - Payment ID: {payment_id}")
    log(f"   Fundo: {fundo_nome} ({fundo_id})")
    
    # 3. Baixar PDF do comprovante usando o cliente do fundo correto
    resultado['etapa'] = 'download_pdf'
    caminho_pdf = obter_pdf_comprovante(payment_id, fundo_id=fundo_id, cliente_santander=cliente)
    
    if not caminho_pdf:
        resultado['motivo'] = 'Falha ao baixar PDF do Santander'
        log(f"❌ {card['title']}: {resultado['motivo']}")
        return resultado
    
    log(f"✅ PDF baixado: {caminho_pdf}")
    
    # 4. Fazer upload para o Pipefy
    resultado['etapa'] = 'upload_pipefy'
    arquivo_url = fazer_upload_arquivo_pipefy(caminho_pdf)
    
    if not arquivo_url:
        resultado['motivo'] = 'Falha ao fazer upload para Pipefy'
        log(f"❌ {card['title']}: {resultado['motivo']}")
        return resultado
    
    log(f"✅ Arquivo enviado para Pipefy: {arquivo_url}")
    
    # 5. Anexar PDF ao card
    resultado['etapa'] = 'anexar_card'
    anexou = anexar_pdf_ao_card(card['id'], arquivo_url)
    
    if not anexou:
        resultado['motivo'] = 'Falha ao anexar PDF ao card'
        log(f"❌ {card['title']}: {resultado['motivo']}")
        return resultado
    
    log(f"✅ PDF anexado ao card!")
    
    # 6. Marcar "Comprovante anexado corretamente?" como SIM
    resultado['etapa'] = 'marcar_checkbox'
    marcou = marcar_comprovante_anexado_corretamente(card['id'])
    
    if not marcou:
        resultado['motivo'] = 'PDF anexado, mas falha ao marcar checkbox'
        log(f"⚠️ {card['title']}: {resultado['motivo']}")
        # Continua mesmo se falhar, pois o PDF já foi anexado
    else:
        log(f"✅ Checkbox marcado como SIM!")
    
    # 7. Mover card para fase "Solicitação Paga"
    resultado['etapa'] = 'mover_fase'
    log(f"🔄 Iniciando movimentação para fase 'Solicitação Paga' (ID: {FASE_TAXAS_SOLICITACAO_PAGA})...")
    moveu = mover_card_para_fase(card['id'], FASE_TAXAS_SOLICITACAO_PAGA)
    
    if not moveu:
        resultado['motivo'] = 'PDF anexado, mas falha ao mover para "Solicitação Paga"'
        resultado['sucesso'] = True  # Consideramos sucesso parcial
        log(f"⚠️ {card['title']}: {resultado['motivo']}")
        log(f"⚠️ Card ID: {card['id']} - Verifique manualmente")
        return resultado
    
    # Sucesso completo!
    resultado['sucesso'] = True
    resultado['etapa'] = 'concluido'
    resultado['motivo'] = 'Comprovante anexado e card movido com sucesso'
    resultado['arquivo_url'] = arquivo_url
    resultado['payment_id'] = payment_id
    resultado['fase_destino'] = 'Solicitação Paga'
    
    log(f"✅✅✅ {card['title']}: PROCESSAMENTO COMPLETO!")
    log(f"{'='*80}\n")
    
    return resultado


def processar_todos_cards(data_busca=None):
    """
    Processa todos os cards da fase "Aguardando Comprovante" do Pipe de TAXAS
    Busca comprovantes e anexa PDFs automaticamente
    
    Args:
        data_busca: Data para buscar comprovantes (formato YYYY-MM-DD). Se None, usa ONTEM.
    """
    log("\n" + "="*80)
    log("🚀 INICIANDO PROCESSAMENTO DE CARDS - PIPE TAXAS - ANEXAR COMPROVANTES")
    log("="*80 + "\n")
    
    # 1. Buscar ID da fase
    fase_id = buscar_fase_por_nome(PIPE_TAXAS_ID, "Aguardando Comprovante")
    
    if not fase_id:
        log("❌ Não foi possível encontrar a fase. Encerrando.")
        return None
    
    # 2. Buscar cards da fase (TODOS os cards, sem limite)
    cards = buscar_cards_da_fase(fase_id, limite=999999)  # Sem limite prático
    
    if not cards:
        log("ℹ️ Nenhum card para processar")
        return []
    
    log(f"📋 Total de cards a processar: {len(cards)}\n")
    
    # 3. CACHEAR COMPROVANTES - Buscar UMA ÚNICA VEZ antes do loop
    log("="*80)
    log("📦 CACHEANDO COMPROVANTES DE TODOS OS FUNDOS")
    log("="*80)
    
    # Determinar data de busca
    from datetime import date, timedelta
    if data_busca is None:
        data_hoje = date.today()
        data_inicio = data_hoje
        data_fim = data_hoje
        data_busca_str = data_hoje.strftime('%Y-%m-%d')
        
        log(f"� DATA DE BUSCA: HOJE ({data_busca_str})")
        log(f"   ⚠️  Nenhuma data específica informada, usando data atual")
    else:
        data_inicio = data_busca
        data_fim = data_busca
        data_busca_str = data_busca if isinstance(data_busca, str) else data_busca.strftime('%Y-%m-%d')
        
        log(f"� DATA DE BUSCA: {data_busca_str}")
        log(f"   ✅ Data específica informada pelo usuário")
    
    log("   ⚠️  API Santander não fornece documento do beneficiário")
    log("   Matching será feito apenas por VALOR\n")
    
    try:
        if isinstance(data_inicio, str):
            cache_comprovantes = listar_comprovantes_todos_fundos(data_inicio, data_fim)
        else:
            cache_comprovantes = listar_comprovantes_todos_fundos(
                data_inicio.strftime('%Y-%m-%d'), 
                data_fim.strftime('%Y-%m-%d')
            )
        
        # Contar total de comprovantes
        total_comprovantes = sum(len(comps) for comps in cache_comprovantes.values())
        
        log(f"\n✅ Cache criado com sucesso!")
        log(f"   📊 Total: {total_comprovantes} comprovante(s) encontrado(s)\n")
        
        # Log resumido por fundo
        if total_comprovantes > 0:
            log("   📋 Distribuição por fundo:")
            for fundo_id, comprovantes in cache_comprovantes.items():
                if len(comprovantes) > 0:
                    log(f"      • {fundo_id}: {len(comprovantes)} comprovante(s)")
        
        log("\n" + "="*80 + "\n")
        
    except Exception as e:
        log(f"\n❌ Erro ao cachear comprovantes: {e}")
        log("   Processamento será interrompido.\n")
        return None
    
    # 4. Processar cada card usando o cache
    resultados = []
    cards_com_match = 0
    cards_sem_match = 0
    cards_anexados = 0
    cards_pulados = 0
    
    log("="*80)
    log("🔄 PROCESSANDO CARDS")
    log("="*80 + "\n")
    
    for idx, card in enumerate(cards, 1):
        card_title = card.get('title', 'Sem título')
        log(f"[{idx}/{len(cards)}] 📄 Card: {card_title}")
        
        resultado = processar_card_completo(card, cache_comprovantes=cache_comprovantes)
        resultados.append(resultado)
        
        if resultado.get('pulado', False):
            cards_pulados += 1
            log(f"   ⏭️  Pulado (já tem comprovante)")
        elif resultado['sucesso']:
            cards_anexados += 1
            log(f"   ✅ Comprovante anexado com sucesso!")
        elif resultado['etapa'] == 'matching' and 'não encontrado' in resultado['motivo'].lower():
            cards_sem_match += 1
            log(f"   ⚠️  Sem match: {resultado['motivo']}")
        elif resultado['etapa'] == 'matching':
            cards_com_match += 1
            log(f"   ℹ️  Match encontrado mas não anexado: {resultado['motivo']}")
        else:
            log(f"   ❌ Erro: {resultado['motivo']}")
        
        log("")  # Linha em branco entre cards
    
    # 5. Relatório final
    log("="*80)
    log("📊 RELATÓRIO FINAL - PIPE TAXAS")
    log("="*80)
    
    sucessos = [r for r in resultados if r['sucesso']]
    pulados = [r for r in resultados if r.get('pulado', False)]
    falhas = [r for r in resultados if not r['sucesso'] and not r.get('pulado', False)]
    
    log(f"\n📈 Estatísticas:")
    log(f"   • Total de cards processados: {len(resultados)}")
    log(f"   • ✅ Comprovantes anexados: {cards_anexados}")
    log(f"   • ⏭️  Cards pulados (já têm comprovante): {cards_pulados}")
    log(f"   • ⚠️  Cards sem match: {cards_sem_match}")
    log(f"   • ❌ Erros/Falhas: {len(falhas) - cards_sem_match}")
    
    # NOVA SEÇÃO: Resumo detalhado dos matches com sucesso
    if sucessos:
        log(f"\n{'='*80}")
        log(f"✅ COMPROVANTES ANEXADOS COM SUCESSO ({len(sucessos)})")
        log(f"{'='*80}")
        log(f"\n📋 Informações dos Matches:\n")
        
        for idx, r in enumerate(sucessos, 1):
            card_info = r.get('card_dados', {})
            comprovante_info = r.get('comprovante_match', {})
            
            log(f"[{idx}] {r['card_title']}")
            log(f"    💰 Valor: R$ {card_info.get('valor', 0):,.2f}")
            log(f"    🏢 Beneficiário: {card_info.get('nome_beneficiario', 'N/A')}")
            log(f"    📄 Documento: {card_info.get('documento_beneficiario', 'N/A')}")
            log(f"    🏦 Fundo: {comprovante_info.get('fundo', 'N/A')}")
            log(f"    📅 Data Pagamento: {comprovante_info.get('data_pagamento', 'N/A')}")
            
            if r.get('payment_id'):
                payment_id_short = r.get('payment_id', 'N/A')[:30] + '...' if len(r.get('payment_id', '')) > 30 else r.get('payment_id', 'N/A')
                log(f"    � Payment ID: {payment_id_short}")
            
            log(f"    ✅ Status: Anexado e movido para 'Solicitação Paga'")
            log("")
    
    if falhas:
        falhas_reais = [r for r in falhas if 'não encontrado' not in r['motivo'].lower()]
        if falhas_reais:
            log(f"\n{'='*80}")
            log(f"❌ ERROS DURANTE PROCESSAMENTO ({len(falhas_reais)})")
            log(f"{'='*80}")
            for r in falhas_reais:
                log(f"\n✗ {r['card_title']}")
                log(f"   Etapa: {r['etapa']}")
                log(f"   Motivo: {r['motivo']}")
    
    log("\n" + "="*80)
    log(f"🏁 PROCESSAMENTO CONCLUÍDO - PIPE TAXAS")
    log(f"   📅 Data de busca utilizada: {data_busca_str if 'data_busca_str' in locals() else 'N/A'}")
    log(f"   📊 Taxa de sucesso: {len(sucessos)}/{len(resultados)} ({(len(sucessos)/len(resultados)*100):.1f}%)")
    if sucessos:
        log(f"   ✅ {len(sucessos)} card(s) com comprovante anexado e movido(s) para 'Solicitação Paga'")
    log("="*80 + "\n")
    
    return resultados


def testar_matching_apenas(data_busca=None):
    """
    Testa apenas a etapa de matching (sem download de PDF ou anexação)
    Mostra quais cards teriam match com os comprovantes do Santander
    
    Args:
        data_busca: Data para buscar comprovantes (formato YYYY-MM-DD). Se None, usa hoje.
    """
    log("\n" + "="*80)
    log("🧪 TESTE DE MATCHING - PIPE TAXAS - VERIFICAR QUAIS CARDS TÊM COMPROVANTES")
    log("="*80 + "\n")
    
    # 1. Buscar ID da fase "Solicitação Paga" (cards recém pagos)
    fase_id = buscar_fase_por_nome(PIPE_TAXAS_ID, "Solicitação Paga")
    
    if not fase_id:
        log("❌ Não foi possível encontrar a fase 'Solicitação Paga'. Encerrando.")
        return None
    
    # 2. Buscar cards da fase
    cards = buscar_cards_da_fase(fase_id, limite=200)
    
    if not cards:
        log("ℹ️ Nenhum card para processar na fase 'Solicitação Paga'")
        return []
    
    log(f"📋 Total de cards a testar: {len(cards)}\n")
    
    # 3. CACHEAR COMPROVANTES
    log("="*80)
    log("📦 CACHEANDO COMPROVANTES DE TODOS OS FUNDOS")
    log("="*80)
    
    # Determinar data de busca
    from datetime import date
    if data_busca is None:
        data_busca = date.today().strftime('%Y-%m-%d')
    
    log(f"📅 Data de busca: {data_busca}\n")
    
    try:
        cache_comprovantes = listar_comprovantes_todos_fundos(data_busca, data_busca)
        total_comprovantes = sum(len(comps) for comps in cache_comprovantes.values())
        
        log(f"✅ Cache criado: {total_comprovantes} comprovante(s)\n")
        
        if total_comprovantes > 0:
            log("📋 Distribuição por fundo:")
            for fundo_id, comprovantes in cache_comprovantes.items():
                if len(comprovantes) > 0:
                    log(f"   • {fundo_id}: {len(comprovantes)} comprovante(s)")
        
        log("\n" + "="*80)
        log("🎯 TESTANDO MATCHING")
        log("="*80 + "\n")
        
    except Exception as e:
        log(f"\n❌ Erro ao cachear comprovantes: {e}")
        return None
    
    # 4. Testar matching para cada card
    resultados = []
    
    for idx, card in enumerate(cards, 1):
        log(f"\n{'='*80}")
        log(f"[{idx}/{len(cards)}] {card['title']} (ID: {card['id']})")
        log(f"{'='*80}")
        
        # Extrair dados
        dados = extrair_dados_para_matching(card)
        
        log(f"📄 Dados extraídos:")
        log(f"   • Documento: {dados.get('documento_beneficiario', 'N/A')}")
        log(f"   • Nome: {dados.get('nome_beneficiario', 'N/A')}")
        log(f"   • Valor: R$ {dados.get('valor', 0):,.2f}")
        log(f"   • Data: {dados.get('data_pagamento', 'N/A')}")
        
        # Validações básicas
        if not dados['documento_beneficiario']:
            log(f"\n❌ RESULTADO: Card sem documento do beneficiário")
            resultados.append({'card': card['title'], 'match': False, 'motivo': 'Sem documento'})
            continue
        
        # Buscar comprovantes (usando cache)
        comprovantes = buscar_comprovante_por_documento(
            dados['documento_beneficiario'],
            dados['data_pagamento'],
            cache_comprovantes=cache_comprovantes
        )
        
        if not comprovantes:
            log(f"\n❌ RESULTADO: Nenhum comprovante encontrado na data")
            resultados.append({'card': card['title'], 'match': False, 'motivo': 'Sem comprovantes na data'})
            continue
        
        # Fazer match por CNPJ FUNDO + BENEFICIÁRIO + VALOR
        nome_beneficiario = dados.get('nome_beneficiario')
        nome_fundo = dados.get('nome_fundo')
        cnpj_fundo = dados.get('cnpj_fundo')
        comprovante_match = fazer_match_por_valor(
            comprovantes, 
            dados['valor'], 
            nome_beneficiario=nome_beneficiario,
            nome_fundo=nome_fundo,
            cnpj_fundo=cnpj_fundo
        )
        
        if comprovante_match:
            log(f"\n✅ RESULTADO: MATCH ENCONTRADO!")
            log(f"   • Payment ID: {comprovante_match['payment_id']}")
            log(f"   • Fundo: {comprovante_match.get('fundo_nome', 'N/A')}")
            log(f"   • Beneficiário: {comprovante_match.get('payee_name', 'N/A')}")
            valor_match = float(comprovante_match['amount'])
            log(f"   • Valor: R$ {valor_match:,.2f}")
            resultados.append({'card': card['title'], 'match': True, 'payment_id': comprovante_match['payment_id']})
        else:
            log(f"\n❌ RESULTADO: Valor não encontrado (R$ {dados['valor']:,.2f})")
            resultados.append({'card': card['title'], 'match': False, 'motivo': 'Valor não confere'})
    
    # 5. Relatório final
    log("\n" + "="*80)
    log("📊 RELATÓRIO FINAL DO TESTE DE MATCHING - PIPE TAXAS")
    log("="*80)
    
    matches = [r for r in resultados if r['match']]
    sem_match = [r for r in resultados if not r['match']]
    
    log(f"\n✅ Cards com MATCH: {len(matches)}/{len(resultados)}")
    for r in matches:
        log(f"   ✓ {r['card']} (Payment ID: {r['payment_id']})")
    
    if sem_match:
        log(f"\n❌ Cards SEM MATCH: {len(sem_match)}/{len(resultados)}")
        for r in sem_match:
            log(f"   ✗ {r['card']} - {r.get('motivo', 'Desconhecido')}")
    
    log("\n" + "="*80)
    log(f"🏁 TESTE CONCLUÍDO - {len(matches)}/{len(resultados)} cards têm comprovantes")
    log("="*80 + "\n")
    
    return resultados


# ==================== EXECUÇÃO ====================

if __name__ == "__main__":
    # Modo padrão: EXECUTAR AUTOMAÇÃO COMPLETA - Anexar comprovantes PIPE TAXAS
    # Busca comprovantes APENAS DE HOJE automaticamente
    
    log(f"⚠️ MODO AUTOMÁTICO: Buscando comprovantes apenas de hoje")
    processar_todos_cards()  # data_busca=None usa apenas hoje
