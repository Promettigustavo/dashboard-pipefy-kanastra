"""
Anexar Comprovantes Pipe - Versão Simplificada
Passo 1: Obter todas as informações dos cards do Pipefy
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
PIPE_LIQUIDACAO_ID = "303418384"

# IDs das Fases do Pipe Liquidação
FASE_LIQUIDACAO_AGUARDANDO_COMPROVANTE = "325983455"
FASE_LIQUIDACAO_SOLICITACAO_PAGA = "321352632"

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


def exibir_informacoes_card(card, indice=None):
    """Exibe todas as informações de um card de forma organizada"""
    
    prefixo = f"📄 CARD {indice}" if indice else "📄 CARD"
    
    print("\n" + "="*80)
    log(f"{prefixo}: {card['title']}")
    print("="*80)
    
    # Informações básicas
    log(f"🆔 ID: {card['id']}")
    log(f"📅 Criado em: {card.get('createdAt', 'N/A')}")
    log(f"✅ Finalizado em: {card.get('finished_at', 'N/A')}")
    
    # Responsáveis
    if card.get('assignees'):
        responsaveis = ", ".join([a['name'] for a in card['assignees']])
        log(f"👤 Responsáveis: {responsaveis}")
    else:
        log(f"👤 Responsáveis: Nenhum")
    
    # Campos do card
    log(f"\n📋 CAMPOS DO CARD:")
    print("-" * 80)
    
    if not card.get('fields'):
        log("   (Nenhum campo encontrado)")
    else:
        campos_ordenados = sorted(card['fields'], key=lambda x: x['name'])
        
        for field in campos_ordenados:
            nome = field['name']
            valor = field['value']
            tipo = field['field']['type'] if field.get('field') else 'unknown'
            
            # Formatar valor baseado no tipo
            if valor is None or valor == '':
                valor_formatado = "(vazio)"
            elif isinstance(valor, list):
                valor_formatado = f"[{len(valor)} itens]"
            elif len(str(valor)) > 100:
                valor_formatado = str(valor)[:100] + "..."
            else:
                valor_formatado = str(valor)
            
            log(f"   • {nome}")
            log(f"     Tipo: {tipo}")
            log(f"     Valor: {valor_formatado}")
            print()


def obter_todos_cards_aguardando_comprovante():
    """Função principal: busca e exibe todos os cards da fase 'Aguardando Comprovante'"""
    
    log("="*80)
    log("🚀 INICIANDO BUSCA DE CARDS - AGUARDANDO COMPROVANTE")
    log("="*80)
    
    # 1. Buscar ID da fase
    fase_id = buscar_fase_por_nome(PIPE_LIQUIDACAO_ID, "Aguardando Comprovante")
    
    if not fase_id:
        log("❌ Não foi possível encontrar a fase. Encerrando.")
        return
    
    # 2. Buscar cards da fase
    cards = buscar_cards_da_fase(fase_id, limite=50)
    
    if not cards:
        log("⚠️ Nenhum card encontrado na fase 'Aguardando Comprovante'")
        return
    
    # 3. Exibir informações detalhadas de cada card
    log(f"\n📊 EXIBINDO INFORMAÇÕES DE {len(cards)} CARDS:")
    
    for i, card in enumerate(cards, 1):
        exibir_informacoes_card(card, i)
    
    # 4. Resumo final
    print("\n" + "="*80)
    log("📊 RESUMO DA BUSCA")
    print("="*80)
    log(f"✅ Total de cards encontrados: {len(cards)}")
    log(f"📍 Fase: Aguardando Comprovante (ID: {fase_id})")
    log(f"🏢 Pipe: {PIPE_LIQUIDACAO_ID}")


def extrair_dados_para_matching(card):
    """
    Extrai os dados necessários do card para fazer matching com API do Santander
    
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
        'nome_beneficiario': '',
        'data_pagamento': '',
        'nome_fundo': '',
        'cnpj_fundo': '',
        'descricao': ''
    }
    
    fields = card.get('fields', [])
    
    # Converter lista de fields para dict por nome
    fields_dict = {}
    for field in fields:
        nome = field.get('name', '').lower()
        valor = field.get('value')
        fields_dict[nome] = valor
    
    # 1. EXTRAIR CNPJ DO BENEFICIÁRIO
    if 'cnpj' in fields_dict and fields_dict['cnpj']:
        cnpj = re.sub(r'\D', '', str(fields_dict['cnpj']))
        if len(cnpj) == 14:
            dados['cnpj_beneficiario'] = cnpj
            dados['documento_beneficiario'] = cnpj
    
    # 2. EXTRAIR CPF DO BENEFICIÁRIO (se não tiver CNPJ)
    if not dados['documento_beneficiario'] and 'cpf' in fields_dict and fields_dict['cpf']:
        cpf = re.sub(r'\D', '', str(fields_dict['cpf']))
        if len(cpf) == 11:
            dados['cpf_beneficiario'] = cpf
            dados['documento_beneficiario'] = cpf
    
    # 3. EXTRAIR VALOR
    if 'valor' in fields_dict and fields_dict['valor']:
        # Formato brasileiro: 1.345,50 → remover pontos de milhar, trocar vírgula por ponto
        valor_str = str(fields_dict['valor']).replace('R$', '').strip()
        # Remover pontos (separador de milhar)
        valor_str = valor_str.replace('.', '')
        # Trocar vírgula por ponto (decimal)
        valor_str = valor_str.replace(',', '.')
        try:
            dados['valor'] = float(valor_str)
        except:
            dados['valor'] = 0.0
    
    # 4. EXTRAIR NOME DO BENEFICIÁRIO
    if 'razão social do beneficiário' in fields_dict:
        dados['nome_beneficiario'] = str(fields_dict['razão social do beneficiário'])
    elif 'beneficiário' in fields_dict:
        dados['nome_beneficiario'] = str(fields_dict['beneficiário'])
    
    # 5. DATA DE BUSCA DO COMPROVANTE
    # Não precisa definir aqui, será buscado do dia de hoje no cache
    # Deixar vazio para usar o cache do dia
    dados['data_pagamento'] = ''
    
    # 6. EXTRAIR NOME DO FUNDO
    if 'nome do fundo' in fields_dict:
        dados['nome_fundo'] = str(fields_dict['nome do fundo'])
    
    # 7. EXTRAIR CNPJ DO FUNDO
    if 'cnpj do fundo' in fields_dict and fields_dict['cnpj do fundo']:
        cnpj_fundo = re.sub(r'\D', '', str(fields_dict['cnpj do fundo']))
        if len(cnpj_fundo) == 14:
            dados['cnpj_fundo'] = cnpj_fundo
    
    # 8. EXTRAIR DESCRIÇÃO
    if 'descrição' in fields_dict:
        dados['descricao'] = str(fields_dict['descrição'])
    
    return dados


def exibir_dados_extraidos_para_matching():
    """
    Função para testar a extração de dados dos cards para matching
    """
    log("="*80)
    log("🔍 ANALISANDO DADOS PARA MATCHING COM API SANTANDER")
    log("="*80)
    
    # 1. Buscar ID da fase
    fase_id = buscar_fase_por_nome(PIPE_LIQUIDACAO_ID, "Aguardando Comprovante")
    
    if not fase_id:
        log("❌ Não foi possível encontrar a fase. Encerrando.")
        return
    
    # 2. Buscar cards da fase
    cards = buscar_cards_da_fase(fase_id, limite=50)
    
    if not cards:
        log("⚠️ Nenhum card encontrado na fase 'Aguardando Comprovante'")
        return
    
    log(f"\n📊 DADOS EXTRAÍDOS DE {len(cards)} CARDS PARA MATCHING:\n")
    
    cards_com_documento = 0
    cards_sem_documento = 0
    
    for i, card in enumerate(cards, 1):
        dados = extrair_dados_para_matching(card)
        
        print("="*80)
        log(f"📄 CARD {i}: {card['title']}")
        print("-"*80)
        
        if dados['documento_beneficiario']:
            cards_com_documento += 1
            log(f"✅ Documento Beneficiário: {dados['documento_beneficiario']} ({'CNPJ' if len(dados['documento_beneficiario']) == 14 else 'CPF'})")
        else:
            cards_sem_documento += 1
            log(f"❌ Documento Beneficiário: NÃO ENCONTRADO")
        
        log(f"💰 Valor: R$ {dados['valor']:,.2f}")
        log(f"👤 Nome: {dados['nome_beneficiario']}")
        log(f"📅 Data de Busca: {dados['data_pagamento']} (DATA ATUAL - dia da execução)")
        log(f"🏢 Fundo: {dados['nome_fundo']}")
        
        # Simular chamada API
        if dados['documento_beneficiario'] and dados['data_pagamento']:
            log(f"\n🔍 Query API Santander:")
            log(f"   beneficiary_document={dados['documento_beneficiario']}")
            log(f"   start_date={dados['data_pagamento']}")
            log(f"   end_date={dados['data_pagamento']}")
            log(f"   ✅ Pronto para buscar comprovante!")
            log(f"   💰 Match será feito por VALOR EXATO: R$ {dados['valor']:,.2f}")
            log(f"   ℹ️  Busca será feita na data ATUAL (não no vencimento)")
        else:
            log(f"\n⚠️ Faltam dados para buscar na API:")
            if not dados['documento_beneficiario']:
                log(f"   ❌ Documento do beneficiário")
            if not dados['data_pagamento']:
                log(f"   ❌ Data de pagamento")
        
        print()
    
    # Resumo
    print("="*80)
    log("📊 RESUMO")
    print("="*80)
    log(f"✅ Cards com documento: {cards_com_documento}")
    log(f"❌ Cards sem documento: {cards_sem_documento}")
    log(f"📈 Taxa de sucesso: {(cards_com_documento/len(cards)*100):.1f}%")
    print()


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
    
    # 4. Fazer match por CNPJ FUNDO + BENEFICIÁRIO + VALOR
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
        caminho_pdf = cliente.buscar_e_baixar_comprovante(payment_id)
        
        if caminho_pdf:
            log(f"✅ PDF salvo em: {caminho_pdf}")
            return str(caminho_pdf)
        else:
            log(f"❌ Falha ao baixar PDF")
            return None
            
    except Exception as e:
        log(f"❌ Erro ao obter PDF: {e}")
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


def anexar_pdf_ao_card(card_id, arquivo_url):
    """
    Anexa o PDF ao campo de attachment do card
    
    Args:
        card_id: ID do card no Pipefy
        arquivo_url: URL do arquivo no S3 do Pipefy
    
    Retorna:
        bool: True se sucesso, False se erro
    """
    log(f"📎 Anexando PDF ao card {card_id}...")
    
    try:
        # Extrair apenas o caminho relativo da URL do S3
        # A URL vem como: https://pipefy-prd-us-east-1.s3.amazonaws.com/orgs/UUID/uploads/UUID/file.pdf
        # Precisamos apenas: orgs/UUID/uploads/UUID/file.pdf
        from urllib.parse import urlparse
        parsed = urlparse(arquivo_url)
        
        # Pegar apenas o path sem a barra inicial
        caminho_relativo = parsed.path.lstrip('/')
        
        log(f"   URL original: {arquivo_url}")
        log(f"   Caminho relativo: {caminho_relativo}")
        
        # Para campos de attachment, usar updateCardField com o field_id correto
        # Seguindo a documentação oficial: https://developers.pipefy.com/reference/add-attachments-to-a-card-or-field
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
            "fieldId": "anexar_comprovante_de_pagamento",  # Campo correto de comprovante
            "value": [caminho_relativo]  # Array com o CAMINHO RELATIVO (não URL completa)
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


def anexar_arquivo_ao_card(card_id, caminho_arquivo):
    """
    Faz upload de um arquivo e anexa ao card (SEM mudar a fase)
    
    Args:
        card_id: ID do card no Pipefy
        caminho_arquivo: Caminho completo do arquivo PDF
    
    Retorna:
        bool: True se sucesso, False se erro
    """
    try:
        # 1. Fazer upload do arquivo
        arquivo_url = fazer_upload_arquivo_pipefy(caminho_arquivo)
        
        if not arquivo_url:
            log(f"   ❌ Falha ao fazer upload do arquivo")
            return False
        
        # 2. Anexar ao card
        sucesso = anexar_pdf_ao_card(card_id, arquivo_url)
        
        return sucesso
        
    except Exception as e:
        log(f"   ❌ Erro ao anexar arquivo: {e}")
        return False


def mover_card_para_fase(card_id, fase_id_destino):
    """
    Move um card para uma fase específica usando o ID da fase diretamente
    
    Args:
        card_id: ID do card a ser movido
        fase_id_destino: ID da fase de destino (usar constantes FASE_LIQUIDACAO_*)
    
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
                    current_phase {
                        id
                        name
                    }
                }
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
        
        # Verificar se o card foi retornado na resposta (indica sucesso)
        card_movido = data.get('data', {}).get('moveCardToPhase', {}).get('card')
        
        if card_movido and card_movido.get('id'):
            fase_atual = card_movido.get('current_phase', {})
            log(f"   ✅ SUCCESS! Card movido para fase: {fase_atual.get('name', 'N/A')} (ID: {fase_atual.get('id', 'N/A')})")
            return True
        else:
            log(f"   ❌ FALHA: Card não retornado na resposta")
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
    Verifica se o card já possui comprovante de pagamento anexado no campo específico
    
    Args:
        card: Dicionário com dados do card do Pipefy
    
    Retorna:
        bool: True se já possui comprovante, False caso contrário
    """
    fields = card.get('fields', [])
    
    # ID do campo específico de comprovante de pagamento
    FIELD_ID_COMPROVANTE = "anexar_comprovante_de_pagamento"
    
    for field in fields:
        field_id = field.get('field', {}).get('id', '')
        valor = field.get('value')
        
        # Verificar especificamente o campo de anexar comprovante
        if field_id == FIELD_ID_COMPROVANTE and valor:
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
    log(f"\n{'='*80}", level='debug')
    log(f"🔄 Processando card: {card['title']}", level='debug')
    log(f"   Card ID: {card['id']}", level='debug')
    
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
        log(f"❌ {card['title']}: {resultado['motivo']}", level='debug')
        return resultado
    
    comprovante = match_result['comprovante']
    payment_id = comprovante['payment_id']
    fundo_id = comprovante.get('fundo_id')
    fundo_nome = comprovante.get('fundo_nome', 'N/A')
    cliente = comprovante.get('cliente')
    
    log(f"✅ Match encontrado - Payment ID: {payment_id}", level='debug')
    log(f"   Fundo: {fundo_nome} ({fundo_id})", level='debug')
    
    # 3. Baixar PDF do comprovante usando o cliente do fundo correto
    resultado['etapa'] = 'download_pdf'
    caminho_pdf = obter_pdf_comprovante(payment_id, fundo_id=fundo_id, cliente_santander=cliente)
    
    if not caminho_pdf:
        resultado['motivo'] = 'Falha ao baixar PDF do Santander'
        log(f"❌ {card['title']}: {resultado['motivo']}", level='debug')
        return resultado
    
    log(f"✅ PDF baixado: {caminho_pdf}", level='debug')
    
    # 4. Fazer upload para o Pipefy
    resultado['etapa'] = 'upload_pipefy'
    arquivo_url = fazer_upload_arquivo_pipefy(caminho_pdf)
    
    if not arquivo_url:
        resultado['motivo'] = 'Falha ao fazer upload para Pipefy'
        log(f"❌ {card['title']}: {resultado['motivo']}", level='debug')
        return resultado
    
    log(f"✅ Arquivo enviado para Pipefy: {arquivo_url}", level='debug')
    
    # 5. Anexar PDF ao card
    resultado['etapa'] = 'anexar_card'
    anexou = anexar_pdf_ao_card(card['id'], arquivo_url)
    
    if not anexou:
        resultado['motivo'] = 'Falha ao anexar PDF ao card'
        log(f"❌ {card['title']}: {resultado['motivo']}", level='debug')
        return resultado
    
    log(f"✅ PDF anexado ao card!", level='debug')
    
    # 6. Mover card para fase "Solicitação Paga"
    resultado['etapa'] = 'mover_fase'
    log(f"🔄 Iniciando movimentação para fase 'Solicitação Paga' (ID: {FASE_LIQUIDACAO_SOLICITACAO_PAGA})...", level='debug')
    moveu = mover_card_para_fase(card['id'], FASE_LIQUIDACAO_SOLICITACAO_PAGA)
    
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
    
    # Adicionar informações do comprovante para o relatório final
    resultado['comprovante_match'] = {
        'fundo': fundo_id if fundo_id else 'N/A',
        'payment_id': payment_id,
        'data_pagamento': comprovante.get('value_date', 'N/A') if comprovante else 'N/A',
        'valor': comprovante.get('amount', dados_card.get('valor', 0)) if comprovante else dados_card.get('valor', 0)
    }
    
    log(f"✅✅✅ {card['title']}: PROCESSAMENTO COMPLETO!", level='debug')
    log(f"{'='*80}\n", level='debug')
    
    return resultado


def processar_todos_cards(data_busca=None, clientes_santander=None):
    """
    Processa todos os cards da fase "Aguardando Comprovante"
    Busca comprovantes e anexa PDFs automaticamente
    
    Args:
        data_busca: Data para buscar comprovantes (formato YYYY-MM-DD). Se None, usa hoje.
        clientes_santander: Dict com clientes SantanderComprovantes já inicializados (opcional).
                           Se fornecido, usa esses clientes em vez dos globais.
    """
    global santander_clients
    
    # Se recebeu clientes externos, usar eles
    if clientes_santander:
        log(f"📦 Usando {len(clientes_santander)} cliente(s) Santander fornecidos externamente")
        santander_clients = clientes_santander
    
    # Salvar data de busca para usar no relatório final
    global data_busca_str
    from datetime import date
    if data_busca is None:
        data_busca_str = date.today().strftime('%Y-%m-%d')
    else:
        data_busca_str = data_busca if isinstance(data_busca, str) else data_busca.strftime('%Y-%m-%d')
    
    log("\n" + "="*80)
    log("🚀 PROCESSAMENTO - PIPE LIQUIDAÇÃO")
    log("="*80)
    
    # 1. Buscar ID da fase (silencioso)
    fase_id = buscar_fase_por_nome(PIPE_LIQUIDACAO_ID, "Aguardando Comprovante")
    
    if not fase_id:
        log("❌ Erro: Fase 'Aguardando Comprovante' não encontrada")
        return None
    
    # 2. Buscar cards da fase (silencioso)
    cards = buscar_cards_da_fase(fase_id, limite=999999)
    
    if not cards:
        log("ℹ️  Nenhum card para processar")
        return []
    
    log(f"📋 Total de cards a processar: {len(cards)}\n")
    
    # 3. CACHEAR COMPROVANTES - Buscar UMA ÚNICA VEZ antes do loop
    log("="*80)
    log("📦 CACHEANDO COMPROVANTES DE TODOS OS FUNDOS")
    log("="*80)
    
    # Determinar data de busca - APENAS HOJE
    from datetime import date, timedelta
    if data_busca is None:
        # Buscar apenas do dia atual
        data_hoje = date.today()
        data_inicio = data_hoje
        data_fim = data_hoje
        data_busca_str = data_hoje.strftime('%Y-%m-%d')
        
        log(f"� DATA DE BUSCA: HOJE ({data_busca_str})")
        log(f"   ⚠️  Nenhuma data específica informada, usando data atual")
    else:
        # Se data específica foi passada, usar ela
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
        
        log(f"✅ {total_comprovantes} comprovante(s) encontrado(s)")
        
        # Log resumido por fundo (apenas em modo debug)
        if total_comprovantes > 0:
            log(f"\n   Distribuição por fundo:", level='debug')
            for fundo_id, comprovantes in cache_comprovantes.items():
                if len(comprovantes) > 0:
                    log(f"      • {fundo_id}: {len(comprovantes)}", level='debug')
        
        log("", level='debug')
        
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
    
    log("\n🔄 Processando cards...")
    
    for idx, card in enumerate(cards, 1):
        card_title = card.get('title', 'Sem título')
        log(f"[{idx}/{len(cards)}] {card_title}", level='debug')
        
        resultado = processar_card_completo(card, cache_comprovantes=cache_comprovantes)
        resultados.append(resultado)
        
        if resultado.get('pulado', False):
            cards_pulados += 1
            log(f"   ⏭️  Pulado (já tem comprovante)")
        elif resultado['sucesso']:
            cards_anexados += 1
            log(f"   ✅ Anexado")
        elif resultado['etapa'] == 'matching' and 'não encontrado' in resultado['motivo'].lower():
            cards_sem_match += 1
            log(f"   ⚠️ {resultado['motivo']}", level='debug')
        elif resultado['etapa'] == 'matching':
            cards_com_match += 1
            log(f"   ℹ️ {resultado['motivo']}", level='debug')
        else:
            log(f"   ❌ {resultado['motivo']}")
        
        # Remover linha em branco entre cards no minimal
    
    # 3. Relatório final
    log("\n" + "="*80)
    log("📊 RELATÓRIO FINAL")
    log("="*80)
    
    sucessos = [r for r in resultados if r['sucesso']]
    pulados = [r for r in resultados if r.get('pulado', False)]
    falhas = [r for r in resultados if not r['sucesso'] and not r.get('pulado', False)]
    
    log(f"\n✅ Comprovantes anexados: {cards_anexados}/{len(resultados)}")
    log(f"⏭️  Cards pulados (já têm comprovante): {cards_pulados}")
    log(f"⚠️  Cards sem match: {cards_sem_match}")
    log(f"❌ Erros: {len(falhas) - cards_sem_match}")
    log(f"📅 Data de busca: {data_busca_str}")
    
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
    
    log("="*80)
    
    return resultados


# ==================== TESTE DE MATCHING ====================

def testar_matching_apenas(data_busca=None):
    """
    Testa apenas a etapa de matching (sem download de PDF ou anexação)
    Mostra quais cards teriam match com os comprovantes do Santander
    
    Args:
        data_busca: Data para buscar comprovantes (formato YYYY-MM-DD). Se None, usa hoje.
    """
    log("\n" + "="*80)
    log("🧪 TESTE DE MATCHING - VERIFICAR QUAIS CARDS TÊM COMPROVANTES")
    log("="*80 + "\n")
    
    # 1. Buscar ID da fase "Solicitação Paga" (cards recém pagos)
    fase_id = buscar_fase_por_nome(PIPE_LIQUIDACAO_ID, "Solicitação Paga")
    
    if not fase_id:
        log("❌ Não foi possível encontrar a fase 'Solicitação Paga'. Encerrando.")
        return None
    
    # 2. Buscar cards da fase (SEM LIMITE - pegar todos)
    cards = buscar_cards_da_fase(fase_id, limite=200)  # Aumentado para pegar todos
    
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
        
        # Log resumido por fundo
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
    
    # 4. Testar matching para cada card (SEM processar o resto)
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
    log("📊 RELATÓRIO FINAL DO TESTE DE MATCHING")
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
    # Verificar argumentos de linha de comando
    if len(sys.argv) > 1:
        if sys.argv[1] == "--consultar":
            # Modo: apenas consultar cards (sem processar)
            obter_todos_cards_aguardando_comprovante()
        
        elif sys.argv[1] == "--matching":
            # Modo: mostrar dados extraídos para matching
            exibir_dados_extraidos_para_matching()
        
        elif sys.argv[1] == "--testar-matching":
            # Modo: NOVO - testar apenas o matching (sem download/anexação)
            testar_matching_apenas()
        
        elif sys.argv[1] == "--testar-santander":
            # Modo: testar integração com API Santander
            log("="*80)
            log("🧪 TESTE DE INTEGRAÇÃO COM API SANTANDER - TODOS OS FUNDOS")
            log("="*80)
            
            if santander_clients:
                log(f"✅ {len(santander_clients)} cliente(s) Santander inicializado(s)")
                log("\n🔐 Testando autenticação e busca de comprovantes...")
                
                # Testar listagem de comprovantes do dia
                from datetime import date
                hoje = date.today().isoformat()
                
                try:
                    todos_comprovantes = listar_comprovantes_todos_fundos(hoje, hoje)
                    total = sum(len(comps) for comps in todos_comprovantes.values())
                    
                    log(f"\n✅ API funcionando! {total} comprovante(s) encontrado(s) hoje em todos os fundos.")
                    log("\n🎯 Integração bem-sucedida! Pronto para processar cards.")
                except Exception as e:
                    log(f"\n❌ Erro ao testar API: {e}")
            else:
                log("❌ Nenhum cliente Santander inicializado")
                log("   Verifique se credenciais_bancos.py está configurado corretamente")
                log("   Configure client_id e client_secret para cada fundo")
    
    else:
        # Modo padrão: EXECUTAR AUTOMAÇÃO COMPLETA - Anexar comprovantes
        # Busca comprovantes APENAS DE HOJE automaticamente
        log(f"⚠️ MODO AUTOMÁTICO: Buscando comprovantes apenas de hoje")
        processar_todos_cards()  # data_busca=None usa apenas hoje
