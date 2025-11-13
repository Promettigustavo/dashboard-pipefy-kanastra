#!/usr/bin/env python3
"""
Automao completa: Gera arquivo Excel via API Pipefy e executa pipeliquidao automaticamente
Usa a data fornecida pelo launcher para o processamento
"""

import requests
import json
import os
from datetime import datetime
import subprocess
import sys
import time
import threading

def filtrar_e_mover_cards():
    """
    Filtra e move cards da triagem antes de gerar o arquivo
    """
    try:
        print("\n FILTRANDO E MOVENDO CARDS")
        print("=" * 40)
        
        # Importar e executar a funo de movecards
        import movecards
        resultado = movecards.filtrar_cards_triagem()
        
        if resultado:
            print(f" Filtro executado com sucesso!")
            print(f" Cards movimentveis: {len(resultado.get('cards_movimentaveis', []))}")
            print(f" Cards bloqueados: {len(resultado.get('cards_bloqueados', []))}")
            print(f" Cards movidos: {len(resultado.get('cards_movidos', []))}")
            if resultado.get('cards_com_erro'):
                print(f" Cards com erro: {len(resultado['cards_com_erro'])}")
            return True
        else:
            print(" Nenhum resultado do filtro de cards")
            return False
            
    except Exception as e:
        print(f" Erro ao filtrar cards: {e}")
        return False


def iniciar_move_cards_periodico(intervalo_segundos: int = 30):
    """
    Inicia um thread daemon que executa filtrar_e_mover_cards() a cada N segundos.
    Retorna um Event para sinalizar parada.
    """
    stop_event = threading.Event()

    def _worker():
        while not stop_event.is_set():
            try:
                filtrar_e_mover_cards()
            except Exception as e:
                print(f"Aviso: falha no move-cards periodico: {e}")
            # espera com possibilidade de parada antecipada
            stop_event.wait(intervalo_segundos)

    t = threading.Thread(target=_worker, daemon=True)
    t.start()
    return stop_event

def descobrir_report_id(pipe_id, headers):
    """
    Descobre o ID do report padro do pipe para usar na exportao
    """
    
    print(" Descobrindo report ID...")
    
    try:
        # Query para buscar reports do pipe (corrigida)
        reports_query = """
        query GetPipeReports($pipeId: ID!) {
            pipe(id: $pipeId) {
                reports {
                    id
                    name
                }
            }
        }
        """
        
        response = requests.post(
            "https://api.pipefy.com/graphql",
            headers=headers,
            json={
                "query": reports_query,
                "variables": {"pipeId": pipe_id}
            }
        )
        
        if response.status_code != 200:
            print(f" Erro HTTP ao buscar reports: {response.status_code}")
            return None
        
        result = response.json()
        
        if "errors" in result:
            print(f" Erro GraphQL ao buscar reports: {result['errors']}")
            return None
        
        reports = result["data"]["pipe"]["reports"]
        
        if not reports:
            print(" Nenhum report encontrado no pipe")
            return None
        
        # Mostrar todos os reports disponveis
        print(f" Reports encontrados:")
        for i, report in enumerate(reports, 1):
            print(f"   {i}. {report['name']} (ID: {report['id']})")
        
        # Usar o primeiro report (normalmente  o padro)
        report_id = reports[0]["id"]
        report_name = reports[0]["name"]
        
        print(f" Usando report: '{report_name}' (ID: {report_id})")
        return report_id
        
    except Exception as e:
        print(f" Erro ao descobrir report ID: {e}")
        return None


def gerar_arquivo_pipefy(pipe_id, headers, pasta_saida=None):
    """
    Gera arquivo Excel usando a API oficial do Pipefy
    
    Args:
        pipe_id (str): ID do pipe no Pipefy
        headers (dict): Headers com token de autenticao
        pasta_saida (str): Pasta onde salvar o arquivo. Se None, usa Downloads
    """
    
    print(f"\n GERANDO ARQUIVO EXCEL VIA API DO PIPEFY")
    print("=" * 50)
    
    try:
        print(f" Pipe ID: {pipe_id}")
        
        # 1. Descobrir o report ID
        report_id = descobrir_report_id(pipe_id, headers)
        
        if not report_id:
            print(" No foi possvel encontrar report para exportao")
            return None
        
        # 2. Iniciar a exportao
        print(f"\n Iniciando exportao do report...")
        
        export_mutation = """
        mutation ExportPipeReport($pipeId: ID!, $reportId: ID!) {
            exportPipeReport(input: {
                pipeId: $pipeId,
                pipeReportId: $reportId
            }) {
                pipeReportExport {
                    id
                }
            }
        }
        """
        
        response = requests.post(
            "https://api.pipefy.com/graphql",
            headers=headers,
            json={
                "query": export_mutation,
                "variables": {
                    "pipeId": pipe_id,
                    "reportId": report_id
                }
            }
        )
        
        if response.status_code != 200:
            print(f" Erro HTTP ao iniciar exportao: {response.status_code}")
            return None
        
        result = response.json()
        
        if "errors" in result:
            print(f" Erro GraphQL ao iniciar exportao: {result['errors']}")
            return None
        
        export_id = result["data"]["exportPipeReport"]["pipeReportExport"]["id"]
        print(f" Exportao iniciada! ID: {export_id}")
        
        # 3. Aguardar concluso e obter URL do arquivo
        print(f"\n Aguardando processamento do arquivo...")
        
        max_tentativas = 60  # Mximo 10 minutos
        tentativa = 0
        
        # Marca para agendamento do move-cards peridico
        ultimo_move = time.time()

        while tentativa < max_tentativas:
            # Dispara move-cards a cada 30s enquanto aguarda
            try:
                if time.time() - ultimo_move >= 30:
                    print("\nAtualizando fila: mover cards de Triagem para Em Analise...")
                    filtrar_e_mover_cards()
                    ultimo_move = time.time()
            except Exception as _e:
                print(f"Aviso: falha ao mover cards durante polling: {_e}")
            time.sleep(10)  # Aguarda 10 segundos
            tentativa += 1
            
            print(f"   Verificao {tentativa}/{max_tentativas}...")
            
            # Query para verificar status da exportao
            status_query = """
            query GetExportStatus($exportId: ID!) {
                pipeReportExport(id: $exportId) {
                    fileURL
                    finishedAt
                }
            }
            """
            
            response = requests.post(
                "https://api.pipefy.com/graphql",
                headers=headers,
                json={
                    "query": status_query,
                    "variables": {"exportId": export_id}
                }
            )
            
            if response.status_code != 200:
                print(f"    Erro HTTP ao verificar status: {response.status_code}")
                continue
            
            result = response.json()
            
            if "errors" in result:
                print(f"    Erro GraphQL ao verificar status: {result['errors']}")
                continue
            
            export_data = result["data"]["pipeReportExport"]
            
            if export_data["finishedAt"] and export_data["fileURL"]:
                file_url = export_data["fileURL"]
                print(f"\nArquivo pronto!")
                
                # 4. Baixar o arquivo
                return baixar_arquivo(file_url, pasta_saida)
            else:
                print(f"    Ainda processando...")
        
        print(f" Timeout: Exportao demorou mais de {max_tentativas * 10} segundos")
        return None
        
    except Exception as e:
        print(f" Erro ao gerar arquivo: {e}")
        return None


def baixar_arquivo(file_url, pasta_saida=None):
    """
    Baixa o arquivo Excel gerado pelo Pipefy
    
    Args:
        file_url (str): URL do arquivo no Pipefy
        pasta_saida (str): Pasta onde salvar o arquivo. Se None, usa Downloads
    """
    
    print("\nBAIXANDO ARQUIVO")
    print("=" * 30)
    
    try:
        # Definir pasta de saida
        if pasta_saida is None:
            # Usar pasta Downloads do usurio
            pasta_saida = os.path.join(os.path.expanduser("~"), "Downloads")
        
        # Criar pasta se no existir
        os.makedirs(pasta_saida, exist_ok=True)
        
        # Gerar nome do arquivo com timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nome_arquivo = f"pipefy_liquidacao_{timestamp}.xlsx"
        caminho_arquivo = os.path.join(pasta_saida, nome_arquivo)
        
        print(f" Baixando arquivo...")
        print(f" Nome: {nome_arquivo}")
        
        # Baixar o arquivo
        response = requests.get(file_url, timeout=120)
        
        if response.status_code != 200:
            print(f" Erro HTTP ao baixar arquivo: {response.status_code}")
            return None
        
        # Salvar arquivo
        with open(caminho_arquivo, 'wb') as f:
            f.write(response.content)
        
        # Verificar se o arquivo foi salvo
        if os.path.exists(caminho_arquivo):
            tamanho = os.path.getsize(caminho_arquivo)
            print(f"Arquivo baixado com sucesso!")
            print(f"Tamanho: {tamanho:,} bytes ({tamanho/1024:.1f} KB)")
            print(f"Pasta: {pasta_saida}")
            print(f"Caminho completo: {caminho_arquivo}")
            
            return caminho_arquivo
        else:
            print(f"Erro: Arquivo no foi criado")
            return None
            
    except Exception as e:
        print(f" Erro ao baixar arquivo: {e}")
        return None


def executar_pipeliquidacao(caminho_arquivo, data_pagamento):
    """
    Executa o cdigo pipeliquidao automaticamente com o arquivo gerado
    Usa a data fornecida pelo launcher
    """
    
    print(f"\n EXECUTANDO PIPELIQUIDAO")
    print("=" * 40)
    
    try:
        # Verificar se o arquivo pipeliquidacao.py existe
        script_pipeliquidacao = "pipeliquidacao.py"
        
        if not os.path.exists(script_pipeliquidacao):
            print(f" Arquivo {script_pipeliquidacao} no encontrado!")
            print(f" Diretrio atual: {os.getcwd()}")
            return False
        
        print(f" Script encontrado: {script_pipeliquidacao}")
        print(f" Arquivo de entrada: {os.path.basename(caminho_arquivo)}")
        print(f" Data de processamento: {data_pagamento}")
        
        # Executar o script pipeliquidacao
        print(f"\n Executando pipeliquidao...")
        
        # Comando para executar o script Python com os argumentos corretos
        comando = [
            sys.executable,  # Usa o mesmo Python que est executando este script
            script_pipeliquidacao,
            "--input", caminho_arquivo,  # Arquivo Excel gerado
            "--data", data_pagamento     # Data fornecida pelo launcher
        ]
        
        resultado = subprocess.run(
            comando,
            capture_output=True,
            text=True,
            timeout=300  # Timeout de 5 minutos
        )
        
        print(f" Sada do pipeliquidao:")
        print("-" * 40)
        if resultado.stdout:
            print(resultado.stdout)
        
        if resultado.stderr:
            print(f" Erros/Avisos:")
            print(resultado.stderr)
        
        if resultado.returncode == 0:
            print(f" Pipeliquidao executado com sucesso!")
            return True
        else:
            print(f" Pipeliquidao falhou com cdigo: {resultado.returncode}")
            return False
        
    except subprocess.TimeoutExpired:
        print(f" Timeout: Pipeliquidao demorou mais de 5 minutos")
        return False
    except Exception as e:
        print(f" Erro ao executar pipeliquidao: {e}")
        return False


def main(data_pagamento=None, pasta_saida=None):
    """
    Funo principal que orquestra todo o processo usando API oficial do Pipefy
    
    Args:
        data_pagamento (str): Data no formato DD/MM/YYYY para processamento
        pasta_saida (str): Pasta onde salvar os arquivos. Se None, usa Downloads
    """
    
    # Se no fornecida, usa data de hoje
    if data_pagamento is None:
        data_pagamento = datetime.now().strftime("%d/%m/%Y")
    
    # Token funcionando
    api_token = "eyJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJQaXBlZnkiLCJpYXQiOjE3NjExMzkxNDcsImp0aSI6ImM1NzhhYzM5LTUwZmUtNGI0NC1iMzYzLWE5ZjNhMzBmNjUwYyIsInN1YiI6MzA2ODY4NTY3LCJ1c2VyIjp7ImlkIjozMDY4Njg1NjcsImVtYWlsIjoiZ3VzdGF2by5wcm9tZXR0aUBrYW5hc3RyYS5jb20uYnIifSwidXNlcl90eXBlIjoiYXV0aGVudGljYXRlZCJ9.hjcPATGMMX1xBcRMHQ7gfjkvqB7Nq9w0Ou9tD33fIlmLoicU928x5sd_T_nmkL04DV37GtxFtF5mCFaFSa4fVQ"
    
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json"
    }
    
    print(" AUTOMAO COMPLETA: PIPEFY  ARQUIVO  PIPELIQUIDAO")
    print("=" * 60)
    print(f" Incio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f" Data de processamento: {data_pagamento}")
    print()
    
    try:
        pipe_id = "303418384"  # ID do pipe "1 - A Liquidao"
        
        # 1. Filtrar e mover cards da triagem para anlise
        sucesso_filtro = filtrar_e_mover_cards()
        if not sucesso_filtro:
            print(" Falha no filtro de cards, mas continuando com gerao do arquivo...")
        
        # 2. Gerar arquivo usando API oficial do Pipefy
        caminho_arquivo = gerar_arquivo_pipefy(pipe_id, headers, pasta_saida)
        
        if not caminho_arquivo:
            print(" Falha ao gerar arquivo via API. Processo interrompido.")
            return False
        
        # 3. Executar pipeliquidao com o arquivo gerado e a data fornecida
        sucesso = executar_pipeliquidacao(caminho_arquivo, data_pagamento)
        
        # 4. Resumo final
        print(f"\n PROCESSO CONCLUDO")
        print("=" * 30)
        print(f" Mtodo: API Oficial do Pipefy")
        print(f" Filtro de cards: {' Sucesso' if sucesso_filtro else ' Com avisos'}")
        print(f" Arquivo: {os.path.basename(caminho_arquivo)}")
        print(f" Pipeliquidao: {' Sucesso' if sucesso else ' Falha'}")
        print(f" Data utilizada: {data_pagamento}")
        print(f" Fim: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        return sucesso
        
    except Exception as e:
        print(f" Erro geral no processo: {e}")
        return False


if __name__ == "__main__":
    main()
