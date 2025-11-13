"""
Módulo para buscar extratos bancários da API Santander
Usa o token de autenticação gerado pelo módulo credenciais_bancos
"""

import requests
import json
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional
import logging
from credenciais_bancos import SantanderAuth

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SantanderExtratos:
    """
    Classe para buscar extratos bancários do Santander
    """
    
    def __init__(self, santander_auth: SantanderAuth, 
                 conta_padrao: str = None, agencia_padrao: str = None):
        """
        Inicializa o cliente de extratos
        
        Args:
            santander_auth: Instância configurada de SantanderAuth
            conta_padrao: Número da conta padrão (opcional)
            agencia_padrao: Código da agência padrão (opcional)
        """
        self.auth = santander_auth
        self.api_base = self.auth.base_urls[self.auth.ambiente]['api']
        
        # Conta e agência padrão para simplificar requisições
        self.conta_padrao = conta_padrao
        self.agencia_padrao = agencia_padrao
        
        # Diretório para salvar extratos
        self.extratos_dir = Path("Extratos")
        self.extratos_dir.mkdir(exist_ok=True)
        
        logger.info("Cliente de extratos Santander inicializado")
    
    def _get_headers(self) -> Dict[str, str]:
        """
        Prepara os headers para requisições à API
        
        Returns:
            Dicionário com headers incluindo token de autenticação
        """
        # Garante que temos um token válido
        if not self.auth._is_token_valid():
            logger.info("Token expirado, obtendo novo token...")
            self.auth.obter_token_acesso()
        
        token = self.auth.token_data['access_token']
        
        return {
            "Authorization": f"Bearer {token}",
            "X-Application-Key": self.auth.client_id,
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive"
        }
    
    def buscar_extrato(self, account_number: str, branch_code: str, 
                       data_inicio: str, data_fim: str, 
                       account_id: str = None, bank_id: str = "0033") -> Dict[str, Any]:
        """
        Busca extrato de uma conta
        
        Args:
            account_number: Número da conta (ex: "130163172")
            branch_code: Código da agência (ex: "2271" ou "0001")
            data_inicio: Data inicial no formato 'YYYY-MM-DD'
            data_fim: Data final no formato 'YYYY-MM-DD'
            account_id: ID da conta (obrigatório na maioria dos casos)
            bank_id: Código do banco com 4 dígitos (padrão: "0033" para Santander)
        
        Returns:
            Dados do extrato em formato JSON
        """
        # Endpoint conforme documentação - Consulta de Extrato
        endpoint = f"/bank_account_information/v1/banks/{bank_id}/statements"
        url = f"{self.api_base}{endpoint}"
        
        # Query Parameters conforme documentação
        params = {
            "accountNumber": account_number,
            "branchCode": branch_code,
            "initialDate": data_inicio,
            "finalDate": data_fim
        }
        
        # accountId geralmente é obrigatório
        if account_id:
            params["accountId"] = account_id
        else:
            # Se não fornecido, usa o número da conta como ID
            params["accountId"] = account_number
        
        headers = self._get_headers()
        cert_tuple = self.auth._get_cert_tuple()
        
        try:
            logger.info(f"Buscando extrato - Conta: {account_number}, Agência: {branch_code}, Período: {data_inicio} a {data_fim}")
            logger.info(f"URL: {url}")
            logger.info(f"Params: {params}")
            logger.info(f"Headers: {headers}")
            
            response = requests.get(
                url,
                headers=headers,
                params=params,
                cert=cert_tuple,
                verify=True,
                timeout=60
            )
            
            logger.info(f"Status Code: {response.status_code}")
            logger.info(f"Response: {response.text[:500]}")  # Primeiros 500 caracteres
            
            response.raise_for_status()
            extrato_data = response.json()
            
            transactions = extrato_data.get('_content', [])
            logger.info(f"Extrato obtido com sucesso - {len(transactions)} transações")
            return extrato_data
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"Erro HTTP ao buscar extrato: {e}")
            if hasattr(e.response, 'text'):
                logger.error(f"Resposta: {e.response.text}")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro na requisição: {e}")
            raise
    
    def buscar_comprovantes(self, conta: str, data_inicio: str, data_fim: str) -> List[Dict[str, Any]]:
        """
        Busca comprovantes de pagamento (vouchers)
        
        Args:
            conta: Número da conta
            data_inicio: Data inicial no formato 'YYYY-MM-DD'
            data_fim: Data final no formato 'YYYY-MM-DD'
        
        Returns:
            Lista de comprovantes
        """
        # Endpoint para comprovantes/vouchers
        endpoint = f"/vouchers/v1/accounts/{conta}/payment-receipts"
        url = f"{self.api_base}{endpoint}"
        
        params = {
            "startDate": data_inicio,
            "endDate": data_fim
        }
        
        headers = self._get_headers()
        cert_tuple = self.auth._get_cert_tuple()
        
        try:
            logger.info(f"Buscando comprovantes da conta {conta} de {data_inicio} até {data_fim}")
            
            response = requests.get(
                url,
                headers=headers,
                params=params,
                cert=cert_tuple,
                verify=True
            )
            
            response.raise_for_status()
            comprovantes = response.json()
            
            logger.info(f"Comprovantes obtidos com sucesso")
            return comprovantes
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"Erro HTTP ao buscar comprovantes: {e}")
            if hasattr(e.response, 'text'):
                logger.error(f"Resposta: {e.response.text}")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro na requisição: {e}")
            raise
    
    def salvar_extrato(self, extrato: Dict[str, Any], conta: str, agencia: str,
                       data_inicio: str, data_fim: str, cliente: str = None):
        """
        Salva o extrato em arquivo JSON
        
        Args:
            extrato: Dados do extrato
            conta: Número da conta
            agencia: Código da agência
            data_inicio: Data inicial
            data_fim: Data final
            cliente: Nome do cliente (opcional)
        """
        # Cria subdiretório com a data atual
        data_hoje = datetime.now().strftime("%Y%m%d")
        dir_data = self.extratos_dir / data_hoje
        
        # Se tiver nome do cliente, cria subpasta
        if cliente:
            dir_final = dir_data / cliente
        else:
            dir_final = dir_data / f"Agencia_{agencia}"
        
        dir_final.mkdir(parents=True, exist_ok=True)
        
        # Nome do arquivo
        if cliente:
            nome_arquivo = f"{cliente}_extrato_{data_inicio}_{data_fim}.json"
        else:
            nome_arquivo = f"conta_{conta}_ag_{agencia}_extrato_{data_inicio}_{data_fim}.json"
        
        caminho_completo = dir_final / nome_arquivo
        
        try:
            with open(caminho_completo, 'w', encoding='utf-8') as f:
                json.dump(extrato, f, indent=4, ensure_ascii=False)
            logger.info(f"Extrato salvo em: {caminho_completo}")
            return str(caminho_completo)
        except Exception as e:
            logger.error(f"Erro ao salvar extrato: {e}")
            raise
    
    def buscar_e_salvar_extrato(self, conta: str, agencia: str, 
                                 data_inicio: str, data_fim: str, 
                                 cliente: str = None) -> str:
        """
        Busca e salva o extrato automaticamente
        
        Args:
            conta: Número da conta
            agencia: Código da agência
            data_inicio: Data inicial no formato 'YYYY-MM-DD'
            data_fim: Data final no formato 'YYYY-MM-DD'
            cliente: Nome do cliente para organização (opcional)
        
        Returns:
            Caminho do arquivo salvo
        """
        # Busca o extrato
        extrato = self.buscar_extrato(conta, agencia, data_inicio, data_fim)
        
        # Salva o extrato
        caminho = self.salvar_extrato(extrato, conta, agencia, data_inicio, data_fim, cliente)
        
        return caminho
    
    def buscar_extrato_periodo(self, conta: str = None, agencia: str = None, 
                                dias: int = 30, cliente: str = None) -> str:
        """
        Busca extrato dos últimos N dias
        
        Args:
            conta: Número da conta (usa padrão se não informado)
            agencia: Código da agência (usa padrão se não informado)
            dias: Número de dias para buscar (padrão: 30)
            cliente: Nome do cliente (opcional)
        
        Returns:
            Caminho do arquivo salvo
        """
        # Usa valores padrão se não informados
        conta = conta or self.conta_padrao
        agencia = agencia or self.agencia_padrao
        
        if not conta or not agencia:
            raise ValueError("Conta e agência devem ser informados ou configurados como padrão")
        
        data_fim = date.today()
        data_inicio = data_fim - timedelta(days=dias)
        
        return self.buscar_e_salvar_extrato(
            conta,
            agencia,
            data_inicio.strftime("%Y-%m-%d"),
            data_fim.strftime("%Y-%m-%d"),
            cliente
        )
    
    def buscar_por_data(self, data_inicio: str, data_fim: str, 
                        conta: str = None, agencia: str = None, 
                        cliente: str = None) -> str:
        """
        Busca extrato por período específico (versão simplificada)
        Usa conta/agência padrão se não informados
        
        Args:
            data_inicio: Data inicial no formato 'YYYY-MM-DD'
            data_fim: Data final no formato 'YYYY-MM-DD'
            conta: Número da conta (opcional se configurado padrão)
            agencia: Código da agência (opcional se configurado padrão)
            cliente: Nome do cliente (opcional)
        
        Returns:
            Caminho do arquivo salvo
        """
        # Usa valores padrão se não informados
        conta = conta or self.conta_padrao
        agencia = agencia or self.agencia_padrao
        
        if not conta or not agencia:
            raise ValueError("Conta e agência devem ser informados ou configurados como padrão")
        
        return self.buscar_e_salvar_extrato(conta, agencia, data_inicio, data_fim, cliente)
    
    def buscar_multiplas_contas(self, contas: List[Dict[str, str]], 
                                 data_inicio: str, data_fim: str) -> Dict[str, str]:
        """
        Busca extratos de múltiplas contas
        
        Args:
            contas: Lista de dicionários com 'conta' e 'cliente'
                   Exemplo: [{'conta': '12345', 'cliente': 'Empresa A'}]
            data_inicio: Data inicial
            data_fim: Data final
        
        Returns:
            Dicionário com conta -> caminho do arquivo
        """
        resultados = {}
        
        for item in contas:
            conta = item.get('conta')
            cliente = item.get('cliente', conta)
            
            try:
                logger.info(f"Processando conta {conta} - Cliente: {cliente}")
                caminho = self.buscar_e_salvar_extrato(conta, data_inicio, data_fim, cliente)
                resultados[conta] = caminho
                logger.info(f"✅ Conta {conta} processada com sucesso")
            except Exception as e:
                logger.error(f"❌ Erro ao processar conta {conta}: {e}")
                resultados[conta] = f"ERRO: {str(e)}"
        
        return resultados


# Exemplo de uso
if __name__ == "__main__":
    print("\n" + "="*60)
    print("BUSCAR EXTRATOS SANTANDER")
    print("="*60)
    
    # ============================================================
    # CONFIGURAÇÃO
    # ============================================================
    CLIENT_ID = "WUrgXgftrP3G9iZXXIqljABiFx9oRBUC"
    CLIENT_SECRET = "e4FAtyTG6mbDKPFV"
    CERT_PEM_PATH = r"C:\Users\GustavoPrometti\Cert\santander_cert.pem"
    KEY_PEM_PATH = r"C:\Users\GustavoPrometti\Cert\santander_key.pem"
    
    try:
        # Inicializa autenticação
        print("\n⏳ Autenticando...")
        santander_auth = SantanderAuth(
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            cert_path=CERT_PEM_PATH,
            key_path=KEY_PEM_PATH,
            ambiente="producao"
        )
        
        # Obtém token
        santander_auth.obter_token_acesso()
        print("✅ Autenticado com sucesso!")
        
        # Dados da conta padrão
        CONTA = "130163172"
        AGENCIA = "2271"
        
        # Inicializa cliente de extratos com conta padrão
        extrator = SantanderExtratos(
            santander_auth,
            conta_padrao=CONTA,
            agencia_padrao=AGENCIA
        )
        
        # ============================================================
        # EXEMPLO DE USO
        # ============================================================
        
        print("\n" + "-"*60)
        print("BUSCAR EXTRATO DA CONTA")
        print("-"*60)
        
        # OPÇÃO 1: Buscar por período (últimos N dias)
        print(f"\n⏳ Buscando extrato dos últimos 30 dias...")
        print(f"Conta: {CONTA} | Agência: {AGENCIA}")
        
        caminho = extrator.buscar_extrato_periodo(dias=30, cliente="TESTE")
        print(f"✅ Extrato salvo em: {caminho}")
        
        # OPÇÃO 2: Buscar por datas específicas (apenas token + datas)
        print(f"\n⏳ Buscando extrato por período específico...")
        caminho2 = extrator.buscar_por_data(
            data_inicio="2025-10-01",
            data_fim="2025-11-05"
        )
        print(f"✅ Extrato salvo em: {caminho2}")
        
        print("\n✅ Processo concluído!")
        
    except Exception as e:
        print(f"\n❌ Erro: {e}")
        import traceback
        traceback.print_exc()
