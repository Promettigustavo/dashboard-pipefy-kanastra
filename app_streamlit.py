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
import importlib
import importlib.util

# ===== Funções Helper CETIP =====
def _import_local_module(mod_name: str, base_path: Path = None):
    """
    Importa módulo local CETIP.
    Se base_path não fornecido, procura na pasta 'Projeto CETIP' relativa ao script.
    """
    if base_path is None:
        # Tenta encontrar a pasta Projeto CETIP
        current_dir = Path(__file__).parent
        cetip_path = current_dir.parent / "Projeto CETIP"
        if not cetip_path.exists():
            # Fallback: mesmo diretório
            cetip_path = current_dir
    else:
        cetip_path = base_path
    
    local_path = cetip_path / f"{mod_name}.py"
    
    if local_path.exists():
        spec = importlib.util.spec_from_file_location(mod_name, str(local_path))
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            sys.modules[mod_name] = mod
            spec.loader.exec_module(mod)
            return mod
    
    # Fallback: import normal
    return importlib.import_module(mod_name)

def _count_registros_em_arquivo(path_arquivo: Path, tipo: str) -> int:
    """
    Conta quantos registros foram gerados no arquivo CETIP:
    - tipo 'nc'   -> começa com 'NC   1'
    - tipo 'mda'  -> começa com 'MDA  1' (Depósito/Venda)
    - tipo 'cci'  -> começa com 'CCI  1'
    """
    if not path_arquivo or not path_arquivo.exists():
        return 0
    
    if tipo == "nc":
        prefixos = ["NC   1"]
    elif tipo == "mda":
        prefixos = ["MDA  1"]
    elif tipo == "cci":
        prefixos = ["CCI  1"]
    else:
        prefixos = []
    
    total = 0
    try:
        with open(path_arquivo, "r", encoding="utf-8", errors="ignore") as f:
            for ln in f:
                if any(ln.startswith(p) for p in prefixos):
                    total += 1
    except Exception:
        try:
            with open(path_arquivo, "r", errors="ignore") as f:
                for ln in f:
                    if any(ln.startswith(p) for p in prefixos):
                        total += 1
        except Exception:
            return 0
    return total

def _stem_clean(p: Path) -> str:
    """Nome base sem extensão, limpo para compor arquivos de saída."""
    return p.stem.replace(" ", "_")

def _ensure_dir(p: Path):
    """Cria diretório se não existir."""
    p.mkdir(parents=True, exist_ok=True)

def _choose_out_dir_or_sibling(selected_path: Path, out_dir: str | None) -> Path:
    """
    Retorna a pasta onde salvar:
    - se out_dir estiver preenchido: usa out_dir
    - caso contrário: pasta da planilha/arquivo de entrada
    """
    if out_dir:
        out = Path(out_dir).expanduser()
        _ensure_dir(out)
        return out
    return selected_path.parent

# ===== Funções de Processamento CETIP =====
def run_emissao_nc(log_list: list, selected_path: Path, out_dir: str | None) -> int:
    """Executa Emissão NC."""
    try:
        log_list.append("[NC] Iniciando Emissão de NC...")
        nc_mod = _import_local_module("EmissaoNC_v2")
        
        out_folder = _choose_out_dir_or_sibling(selected_path, out_dir)
        out_path = out_folder / f"NC_{_stem_clean(selected_path)}.txt"
        
        if hasattr(nc_mod, "main"):
            nc_mod.main(
                arquivo_saida=str(out_path),
                caminho_entrada=str(selected_path),
                sheet_index=1  # 2ª aba
            )
            log_list.append(f"✅ Arquivo gerado: {out_path.name}")
        else:
            raise RuntimeError("O módulo EmissaoNC_v2 não possui função main().")
        
        qtd_nc = _count_registros_em_arquivo(out_path, "nc")
        log_list.append(f"📊 Emissões geradas: {qtd_nc}")
        return qtd_nc
    except Exception as e:
        log_list.append(f"❌ ERRO: {str(e)}")
        log_list.append(traceback.format_exc())
        return 0

def _rodar_dep_uma_vez(dep_mod, selected_path: Path, out_path: Path, papel: str, log_list: list):
    """Executa depósito para um papel específico."""
    if hasattr(dep_mod, "gerar_emissao_deposito_from_excel"):
        try:
            dep_mod.gerar_emissao_deposito_from_excel(
                caminho_planilha=selected_path,
                sheet_index=1,
                arquivo_saida=out_path,
                data_operacao=None,
                papel_participante=papel,
            )
        except TypeError:
            setattr(dep_mod, "PAPEL_PARTICIPANTE", papel)
            dep_mod.gerar_emissao_deposito_from_excel(
                caminho_planilha=selected_path,
                sheet_index=1,
                arquivo_saida=out_path,
                data_operacao=None,
            )
        except Exception as e1:
            log_list.append(f"⚠️ Falhou sheet_index=1: {e1.__class__.__name__}. Tentando aba 0...")
            try:
                dep_mod.gerar_emissao_deposito_from_excel(
                    caminho_planilha=selected_path,
                    sheet_index=0,
                    arquivo_saida=out_path,
                    data_operacao=None,
                    papel_participante=papel,
                )
            except TypeError:
                setattr(dep_mod, "PAPEL_PARTICIPANTE", papel)
                dep_mod.gerar_emissao_deposito_from_excel(
                    caminho_planilha=selected_path,
                    sheet_index=0,
                    arquivo_saida=out_path,
                    data_operacao=None,
                )

def run_emissao_deposito(log_list: list, selected_path: Path, papel_option: str, out_dir: str | None) -> int:
    """Executa Emissão Depósito."""
    try:
        log_list.append(f"[DEP] Iniciando Emissão Depósito (Papel: {papel_option})...")
        dep_mod = _import_local_module("emissao_deposito")
        out_folder = _choose_out_dir_or_sibling(selected_path, out_dir)
        
        total_emitidas = 0
        
        if papel_option == "ambos":
            # Emissor
            out_path_em = out_folder / f"DEP_{_stem_clean(selected_path)}_EMISSOR.txt"
            _rodar_dep_uma_vez(dep_mod, selected_path, out_path_em, "02", log_list)
            log_list.append(f"✅ Arquivo gerado (Emissor): {out_path_em.name}")
            qtd_em = _count_registros_em_arquivo(out_path_em, "mda")
            log_list.append(f"📊 Emissões (Emissor): {qtd_em}")
            total_emitidas += qtd_em
            
            # Distribuidor
            out_path_di = out_folder / f"DEP_{_stem_clean(selected_path)}_DISTRIBUIDOR.txt"
            _rodar_dep_uma_vez(dep_mod, selected_path, out_path_di, "03", log_list)
            log_list.append(f"✅ Arquivo gerado (Distribuidor): {out_path_di.name}")
            qtd_di = _count_registros_em_arquivo(out_path_di, "mda")
            log_list.append(f"📊 Emissões (Distribuidor): {qtd_di}")
            total_emitidas += qtd_di
        else:
            papel_nome = "EMISSOR" if papel_option == "02" else "DISTRIBUIDOR"
            out_path = out_folder / f"DEP_{_stem_clean(selected_path)}_{papel_nome}.txt"
            _rodar_dep_uma_vez(dep_mod, selected_path, out_path, papel_option, log_list)
            log_list.append(f"✅ Arquivo gerado ({papel_nome}): {out_path.name}")
            total_emitidas = _count_registros_em_arquivo(out_path, "mda")
            log_list.append(f"📊 Emissões geradas: {total_emitidas}")
        
        return total_emitidas
    except Exception as e:
        log_list.append(f"❌ ERRO: {str(e)}")
        log_list.append(traceback.format_exc())
        return 0

def run_compra_venda(log_list: list, selected_path: Path, out_dir: str | None) -> int:
    """Executa Operação de Venda."""
    try:
        log_list.append("[CV] Iniciando Operação de Venda...")
        cv_mod = None
        for mod_name in ["operacao_compra_venda", "Compra_Venda", "compra_venda"]:
            try:
                cv_mod = _import_local_module(mod_name)
                break
            except:
                continue
        
        if cv_mod is None:
            raise ModuleNotFoundError("Módulo de Compra/Venda não encontrado")
        
        out_folder = _choose_out_dir_or_sibling(selected_path, out_dir)
        out_path = out_folder / f"Venda_{_stem_clean(selected_path)}.txt"
        
        if hasattr(cv_mod, "gerar_compra_venda_from_excel"):
            try:
                cv_mod.gerar_compra_venda_from_excel(
                    caminho_planilha=selected_path,
                    sheet_index=1,
                    arquivo_saida=out_path,
                    data_operacao=None,
                )
                log_list.append(f"✅ Arquivo gerado: {out_path.name}")
            except:
                cv_mod.gerar_compra_venda_from_excel(
                    caminho_planilha=selected_path,
                    sheet_index=0,
                    arquivo_saida=out_path,
                    data_operacao=None,
                )
                log_list.append(f"✅ Arquivo gerado (aba 0): {out_path.name}")
        
        qtd_cv = _count_registros_em_arquivo(out_path, "mda")
        log_list.append(f"📊 Emissões geradas: {qtd_cv}")
        return qtd_cv
    except Exception as e:
        log_list.append(f"❌ ERRO: {str(e)}")
        log_list.append(traceback.format_exc())
        return 0

def meu_numero_factory_from_state(out_dir: str | None, selected_path: Path):
    """Fábrica do 'meu número' para CCI."""
    state_dir = Path(out_dir) if out_dir else selected_path.parent
    state_dir.mkdir(parents=True, exist_ok=True)
    state_file = state_dir / "meu_numero_state.txt"
    
    def _next() -> str:
        today = dt.date.today().isoformat()
        if state_file.exists():
            try:
                last_day, last_num = state_file.read_text(encoding="utf-8").strip().split(",")
                n = (int(last_num) + 1) if last_day == today else 1
            except:
                n = 1
        else:
            n = 1
        state_file.write_text(f"{today},{n}", encoding="utf-8")
        return str(n).zfill(10)
    
    return _next

def run_cci(log_list: list, selected_path: Path, operacao_option: str, modalidade_option: str, out_dir: str | None) -> int:
    """Executa Emissão CCI."""
    try:
        log_list.append(f"[CCI] Iniciando Emissão CCI (Operação: {operacao_option} | Modalidade: {modalidade_option})...")
        cci_mod = _import_local_module("CCI")
        
        out_folder = _choose_out_dir_or_sibling(selected_path, out_dir)
        out_path = out_folder / f"CCI_{_stem_clean(selected_path)}.txt"
        
        fn_meu = meu_numero_factory_from_state(out_dir, selected_path)
        
        if hasattr(cci_mod, "registros_from_excel") and hasattr(cci_mod, "gerar_arquivo_cci"):
            regs = cci_mod.registros_from_excel(
                path_xlsx=str(selected_path),
                operacao=operacao_option,
                modalidade=modalidade_option,
                meu_numero_factory=fn_meu,
                sheet_index=0,
            )
            conteudo = cci_mod.gerar_arquivo_cci(regs, participante="LIMINETRUSTDTVM", data_arquivo=None)
            with open(out_path, "w", encoding="utf-8", newline="\n") as f:
                f.write(conteudo + "\n" if not conteudo.endswith("\n") else conteudo)
            log_list.append(f"✅ Arquivo gerado: {out_path.name}")
        else:
            raise RuntimeError("Módulo CCI sem APIs esperadas")
        
        qtd_cci = _count_registros_em_arquivo(out_path, "cci")
        log_list.append(f"📊 Registros gerados: {qtd_cci}")
        return qtd_cci
    except Exception as e:
        log_list.append(f"❌ ERRO: {str(e)}")
        log_list.append(traceback.format_exc())
        return 0

def run_conversor_v2c(log_list: list, selected_path: Path, out_dir: str | None):
    """Executa Conversor V2C (Venda → Compra)."""
    try:
        log_list.append("[V2C] Iniciando Conversor V2C (GOORO)...")
        conv_mod = _import_local_module("conversor_v2")
        
        out_folder = _choose_out_dir_or_sibling(selected_path, out_dir)
        default_name = (
            (selected_path.name[:-10] + "_compra.txt") if selected_path.name.endswith("_venda.txt")
            else (selected_path.stem + "_compra.txt")
        )
        out_path = out_folder / default_name
        
        if hasattr(conv_mod, "executar_gooro_from_path"):
            conv_mod.executar_gooro_from_path(
                caminho_venda=str(selected_path),
                arquivo_saida=str(out_path),
            )
            log_list.append(f"✅ Arquivo gerado: {out_path.name}")
        elif hasattr(conv_mod, "executar_gooro"):
            conv_mod.executar_gooro(arquivo_saida=str(out_path))
            log_list.append(f"✅ Arquivo gerado: {out_path.name}")
        else:
            raise RuntimeError("Módulo conversor_v2 sem APIs conhecidas")
        
        log_list.append("✅ [V2C] Conversão concluída")
    except Exception as e:
        log_list.append(f"❌ ERRO: {str(e)}")
        log_list.append(traceback.format_exc())

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
        color: #00875F;
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
        background-color: #00875F;
        color: white;
        font-weight: 600;
        border-radius: 0.5rem;
        padding: 0.75rem 1.5rem;
        border: none;
        transition: all 0.3s;
    }
    .stButton>button:hover {
        background-color: #006644;
        transform: translateY(-2px);
        box-shadow: 0 4px 6px rgba(0,135,95,0.2);
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
        background-color: #00875F;
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
        <div style='background: linear-gradient(90deg, #00875F 0%, #006644 100%); 
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
        <div style='background-color: #f8f9fa; padding: 1rem; border-radius: 8px; margin-bottom: 1.5rem; border-left: 4px solid #00875F;'>
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
        <div style='background: linear-gradient(90deg, #00875F 0%, #006644 100%); 
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
            <div style='background-color: #f8f9fa; padding: 1rem; border-radius: 8px; border-left: 4px solid #00875F;'>
                <h4 style='margin: 0 0 0.75rem 0; color: #00875F;'>📋 Processos</h4>
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
            <div style='background-color: #f8f9fa; padding: 1rem; border-radius: 8px; border-left: 4px solid #00875F;'>
                <h4 style='margin: 0 0 0.75rem 0; color: #00875F;'>📁 Arquivos de Entrada</h4>
            </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Determinar qual tipo de arquivo aceitar baseado nos processos selecionados
        processos_ativos = []
        aceita_excel = False
        aceita_txt = False
        
        if executar_nc:
            processos_ativos.append("Emissão NC (2ª aba)")
            aceita_excel = True
        if executar_dep:
            processos_ativos.append("Emissão Depósito (2ª aba)")
            aceita_excel = True
        if executar_cv:
            processos_ativos.append("Operação de Venda (2ª aba)")
            aceita_excel = True
        if executar_cci:
            processos_ativos.append("Emissão CCI (aba principal)")
            aceita_excel = True
        if executar_v2c:
            processos_ativos.append("Conversor V2C")
            aceita_txt = True
        
        # Tipos de arquivo aceitos
        tipos_aceitos = []
        if aceita_excel:
            tipos_aceitos.extend(['xlsx', 'xls', 'xlsm', 'csv'])
        if aceita_txt:
            tipos_aceitos.append('txt')
        
        # Label dinâmico
        if processos_ativos:
            label_processos = " | ".join(processos_ativos)
            help_text = f"Arquivo para: {label_processos}"
        else:
            label_processos = "Nenhum processo selecionado"
            help_text = "Selecione pelo menos um processo na coluna ao lado"
        
        # Upload único que se adapta aos processos selecionados
        arquivo_cetip = st.file_uploader(
            f"📂 Arquivo para processos selecionados:",
            type=tipos_aceitos if tipos_aceitos else None,
            key="cetip_arquivo_unico",
            disabled=not processos_ativos,
            help=help_text
        )
        
        # Informação sobre processos ativos
        if processos_ativos:
            st.caption(f"✅ Processos selecionados: {len(processos_ativos)}")
            with st.expander("📋 Detalhes dos processos", expanded=False):
                for processo in processos_ativos:
                    st.markdown(f"- {processo}")
        else:
            st.warning("⚠️ Selecione pelo menos um processo")
        
        # Preview do arquivo
        if arquivo_cetip:
            with st.expander("👁️ Preview do arquivo", expanded=False):
                try:
                    if arquivo_cetip.name.endswith('.txt'):
                        content = arquivo_cetip.getvalue().decode('utf-8')
                        st.text_area("Conteúdo", content[:1000], height=200, disabled=True)
                        st.caption(f"📄 {len(content)} caracteres | Arquivo: {arquivo_cetip.name}")
                    else:
                        df_preview = pd.read_excel(arquivo_cetip) if arquivo_cetip.name.endswith(('.xlsx', '.xls', '.xlsm')) else pd.read_csv(arquivo_cetip)
                        st.dataframe(df_preview.head(10), use_container_width=True)
                        st.caption(f"📊 {len(df_preview)} linhas × {len(df_preview.columns)} colunas | Arquivo: {arquivo_cetip.name}")
                except Exception as e:
                    st.error(f"Erro ao visualizar arquivo: {str(e)}")
    
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
        
        # Verificar se arquivo foi fornecido
        arquivo_fornecido = arquivo_cetip is not None
        
        executar_disabled = not algum_processo or not arquivo_fornecido
        
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
                    log_cetip.append(f"📂 Arquivo fornecido: {arquivo_cetip.name}")
                    log_cetip.append("")
                    
                    # Salvar arquivo temporário (usado por todos os processos)
                    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(arquivo_cetip.name)[1]) as tmp:
                        tmp.write(arquivo_cetip.getvalue())
                        tmp_path = tmp.name
                    
                    log_cetip.append(f"📂 Arquivo temporário: {tmp_path}")
                    log_cetip.append("")
                    
                    # Converter string de tmp_path para Path object
                    tmp_path_obj = Path(tmp_path)
                    
                    # Processar NC
                    if executar_nc:
                        log_cetip.append("─" * 60)
                        log_cetip.append("📄 EMISSÃO NC")
                        log_cetip.append("─" * 60)
                        qtd_nc = run_emissao_nc(log_cetip, tmp_path_obj, pasta_saida_cetip)
                        contadores["NC"] = qtd_nc
                        log_cetip.append("")
                    
                    # Processar Depósito
                    if executar_dep:
                        log_cetip.append("─" * 60)
                        log_cetip.append("💰 EMISSÃO DEPÓSITO")
                        log_cetip.append("─" * 60)
                        qtd_dep = run_emissao_deposito(log_cetip, tmp_path_obj, papel_deposito, pasta_saida_cetip)
                        contadores["Depósito"] = qtd_dep
                        log_cetip.append("")
                    
                    # Processar Compra/Venda
                    if executar_cv:
                        log_cetip.append("─" * 60)
                        log_cetip.append("📊 OPERAÇÃO DE VENDA")
                        log_cetip.append("─" * 60)
                        qtd_cv = run_compra_venda(log_cetip, tmp_path_obj, pasta_saida_cetip)
                        contadores["Venda"] = qtd_cv
                        log_cetip.append("")
                    
                    # Processar CCI
                    if executar_cci:
                        log_cetip.append("─" * 60)
                        log_cetip.append("📝 EMISSÃO CCI")
                        log_cetip.append("─" * 60)
                        qtd_cci = run_cci(log_cetip, tmp_path_obj, operacao_cci, modalidade_cci, pasta_saida_cetip)
                        contadores["CCI"] = qtd_cci
                        log_cetip.append("")
                    
                    # Processar V2C
                    if executar_v2c:
                        log_cetip.append("─" * 60)
                        log_cetip.append("🔄 CONVERSOR V2C (GOORO)")
                        log_cetip.append("─" * 60)
                        run_conversor_v2c(log_cetip, tmp_path_obj, pasta_saida_cetip)
                        log_cetip.append("ℹ️ Conversor V2C não participa da contagem de emissões")
                        log_cetip.append("")
                    
                    # Limpar arquivo temporário
                    try:
                        os.unlink(tmp_path)
                        log_cetip.append("🗑️ Arquivo temporário removido")
                    except Exception as e:
                        log_cetip.append(f"⚠️ Aviso: não foi possível remover arquivo temporário: {e}")
                    
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
    elif not arquivo_fornecido:
        st.warning("⚠️ Forneça o arquivo de entrada para processar")
    
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
        <div style='background: linear-gradient(90deg, #00875F 0%, #006644 100%); 
                    padding: 1.5rem; border-radius: 10px; margin-bottom: 2rem;'>
            <h1 style='color: white; margin: 0; font-size: 2rem;'>
                📎 Anexar Comprovantes Santander
            </h1>
            <p style='color: rgba(255,255,255,0.9); margin: 0.5rem 0 0 0; font-size: 1rem;'>
                Busque e anexe comprovantes automaticamente via API Santander
            </p>
        </div>
    """, unsafe_allow_html=True)
    
    st.info("💡 Busque comprovantes da API Santander e anexe automaticamente aos cards do Pipefy com matching inteligente por valor e beneficiário")
    
    # Layout em 2 colunas: Buscar + Anexar
    col_buscar, col_anexar = st.columns([1, 1])
    
    # ===== COLUNA ESQUERDA: BUSCAR COMPROVANTES =====
    with col_buscar:
        st.markdown("""
            <div style='background-color: #f8f9fa; padding: 1rem; border-radius: 8px; border-left: 4px solid #00875F;'>
                <h4 style='margin: 0 0 0.75rem 0; color: #00875F;'>🔍 Buscar Comprovantes (API Santander)</h4>
            </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Data de busca
        data_busca_santander = st.date_input(
            "📅 Data de Busca",
            value=dt.date.today(),
            help="Data para buscar comprovantes na API Santander",
            key="data_busca_santander"
        )
        
        # Pasta de destino
        pasta_destino = st.text_input(
            "📁 Pasta de Destino",
            value=str(Path.cwd() / "Comprovantes"),
            help="Pasta onde os PDFs serão salvos",
            key="pasta_destino_comp"
        )
        
        st.markdown("---")
        
        # Seleção de fundos Santander
        st.markdown("**💼 Fundos Santander**")
        
        # Importar lista de fundos
        try:
            # Importar módulo credenciais_bancos
            import sys
            from pathlib import Path
            
            # Garantir que o path do módulo está no sys.path
            current_dir = Path(__file__).parent
            if str(current_dir) not in sys.path:
                sys.path.insert(0, str(current_dir))
            
            from credenciais_bancos import SANTANDER_FUNDOS
            fundos_disponiveis = sorted(list(SANTANDER_FUNDOS.keys()))
            
            if len(fundos_disponiveis) == 0:
                st.warning("⚠️ Lista de fundos Santander vazia")
        except ImportError as e:
            fundos_disponiveis = []
            st.error(f"❌ Erro ao importar credenciais_bancos: {str(e)}")
        except Exception as e:
            fundos_disponiveis = []
            st.error(f"❌ Erro ao carregar fundos: {str(e)}")
        
        # Campo de busca/filtro
        filtro_fundo = st.text_input(
            "🔍 Filtrar fundos",
            placeholder="Digite para filtrar...",
            key="filtro_fundos_comp"
        )
        
        # Filtrar fundos se houver texto
        if filtro_fundo:
            fundos_filtrados = [f for f in fundos_disponiveis if filtro_fundo.lower() in f.lower()]
        else:
            fundos_filtrados = fundos_disponiveis
        
        # Multiselect para seleção de fundos
        fundos_selecionados = st.multiselect(
            "Selecione os fundos",
            options=fundos_filtrados,
            default=fundos_filtrados[:3] if len(fundos_filtrados) > 0 else [],
            key="fundos_selecionados_comp",
            help="Segure Ctrl/Cmd para seleção múltipla"
        )
        
        # Botões de seleção rápida
        col_sel1, col_sel2 = st.columns(2)
        with col_sel1:
            if st.button("✓ Todos", key="selecionar_todos_fundos", use_container_width=True):
                st.session_state['fundos_selecionados_comp'] = fundos_filtrados
                st.rerun()
        with col_sel2:
            if st.button("✕ Limpar", key="limpar_fundos", use_container_width=True):
                st.session_state['fundos_selecionados_comp'] = []
                st.rerun()
        
        st.caption(f"� {len(fundos_selecionados)} de {len(fundos_filtrados)} fundos selecionados")
        
        st.markdown("---")
        
        # Botão Buscar Comprovantes
        if st.button(
            "🔍 Buscar Comprovantes via API",
            type="primary",
            use_container_width=True,
            key="btn_buscar_santander",
            disabled=len(fundos_selecionados) == 0
        ):
            st.warning("⚠️ Funcionalidade de busca via API Santander em desenvolvimento")
            st.info(f"📅 Data: {data_busca_santander.strftime('%Y-%m-%d')}")
            st.info(f"💼 Fundos: {len(fundos_selecionados)}")
            st.info(f"📁 Destino: {pasta_destino}")
    
    # ===== COLUNA DIREITA: ANEXAR NO PIPEFY =====
    with col_anexar:
        st.markdown("""
            <div style='background-color: #f8f9fa; padding: 1rem; border-radius: 8px; border-left: 4px solid #00875F;'>
                <h4 style='margin: 0 0 0.75rem 0; color: #00875F;'>⚙️ Anexar no Pipefy</h4>
            </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Seleção de pipes
        st.markdown("**📊 Selecione os pipes para processar:**")
        
        pipe_liquidacao = st.checkbox(
            "💰 Pipe Liquidação",
            value=True,
            key="pipe_comp_liquidacao"
        )
        
        pipe_taxas = st.checkbox(
            "📊 Pipe Taxas",
            value=False,
            key="pipe_comp_taxas"
        )
        
        pipe_taxas_anbima = st.checkbox(
            "📈 Taxas Anbima (em desenvolvimento)",
            value=False,
            disabled=True,
            key="pipe_comp_taxas_anbima"
        )
        
        st.markdown("---")
        
        # Data para buscar no Pipefy
        data_pipefy = st.date_input(
            "📅 Data de Referência Pipefy",
            value=dt.date.today(),
            help="Data para buscar comprovantes correspondentes no Pipefy",
            key="data_pipefy_comp"
        )
        
        st.markdown("---")
        
        # Card informativo
        st.info("""
        **ℹ️ Como funciona:**
        
        • Matching por VALOR e NOME do beneficiário
        
        • Anexa automaticamente ao card correspondente
        
        • Move para fase "Solicitação Paga"
        """)
        
        st.markdown("---")
        
        # Botão principal
        if st.button(
            "▶ Anexar Comprovantes",
            type="primary",
            use_container_width=True,
            key="btn_anexar_comprovantes",
            disabled=not any([pipe_liquidacao, pipe_taxas])
        ):
            with st.spinner("Processando..."):
                try:
                    data_busca_str = data_pipefy.strftime("%Y-%m-%d")
                    
                    st.markdown("---")
                    st.markdown("### 📊 Logs de Execução")
                    
                    log_container = st.container()
                    
                    # Processar pipes selecionados
                    if pipe_liquidacao:
                        with log_container:
                            st.markdown("#### 💰 Pipe Liquidação")
                            
                            module, error = get_module('Anexarcomprovantespipe')
                            if not module:
                                st.error(f"❌ Módulo não disponível: {error}")
                            else:
                                st.info(f"� Buscando cards com data: {data_busca_str}")
                                
                                if hasattr(module, 'processar_todos_cards'):
                                    resultados = module.processar_todos_cards(data_busca=data_busca_str)
                                    
                                    if resultados:
                                        sucessos = [r for r in resultados if r.get('sucesso')]
                                        st.success(f"✅ {len(sucessos)} card(s) processado(s) com sucesso")
                                        
                                        for r in sucessos:
                                            st.write(f"  ✅ {r.get('card_title', 'Card')} → Solicitação Paga")
                                    else:
                                        st.warning("⚠️ Nenhum card processado")
                                else:
                                    st.error("❌ Função processar_todos_cards não encontrada")
                    
                    if pipe_taxas:
                        with log_container:
                            st.markdown("#### 📊 Pipe Taxas")
                            
                            module, error = get_module('Anexarcomprovantespipetaxas')
                            if not module:
                                st.error(f"❌ Módulo não disponível: {error}")
                            else:
                                st.info(f"� Buscando cards com data: {data_busca_str}")
                                
                                if hasattr(module, 'processar_todos_cards'):
                                    resultados = module.processar_todos_cards(data_busca=data_busca_str)
                                    
                                    if resultados:
                                        sucessos = [r for r in resultados if r.get('sucesso')]
                                        st.success(f"✅ {len(sucessos)} card(s) processado(s) com sucesso")
                                        
                                        for r in sucessos:
                                            st.write(f"  ✅ {r.get('card_title', 'Card')} → Solicitação Paga")
                                    else:
                                        st.warning("⚠️ Nenhum card processado")
                                else:
                                    st.error("❌ Função processar_todos_cards não encontrada")
                    
                    st.markdown("---")
                    st.success("✅ Processamento concluído!")
                    
                except Exception as e:
                    st.error(f"❌ Erro: {str(e)}")
                    with st.expander("🔍 Detalhes do erro"):
                        st.code(traceback.format_exc())
        
        # Botão de teste
        if st.button(
            "🧪 Testar Matching (sem anexar)",
            use_container_width=True,
            key="btn_testar_matching",
            disabled=not pipe_liquidacao
        ):
            with st.spinner("Testando matching..."):
                try:
                    data_busca_str = data_pipefy.strftime("%Y-%m-%d")
                    
                    st.markdown("---")
                    st.markdown("### 🧪 Teste de Matching")
                    
                    module, error = get_module('Anexarcomprovantespipe')
                    if not module:
                        st.error(f"❌ Módulo não disponível: {error}")
                    else:
                        st.info(f"📅 Data: {data_busca_str}")
                        st.info("⚠️ Modo teste - Sem anexar ou mover cards")
                        
                        if hasattr(module, 'testar_matching_apenas'):
                            module.testar_matching_apenas(data_busca=data_busca_str)
                            st.success("✅ Teste concluído!")
                        else:
                            st.error("❌ Função testar_matching_apenas não encontrada")
                
                except Exception as e:
                    st.error(f"❌ Erro: {str(e)}")
                    with st.expander("� Detalhes do erro"):
                        st.code(traceback.format_exc())


# ===== RODAPÉ =====
st.markdown("---")

col_footer1, col_footer2, col_footer3 = st.columns(3)

with col_footer1:
    st.caption("📊 Dashboard desenvolvido com Streamlit")

with col_footer2:
    st.caption("🔐 Kanastra - Sistema Interno")

with col_footer3:
    st.caption(f"📅 {datetime.now().strftime('%d/%m/%Y %H:%M')}")
