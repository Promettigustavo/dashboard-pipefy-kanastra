"""
Dashboard Streamlit - Sistema de Integração Pipefy
Versão simplificada com 3 abas: Liquidação, CETIP e Comprovantes
"""

import streamlit as st
from pathlib import Path
import datetime as dt
from datetime import datetime, timedelta
import sys
import pandas as pd
import io
import traceback
import tempfile
import os
import requests
import json

# Configuração do repositório GitHub
try:
    from config_streamlit import GITHUB_REPO, GITHUB_BRANCH
except:
    # Fallback se config não existir
    GITHUB_REPO = st.secrets.get("github", {}).get("repo", "Promettigustavo/Automa-o-Finance")
    GITHUB_BRANCH = st.secrets.get("github", {}).get("branch", "main")

GITHUB_RAW_URL = f"https://raw.githubusercontent.com/{GITHUB_REPO}/{GITHUB_BRANCH}"

# Configuração da página
st.set_page_config(
    page_title="Integração Pipefy - Kanastra",
    page_icon="https://www.kanastra.design/symbol.svg",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS customizado - Identidade Visual Kanastra
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    * {
        font-family: 'Inter', sans-serif;
    }
    
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #00B37E;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #64748b;
        margin-bottom: 2rem;
        font-weight: 400;
    }
    .stButton>button {
        width: 100%;
        background-color: #00B37E;
        color: white;
        font-weight: 600;
        border-radius: 0.5rem;
        padding: 0.75rem 1.5rem;
        border: none;
        transition: all 0.3s;
    }
    .stButton>button:hover {
        background-color: #00875F;
        transform: translateY(-2px);
        box-shadow: 0 4px 6px rgba(0,179,126,0.2);
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #f8fafc;
        border-radius: 8px 8px 0 0;
        padding: 12px 24px;
        font-weight: 500;
    }
    .stTabs [aria-selected="true"] {
        background-color: #00B37E;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

# ===== VERIFICAÇÃO DE BANCOS DE DADOS =====
def baixar_base_github(nome_arquivo):
    """Baixa base de dados do GitHub se não existir localmente"""
    try:
        url = f"{GITHUB_RAW_URL}/{nome_arquivo}"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            with open(nome_arquivo, 'wb') as f:
                f.write(response.content)
            return True, f"✅ {nome_arquivo} baixado do GitHub"
        else:
            return False, f"❌ Erro {response.status_code} ao baixar {nome_arquivo}"
    except Exception as e:
        return False, f"❌ Erro ao baixar {nome_arquivo}: {str(e)}"

def verificar_bases_dados(auto_download=True):
    """Verifica se as bases de dados existem e tenta baixar do GitHub"""
    bases = {
        'Basedadosfundos.xlsx': Path('Basedadosfundos.xlsx').exists(),
        'Basedadosfundos_Arbi.xlsx': Path('Basedadosfundos_Arbi.xlsx').exists()
    }
    
    mensagens = []
    
    # Se auto_download ativado, tentar baixar bases faltantes
    if auto_download and GITHUB_REPO != "seu-usuario/seu-repo":
        for nome, existe in bases.items():
            if not existe:
                sucesso, msg = baixar_base_github(nome)
                mensagens.append(msg)
                if sucesso:
                    bases[nome] = True
    
    return bases, mensagens

# ===== IMPORTS DOS MÓDULOS =====
@st.cache_resource
def import_module_lazy(module_name):
    """Importa um módulo sob demanda (lazy loading) com cache"""
    try:
        return __import__(module_name), None
    except Exception as e:
        return None, str(e)

def get_available_modules():
    """Retorna lista de módulos disponíveis sem importar"""
    return {
        'pipeliquidacao': 'pipeliquidacao',
        'taxasarbi': 'taxasarbi',
        'PipeTaxas': 'PipeTaxas',
        'Amortizacao': 'Amortizacao',
        'Anexarcomprovantespipe': 'Anexarcomprovantespipe',
        'Anexarcomprovantespipetaxas': 'Anexarcomprovantespipetaxas',
        'integrador': 'integrador',
        'auto_pipeliquidacao': 'auto_pipeliquidacao',
        'auto_pipetaxas': 'auto_pipetaxas',
        'auto_amortizacao': 'auto_amortizacao',
        'auto_taxasanbima': 'auto_taxasanbima',
        'movecards': 'movecards',
        'mover_2a_aprovacao': 'mover_2a_aprovacao',
    }

def get_module(module_key):
    """Obtém um módulo, importando se necessário"""
    import importlib
    available = get_available_modules()
    if module_key not in available:
        return None, f"Módulo {module_key} não reconhecido"
    
    module, error = import_module_lazy(available[module_key])
    
    # Recarregar módulo para pegar última versão (importante para movecards e mover_2a_aprovacao)
    if module and module_key in ['movecards', 'mover_2a_aprovacao']:
        try:
            module = importlib.reload(module)
        except:
            pass
    
    return module, error

# Header principal
st.markdown("""
    <div style="display: flex; align-items: center; gap: 1rem; margin-bottom: 1rem;">
        <img src="https://www.kanastra.design/symbol-green.svg" width="48" height="48" alt="Kanastra Symbol"/>
        <div>
            <div class="main-header">Sistema de Integração Pipefy</div>
        </div>
    </div>
""", unsafe_allow_html=True)
st.markdown('<div class="sub-header">Liquidação • CETIP • Comprovantes</div>', unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    # Logo Kanastra
    st.markdown("""
        <div style="text-align: center; padding: 1rem 0;">
            <img src="https://www.kanastra.design/wordmark-green.svg" width="180" alt="Kanastra"/>
        </div>
    """, unsafe_allow_html=True)
    st.markdown("---")
    
    # Seleção de aba no sidebar
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📑 Navegação")
    aba_selecionada = st.sidebar.radio(
        "Selecione a aba:",
        options=["💰 Liquidação", "🏦 CETIP", "📎 Comprovantes"],
        label_visibility="collapsed"
    )
    
    st.sidebar.markdown("---")
    
    # Status dos módulos
    with st.sidebar.expander("📊 Status dos Módulos", expanded=False):
        available_modules = get_available_modules()
        st.info(f"📦 {len(available_modules)} módulos disponíveis")
        st.caption("Módulos serão carregados sob demanda")
    
    # Status das bases de dados
    with st.sidebar.expander("💾 Bases de Dados", expanded=False):
        # Checkbox para auto-download
        auto_download = st.checkbox(
            "Auto-download do GitHub", 
            value=True,
            help="Baixa automaticamente bases faltantes do repositório GitHub"
        )
        
        bases, mensagens = verificar_bases_dados(auto_download)
        
        # Exibir status
        for nome, existe in bases.items():
            if existe:
                st.success(f"✅ {nome}")
            else:
                st.error(f"❌ {nome}")
        
        # Exibir mensagens de download
        for msg in mensagens:
            if "✅" in msg:
                st.info(msg)
            elif "❌" in msg:
                st.warning(msg)

# ===== ABA LIQUIDAÇÃO =====
if aba_selecionada == "💰 Liquidação":
    # Header com estilo
    st.markdown("""
        <div style='background: linear-gradient(90deg, #00B37E 0%, #00875F 100%); 
                    padding: 1.5rem; border-radius: 10px; margin-bottom: 2rem;'>
            <h1 style='color: white; margin: 0; font-size: 2rem;'>
                💰 Processamento de Liquidação
            </h1>
            <p style='color: rgba(255,255,255,0.9); margin: 0.5rem 0 0 0; font-size: 1rem;'>
                Automatize o processamento de liquidações financeiras
            </p>
        </div>
    """, unsafe_allow_html=True)
    
    # Verificar se bases existem
    bases, msgs = verificar_bases_dados(auto_download=True)
    
    if not all(bases.values()):
        st.warning("⚠️ Bases de dados não encontradas. Verifique a sidebar.")
    
    # ===== BOTÕES DE MOVER CARDS (TOPO) =====
    st.markdown("""
        <div style='background-color: #f8f9fa; padding: 1rem; border-radius: 8px; margin-bottom: 1.5rem; border-left: 4px solid #00B37E;'>
            <h3 style='margin: 0; color: #1a1a1a;'>🔄 Movimentação de Cards</h3>
            <p style='margin: 0.5rem 0 0 0; color: #666; font-size: 0.9rem;'>
                Mova cards entre fases do pipeline
            </p>
        </div>
    """, unsafe_allow_html=True)
    
    col_move1, col_move2 = st.columns(2)
    
    with col_move1:
        if st.button(
            "📊 Mover Cards - Análise",
            type="secondary",
            key="btn_mover_analise_topo",
            use_container_width=True,
            help="Move cards para a fase de análise"
        ):
            with st.spinner("Movendo cards para análise..."):
                try:
                    # Importar sem cache para pegar versão atualizada
                    import importlib
                    import sys
                    if 'movecards' in sys.modules:
                        del sys.modules['movecards']
                    import movecards
                    
                    st.info("🔄 Executando movimentação para análise...")
                    resultado = movecards.main()
                    
                    if resultado is not None:
                        st.success("✅ Cards movidos para análise com sucesso!")
                        if isinstance(resultado, dict):
                            for key, value in resultado.items():
                                st.metric(key, value)
                        else:
                            st.metric("Cards movidos", resultado)
                    else:
                        st.warning("⚠️ Nenhum card foi movido")
                except Exception as e:
                    st.error(f"❌ Erro ao mover cards: {str(e)}")
                    st.code(traceback.format_exc())
    
    with col_move2:
        if st.button(
            "✅ Mover Cards - 2ª Aprovação",
            type="secondary",
            key="btn_mover_2a_aprovacao_topo",
            use_container_width=True,
            help="Move cards para a 2ª aprovação"
        ):
            with st.spinner("Movendo cards para 2ª aprovação..."):
                try:
                    # Importar sem cache para pegar versão atualizada
                    import importlib
                    import sys
                    if 'mover_2a_aprovacao' in sys.modules:
                        del sys.modules['mover_2a_aprovacao']
                    import mover_2a_aprovacao
                    
                    st.info("🔄 Executando movimentação para 2ª aprovação...")
                    resultado = mover_2a_aprovacao.main()
                    
                    if resultado is not None:
                        st.success("✅ Cards movidos para 2ª aprovação com sucesso!")
                        if isinstance(resultado, dict):
                            for key, value in resultado.items():
                                st.metric(key, value)
                        else:
                            st.metric("Cards movidos", resultado)
                    else:
                        st.warning("⚠️ Nenhum card foi movido")
                except Exception as e:
                    st.error(f"❌ Erro ao mover cards: {str(e)}")
                    st.code(traceback.format_exc())
    
    st.markdown("---")
    
    # Seletor de modo: Manual (arquivo) ou Automático (API)
    st.markdown("""
        <div style='background-color: #f8f9fa; padding: 0.75rem; border-radius: 8px; margin-bottom: 1rem;'>
            <p style='margin: 0; color: #666; font-size: 0.9rem; font-weight: 600;'>
                MODO DE PROCESSAMENTO
            </p>
        </div>
    """, unsafe_allow_html=True)
    
    modo_processamento = st.radio(
        "Modo de processamento",
        options=["🤖 Automático (via API Pipefy)", "📁 Manual (com arquivo)"],
        horizontal=True,
        key="modo_liquidacao",
        label_visibility="collapsed"
    )
    
    st.markdown("---")
    
    # ===== MODO AUTOMÁTICO (VIA API) =====
    if modo_processamento == "🤖 Automático (via API Pipefy)":
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown("### 🤖 Automação via API Pipefy")
            st.info("💡 Busca automaticamente cards do Pipefy e processa via API Santander")
            
            # Seleção do módulo com radio buttons
            st.markdown("**Selecione a automação:**")
            modulo_auto = st.radio(
                "Módulo",
                options=[
                    "Auto Liquidação",
                    "Auto Taxas",
                    "Auto Amortização",
                    "Auto Taxas ANBIMA"
                ],
                label_visibility="collapsed",
                key="modulo_auto",
                horizontal=False
            )
        
        with col2:
            st.markdown("### ⚙️ Configurações")
            
            # Data de pagamento
            st.markdown("**📅 Data de Pagamento:**")
            
            data_pagamento_api = st.date_input(
                "Data de pagamento",
                value=dt.date.today(),
                key="data_pagamento_auto"
            )
            
            st.caption("💡 Data que será incluída no arquivo de processamento")
            
            st.markdown("---")
            
            # Status
            if 'status_auto' not in st.session_state:
                st.session_state.status_auto = "⏸️ Aguardando"
            
            st.metric("Status", st.session_state.status_auto)
        
        st.markdown("---")
        
        # Botão de execução
        col_exec1, col_exec2 = st.columns([1, 1])
        
        with col_exec1:
            if st.button(
                "🚀 Executar Automação",
                type="primary",
                key="btn_exec_auto",
                use_container_width=True
            ):
                with st.spinner(f"Executando {modulo_auto}..."):
                    try:
                        st.session_state.status_auto = "▶️ Executando..."
                        
                        # Formatar data
                        data_str = data_pagamento_api.strftime("%Y-%m-%d")
                        
                        resultado = None
                        arquivo_saida = None
                        
                        # Executar automação selecionada
                        if modulo_auto == "Auto Liquidação":
                            module, error = get_module('auto_pipeliquidacao')
                            if module:
                                st.info(f"🔄 Executando Auto Liquidação via API Pipefy...")
                                st.info(f"📅 Data de pagamento: {data_str}")
                                
                                # Passar data e pasta de saída para o módulo
                                data_formatada = data_pagamento_api.strftime("%d/%m/%Y")
                                pasta_trabalho = os.getcwd()
                                resultado = module.main(data_pagamento=data_formatada, pasta_saida=pasta_trabalho)
                                
                                # Procurar arquivo gerado mais recentemente
                                arquivos_gerados = [f for f in os.listdir(pasta_trabalho) if f.startswith('liquidacao_') and f.endswith('.xlsx')]
                                if arquivos_gerados:
                                    arquivo_saida = max(arquivos_gerados, key=lambda x: os.path.getmtime(os.path.join(pasta_trabalho, x)))
                                    arquivo_saida = os.path.join(pasta_trabalho, arquivo_saida)
                                else:
                                    arquivo_saida = os.path.join(pasta_trabalho, f"auto_liquidacao_{data_str}.xlsx")
                            else:
                                # Fallback: usar módulo de anexar comprovantes
                                module_fallback, error_fb = get_module('Anexarcomprovantespipe')
                                if module_fallback:
                                    st.info(f"🔄 Executando anexação de comprovantes (Liquidação)...")
                                    st.info(f"📅 Data de pagamento: {data_str}")
                                    resultado = module_fallback.main()
                                    arquivo_saida = f"comprovantes_liquidacao_{data_str}.xlsx"
                                else:
                                    st.error(f"❌ Módulo de automação não disponível: {error or error_fb}")
                        
                        elif modulo_auto == "Auto Taxas":
                            module, error = get_module('auto_pipetaxas')
                            if module:
                                st.info(f"🔄 Executando Auto Taxas via API Pipefy...")
                                st.info(f"📅 Data de pagamento: {data_str}")
                                resultado = module.main()
                                arquivo_saida = f"auto_taxas_{data_str}.xlsx"
                            else:
                                # Fallback: usar módulo de anexar comprovantes taxas
                                module_fallback, error_fb = get_module('Anexarcomprovantespipetaxas')
                                if module_fallback:
                                    st.info(f"🔄 Executando anexação de comprovantes (Taxas)...")
                                    st.info(f"📅 Data de pagamento: {data_str}")
                                    resultado = module_fallback.main()
                                    arquivo_saida = f"comprovantes_taxas_{data_str}.xlsx"
                                else:
                                    st.error(f"❌ Módulo de automação não disponível: {error or error_fb}")
                        
                        elif modulo_auto == "Auto Amortização":
                            module, error = get_module('auto_amortizacao')
                            if module:
                                st.info(f"🔄 Executando Auto Amortização via API Pipefy...")
                                st.info(f"📅 Data de referência: {data_str}")
                                resultado = module.main()
                                arquivo_saida = f"auto_amortizacao_{data_str}.xlsx"
                            else:
                                st.error(f"❌ Módulo auto_amortizacao não disponível: {error}")
                        
                        elif modulo_auto == "Auto Taxas ANBIMA":
                            module, error = get_module('auto_taxasanbima')
                            if module:
                                st.info(f"🔄 Executando Auto Taxas ANBIMA...")
                                st.info(f"📅 Data de referência: {data_str}")
                                resultado = module.main()
                                arquivo_saida = f"taxas_anbima_{data_str}.xlsx"
                            else:
                                st.error(f"❌ Módulo auto_taxasanbima não disponível: {error}")
                        
                        # Processar resultado
                        if resultado is not None:
                            st.success(f"✅ {modulo_auto} concluído!")
                            st.session_state.status_auto = "✅ Concluído"
                            
                            # Salvar no session_state
                            st.session_state['ultimo_resultado'] = resultado
                            st.session_state['arquivo_saida'] = arquivo_saida
                            
                            # Exibir métricas
                            if isinstance(resultado, dict):
                                cols_metricas = st.columns(min(4, len(resultado)))
                                for idx, (key, value) in enumerate(list(resultado.items())[:4]):
                                    with cols_metricas[idx]:
                                        st.metric(key, value)
                            else:
                                st.metric("Registros processados", resultado)
                        else:
                            st.warning("⚠️ Nenhum resultado retornado")
                            st.session_state.status_auto = "⚠️ Sem resultado"
                    
                    except Exception as e:
                        st.error(f"❌ Erro na automação: {str(e)}")
                        st.code(traceback.format_exc())
                        st.session_state.status_auto = "❌ Erro"
        
        with col_exec2:
            # Botão de download
            if 'arquivo_saida' in st.session_state and st.session_state.get('arquivo_saida'):
                st.markdown("### 📥 Download")
                
                arquivo_path = st.session_state['arquivo_saida']
                
                # Verificar se é caminho absoluto ou relativo
                if not os.path.isabs(arquivo_path):
                    # Procurar arquivo no diretório atual
                    arquivo_path = os.path.join(os.getcwd(), arquivo_path)
                
                if os.path.exists(arquivo_path):
                    with open(arquivo_path, 'rb') as f:
                        st.download_button(
                            label="📥 Baixar Resultado",
                            data=f,
                            file_name=os.path.basename(arquivo_path),
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True
                        )
                    st.caption(f"📄 {os.path.basename(arquivo_path)}")
                else:
                    st.warning(f"⚠️ Arquivo não encontrado: {os.path.basename(arquivo_path)}")
                    st.caption(f"Caminho procurado: {arquivo_path}")
                    
                    # Tentar encontrar arquivos .xlsx recentes no diretório (excluindo bases de dados)
                    try:
                        # Arquivos a ignorar (bases de dados)
                        arquivos_ignorar = [
                            'Basedadosfundos.xlsx',
                            'Basedadosfundos_Arbi.xlsx',
                            'ExtratosAutomaticos.xlsx',
                            'ModeloRazaodeInvestidores.xlsx'
                        ]
                        
                        arquivos_xlsx = sorted(
                            [f for f in os.listdir('.') 
                             if f.endswith('.xlsx') and f not in arquivos_ignorar],
                            key=lambda x: os.path.getmtime(x),
                            reverse=True
                        )
                        if arquivos_xlsx:
                            st.info("📁 Arquivos .xlsx encontrados (mais recentes primeiro):")
                            for arq in arquivos_xlsx[:5]:  # Mostrar até 5
                                if os.path.exists(arq):
                                    with open(arq, 'rb') as f:
                                        st.download_button(
                                            label=f"📥 {arq}",
                                            data=f,
                                            file_name=arq,
                                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                            key=f"download_{arq}"
                                        )
                    except Exception as e:
                        st.error(f"Erro ao listar arquivos: {e}")
            else:
                st.info("💡 Execute a automação para gerar o arquivo")
        
    
    # ===== MODO MANUAL (COM ARQUIVO) =====
    else:
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown("### 📁 Arquivo de Entrada")
            
            # Upload de arquivo
            arquivo_entrada = st.file_uploader(
                "Selecione o arquivo para processar",
                type=['xlsx', 'xls', 'csv'],
                key="arquivo_liquidacao",
                help="Faça upload do arquivo Excel ou CSV para processamento"
            )
            
            # Preview do arquivo
            if arquivo_entrada:
                try:
                    df_preview = pd.read_excel(arquivo_entrada) if arquivo_entrada.name.endswith(('.xlsx', '.xls')) else pd.read_csv(arquivo_entrada)
                    
                    with st.expander("👁️ Preview do arquivo", expanded=False):
                        st.dataframe(df_preview.head(10), use_container_width=True)
                        st.caption(f"📊 {len(df_preview)} linhas × {len(df_preview.columns)} colunas")
                except Exception as e:
                    st.warning(f"Não foi possível visualizar o arquivo: {str(e)}")
        
        with col2:
            st.markdown("### ⚙️ Configurações")
            
            # Seleção do módulo com radio buttons
            st.markdown("**Selecione o módulo:**")
            modulo_selecionado = st.radio(
                "Módulo",
                options=[
                    "Pipe Liquidação",
                    "Taxas ARBI",
                    "Pipe Taxas",
                    "Amortização"
                ],
                label_visibility="collapsed",
                key="modulo_liquidacao"
            )
            
            # Data de pagamento (sempre data atual)
            data_pagamento = dt.date.today()
            st.info(f"📅 Data de pagamento: {data_pagamento.strftime('%d/%m/%Y')}")
            
            st.markdown("---")
            
            # Info do módulo selecionado
            modulo_info = {
                "Pipe Liquidação": "🔄 Processa liquidações financeiras",
                "Taxas ARBI": "💰 Processa taxas ARBI",
                "Pipe Taxas": "📊 Processa taxas do pipe",
                "Amortização": "📈 Processa amortizações"
            }
            st.info(modulo_info.get(modulo_selecionado, ""))
        
        st.markdown("---")
        
        # Área de execução e resultado
        col_exec1, col_exec2 = st.columns([1, 1])
        
        with col_exec1:
            # Botão executar
            executar_disabled = not arquivo_entrada
            
            if st.button(
                "▶ Executar Processamento",
                type="primary",
                disabled=executar_disabled,
                key="btn_exec_liquidacao_manual",
                use_container_width=True
            ):
                with st.spinner(f"Processando {modulo_selecionado}..."):
                    try:
                        # Salvar arquivo temporário
                        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
                            tmp_file.write(arquivo_entrada.getvalue())
                            tmp_path = tmp_file.name
                        
                        data_str = data_pagamento.strftime("%Y-%m-%d")
                        resultado = None
                        arquivo_saida_path = None
                        
                        # Executar módulo selecionado
                        if modulo_selecionado == "Pipe Liquidação":
                            module, error = get_module('pipeliquidacao')
                            if module:
                                st.info("🔄 Executando Pipe Liquidação...")
                                resultado = module.processar_arquivo(
                                    tmp_path,
                                    data_str,
                                    "Basedadosfundos.xlsx"
                                )
                                arquivo_saida_path = "liquidacao_resultado.xlsx"
                            else:
                                st.error(f"❌ Módulo não disponível: {error}")
                            
                        elif modulo_selecionado == "Taxas ARBI":
                            module, error = get_module('taxasarbi')
                            if module:
                                st.info("🔄 Executando Taxas ARBI...")
                                resultado = module.processar_arquivo(
                                    tmp_path,
                                    data_str,
                                    "Basedadosfundos_Arbi.xlsx"
                                )
                                arquivo_saida_path = "taxas_arbi_resultado.xlsx"
                            else:
                                st.error(f"❌ Módulo não disponível: {error}")
                            
                        elif modulo_selecionado == "Pipe Taxas":
                            module, error = get_module('PipeTaxas')
                            if module:
                                st.info("🔄 Executando Pipe Taxas...")
                                resultado = module.processar_arquivo(
                                    tmp_path,
                                    data_str
                                )
                                arquivo_saida_path = "pipe_taxas_resultado.xlsx"
                            else:
                                st.error(f"❌ Módulo não disponível: {error}")
                            
                        elif modulo_selecionado == "Amortização":
                            module, error = get_module('Amortizacao')
                            if module:
                                st.info("🔄 Executando Amortização...")
                                arquivo_saida_path = "amortizacao_resultado.xlsx"
                                resultado = module.run_amortizacao(
                                    Path(tmp_path),
                                    data_str,
                                    Path(arquivo_saida_path)
                                )
                            else:
                                st.error(f"❌ Módulo não disponível: {error}")
                        
                        # Limpar temporário
                        os.unlink(tmp_path)
                        
                        # Mostrar resultado
                        if resultado is not None:
                            st.success(f"✅ {modulo_selecionado} concluído com sucesso!")
                            
                            # Salvar resultado no session_state
                            st.session_state['ultimo_resultado'] = resultado
                            st.session_state['arquivo_saida'] = arquivo_saida_path
                            
                            # Exibir métricas se for dict
                            if isinstance(resultado, dict):
                                cols_metricas = st.columns(len(resultado))
                                for idx, (key, value) in enumerate(resultado.items()):
                                    with cols_metricas[idx]:
                                        st.metric(key, value)
                    
                    except Exception as e:
                        st.error(f"❌ Erro ao processar: {str(e)}")
                        st.code(traceback.format_exc())
        
        with col_exec2:
            # Botão de download (só aparece se tiver resultado)
            if 'arquivo_saida' in st.session_state and st.session_state.get('arquivo_saida'):
                st.markdown("### 📥 Download")
                
                arquivo_path = st.session_state['arquivo_saida']
                
                if os.path.exists(arquivo_path):
                    with open(arquivo_path, 'rb') as f:
                        st.download_button(
                            label="📥 Baixar Resultado",
                            data=f,
                            file_name=os.path.basename(arquivo_path),
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True
                        )
                    
                    st.caption(f"📄 {os.path.basename(arquivo_path)}")
                else:
                    st.warning("Arquivo de saída não encontrado")
            else:
                st.info("💡 Execute o processamento para gerar o arquivo de saída")
    
    # Resultado detalhado (compartilhado entre modos)
    if 'ultimo_resultado' in st.session_state:
        with st.expander("📊 Detalhes do Resultado", expanded=False):
            st.json(st.session_state['ultimo_resultado'])

# ===== ABA CETIP =====
elif aba_selecionada == "🏦 CETIP":
    # Header com estilo
    st.markdown("""
        <div style='background: linear-gradient(90deg, #0066CC 0%, #0052A3 100%); 
                    padding: 1.5rem; border-radius: 10px; margin-bottom: 2rem;'>
            <h1 style='color: white; margin: 0; font-size: 2rem;'>
                🏦 CETIP - Integração
            </h1>
            <p style='color: rgba(255,255,255,0.9); margin: 0.5rem 0 0 0; font-size: 1rem;'>
                Geração de arquivos para sistema CETIP - Selecione os processos desejados
            </p>
        </div>
    """, unsafe_allow_html=True)
    
    st.info("💡 Selecione um ou mais processos CETIP e configure os arquivos de entrada. Os arquivos serão gerados na pasta de saída escolhida ou ao lado dos arquivos de entrada.")
    
    # Layout em 2 colunas: Processos + Entradas
    col_processos, col_entradas = st.columns([1, 2])
    
    with col_processos:
        st.markdown("""
            <div style='background-color: #f8f9fa; padding: 1rem; border-radius: 8px; border-left: 4px solid #0066CC;'>
                <h4 style='margin: 0 0 0.75rem 0; color: #0066CC;'>📋 Processos</h4>
            </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Checkboxes para cada processo
        executar_nc = st.checkbox("📄 Emissão NC", key="cetip_exec_nc", value=True)
        executar_dep = st.checkbox("💰 Emissão Depósito", key="cetip_exec_dep", value=False)
        executar_cv = st.checkbox("📊 Operação de Venda", key="cetip_exec_cv", value=False)
        executar_cci = st.checkbox("📝 Emissão CCI", key="cetip_exec_cci", value=False)
        executar_v2c = st.checkbox("🔄 Conversor V2C", key="cetip_exec_v2c", value=False)
    
    with col_entradas:
        st.markdown("""
            <div style='background-color: #f8f9fa; padding: 1rem; border-radius: 8px; border-left: 4px solid #0066CC;'>
                <h4 style='margin: 0 0 0.75rem 0; color: #0066CC;'>📁 Arquivos de Entrada</h4>
            </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Upload para NC
        arquivo_nc = st.file_uploader(
            "Entrada — Emissão NC (planilha, 2ª aba):",
            type=['xlsx', 'xls', 'xlsm', 'csv'],
            key="cetip_arquivo_nc",
            disabled=not executar_nc,
            help="Planilha Excel para Emissão de NC (usa a 2ª aba)"
        )
        
        # Upload para Depósito
        arquivo_dep = st.file_uploader(
            "Entrada — Emissão Depósito (planilha, 2ª aba):",
            type=['xlsx', 'xls', 'xlsm', 'csv'],
            key="cetip_arquivo_dep",
            disabled=not executar_dep,
            help="Planilha Excel para Emissão Depósito (usa a 2ª aba)"
        )
        
        # Upload para Compra/Venda
        arquivo_cv = st.file_uploader(
            "Entrada — Operação de Venda (planilha, 2ª aba):",
            type=['xlsx', 'xls', 'xlsm', 'csv'],
            key="cetip_arquivo_cv",
            disabled=not executar_cv,
            help="Planilha Excel para Operação de Venda (usa a 2ª aba)"
        )
        
        # Upload para CCI
        arquivo_cci = st.file_uploader(
            "Entrada — Emissão CCI (planilha, aba principal):",
            type=['xlsx', 'xls', 'xlsm', 'csv'],
            key="cetip_arquivo_cci",
            disabled=not executar_cci,
            help="Planilha Excel para Emissão CCI (usa a aba principal/índice 0)"
        )
        
        # Upload para V2C
        arquivo_v2c = st.file_uploader(
            "Entrada — V2C (arquivo venda .txt):",
            type=['txt'],
            key="cetip_arquivo_v2c",
            disabled=not executar_v2c,
            help="Arquivo de venda em formato .txt para conversão V2C (GOORO)"
        )
    
    st.markdown("---")
    
    # Pasta de saída e opções
    st.markdown("### ⚙️ Configurações")
    
    col_config1, col_config2 = st.columns(2)
    
    # Pasta de saída
    with col_config1:
        pasta_saida_cetip = st.text_input(
            "📂 Pasta de saída (opcional)",
            placeholder="Deixe vazio para salvar ao lado das entradas",
            key="cetip_pasta_saida"
        )
    
    # Opções do Depósito
    if executar_dep:
        st.markdown("**💰 Papel do Participante (Depósito):**")
        col_dep1, col_dep2, col_dep3 = st.columns(3)
        
        with col_dep1:
            papel_emissor_sel = st.checkbox("02 - Emissor", key="cetip_papel_02", value=True)
        with col_dep2:
            papel_dist_sel = st.checkbox("03 - Distribuidor", key="cetip_papel_03", value=False)
        with col_dep3:
            st.markdown("<br>", unsafe_allow_html=True)
        
        # Determinar valor do papel
        if papel_emissor_sel and papel_dist_sel:
            papel_deposito = "ambos"
        elif papel_emissor_sel:
            papel_deposito = "02"
        elif papel_dist_sel:
            papel_deposito = "03"
        else:
            papel_deposito = "02"  # Default
        
        st.caption("ℹ️ Se ambos forem selecionados, dois arquivos serão gerados (emissor e distribuidor).")
    
    # Opções do CCI
    if executar_cci:
        st.markdown("**📝 Opções - Emissão CCI:**")
        col_cci1, col_cci2 = st.columns(2)
        
        with col_cci1:
            operacao_cci = st.radio(
                "Operação",
                options=["Venda", "Compra"],
                key="cetip_operacao_cci",
                horizontal=True
            )
        
        with col_cci2:
            modalidade_cci = st.radio(
                "Modalidade",
                options=["Sem Modalidade", "Bruta"],
                key="cetip_modalidade_cci",
                horizontal=True
            )
    
    st.markdown("---")
    
    # Botões de ação
    col_btn1, col_btn2, col_btn3 = st.columns([2, 1, 1])
    
    with col_btn2:
        if st.button("🧹 Limpar", key="cetip_limpar", use_container_width=True):
            # Limpar session_state
            for key in list(st.session_state.keys()):
                if key.startswith('cetip_'):
                    del st.session_state[key]
            st.rerun()
    
    with col_btn3:
        # Verificar se pelo menos um processo está marcado
        algum_processo = executar_nc or executar_dep or executar_cv or executar_cci or executar_v2c
        
        # Verificar se arquivos necessários foram fornecidos
        arquivos_ok = True
        if executar_nc and not arquivo_nc:
            arquivos_ok = False
        if executar_dep and not arquivo_dep:
            arquivos_ok = False
        if executar_cv and not arquivo_cv:
            arquivos_ok = False
        if executar_cci and not arquivo_cci:
            arquivos_ok = False
        if executar_v2c and not arquivo_v2c:
            arquivos_ok = False
        
        executar_disabled = not algum_processo or not arquivos_ok
        
        if st.button(
            "🚀 Executar",
            type="primary",
            disabled=executar_disabled,
            key="cetip_executar",
            use_container_width=True
        ):
            # Inicializar log
            log_cetip = []
            contadores = {"NC": 0, "Depósito": 0, "Venda": 0, "CCI": 0}
            
            with st.spinner("Processando módulos CETIP..."):
                try:
                    log_cetip.append("=" * 60)
                    log_cetip.append("🏦 INICIANDO PROCESSAMENTO CETIP")
                    log_cetip.append("=" * 60)
                    log_cetip.append("")
                    
                    processos_selecionados = []
                    if executar_nc:
                        processos_selecionados.append("Emissão NC")
                    if executar_dep:
                        processos_selecionados.append("Emissão Depósito")
                    if executar_cv:
                        processos_selecionados.append("Operação de Venda")
                    if executar_cci:
                        processos_selecionados.append("Emissão CCI")
                    if executar_v2c:
                        processos_selecionados.append("Conversor V2C")
                    
                    log_cetip.append(f"📋 Processos selecionados: {', '.join(processos_selecionados)}")
                    log_cetip.append("")
                    
                    # Processar NC
                    if executar_nc and arquivo_nc:
                        log_cetip.append("─" * 60)
                        log_cetip.append("📄 [NC] Iniciando Emissão de NC...")
                        log_cetip.append("─" * 60)
                        
                        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(arquivo_nc.name)[1]) as tmp:
                            tmp.write(arquivo_nc.getvalue())
                            tmp_path_nc = tmp.name
                        
                        log_cetip.append(f"📂 Arquivo de entrada: {arquivo_nc.name}")
                        log_cetip.append(f"📂 Arquivo temporário: {tmp_path_nc}")
                        log_cetip.append("⚙️ Configuração: Sheet index = 1 (2ª aba)")
                        log_cetip.append(f"📁 Pasta de saída: {pasta_saida_cetip if pasta_saida_cetip else 'ao lado da entrada'}")
                        log_cetip.append("")
                        log_cetip.append("⚠️ Integração com módulo EmissaoNC_v2.py em desenvolvimento")
                        log_cetip.append("✅ [NC] Simulação concluída")
                        
                        contadores["NC"] = 1  # Simulado
                        
                        os.unlink(tmp_path_nc)
                        log_cetip.append("")
                    
                    # Processar Depósito
                    if executar_dep and arquivo_dep:
                        log_cetip.append("─" * 60)
                        log_cetip.append("💰 [DEP] Iniciando Emissão Depósito...")
                        log_cetip.append("─" * 60)
                        
                        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(arquivo_dep.name)[1]) as tmp:
                            tmp.write(arquivo_dep.getvalue())
                            tmp_path_dep = tmp.name
                        
                        log_cetip.append(f"📂 Arquivo de entrada: {arquivo_dep.name}")
                        log_cetip.append(f"👤 Papel do participante: {papel_deposito}")
                        log_cetip.append(f"📁 Pasta de saída: {pasta_saida_cetip if pasta_saida_cetip else 'ao lado da entrada'}")
                        log_cetip.append("")
                        
                        if papel_deposito == "ambos":
                            log_cetip.append("⚙️ Gerando arquivo para EMISSOR (02)...")
                            log_cetip.append(f"   Saída: DEP_{os.path.splitext(arquivo_dep.name)[0]}_EMISSOR.txt")
                            log_cetip.append("⚙️ Gerando arquivo para DISTRIBUIDOR (03)...")
                            log_cetip.append(f"   Saída: DEP_{os.path.splitext(arquivo_dep.name)[0]}_DISTRIBUIDOR.txt")
                            contadores["Depósito"] = 2  # Simulado
                        else:
                            papel_nome = "EMISSOR" if papel_deposito == "02" else "DISTRIBUIDOR"
                            log_cetip.append(f"⚙️ Gerando arquivo para {papel_nome} ({papel_deposito})...")
                            log_cetip.append(f"   Saída: DEP_{os.path.splitext(arquivo_dep.name)[0]}_{papel_nome}.txt")
                            contadores["Depósito"] = 1  # Simulado
                        
                        log_cetip.append("")
                        log_cetip.append("⚠️ Integração com módulo emissao_deposito.py em desenvolvimento")
                        log_cetip.append("✅ [DEP] Simulação concluída")
                        
                        os.unlink(tmp_path_dep)
                        log_cetip.append("")
                    
                    # Processar Compra/Venda
                    if executar_cv and arquivo_cv:
                        log_cetip.append("─" * 60)
                        log_cetip.append("📊 [CV] Iniciando Operação de Venda...")
                        log_cetip.append("─" * 60)
                        
                        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(arquivo_cv.name)[1]) as tmp:
                            tmp.write(arquivo_cv.getvalue())
                            tmp_path_cv = tmp.name
                        
                        log_cetip.append(f"📂 Arquivo de entrada: {arquivo_cv.name}")
                        log_cetip.append("⚙️ Configuração: Sheet index = 1 (2ª aba)")
                        log_cetip.append(f"📁 Pasta de saída: {pasta_saida_cetip if pasta_saida_cetip else 'ao lado da entrada'}")
                        log_cetip.append(f"   Saída: Venda_{os.path.splitext(arquivo_cv.name)[0]}.txt")
                        log_cetip.append("")
                        log_cetip.append("⚠️ Integração com módulo operacao_compra_venda.py em desenvolvimento")
                        log_cetip.append("✅ [CV] Simulação concluída")
                        
                        contadores["Venda"] = 1  # Simulado
                        
                        os.unlink(tmp_path_cv)
                        log_cetip.append("")
                    
                    # Processar CCI
                    if executar_cci and arquivo_cci:
                        log_cetip.append("─" * 60)
                        log_cetip.append("📝 [CCI] Iniciando Emissão CCI...")
                        log_cetip.append("─" * 60)
                        
                        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(arquivo_cci.name)[1]) as tmp:
                            tmp.write(arquivo_cci.getvalue())
                            tmp_path_cci = tmp.name
                        
                        log_cetip.append(f"📂 Arquivo de entrada: {arquivo_cci.name}")
                        log_cetip.append(f"⚙️ Operação: {operacao_cci}")
                        log_cetip.append(f"⚙️ Modalidade: {modalidade_cci}")
                        log_cetip.append("⚙️ Configuração: Sheet index = 0 (aba principal)")
                        log_cetip.append("⚙️ Participante: LIMINETRUSTDTVM")
                        log_cetip.append(f"📁 Pasta de saída: {pasta_saida_cetip if pasta_saida_cetip else 'ao lado da entrada'}")
                        log_cetip.append(f"   Saída: CCI_{os.path.splitext(arquivo_cci.name)[0]}.txt")
                        log_cetip.append("")
                        log_cetip.append("⚠️ Integração com módulo CCI.py em desenvolvimento")
                        log_cetip.append("✅ [CCI] Simulação concluída")
                        
                        contadores["CCI"] = 1  # Simulado
                        
                        os.unlink(tmp_path_cci)
                        log_cetip.append("")
                    
                    # Processar V2C
                    if executar_v2c and arquivo_v2c:
                        log_cetip.append("─" * 60)
                        log_cetip.append("🔄 [V2C] Iniciando Conversor V2C (GOORO)...")
                        log_cetip.append("─" * 60)
                        
                        with tempfile.NamedTemporaryFile(delete=False, suffix='.txt') as tmp:
                            tmp.write(arquivo_v2c.getvalue())
                            tmp_path_v2c = tmp.name
                        
                        log_cetip.append(f"📂 Arquivo de entrada: {arquivo_v2c.name}")
                        log_cetip.append("⚙️ Conversão: Venda → Compra")
                        log_cetip.append(f"📁 Pasta de saída: {pasta_saida_cetip if pasta_saida_cetip else 'ao lado da entrada'}")
                        
                        # Nome do arquivo de saída
                        if arquivo_v2c.name.endswith("_venda.txt"):
                            nome_saida = arquivo_v2c.name[:-10] + "_compra.txt"
                        else:
                            nome_saida = os.path.splitext(arquivo_v2c.name)[0] + "_compra.txt"
                        
                        log_cetip.append(f"   Saída: {nome_saida}")
                        log_cetip.append("")
                        log_cetip.append("⚠️ Integração com módulo conversor_v2.py em desenvolvimento")
                        log_cetip.append("✅ [V2C] Simulação concluída")
                        log_cetip.append("ℹ️ Conversor V2C não participa da contagem de emissões")
                        
                        os.unlink(tmp_path_v2c)
                        log_cetip.append("")
                    
                    # Resumo final
                    total_emissoes = contadores["NC"] + contadores["Depósito"] + contadores["Venda"] + contadores["CCI"]
                    
                    log_cetip.append("")
                    log_cetip.append("=" * 60)
                    log_cetip.append("📊 RESUMO FINAL DAS EMISSÕES")
                    log_cetip.append("=" * 60)
                    log_cetip.append(f"📄 NC: {contadores['NC']}")
                    log_cetip.append(f"💰 Depósito: {contadores['Depósito']}")
                    log_cetip.append(f"📊 Venda: {contadores['Venda']}")
                    log_cetip.append(f"📝 CCI: {contadores['CCI']}")
                    log_cetip.append(f"🔢 Total (NC + Depósito + Venda + CCI): {total_emissoes}")
                    log_cetip.append("=" * 60)
                    
                    # Salvar em session_state
                    st.session_state['cetip_log'] = "\n".join(log_cetip)
                    st.session_state['cetip_contadores'] = contadores
                    
                    st.success("✅ Processamento CETIP concluído!")
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"❌ Erro durante processamento: {str(e)}")
                    st.code(traceback.format_exc())
    
    # Exibir mensagens de validação
    if not algum_processo:
        st.warning("⚠️ Selecione pelo menos um processo para executar")
    elif not arquivos_ok:
        st.warning("⚠️ Forneça os arquivos de entrada para os processos selecionados")
    
    # Relatório/Log
    st.markdown("---")
    st.markdown("### 📋 Relatório de Execução")
    
    if 'cetip_log' in st.session_state:
        # Métricas
        if 'cetip_contadores' in st.session_state:
            st.markdown("#### 📊 Resumo de Emissões")
            col_m1, col_m2, col_m3, col_m4, col_m5 = st.columns(5)
            
            contadores = st.session_state['cetip_contadores']
            
            with col_m1:
                st.metric("📄 NC", contadores.get("NC", 0))
            with col_m2:
                st.metric("💰 Depósito", contadores.get("Depósito", 0))
            with col_m3:
                st.metric("📊 Venda", contadores.get("Venda", 0))
            with col_m4:
                st.metric("📝 CCI", contadores.get("CCI", 0))
            with col_m5:
                total = sum([contadores.get("NC", 0), contadores.get("Depósito", 0), 
                            contadores.get("Venda", 0), contadores.get("CCI", 0)])
                st.metric("🔢 Total", total)
        
        # Log detalhado
        st.markdown("#### 📝 Log Detalhado")
        st.text_area(
            "Log de processamento",
            value=st.session_state['cetip_log'],
            height=400,
            label_visibility="collapsed"
        )
    else:
        st.info("💡 Execute o processamento para ver o relatório")
    
    # Informações adicionais
    with st.expander("ℹ️ Informações sobre os módulos CETIP"):
        st.markdown("""
        **Módulos disponíveis:**
        
        - **📄 Emissão de NC**: Gera arquivo de Nota de Custódia a partir de planilha Excel (2ª aba)
          - Entrada: Planilha `.xlsx`, `.xls`, `.xlsm` ou `.csv`
          - Saída: Arquivo `.txt` com registros NC (formato: `NC   1...`)
          - Módulo: `EmissaoNC_v2.py`
        
        - **💰 Emissão Depósito**: Gera arquivo de Depósito para Emissor (02) e/ou Distribuidor (03)
          - Entrada: Planilha `.xlsx`, `.xls`, `.xlsm` ou `.csv` (2ª aba)
          - Saída: 1 ou 2 arquivos `.txt` com registros MDA (formato: `MDA  1...`)
          - Papel: Emissor (02), Distribuidor (03) ou Ambos
          - Se "Ambos", gera: `DEP_<nome>_EMISSOR.txt` e `DEP_<nome>_DISTRIBUIDOR.txt`
          - Módulo: `emissao_deposito.py`
        
        - **📊 Operação de Compra/Venda**: Processa operações de venda
          - Entrada: Planilha `.xlsx`, `.xls`, `.xlsm` ou `.csv` (2ª aba)
          - Saída: Arquivo `.txt` com registros MDA (formato: `MDA  1...`)
          - Módulo: `operacao_compra_venda.py`, `Compra_Venda.py` ou `compra_venda.py`
        
        - **📝 Emissão CCI**: Gera arquivo CCI com operação (VENDA/COMPRA) e modalidade
          - Entrada: Planilha `.xlsx`, `.xls`, `.xlsm` ou `.csv` (aba principal/índice 0)
          - Saída: Arquivo `.txt` com registros CCI (formato: `CCI  1...`)
          - Operação: Venda ou Compra
          - Modalidade: Sem Modalidade ou Bruta
          - Participante: LIMINETRUSTDTVM
          - Módulo: `CCI.py`
        
        - **🔄 Conversor V2C (GOORO)**: Converte arquivo de venda para formato de compra
          - Entrada: Arquivo `.txt` de venda
          - Saída: Arquivo `.txt` de compra
          - Se entrada termina com `_venda.txt`, saída será `_compra.txt`
          - Nota: Não participa da contagem de emissões
          - Módulo: `conversor_v2.py`
        
        **Localização dos módulos:** `C:\\Users\\GustavoPrometti\\OneDrive - Kanastra\\Documentos\\Kanastra\\Projeto CETIP`
        
        **Pasta de saída:** Se não especificada, os arquivos são salvos ao lado dos arquivos de entrada.
        
        **Estrutura do integrador tkinter replicada:**
        - Checkboxes para seleção de processos
        - Uploads independentes para cada arquivo
        - Opções de papel para Depósito (02/03/ambos)
        - Opções de operação e modalidade para CCI
        - Log detalhado com contadores de emissões
        - Resumo final igual ao launcher original
        """)


# ===== ABA COMPROVANTES =====
elif aba_selecionada == "📎 Comprovantes":
    # Header com estilo
    st.markdown("""
        <div style='background: linear-gradient(90deg, #DC2626 0%, #B91C1C 100%); 
                    padding: 1.5rem; border-radius: 10px; margin-bottom: 2rem;'>
            <h1 style='color: white; margin: 0; font-size: 2rem;'>
                📎 Anexar Comprovantes Santander
            </h1>
            <p style='color: rgba(255,255,255,0.9); margin: 0.5rem 0 0 0; font-size: 1rem;'>
                Anexação automática de comprovantes via API Santander
            </p>
        </div>
    """, unsafe_allow_html=True)
    
    # Layout
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("### 📁 Arquivo de Entrada")
        
        # Upload de arquivo
        arquivo_comprovantes = st.file_uploader(
            "Selecione o arquivo de cards (opcional)",
            type=['xlsx', 'xls', 'csv', 'json'],
            key="arquivo_comprovantes",
            help="Deixe em branco para buscar automaticamente cards pendentes do Pipefy"
        )
        
        # Preview
        if arquivo_comprovantes:
            try:
                if arquivo_comprovantes.name.endswith('.json'):
                    content = json.loads(arquivo_comprovantes.getvalue().decode('utf-8'))
                    with st.expander("👁️ Preview do arquivo", expanded=False):
                        st.json(content if isinstance(content, dict) else content[:5])
                        st.caption(f"📄 {len(content) if isinstance(content, list) else 'N/A'} registros")
                else:
                    df_preview = pd.read_excel(arquivo_comprovantes) if arquivo_comprovantes.name.endswith(('.xlsx', '.xls')) else pd.read_csv(arquivo_comprovantes)
                    
                    with st.expander("👁️ Preview do arquivo", expanded=False):
                        st.dataframe(df_preview.head(10), use_container_width=True)
                        st.caption(f"📊 {len(df_preview)} linhas × {len(df_preview.columns)} colunas")
            except Exception as e:
                st.warning(f"Não foi possível visualizar o arquivo: {str(e)}")
    
    with col2:
        st.markdown("### ⚙️ Configurações")
        
        # Tipo de pipe
        tipo_pipe = st.selectbox(
            "Tipo de pipe",
            options=[
                "Liquidação",
                "Taxas"
            ],
            key="tipo_pipe_comp"
        )
        
        # Período de busca
        periodo_dias = st.number_input(
            "Período (dias)",
            min_value=1,
            max_value=30,
            value=7,
            help="Buscar comprovantes dos últimos N dias"
        )
        
        # Modo de anexação
        modo_anexacao = st.radio(
            "Modo",
            options=["Automático", "Manual"],
            help="Automático: busca cards pendentes do Pipefy. Manual: usa arquivo enviado"
        )
        
        st.markdown("---")
        st.info(f"📋 Pipe: {tipo_pipe}")
    
    st.markdown("---")
    
    # Execução
    col_exec1, col_exec2 = st.columns([1, 1])
    
    with col_exec1:
        # Botão executar
        executar_disabled = modo_anexacao == "Manual" and not arquivo_comprovantes
        
        if st.button(
            "▶ Anexar Comprovantes",
            type="primary",
            disabled=executar_disabled,
            key="btn_exec_comprovantes",
            use_container_width=True
        ):
            with st.spinner("Anexando comprovantes..."):
                try:
                    data_fim = dt.date.today()
                    data_inicio = data_fim - timedelta(days=periodo_dias)
                    
                    data_inicio_str = data_inicio.strftime("%Y-%m-%d")
                    data_fim_str = data_fim.strftime("%Y-%m-%d")
                    
                    resultado = None
                    arquivo_saida = None
                    
                    # Determinar módulo baseado no tipo
                    if tipo_pipe == "Liquidação":
                        module, error = get_module('Anexarcomprovantespipe')
                        if not module:
                            st.error(f"❌ Módulo Anexarcomprovantespipe não disponível: {error}")
                        else:
                            st.info("🔄 Anexando comprovantes no pipe de liquidação...")
                            
                            # Modo automático (padrão)
                            resultado = module.main()
                            arquivo_saida = f"comprovantes_liquidacao_{data_fim_str}.xlsx"
                    
                    elif tipo_pipe == "Taxas":
                        module, error = get_module('Anexarcomprovantespipetaxas')
                        if not module:
                            st.error(f"❌ Módulo Anexarcomprovantespipetaxas não disponível: {error}")
                        else:
                            st.info("🔄 Anexando comprovantes no pipe de taxas...")
                            
                            # Modo automático (padrão)
                            resultado = module.main()
                            arquivo_saida = f"comprovantes_taxas_{data_fim_str}.xlsx"
                    
                    # Mostrar resultado
                    if resultado or resultado == 0:
                        st.success(f"✅ Comprovantes anexados com sucesso!")
                        
                        # Salvar no session_state
                        st.session_state['ultimo_resultado_comp'] = resultado
                        st.session_state['arquivo_saida_comp'] = arquivo_saida
                        
                        # Exibir métricas
                        if isinstance(resultado, dict):
                            cols_metricas = st.columns(min(4, len(resultado)))
                            for idx, (key, value) in enumerate(list(resultado.items())[:4]):
                                with cols_metricas[idx]:
                                    st.metric(key, value)
                        else:
                            st.metric("Processados", resultado)
                
                except Exception as e:
                    st.error(f"❌ Erro ao anexar comprovantes: {str(e)}")
                    st.code(traceback.format_exc())
    
    with col_exec2:
        # Botão de download
        if 'arquivo_saida_comp' in st.session_state:
            st.markdown("### 📥 Download")
            
            arquivo_path = st.session_state['arquivo_saida_comp']
            
            if os.path.exists(arquivo_path):
                with open(arquivo_path, 'rb') as f:
                    st.download_button(
                        label="📥 Baixar Relatório",
                        data=f,
                        file_name=os.path.basename(arquivo_path),
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
                st.caption(f"📄 {os.path.basename(arquivo_path)}")
            else:
                st.warning("Arquivo de saída não encontrado")
        else:
            st.info("💡 Execute a anexação para gerar o relatório")
    
    # Resultado detalhado
    if 'ultimo_resultado_comp' in st.session_state:
        with st.expander("📊 Detalhes do Resultado", expanded=False):
            st.json(st.session_state['ultimo_resultado_comp'])

# ===== RODAPÉ =====
st.markdown("---")

col_footer1, col_footer2, col_footer3 = st.columns(3)

with col_footer1:
    st.caption("📊 Dashboard desenvolvido com Streamlit")

with col_footer2:
    st.caption("🔐 Kanastra - Sistema Interno")

with col_footer3:
    st.caption(f"📅 {datetime.now().strftime('%d/%m/%Y %H:%M')}")
