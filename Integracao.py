# Integração / Launcher – vFinal (Liquidação + Taxas ARBI + Pipe Taxas + Amortização)

from __future__ import annotations
import os
import sys
import base64
import importlib
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
import datetime as dt
import threading
import webbrowser

# ====== Ícone (PNG) embutido em base64 (32x32) ======
_APP_ICON_PNG_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAYAAABzenr0AAAABHNCSVQICAgIfAhkiAAA..."
    "AAA"  # (b64 encurtado — pode deixar assim; Tk ignora se inválido)
)

# ===== Import dos cores (mantenha os nomes) =====
import pipeliquidacao as liq_core
import taxasarbi as taxas_arbi_core   # mantém ARBI
import PipeTaxas as pipe_taxas_core   # Pipe Taxas (sem base)

# === AMORTIZAÇÃO === import do módulo de amortização
try:
    import Amortizacao as amort_core  # deve expor run_amortizacao(...)
except Exception:
        class _AmortStub:
            @staticmethod
            def run_amortizacao(input_file: Path, data_pagamento: str, saida_path: Path):
                # Fallback para permitir testes do fluxo sem o core pronto
                saida_path.parent.mkdir(parents=True, exist_ok=True)
                return {
                    "csv": str(saida_path.with_suffix('.csv')),
                    "xlsx": str(saida_path.with_suffix('.xlsx')),
                    "total_registros": 0,
                    "ok": 0,
                    "pendentes": 0,
                    "mensagem": "AMORTIZAÇÃO – EM DESENVOLVIMENTO (stub)."
                }
        amort_core = _AmortStub()

# === AUTO PIPELIQUIDAÇÃO === import da automação completa
try:
    import auto_pipeliquidacao as auto_pipe
except Exception as e:
    print(f"⚠️ Erro ao importar auto_pipeliquidacao: {e}")
    auto_pipe = None

# === AUTO PIPETAXAS === import da automação completa para taxas
try:
    import auto_pipetaxas as auto_taxas
except Exception as e:
    print(f"⚠️ Erro ao importar auto_pipetaxas: {e}")
    auto_taxas = None

# === AUTO TAXAS ANBIMA === import da automação completa para taxas anbima
try:
    import auto_taxasanbima as auto_taxas_anbima
except Exception as e:
    print(f"⚠️ Erro ao importar auto_taxasanbima: {e}")
    auto_taxas_anbima = None

# === AUTO AMORTIZAÇÃO === import da automação completa para amortização
try:
    import auto_amortizacao as auto_amort
    # Forçar reload para pegar alterações
    import importlib
    importlib.reload(auto_amort)
except Exception as e:
    print(f"⚠️ Erro ao importar auto_amortizacao: {e}")
    auto_amort = None

# === MOVECARDS === import opcional para mover cards Triagem -> Em Análise
try:
    import movecards as move_cards
except Exception as e:
    print(f"⚠️ Erro ao importar movecards: {e}")
    move_cards = None

# === MOVER 2A APROVAÇÃO === import opcional para mover cards 2a Aprovação -> Aguardando Comprovante
try:
    import mover_2a_aprovacao as mover_2a
except Exception as e:
    print(f"⚠️ Erro ao importar mover_2a_aprovacao: {e}")
    mover_2a = None

# === ANEXAR COMPROVANTES === import para anexação automática de comprovantes
try:
    import Anexarcomprovantespipe as comprovantes_pipe
    print(f"✅ Módulo Anexarcomprovantespipe importado com sucesso")
except Exception as e:
    print(f"⚠️ Erro ao importar Anexarcomprovantespipe: {e}")
    import traceback
    traceback.print_exc()
    comprovantes_pipe = None

# === ANEXAR COMPROVANTES TAXAS === import para anexação no pipe de Taxas
try:
    import Anexarcomprovantespipetaxas as comprovantes_pipe_taxas
    print(f"✅ Módulo Anexarcomprovantespipetaxas importado com sucesso")
except Exception as e:
    print(f"⚠️ Erro ao importar Anexarcomprovantespipetaxas: {e}")
    import traceback
    traceback.print_exc()
    comprovantes_pipe_taxas = None


APP_TITLE = "Launcher de Automação Pipefy"
APP_SUBTITLE = "Liquidação • Taxas ARBI • Pipe Taxas • Amortização"

DB_LIQ = "Basedadosfundos.xlsx"
DB_TAX_ARBI = "Basedadosfundos_Arbi.xlsx"

# ===== Cores do tema moderno =====
COLORS = {
    'primary': '#2563eb',      # Azul moderno
    'primary_hover': '#1d4ed8',
    'success': '#10b981',      # Verde
    'warning': '#f59e0b',      # Laranja
    'danger': '#ef4444',       # Vermelho
    'bg_dark': '#1e293b',      # Cinza escuro
    'bg_medium': '#94a3b8',    # Cinza médio
    'bg_light': '#f8fafc',     # Cinza claro
    'text_dark': '#0f172a',
    'text_light': '#64748b',
    'border': '#e2e8f0'
}

# ===== Tema moderno opcional =====
USING_BOOTSTRAP = False
try:
    import ttkbootstrap as tb  # type: ignore
    USING_BOOTSTRAP = True
except Exception:
    USING_BOOTSTRAP = False


def file_exists_here(filename: str) -> bool:
    return Path(filename).exists()


def validar_presenca_bancos(
    rodar_liq: bool,
    rodar_tax_arbi: bool,
    rodar_pipe_taxas: bool,
    rodar_amort: bool
) -> tuple[bool, list[str]]:
    """
    Liquidação exige DB_LIQ; Taxas ARBI exige DB_TAX_ARBI;
    Pipe Taxas e Amortização não exigem base.
    """
    faltando: list[str] = []
    if rodar_liq and not file_exists_here(DB_LIQ):
        faltando.append(DB_LIQ)
    if rodar_tax_arbi and not file_exists_here(DB_TAX_ARBI):
        faltando.append(DB_TAX_ARBI)
    return (len(faltando) == 0, faltando)


def default_out_name(prefix: str, ext: str = ".xlsx") -> str:
    """Gera nome padrão: Processo_Tipo_AAAAMMDD.ext"""
    data_hoje = dt.date.today().strftime('%Y%m%d')
    return f"{prefix}_{data_hoje}{ext}"


def open_in_explorer(path: Path) -> None:
    """Abre pasta/arquivo no SO."""
    try:
        if os.name == "nt":
            os.startfile(str(path if path.is_dir() else path.parent))  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            os.system(f'open "{(path if path.is_dir() else path.parent).as_posix()}"')
        else:
            os.system(f'xdg-open "{(path if path.is_dir() else path.parent).as_posix()}"')
    except Exception:
        webbrowser.open((path if path.is_dir() else path.parent).as_uri())


class LauncherApp:
    def __init__(self, root: "tk.Tk | tb.Window", is_in_tab: bool = False):
        self.root = root
        self.is_in_tab = is_in_tab
        
        if not is_in_tab:
            self.root.title(APP_TITLE)
            # Dimensões da janela
            self.root.geometry("1200x850")
            self.root.minsize(1000, 750)
        
        # Configurar cores de fundo
        self.root.configure(bg=COLORS['bg_light'])

        # Ícone
        self._apply_icon()

        # Estados
        self.var_dt = tk.StringVar(value=dt.date.today().strftime("%d/%m/%Y"))
        self.var_liq = tk.BooleanVar(value=True)
        self.var_tax_arbi = tk.BooleanVar(value=False)
        self.var_pipe_taxas = tk.BooleanVar(value=False)
        self.var_taxas_anbima = tk.BooleanVar(value=False)
        # === AMORTIZAÇÃO ===
        self.var_amort = tk.BooleanVar(value=False)

        self.var_in_liq = tk.StringVar(value="")
        self.var_in_tax_arbi = tk.StringVar(value="")
        self.var_in_pipe_taxas = tk.StringVar(value="")
        # === AMORTIZAÇÃO === entradas do usuário
        self.var_in_amort = tk.StringVar(value="")

        self.var_out_dir = tk.StringVar(value="")
        self._last_outputs: list[Path] = []

        # UI
        self._build_ui()
        self._refresh_db_badges()
        
        # Log inicial
        self._add_log("✨ Sistema inicializado com sucesso!")
        self._add_log("💡 Selecione os pipes e escolha o modo de execução")
        self._add_log("")
        
        # === PIPEFY INTEGRATION === Iniciar filtro automático em background
        self._init_pipefy_filter()

    # ---------- UI helpers ----------
    def _apply_icon(self):
        try:
            data = base64.b64decode(_APP_ICON_PNG_B64)
            img = tk.PhotoImage(data=data)
            self.root.iconphoto(True, img)
            self._icon_img = img  # evita GC
        except Exception:
            pass

    def _badge(self, parent, text: str, ok: bool) -> tk.Label:
        """Badge moderno com cantos arredondados"""
        color_bg = COLORS['success'] if ok else COLORS['danger']
        color_fg = "white"
        
        lbl = tk.Label(
            parent, 
            text=f" ✓ {text} " if ok else f" ✗ {text} ",
            bg=color_bg,
            fg=color_fg,
            font=("Segoe UI", 9, "bold"),
            padx=12,
            pady=4,
            relief="flat"
        )
        return lbl

    def _separator(self, parent):
        return ttk.Separator(parent, orient="horizontal")

    def _header(self, parent):
        """Header moderno com gradiente visual"""
        frm = tk.Frame(parent, bg=COLORS['bg_dark'], height=80)
        frm.pack_propagate(False)
        
        # Container interno para conteúdo
        inner = tk.Frame(frm, bg=COLORS['bg_dark'])
        inner.pack(fill="both", expand=True, padx=30, pady=15)
        
        # Título principal
        tk.Label(
            inner, 
            text="🚀 " + APP_TITLE,
            font=("Segoe UI", 20, "bold"),
            fg="white",
            bg=COLORS['bg_dark']
        ).pack(anchor="w")
        
        # Subtítulo
        tk.Label(
            inner,
            text=APP_SUBTITLE,
            font=("Segoe UI", 10),
            fg=COLORS['text_light'],
            bg=COLORS['bg_dark']
        ).pack(anchor="w", pady=(5, 0))
        
        return frm

    # ---------- lógica ----------
    def _validar_data(self, s: str) -> str:
        return liq_core.valida_data_pagamento(s)

    def _montar_caminho_saida(self, pasta: str | None, nome: str, base: Path) -> Path:
        return (Path(pasta) / nome) if (pasta and pasta.strip()) else base.with_name(nome)

    def _add_log(self, message: str):
        """Adiciona uma mensagem ao log da interface"""
        try:
            self.log_text.configure(state="normal")
            self.log_text.insert("end", f"{message}\n")
            self.log_text.see("end")  # Scroll para o final
            self.log_text.configure(state="disabled")
        except Exception:
            pass  # Fail silently se houver problema com a interface

    # ---------- callbacks ----------
    def _pick_in_liq(self):
        path = filedialog.askopenfilename(
            title="Selecione a planilha de entrada do Pipe de Liquidação",
            filetypes=[("Excel", ".xlsx;.xls"), ("CSV/TXT", ".csv;.txt"), ("Todos os arquivos", ".*")],
            initialdir=os.getcwd()
        )
        if path:
            self.var_in_liq.set(path)

    def _pick_in_tax_arbi(self):
        path = filedialog.askopenfilename(
            title="Selecione a planilha de entrada do Pipe de Taxas ARBI",
            filetypes=[("Excel", ".xlsx;.xls"), ("CSV/TXT", ".csv;.txt"), ("Todos os arquivos", ".*")],
            initialdir=os.getcwd()
        )
        if path:
            self.var_in_tax_arbi.set(path)

    def _pick_in_pipe_taxas(self):
        path = filedialog.askopenfilename(
            title="Selecione a planilha de entrada do Pipe de Taxas",
            filetypes=[("Excel", ".xlsx;.xls"), ("CSV/TXT", ".csv;.txt"), ("Todos os arquivos", ".*")],
            initialdir=os.getcwd()
        )
        if path:
            self.var_in_pipe_taxas.set(path)

    # === AMORTIZAÇÃO ===
    def _pick_in_amort(self):
        path = filedialog.askopenfilename(
            title="Selecione a planilha de entrada do Pipe de Amortização",
            filetypes=[("Excel", ".xlsx;.xls"), ("CSV/TXT", ".csv;.txt"), ("Todos os arquivos", ".*")],
            initialdir=os.getcwd()
        )
        if path:
            self.var_in_amort.set(path)

    # Comentários (amortização) removidos – fluxo Excel-only

    def _pick_out_dir(self):
        d = filedialog.askdirectory(title="Pasta de saída (opcional)", initialdir=os.getcwd())
        if d:
            self.var_out_dir.set(d)

    def _open_output_folder(self):
        if self._last_outputs:
            open_in_explorer(self._last_outputs[-1])
        elif self.var_out_dir.get().strip():
            open_in_explorer(Path(self.var_out_dir.get().strip()))
        else:
            messagebox.showinfo("Abrir pasta", "Nenhuma saída gerada ainda.")

    def _on_toggle_pipes(self, *_):
        self._refresh_db_badges()

    def _refresh_db_badges(self):
        liq_needed = self.var_liq.get()
        tax_arbi_needed = self.var_tax_arbi.get()
        pipe_taxas_needed = self.var_pipe_taxas.get()
        amort_needed = self.var_amort.get()  # === AMORTIZAÇÃO ===

        ok_liq = (not liq_needed) or file_exists_here(DB_LIQ)
        ok_tax_arbi = (not tax_arbi_needed) or file_exists_here(DB_TAX_ARBI)

        for w in self.badges_frame.winfo_children():
            w.destroy()

        if liq_needed:
            self._badge(self.badges_frame, DB_LIQ, ok_liq).pack(side="left", padx=(0, 6))
        if tax_arbi_needed:
            self._badge(self.badges_frame, DB_TAX_ARBI, ok_tax_arbi).pack(side="left", padx=(0, 6))
        # Amortização não exige base adicional

    def _init_pipefy_filter(self):
        """
        Inicializa o movecards automático do Pipefy em background
        Roda imediatamente e depois a cada 3 minutos
        """
        def run_movecards():
            try:
                if move_cards:
                    self._add_log("🔄 MOVECARDS: Executando movimentação automática...")
                    
                    # Executa a função filtrar_cards_triagem do módulo movecards
                    # Ela já faz toda a lógica de filtrar e mover os cards
                    result = move_cards.filtrar_cards_triagem()
                    
                    if result:
                        movidos = len(result.get('cards_movidos', []))
                        bloqueados = len(result.get('cards_bloqueados', []))
                        self._add_log(f"✅ MOVECARDS: {movidos} movidos | {bloqueados} bloqueados")
                    else:
                        self._add_log("⚠️ MOVECARDS: Nenhum resultado retornado")
                else:
                    self._add_log("⚠️ MOVECARDS: Módulo não disponível")
                
                # Agenda próxima execução em 3 minutos (180000 ms)
                self.root.after(180000, run_movecards)
                    
            except Exception as e:
                self._add_log(f"❌ MOVECARDS: Erro - {e}")
                # Em caso de erro, tenta novamente em 3 minutos (180000 ms)
                self.root.after(180000, run_movecards)
        
        # Log inicial
        self._add_log("🚀 MOVECARDS: Sistema de movimentação automática iniciado")
        
        # Inicia primeira execução imediatamente (após 5 segundos para UI carregar)
        self.root.after(5000, run_movecards)

        if self.var_liq.get() or self.var_tax_arbi.get() or self.var_pipe_taxas.get() or self.var_amort.get():
            ttk.Label(self.badges_frame, text="Deixe os bancos na MESMA pasta do launcher.", foreground="#666") \
                .pack(side="left")

    def _executar_via_api(self):
        """
        Executa a automação completa via API do Pipefy (gera arquivo + processa)
        """
        if auto_pipe is None:
            messagebox.showerror("Erro", "Módulo auto_pipeliquidacao não está disponível!")
            return
        
        # Confirmar execução
        resposta = messagebox.askyesno(
            "Executar via API",
            "🚀 Executar automação completa?\n\n"
            "• Buscar dados via API do Pipefy\n"
            "• Gerar arquivo Excel automaticamente\n"
            "• Processar pipeliquidação\n"
            "• Usar datas individuais dos cards\n\n"
            "⚠️ Não é necessário selecionar arquivo de entrada!"
        )
        
        if not resposta:
            return
        
        # Executar em thread separada para não travar a UI
        def executar_thread():
            try:
                self._set_running(True)
                self._set_progress(5, "🚀 Iniciando automação via API...")
                self._add_log("🚀 INICIANDO AUTOMAÇÃO VIA API...")
                self._add_log("📊 Gerando arquivo Excel via API do Pipefy...")
                
                self._set_progress(20, "📅 Processando data...")
                
                # Obter a data do campo de entrada
                data_pagamento = self.var_dt.get().strip()
                if not data_pagamento:
                    self._add_log("⚠️ Data não informada, usando data de hoje")
                    data_pagamento = None
                else:
                    self._add_log(f"📅 Usando data: {data_pagamento}")
                
                self._set_progress(30, "📁 Verificando pasta de saída...")
                
                # Obter pasta de saída (se especificada)
                pasta_saida = self.var_out_dir.get().strip() or None
                
                self._set_progress(40, "🔄 Executando automação...")
                
                # Chamar a função main do auto_pipeliquidacao com a data e pasta
                sucesso = auto_pipe.main(data_pagamento, pasta_saida)
                
                self._set_progress(90, "📝 Finalizando processamento...")
                
                if sucesso:
                    self._set_progress(100, "✅ Automação concluída!")
                    self._add_log("✅ AUTOMAÇÃO CONCLUÍDA COM SUCESSO!")
                    if pasta_saida:
                        self._add_log(f"📁 Arquivos gerados em: {pasta_saida}")
                    else:
                        self._add_log("📁 Arquivos gerados em: Downloads")
                    messagebox.showinfo("Sucesso", "✅ Automação executada com sucesso!\nVerifique a pasta de saída.")
                else:
                    self._set_progress(100, "❌ Automação falhou!")
                    self._add_log("❌ AUTOMAÇÃO FALHOU!")
                    messagebox.showerror("Erro", "❌ Falha na automação.\nVerifique os logs para detalhes.")
                    
            except Exception as e:
                self._set_progress(100, "❌ Erro na automação!")
                self._add_log(f"❌ ERRO na automação: {e}")
                messagebox.showerror("Erro", f"❌ Erro na automação:\n{e}")
            finally:
                self._set_running(False)
        
        # Executar em thread
        threading.Thread(target=executar_thread, daemon=True).start()

    def _executar_taxas_via_api(self):
        """
        Executa a automação completa para Pipe Taxas via API do Pipefy
        """
        
        if auto_taxas is None:
            messagebox.showerror("Erro", "Módulo auto_pipetaxas não está disponível!")
            return
        
        # Confirmar execução
        resposta = messagebox.askyesno(
            "Confirmar Automação", 
            "🤖 AUTOMAÇÃO PIPE TAXAS VIA API\n\n"
            "Esta automação irá:\n"
            "• Gerar arquivo Excel via API do Pipefy\n"
            "• Processar automaticamente via PipeTaxas\n"
            "• Usar a data informada no campo\n\n"
            "Deseja continuar?"
        )
        
        if not resposta:
            return
        
        def executar_thread():
            try:
                self._set_running(True)
                self._set_progress(5, "🚀 Iniciando automação de taxas...")
                self._add_log("🚀 INICIANDO AUTOMAÇÃO TAXAS VIA API...")
                self._add_log("📊 Gerando arquivo Excel via API do Pipefy...")
                
                self._set_progress(20, "📅 Processando data...")
                
                # Obter a data do campo de entrada
                data_pagamento = self.var_dt.get().strip()
                if not data_pagamento:
                    self._add_log("⚠️ Data não informada, usando data de hoje")
                    data_pagamento = None
                else:
                    self._add_log(f"📅 Usando data: {data_pagamento}")
                
                self._set_progress(40, "🔄 Executando automação de taxas...")
                
                # Chamar a função main do auto_pipetaxas com a data
                sucesso = auto_taxas.main(data_pagamento)
                
                self._set_progress(90, "📝 Finalizando processamento...")
                
                if sucesso:
                    self._set_progress(100, "✅ Automação de taxas concluída!")
                    self._add_log("✅ AUTOMAÇÃO TAXAS CONCLUÍDA COM SUCESSO!")
                    self._add_log("📁 Arquivos gerados na pasta do projeto")
                    messagebox.showinfo("Sucesso", "✅ Automação de taxas executada com sucesso!\nVerifique a pasta do projeto.")
                else:
                    self._set_progress(100, "❌ Automação de taxas falhou!")
                    self._add_log("❌ AUTOMAÇÃO TAXAS FALHOU!")
                    messagebox.showerror("Erro", "❌ Falha na automação de taxas.\nVerifique os logs para detalhes.")
                    
            except Exception as e:
                self._set_progress(100, "❌ Erro na automação de taxas!")
                self._add_log(f"❌ ERRO na automação de taxas: {e}")
                messagebox.showerror("Erro", f"❌ Erro na automação de taxas:\n{e}")
            finally:
                self._set_running(False)
        
        # Executar em thread
        threading.Thread(target=executar_thread, daemon=True).start()

    def _executar_amort_via_api(self):
        """
        Executa a automação completa para Amortização via API do Pipefy
        """
        
        if auto_amort is None:
            messagebox.showerror("Erro", "Módulo auto_amortizacao não está disponível!")
            return
        
        def executar_thread():
            try:
                self._set_running(True)
                self._add_log("🚀 INICIANDO AUTOMAÇÃO AMORTIZAÇÃO VIA API...")
                self._add_log("📊 Gerando arquivo Excel via API do Pipefy...")
                
                # Obter a data do campo de entrada
                data_pagamento = self.var_dt.get().strip()
                if not data_pagamento:
                    self._add_log("⚠️ Data não informada, usando data de hoje")
                    data_pagamento = None
                else:
                    self._add_log(f"📅 Usando data: {data_pagamento}")
                
                # Obter pasta de saída (opcional)
                pasta_saida = self.var_pasta_saida.get().strip() or None
                if pasta_saida:
                    self._add_log(f"📁 Pasta de saída: {pasta_saida}")
                
                # Chamar a função main do auto_amortizacao com a data e pasta
                self._add_log("🔄 Chamando auto_amortizacao.main()...")
                sucesso = auto_amort.main(data_pagamento, pasta_saida)
                
                if sucesso:
                    self._add_log("✅ AUTOMAÇÃO AMORTIZAÇÃO CONCLUÍDA COM SUCESSO!")
                    self._add_log("📁 Arquivos gerados na pasta do projeto")
                    messagebox.showinfo("Sucesso", "✅ Automação de amortização executada com sucesso!\nVerifique a pasta do projeto.")
                else:
                    self._add_log("❌ AUTOMAÇÃO AMORTIZAÇÃO FALHOU!")
                    messagebox.showerror("Erro", "❌ Falha na automação de amortização.\nVerifique os logs para detalhes.")
                    
            except Exception as e:
                import traceback
                erro_completo = traceback.format_exc()
                self._add_log(f"❌ ERRO na automação de amortização: {e}")
                self._add_log(f"📋 Traceback completo:\n{erro_completo}")
                messagebox.showerror("Erro", f"❌ Erro na automação de amortização:\n{e}")
            finally:
                self._set_running(False)
        
        # Executar em thread
        threading.Thread(target=executar_thread, daemon=True).start()

    def _mover_cards_2a_aprovacao(self):
        """
        Move cards da fase 2ª Aprovação para Aguardando Comprovante,
        preenchendo automaticamente o banco baseado no fundo
        """
        
        if mover_2a is None:
            messagebox.showerror("Erro", "Módulo mover_2a_aprovacao não está disponível!")
            return
        
        # Confirmar execução
        resposta = messagebox.askyesno(
            "Mover Cards - 2ª Aprovação", 
            "� AUTOMAÇÃO DE MOVIMENTAÇÃO DE CARDS\n\n"
            "Esta automação irá mover automaticamente os cards da fase '2ª Aprovação' para 'Aguardando comprovante' com o banco preenchido.\n\n"
            "💡 Cards sem fundo cadastrado serão ignorados.\n\n"
            "Deseja continuar?"
        )
        
        if not resposta:
            return
        
        def executar_thread():
            try:
                self._set_running(True)
                self._set_progress(5, "🚀 Iniciando movimentação de cards...")
                self._add_log("🚀 INICIANDO MOVIMENTAÇÃO DE CARDS...")
                self._add_log("📋 Fase origem: 2ª Aprovação [Liquidação]")
                self._add_log("📋 Fase destino: Aguardando comprovante")
                self._add_log("")
                
                self._set_progress(15, "🔍 Buscando cards...")
                
                # Chamar a função main do mover_2a_aprovacao
                resultado = mover_2a.main()
                
                self._set_progress(95, "📊 Processando resultados...")
                
                # Processar resultado
                if resultado:
                    movidos = resultado.get('movidos', 0)
                    ignorados = resultado.get('ignorados', 0)
                    erros = resultado.get('erros', 0)
                    
                    self._add_log("")
                    self._add_log("=" * 50)
                    self._add_log("📊 RESUMO DA MOVIMENTAÇÃO")
                    self._add_log("=" * 50)
                    self._add_log(f"✅ Cards movidos com sucesso: {movidos}")
                    if ignorados > 0:
                        self._add_log(f"⚠️ Cards ignorados (sem fundo): {ignorados}")
                    if erros > 0:
                        self._add_log(f"❌ Erros encontrados: {erros}")
                    self._add_log("=" * 50)
                    
                    self._set_progress(100, "✅ Movimentação concluída!")
                    
                    if movidos > 0:
                        messagebox.showinfo(
                            "Sucesso", 
                            f"✅ Movimentação concluída!\n\n"
                            f"Cards movidos: {movidos}\n"
                            f"Cards ignorados: {ignorados}\n"
                            f"Erros: {erros}"
                        )
                    else:
                        messagebox.showwarning(
                            "Atenção", 
                            f"⚠️ Nenhum card foi movido.\n\n"
                            f"Cards ignorados: {ignorados}\n"
                            f"Erros: {erros}\n\n"
                            f"Verifique se há cards na fase '2ª Aprovação'"
                        )
                else:
                    self._set_progress(100, "❌ Movimentação falhou!")
                    self._add_log("❌ MOVIMENTAÇÃO FALHOU!")
                    messagebox.showerror("Erro", "❌ Falha na movimentação de cards.\nVerifique os logs para detalhes.")
                    
            except Exception as e:
                self._set_progress(100, "❌ Erro na movimentação!")
                self._add_log(f"❌ ERRO na movimentação: {e}")
                messagebox.showerror("Erro", f"❌ Erro na movimentação de cards:\n{e}")
            finally:
                self._set_running(False)
        
        # Executar em thread
        threading.Thread(target=executar_thread, daemon=True).start()

    def _executar_selecionados_via_api(self):
        """
        Executa TODOS os pipes marcados via API (sem arquivo de entrada)
        """
        run_liq = self.var_liq.get()
        run_pipe_taxas = self.var_pipe_taxas.get()
        run_taxas_anbima = self.var_taxas_anbima.get()
        run_amort = self.var_amort.get()
        
        if not (run_liq or run_pipe_taxas or run_taxas_anbima or run_amort):
            messagebox.showwarning("Atenção", "Marque pelo menos um pipe para executar via API.")
            return
        
        # Montar lista de pipes que serão executados
        pipes_selecionados = []
        if run_liq:
            pipes_selecionados.append("Liquidação")
        if run_pipe_taxas:
            pipes_selecionados.append("Pipe Taxas")
        if run_taxas_anbima:
            pipes_selecionados.append("Taxas Anbima")
        if run_amort:
            pipes_selecionados.append("Amortização")
        
        # Executar em thread separada
        def executar_thread():
            try:
                self._set_running(True)
                self._set_progress(5, "🚀 Iniciando execução via API...")
                self.log_text.configure(state="normal")
                self.log_text.delete("1.0", "end")
                
                self._add_log("=" * 60)
                self._add_log("🚀 EXECUÇÃO VIA API INICIADA")
                self._add_log("=" * 60)
                
                self._set_progress(10, "📅 Processando configurações...")
                
                data_pagamento = self.var_dt.get().strip() or None
                if data_pagamento:
                    self._add_log(f"📅 Data informada: {data_pagamento}")
                else:
                    self._add_log("📅 Usando data atual")
                
                self._add_log("")
                
                sucessos = 0
                falhas = 0
                erros_detalhados = []  # 📋 Lista para capturar erros específicos
                total_pipes = sum([run_liq, run_pipe_taxas, run_taxas_anbima, run_amort])
                pipe_atual = 0
                
                # Executar Liquidação via API
                if run_liq:
                    pipe_atual += 1
                    progresso = 20 + (pipe_atual - 1) * (70 // total_pipes)
                    self._set_progress(progresso, f"📋 Processando Liquidação ({pipe_atual}/{total_pipes})")
                    
                    self._add_log("─" * 60)
                    self._add_log("📋 PIPE DE LIQUIDAÇÃO")
                    self._add_log("─" * 60)
                    
                    if auto_pipe is None:
                        erro_msg = "Módulo auto_pipeliquidacao não disponível"
                        self._add_log(f"❌ {erro_msg}")
                        erros_detalhados.append(f"LIQUIDAÇÃO: {erro_msg}")
                        falhas += 1
                    else:
                        try:
                            self._add_log("🚀 Iniciando processamento...")
                            # Obter pasta de saída
                            pasta_saida = self.var_out_dir.get().strip() or None
                            self._add_log(f"📁 Pasta de saída: {pasta_saida or 'Downloads (padrão)'}")
                            
                            sucesso = auto_pipe.main(data_pagamento, pasta_saida)
                            
                            if sucesso:
                                self._add_log("✅ LIQUIDAÇÃO CONCLUÍDA COM SUCESSO!")
                                sucessos += 1
                            else:
                                erro_msg = "Processamento retornou False - verifique logs do módulo"
                                self._add_log(f"❌ LIQUIDAÇÃO FALHOU! {erro_msg}")
                                erros_detalhados.append(f"LIQUIDAÇÃO: {erro_msg}")
                                falhas += 1
                        except Exception as e:
                            erro_msg = f"Exceção durante execução: {str(e)}"
                            self._add_log(f"❌ ERRO LIQUIDAÇÃO: {erro_msg}")
                            erros_detalhados.append(f"LIQUIDAÇÃO: {erro_msg}")
                            falhas += 1
                    
                    self._add_log("")
                
                # Executar Pipe Taxas via API
                if run_pipe_taxas:
                    pipe_atual += 1
                    progresso = 20 + (pipe_atual - 1) * (70 // total_pipes)
                    self._set_progress(progresso, f"📋 Processando Pipe Taxas ({pipe_atual}/{total_pipes})")
                    
                    self._add_log("─" * 60)
                    self._add_log("📋 PIPE TAXAS")
                    self._add_log("─" * 60)
                    
                    if auto_taxas is None:
                        erro_msg = "Módulo auto_pipetaxas não disponível"
                        self._add_log(f"❌ {erro_msg}")
                        erros_detalhados.append(f"PIPE TAXAS: {erro_msg}")
                        falhas += 1
                    else:
                        try:
                            self._add_log("🚀 Iniciando processamento...")
                            # Obter pasta de saída
                            pasta_saida = self.var_out_dir.get().strip() or None
                            self._add_log(f"📁 Pasta de saída: {pasta_saida or 'Downloads (padrão)'}")
                            
                            sucesso = auto_taxas.main(data_pagamento, pasta_saida)
                            
                            if sucesso:
                                self._add_log("✅ PIPE TAXAS CONCLUÍDO COM SUCESSO!")
                                sucessos += 1
                            else:
                                erro_msg = "Processamento retornou False - verifique logs do módulo"
                                self._add_log(f"❌ PIPE TAXAS FALHOU! {erro_msg}")
                                erros_detalhados.append(f"PIPE TAXAS: {erro_msg}")
                                falhas += 1
                        except Exception as e:
                            erro_msg = f"Exceção durante execução: {str(e)}"
                            self._add_log(f"❌ ERRO PIPE TAXAS: {erro_msg}")
                            erros_detalhados.append(f"PIPE TAXAS: {erro_msg}")
                            falhas += 1
                    
                    self._add_log("")
                
                # Executar Taxas Anbima via API
                if run_taxas_anbima:
                    pipe_atual += 1
                    progresso = 20 + (pipe_atual - 1) * (70 // total_pipes)
                    self._set_progress(progresso, f"📋 Processando Taxas Anbima ({pipe_atual}/{total_pipes})")
                    
                    self._add_log("─" * 60)
                    self._add_log("📋 TAXAS ANBIMA")
                    self._add_log("─" * 60)
                    
                    if auto_taxas_anbima is None:
                        erro_msg = "Módulo auto_taxasanbima não disponível"
                        self._add_log(f"❌ {erro_msg}")
                        erros_detalhados.append(f"TAXAS ANBIMA: {erro_msg}")
                        falhas += 1
                    else:
                        try:
                            self._add_log("🚀 Iniciando processamento...")
                            # Obter pasta de saída
                            pasta_saida = self.var_out_dir.get().strip() or None
                            self._add_log(f"📁 Pasta de saída: {pasta_saida or 'Downloads (padrão)'}")
                            
                            sucesso = auto_taxas_anbima.main(data_pagamento, pasta_saida)
                            
                            if sucesso:
                                self._add_log("✅ TAXAS ANBIMA CONCLUÍDO COM SUCESSO!")
                                sucessos += 1
                            else:
                                erro_msg = "Processamento retornou False - verifique logs do módulo"
                                self._add_log(f"❌ TAXAS ANBIMA FALHOU! {erro_msg}")
                                erros_detalhados.append(f"TAXAS ANBIMA: {erro_msg}")
                                falhas += 1
                        except Exception as e:
                            erro_msg = f"Exceção durante execução: {str(e)}"
                            self._add_log(f"❌ ERRO TAXAS ANBIMA: {erro_msg}")
                            erros_detalhados.append(f"TAXAS ANBIMA: {erro_msg}")
                            falhas += 1
                    
                    self._add_log("")
                
                # Executar Amortização via API
                if run_amort:
                    pipe_atual += 1
                    progresso = 20 + (pipe_atual - 1) * (70 // total_pipes)
                    self._set_progress(progresso, f"📋 Processando Amortização ({pipe_atual}/{total_pipes})")
                    
                    self._add_log("─" * 60)
                    self._add_log("📋 AMORTIZAÇÃO")
                    self._add_log("─" * 60)
                    
                    if auto_amort is None:
                        erro_msg = "Módulo auto_amortizacao não disponível"
                        self._add_log(f"❌ {erro_msg}")
                        erros_detalhados.append(f"AMORTIZAÇÃO: {erro_msg}")
                        falhas += 1
                    else:
                        try:
                            self._add_log("🚀 Iniciando processamento...")
                            pasta_saida = self.var_out_dir.get().strip() or None
                            self._add_log(f"📁 Pasta de saída: {pasta_saida or 'Downloads (padrão)'}")
                            
                            sucesso = auto_amort.main(data_pagamento, pasta_saida)
                            
                            if sucesso:
                                self._add_log("✅ AMORTIZAÇÃO CONCLUÍDA COM SUCESSO!")
                                sucessos += 1
                            else:
                                erro_msg = "Processamento retornou False - verifique logs do módulo"
                                self._add_log(f"❌ AMORTIZAÇÃO FALHOU! {erro_msg}")
                                erros_detalhados.append(f"AMORTIZAÇÃO: {erro_msg}")
                                falhas += 1
                        except Exception as e:
                            erro_msg = f"Exceção durante execução: {str(e)}"
                            self._add_log(f"❌ ERRO AMORTIZAÇÃO: {erro_msg}")
                            erros_detalhados.append(f"AMORTIZAÇÃO: {erro_msg}")
                            falhas += 1
                    
                    self._add_log("")
                
                # Resumo final
                self._set_progress(95, "📊 Gerando resumo final...")
                
                self._add_log("=" * 60)
                self._add_log("📊 RESUMO DA EXECUÇÃO")
                self._add_log("=" * 60)
                self._add_log(f"✅ Sucessos: {sucessos}")
                self._add_log(f"❌ Falhas: {falhas}")
                self._add_log(f"📋 Total: {sucessos + falhas}")
                
                # 📋 Mostrar erros específicos se houver falhas
                if erros_detalhados:
                    self._add_log("")
                    self._add_log("🔍 DETALHES DOS ERROS:")
                    self._add_log("─" * 40)
                    for i, erro in enumerate(erros_detalhados, 1):
                        self._add_log(f"{i}. {erro}")
                    self._add_log("─" * 40)
                
                # Informar pasta de saída
                pasta_saida = self.var_out_dir.get().strip()
                if pasta_saida:
                    self._add_log(f"📁 Pasta de saída: {pasta_saida}")
                else:
                    import os
                    downloads = os.path.join(os.path.expanduser("~"), "Downloads")
                    self._add_log(f"📁 Pasta de saída: {downloads} (padrão)")
                
                self._add_log("=" * 60)
                
                self.log_text.configure(state="disabled")
                
                if falhas == 0:
                    self._set_progress(100, "✅ Execução concluída com sucesso!")
                    messagebox.showinfo("Concluído", f"✅ Execução via API concluída!\n\nTodos os {sucessos} pipe(s) foram processados com sucesso.")
                else:
                    self._set_progress(100, "⚠️ Execução concluída com erros!")
                    
                    # 🚨 Criar mensagem detalhada com os erros específicos
                    erro_detalhado = "\n".join([f"• {erro}" for erro in erros_detalhados[:3]])  # Máximo 3 erros
                    if len(erros_detalhados) > 3:
                        erro_detalhado += f"\n... e mais {len(erros_detalhados) - 3} erro(s)"
                    
                    messagebox.showwarning(
                        "Concluído com erros", 
                        f"⚠️ Execução via API concluída com problemas:\n\n"
                        f"✅ Sucessos: {sucessos}\n"
                        f"❌ Falhas: {falhas}\n\n"
                        f"🔍 PRINCIPAIS ERROS:\n{erro_detalhado}\n\n"
                        f"📋 Verifique os logs para detalhes completos."
                    )
                    
            except Exception as e:
                self._set_progress(100, "❌ Erro crítico!")
                erro_critico = f"Exceção não tratada na execução: {str(e)}"
                self._add_log(f"❌ ERRO CRÍTICO: {erro_critico}")
                self._add_log(f"🔍 Tipo do erro: {type(e).__name__}")
                
                # Tentar obter mais detalhes do erro
                import traceback
                traceback_info = traceback.format_exc()
                self._add_log("📋 Traceback completo:")
                for linha in traceback_info.split('\n')[-5:]:  # Últimas 5 linhas do traceback
                    if linha.strip():
                        self._add_log(f"   {linha}")
                
                messagebox.showerror(
                    "Erro Crítico", 
                    f"❌ Erro crítico na execução via API:\n\n"
                    f"🔍 Erro: {erro_critico}\n\n"
                    f"📋 Verifique os logs para o traceback completo."
                )
            finally:
                self._set_running(False)
        
        # Executar em thread
        threading.Thread(target=executar_thread, daemon=True).start()

    def _set_running(self, running: bool):
        state = "disabled" if running else "normal"
        for w in self.inputs_to_toggle:
            try:
                w.configure(state=state)
            except Exception:
                pass
        if running:
            self._set_progress(0)
            self.status_var.set("⚙️ Processando...")
        else:
            self._set_progress(0)
            self.status_var.set("✨ Pronto para executar")
            try:
                self.btn_open_out.configure(state=("normal" if (not running) else "disabled"))
            except Exception:
                pass

    def _set_progress(self, value: int, message: str = None):
        """Define o progresso da barra (0-100) e opcionalmente uma mensagem"""
        try:
            self.progress['value'] = max(0, min(100, value))
            self.progress_label.configure(text=f"{value}%")
            if message:
                self.status_var.set(message)
            self.root.update_idletasks()  # Atualiza a interface
        except Exception:
            pass

    def _increment_progress(self, increment: int, message: str = None):
        """Incrementa o progresso atual"""
        try:
            current = int(self.progress['value'])
            new_value = min(100, current + increment)
            self._set_progress(new_value, message)
        except Exception:
            pass

    def _run_selected_threaded(self):
        threading.Thread(target=self._run_selected_safe, daemon=True).start()

    def _run_selected_safe(self):
        try:
            self._set_running(True)
            self.log_text.configure(state="normal")
            self.log_text.delete("1.0", "end")

            run_liq = self.var_liq.get()
            run_tax_arbi = self.var_tax_arbi.get()
            run_pipe_taxas = self.var_pipe_taxas.get()
            run_amort = self.var_amort.get()

            if not (run_liq or run_tax_arbi or run_pipe_taxas or run_amort):
                messagebox.showwarning("Atenção", "Selecione pelo menos um pipe para rodar.")
                self.status_var.set("⚠️ Nenhum pipe selecionado")
                return

            # Validar presença dos bancos
            ok, faltando = validar_presenca_bancos(run_liq, run_tax_arbi, run_pipe_taxas, run_amort)
            if not ok:
                messagebox.showerror(
                    "Banco(s) ausente(s)",
                    "Os seguintes bancos não foram encontrados na mesma pasta do launcher:\n\n- " +
                    "\n- ".join(faltando) +
                    "\n\nColoque-os ao lado do launcher e tente novamente."
                )
                self.status_var.set("Bancos ausentes.")
                return

            data_ok = self._validar_data(self.var_dt.get().strip())
            out_dir = self.var_out_dir.get().strip() or ""

            relatorio_msgs: list[str] = []

            # LIQ
            if run_liq:
                in_liq = self.var_in_liq.get().strip()
                if not in_liq:
                    messagebox.showwarning("Entrada faltando", "Selecione o arquivo de entrada do Pipe de Liquidação.")
                    self.status_var.set("Entrada de Liquidação faltando.")
                    return
                in_liq_path = Path(in_liq)
                out_liq_path = self._montar_caminho_saida(out_dir, default_out_name("Liquidacao_Remessa"), in_liq_path)
                self.status_var.set("Rodando: Pipe de Liquidação…")
                info_liq = liq_core.run_liquidacao(
                    input_file=in_liq_path,
                    data_pagamento=data_ok,
                    saida_path=out_liq_path
                )
                if info_liq.get("saida_principal"):
                    self._last_outputs.append(Path(info_liq["saida_principal"]))
                if info_liq.get("nao_importados"):
                    self._last_outputs.append(Path(info_liq["nao_importados"]))

                relatorio_msgs.append(
                    "✅ Liquidação concluída:\n"
                    f" - Saída principal: {info_liq.get('saida_principal','')}\n"
                    f" - Não importados: {info_liq.get('nao_importados','')}\n"
                    f" - Total linhas: {info_liq.get('qtd_total',0)}\n"
                    f" - Não importados: {info_liq.get('qtd_nao_importados',0)}"
                )

            # TAXAS ARBI
            if run_tax_arbi:
                in_tax_arbi = self.var_in_tax_arbi.get().strip()
                if not in_tax_arbi:
                    messagebox.showwarning("Entrada faltando", "Selecione o arquivo de entrada do Pipe de Taxas ARBI.")
                    self.status_var.set("Entrada de Taxas ARBI faltando.")
                    return
                in_tax_arbi_path = Path(in_tax_arbi)
                out_tax_arbi_path = self._montar_caminho_saida(out_dir, default_out_name("TaxasArbi_Final"), in_tax_arbi_path)
                self.status_var.set("Rodando: Pipe de Taxas ARBI…")
                info_tax_arbi = taxas_arbi_core.run_taxas(
                    input_file=in_tax_arbi_path,
                    data_pagamento=data_ok,
                    saida_path=out_tax_arbi_path
                )
                if info_tax_arbi.get("saida_taxas_final"):
                    self._last_outputs.append(Path(info_tax_arbi["saida_taxas_final"]))
                if info_tax_arbi.get("saida_taxas_pendentes"):
                    self._last_outputs.append(Path(info_tax_arbi["saida_taxas_pendentes"]))

                resumo_arbi = [
                    "✅ Taxas ARBI concluído:",
                    f" - Final: {info_tax_arbi.get('saida_taxas_final','')}",
                ]
                pend = info_tax_arbi.get("saida_taxas_pendentes", "")
                if pend:
                    resumo_arbi.append(f" - Pendentes: {pend}")
                resumo_arbi.append(f" - Linhas OK: {info_tax_arbi.get('qtd_ok',0)} / {info_tax_arbi.get('qtd_total',0)}")
                resumo_arbi.append(f" - Pendentes: {info_tax_arbi.get('qtd_pendentes',0)}")
                relatorio_msgs.append("\n".join(resumo_arbi))

            # PIPE TAXAS (genérico)
            if run_pipe_taxas:
                in_pipe_taxas = self.var_in_pipe_taxas.get().strip()
                if not in_pipe_taxas:
                    messagebox.showwarning("Entrada faltando", "Selecione o arquivo de entrada do Pipe de Taxas.")
                    self.status_var.set("Entrada do Pipe Taxas faltando.")
                    return
                in_pipe_taxas_path = Path(in_pipe_taxas)
                out_pipe_taxas_path = self._montar_caminho_saida(out_dir, default_out_name("PipeTaxas_Final"), in_pipe_taxas_path)
                self.status_var.set("Rodando: Pipe de Taxas…")
                info_pipe_taxas = pipe_taxas_core.run_pipe_taxas(
                    input_file=in_pipe_taxas_path,
                    data_pagamento=data_ok,
                    saida_path=out_pipe_taxas_path
                )
                if info_pipe_taxas.get("saida_taxas_final"):
                    self._last_outputs.append(Path(info_pipe_taxas["saida_taxas_final"]))
                if info_pipe_taxas.get("saida_taxas_pendentes"):
                    self._last_outputs.append(Path(info_pipe_taxas["saida_taxas_pendentes"]))

                resumo_pipe = [
                    "✅ Pipe Taxas concluído:",
                    f" - Final: {info_pipe_taxas.get('saida_taxas_final','')}",
                ]
                pend2 = info_pipe_taxas.get("saida_taxas_pendentes", "")
                if pend2:
                    resumo_pipe.append(f" - Pendentes: {pend2}")
                resumo_pipe.append(f" - Linhas OK: {info_pipe_taxas.get('qtd_ok',0)} / {info_pipe_taxas.get('qtd_total',0)}")
                resumo_pipe.append(f" - Pendentes: {info_pipe_taxas.get('qtd_pendentes',0)}")
                relatorio_msgs.append("\n".join(resumo_pipe))

            # === AMORTIZAÇÃO ===
            if run_amort:
                in_amort = self.var_in_amort.get().strip()
                # Comentários removidos – apenas entrada principal Excel

                if not in_amort:
                    messagebox.showwarning("Entrada faltando", "Selecione o arquivo de entrada do Pipe de Amortização.")
                    self.status_var.set("Entrada de Amortização faltando.")
                    return

                in_amort_path = Path(in_amort)
                out_amort_path = self._montar_caminho_saida(out_dir, default_out_name("Amortizacao_Final", ext=".xlsx"), in_amort_path)

                self.status_var.set("Rodando: Pipe de Amortização…")
                info_amort = amort_core.run_amortizacao(
                    input_file=in_amort_path,
                    data_pagamento=data_ok,
                    saida_path=out_amort_path
                )

                if info_amort.get("csv"):
                    self._last_outputs.append(Path(info_amort["csv"]))
                if info_amort.get("xlsx"):
                    self._last_outputs.append(Path(info_amort["xlsx"]))

                resumo_amort = [
                    "✅ Amortização concluída:",
                    f" - CSV: {info_amort.get('csv','')}",
                    f" - XLSX: {info_amort.get('xlsx','')}",
                    f" - Linhas OK: {info_amort.get('ok',0)} / {info_amort.get('total_registros',0)}",
                    f" - Pendentes: {info_amort.get('pendentes',0)}",
                ]
                if info_amort.get("mensagem"):
                    resumo_amort.append(f" - Obs: {info_amort.get('mensagem')}")

                relatorio_msgs.append("\n".join(resumo_amort))

            final_msg = "\n\n".join(relatorio_msgs) if relatorio_msgs else "Concluído."
            self.log_text.insert("end", final_msg + "\n")
            self.log_text.configure(state="disabled")
            self.status_var.set("Finalizado.")
            messagebox.showinfo("Processo finalizado", final_msg)

        except Exception as e:
            self.status_var.set("Erro.")
            messagebox.showerror("Erro", f"Ocorreu um erro:\n{e}")
        finally:
            self._set_running(False)
            self._refresh_db_badges()

    def _clear_fields(self):
        self.var_in_liq.set("")
        self.var_in_tax_arbi.set("")
        self.var_in_pipe_taxas.set("")
        self.var_in_amort.set("")
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")
        self.status_var.set("✨ Pronto para executar")

    # ---------- construção da UI ----------
    def _build_ui(self):
        # Configurar estilos modernos
        style = ttk.Style()
        if not USING_BOOTSTRAP:
            try:
                style.theme_use("clam")
            except Exception:
                pass
        
        # Estilos personalizados
        style.configure("Card.TFrame", background="white", relief="flat")
        style.configure("Title.TLabel", font=("Segoe UI", 11, "bold"), foreground=COLORS['text_dark'])
        style.configure("Subtitle.TLabel", font=("Segoe UI", 9), foreground=COLORS['text_light'])
        style.configure("Primary.TButton", font=("Segoe UI", 10, "bold"))
        style.configure("Success.TButton", font=("Segoe UI", 10))
        
        # Configurar checkboxes maiores
        style.configure("Big.TCheckbutton", font=("Segoe UI", 10))

        root = self.root
        root.columnconfigure(0, weight=1)

        # Menu superior (Ajuda) - apenas se não estiver em aba
        if not self.is_in_tab:
            menubar = tk.Menu(root, bg=COLORS['bg_dark'], fg="white", activebackground=COLORS['primary'])
            root.config(menu=menubar)
            menu_help = tk.Menu(menubar, tearoff=0)
            menu_help.add_command(label="📖 Sobre", command=lambda: messagebox.showinfo(
                "Sobre", "🚀 Kanastra Pipe Launcher\n\nVersão: 3.0\nKanastra - Automação Financeira\n\n📧 Suporte: gustavo.prometti@kanastra.com.br\n\n© 2025 Kanastra"
            ))
            menubar.add_cascade(label="❓ Ajuda", menu=menu_help)

        # Header moderno
        self._header(root).grid(row=1, column=0, sticky="ew")

        # Badges bancos - Card moderno
        frm_req = tk.Frame(root, bg=COLORS['bg_light'])
        frm_req.grid(row=2, column=0, sticky="ew", padx=20, pady=(10, 8))
        
        badge_card = tk.Frame(frm_req, bg="white", relief="flat", bd=0)
        badge_card.pack(fill="x", pady=3)
        
        tk.Label(
            badge_card,
            text="📊 Status dos Bancos de Dados",
            font=("Segoe UI", 10, "bold"),
            fg=COLORS['text_dark'],
            bg="white"
        ).pack(anchor="w", padx=15, pady=(8, 4))
        
        self.badges_frame = tk.Frame(badge_card, bg="white")
        self.badges_frame.pack(anchor="w", padx=15, pady=(0, 8))

        # Painel principal com padding
        frm_main = tk.Frame(root, bg=COLORS['bg_light'])
        frm_main.grid(row=3, column=0, sticky="ew", padx=20)
        frm_main.columnconfigure(1, weight=1)

        # Esquerda: configurações - Card moderno
        opt = tk.Frame(frm_main, bg="white", relief="flat", bd=0)
        opt.grid(row=0, column=0, padx=(0, 15), sticky="nsw", pady=10)
        opt.columnconfigure(1, weight=1)
        
        # Título do card
        tk.Label(
            opt,
            text="⚙️ Configurações",
            font=("Segoe UI", 12, "bold"),
            fg=COLORS['text_dark'],
            bg="white"
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=20, pady=(15, 10))

        # Data de pagamento
        tk.Label(
            opt,
            text="📅 Data de pagamento",
            font=("Segoe UI", 9, "bold"),
            fg=COLORS['text_dark'],
            bg="white"
        ).grid(row=1, column=0, sticky="w", padx=(20, 10), pady=(8, 2))
        
        ent_dt = ttk.Entry(opt, width=20, textvariable=self.var_dt, font=("Segoe UI", 9))
        ent_dt.grid(row=2, column=0, columnspan=2, sticky="w", padx=(20, 20), pady=(0, 10))

        # Separador visual
        tk.Frame(opt, bg=COLORS['border'], height=1).grid(row=3, column=0, columnspan=2, sticky="ew", padx=20, pady=8)

        # Pipes a executar
        tk.Label(
            opt,
            text="🎯 Pipes a Executar",
            font=("Segoe UI", 9, "bold"),
            fg=COLORS['text_dark'],
            bg="white"
        ).grid(row=4, column=0, columnspan=2, sticky="w", padx=(20, 10), pady=(3, 3))
        
        # Instrução
        tk.Label(
            opt,
            text="💡 Marque os processos desejados",
            font=("Segoe UI", 8),
            fg=COLORS['primary'],
            bg="white"
        ).grid(row=5, column=0, columnspan=2, sticky="w", padx=(20, 10), pady=(0, 6))
        
        # Checkboxes com ícones
        chk_liq = ttk.Checkbutton(
            opt,
            text="💰 Pipe de Liquidação",
            variable=self.var_liq,
            command=self._on_toggle_pipes,
            style="Big.TCheckbutton"
        )
        chk_liq.grid(row=6, column=0, columnspan=2, sticky="w", padx=(20, 10), pady=3)
        
        chk_tax_arbi = ttk.Checkbutton(
            opt,
            text="📊 Pipe de Taxas ARBI",
            variable=self.var_tax_arbi,
            command=self._on_toggle_pipes,
            style="Big.TCheckbutton"
        )
        chk_tax_arbi.grid(row=7, column=0, columnspan=2, sticky="w", padx=(20, 10), pady=3)
        
        chk_pipe_taxas = ttk.Checkbutton(
            opt,
            text="💳 Pipe Taxas",
            variable=self.var_pipe_taxas,
            command=self._on_toggle_pipes,
            style="Big.TCheckbutton"
        )
        chk_pipe_taxas.grid(row=8, column=0, columnspan=2, sticky="w", padx=(20, 10), pady=3)
        
        chk_taxas_anbima = ttk.Checkbutton(
            opt,
            text="💰 Taxas Anbima",
            variable=self.var_taxas_anbima,
            command=self._on_toggle_pipes,
            style="Big.TCheckbutton"
        )
        chk_taxas_anbima.grid(row=9, column=0, columnspan=2, sticky="w", padx=(20, 10), pady=3)
        
        chk_amort = ttk.Checkbutton(
            opt,
            text="📈 Amortização",
            variable=self.var_amort,
            command=self._on_toggle_pipes,
            style="Big.TCheckbutton"
        )
        chk_amort.grid(row=10, column=0, columnspan=2, sticky="w", padx=(20, 10), pady=3)

        # Separador
        tk.Frame(opt, bg=COLORS['border'], height=1).grid(row=10, column=0, columnspan=2, sticky="ew", padx=20, pady=8)

        # Pasta de saída
        tk.Label(
            opt,
            text="📁 Pasta de Saída (opcional)",
            font=("Segoe UI", 9, "bold"),
            fg=COLORS['text_dark'],
            bg="white"
        ).grid(row=11, column=0, columnspan=2, sticky="w", padx=(20, 10), pady=(3, 3))
        
        ent_out = ttk.Entry(opt, width=38, textvariable=self.var_out_dir, font=("Segoe UI", 9))
        ent_out.grid(row=12, column=0, columnspan=2, sticky="we", padx=(20, 20), pady=(0, 3))
        
        btn_out = ttk.Button(opt, text="📂 Escolher Pasta", command=self._pick_out_dir)
        btn_out.grid(row=13, column=0, columnspan=2, sticky="w", padx=(20, 20), pady=(0, 12))

        # Direita: entradas - Card moderno
        inputs = tk.Frame(frm_main, bg="white", relief="flat", bd=0)
        inputs.grid(row=0, column=1, sticky="nsew", pady=10)
        inputs.columnconfigure(1, weight=1)
        
        # Título do card
        tk.Label(
            inputs,
            text="📂 Arquivos de Entrada",
            font=("Segoe UI", 12, "bold"),
            fg=COLORS['text_dark'],
            bg="white"
        ).grid(row=0, column=0, columnspan=3, sticky="w", padx=20, pady=(15, 5))
        
        tk.Label(
            inputs,
            text="Modo arquivo: selecione os arquivos Excel para processar",
            font=("Segoe UI", 9),
            fg=COLORS['text_light'],
            bg="white"
        ).grid(row=1, column=0, columnspan=3, sticky="w", padx=20, pady=(0, 15))

        # Entrada Liquidação
        tk.Label(
            inputs,
            text="💰 Liquidação",
            font=("Segoe UI", 9, "bold"),
            fg=COLORS['text_dark'],
            bg="white"
        ).grid(row=2, column=0, sticky="nw", padx=(20, 10), pady=(10, 5))
        
        ent_in_liq = ttk.Entry(inputs, width=70, textvariable=self.var_in_liq, font=("Segoe UI", 9))
        ent_in_liq.grid(row=2, column=1, sticky="ew", padx=(0, 10), pady=(10, 5))
        
        btn_in_liq = ttk.Button(inputs, text="📄 Escolher", command=self._pick_in_liq)
        btn_in_liq.grid(row=2, column=2, sticky="e", padx=(0, 20), pady=(10, 5))

        # Entrada Taxas ARBI
        tk.Label(
            inputs,
            text="📊 Taxas ARBI",
            font=("Segoe UI", 9, "bold"),
            fg=COLORS['text_dark'],
            bg="white"
        ).grid(row=3, column=0, sticky="nw", padx=(20, 10), pady=(10, 5))
        
        ent_in_tax_arbi = ttk.Entry(inputs, width=70, textvariable=self.var_in_tax_arbi, font=("Segoe UI", 9))
        ent_in_tax_arbi.grid(row=3, column=1, sticky="ew", padx=(0, 10), pady=(10, 5))
        
        btn_in_tax_arbi = ttk.Button(inputs, text="📄 Escolher", command=self._pick_in_tax_arbi)
        btn_in_tax_arbi.grid(row=3, column=2, sticky="e", padx=(0, 20), pady=(10, 5))

        # Entrada Pipe Taxas
        tk.Label(
            inputs,
            text="💳 Pipe Taxas",
            font=("Segoe UI", 9, "bold"),
            fg=COLORS['text_dark'],
            bg="white"
        ).grid(row=4, column=0, sticky="nw", padx=(20, 10), pady=(10, 5))
        
        ent_in_pipe_taxas = ttk.Entry(inputs, width=70, textvariable=self.var_in_pipe_taxas, font=("Segoe UI", 9))
        ent_in_pipe_taxas.grid(row=4, column=1, sticky="ew", padx=(0, 10), pady=(10, 5))
        
        btn_in_pipe_taxas = ttk.Button(inputs, text="📄 Escolher", command=self._pick_in_pipe_taxas)
        btn_in_pipe_taxas.grid(row=4, column=2, sticky="e", padx=(0, 20), pady=(10, 5))

        # Entrada Amortização
        tk.Label(
            inputs,
            text="📈 Amortização",
            font=("Segoe UI", 9, "bold"),
            fg=COLORS['text_dark'],
            bg="white"
        ).grid(row=5, column=0, sticky="nw", padx=(20, 10), pady=(10, 5))
        
        ent_in_amort = ttk.Entry(inputs, width=70, textvariable=self.var_in_amort, font=("Segoe UI", 9))
        ent_in_amort.grid(row=5, column=1, sticky="ew", padx=(0, 10), pady=(10, 5))
        
        btn_in_amort = ttk.Button(inputs, text="📄 Escolher", command=self._pick_in_amort)
        btn_in_amort.grid(row=5, column=2, sticky="e", padx=(0, 20), pady=(10, 5))

        # Separador visual
        tk.Frame(inputs, bg=COLORS['border'], height=1).grid(row=6, column=0, columnspan=3, sticky="ew", padx=20, pady=15)

        # === LOGS DE EXECUÇÃO === Dentro do card de entradas
        tk.Label(
            inputs,
            text="📋 Logs de Execução",
            font=("Segoe UI", 10, "bold"),
            fg=COLORS['text_dark'],
            bg="white"
        ).grid(row=7, column=0, columnspan=3, sticky="w", padx=20, pady=(3, 3))
        
        tk.Label(
            inputs,
            text="• Acompanhe o processamento em tempo real",
            font=("Segoe UI", 8),
            fg=COLORS['text_light'],
            bg="white"
        ).grid(row=8, column=0, columnspan=3, sticky="w", padx=20, pady=(0, 6))

        # Text widget com estilo aprimorado
        self.log_text = tk.Text(
            inputs,
            height=5,
            wrap="word",
            font=("Consolas", 9),
            bg="#f8f9fa",
            fg=COLORS['text_dark'],
            relief="solid",
            borderwidth=1,
            highlightthickness=0
        )
        self.log_text.grid(row=9, column=0, columnspan=2, sticky="ew", padx=20, pady=(0, 10))
        
        scr = ttk.Scrollbar(inputs, command=self.log_text.yview)
        scr.grid(row=9, column=2, sticky="ns", pady=(0, 10), padx=(0, 20))
        self.log_text.configure(yscrollcommand=scr.set)

        # Ações - Barra moderna com botões destacados
        frm_actions = tk.Frame(root, bg=COLORS['bg_light'])
        frm_actions.grid(row=4, column=0, sticky="ew", padx=20, pady=(5, 10))
        frm_actions.columnconfigure(0, weight=1)
        
        # Card para ações
        action_card = tk.Frame(frm_actions, bg="white", relief="flat", bd=0)
        action_card.pack(fill="x")
        
        action_inner = tk.Frame(action_card, bg="white")
        action_inner.pack(fill="x", padx=20, pady=10)
        action_inner.columnconfigure(0, weight=1)

        # Progress bar moderna com percentual
        self.progress = ttk.Progressbar(action_inner, mode="determinate", length=300, maximum=100)
        self.progress.grid(row=0, column=0, sticky="ew", padx=(0, 15))
        
        # Label para mostrar percentual
        self.progress_label = tk.Label(
            action_inner,
            text="0%",
            font=("Segoe UI", 8, "bold"),
            fg=COLORS['text_dark'],
            bg="white"
        )
        self.progress_label.grid(row=1, column=0, sticky="w", padx=(0, 15))

        # Botão abrir pasta
        self.btn_open_out = ttk.Button(
            action_inner,
            text="📁 Abrir Pasta",
            command=self._open_output_folder,
            state="disabled"
        )
        self.btn_open_out.grid(row=0, column=1, sticky="e", padx=(0, 10))

        # Botão Mover Cards 2a Aprovação - Destaque laranja
        btn_mover_2a = tk.Button(
            action_inner,
            text="📋 Mover 2ª Aprovação",
            command=self._mover_cards_2a_aprovacao,
            bg=COLORS['warning'],
            fg="white",
            font=("Segoe UI", 9, "bold"),
            padx=12,
            pady=6,
            relief="flat",
            cursor="hand2",
            activebackground="#d97706",
            activeforeground="white"
        )
        btn_mover_2a.grid(row=0, column=2, sticky="e", padx=(0, 10))

        # Botão Executar via API - Destaque azul
        btn_exec_api = tk.Button(
            action_inner,
            text="🌐 Executar via API",
            command=self._executar_selecionados_via_api,
            bg=COLORS['primary'],
            fg="white",
            font=("Segoe UI", 9, "bold"),
            padx=12,
            pady=6,
            relief="flat",
            cursor="hand2",
            activebackground=COLORS['primary_hover'],
            activeforeground="white"
        )
        btn_exec_api.grid(row=0, column=3, sticky="e", padx=(0, 10))

        # Botão Executar - Destaque verde
        btn_exec = tk.Button(
            action_inner,
            text="▶️ Executar",
            command=self._run_selected_threaded,
            bg=COLORS['success'],
            fg="white",
            font=("Segoe UI", 9, "bold"),
            padx=15,
            pady=6,
            relief="flat",
            cursor="hand2",
            activebackground="#059669",
            activeforeground="white"
        )
        btn_exec.grid(row=0, column=4, sticky="e")

        # Status - Barra moderna
        self.status_var = tk.StringVar(value="✨ Pronto para executar")
        status_bar = tk.Frame(root, bg=COLORS['bg_dark'], height=28)
        status_bar.grid(row=6, column=0, sticky="ew")
        status_bar.columnconfigure(0, weight=1)
        
        tk.Label(
            status_bar,
            textvariable=self.status_var,
            fg="white",
            bg=COLORS['bg_dark'],
            font=("Segoe UI", 9),
            anchor="w"
        ).grid(row=0, column=0, sticky="w", padx=20)

        # Rodapé - Barra de ferramentas
        frm_short = tk.Frame(root, bg="white", height=25)
        frm_short.grid(row=7, column=0, sticky="ew")
        
        footer_inner = tk.Frame(frm_short, bg="white")
        footer_inner.pack(fill="x", padx=20, pady=3)
        
        ttk.Button(
            footer_inner,
            text="�️ Limpar Campos",
            command=self._clear_fields
        ).pack(side="left", padx=(0, 15))
        
        tk.Label(
            footer_inner,
            text="💡 Executar via API busca do Pipefy • Executar processa arquivos locais",
            font=("Segoe UI", 8),
            fg=COLORS['text_light'],
            bg="white"
        ).pack(side="left")

        # Inputs que desabilitamos durante execução
        self.inputs_to_toggle = [
            # configs
            ent_dt, chk_liq, chk_tax_arbi, chk_pipe_taxas, chk_amort,
            ent_out, btn_out,
            # entradas
            ent_in_liq, btn_in_liq,
            ent_in_tax_arbi, btn_in_tax_arbi,
            ent_in_pipe_taxas, btn_in_pipe_taxas,
            ent_in_amort, btn_in_amort,
            # ações
            self.btn_open_out,
            btn_exec
        ]


# ----- fim da classe -----

# ===== INTEGRADOR CETIP =====
# Importar módulos CETIP
CETIP_DIR = Path(r"C:\Users\GustavoPrometti\OneDrive - Kanastra\Documentos\Kanastra\Projeto CETIP")
if CETIP_DIR.exists() and str(CETIP_DIR) not in sys.path:
    sys.path.insert(0, str(CETIP_DIR))

CETIP_AVAILABLE = False
try:
    import importlib.util
    spec = importlib.util.spec_from_file_location("integrador_cetip", CETIP_DIR / "integrador.py")
    if spec and spec.loader:
        integrador_cetip_module = importlib.util.module_from_spec(spec)
        sys.modules["integrador_cetip"] = integrador_cetip_module
        spec.loader.exec_module(integrador_cetip_module)
        CETIP_AVAILABLE = True
except Exception as e:
    print(f"⚠️ Aviso: Não foi possível importar integrador CETIP: {e}")
    integrador_cetip_module = None


class IntegracaoUnificada:
    """Launcher unificado com abas para Pipefy e CETIP"""
    
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Finance Automation - Kanastra")
        self.root.geometry("1200x900")
        self.root.minsize(1000, 750)
        self.root.configure(bg=COLORS['bg_light'])
        
        # Aplicar ícone
        self._apply_icon()
        
        # Criar notebook (abas)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Aba Pipefy
        self.pipefy_frame = tk.Frame(self.notebook, bg=COLORS['bg_light'])
        self.notebook.add(self.pipefy_frame, text="  🔄 Pipefy  ")
        
        # Aba CETIP
        self.cetip_frame = tk.Frame(self.notebook, bg=COLORS['bg_light'])
        self.notebook.add(self.cetip_frame, text="  🏦 CETIP  ")
        
        # Aba Anexar Comprovantes
        self.comprovantes_frame = tk.Frame(self.notebook, bg=COLORS['bg_light'])
        self.notebook.add(self.comprovantes_frame, text="  � Anexar Comprovantes  ")
        
        # Inicializar abas
        self._init_pipefy_tab()
        self._init_cetip_tab()
        self._init_comprovantes_tab()
        
    def _apply_icon(self):
        """Aplica ícone à janela"""
        try:
            data = base64.b64decode(_APP_ICON_PNG_B64)
            img = tk.PhotoImage(data=data)
            self.root.iconphoto(True, img)
            self._icon_img = img
        except Exception:
            pass
    
    def _init_pipefy_tab(self):
        """Inicializa aba Pipefy com o launcher original"""
        # Criar a aplicação Pipefy dentro do frame
        self.pipefy_app = LauncherApp(self.pipefy_frame, is_in_tab=True)
    
    def _init_cetip_tab(self):
        """Inicializa aba CETIP com o integrador CETIP"""
        if CETIP_AVAILABLE and integrador_cetip_module:
            try:
                # Configurar fundo do frame
                self.cetip_frame.configure(bg=COLORS['bg_light'])
                
                # Criar a aplicação CETIP dentro do frame
                # Nota: LauncherCETIP espera tk.Tk, mas funciona com Frame também
                # Precisamos evitar as configurações de janela
                original_title = getattr(self.cetip_frame, 'title', None)
                original_geometry = getattr(self.cetip_frame, 'geometry', None)
                original_config = self.cetip_frame.config
                
                # Monkey-patch temporário para evitar erros
                self.cetip_frame.title = lambda x: None
                self.cetip_frame.geometry = lambda x: None
                
                # Interceptar config para ignorar 'menu'
                def safe_config(**kwargs):
                    # Remove 'menu' dos kwargs pois Frame não suporta
                    kwargs.pop('menu', None)
                    if kwargs:  # Se ainda há outros parâmetros, aplica
                        original_config(**kwargs)
                
                self.cetip_frame.config = safe_config
                
                self.cetip_app = integrador_cetip_module.LauncherCETIP(self.cetip_frame)
                
                # Aplicar estilo Pipefy ao CETIP
                self._apply_pipefy_style_to_cetip()
                
                # Restaurar métodos originais
                self.cetip_frame.config = original_config
                if original_title:
                    self.cetip_frame.title = original_title
                if original_geometry:
                    self.cetip_frame.geometry = original_geometry
                    
            except Exception as e:
                import traceback
                error_details = traceback.format_exc()
                self._show_error_in_tab(self.cetip_frame, 
                    "Erro ao carregar CETIP", f"{str(e)}\n\n{error_details}")
        else:
            self._show_error_in_tab(self.cetip_frame, 
                "Módulo CETIP não disponível",
                f"Verifique se integrador.py está no diretório:\n{CETIP_DIR}")
    
    def _apply_pipefy_style_to_cetip(self):
        """Aplica o estilo visual do Pipefy ao launcher CETIP"""
        try:
            # Configurar estilo ttk
            style = ttk.Style()
            
            # Estilo dos LabelFrames
            style.configure("TLabelframe", 
                background=COLORS['bg_light'],
                borderwidth=1)
            style.configure("TLabelframe.Label",
                background=COLORS['bg_light'],
                foreground=COLORS['text_dark'],
                font=("Segoe UI", 10, "bold"))
            
            # Estilo dos Frames
            style.configure("TFrame",
                background=COLORS['bg_light'])
            
            # Estilo dos Labels
            style.configure("TLabel",
                background=COLORS['bg_light'],
                foreground=COLORS['text_dark'],
                font=("Segoe UI", 9))
            
            # Estilo dos Buttons com cor primária
            style.configure("Primary.TButton",
                font=("Segoe UI", 9, "bold"),
                padding=(12, 8))
            
            # Estilo dos Entry
            style.configure("TEntry",
                fieldbackground="white",
                borderwidth=1)
            
            # Estilo dos Checkbuttons
            style.configure("TCheckbutton",
                background=COLORS['bg_light'],
                foreground=COLORS['text_dark'],
                font=("Segoe UI", 9))
            
            # Estilo dos Radiobuttons
            style.configure("TRadiobutton",
                background=COLORS['bg_light'],
                foreground=COLORS['text_dark'],
                font=("Segoe UI", 9))
            
            # Aplicar cores nos widgets do CETIP recursivamente
            self._apply_colors_recursive(self.cetip_frame)
            
        except Exception as e:
            print(f"⚠️ Erro ao aplicar estilo Pipefy ao CETIP: {e}")
    
    def _apply_colors_recursive(self, widget):
        """Aplica cores recursivamente em todos os widgets"""
        try:
            # Configurar fundo do widget se possível
            if isinstance(widget, (tk.Frame, ttk.Frame, ttk.Labelframe)):
                try:
                    widget.configure(background=COLORS['bg_light'])
                except:
                    pass
            
            # Configurar Text widgets (área de log)
            if isinstance(widget, tk.Text):
                try:
                    widget.configure(
                        bg='white',
                        fg=COLORS['text_dark'],
                        font=("Consolas", 9),
                        relief=tk.FLAT,
                        borderwidth=1
                    )
                except:
                    pass
            
            # Configurar Labels
            if isinstance(widget, ttk.Label):
                try:
                    widget.configure(
                        background=COLORS['bg_light'],
                        foreground=COLORS['text_dark']
                    )
                except:
                    pass
            
            # Processar filhos
            for child in widget.winfo_children():
                self._apply_colors_recursive(child)
                
        except Exception:
            pass
    
    def _init_comprovantes_tab(self):
        """Inicializa aba Comprovantes"""
        # Container principal com scroll
        canvas = tk.Canvas(self.comprovantes_frame, bg=COLORS['bg_light'], highlightthickness=0)
        scrollbar = tk.Scrollbar(self.comprovantes_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=COLORS['bg_light'])
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        # Criar janela com largura que acompanha o canvas
        canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        
        # Configurar para expandir horizontalmente
        def configure_scroll_region(event):
            canvas.itemconfig(canvas_window, width=event.width)
        canvas.bind("<Configure>", configure_scroll_region)
        
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        container = tk.Frame(scrollable_frame, bg=COLORS['bg_light'])
        container.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # ========== HEADER MODERNO ==========
        header_frame = tk.Frame(container, bg="white", relief="flat", bd=0)
        header_frame.pack(fill=tk.X, pady=(0, 15))
        
        # Título sem ícone - mais profissional
        title_container = tk.Frame(header_frame, bg="white")
        title_container.pack(fill=tk.X, padx=20, pady=15)
        
        tk.Label(title_container, text="Anexar Comprovantes via API", 
                font=("Segoe UI", 18, "bold"),
                fg=COLORS['text_dark'], bg="white").pack(anchor=tk.W)
        
        tk.Label(title_container, 
                text="Busque e anexe comprovantes de pagamento automaticamente nos cards do Pipefy",
                font=("Segoe UI", 9),
                fg=COLORS['text_light'], bg="white").pack(anchor=tk.W, pady=(3,0))
        
        # Separador visual
        tk.Frame(header_frame, bg=COLORS['border'], height=1).pack(fill=tk.X, padx=20)
        
        # Flag de controle de execução
        self.comp_running = False
        
        # ========== LAYOUT HORIZONTAL: 2 COLUNAS ==========
        # Frame principal com grid para layout horizontal
        main_grid = tk.Frame(container, bg=COLORS['bg_light'])
        main_grid.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        main_grid.columnconfigure(0, weight=1)  # Coluna esquerda (buscar)
        main_grid.columnconfigure(1, weight=1)  # Coluna direita (pipefy)
        
        # ========== COLUNA ESQUERDA: BUSCAR COMPROVANTES ==========
        buscar_frame = tk.LabelFrame(main_grid, text="🔍 Buscar e Baixar Comprovantes", 
                                     bg="white", fg=COLORS['text_dark'],
                                     font=("Segoe UI", 9, "bold"), padx=15, pady=10)
        buscar_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        
        # Data
        data_row = tk.Frame(buscar_frame, bg="white")
        data_row.pack(fill=tk.X, pady=(0, 15))
        
        tk.Label(data_row, text="📅 Data:", font=("Segoe UI", 10, "bold"),
                fg=COLORS['text_dark'], bg="white").pack(side=tk.LEFT, padx=(0, 10))
        
        from datetime import date
        self.comp_data_var = tk.StringVar(value=date.today().strftime("%Y-%m-%d"))
        self.comp_data_entry = tk.Entry(data_row, textvariable=self.comp_data_var,
                                       font=("Segoe UI", 10), width=15)
        self.comp_data_entry.pack(side=tk.LEFT, padx=(0, 10))
        
        tk.Label(data_row, text="(formato: YYYY-MM-DD)", 
                font=("Segoe UI", 8, "italic"), fg=COLORS['text_light'], bg="white").pack(side=tk.LEFT)
        
        # Pasta de destino com estilo melhorado
        pasta_row = tk.Frame(buscar_frame, bg="white")
        pasta_row.pack(fill=tk.X, pady=(0, 15))
        
        tk.Label(pasta_row, text="📁 Pasta de Destino:", font=("Segoe UI", 10, "bold"),
                fg=COLORS['text_dark'], bg="white").pack(anchor=tk.W, pady=(0, 5))
        
        pasta_input_row = tk.Frame(pasta_row, bg="white")
        pasta_input_row.pack(fill=tk.X)
        
        self.comp_pasta_var = tk.StringVar(value=str(Path(__file__).parent / "Comprovantes"))
        self.comp_pasta_entry = tk.Entry(pasta_input_row, textvariable=self.comp_pasta_var,
                                        font=("Segoe UI", 9), bg="#f8f9fa", relief=tk.FLAT, bd=1)
        self.comp_pasta_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
        
        tk.Button(pasta_input_row, text="📂  Escolher", font=("Segoe UI", 9),
                 bg=COLORS['bg_medium'], fg=COLORS['text_dark'],
                 relief=tk.FLAT, padx=12, pady=6, cursor="hand2",
                 command=self._comp_selecionar_pasta).pack(side=tk.LEFT)
        
        # Fundos disponíveis com separador visual
        tk.Frame(buscar_frame, bg=COLORS['border'], height=1).pack(fill=tk.X, pady=15)
        
        fundos_label = tk.Label(buscar_frame, text="💼 Fundos Santander (seleção múltipla):", 
                               font=("Segoe UI", 10, "bold"),
                               fg=COLORS['text_dark'], bg="white")
        fundos_label.pack(anchor=tk.W, pady=(0, 8))
        
        # Importar lista de fundos
        try:
            from credenciais_bancos import SANTANDER_FUNDOS
            fundos_disponiveis = sorted(list(SANTANDER_FUNDOS.keys()))
        except:
            fundos_disponiveis = []
        
        # Campo de pesquisa com estilo melhorado
        search_container = tk.Frame(buscar_frame, bg="#f8f9fa", relief=tk.FLAT, bd=1)
        search_container.pack(fill=tk.X, pady=(0, 10))
        
        search_frame = tk.Frame(search_container, bg="#f8f9fa")
        search_frame.pack(fill=tk.X, padx=8, pady=6)
        
        tk.Label(search_frame, text="🔍", font=("Segoe UI", 11),
                bg="#f8f9fa").pack(side=tk.LEFT, padx=(0, 8))
        
        self.comp_search_var = tk.StringVar()
        self.comp_search_var.trace('w', lambda *args: self._comp_filtrar_fundos())
        
        search_entry = tk.Entry(search_frame, textvariable=self.comp_search_var,
                               font=("Segoe UI", 9),
                               bg="#f8f9fa", fg=COLORS['text_dark'],
                               relief=tk.FLAT, borderwidth=0)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        search_entry.insert(0, "")
        search_entry.bind("<FocusIn>", lambda e: search_entry.config(bg="white"))
        search_entry.bind("<FocusOut>", lambda e: search_entry.config(bg="#f8f9fa"))
        
        tk.Button(search_frame, text="✕", font=("Segoe UI", 9, "bold"),
                 bg="#f8f9fa", fg=COLORS['text_light'],
                 relief=tk.FLAT, padx=5, cursor="hand2", bd=0,
                 activebackground="#e5e7eb",
                 command=lambda: self.comp_search_var.set("")).pack(side=tk.LEFT, padx=(5, 0))
        
        # Armazenar lista completa de fundos para filtragem
        self.comp_fundos_completos = fundos_disponiveis
        
        # Frame para listbox com borda arredondada
        fundos_container = tk.Frame(buscar_frame, bg="white", relief=tk.FLAT, bd=1, highlightthickness=1, highlightbackground=COLORS['border'])
        fundos_container.pack(fill=tk.X, pady=(0, 8))
        
        # Scrollbar
        fundos_scrollbar = tk.Scrollbar(fundos_container)
        fundos_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Listbox com múltipla seleção
        self.comp_fundos_listbox = tk.Listbox(fundos_container,
                                              selectmode=tk.MULTIPLE,
                                              height=4,
                                              font=("Segoe UI", 9),
                                              bg="white",
                                              fg=COLORS['text_dark'],
                                              selectbackground=COLORS['primary'],
                                              selectforeground="white",
                                              relief=tk.FLAT,
                                              borderwidth=0,
                                              highlightthickness=0,
                                              yscrollcommand=fundos_scrollbar.set)
        self.comp_fundos_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=2, pady=2)
        fundos_scrollbar.config(command=self.comp_fundos_listbox.yview)
        
        # Adicionar fundos à listbox
        for fundo_id in fundos_disponiveis:
            self.comp_fundos_listbox.insert(tk.END, fundo_id)
        
        # Selecionar todos por padrão
        for i in range(len(fundos_disponiveis)):
            self.comp_fundos_listbox.selection_set(i)
        
        # Botões de seleção com estilo aprimorado
        btn_sel_frame = tk.Frame(buscar_frame, bg="white")
        btn_sel_frame.pack(fill=tk.X, pady=(8, 15))
        
        tk.Button(btn_sel_frame, text="✓  Selecionar Todos", font=("Segoe UI", 8),
                 bg="#e0f2fe", fg="#0369a1",
                 relief=tk.FLAT, padx=12, pady=4, cursor="hand2",
                 activebackground="#bae6fd",
                 command=lambda: self._comp_toggle_fundos(True)).pack(side=tk.LEFT, padx=(0, 5))
        
        tk.Button(btn_sel_frame, text="✕  Limpar Seleção", font=("Segoe UI", 8),
                 bg="#fee2e2", fg="#991b1b",
                 relief=tk.FLAT, padx=12, pady=4, cursor="hand2",
                 activebackground="#fecaca",
                 command=lambda: self._comp_toggle_fundos(False)).pack(side=tk.LEFT)
        
        # Hint de uso
        tk.Label(buscar_frame, text="💡 Use Ctrl+Click para seleção múltipla ou Shift+Click para intervalo", 
                font=("Segoe UI", 7, "italic"), fg=COLORS['text_light'], bg="white").pack(anchor=tk.W, pady=(0, 10))
        
        # Separador antes do botão
        tk.Frame(buscar_frame, bg=COLORS['border'], height=1).pack(fill=tk.X, pady=(5, 12))
        
        # Botão buscar com estilo melhorado
        btn_buscar_container = tk.Frame(buscar_frame, bg="white")
        btn_buscar_container.pack(fill=tk.X, pady=(0, 0))
        
        self.comp_buscar_btn = tk.Button(btn_buscar_container, text="🔍  Buscar Comprovantes",
                 font=("Segoe UI", 10, "bold"), bg=COLORS['success'], fg="white",
                 activebackground="#059669", activeforeground="white",
                 relief=tk.FLAT, padx=20, pady=12, cursor="hand2",
                 command=self._comp_buscar_comprovantes)
        self.comp_buscar_btn.pack(fill=tk.X)
        
        # ========== COLUNA DIREITA: PROCESSAR NO PIPEFY ==========
        pipefy_frame = tk.LabelFrame(main_grid, text="⚙️  Anexar no Pipefy", 
                                    bg="white", fg=COLORS['text_dark'],
                                    font=("Segoe UI", 9, "bold"), padx=15, pady=10)
        pipefy_frame.grid(row=0, column=1, sticky="nsew")
        
        # Seleção de pipes com estilo aprimorado
        tk.Label(pipefy_frame, text="Selecione os pipes para processar:", 
                font=("Segoe UI", 9), fg=COLORS['text_dark'], bg="white").pack(anchor=tk.W, pady=(0, 8))
        
        pipes_container = tk.Frame(pipefy_frame, bg="#f8f9fa", relief=tk.FLAT, bd=1)
        pipes_container.pack(fill=tk.X, pady=(0, 12))
        
        # Grid de checkboxes com estilo card
        pipes_grid = tk.Frame(pipes_container, bg="#f8f9fa")
        pipes_grid.pack(fill=tk.X, padx=10, pady=10)
        
        self.comp_var_liquidacao = tk.BooleanVar(value=True)
        self.comp_var_taxas = tk.BooleanVar(value=False)
        self.comp_var_taxas_anbima = tk.BooleanVar(value=False)
        
        # Checkboxes com fontes maiores e melhor espaçamento
        tk.Checkbutton(pipes_grid, text="💰 Pipe Liquidação", variable=self.comp_var_liquidacao,
                      font=("Segoe UI", 9, "bold"), bg="#f8f9fa", fg=COLORS['text_dark'],
                      activebackground="#f8f9fa", selectcolor="white").grid(row=0, column=0, sticky="w", padx=(0,15), pady=4)
        
        tk.Checkbutton(pipes_grid, text="📊 Pipe Taxas", variable=self.comp_var_taxas,
                      font=("Segoe UI", 9, "bold"), bg="#f8f9fa", fg=COLORS['text_dark'],
                      activebackground="#f8f9fa", selectcolor="white").grid(row=1, column=0, sticky="w", padx=(0,15), pady=4)
        
        tk.Checkbutton(pipes_grid, text="📈 Taxas Anbima", variable=self.comp_var_taxas_anbima,
                      font=("Segoe UI", 9), bg="#f8f9fa", fg=COLORS['text_light'],
                      activebackground="#f8f9fa", selectcolor="white", state=tk.DISABLED).grid(row=2, column=0, sticky="w", pady=4)
        
        tk.Label(pipes_grid, text="(em desenvolvimento)", 
                font=("Segoe UI", 7, "italic"), fg=COLORS['text_light'], bg="#f8f9fa").grid(row=2, column=1, sticky="w", padx=(5,0))
        
        # Data para buscar comprovantes
        tk.Label(pipefy_frame, text="Data dos comprovantes:", 
                font=("Segoe UI", 9), fg=COLORS['text_dark'], bg="white").pack(anchor=tk.W, pady=(0, 5))
        
        data_pipefy_row = tk.Frame(pipefy_frame, bg="white")
        data_pipefy_row.pack(fill=tk.X, pady=(0, 12))
        
        tk.Label(data_pipefy_row, text="📅", font=("Segoe UI", 10),
                bg="white").pack(side=tk.LEFT, padx=(0, 5))
        
        from datetime import date
        self.comp_pipefy_data_var = tk.StringVar(value=date.today().strftime("%Y-%m-%d"))
        self.comp_pipefy_data_entry = tk.Entry(data_pipefy_row, textvariable=self.comp_pipefy_data_var,
                                              font=("Segoe UI", 9), width=12, bg="lightyellow")
        self.comp_pipefy_data_entry.pack(side=tk.LEFT)
        
        tk.Label(data_pipefy_row, text="(formato: YYYY-MM-DD)", 
                font=("Segoe UI", 7), fg=COLORS['text_light'], bg="white").pack(side=tk.LEFT, padx=(5, 0))
        
        # Card de informações com fundo destacado
        info_card = tk.Frame(pipefy_frame, bg="#e0f2fe", relief=tk.FLAT, bd=1)
        info_card.pack(fill=tk.X, pady=(0, 15))
        
        info_inner = tk.Frame(info_card, bg="#e0f2fe")
        info_inner.pack(fill=tk.X, padx=10, pady=8)
        
        tk.Label(info_inner, text="ℹ️  Como funciona:", 
                font=("Segoe UI", 9, "bold"), fg="#0369a1", bg="#e0f2fe").pack(anchor=tk.W)
        
        tk.Label(info_inner, text="• Faz matching por VALOR e NOME do beneficiário", 
                font=("Segoe UI", 8), fg="#0c4a6e", bg="#e0f2fe").pack(anchor=tk.W, padx=(20, 0), pady=(2, 0))
        
        tk.Label(info_inner, text="• Anexa automaticamente ao card correspondente", 
                font=("Segoe UI", 8), fg="#0c4a6e", bg="#e0f2fe").pack(anchor=tk.W, padx=(20, 0))
        
        tk.Label(info_inner, text="• Move para fase \"Solicitação Paga\"", 
                font=("Segoe UI", 8), fg="#0c4a6e", bg="#e0f2fe").pack(anchor=tk.W, padx=(20, 0))
        
        # Botões com melhor visual
        btn_container = tk.Frame(pipefy_frame, bg="white")
        btn_container.pack(fill=tk.X)
        
        self.comp_process_btn = tk.Button(btn_container, text="▶  Anexar Comprovantes",
                 font=("Segoe UI", 10, "bold"), bg=COLORS['primary'], fg="white",
                 activebackground=COLORS['primary_hover'], activeforeground="white",
                 relief=tk.FLAT, padx=20, pady=12, cursor="hand2",
                 command=self._run_comprovantes)
        self.comp_process_btn.pack(fill=tk.X, pady=(0, 8))
        
        self.comp_test_btn = tk.Button(btn_container, text="🧪  Testar Matching (sem anexar)",
                 font=("Segoe UI", 9), bg=COLORS['bg_medium'], fg=COLORS['text_dark'],
                 activebackground=COLORS['bg_dark'], activeforeground="white",
                 relief=tk.FLAT, padx=15, pady=10, cursor="hand2",
                 command=self._test_matching)
        self.comp_test_btn.pack(fill=tk.X)
        
        # ========== SEÇÃO INFERIOR: LOGS E PROGRESSO (LARGURA TOTAL) ==========
        
        # Frame de progresso ocupa toda a largura
        progress_frame = tk.LabelFrame(container, text="📊 Status e Logs de Execução", 
                                      bg="white", fg=COLORS['text_dark'],
                                      font=("Segoe UI", 9, "bold"), padx=15, pady=10)
        progress_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Barra de progresso horizontal na parte superior
        progress_top = tk.Frame(progress_frame, bg="white")
        progress_top.pack(fill=tk.X, pady=(0, 6))
        
        self.comp_progress_label = tk.Label(progress_top, text="Aguardando execução...", 
                                           font=("Segoe UI", 8), fg=COLORS['text_dark'], bg="white")
        self.comp_progress_label.pack(side=tk.LEFT, padx=(0, 15))
        
        self.comp_progress_bar = ttk.Progressbar(progress_top, mode='indeterminate', length=400)
        self.comp_progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Texto de status com scroll - altura aumentada para melhor visualização
        status_scroll = tk.Scrollbar(progress_frame)
        status_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.comprovantes_status_text = tk.Text(progress_frame, height=6, 
                                               font=("Consolas", 8),
                                               bg="#f8f9fa", fg=COLORS['text_dark'],
                                               yscrollcommand=status_scroll.set,
                                               relief=tk.FLAT, padx=6, pady=6)
        self.comprovantes_status_text.pack(fill=tk.BOTH, expand=True)
        status_scroll.config(command=self.comprovantes_status_text.yview)
        
        self._comp_add_log("Aguardando execução...")
        self.comprovantes_status_text.config(state=tk.DISABLED)
        
        # Frame de botões gerais
        btn_frame = tk.Frame(container, bg=COLORS['bg_light'])
        btn_frame.pack(fill=tk.X)
        
        # Botão Abrir Pasta
        tk.Button(btn_frame, text="📁  Abrir Pasta",
                 font=("Segoe UI", 9), bg=COLORS['bg_medium'], fg=COLORS['text_dark'],
                 activebackground=COLORS['bg_dark'], activeforeground="white",
                 relief=tk.FLAT, padx=15, pady=10, cursor="hand2",
                 command=self._open_comprovantes_folder).pack(side=tk.LEFT, padx=(0, 10))
        
        # Botão Limpar Logs
        tk.Button(btn_frame, text="🗑️  Limpar Logs",
                 font=("Segoe UI", 9), bg=COLORS['bg_medium'], fg=COLORS['text_dark'],
                 activebackground=COLORS['bg_dark'], activeforeground="white",
                 relief=tk.FLAT, padx=15, pady=10, cursor="hand2",
                 command=self._comp_clear_logs).pack(side=tk.LEFT)
    
    def _comp_add_log(self, message):
        """Adiciona log com timestamp"""
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.comprovantes_status_text.config(state=tk.NORMAL)
        self.comprovantes_status_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.comprovantes_status_text.see(tk.END)
        self.comprovantes_status_text.config(state=tk.DISABLED)
        self.comprovantes_status_text.update_idletasks()
    
    def _comp_set_progress(self, message):
        """Atualiza mensagem de progresso"""
        self.comp_progress_label.config(text=message)
        self.comp_progress_label.update_idletasks()
    
    def _comp_clear_logs(self):
        """Limpa logs de execução"""
        self.comprovantes_status_text.config(state=tk.NORMAL)
        self.comprovantes_status_text.delete("1.0", tk.END)
        self._comp_add_log("Logs limpos")
        self.comprovantes_status_text.config(state=tk.DISABLED)
    
    def _comp_selecionar_pasta(self):
        """Abre dialog para selecionar pasta de destino"""
        from tkinter import filedialog
        pasta = filedialog.askdirectory(
            title="Selecionar pasta para salvar comprovantes",
            initialdir=self.comp_pasta_var.get()
        )
        if pasta:
            self.comp_pasta_var.set(pasta)
    
    def _comp_toggle_fundos(self, selecionar_todos):
        """Marca/desmarca todos os fundos na listbox"""
        self.comp_fundos_listbox.selection_clear(0, tk.END)
        if selecionar_todos:
            total_items = self.comp_fundos_listbox.size()
            for i in range(total_items):
                self.comp_fundos_listbox.selection_set(i)
    
    def _comp_filtrar_fundos(self):
        """Filtra fundos na listbox baseado no termo de busca"""
        termo = self.comp_search_var.get().upper()
        
        # Salvar seleções atuais
        selecoes_atuais = [self.comp_fundos_listbox.get(i) for i in self.comp_fundos_listbox.curselection()]
        
        # Limpar listbox
        self.comp_fundos_listbox.delete(0, tk.END)
        
        # Filtrar e adicionar fundos
        fundos_filtrados = [f for f in self.comp_fundos_completos if termo in f.upper()]
        
        for fundo in fundos_filtrados:
            self.comp_fundos_listbox.insert(tk.END, fundo)
            
            # Reselecionar se estava selecionado antes
            if fundo in selecoes_atuais:
                idx = fundos_filtrados.index(fundo)
                self.comp_fundos_listbox.selection_set(idx)
    
    def _comp_buscar_comprovantes(self):
        """Busca e baixa comprovantes do Santander"""
        # Verificar se já está executando
        if self.comp_running:
            messagebox.showwarning("Atenção", "⚠️ Já existe uma operação em andamento!\nAguarde a conclusão.")
            return
        
        try:
            from buscar_comprovantes_santander import SantanderComprovantes
            from credenciais_bancos import SantanderAuth
        except ImportError as e:
            messagebox.showerror("Erro", f"Módulo não disponível: {str(e)}")
            return
        
        # Validar seleção de fundos da listbox
        indices_selecionados = self.comp_fundos_listbox.curselection()
        if not indices_selecionados:
            messagebox.showwarning("Atenção", "Selecione pelo menos um fundo!")
            return
        
        fundos_selecionados = [self.comp_fundos_listbox.get(i) for i in indices_selecionados]
        
        # Validar data
        data_str = self.comp_data_var.get()
        try:
            from datetime import datetime
            data_obj = datetime.strptime(data_str, "%Y-%m-%d")
        except ValueError:
            messagebox.showerror("Erro", "Data inválida! Use o formato YYYY-MM-DD")
            return
        
        # Validar pasta
        pasta_destino = Path(self.comp_pasta_var.get())
        if not pasta_destino.exists():
            try:
                pasta_destino.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                messagebox.showerror("Erro", f"Não foi possível criar a pasta: {str(e)}")
                return
        
        # Limpar logs
        self.comprovantes_status_text.config(state=tk.NORMAL)
        self.comprovantes_status_text.delete("1.0", tk.END)
        self.comprovantes_status_text.config(state=tk.DISABLED)
        
        # Iniciar progresso
        self.comp_progress_bar.start(10)
        self._comp_set_progress(f"Buscando comprovantes de {len(fundos_selecionados)} fundo(s)...")
        
        # Desabilitar botões
        self.comp_running = True
        self.comp_buscar_btn.config(state=tk.DISABLED, bg=COLORS['bg_medium'])
        self.comp_process_btn.config(state=tk.DISABLED, bg=COLORS['bg_medium'])
        
        def run_thread():
            try:
                import sys
                class TextRedirector:
                    def __init__(self, widget):
                        self.widget = widget
                    def write(self, text):
                        self.widget.config(state=tk.NORMAL)
                        self.widget.insert(tk.END, text)
                        self.widget.see(tk.END)
                        self.widget.config(state=tk.DISABLED)
                        self.widget.update_idletasks()
                    def flush(self):
                        pass
                
                sys.stdout = TextRedirector(self.comprovantes_status_text)
                
                self._comp_add_log("="*60)
                self._comp_add_log("🔍 BUSCAR COMPROVANTES SANTANDER")
                self._comp_add_log("="*60)
                self._comp_add_log(f"📅 Data de referência: {data_str}")
                self._comp_add_log(f"📁 Pasta destino: {pasta_destino}")
                self._comp_add_log(f"💼 Fundos selecionados: {len(fundos_selecionados)}")
                self._comp_add_log("="*60)
                
                total_comprovantes = 0
                
                for idx, fundo_id in enumerate(fundos_selecionados, 1):
                    self._comp_set_progress(f"Processando {idx}/{len(fundos_selecionados)}: {fundo_id}")
                    self._comp_add_log(f"\n📊 [{idx}/{len(fundos_selecionados)}] Fundo: {fundo_id}")
                    self._comp_add_log("-"*60)
                    
                    try:
                        # Autenticar usando método correto
                        auth = SantanderAuth.criar_por_fundo(fundo_id)
                        santander = SantanderComprovantes(auth)
                        
                        # Alterar diretório de destino
                        santander.comprovantes_dir = pasta_destino
                        
                        # Buscar comprovantes
                        self._comp_add_log(f"🔎 Consultando API Santander (data: {data_str})...")
                        comprovantes = santander.listar_comprovantes(data_str, data_str)
                        receipts = comprovantes.get('paymentsReceipts', [])
                        
                        self._comp_add_log(f"✅ {len(receipts)} comprovante(s) encontrado(s)")
                        total_comprovantes += len(receipts)
                        
                        # Baixar cada comprovante
                        for receipt in receipts:
                            payment = receipt.get('payment', {})
                            payment_id = payment.get('paymentId', 'N/A')
                            
                            try:
                                pdf_path = santander.buscar_e_baixar_comprovante(payment_id, data_str)
                                if pdf_path:
                                    self._comp_add_log(f"  ✓ {payment_id}: {pdf_path}")
                            except Exception as e:
                                self._comp_add_log(f"  ✗ {payment_id}: Erro - {str(e)}")
                        
                    except Exception as e:
                        self._comp_add_log(f"❌ Erro no fundo {fundo_id}: {str(e)}")
                
                sys.stdout = sys.__stdout__
                
                self._comp_set_progress(f"✅ Concluído! {total_comprovantes} comprovante(s) baixado(s)")
                self._comp_add_log("\n" + "="*60)
                self._comp_add_log(f"✅ Busca finalizada! Total: {total_comprovantes} comprovante(s)")
                
            except Exception as e:
                sys.stdout = sys.__stdout__
                self._comp_set_progress("❌ Erro durante busca")
                self._comp_add_log(f"\n❌ Erro: {str(e)}")
                import traceback
                self._comp_add_log(f"\n{traceback.format_exc()}")
            
            finally:
                self.comp_progress_bar.stop()
                # Reabilitar botões
                self.comp_running = False
                self.comp_buscar_btn.config(state=tk.NORMAL, bg=COLORS['primary'])
                self.comp_process_btn.config(state=tk.NORMAL, bg=COLORS['primary'])
        
        thread = threading.Thread(target=run_thread, daemon=True)
        thread.start()
    
    def _run_comprovantes(self):
        """Executa processamento de comprovantes em thread separada"""
        # Verificar se já está executando
        if self.comp_running:
            messagebox.showwarning("Atenção", "⚠️ Já existe uma operação em andamento!\nAguarde a conclusão.")
            return
        
        # Validar seleção
        if not any([self.comp_var_liquidacao.get(), self.comp_var_taxas.get(), self.comp_var_taxas_anbima.get()]):
            messagebox.showwarning("Atenção", "Selecione pelo menos um pipe!")
            return
        
        if not comprovantes_pipe:
            messagebox.showerror("Erro", "Módulo Anexarcomprovantespipe não disponível!")
            return
        
        # Desabilitar botões
        self.comp_running = True
        self.comp_buscar_btn.config(state=tk.DISABLED, bg=COLORS['bg_medium'])
        self.comp_process_btn.config(state=tk.DISABLED, text="⏳ Processando...", bg=COLORS['bg_medium'])
        
        # Iniciar barra de progresso
        self.comp_progress_bar.start(10)
        self._comp_set_progress("Iniciando processamento...")
        
        # Limpar logs
        self.comprovantes_status_text.config(state=tk.NORMAL)
        self.comprovantes_status_text.delete("1.0", tk.END)
        self.comprovantes_status_text.config(state=tk.DISABLED)
        
        # Executar em thread
        def run_thread():
            try:
                # Redirecionar output para o widget de texto
                import sys
                
                class TextRedirector:
                    def __init__(self, widget):
                        self.widget = widget
                
                    def write(self, text):
                        self.widget.config(state=tk.NORMAL)
                        self.widget.insert(tk.END, text)
                        self.widget.see(tk.END)
                        self.widget.config(state=tk.DISABLED)
                        self.widget.update_idletasks()
                    
                    def flush(self):
                        pass
                
                # Redirecionar stdout
                sys.stdout = TextRedirector(self.comprovantes_status_text)
                
                # Processar pipes selecionados
                pipes_selecionados = []
                if self.comp_var_liquidacao.get():
                    pipes_selecionados.append("Liquidação")
                if self.comp_var_taxas.get():
                    pipes_selecionados.append("Taxas")
                if self.comp_var_taxas_anbima.get():
                    pipes_selecionados.append("Taxas Anbima")
                
                self._comp_add_log(f"🚀 Processando pipes: {', '.join(pipes_selecionados)}")
                self._comp_add_log("="*60)
                
                # Pegar data selecionada - COM DEBUG DETALHADO
                self._comp_add_log(f"🔍 VERIFICANDO CAMPO DE DATA...")
                self._comp_add_log(f"   Widget entry state: {self.comp_pipefy_data_entry['state']}")
                self._comp_add_log(f"   Widget entry existe: {self.comp_pipefy_data_entry.winfo_exists()}")
                
                valor_bruto = self.comp_pipefy_data_var.get()
                self._comp_add_log(f"   📋 Valor RAW da StringVar: '{valor_bruto}' (tipo: {type(valor_bruto).__name__}, len={len(valor_bruto)})")
                self._comp_add_log(f"   � Repr do valor: {repr(valor_bruto)}")
                
                data_busca_pipefy = valor_bruto.strip()
                self._comp_add_log(f"   📋 Após .strip(): '{data_busca_pipefy}' (len={len(data_busca_pipefy)})")
                
                # Converter string vazia para None
                if not data_busca_pipefy:
                    data_busca_pipefy = None
                    self._comp_add_log(f"   ⚠️  String vazia convertida para None")
                
                if data_busca_pipefy:
                    self._comp_add_log(f"📅 Data de referência para buscar comprovantes: {data_busca_pipefy}")
                else:
                    self._comp_add_log(f"📅 Data de referência: HOJE (data não especificada)")
                
                # Processar pipes selecionados
                if self.comp_var_liquidacao.get():
                    if not comprovantes_pipe:
                        self._comp_add_log("\n❌ Pipe LIQUIDAÇÃO: módulo não disponível")
                    else:
                        self._comp_set_progress("Processando Liquidação...")
                        self._comp_add_log("\n📊 Pipe: LIQUIDAÇÃO")
                        self._comp_add_log("-"*60)
                        self._comp_add_log(f"🔍 Buscando comprovantes com data de referência: {data_busca_pipefy if data_busca_pipefy else 'HOJE'}")
                        resultados_liq = comprovantes_pipe.processar_todos_cards(data_busca=data_busca_pipefy)
                        
                        # Log resumido para o launcher
                        if resultados_liq:
                            sucessos_liq = [r for r in resultados_liq if r['sucesso']]
                            if sucessos_liq:
                                self._comp_add_log(f"\n🎯 RESUMO PIPE LIQUIDAÇÃO: {len(sucessos_liq)} card(s) processado(s) com sucesso")
                                for r in sucessos_liq:
                                    self._comp_add_log(f"   ✅ {r['card_title']} → Solicitação Paga")
                
                if self.comp_var_taxas.get():
                    # Debug: mostrar status do módulo
                    if comprovantes_pipe_taxas is None:
                        self._comp_add_log("\n❌ Pipe TAXAS: módulo não disponível (comprovantes_pipe_taxas = None)")
                        self._comp_add_log("   Verifique o console/terminal para detalhes do erro de import")
                    elif not hasattr(comprovantes_pipe_taxas, 'processar_todos_cards'):
                        self._comp_add_log("\n❌ Pipe TAXAS: módulo carregado mas função processar_todos_cards não encontrada")
                    else:
                        self._comp_set_progress("Processando Taxas...")
                        self._comp_add_log("\n📊 Pipe: TAXAS")
                        self._comp_add_log("-"*60)
                        self._comp_add_log(f"🔍 Buscando comprovantes com data de referência: {data_busca_pipefy if data_busca_pipefy else 'HOJE'}")
                        resultados_taxas = comprovantes_pipe_taxas.processar_todos_cards(data_busca=data_busca_pipefy)
                        
                        # Log resumido para o launcher
                        if resultados_taxas:
                            sucessos_taxas = [r for r in resultados_taxas if r['sucesso']]
                            if sucessos_taxas:
                                self._comp_add_log(f"\n🎯 RESUMO PIPE TAXAS: {len(sucessos_taxas)} card(s) processado(s) com sucesso")
                                for r in sucessos_taxas:
                                    self._comp_add_log(f"   ✅ {r['card_title']} → Solicitação Paga")
                
                if self.comp_var_taxas_anbima.get():
                    self._comp_add_log("\n⚠️ Pipe TAXAS ANBIMA ainda não implementado")
                
                # Restaurar stdout
                sys.stdout = sys.__stdout__
                
                # Mensagem final
                self._comp_set_progress("✅ Processamento concluído!")
                self._comp_add_log("\n" + "="*60)
                self._comp_add_log("✅ Todos os pipes foram processados com sucesso!")
                
            except Exception as e:
                # Restaurar stdout
                sys.stdout = sys.__stdout__
                
                self._comp_set_progress(f"❌ Erro durante processamento")
                self._comp_add_log(f"\n❌ Erro: {str(e)}")
                import traceback
                self._comp_add_log(f"\n{traceback.format_exc()}")
                
            finally:
                # Parar barra de progresso
                self.comp_progress_bar.stop()
                
                # Reabilitar botões
                self.comp_running = False
                self.comp_buscar_btn.config(state=tk.NORMAL, bg=COLORS['primary'])
                self.comp_process_btn.config(state=tk.NORMAL,
                                            text="▶ Processar",
                                            bg=COLORS['primary'])
        
        thread = threading.Thread(target=run_thread, daemon=True)
        thread.start()
    
    def _test_matching(self):
        """Testa matching sem processar cards"""
        # Verificar se já está executando
        if self.comp_running:
            messagebox.showwarning("Atenção", "⚠️ Já existe uma operação em andamento!\nAguarde a conclusão.")
            return
        
        if not comprovantes_pipe:
            messagebox.showerror("Erro", "Módulo Anexarcomprovantespipe não disponível!")
            return
        
        # Validar que Liquidação esteja selecionado (único implementado)
        if not self.comp_var_liquidacao.get():
            messagebox.showwarning("Atenção", "Selecione o pipe Liquidação para testar!")
            return
        
        # Desabilitar botões
        self.comp_running = True
        self.comp_buscar_btn.config(state=tk.DISABLED, bg=COLORS['bg_medium'])
        self.comp_process_btn.config(state=tk.DISABLED, bg=COLORS['bg_medium'])
        
        # Limpar logs
        self.comprovantes_status_text.config(state=tk.NORMAL)
        self.comprovantes_status_text.delete("1.0", tk.END)
        self.comprovantes_status_text.config(state=tk.DISABLED)
        
        # Iniciar barra de progresso
        self.comp_progress_bar.start(10)
        self._comp_set_progress("Testando matching...")
        
        def run_thread():
            try:
                import sys
                class TextRedirector:
                    def __init__(self, widget):
                        self.widget = widget
                    def write(self, text):
                        self.widget.config(state=tk.NORMAL)
                        self.widget.insert(tk.END, text)
                        self.widget.see(tk.END)
                        self.widget.config(state=tk.DISABLED)
                        self.widget.update_idletasks()
                    def flush(self):
                        pass
                
                sys.stdout = TextRedirector(self.comprovantes_status_text)
                
                # Pegar data selecionada
                data_busca_pipefy = self.comp_pipefy_data_var.get().strip()
                # Converter string vazia para None
                if not data_busca_pipefy:
                    data_busca_pipefy = None
                
                self._comp_add_log("🧪 Modo de teste - Apenas matching (sem anexar/mover)")
                self._comp_add_log(f"📅 Data para buscar comprovantes: {data_busca_pipefy if data_busca_pipefy else 'HOJE'}")
                self._comp_add_log("="*60)
                
                comprovantes_pipe.testar_matching_apenas(data_busca=data_busca_pipefy)
                
                sys.stdout = sys.__stdout__
                
                self._comp_set_progress("✅ Teste concluído!")
                self._comp_add_log("\n" + "="*60)
                self._comp_add_log("✅ Teste de matching finalizado!")
                
            except Exception as e:
                sys.stdout = sys.__stdout__
                self._comp_set_progress(f"❌ Erro durante teste")
                self._comp_add_log(f"\n❌ Erro: {str(e)}")
                import traceback
                self._comp_add_log(f"\n{traceback.format_exc()}")
            
            finally:
                self.comp_progress_bar.stop()
                # Reabilitar botões
                self.comp_running = False
                self.comp_buscar_btn.config(state=tk.NORMAL, bg=COLORS['primary'])
                self.comp_process_btn.config(state=tk.NORMAL, bg=COLORS['primary'])
        
        thread = threading.Thread(target=run_thread, daemon=True)
        thread.start()
    
    def _open_comprovantes_folder(self):
        """Abre a pasta Comprovantes no explorador"""
        pasta = Path(__file__).parent / "Comprovantes"
        pasta.mkdir(parents=True, exist_ok=True)
        
        try:
            import subprocess
            subprocess.Popen(f'explorer "{pasta}"')
        except:
            messagebox.showinfo("Pasta Comprovantes", f"Pasta criada em:\n{pasta}")
    
    def _show_error_in_tab(self, parent_frame, title, message):
        """Mostra mensagem de erro em uma aba"""
        error_frame = tk.Frame(parent_frame, bg=COLORS['bg_light'])
        error_frame.pack(fill=tk.BOTH, expand=True, padx=50, pady=50)
        
        # Ícone de erro
        tk.Label(error_frame, text="⚠️", font=("Segoe UI", 48), 
                bg=COLORS['bg_light']).pack(pady=20)
        
        # Título
        tk.Label(error_frame, text=title, font=("Segoe UI", 16, "bold"),
                fg=COLORS['text_dark'], bg=COLORS['bg_light']).pack(pady=10)
        
        # Mensagem
        tk.Label(error_frame, text=message, font=("Segoe UI", 10),
                fg=COLORS['text_light'], bg=COLORS['bg_light'],
                justify=tk.CENTER).pack(pady=10)


def main():
    if USING_BOOTSTRAP:
        root = tb.Window(themename="flatly")
    else:
        root = tk.Tk()
    
    # Criar launcher unificado com abas
    app = IntegracaoUnificada(root)

    # Centralizar
    root.update_idletasks()
    w, h = root.winfo_width(), root.winfo_height()
    x = (root.winfo_screenwidth() // 2) - (w // 2)
    y = (root.winfo_screenheight() // 2) - (h // 2)
    root.geometry(f"{w}x{h}+{x}+{y}")
    root.mainloop()


if __name__ == "__main__":
    main()



