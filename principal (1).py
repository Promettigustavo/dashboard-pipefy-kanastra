from selenium import webdriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
import time
import xlwings as xw
import os
import shutil
from tkinter import filedialog, messagebox
import customtkinter as ctk
import keyboard
from funcoes import esperar_e_clicar, esperar_e_escrever
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

root = ctk.CTk()
root.title("Formulário de Login e Diretório")
root.geometry
                                            # bbbbbbbbb -]]]]]]]]]]]]]
                                            
usar_santander = ctk.BooleanVar(value=False)
usar_arbi = ctk.BooleanVar(value=False)

def coletar_dados():
    global usuario_santander, senha_santander, diretorio_origem, cpf_arbi, senha_arbi, santander, arbi
    
    santander = 0
    arbi = 0

    if usar_santander.get():
        santander = 1
        usuario_santander = entry_usuario_santander.get()
        senha_santander = entry_senha_santander.get()
    
    if usar_arbi.get():
        arbi = 1
        cpf_arbi = entry_cpf_arbi.get()
        senha_arbi = entry_senha_arbi.get()
    
    diretorio_origem = entry_diretorio.get()

    if not diretorio_origem:
        messagebox.showwarning("Aviso", "Selecione um diretório para os downloads.")
        return

    messagebox.showinfo("Dados Coletados", f"Usuário Santander: {usuario_santander if usar_santander.get() else 'Não utilizado'}\n"
                                           f"CPF Arbi: {cpf_arbi if usar_arbi.get() else 'Não utilizado'}\n"
                                           f"Diretório: {diretorio_origem}")
    root.destroy()

def selecionar_diretorio():
    diretorio_origem = filedialog.askdirectory(title="Escolha a pasta de downloads")
    if diretorio_origem:
        entry_diretorio.delete(0, "end")
        entry_diretorio.insert(0, diretorio_origem)

def ativar_santander():
    estado = "normal" if usar_santander.get() else "disabled"
    entry_usuario_santander.configure(state=estado)
    entry_senha_santander.configure(state=estado)

def ativar_arbi():
    estado = "normal" if usar_arbi.get() else "disabled"
    entry_cpf_arbi.configure(state=estado)
    entry_senha_arbi.configure(state=estado)

# === FRAME PARA SANTANDER ===
frame_santander = ctk.CTkFrame(root)
frame_santander.pack(pady=10, padx=10, fill="x")

check_santander = ctk.CTkCheckBox(frame_santander, text="Usar Santander", variable=usar_santander, command=ativar_santander)
check_santander.grid(row=0, column=0, columnspan=2, pady=5, sticky="w")

label_usuario_santander = ctk.CTkLabel(frame_santander, text="Usuário:")
label_usuario_santander.grid(row=1, column=0, padx=10, pady=5, sticky="w")
entry_usuario_santander = ctk.CTkEntry(frame_santander, width=250, state="disabled")
entry_usuario_santander.grid(row=1, column=1, padx=10, pady=5)

label_senha_santander = ctk.CTkLabel(frame_santander, text="Senha:")
label_senha_santander.grid(row=2, column=0, padx=10, pady=5, sticky="w")
entry_senha_santander = ctk.CTkEntry(frame_santander, width=250, show="*", state="disabled")
entry_senha_santander.grid(row=2, column=1, padx=10, pady=5)

# === FRAME PARA ARBI ===
frame_arbi = ctk.CTkFrame(root)
frame_arbi.pack(pady=10, padx=10, fill="x")

check_arbi = ctk.CTkCheckBox(frame_arbi, text="Usar Arbi", variable=usar_arbi, command=ativar_arbi)
check_arbi.grid(row=0, column=0, columnspan=2, pady=5, sticky="w")

label_cpf_arbi = ctk.CTkLabel(frame_arbi, text="CPF:")
label_cpf_arbi.grid(row=1, column=0, padx=10, pady=5, sticky="w")
entry_cpf_arbi = ctk.CTkEntry(frame_arbi, width=250, state="disabled")
entry_cpf_arbi.grid(row=1, column=1, padx=10, pady=5)

label_senha_arbi = ctk.CTkLabel(frame_arbi, text="Senha:")
label_senha_arbi.grid(row=2, column=0, padx=10, pady=5, sticky="w")
entry_senha_arbi = ctk.CTkEntry(frame_arbi, width=250, show="*", state="disabled")
entry_senha_arbi.grid(row=2, column=1, padx=10, pady=5)

# === SELEÇÃO DE DIRETÓRIO ===
label_diretorio = ctk.CTkLabel(root, text="Pasta de Downloads:")
label_diretorio.pack(pady=5)
entry_diretorio = ctk.CTkEntry(root, width=300)
entry_diretorio.pack(pady=5)
botao_diretorio = ctk.CTkButton(root, text="Selecionar Diretório", command=selecionar_diretorio)
botao_diretorio.pack(pady=5)

# === BOTÃO ENVIAR ===
botao_enviar = ctk.CTkButton(root, text="Enviar", command=coletar_dados, width=200, height=40)
botao_enviar.pack(pady=20, expand=True)  # Adicionei expand=True e fill="both"

root.mainloop()

options = webdriver.ChromeOptions()
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option("useAutomationExtension", False)

service = Service(ChromeDriverManager().install()) 
navegador = webdriver.Chrome(service=service, options=options)
navegador.maximize_window()

tempo_espera = 10
tempo_padrao = 0.3

planilha_controle = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ExtratosAutomaticos.xlsx")
with xw.App(visible=True, add_book=False) as app:
    wb = app.books.open(planilha_controle)
    time.sleep(1)
    sheet_controle = wb.sheets['Controle']
    sheet_santander = wb.sheets['Santander'] 
    sheet_arbi = wb.sheets['Arbi']
    sheet_bradesco = wb.sheets['Bradesco']
    sheet_itau = wb.sheets['Itau']
    data = str(sheet_controle.range(f'B3').value).split(" ")[0].replace("-", "")
    diretorio_base = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Extratos", data)

    if santander == 1:
        navegador.get('https://www.santander.com.br/empresas')
        time.sleep(5)
        a = 0
        fundos_santander = [fundo.strip() if isinstance(fundo, str) else fundo for fundo in sheet_santander.range((2, "B")).expand('down').value]

        os.makedirs(os.path.join(os.path.dirname(os.path.abspath(__file__)), "Extratos", data), exist_ok=True)
        for fundo in fundos_santander:
            caminho = os.path.join(diretorio_base, fundo)
            os.makedirs(caminho, exist_ok=True)

        for fundo in fundos_santander:
            caminho = os.path.join(diretorio_base, fundo, "Santander")
            os.makedirs(caminho, exist_ok=True)
        
        fim = len(fundos_santander) + 1
        i = 2
        while i <= fim:
            if sheet_santander.range(f'A{i}').value == sheet_controle.range(f'B3').value:
                i += 1
                continue
            agencia = str(sheet_santander.range(f'C{i}').value).strip().split(".")[0]
            time.sleep(tempo_padrao)
            conta = str(sheet_santander.range(f'D{i}').value).strip().split(".")[0]
            time.sleep(tempo_padrao)
            if str(sheet_santander.range(f'E{i}').value).lower() == "sim":
                invest = 1
            else:
                invest = 0
            try:
                if a == 0:
                    host_shadow = navegador.find_element(By.CSS_SELECTOR, "wpc-mfe-home-header-element[ibpf-choice='ibpf-novo']")
                    shadow_root = navegador.execute_script("return arguments[0].shadowRoot", host_shadow)

                    input_agencia = shadow_root.find_element(By.CSS_SELECTOR, "input[formcontrolname='ag']")
                    input_conta = shadow_root.find_element(By.CSS_SELECTOR, "input[formcontrolname='acc']")

                    input_agencia.clear()
                    input_agencia.send_keys(agencia)
                    time.sleep(0.2)
                    
                    input_conta.clear()
                    input_conta.send_keys(conta)
                    time.sleep(1)
                    botao_login = shadow_root.find_element(By.CSS_SELECTOR, "button[class='login-icon dss-button dss-button--text']")
                    botao_login.click()
                    time.sleep(1)

                    esperar_e_clicar(navegador, '//*[@id="formGeral:usuario"]')
                    esperar_e_escrever(navegador, '//*[@id="formGeral:usuario"]', usuario_santander)
                    esperar_e_escrever(navegador, '/html/body/form/div[6]/div[2]/div/div/div[1]/div[2]/div/div[2]/div/div/input', senha_santander)
                    esperar_e_clicar(navegador, '/html/body/form/div[6]/div[2]/div/div/input')
                else:
                    esperar_e_clicar(navegador, '/html/body/div[2]/div/div/div[2]/div/div/form/a')
                    time.sleep(1)
                    esperar_e_escrever(navegador, '/html/body/div[2]/div/div/div[2]/div/div/form/div/div/span/div/div/div/div/div[1]/div[1]/input', conta)
                    time.sleep(1)
                    fundoencontrado = navegador.find_elements("xpath", "/html/body/div[2]/div/div/div[2]/div/div/form/div/div/span/div/div/div/div/div[2]/table/tbody/tr/td[2]")
                    if fundoencontrado:
                        pass
                    else:
                        navegador.refresh()
                        time.sleep(2)
                        esperar_e_clicar(navegador, '/html/body/div[2]/div/div/div[2]/div/div/form/a')
                        time.sleep(1.5)
                        esperar_e_escrever(navegador, '/html/body/div[2]/div/div/div[2]/div/div/form/div/div/span/div/div/div/div/div[1]/div[1]/input', conta)
                        pass
                    esperar_e_clicar(navegador, '/html/body/div[2]/div/div/div[2]/div/div/form/div/div/span/div/div/div/div/div[2]/table/tbody/tr/td[2]')
                time.sleep(6)
                tentativas = 0
                max_tentativas = 3
                while tentativas < max_tentativas:
                    try:
                        tentativas += 1
                        xpath = '/html/body/section/div/div/form/div[2]/div[2]/ul/li[2]/a/span[1]'
                        elemento = WebDriverWait(navegador, 3).until(
                            EC.element_to_be_clickable(('xpath', xpath))
                        )
                        esperar_e_clicar(navegador, xpath)
                        break
                    except Exception as e:
                        try:
                            xpath = '/html/body/div[3]/div[2]/div/div/div[2]/div/a'
                            elemento = WebDriverWait(navegador, 0.2).until(
                                EC.element_to_be_clickable(('xpath', xpath))
                            )
                            esperar_e_clicar(navegador, xpath)
                            esperar_e_escrever(navegador, '//*[@id="formGeral:usuario"]', usuario_santander)
                            esperar_e_escrever(navegador, '/html/body/form/div[6]/div[2]/div/div/div[1]/div[2]/div/div[2]/div/div/input', senha_santander)
                            time.sleep(180)
                            esperar_e_clicar(navegador, '/html/body/div[2]/div/div/div[2]/div/div/form/div/div/span/div/div/div/div/div[2]/table/tbody/tr/td[2]')
                        except Exception as e:
                            pass

                        try:
                            xpath = '/html/body/section/div/div/form/div[2]/div/ibe-privacy-policy-term-element/div/ibe-home/section/div[6]/div/button'
                            elemento = WebDriverWait(navegador, 0.2).until(
                                EC.element_to_be_clickable(('xpath', xpath))
                            )
                            esperar_e_clicar(navegador, xpath)
                        except Exception as e:
                            pass
                        try:
                            xpath = '/html/body/form/div[2]/div[2]/table/tbody/tr/td/span'
                            elemento = WebDriverWait(navegador, 0.2).until(
                                EC.element_to_be_clickable(('xpath', xpath))
                            )
                            time.sleep(2)
                            esperar_e_clicar(navegador, xpath)
                        except Exception as e:
                            pass

                esperar_e_escrever(navegador, '//input[contains(@id, "formPainelNotificacoes")]', "conta corrente extrato consultar")
                time.sleep(1.5)
                pesquisarencontrado = navegador.find_elements("xpath", "//li[contains(@data-item-label, 'Conta Corrente -> Extrato -> Consultar')]")
                if pesquisarencontrado:
                    pass
                else:
                    navegador.refresh()
                    time.sleep(2)
                    esperar_e_escrever(navegador, '//input[contains(@id, "formPainelNotificacoes")]', "conta corrente extrato consultar")
                    time.sleep(4)
                    esperar_e_clicar(navegador, "//li[contains(@data-item-label, 'Conta Corrente -> Extrato -> Consultar')]")
                    pass
                esperar_e_clicar(navegador, "//li[contains(@data-item-label, 'Conta Corrente -> Extrato -> Consultar')]")

                time.sleep(3)
                esperar_e_clicar(navegador, '//a[contains(@id, "formGeral:exportarExtratoExcel")]')
                esperar_e_clicar(navegador, '//div[contains(@id, "formGeral:dialogMessage")]/div[contains(@class, "ui-dialog-titlebar")]/a')
                esperar_e_clicar(navegador, '//a[contains(@id, "formGeral:salvarPDF")]')
                esperar_e_clicar(navegador, '//div[contains(@id, "formGeral:dialogMessage")]/div[contains(@class, "ui-dialog-titlebar")]/a')

                if invest == 1:
                    esperar_e_escrever(navegador, '//input[contains(@id, "formPainelNotificacoes")]', "investimentos fundos consultar extrato por período")
                    time.sleep(1.5)
                    pesquisarencontrado = navegador.find_elements("xpath", "//li[contains(@data-item-label, 'Investimentos -> Fundos -> Consultar extrato por período')]")
                    if pesquisarencontrado:
                        pass
                    else:
                        navegador.refresh()
                        time.sleep(2)
                        esperar_e_escrever(navegador, '//input[contains(@id, "formPainelNotificacoes")]', "investimentos fundos consultar extrato por período")
                        time.sleep(4)
                        esperar_e_clicar(navegador, "//li[contains(@data-item-label, 'Investimentos -> Fundos -> Consultar extrato por período')]")
                        pass
                    esperar_e_clicar(navegador, "//li[contains(@data-item-label, 'Investimentos -> Fundos -> Consultar extrato por período')]")

                    esperar_e_clicar(navegador, '/html/body/section/div/div/form/div[3]/div/ibe-fundos-extrato-periodo-element/div/ibe-funds-list/dss-segment-control/div/div[2]/div/div[3]/div/dss-form-field/div/dss-dropdown/div/button')
                    esperar_e_clicar(navegador, '/html/body/section/div/div/form/div[3]/div/ibe-fundos-extrato-periodo-element/div/ibe-funds-list/dss-segment-control/div/div[2]/div/div[3]/div/dss-form-field/div/dss-dropdown/div/ul/li[1]/a')
                    time.sleep(3)

                    semmovimentacao = navegador.find_elements("xpath", "//span[contains(text(),'Cliente não possui movimentação')]")
                    if semmovimentacao:
                        invest = invest - 1
                    else:
                        esperar_e_clicar(navegador, '/html/body/section/div/div/form/div[3]/div/ibe-fundos-extrato-periodo-element/div/ibe-funds-list/div[3]/dss-data-table/section/div[1]/table/tbody/tr/td[1]/dss-radio-group/div/dss-radio-button/label')
                        esperar_e_clicar(navegador, '/html/body/section/div/div/form/div[3]/div/ibe-fundos-extrato-periodo-element/div/ibe-funds-list/div[6]/div[2]/button')
                        esperar_e_clicar(navegador, '//a[contains(text(), "Salvar em PDF")]')
                
                time.sleep(6)
                pasta = str(sheet_santander.range(f'B{i}').value).strip().split(".")[0]

                diretorio_destino = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Extratos", data, pasta, "Santander")

                arquivos = os.listdir(diretorio_origem)

                arquivos = [f for f in arquivos if os.path.isfile(os.path.join(diretorio_origem, f))]

                arquivos.sort(key=lambda x: os.path.getmtime(os.path.join(diretorio_origem, x)), reverse=True)

                narq = invest + 2
                ultimos_arquivos = arquivos[:narq]

                for arquivo in ultimos_arquivos:
                    caminho_origem = os.path.join(diretorio_origem, arquivo)
                    caminho_destino = os.path.join(diretorio_destino, arquivo)

                    shutil.move(caminho_origem, diretorio_destino)
                    print(f"Arquivo {arquivo} movido com sucesso!")

                sheet_santander.range(f'A{i}').value = sheet_controle.range(f'B3').value
                a = 1
            except Exception as e:
                sheet_santander.range(f'A{i}').value = "Erro"
            
                pasta = str(sheet_santander.range(f'B{i}').value).strip().split(".")[0]
                diretorio_destino = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Extratos", data, pasta, "Santander")
                shutil.rmtree(diretorio_destino, ignore_errors=True)
                os.makedirs(diretorio_destino, exist_ok=True)
                navegador.get('https://www.santander.com.br/empresas')
                a = 0
            wb.save()
            i = i + 1

        ####
    if arbi == 1:
        fundos_arbi = [fundo.strip() if isinstance(fundo, str) else fundo for fundo in sheet_arbi.range((2, "B")).expand('down').value]

        for fundo in fundos_arbi:
            caminho = os.path.join(diretorio_base, fundo)
            os.makedirs(caminho, exist_ok=True)

        for fundo in fundos_arbi:
            caminho = os.path.join(diretorio_base, fundo, "Arbi")
            os.makedirs(caminho, exist_ok=True)
        
        i = 2
        fim = len(fundos_arbi)
        a = 0
        while i <= fim:
            
            if sheet_arbi.range(f'A{i}').value == sheet_controle.range(f'B3').value:
                i += 1
                continue

            conta = str(sheet_arbi.range(f'C{i}').value).strip().split(".")[0]
            time.sleep(tempo_padrao)
            navegador.get('https://portal.bancoarbi.com.br/')
            try:
                if a == 0:
                    esperar_e_escrever(navegador, '/html/body/div[2]/div[1]/div[1]/div[1]/div/div[2]/form/div[1]/input', cpf_arbi)
                    esperar_e_clicar(navegador, '/html/body/div[2]/div[1]/div[1]/div[1]/div/div[2]/form/div[2]/input')
                    while True:
                        if keyboard.is_pressed('f9'):
                            print("Tecla 'f9' pressionada. Continuando com o script...")
                            break
                        time.sleep(0.1)
                    time.sleep(1)
                
                esperar_e_clicar(navegador, '//a[@href="/consultas"]')                   
                esperar_e_clicar(navegador, '/html/body/div[3]/div[1]/div/div[1]/div/div/form/span/span[1]/span/span[1]')
                esperar_e_escrever(navegador, '/html/body/span/span/span[1]/input', conta)
                time.sleep(0.5)
                esperar_e_clicar(navegador, '/html/body/span/span/span[2]/ul/li/div')
                time.sleep(0.5)
                esperar_e_clicar(navegador, '/html/body/div[3]/div[2]/div[5]/form[1]/div/span[1]/select')
                esperar_e_clicar(navegador, '/html/body/div[3]/div[2]/div[5]/form[1]/div/span[1]/select/option[4]')
                esperar_e_clicar(navegador, '/html/body/div[3]/div[2]/div[5]/form[1]/div/div/div[1]')
                time.sleep(3)
                
                pasta = str(sheet_arbi.range(f'B{i}').value).strip().split(".")[0]

                diretorio_destino = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Extratos", data, pasta, "Arbi")

                arquivos = os.listdir(diretorio_origem)

                arquivos = [f for f in arquivos if os.path.isfile(os.path.join(diretorio_origem, f))]

                arquivos.sort(key=lambda x: os.path.getmtime(os.path.join(diretorio_origem, x)), reverse=True)

                narq = 1
                ultimos_arquivos = arquivos[:narq]

                for arquivo in ultimos_arquivos:
                    caminho_origem = os.path.join(diretorio_origem, arquivo)
                    caminho_destino = os.path.join(diretorio_destino, arquivo)

                    shutil.move(caminho_origem, diretorio_destino)
                    print(f"Arquivo {arquivo} movido com sucesso!")

                sheet_arbi.range(f'A{i}').value = sheet_controle.range(f'B3').value
                a = 1

            except Exception as e:
                sheet_arbi.range(f'A{i}').value = "Erro"
                pasta = str(sheet_arbi.range(f'B{i}').value).strip().split(".")[0]
                diretorio_destino = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Extratos", data, pasta, "Arbi")
                shutil.rmtree(diretorio_destino, ignore_errors=True)
                os.makedirs(diretorio_destino, exist_ok=True)
                navegador.get('https://portal.bancoarbi.com.br/')
            i = i + 1
            wb.save()
    wb.save()
    wb.close()