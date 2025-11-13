"""
Auto Amortização - Versão Refatorada
Extrai arquivos Excel do Pipefy e processa com Amortizacao.py
"""

from pathlib import Path
import requests
from typing import List, Dict, Optional
import time
from datetime import datetime
import tkinter as tk
from tkinter import ttk

# Importar módulo de processamento
try:
    import Amortizacao as modulo_amortizacao
except ImportError:
    modulo_amortizacao = None
    print("⚠️ Módulo Amortizacao não encontrado")


# ============================================================================
# CONFIGURAÇÕES
# ============================================================================

PIPEFY_API_URL = "https://api.pipefy.com/graphql"
PIPEFY_TOKEN = "eyJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJQaXBlZnkiLCJpYXQiOjE3NjExMzkxNDcsImp0aSI6ImM1NzhhYzM5LTUwZmUtNGI0NC1iMzYzLWE5ZjNhMzBmNjUwYyIsInN1YiI6MzA2ODY4NTY3LCJ1c2VyIjp7ImlkIjozMDY4Njg1NjcsImVtYWlsIjoiZ3VzdGF2by5wcm9tZXR0aUBrYW5hc3RyYS5jb20uYnIifSwidXNlcl90eXBlIjoiYXV0aGVudGljYXRlZCJ9.hjcPATGMMX1xBcRMHQ7gfjkvqB7Nq9w0Ou9tD33fIlmLoicU928x5sd_T_nmkL04DV37GtxFtF5mCFaFSa4fVQ"

# IDs do Pipe de Liquidação
PIPE_ID = "304119818"  # Pipe: Amortização de Empréstimos
PHASE_ID_LIQUIDACAO = "318444653"  # Fase: Liquidação

# Campo de anexos (ajustar conforme necessário)
FIELD_ID_ANEXOS = "planilha_de_liquida_o"  # Nome do campo de anexos


# ============================================================================
# FUNÇÕES DE API PIPEFY
# ============================================================================

def _graphql_request(query: str, variables: dict = None) -> dict:
    """
    Executa requisição GraphQL no Pipefy
    """
    headers = {
        "Authorization": f"Bearer {PIPEFY_TOKEN}",
        "Content-Type": "application/json",
    }
    
    payload = {"query": query}
    if variables:
        payload["variables"] = variables
    
    response = requests.post(PIPEFY_API_URL, json=payload, headers=headers, timeout=30)
    response.raise_for_status()
    
    data = response.json()
    if "errors" in data:
        raise Exception(f"GraphQL Error: {data['errors']}")
    
    return data


def _normalizar_texto(texto: str) -> str:
    """Normaliza texto para comparação"""
    if not texto:
        return ''
    import unicodedata
    texto = unicodedata.normalize('NFKD', texto)
    return ''.join(ch for ch in texto if ch.isalnum()).lower()


def buscar_fase_liquidacao() -> str:
    """
    Busca dinamicamente o ID da fase Liquidação
    """
    query = """
    query($pipeId: ID!) {
        pipe(id: $pipeId) {
            phases {
                id
                name
            }
        }
    }
    """
    
    variables = {"pipeId": PIPE_ID}
    result = _graphql_request(query, variables)
    
    phases = result.get("data", {}).get("pipe", {}).get("phases", [])
    
    for phase in phases:
        nome_normalizado = _normalizar_texto(phase['name'])
        if nome_normalizado == _normalizar_texto('Liquidação'):
            return phase['id']
    
    raise Exception("Fase 'Liquidação' não encontrada no pipe")


def buscar_cards_liquidacao(progress_callback=None) -> List[Dict]:
    """
    Busca todos os cards da fase Liquidação com paginação
    """
    # Primeiro, buscar o ID da fase Liquidação
    if progress_callback:
        progress_callback("🔍 Buscando ID da fase Liquidação...")
    
    phase_id = buscar_fase_liquidacao()
    
    if progress_callback:
        progress_callback(f"✅ Fase Liquidação encontrada: ID {phase_id}")
    
    query = """
    query($phaseId: ID!, $after: String) {
        phase(id: $phaseId) {
            cards(first: 50, after: $after) {
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
                            array_value
                        }
                    }
                }
            }
        }
    }
    """
    
    all_cards = []
    has_next = True
    after = None
    page = 0
    
    while has_next:
        page += 1
        if progress_callback:
            progress_callback(f"📥 Buscando cards da fase Liquidação (página {page})...")
        
        variables = {
            "phaseId": phase_id,
            "after": after
        }
        
        result = _graphql_request(query, variables)
        
        cards_data = result.get("data", {}).get("phase", {}).get("cards", {})
        edges = cards_data.get("edges", [])
        page_info = cards_data.get("pageInfo", {})
        
        for edge in edges:
            card = edge.get("node", {})
            all_cards.append(card)
        
        has_next = page_info.get("hasNextPage", False)
        after = page_info.get("endCursor")
        
        time.sleep(0.5)  # Rate limiting
    
    if progress_callback:
        progress_callback(f"✅ {len(all_cards)} cards encontrados na fase Liquidação")
    
    return all_cards


def buscar_anexos_card(card_id: str) -> List[Dict]:
    """
    Busca anexos de um card específico
    """
    query = """
    query($cardId: ID!) {
        card(id: $cardId) {
            id
            title
            attachments {
                url
            }
        }
    }
    """
    
    try:
        variables = {"cardId": card_id}
        result = _graphql_request(query, variables)
        
        card_data = result.get("data", {}).get("card")
        if card_data:
            return card_data.get("attachments", [])
        
        return []
    
    except Exception as e:
        print(f"   ⚠️ Erro ao buscar anexos do card {card_id}: {e}")
        return []


def selecionar_cards_popup(cards: List[Dict]) -> List[Dict]:
    """
    Mostra popup com checkboxes para usuário selecionar quais cards processar
    
    Args:
        cards: Lista de dicts com id e title dos cards
        
    Returns:
        Lista de cards selecionados pelo usuário
    """
    cards_selecionados = []
    
    def confirmar_selecao():
        nonlocal cards_selecionados
        cards_selecionados = [card for card, var in zip(cards, checkboxes_vars) if var.get()]
        janela.destroy()
    
    def cancelar():
        nonlocal cards_selecionados
        cards_selecionados = []
        janela.destroy()
    
    def selecionar_todos():
        for var in checkboxes_vars:
            var.set(True)
    
    def desselecionar_todos():
        for var in checkboxes_vars:
            var.set(False)
    
    # Criar janela
    janela = tk.Toplevel()
    janela.title("Selecionar Cards para Amortização")
    janela.geometry("700x500")
    janela.transient()
    janela.grab_set()
    
    # Frame principal
    main_frame = ttk.Frame(janela, padding="10")
    main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
    
    # Label de instrução
    label = ttk.Label(main_frame, text=f"📋 Selecione os cards para processar ({len(cards)} encontrados):", 
                      font=('Segoe UI', 10, 'bold'))
    label.grid(row=0, column=0, columnspan=2, pady=(0, 10), sticky=tk.W)
    
    # Frame com scroll para checkboxes
    canvas = tk.Canvas(main_frame, height=300)
    scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
    scrollable_frame = ttk.Frame(canvas)
    
    scrollable_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )
    
    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)
    
    canvas.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
    scrollbar.grid(row=1, column=1, sticky=(tk.N, tk.S))
    
    # Criar checkboxes
    checkboxes_vars = []
    for idx, card in enumerate(cards):
        var = tk.BooleanVar(value=True)  # Todos selecionados por padrão
        checkboxes_vars.append(var)
        
        card_title = card.get('title', f"Card {card.get('id', '')}")
        card_id = card.get('id', '')
        
        cb = ttk.Checkbutton(
            scrollable_frame,
            text=f"[{idx+1}] {card_title} (ID: {card_id})",
            variable=var
        )
        cb.grid(row=idx, column=0, sticky=tk.W, pady=2, padx=5)
    
    # Frame para botões de seleção rápida
    select_frame = ttk.Frame(main_frame)
    select_frame.grid(row=2, column=0, columnspan=2, pady=10)
    
    btn_todos = ttk.Button(select_frame, text="✓ Selecionar Todos", command=selecionar_todos)
    btn_todos.grid(row=0, column=0, padx=5)
    
    btn_nenhum = ttk.Button(select_frame, text="✗ Desselecionar Todos", command=desselecionar_todos)
    btn_nenhum.grid(row=0, column=1, padx=5)
    
    # Frame para botões de ação
    action_frame = ttk.Frame(main_frame)
    action_frame.grid(row=3, column=0, columnspan=2, pady=10)
    
    btn_confirmar = ttk.Button(action_frame, text="✓ Confirmar", command=confirmar_selecao, width=15)
    btn_confirmar.grid(row=0, column=0, padx=5)
    
    btn_cancelar = ttk.Button(action_frame, text="✗ Cancelar", command=cancelar, width=15)
    btn_cancelar.grid(row=0, column=1, padx=5)
    
    # Configurar grid weights
    janela.columnconfigure(0, weight=1)
    janela.rowconfigure(0, weight=1)
    main_frame.columnconfigure(0, weight=1)
    main_frame.rowconfigure(1, weight=1)
    
    # Centralizar janela
    janela.update_idletasks()
    x = (janela.winfo_screenwidth() // 2) - (janela.winfo_width() // 2)
    y = (janela.winfo_screenheight() // 2) - (janela.winfo_height() // 2)
    janela.geometry(f"+{x}+{y}")
    
    # Aguardar fechamento
    janela.wait_window()
    
    return cards_selecionados


def extrair_anexos_excel(cards: List[Dict], output_dir: Path, progress_callback=None) -> List[Dict]:
    """
    Extrai anexos Excel dos cards e salva no diretório de saída
    
    Returns:
        Lista de dicts com: card_id, card_title, arquivo_path
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    arquivos_extraidos = []
    
    for idx, card in enumerate(cards, 1):
        card_id = card.get("id", "")
        card_title = card.get("title", f"Card_{card_id}")
        
        if progress_callback:
            progress_callback(f"📄 Processando card {idx}/{len(cards)}: {card_title}")
        
        # Buscar anexos do card
        anexos = buscar_anexos_card(card_id)
        
        if not anexos:
            if progress_callback:
                progress_callback(f"   ⚠️ Nenhum anexo encontrado")
            continue
        
        # Filtrar apenas arquivos Excel
        anexos_excel = []
        for anexo in anexos:
            url = anexo.get('url', '')
            if url:
                # Extrair nome do arquivo da URL
                url_parts = url.split('/')
                nome_arquivo = url_parts[-1] if url_parts else "arquivo_sem_nome"
                nome_arquivo = nome_arquivo.split('?')[0]  # Remove parâmetros
                
                nome_lower = nome_arquivo.lower()
                
                # Verificar se é Excel
                if any(ext in nome_lower for ext in ['.xlsx', '.xls', '.xlsm']):
                    anexos_excel.append({
                        'nome': nome_arquivo,
                        'url': url
                    })
                    if progress_callback:
                        progress_callback(f"   ✅ Excel encontrado: {nome_arquivo}")
        
        if not anexos_excel:
            if progress_callback:
                progress_callback(f"   ⚠️ Nenhum arquivo Excel nos anexos")
            continue
        
        # Download dos anexos Excel
        for anexo_idx, anexo_info in enumerate(anexos_excel, 1):
            try:
                anexo_url = anexo_info['url']
                nome_arquivo = anexo_info['nome']
                
                # Determinar extensão
                ext = '.xlsx'
                if nome_arquivo.lower().endswith('.xls'):
                    ext = '.xls'
                elif nome_arquivo.lower().endswith('.xlsm'):
                    ext = '.xlsm'
                
                # Nome do arquivo
                safe_title = "".join(c for c in card_title if c.isalnum() or c in (' ', '-', '_')).strip()
                safe_title = safe_title[:50]  # Limitar tamanho
                
                if len(anexos_excel) > 1:
                    filename = f"{safe_title}_{anexo_idx}{ext}"
                else:
                    filename = f"{safe_title}{ext}"
                
                arquivo_path = output_dir / filename
                
                # Download
                response = requests.get(anexo_url, timeout=60)
                response.raise_for_status()
                
                with open(arquivo_path, 'wb') as f:
                    f.write(response.content)
                
                arquivos_extraidos.append({
                    'card_id': card_id,
                    'card_title': card_title,
                    'arquivo_path': arquivo_path
                })
                
                if progress_callback:
                    progress_callback(f"   ✅ Baixado: {filename}")
            
            except Exception as e:
                if progress_callback:
                    progress_callback(f"   ⚠️ Erro ao baixar anexo: {e}")
                continue
        
        time.sleep(0.3)  # Rate limiting
    
    return arquivos_extraidos


# ============================================================================
# FUNÇÃO PRINCIPAL - PASSO 1
# ============================================================================

def passo1_extrair_arquivos(pasta_saida: str = None, progress_callback=None) -> Dict:
    """
    Passo 1: Extrai arquivos Excel do Pipe de Liquidação
    
    Args:
        pasta_saida: Caminho da pasta de saída (opcional, padrão: Downloads)
        progress_callback: Função para feedback de progresso
    
    Returns:
        dict com: arquivos (lista), total, pasta_saida, sucesso
    """
    try:
        if progress_callback:
            progress_callback("🚀 Iniciando extração de arquivos do Pipe de Liquidação...")
            progress_callback("🔍 DEBUG: Configurando pasta de saída...")
        
        # Definir pasta de saída
        if pasta_saida:
            output_dir = Path(pasta_saida)
        else:
            # Usar pasta Downloads do usuário
            downloads_dir = Path.home() / "Downloads"
            output_dir = downloads_dir / "amortizacao_arquivos"
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        if progress_callback:
            progress_callback(f"🔍 DEBUG: Pasta criada: {output_dir}")
            progress_callback("🔍 DEBUG: Chamando buscar_cards_liquidacao()...")
        
        # Buscar cards
        cards = buscar_cards_liquidacao(progress_callback)
        
        if progress_callback:
            progress_callback(f"🔍 DEBUG: {len(cards)} cards retornados")
        
        if not cards:
            return {
                'sucesso': False,
                'arquivos': [],
                'total': 0,
                'pasta_saida': str(output_dir),
                'mensagem': 'Nenhum card encontrado na fase Liquidação'
            }
        
        # NOVO: Mostrar popup para seleção de cards
        if progress_callback:
            progress_callback(f"\n� Mostrando popup de seleção de cards...")
        
        cards_selecionados = selecionar_cards_popup(cards)
        
        if not cards_selecionados:
            if progress_callback:
                progress_callback("⚠️ Nenhum card selecionado. Operação cancelada.")
            return {
                'sucesso': False,
                'arquivos': [],
                'total': 0,
                'pasta_saida': str(output_dir),
                'mensagem': 'Operação cancelada pelo usuário'
            }
        
        if progress_callback:
            progress_callback(f"✅ {len(cards_selecionados)} cards selecionados de {len(cards)}")
            progress_callback("�🔍 DEBUG: Chamando extrair_anexos_excel()...")
        
        # Extrair anexos Excel apenas dos cards selecionados
        arquivos = extrair_anexos_excel(cards_selecionados, output_dir, progress_callback)
        
        if progress_callback:
            progress_callback(f"\n✅ Extração concluída!")
            progress_callback(f"   📁 Pasta: {output_dir}")
            progress_callback(f"   📊 Total de arquivos: {len(arquivos)}")
        
        return {
            'sucesso': True,
            'arquivos': arquivos,
            'total': len(arquivos),
            'pasta_saida': str(output_dir),
            'mensagem': f'{len(arquivos)} arquivos Excel extraídos com sucesso'
        }
    
    except Exception as e:
        if progress_callback:
            progress_callback(f"❌ ERRO em passo1_extrair_arquivos: {e}")
            import traceback
            progress_callback(f"🔍 DEBUG: {traceback.format_exc()}")
        
        return {
            'sucesso': False,
            'arquivos': [],
            'total': 0,
            'pasta_saida': str(output_dir) if 'output_dir' in locals() else 'N/A',
            'mensagem': f'Erro na extração: {str(e)}'
        }


# ============================================================================
# PASSO 2 - PROCESSAR ARQUIVOS COM AMORTIZACAO_NEW
# ============================================================================

def passo2_processar_arquivos(
    arquivos_extraidos: List[Dict],
    data_pagamento: str,
    pasta_saida: str = None,
    progress_callback=None
) -> Dict:
    """
    Passo 2: Processa arquivos Excel extraídos usando Amortizacao.py
    
    Args:
        arquivos_extraidos: Lista de dicts com 'arquivo_path', 'card_id', 'card_title'
        data_pagamento: Data de pagamento no formato dd/mm/yyyy
        pasta_saida: Pasta de saída para arquivos processados (opcional)
        progress_callback: Função para feedback de progresso
    
    Returns:
        dict com: processados (lista), total, sucessos, falhas, pasta_saida
    """
    if not modulo_amortizacao:
        raise ImportError("Módulo Amortizacao não está disponível")
    
    if progress_callback:
        progress_callback(f"\n🔄 Iniciando processamento de {len(arquivos_extraidos)} arquivos...")
    
    # Definir pasta de saída para arquivos processados
    if pasta_saida:
        output_dir = Path(pasta_saida)
    else:
        downloads_dir = Path.home() / "Downloads"
        output_dir = downloads_dir / "amortizacao_processados"
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    processados = []
    sucessos = 0
    falhas = 0
    
    for idx, arquivo_info in enumerate(arquivos_extraidos, 1):
        arquivo_path = arquivo_info['arquivo_path']
        card_title = arquivo_info['card_title']
        card_id = arquivo_info['card_id']
        
        if progress_callback:
            progress_callback(f"\n📊 [{idx}/{len(arquivos_extraidos)}] Processando: {arquivo_path.name}")
        
        try:
            # Nome base para arquivos de saída
            safe_title = "".join(c for c in card_title if c.isalnum() or c in (' ', '-', '_')).strip()
            safe_title = safe_title[:50]
            saida_base = output_dir / f"amortizacao_{safe_title}"
            
            # Processar com Amortizacao
            resultado = modulo_amortizacao.processar_amortizacao(
                input_file=arquivo_path,
                data_pagamento=data_pagamento,
                saida_path=saida_base
            )
            
            processados.append({
                'card_id': card_id,
                'card_title': card_title,
                'arquivo_entrada': str(arquivo_path),
                'csv_saida': resultado['csv'],
                'xlsx_saida': resultado['xlsx'],
                'total_registros': resultado['total_registros'],
                'sucesso': True,
                'mensagem': resultado['mensagem']
            })
            
            sucessos += 1
            
            if progress_callback:
                progress_callback(f"   ✅ Processado: {resultado['total_registros']} registros")
        
        except Exception as e:
            processados.append({
                'card_id': card_id,
                'card_title': card_title,
                'arquivo_entrada': str(arquivo_path),
                'sucesso': False,
                'mensagem': f'Erro: {str(e)}'
            })
            
            falhas += 1
            
            if progress_callback:
                progress_callback(f"   ❌ Erro: {e}")
    
    if progress_callback:
        progress_callback(f"\n{'='*60}")
        progress_callback(f"✅ Processamento concluído!")
        progress_callback(f"   Sucessos: {sucessos}")
        progress_callback(f"   Falhas: {falhas}")
        progress_callback(f"   Pasta de saída: {output_dir}")
        progress_callback(f"{'='*60}")
    
    return {
        'processados': processados,
        'total': len(arquivos_extraidos),
        'sucessos': sucessos,
        'falhas': falhas,
        'pasta_saida': str(output_dir),
        'mensagem': f'{sucessos} arquivos processados, {falhas} falhas'
    }


# ============================================================================
# FUNÇÃO PRINCIPAL COMPLETA
# ============================================================================

def executar_amortizacao_completa(
    data_pagamento: str,
    pasta_extracao: str = None,
    pasta_processamento: str = None,
    progress_callback=None
) -> Dict:
    """
    Executa processo completo de amortização:
    1. Extrai arquivos Excel do Pipe de Liquidação
    2. Processa cada arquivo com Amortizacao.py
    
    Args:
        data_pagamento: Data de pagamento no formato dd/mm/yyyy
        pasta_extracao: Pasta para salvar arquivos extraídos (opcional)
        pasta_processamento: Pasta para salvar arquivos processados (opcional)
        progress_callback: Função para feedback de progresso
    
    Returns:
        dict com resultado completo
    """
    try:
        if progress_callback:
            progress_callback("🔍 DEBUG: Iniciando passo 1 - extrair arquivos...")
        
        # Passo 1: Extrair arquivos
        resultado_extracao = passo1_extrair_arquivos(
            pasta_saida=pasta_extracao,
            progress_callback=progress_callback
        )
        
        if progress_callback:
            progress_callback(f"🔍 DEBUG: Resultado extração - sucesso={resultado_extracao['sucesso']}")
        
        if not resultado_extracao['sucesso']:
            if progress_callback:
                progress_callback(f"🔍 DEBUG: Extração falhou: {resultado_extracao.get('mensagem')}")
            return resultado_extracao
        
        if not resultado_extracao['arquivos']:
            if progress_callback:
                progress_callback("🔍 DEBUG: Nenhum arquivo extraído")
            return {
                'sucesso': False,
                'mensagem': 'Nenhum arquivo Excel encontrado para processar'
            }
        
        if progress_callback:
            progress_callback(f"🔍 DEBUG: {len(resultado_extracao['arquivos'])} arquivos extraídos")
            progress_callback("🔍 DEBUG: Iniciando passo 2 - processar arquivos...")
        
        # Passo 2: Processar arquivos
        resultado_processamento = passo2_processar_arquivos(
            arquivos_extraidos=resultado_extracao['arquivos'],
            data_pagamento=data_pagamento,
            pasta_saida=pasta_processamento,
            progress_callback=progress_callback
        )
        
        if progress_callback:
            progress_callback(f"🔍 DEBUG: Processamento concluído - sucessos={resultado_processamento['sucessos']}, falhas={resultado_processamento['falhas']}")
        
        return {
            'sucesso': True,
            'extracao': resultado_extracao,
            'processamento': resultado_processamento,
            'mensagem': f"Processo completo: {resultado_processamento['sucessos']} arquivos processados com sucesso"
        }
    
    except Exception as e:
        if progress_callback:
            progress_callback(f"\n❌ ERRO em executar_amortizacao_completa: {e}")
            import traceback
            progress_callback(f"🔍 DEBUG: Traceback:\n{traceback.format_exc()}")
        
        return {
            'sucesso': False,
            'mensagem': f'Erro: {str(e)}'
        }


# ============================================================================
# FUNÇÃO MAIN PARA O LAUNCHER
# ============================================================================

def main(data_pagamento=None, pasta_saida=None):
    """
    Função principal para integração com o launcher
    Mesma assinatura do código antigo: main(data_pagamento, pasta_saida)
    
    Args:
        data_pagamento: Data de pagamento no formato dd/mm/yyyy (opcional)
        pasta_saida: Pasta de saída para arquivos processados (opcional)
    
    Returns:
        bool: True se sucesso, False se falha
    """
    print("🤖 AUTOMAÇÃO DE AMORTIZAÇÃO")
    print("=" * 50)
    print(f"📅 Início: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    if not data_pagamento:
        data_pagamento = datetime.now().strftime("%d/%m/%Y")
        print("📅 Data: Usando data atual")
    else:
        print(f"📅 Data informada: {data_pagamento}")
    
    if pasta_saida:
        print(f"📁 Pasta de saída: {pasta_saida}")
    else:
        pasta_saida = str(Path.home() / "Downloads")
        print(f"📁 Pasta de saída: {pasta_saida} (padrão)")
    
    print()
    
    def print_progress(msg):
        print(msg)
    
    try:
        print("🔍 DEBUG: Iniciando executar_amortizacao_completa...")
        print(f"   - data_pagamento: {data_pagamento}")
        print(f"   - pasta_processamento: {pasta_saida}")
        
        resultado = executar_amortizacao_completa(
            data_pagamento=data_pagamento,
            pasta_processamento=pasta_saida,
            progress_callback=print_progress
        )
        
        print(f"🔍 DEBUG: Resultado recebido: {resultado}")
        
        sucesso = resultado.get('sucesso', False)
        
        if sucesso:
            print(f"\n🎉 PROCESSAMENTO CONCLUÍDO")
            print("=" * 40)
            if resultado.get('processamento'):
                proc = resultado['processamento']
                print(f"✅ Sucessos: {proc['sucessos']}")
                print(f"❌ Falhas: {proc['falhas']}")
        else:
            print(f"\n❌ ERRO: {resultado.get('mensagem', 'Erro desconhecido')}")
        
        print(f"🔍 DEBUG: Retornando sucesso={sucesso}")
        return sucesso
    
    except Exception as e:
        print(f"❌ Erro na execução: {e}")
        import traceback
        print("🔍 DEBUG: Traceback completo:")
        traceback.print_exc()
        return False


# ============================================================================
# EXECUÇÃO DIRETA PARA TESTES
# ============================================================================

if __name__ == "__main__":
    def print_progress(msg):
        print(msg)
    
    # Solicitar data de pagamento
    data_pag = input("Digite a data de pagamento (dd/mm/aaaa): ").strip()
    if not data_pag:
        data_pag = "05/11/2025"  # Data padrão para teste
        print(f"Usando data padrão: {data_pag}")
    
    try:
        resultado = executar_amortizacao_completa(
            data_pagamento=data_pag,
            progress_callback=print_progress
        )
        
        print(f"\n{'='*60}")
        print(f"� RESULTADO FINAL:")
        print(f"   Sucesso: {resultado['sucesso']}")
        print(f"   Mensagem: {resultado['mensagem']}")
        
        if resultado.get('processamento'):
            proc = resultado['processamento']
            print(f"\n   📈 Processamento:")
            print(f"      Total: {proc['total']}")
            print(f"      Sucessos: {proc['sucessos']}")
            print(f"      Falhas: {proc['falhas']}")
            print(f"      Pasta: {proc['pasta_saida']}")
        
        print(f"{'='*60}")
    
    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
