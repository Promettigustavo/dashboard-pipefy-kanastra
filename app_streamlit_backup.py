"""
Dashboard Streamlit - Sistema de Integração Pipefy
Versão web do Integracao.py com abas: Pipefy, CETIP e Comprovantes
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

# Configuração do repositório GitHub
try:
    from config_streamlit import GITHUB_REPO, GITHUB_BRANCH
except:
    # Fallback se config não existir
    GITHUB_REPO = st.secrets.get("github", {}).get("repo", "seu-usuario/seu-repo")
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
    .success-box {
        padding: 1rem;
        background-color: #d1fae5;
        border-left: 4px solid #00B37E;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
    .error-box {
        padding: 1rem;
        background-color: #fee2e2;
        border-left: 4px solid #ef4444;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
    .info-box {
        padding: 1rem;
        background-color: #E1F5FE;
        border-left: 4px solid #00B37E;
        border-radius: 0.5rem;
        margin: 1rem 0;
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
        font-family: 'Inter', sans-serif;
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
    h1, h2, h3 {
        font-family: 'Inter', sans-serif;
        color: #1a1a1a;
    }
    .sidebar .sidebar-content {
        background-color: #f8fafc;
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
def import_modules():
    """Importa todos os módulos necessários"""
    modules = {}
    errors = []
    
    # Módulos Core
    try:
        import pipeliquidacao as liq_core
        modules['pipeliquidacao'] = liq_core
    except Exception as e:
        errors.append(f"pipeliquidacao: {str(e)}")
    
    try:
        import taxasarbi as taxas_arbi_core
        modules['taxasarbi'] = taxas_arbi_core
    except Exception as e:
        errors.append(f"taxasarbi: {str(e)}")
    
    try:
        import PipeTaxas as pipe_taxas_core
        modules['PipeTaxas'] = pipe_taxas_core
    except Exception as e:
        errors.append(f"PipeTaxas: {str(e)}")
    
    try:
        import Amortizacao as amort_core
        modules['Amortizacao'] = amort_core
    except Exception as e:
        errors.append(f"Amortizacao: {str(e)}")
    
    # Automações
    try:
        import auto_pipeliquidacao as auto_pipe
        modules['auto_pipeliquidacao'] = auto_pipe
    except Exception as e:
        errors.append(f"auto_pipeliquidacao: {str(e)}")
    
    try:
        import auto_pipetaxas as auto_taxas
        modules['auto_pipetaxas'] = auto_taxas
    except Exception as e:
        errors.append(f"auto_pipetaxas: {str(e)}")
    
    try:
        import auto_taxasanbima as auto_taxas_anbima
        modules['auto_taxasanbima'] = auto_taxas_anbima
    except Exception as e:
        errors.append(f"auto_taxasanbima: {str(e)}")
    
    try:
        import auto_amortizacao as auto_amort
        modules['auto_amortizacao'] = auto_amort
    except Exception as e:
        errors.append(f"auto_amortizacao: {str(e)}")
    
    # Movimentação de cards
    try:
        import movecards as move_cards
        modules['movecards'] = move_cards
    except Exception as e:
        errors.append(f"movecards: {str(e)}")
    
    try:
        import mover_2a_aprovacao as mover_2a
        modules['mover_2a_aprovacao'] = mover_2a
    except Exception as e:
        errors.append(f"mover_2a_aprovacao: {str(e)}")
    
    # Comprovantes
    try:
        import Anexarcomprovantespipe as comprovantes_pipe
        modules['Anexarcomprovantespipe'] = comprovantes_pipe
    except Exception as e:
        errors.append(f"Anexarcomprovantespipe: {str(e)}")
    
    try:
        import Anexarcomprovantespipetaxas as comprovantes_pipe_taxas
        modules['Anexarcomprovantespipetaxas'] = comprovantes_pipe_taxas
    except Exception as e:
        errors.append(f"Anexarcomprovantespipetaxas: {str(e)}")
    
    try:
        import buscar_comprovantes_santander
        modules['buscar_comprovantes_santander'] = buscar_comprovantes_santander
    except Exception as e:
        errors.append(f"buscar_comprovantes_santander: {str(e)}")
    
    # CETIP - agora no mesmo repo
    try:
        import integrador as cetip_integrador
        modules['integrador'] = cetip_integrador
    except Exception as e:
        errors.append(f"integrador (CETIP): {str(e)}")
    
    return modules, errors

# Header principal
st.markdown("""
    <div style="display: flex; align-items: center; gap: 1rem; margin-bottom: 1rem;">
        <img src="https://www.kanastra.design/symbol-green.svg" width="48" height="48" alt="Kanastra Symbol"/>
        <div>
            <div class="main-header">Sistema de Integração Pipefy</div>
        </div>
    </div>
""", unsafe_allow_html=True)
st.markdown('<div class="sub-header">Liquidação • Taxas ARBI • Pipe Taxas • Amortização • CETIP • Comprovantes</div>', unsafe_allow_html=True)

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
        modules, errors = import_modules()
        
        if errors:
            st.error(f"⚠️ {len(errors)} módulo(s) com erro")
            for error in errors:
                st.caption(f"• {error}")
        else:
            st.success(f"✅ Todos os {len(modules)} módulos carregados")
    
    # Status das bases de dados
    with st.expander("💾 Bases de Dados", expanded=False):
        # Checkbox para auto-download
        auto_download = st.checkbox(
            "Auto-download do GitHub", 
            value=True,
            help="Baixa automaticamente bases faltantes do repositório GitHub"
        )
        
        bases, mensagens = verificar_bases_dados(auto_download)
        
        # Exibir mensagens de download
        for msg in mensagens:
            if "✅" in msg:
                st.success(msg)
            else:
                st.warning(msg)
        
        # Status das bases
        for nome, existe in bases.items():
            if existe:
                st.success(f"✅ {nome}")
            else:
                st.warning(f"⚠️ {nome} não encontrado")
        
        # Botão manual de download
        if st.button("🔄 Baixar Bases do GitHub", key="btn_download_bases"):
            with st.spinner("Baixando do GitHub..."):
                for nome in bases.keys():
                    sucesso, msg = baixar_base_github(nome)
                    if "✅" in msg:
                        st.success(msg)
                    else:
                        st.error(msg)
                st.rerun()
        
        st.markdown("---")
        
        # Upload manual de bases
        st.markdown("**Upload Manual:**")
        base_liq_upload = st.file_uploader("Basedadosfundos.xlsx", type=['xlsx'], key="upload_base_liq")
        base_arbi_upload = st.file_uploader("Basedadosfundos_Arbi.xlsx", type=['xlsx'], key="upload_base_arbi")
        
        if base_liq_upload:
            with open("Basedadosfundos.xlsx", "wb") as f:
                f.write(base_liq_upload.getbuffer())
            st.success("✅ Base Liquidação salva")
            st.rerun()
        
        if base_arbi_upload:
            with open("Basedadosfundos_Arbi.xlsx", "wb") as f:
                f.write(base_arbi_upload.getbuffer())
            st.success("✅ Base ARBI salva")
            st.rerun()
    
    st.markdown("---")
    st.caption("v1.0 - Novembro 2025")

# Tabs principais
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
        st.warning("⚠️ Bases de dados não encontradas. Verifique a sidebar para fazer upload ou download do GitHub.")
        for msg in msgs:
            if "❌" in msg:
                st.error(msg)
    
    # Layout em colunas
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
        
        # Data de pagamento
        data_pagamento = st.date_input(
            "Data de pagamento",
            value=dt.date.today(),
            key="data_pag_liquidacao"
        )
        
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
        executar_disabled = not arquivo_entrada or not all(bases.values())
        
        if st.button(
            "▶ Executar Processamento",
            type="primary",
            disabled=executar_disabled,
            key="btn_exec_liquidacao",
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
                    arquivo_saida = None
                    
                    # Executar módulo selecionado
                    if modulo_selecionado == "Pipe Liquidação" and 'pipeliquidacao' in modules:
                        st.info("🔄 Executando Pipe Liquidação...")
                        resultado = modules['pipeliquidacao'].processar_arquivo(
                            tmp_path,
                            data_str,
                            "Basedadosfundos.xlsx"
                        )
                        arquivo_saida = "liquidacao_resultado.xlsx"
                        
                    elif modulo_selecionado == "Taxas ARBI" and 'taxasarbi' in modules:
                        st.info("🔄 Executando Taxas ARBI...")
                        resultado = modules['taxasarbi'].processar_arquivo(
                            tmp_path,
                            data_str,
                            "Basedadosfundos_Arbi.xlsx"
                        )
                        arquivo_saida = "taxas_arbi_resultado.xlsx"
                        
                    elif modulo_selecionado == "Pipe Taxas" and 'PipeTaxas' in modules:
                        st.info("🔄 Executando Pipe Taxas...")
                        resultado = modules['PipeTaxas'].processar_arquivo(
                            tmp_path,
                            data_str
                        )
                        arquivo_saida = "pipe_taxas_resultado.xlsx"
                        
                    elif modulo_selecionado == "Amortização" and 'Amortizacao' in modules:
                        st.info("🔄 Executando Amortização...")
                        resultado = modules['Amortizacao'].run_amortizacao(
                            Path(tmp_path),
                            data_str,
                            Path("amortizacao_resultado.xlsx")
                        )
                        arquivo_saida = "amortizacao_resultado.xlsx"
                    
                    # Limpar temporário
                    os.unlink(tmp_path)
                    
                    # Mostrar resultado
                    if resultado:
                        st.success(f"✅ {modulo_selecionado} concluído com sucesso!")
                        
                        # Salvar resultado no session_state
                        st.session_state['ultimo_resultado'] = resultado
                        st.session_state['arquivo_saida'] = arquivo_saida
                        
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
    
    # Resultado detalhado
    if 'ultimo_resultado' in st.session_state:
        with st.expander("📊 Detalhes do Resultado", expanded=False):
            st.json(st.session_state['ultimo_resultado'])
    
    # Ajuda
    with st.expander("❓ Ajuda", expanded=False):
        st.markdown("""
        ### Como usar:
        
        1. **Upload**: Selecione o arquivo Excel/CSV para processar
        2. **Módulo**: Escolha qual módulo executar
        3. **Data**: Defina a data de pagamento
        4. **Executar**: Clique no botão para processar
        5. **Download**: Baixe o arquivo de resultado
        
        ### Módulos disponíveis:
        
        - **Pipe Liquidação**: Processa liquidações financeiras usando Basedadosfundos.xlsx
        - **Taxas ARBI**: Processa taxas ARBI usando Basedadosfundos_Arbi.xlsx
        - **Pipe Taxas**: Processa taxas do pipe (não precisa de base)
        - **Amortização**: Processa amortizações (não precisa de base)
        
        ℹ️ As bases de dados são carregadas automaticamente do GitHub ou podem ser enviadas pela sidebar.
        """)

# ===== ABA CETIP =====
with tab_cetip:
    st.header("CETIP - Integração")
    
    st.markdown("### 🏦 Processamento CETIP")
    
    # Verificar se módulo existe
    if 'integrador' not in modules:
        st.warning("⚠️ Módulo integrador não disponível")
        st.info("� Certifique-se de que o arquivo `integrador.py` está no diretório do projeto")
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
                    "Consulta de operações",
                    "Liquidação",
                    "Processamento de arquivo",
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
            executar_disabled = not arquivo_cetip if tipo_operacao == "Processamento de arquivo" else False
            
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
                            resultado = modules['integrador'].processar_arquivo(tmp_path, data_str)
                            
                            os.unlink(tmp_path)
                        
                        elif tipo_operacao == "Consulta de operações":
                            st.info("🔄 Consultando operações CETIP...")
                            resultado = modules['integrador'].consultar_operacoes(data_str)
                        
                        elif tipo_operacao == "Liquidação":
                            st.info("🔄 Processando liquidações CETIP...")
                            resultado = modules['integrador'].processar_liquidacoes(data_str)
                        
                        elif tipo_operacao == "Download de dados":
                            st.info("🔄 Baixando dados CETIP...")
                            resultado = modules['integrador'].download_dados(data_str)
                        
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
                st.markdown("### � Download")
                
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
        
        # Ajuda
        with st.expander("❓ Ajuda", expanded=False):
            st.markdown("""
            ### Como usar:
            
            1. **Upload**: Selecione o arquivo CETIP (se necessário)
            2. **Tipo**: Escolha o tipo de operação
            3. **Data**: Defina a data de referência
            4. **Executar**: Clique no botão para processar
            5. **Download**: Baixe o arquivo de resultado
            
            ### Tipos de operação:
            
            - **Consulta de operações**: Consulta operações CETIP do dia
            - **Liquidação**: Processa liquidações CETIP
            - **Processamento de arquivo**: Processa arquivo CETIP enviado
            - **Download de dados**: Baixa dados do sistema CETIP
            """)

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
                    import json
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
                        if 'Anexarcomprovantespipe' not in modules:
                            st.error("❌ Módulo Anexarcomprovantespipe não disponível")
                        else:
                            st.info("🔄 Anexando comprovantes no pipe de liquidação...")
                            
                            if modo_anexacao == "Manual" and arquivo_comprovantes:
                                # Salvar temporário
                                with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(arquivo_comprovantes.name)[1]) as tmp:
                                    tmp.write(arquivo_comprovantes.getvalue())
                                    tmp_path = tmp.name
                                
                                resultado = modules['Anexarcomprovantespipe'].anexar_com_arquivo(
                                    tmp_path,
                                    data_inicio_str,
                                    data_fim_str
                                )
                                
                                os.unlink(tmp_path)
                            else:
                                # Modo automático
                                resultado = modules['Anexarcomprovantespipe'].anexar_automatico(
                                    data_inicio_str,
                                    data_fim_str
                                )
                            
                            arquivo_saida = f"comprovantes_liquidacao_{data_fim_str}.xlsx"
                    
                    elif tipo_pipe == "Taxas":
                        if 'Anexarcomprovantespipetaxas' not in modules:
                            st.error("❌ Módulo Anexarcomprovantespipetaxas não disponível")
                        else:
                            st.info("🔄 Anexando comprovantes no pipe de taxas...")
                            
                            if modo_anexacao == "Manual" and arquivo_comprovantes:
                                # Salvar temporário
                                with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(arquivo_comprovantes.name)[1]) as tmp:
                                    tmp.write(arquivo_comprovantes.getvalue())
                                    tmp_path = tmp.name
                                
                                resultado = modules['Anexarcomprovantespipetaxas'].anexar_com_arquivo(
                                    tmp_path,
                                    data_inicio_str,
                                    data_fim_str
                                )
                                
                                os.unlink(tmp_path)
                            else:
                                # Modo automático
                                resultado = modules['Anexarcomprovantespipetaxas'].anexar_automatico(
                                    data_inicio_str,
                                    data_fim_str
                                )
                            
                            arquivo_saida = f"comprovantes_taxas_{data_fim_str}.xlsx"
                    
                    # Mostrar resultado
                    if resultado:
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
                        label="� Baixar Relatório",
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
    
    # Ajuda
    with st.expander("❓ Ajuda", expanded=False):
        st.markdown("""
        ### Como usar:
        
        1. **Modo**: Escolha entre Automático (busca cards do Pipefy) ou Manual (usa arquivo)
        2. **Arquivo**: Se modo Manual, faça upload do arquivo de cards
        3. **Tipo**: Selecione o pipe (Liquidação ou Taxas)
        4. **Período**: Defina quantos dias retroativos buscar comprovantes
        5. **Executar**: Clique no botão para anexar
        6. **Download**: Baixe o relatório de anexações
        
        ### Modo Automático:
        
        Busca automaticamente cards na fase "Aguardando Comprovantes" do Pipefy e:
        - Consulta API Santander para buscar comprovantes
        - Faz match automático por CNPJ + Valor + Beneficiário
        - Anexa comprovantes aos cards correspondentes
        - Move cards para próxima fase se configurado
        
        ### Modo Manual:
        
        Usa arquivo fornecido (Excel, CSV ou JSON) com lista de cards e:
        - Processa cards do arquivo
        - Busca comprovantes na API Santander
        - Anexa aos cards do Pipefy
        
        ℹ️ **Nota**: A API Santander tem limite de 30 dias retroativos.
        """)

# ===== RODAPÉ =====
st.markdown("---")
st.caption("� Kanastra Finance Automation Dashboard | Desenvolvido com Streamlit")
    
    # COLUNA 2: Anexar ao Pipefy
    with col2:
        st.subheader("📤 Anexar ao Pipefy")
        
        # Seleção de pipe
        pipe_destino = st.radio(
            "Pipe de destino",
            options=["Liquidação", "Taxas"],
            key="pipe_destino_comp"
        )
        
        # Data dos comprovantes
        data_comprovantes = st.date_input(
            "Data dos comprovantes",
            value=dt.date.today(),
            key="data_comp_pipefy"
        )
        
        # Opções
        with st.expander("⚙️ Opções de Anexação"):
            sobrescrever = st.checkbox("Sobrescrever anexos existentes", value=False)
            validar_match = st.checkbox("Validar match antes de anexar", value=True)
            apenas_simular = st.checkbox("Apenas simular (não anexar)", value=False)
        
        st.markdown("---")
        
        # Estatísticas (mockup)
        col_stat1, col_stat2 = st.columns(2)
        with col_stat1:
            st.metric("Cards aguardando", "0", delta="0")
        with col_stat2:
            st.metric("Comprovantes prontos", "0", delta="0")
        
        st.markdown("---")
        
        # Botão anexar
        if st.button("📤 Anexar Comprovantes", key="btn_anexar_comp", type="primary"):
            with st.spinner("Anexando comprovantes aos cards..."):
                try:
                    data_str = data_comprovantes.strftime("%Y-%m-%d")
                    
                    if pipe_destino == "Liquidação":
                        if 'Anexarcomprovantespipe' not in modules:
                            st.error("❌ Módulo Anexarcomprovantespipe não disponível")
                        else:
                            st.info("🔄 Anexando comprovantes ao pipe de Liquidação...")
                            
                            resultado = modules['Anexarcomprovantespipe'].anexar_comprovantes(
                                data_comprovante=data_str,
                                apenas_simular=apenas_simular
                            )
                            
                            st.success("✅ Comprovantes anexados ao pipe de Liquidação!")
                            
                            with st.expander("📊 Resultado"):
                                if isinstance(resultado, dict):
                                    col_r1, col_r2, col_r3 = st.columns(3)
                                    with col_r1:
                                        st.metric("Total processados", resultado.get('total', 0))
                                    with col_r2:
                                        st.metric("Anexados", resultado.get('sucesso', 0))
                                    with col_r3:
                                        st.metric("Erros", resultado.get('erros', 0))
                                else:
                                    st.write(resultado)
                    else:
                        if 'Anexarcomprovantespipetaxas' not in modules:
                            st.error("❌ Módulo Anexarcomprovantespipetaxas não disponível")
                        else:
                            st.info("🔄 Anexando comprovantes ao pipe de Taxas...")
                            
                            resultado = modules['Anexarcomprovantespipetaxas'].anexar_comprovantes(
                                data_comprovante=data_str,
                                apenas_simular=apenas_simular
                            )
                            
                            st.success("✅ Comprovantes anexados ao pipe de Taxas!")
                            
                            with st.expander("📊 Resultado"):
                                if isinstance(resultado, dict):
                                    col_r1, col_r2, col_r3 = st.columns(3)
                                    with col_r1:
                                        st.metric("Total processados", resultado.get('total', 0))
                                    with col_r2:
                                        st.metric("Anexados", resultado.get('sucesso', 0))
                                    with col_r3:
                                        st.metric("Erros", resultado.get('erros', 0))
                                else:
                                    st.write(resultado)
                    
                except Exception as e:
                    st.error(f"❌ Erro: {str(e)}")
                    st.code(traceback.format_exc())

# Footer
st.markdown("---")
col_footer1, col_footer2, col_footer3 = st.columns(3)

with col_footer1:
    st.caption("📊 Dashboard desenvolvido com Streamlit")

with col_footer2:
    st.caption("🔐 Kanastra - Sistema Interno")

with col_footer3:
    st.caption(f"📅 {datetime.now().strftime('%d/%m/%Y %H:%M')}")
