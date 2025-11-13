# Código da aba de comprovantes compacta para substituir no Integracao.py
# Procure pela função _criar_aba_comprovantes() e substitua completamente

def _criar_aba_comprovantes(self):
    """Cria aba de Anexar Comprovantes Santander - VERSÃO COMPACTA"""
    # Canvas com scroll
    canvas = tk.Canvas(self.comprovantes_frame, bg=COLORS['bg_light'], highlightthickness=0)
    scrollbar = tk.Scrollbar(self.comprovantes_frame, orient="vertical", command=canvas.yview)
    scrollable_frame = tk.Frame(canvas, bg=COLORS['bg_light'])
    
    scrollable_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )
    
    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)
    
    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")
    
    container = tk.Frame(scrollable_frame, bg=COLORS['bg_light'])
    container.pack(fill=tk.BOTH, expand=True, padx=30, pady=15)
    
    # Título compacto
    title_frame = tk.Frame(container, bg=COLORS['bg_light'])
    title_frame.pack(fill=tk.X, pady=(0, 12))
    
    tk.Label(title_frame, text="📎 Anexar Comprovantes Santander", 
            font=("Segoe UI", 16, "bold"),
            fg=COLORS['text_dark'], bg=COLORS['bg_light']).pack(anchor=tk.W)
    
    tk.Label(title_frame, 
            text="Busque comprovantes ou processe automaticamente no Pipefy",
            font=("Segoe UI", 9),
            fg=COLORS['text_light'], bg=COLORS['bg_light']).pack(anchor=tk.W, pady=(2,0))
    
    # Flag de controle de execução
    self.comp_running = False
    
    # ========== SEÇÃO 1: BUSCAR COMPROVANTES (COMPACTA) ==========
    buscar_frame = tk.LabelFrame(container, text="🔍 Buscar e Baixar Comprovantes", 
                                 bg="white", fg=COLORS['text_dark'],
                                 font=("Segoe UI", 10, "bold"), padx=12, pady=8)
    buscar_frame.pack(fill=tk.X, pady=(0, 10))
    
    # Data e Pasta na mesma linha
    grid_row = tk.Frame(buscar_frame, bg="white")
    grid_row.pack(fill=tk.X, pady=(0, 8))
    
    tk.Label(grid_row, text="📅", font=("Segoe UI", 9),
            fg=COLORS['text_dark'], bg="white").grid(row=0, column=0, sticky="w", padx=(0, 3))
    
    from datetime import date
    self.comp_data_var = tk.StringVar(value=date.today().strftime("%Y-%m-%d"))
    tk.Entry(grid_row, textvariable=self.comp_data_var,
            font=("Segoe UI", 9), width=12).grid(row=0, column=1, sticky="w", padx=(0, 12))
    
    tk.Label(grid_row, text="📁", font=("Segoe UI", 9),
            fg=COLORS['text_dark'], bg="white").grid(row=0, column=2, sticky="w", padx=(0, 3))
    
    self.comp_pasta_var = tk.StringVar(value=str(Path(__file__).parent / "Comprovantes"))
    tk.Entry(grid_row, textvariable=self.comp_pasta_var,
            font=("Segoe UI", 8), width=32).grid(row=0, column=3, sticky="w", padx=(0, 3))
    
    tk.Button(grid_row, text="...", font=("Segoe UI", 7),
             bg=COLORS['bg_medium'], fg=COLORS['text_dark'],
             relief=tk.FLAT, padx=6, pady=2, cursor="hand2",
             command=self._comp_selecionar_pasta).grid(row=0, column=4, sticky="w")
    
    # Fundos - linha compacta
    fundos_header = tk.Frame(buscar_frame, bg="white")
    fundos_header.pack(fill=tk.X, pady=(0, 3))
    
    tk.Label(fundos_header, text="💼 Fundos:", font=("Segoe UI", 9, "bold"),
            fg=COLORS['text_dark'], bg="white").pack(side=tk.LEFT)
    
    # Importar fundos
    try:
        from credenciais_bancos import SANTANDER_FUNDOS
        fundos_disponiveis = sorted(list(SANTANDER_FUNDOS.keys()))
    except:
        fundos_disponiveis = []
    
    self.comp_fundos_completos = fundos_disponiveis
    
    # Campo de pesquisa compacto
    search_frame = tk.Frame(buscar_frame, bg="white")
    search_frame.pack(fill=tk.X, pady=(0, 3))
    
    tk.Label(search_frame, text="🔍", font=("Segoe UI", 8),
            fg=COLORS['text_dark'], bg="white").pack(side=tk.LEFT, padx=(0, 2))
    
    self.comp_search_var = tk.StringVar()
    self.comp_search_var.trace('w', lambda *args: self._comp_filtrar_fundos())
    
    tk.Entry(search_frame, textvariable=self.comp_search_var,
            font=("Segoe UI", 8), width=25,
            bg="#f8f9fa", fg=COLORS['text_dark'], relief=tk.FLAT).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 3))
    
    tk.Button(search_frame, text="✗", font=("Segoe UI", 7),
             bg=COLORS['bg_medium'], fg=COLORS['text_dark'],
             relief=tk.FLAT, padx=3, pady=1, cursor="hand2",
             command=lambda: self.comp_search_var.set("")).pack(side=tk.LEFT, padx=(0, 3))
    
    tk.Button(search_frame, text="✓ Todos", font=("Segoe UI", 7),
             bg=COLORS['bg_medium'], fg=COLORS['text_dark'],
             relief=tk.FLAT, padx=5, pady=1, cursor="hand2",
             command=lambda: self._comp_toggle_fundos(True)).pack(side=tk.LEFT, padx=(0, 2))
    
    tk.Button(search_frame, text="✗ Nenhum", font=("Segoe UI", 7),
             bg=COLORS['bg_medium'], fg=COLORS['text_dark'],
             relief=tk.FLAT, padx=5, pady=1, cursor="hand2",
             command=lambda: self._comp_toggle_fundos(False)).pack(side=tk.LEFT)
    
    # Listbox compacta
    fundos_container = tk.Frame(buscar_frame, bg="white")
    fundos_container.pack(fill=tk.X, pady=(0, 6))
    
    fundos_scrollbar = tk.Scrollbar(fundos_container)
    fundos_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    self.comp_fundos_listbox = tk.Listbox(fundos_container,
                                          selectmode=tk.MULTIPLE,
                                          height=4,  # Altura reduzida
                                          font=("Segoe UI", 8),
                                          bg="#f8f9fa",
                                          fg=COLORS['text_dark'],
                                          selectbackground=COLORS['primary'],
                                          selectforeground="white",
                                          relief=tk.FLAT,
                                          yscrollcommand=fundos_scrollbar.set)
    self.comp_fundos_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    fundos_scrollbar.config(command=self.comp_fundos_listbox.yview)
    
    # Adicionar fundos e selecionar todos
    for fundo_id in fundos_disponiveis:
        self.comp_fundos_listbox.insert(tk.END, fundo_id)
    for i in range(len(fundos_disponiveis)):
        self.comp_fundos_listbox.selection_set(i)
    
    # Botão buscar
    self.comp_buscar_btn = tk.Button(buscar_frame, text="🔍 Buscar",
             font=("Segoe UI", 9, "bold"), bg=COLORS['primary'], fg="white",
             activebackground=COLORS['primary_hover'], activeforeground="white",
             relief=tk.FLAT, padx=15, pady=5, cursor="hand2",
             command=self._comp_buscar_comprovantes)
    self.comp_buscar_btn.pack(anchor=tk.W)
    
    # ========== SEÇÃO 2: PROCESSAR NO PIPEFY (COMPACTA) ==========
    pipefy_frame = tk.LabelFrame(container, text="⚙️ Processar no Pipefy", 
                                bg="white", fg=COLORS['text_dark'],
                                font=("Segoe UI", 10, "bold"), padx=12, pady=8)
    pipefy_frame.pack(fill=tk.X, pady=(0, 10))
    
    # Checkboxes e data inline
    grid_pipefy = tk.Frame(pipefy_frame, bg="white")
    grid_pipefy.pack(fill=tk.X, pady=(0, 6))
    
    self.comp_var_liquidacao = tk.BooleanVar(value=True)
    self.comp_var_taxas = tk.BooleanVar(value=False)
    self.comp_var_taxas_anbima = tk.BooleanVar(value=False)
    
    tk.Checkbutton(grid_pipefy, text="💰 Liquidação", variable=self.comp_var_liquidacao,
                  font=("Segoe UI", 8), bg="white", fg=COLORS['text_dark'],
                  activebackground="white", selectcolor="white").grid(row=0, column=0, sticky="w", padx=(0, 10))
    
    tk.Checkbutton(grid_pipefy, text="📊 Taxas", variable=self.comp_var_taxas,
                  font=("Segoe UI", 8), bg="white", fg=COLORS['text_dark'],
                  activebackground="white", selectcolor="white").grid(row=0, column=1, sticky="w", padx=(0, 10))
    
    tk.Checkbutton(grid_pipefy, text="📈 Taxas Anbima", variable=self.comp_var_taxas_anbima,
                  font=("Segoe UI", 8), bg="white", fg=COLORS['text_dark'],
                  activebackground="white", selectcolor="white", state=tk.DISABLED).grid(row=0, column=2, sticky="w", padx=(0, 15))
    
    tk.Label(grid_pipefy, text="📅", font=("Segoe UI", 8),
            fg=COLORS['text_dark'], bg="white").grid(row=0, column=3, sticky="w", padx=(0, 2))
    
    self.comp_pipefy_data_var = tk.StringVar(value=date.today().strftime("%Y-%m-%d"))
    tk.Entry(grid_pipefy, textvariable=self.comp_pipefy_data_var,
            font=("Segoe UI", 9), width=12).grid(row=0, column=4, sticky="w")
    
    # Botões
    btn_frame = tk.Frame(pipefy_frame, bg="white")
    btn_frame.pack(fill=tk.X)
    
    self.comp_process_btn = tk.Button(btn_frame, text="▶ Processar",
             font=("Segoe UI", 9, "bold"), bg=COLORS['primary'], fg="white",
             activebackground=COLORS['primary_hover'], activeforeground="white",
             relief=tk.FLAT, padx=15, pady=5, cursor="hand2",
             command=self._run_comprovantes)
    self.comp_process_btn.pack(side=tk.LEFT, padx=(0, 4))
    
    tk.Button(btn_frame, text="🧪 Testar",
             font=("Segoe UI", 8), bg=COLORS['bg_medium'], fg=COLORS['text_dark'],
             activebackground=COLORS['bg_dark'], activeforeground="white",
             relief=tk.FLAT, padx=10, pady=5, cursor="hand2",
             command=self._test_matching).pack(side=tk.LEFT)
    
    # ========== STATUS E LOGS (COMPACTOS) ==========
    progress_frame = tk.LabelFrame(container, text="📊 Status", 
                                  bg="white", fg=COLORS['text_dark'],
                                  font=("Segoe UI", 10, "bold"), padx=12, pady=8)
    progress_frame.pack(fill=tk.BOTH, expand=True)
    
    self.comp_progress_label = tk.Label(progress_frame, text="Aguardando execução...", 
                                       font=("Segoe UI", 8), fg=COLORS['text_dark'], bg="white")
    self.comp_progress_label.pack(anchor=tk.W, pady=(0, 4))
    
    self.comp_progress_bar = ttk.Progressbar(progress_frame, mode='indeterminate', length=250)
    self.comp_progress_bar.pack(fill=tk.X, pady=(0, 6))
    
    # Logs reduzidos
    status_scroll = tk.Scrollbar(progress_frame)
    status_scroll.pack(side=tk.RIGHT, fill=tk.Y)
    
    self.comprovantes_status_text = tk.Text(progress_frame, height=8,  # Altura reduzida
                                           font=("Consolas", 8),
                                           bg="#f8f9fa", fg=COLORS['text_dark'],
                                           yscrollcommand=status_scroll.set,
                                           relief=tk.FLAT, padx=6, pady=6)
    self.comprovantes_status_text.pack(fill=tk.BOTH, expand=True)
    status_scroll.config(command=self.comprovantes_status_text.yview)
    
    # Botão limpar
    tk.Button(progress_frame, text="🗑️ Limpar",
             font=("Segoe UI", 7), bg=COLORS['bg_medium'], fg=COLORS['text_dark'],
             relief=tk.FLAT, padx=8, pady=3, cursor="hand2",
             command=self._comp_clear_logs).pack(anchor=tk.W, pady=(4, 0))
