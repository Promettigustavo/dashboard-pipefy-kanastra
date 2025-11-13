from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
import time

def esperar_e_clicar(navegador, xpath):
    max_tentativas=3
    tentativas = 0
    
    while tentativas < max_tentativas:
        try:
            tentativas += 1

            elemento = WebDriverWait(navegador, 7).until(
                EC.element_to_be_clickable(('xpath', xpath))
            )
            posicao_elemento = navegador.execute_script("return arguments[0].getBoundingClientRect().top;", elemento)
            altura_tela = navegador.execute_script("return window.innerHeight;")

            limite_superior = 0
            limite_inferior = altura_tela * 0.7

            while not (limite_superior <= posicao_elemento <= limite_inferior):
                distancia = posicao_elemento - (altura_tela / 2)
                passo = distancia * 0.6
                navegador.execute_script("window.scrollBy(0, arguments[0]);", passo)
                time.sleep(0.1)
                p = posicao_elemento
                posicao_elemento = navegador.execute_script("return arguments[0].getBoundingClientRect().top;", elemento)
                if p == posicao_elemento:
                    break
            time.sleep(0.2)

            elemento.click()

            time.sleep(0.3)
            
            break

        except Exception as e:
            time.sleep(2)
    else:
        raise Exception(f"Falha após {max_tentativas} tentativas. Não foi possível clicar no elemento: {xpath}")

def esperar_e_escrever(navegador, xpath, texto):
    max_tentativas=3
    tentativas = 0
    
    while tentativas < max_tentativas:
        try:
            tentativas += 1
            elemento = WebDriverWait(navegador, 7).until(
                EC.element_to_be_clickable(('xpath', xpath))
            )

            posicao_elemento = navegador.execute_script("return arguments[0].getBoundingClientRect().top;", elemento)
            altura_tela = navegador.execute_script("return window.innerHeight;")

            limite_superior = 0
            limite_inferior = altura_tela * 0.7

            while not (limite_superior <= posicao_elemento <= limite_inferior):
                distancia = posicao_elemento - (altura_tela / 2)
                passo = distancia * 0.5
                navegador.execute_script("window.scrollBy(0, arguments[0]);", passo)
                p = posicao_elemento
                posicao_elemento = navegador.execute_script("return arguments[0].getBoundingClientRect().top;", elemento)
                if p == posicao_elemento:
                    break
                

            time.sleep(0.2)

            elemento.clear()
            elemento.send_keys(texto)

            time.sleep(0.3)
            
            break

        except Exception as e:
            time.sleep(2)
    else:
        print("Falha após 3 tentativas. Não foi possível clicar no elemento.")

def esperar_e_copiar(navegador, xpath, popup = 0):
    max_tentativas = 3
    tentativas = 0
    
    while tentativas < max_tentativas:
        try:
            tentativas += 1

            elemento = WebDriverWait(navegador, 7).until(
                EC.presence_of_element_located(('xpath', xpath))
            )
            posicao_elemento = navegador.execute_script("return arguments[0].getBoundingClientRect().top;", elemento)
            altura_tela = navegador.execute_script("return window.innerHeight;")

            limite_superior = 0
            limite_inferior = altura_tela * 0.7

            if popup == 0:
                while not (limite_superior <= posicao_elemento <= limite_inferior):
                    distancia = posicao_elemento - (altura_tela / 2)
                    passo = distancia * 0.6
                    navegador.execute_script("window.scrollBy(0, arguments[0]);", passo)
                    time.sleep(0.1)
                    p = posicao_elemento
                    posicao_elemento = navegador.execute_script("return arguments[0].getBoundingClientRect().top;", elemento)
                    if p == posicao_elemento:
                        break
            elif popup == 1:
                modal = navegador.find_element(By.XPATH, "/html/body/section/div/div/form/div[3]/div/ibe-fundos-saldos-element/div/ibe-funds-list/dss-dialog/div/div/dss-dialog-body")

                navegador.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", modal)
            else:
                modal = navegador.find_element(By.XPATH, "/html/body/section/div/div/form/div[3]/div/ibe-fundos-saldos-element/div/ibe-funds-list/dss-dialog/div/div/dss-dialog-body")
                time.sleep(0.2)
                navegador.execute_script("arguments[0].scrollTop = 0", modal)
            time.sleep(0.2)

            numero = float(elemento.text.strip().replace('.', '').replace(',', '.'))
            
            if numero is not None:
                return numero
            
        except Exception as e:
            time.sleep(2)
    
    raise Exception(f"Falha após {max_tentativas} tentativas. Não foi possível copiar o número do elemento: {xpath}")

def esperar_e_copiar_texto(navegador, xpath, popup=0):
    max_tentativas = 3
    tentativas = 0

    while tentativas < max_tentativas:
        try:
            tentativas += 1

            elemento = WebDriverWait(navegador, 7).until(
                EC.presence_of_element_located(('xpath', xpath))
            )
            posicao_elemento = navegador.execute_script("return arguments[0].getBoundingClientRect().top;", elemento)
            altura_tela = navegador.execute_script("return window.innerHeight;")

            limite_superior = 0
            limite_inferior = altura_tela * 0.7

            if popup == 0:
                while not (limite_superior <= posicao_elemento <= limite_inferior):
                    distancia = posicao_elemento - (altura_tela / 2)
                    passo = distancia * 0.6
                    navegador.execute_script("window.scrollBy(0, arguments[0]);", passo)
                    time.sleep(0.1)
                    p = posicao_elemento
                    posicao_elemento = navegador.execute_script("return arguments[0].getBoundingClientRect().top;", elemento)
                    if p == posicao_elemento:
                        break
            elif popup == 1:
                modal = navegador.find_element(By.XPATH, "/html/body/section/div/div/form/div[3]/div/ibe-fundos-saldos-element/div/ibe-funds-list/dss-dialog/div/div/dss-dialog-body")
                navegador.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", modal)
            else:
                modal = navegador.find_element(By.XPATH, "/html/body/section/div/div/form/div[3]/div/ibe-fundos-saldos-element/div/ibe-funds-list/dss-dialog/div/div/dss-dialog-body")
                time.sleep(0.2)
                navegador.execute_script("arguments[0].scrollTop = 0", modal)
            time.sleep(0.2)

            texto = elemento.text.strip()
            if texto:
                return texto

        except Exception as e:
            time.sleep(2)

    raise Exception(f"Falha após {max_tentativas} tentativas. Não foi possível copiar o texto do elemento: {xpath}")