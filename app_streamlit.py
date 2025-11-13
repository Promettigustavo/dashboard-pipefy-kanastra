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
    
    # Status dos módulos
    with st.expander("📊 Status dos Módulos", expanded=False):
        available_modules = get_available_modules()
        st.info(f"📦 {len(available_modules)} módulos disponíveis")
        st.caption("Módulos serão carregados sob demanda")
    
    # Status das bases de dados
    with st.expander("💾 Bases de Dados", expanded=True):
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

# ===== TABS PRINCIPAIS =====
tab_liquidacao, tab_cetip, tab_comprovantes = st.tabs([
    "💰 Liquidação",
    "🏦 CETIP",
    "📎 Comprovantes"
])

# ===== ABA LIQUIDAÇÃO =====
with tab_liquidacao:
    st.header("Processamento de Liquidação")
    
    # Verificar se bases existem
    bases, msgs = verificar_bases_dados(auto_download=True)
    
    if not all(bases.values()):
        st.warning("⚠️ Bases de dados não encontradas. Verifique a sidebar.")
    
    # Seletor de modo: Manual (arquivo) ou Automático (API)
    modo_processamento = st.radio(
        "Modo de processamento",
        options=["🤖 Automático (via API Pipefy)", "📁 Manual (com arquivo)"],
        horizontal=True,
        key="modo_liquidacao"
    )
    
    st.markdown("---")
    
    # ===== MODO AUTOMÁTICO (VIA API) =====
    if modo_processamento == "🤖 Automático (via API Pipefy)":
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown("### 🤖 Automação via API Pipefy")
            st.info("💡 Busca automaticamente cards do Pipefy e processa via API Santander")
            
            # Seleção do módulo
            modulo_auto = st.selectbox(
                "Selecione a automação",
                options=[
                    "Auto Liquidação",
                    "Auto Taxas",
                    "Auto Amortização",
                    "Auto Taxas ANBIMA"
                ],
                key="modulo_auto"
            )
            
            # Descrições
            descricoes_auto = {
                "Auto Liquidação": """
                **Fluxo completo:**
                1. Busca cards na fase "Aguardando Comprovantes"
                2. Consulta API Santander para cada fundo (período configurado)
                3. Faz match automático (CNPJ + Valor + Beneficiário)
                4. Anexa comprovantes aos cards
                5. Move cards para próxima fase
                """,
                "Auto Taxas": """
                **Fluxo completo:**
                1. Busca cards do pipe de taxas
                2. Processa taxas via API
                3. Anexa comprovantes quando disponíveis
                4. Atualiza status dos cards
                """,
                "Auto Amortização": """
                **Fluxo completo:**
                1. Busca cards de amortização pendentes
                2. Processa cálculos de amortização
                3. Atualiza valores nos cards
                4. Gera relatórios
                """,
                "Auto Taxas ANBIMA": """
                **Fluxo completo:**
                1. Busca taxas ANBIMA do dia
                2. Atualiza cards com taxas atualizadas
                3. Gera relatório de taxas
                """
            }
            
            with st.expander("ℹ️ Sobre esta automação", expanded=False):
                st.markdown(descricoes_auto.get(modulo_auto, ""))
        
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
            
            # Opções avançadas
            with st.expander("⚙️ Opções Avançadas"):
                anexar_comp = st.checkbox("Anexar comprovantes", value=True, key="anexar_comp_auto")
                apenas_simular = st.checkbox("Apenas simular (não executar)", value=False, key="simular_auto")
            
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
                                resultado = module.main()
                                arquivo_saida = f"auto_liquidacao_{data_str}.xlsx"
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
                    
                    # Tentar encontrar arquivos .xlsx recentes no diretório
                    try:
                        arquivos_xlsx = sorted(
                            [f for f in os.listdir('.') if f.endswith('.xlsx')],
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
        
        # ===== BOTÕES DE MOVER CARDS =====
        st.markdown("---")
        st.markdown("### 📋 Movimentação de Cards")
        
        col_move1, col_move2 = st.columns(2)
        
        with col_move1:
            if st.button(
                "📊 Mover Cards - Análise",
                type="secondary",
                key="btn_mover_analise",
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
                key="btn_mover_2a_aprovacao",
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
            
            # Seleção do módulo
            modulo_selecionado = st.selectbox(
                "Módulo para executar",
                options=[
                    "Pipe Liquidação",
                    "Taxas ARBI",
                    "Pipe Taxas",
                    "Amortização"
                ],
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
with tab_cetip:
    st.header("CETIP - Integração")
    
    st.markdown("### 🏦 Processamento CETIP")
    
    # Verificar se módulo existe
    module_integrador, error_integrador = get_module('integrador')
    if not module_integrador:
        st.warning(f"⚠️ Módulo integrador não disponível: {error_integrador}")
        st.info("💡 Certifique-se de que o arquivo `integrador.py` está no diretório do projeto")
    else:
        st.success("✅ Módulo integrador carregado")
        
        # Layout
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown("### 📁 Arquivo de Entrada")
            
            arquivo_cetip = st.file_uploader(
                "Selecione o arquivo CETIP",
                type=['xlsx', 'xls', 'csv', 'txt'],
                key="arquivo_cetip",
                help="Faça upload do arquivo CETIP para processar"
            )
            
            if arquivo_cetip:
                try:
                    # Preview baseado no tipo
                    if arquivo_cetip.name.endswith('.txt'):
                        content = arquivo_cetip.getvalue().decode('utf-8')
                        with st.expander("👁️ Preview do arquivo", expanded=False):
                            st.text_area("Conteúdo", content[:1000], height=200)
                            st.caption(f"📄 {len(content)} caracteres")
                    else:
                        df_preview = pd.read_excel(arquivo_cetip) if arquivo_cetip.name.endswith(('.xlsx', '.xls')) else pd.read_csv(arquivo_cetip)
                        
                        with st.expander("👁️ Preview do arquivo", expanded=False):
                            st.dataframe(df_preview.head(10), use_container_width=True)
                            st.caption(f"📊 {len(df_preview)} linhas × {len(df_preview.columns)} colunas")
                except Exception as e:
                    st.warning(f"Não foi possível visualizar o arquivo: {str(e)}")
        
        with col2:
            st.markdown("### ⚙️ Configurações")
            
            # Tipo de operação CETIP
            tipo_operacao = st.selectbox(
                "Tipo de operação",
                options=[
                    "Processamento de arquivo",
                    "Consulta de operações",
                    "Liquidação",
                    "Download de dados"
                ],
                key="tipo_cetip"
            )
            
            # Data de referência
            data_cetip = st.date_input(
                "Data de referência",
                value=dt.date.today(),
                key="data_cetip"
            )
            
            st.markdown("---")
            st.info(f"📋 Operação: {tipo_operacao}")
        
        st.markdown("---")
        
        # Execução
        col_exec1, col_exec2 = st.columns([1, 1])
        
        with col_exec1:
            executar_disabled = (tipo_operacao == "Processamento de arquivo" and not arquivo_cetip)
            
            if st.button(
                "▶ Executar CETIP",
                type="primary",
                disabled=executar_disabled,
                key="btn_exec_cetip",
                use_container_width=True
            ):
                with st.spinner(f"Processando {tipo_operacao}..."):
                    try:
                        data_str = data_cetip.strftime("%Y-%m-%d")
                        resultado = None
                        
                        # Executar operação CETIP
                        if tipo_operacao == "Processamento de arquivo" and arquivo_cetip:
                            # Salvar temporário
                            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(arquivo_cetip.name)[1]) as tmp:
                                tmp.write(arquivo_cetip.getvalue())
                                tmp_path = tmp.name
                            
                            st.info("🔄 Processando arquivo CETIP...")
                            resultado = module_integrador.processar_arquivo(tmp_path, data_str)
                            
                            os.unlink(tmp_path)
                            arquivo_saida_cetip = f"cetip_resultado_{data_str}.xlsx"
                        
                        # Salvar resultado
                        if resultado:
                            st.success(f"✅ {tipo_operacao} concluído!")
                            
                            st.session_state['ultimo_resultado_cetip'] = resultado
                            st.session_state['arquivo_saida_cetip'] = f"cetip_resultado_{data_str}.xlsx"
                            
                            # Exibir métricas
                            if isinstance(resultado, dict):
                                cols_metricas = st.columns(min(4, len(resultado)))
                                for idx, (key, value) in enumerate(list(resultado.items())[:4]):
                                    with cols_metricas[idx]:
                                        st.metric(key, value)
                        
                    except Exception as e:
                        st.error(f"❌ Erro ao processar CETIP: {str(e)}")
                        st.code(traceback.format_exc())
        
        with col_exec2:
            # Botão de download
            if 'arquivo_saida_cetip' in st.session_state:
                st.markdown("### 📥 Download")
                
                arquivo_path = st.session_state['arquivo_saida_cetip']
                
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
        
        # Resultado detalhado
        if 'ultimo_resultado_cetip' in st.session_state:
            with st.expander("📊 Detalhes do Resultado", expanded=False):
                st.json(st.session_state['ultimo_resultado_cetip'])

# ===== ABA COMPROVANTES =====
with tab_comprovantes:
    st.header("Anexar Comprovantes Santander")
    
    st.markdown("### 📎 Anexação Automática de Comprovantes")
    
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
