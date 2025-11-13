#!/usr/bin/env python3
"""
Automação completa: Gera arquivo Excel via API Pipefy para o Pipe de Taxas Anbima e executa PipeTaxas automaticamente
Pipe: Taxas Anbima (ID: 303808557)
"""

import requests
import json
import os
from datetime import datetime
import subprocess
import sys
import time

def descobrir_report_id(pipe_id, headers):
    """
    Descobre o ID do report padrão do pipe para usar na exportação
    """
    
    print("Descobrindo report ID...")
    
    query = """
    query($pipeId: ID!) {
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
            "query": query,
            "variables": {"pipeId": pipe_id}
        },
        timeout=30
    )
    
    if response.status_code != 200:
        print(f"Erro ao consultar reports: {response.status_code}")
        return None
    
    result = response.json()
    if "errors" in result:
        print(f"Erro GraphQL: {result['errors']}")
        return None
    
    reports = result["data"]["pipe"]["reports"]
    
    print(f"Reports encontrados:")
    for i, report in enumerate(reports, 1):
        print(f"   {i}. {report['name']} (ID: {report['id']})")
    
    if not reports:
        print("Nenhum report encontrado!")
        return None
    
    # Procurar especificamente pelo relatório "ArquivoSaída"
    for report in reports:
        if "arquivosaida" in report["name"].lower().replace(" ", "").replace("í", "i"):
            print(f"Usando report: '{report['name']}' (ID: {report['id']})")
            return report["id"]
    
    # Fallback: procurar por relatórios com palavras-chave
    for report in reports:
        if "gerar" in report["name"].lower() or "exportar" in report["name"].lower() or "saida" in report["name"].lower():
            print(f"Usando report: '{report['name']}' (ID: {report['id']})")
            return report["id"]
    
    # Se não encontrar, usar o primeiro
    primeiro_report = reports[0]
    print(f"Usando primeiro report disponível: '{primeiro_report['name']}' (ID: {primeiro_report['id']})")
    return primeiro_report["id"]


def iniciar_exportacao(pipe_id, report_id, headers):
    """
    Inicia a exportação do report do pipe usando a API oficial do Pipefy
    """
    
    print(f"\nIniciando exportação do report...")
    
    mutation = """
    mutation($pipeId: ID!, $pipeReportId: ID!) {
        exportPipeReport(input: {
            pipeId: $pipeId,
            pipeReportId: $pipeReportId
        }) {
            pipeReportExport {
                id
                startedAt
            }
        }
    }
    """
    
    response = requests.post(
        "https://api.pipefy.com/graphql",
        headers=headers,
        json={
            "query": mutation,
            "variables": {
                "pipeId": pipe_id,
                "pipeReportId": report_id
            }
        },
        timeout=30
    )
    
    if response.status_code != 200:
        print(f"Erro ao iniciar exportação: {response.status_code}")
        return None
    
    result = response.json()
    if "errors" in result:
        print(f"Erro GraphQL: {result['errors']}")
        return None
    
    export_id = result["data"]["exportPipeReport"]["pipeReportExport"]["id"]
    print(f"Exportação iniciada! ID: {export_id}")
    
    return export_id


def aguardar_arquivo(export_id, headers, timeout_segundos=300):
    """
    Aguarda o processamento do arquivo e retorna a URL de download
    """
    
    print(f"\nAguardando processamento do arquivo...")
    
    query = """
    query($exportId: ID!) {
        pipeReportExport(id: $exportId) {
            id
            finishedAt
            fileURL
            state
        }
    }
    """
    
    tentativas = 0
    max_tentativas = timeout_segundos // 5  # Verifica a cada 5 segundos
    
    while tentativas < max_tentativas:
        tentativas += 1
        print(f"   Verificação {tentativas}/{max_tentativas}...")
        
        response = requests.post(
            "https://api.pipefy.com/graphql",
            headers=headers,
            json={
                "query": query,
                "variables": {"exportId": export_id}
            },
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            if "data" in result and result["data"]["pipeReportExport"]:
                export_data = result["data"]["pipeReportExport"]
                
                if export_data["finishedAt"] and export_data["fileURL"]:
                    file_url = export_data["fileURL"]
                    print(f"\nArquivo pronto!")
                    return file_url
        
        time.sleep(5)
    
    print(f"Timeout: Arquivo não ficou pronto em {timeout_segundos} segundos")
    return None


def baixar_arquivo(file_url, pasta_saida=None):
    """
    Baixa o arquivo Excel gerado
    
    Args:
        file_url (str): URL do arquivo no Pipefy
        pasta_saida (str): Pasta onde salvar o arquivo. Se None, usa Downloads
    """
    
    print(f"\nBAIXANDO ARQUIVO")
    print("=" * 30)
    
    try:
        # Definir pasta de saída
        if pasta_saida is None:
            # Usar pasta Downloads do usuário
            pasta_saida = os.path.join(os.path.expanduser("~"), "Downloads")
        
        # Criar pasta se não existir
        os.makedirs(pasta_saida, exist_ok=True)
        
        print(f"Baixando arquivo...")
        
        response = requests.get(file_url, timeout=60)
        response.raise_for_status()
        
        # Gerar nome do arquivo
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nome_arquivo = f"pipefy_taxasanbima_{timestamp}.xlsx"
        caminho_completo = os.path.join(pasta_saida, nome_arquivo)
        
        with open(caminho_completo, 'wb') as f:
            f.write(response.content)
        
        print(f"Nome: {nome_arquivo}")
        print(f"Arquivo baixado com sucesso!")
        print(f"Tamanho: {len(response.content):,} bytes ({len(response.content)/1024:.1f} KB)")
        print(f"Pasta: {pasta_saida}")
        print(f"Caminho completo: {caminho_completo}")
        
        return caminho_completo
        
    except Exception as e:
        print(f"Erro ao baixar arquivo: {e}")
        return None


def gerar_arquivo_pipefy(pipe_id, headers, pasta_saida=None):
    """
    Orquestra todo o processo de geração do arquivo via API do Pipefy
    
    Args:
        pipe_id (str): ID do pipe no Pipefy
        headers (dict): Headers com token de autenticação
        pasta_saida (str): Pasta onde salvar o arquivo. Se None, usa Downloads
    """
    
    print(f"\nGERANDO ARQUIVO EXCEL VIA API DO PIPEFY")
    print("=" * 50)
    print(f"Pipe ID: {pipe_id}")
    
    try:
        # 1. Descobrir report ID
        report_id = descobrir_report_id(pipe_id, headers)
        if not report_id:
            return None
        
        # 2. Iniciar exportação
        export_id = iniciar_exportacao(pipe_id, report_id, headers)
        if not export_id:
            return None
        
        # 3. Aguardar processamento
        file_url = aguardar_arquivo(export_id, headers)
        if not file_url:
            return None
        
        # 4. Baixar arquivo
        caminho_arquivo = baixar_arquivo(file_url, pasta_saida)
        if not caminho_arquivo:
            return None
        
        return caminho_arquivo
        
    except Exception as e:
        print(f"Erro no processo de geração: {e}")
        return None


def executar_pipetaxas(caminho_arquivo, data_pagamento):
    """
    Executa o código PipeTaxas automaticamente com o arquivo gerado
    Salva os arquivos de saída na mesma pasta do arquivo de entrada
    
    Args:
        caminho_arquivo (str): Caminho completo do arquivo do Pipefy
        data_pagamento (str): Data no formato DD/MM/YYYY
    """
    
    print(f"\nEXECUTANDO PIPETAXAS")
    print("=" * 30)
    
    try:
        # Verificar se o arquivo PipeTaxas.py existe
        script_pipetaxas = "PipeTaxas.py"
        
        if not os.path.exists(script_pipetaxas):
            print(f"Arquivo {script_pipetaxas} não encontrado!")
            print(f"Diretório atual: {os.getcwd()}")
            return False
        
        print(f"Script encontrado: {script_pipetaxas}")
        print(f"Arquivo de entrada: {os.path.basename(caminho_arquivo)}")
        print(f"Data de processamento: {data_pagamento}")
        
        # Vamos chamar diretamente a função run_pipe_taxas do módulo
        try:
            from pathlib import Path
            import PipeTaxas
            
            # Gerar nome do arquivo de saída na MESMA PASTA do arquivo de entrada
            pasta_entrada = os.path.dirname(caminho_arquivo)
            timestamp = datetime.now().strftime("%Y%m%d")
            nome_saida = f"TaxasAnbima_{timestamp}.xlsx"
            caminho_saida = os.path.join(pasta_entrada, nome_saida)
            
            print(f"\nExecutando PipeTaxas...")
            print(f"Arquivo de saída: {nome_saida}")
            print(f"Pasta de saída: {pasta_entrada}")
            
            # Chamar a função run_pipe_taxas
            resultado = PipeTaxas.run_pipe_taxas(
                input_file=Path(caminho_arquivo),
                data_pagamento=data_pagamento,
                saida_path=Path(caminho_saida)
            )
            
            print(f"\nRESULTADO DO PIPETAXAS:")
            print("-" * 40)
            print(f"Processamento concluído!")
            print(f"Arquivo FINAL: {resultado.get('saida_taxas_final', 'N/A')}")
            if resultado.get('saida_taxas_pendentes'):
                print(f"Arquivo PENDENTES: {resultado['saida_taxas_pendentes']}")
            else:
                print(f"Sem pendências!")
            
            print(f"Total de registros: {resultado.get('qtd_total', 0)}")
            print(f"Registros processados: {resultado.get('qtd_ok', 0)}")
            print(f"Registros pendentes: {resultado.get('qtd_pendentes', 0)}")
            
            return True
            
        except ImportError as e:
            print(f"Erro ao importar PipeTaxas: {e}")
            return False
        except Exception as e:
            print(f"Erro ao executar PipeTaxas: {e}")
            return False
        
    except Exception as e:
        print(f"Erro geral ao executar PipeTaxas: {e}")
        return False


def main(data_pagamento=None, pasta_saida=None):
    """
    Função principal que orquestra todo o processo usando API oficial do Pipefy
    
    Args:
        data_pagamento (str): Data no formato DD/MM/YYYY para processamento
        pasta_saida (str): Pasta onde salvar os arquivos. Se None, usa Downloads
    """
    
    # Se não fornecida, usa data de hoje
    if data_pagamento is None:
        data_pagamento = datetime.now().strftime("%d/%m/%Y")
    
    # Token funcionando
    api_token = "eyJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJQaXBlZnkiLCJpYXQiOjE3NjExMzkxNDcsImp0aSI6ImM1NzhhYzM5LTUwZmUtNGI0NC1iMzYzLWE5ZjNhMzBmNjUwYyIsInN1YiI6MzA2ODY4NTY3LCJ1c2VyIjp7ImlkIjozMDY4Njg1NjcsImVtYWlsIjoiZ3VzdGF2by5wcm9tZXR0aUBrYW5hc3RyYS5jb20uYnIifSwidXNlcl90eXBlIjoiYXV0aGVudGljYXRlZCJ9.hjcPATGMMX1xBcRMHQ7gfjkvqB7Nq9w0Ou9tD33fIlmLoicU928x5sd_T_nmkL04DV37GtxFtF5mCFaFSa4fVQ"
    
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json"
    }
    
    print("AUTOMACAO COMPLETA: PIPEFY TAXAS ANBIMA -> ARQUIVO -> PIPETAXAS")
    print("=" * 65)
    print(f"Inicio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Data de processamento: {data_pagamento}")
    
    # Mostrar pasta de saída
    if pasta_saida is None:
        pasta_destino = os.path.join(os.path.expanduser("~"), "Downloads")
        print(f"Pasta de saida: {pasta_destino} (padrao)")
    else:
        print(f"Pasta de saida: {pasta_saida}")
    print()
    
    try:
        # Pipe de Taxas Anbima
        pipe_id = "303808557"  # Pipe "Taxas Anbima"
        
        print(f"Usando pipe: 'Taxas Anbima' (ID: {pipe_id})")
        
        # 1. Gerar arquivo usando API oficial do Pipefy
        caminho_arquivo = gerar_arquivo_pipefy(pipe_id, headers, pasta_saida)
        
        if not caminho_arquivo:
            print("Falha ao gerar arquivo via API. Processo interrompido.")
            return False
        
        # 2. Executar PipeTaxas com o arquivo gerado e a data fornecida
        sucesso = executar_pipetaxas(caminho_arquivo, data_pagamento)
        
        # 3. Resumo final
        print(f"\nPROCESSO CONCLUÍDO")
        print("=" * 30)
        print(f"Método: API Oficial do Pipefy")
        print(f"Arquivo: {os.path.basename(caminho_arquivo)}")
        print(f"PipeTaxas: {'Sucesso' if sucesso else 'Falha'}")
        print(f"Data utilizada: {data_pagamento}")
        print(f"Fim: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        return sucesso
        
    except Exception as e:
        print(f"Erro geral no processo: {e}")
        return False


if __name__ == "__main__":
    main()
