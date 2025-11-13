"""
Módulo para buscar comprovantes de pagamento da API Santander
Usa o token de autenticação gerado pelo módulo credenciais_bancos
"""

import requests
import json
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional
import logging
import time

# Import condicional para compatibilidade com Streamlit Cloud
try:
    from credenciais_bancos import SantanderAuth
    HAS_CREDENCIAIS = True
except ImportError:
    HAS_CREDENCIAIS = False
    SantanderAuth = None  # Placeholder para evitar erros de referência

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SantanderComprovantes:
    """
    Classe para buscar comprovantes de pagamento do Santander
    Suporta múltiplos fundos
    """
    
    def __init__(self, santander_auth):
        """
        Inicializa o cliente de comprovantes
        
        Args:
            santander_auth: Instância configurada de SantanderAuth
        """
        self.auth = santander_auth
        self.api_base = self.auth.base_urls[self.auth.ambiente]['api']
        
        # Diretório para salvar comprovantes (na pasta do projeto pipe)
        self.comprovantes_dir = Path(__file__).parent / "Comprovantes"
        self.comprovantes_dir.mkdir(exist_ok=True)
        
        logger.info(f"Cliente de comprovantes Santander inicializado")
        logger.info(f"Diretório de comprovantes: {self.comprovantes_dir.absolute()}")
        
        # Log informações do fundo se disponível
        if self.auth.fundo_id:
            logger.info(f"Fundo: {self.auth.fundo_nome}")
            logger.info(f"CNPJ: {self.auth.fundo_cnpj}")
    
    def get_fundo_info(self) -> dict:
        """Retorna informações do fundo associado"""
        return {
            "fundo_id": self.auth.fundo_id,
            "nome": self.auth.fundo_nome,
            "cnpj": self.auth.fundo_cnpj
        }
    
    def _get_headers(self) -> Dict[str, str]:
        """
        Prepara os headers para requisições à API
        
        Returns:
            Dicionário com headers incluindo token de autenticação
        """
        print(f"DEBUG _get_headers: Verificando validade do token...")
        # Garante que temos um token válido
        if not self.auth._is_token_valid():
            logger.info("Token expirado, obtendo novo token...")
            print(f"DEBUG: Token inválido/expirado, chamando obter_token_acesso...")
            self.auth.obter_token_acesso()
            print(f"DEBUG: Token obtido com sucesso")
        else:
            print(f"DEBUG: Token ainda válido")
        
        token = self.auth.token_data['access_token']
        
        return {
            "Authorization": f"Bearer {token}",
            "X-Application-Key": self.auth.client_id,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
    
    def listar_comprovantes(self, data_inicio: str, data_fim: str) -> Dict[str, Any]:
        """
        Lista comprovantes disponíveis por período
        
        Args:
            data_inicio: Data inicial no formato 'YYYY-MM-DD'
            data_fim: Data final no formato 'YYYY-MM-DD'
        
        Returns:
            Dados dos comprovantes em formato JSON
        """
        print(f"DEBUG listar_comprovantes: Iniciando para período {data_inicio} a {data_fim}")
        print(f"DEBUG: self.auth.fundo_id = {self.auth.fundo_id}")
        print(f"DEBUG: self.api_base = {self.api_base}")
        
        endpoint = "/consult_payment_receipts/v1/payment_receipts"
        url = f"{self.api_base}{endpoint}"
        
        print(f"DEBUG: URL completa = {url}")
        
        params = {
            "start_date": data_inicio,
            "end_date": data_fim
        }
        
        print(f"DEBUG: Obtendo headers...")
        headers = self._get_headers()
        print(f"DEBUG: Headers obtidos com sucesso")
        
        print(f"DEBUG: Obtendo certificados...")
        cert_tuple = self.auth._get_cert_tuple()
        print(f"DEBUG: Certificados obtidos: {cert_tuple}")
        
        try:
            print(f"DEBUG: Fazendo requisição GET para {url}")
            logger.info(f"Listando comprovantes de {data_inicio} até {data_fim}...")
            
            if self.auth.fundo_id:
                logger.info(f"Fundo: {self.auth.fundo_nome} (CNPJ: {self.auth.fundo_cnpj})")
            
            response = requests.get(
                url,
                headers=headers,
                params=params,
                cert=cert_tuple,
                verify=True,
                timeout=35
            )
            
            response.raise_for_status()
            comprovantes_data = response.json()
            
            receipts = comprovantes_data.get('paymentsReceipts', [])
            logger.info(f"✅ {len(receipts)} comprovante(s) encontrado(s)")
            
            # Log detalhado dos comprovantes encontrados
            if receipts:
                logger.info(f"\n{'='*60}")
                logger.info("COMPROVANTES ENCONTRADOS:")
                logger.info(f"{'='*60}")
                for idx, receipt in enumerate(receipts, 1):
                    payment = receipt.get('payment', {})
                    
                    # Informações do pagador
                    payer = payment.get('payer', {}).get('person', {})
                    payer_doc = payer.get('document', {}).get('documentNumber', 'N/A')
                    payer_name = payment.get('payer', {}).get('name', 'N/A')
                    
                    # Informações do beneficiário
                    payee_name = payment.get('payee', {}).get('name', 'N/A')
                    payee_doc = payment.get('payee', {}).get('person', {}).get('document', {}).get('documentNumber', 'N/A')
                    
                    # Valores
                    amount = payment.get('paymentAmountInfo', {}).get('direct', {}).get('amount', 0)
                    # Garantir que amount é numérico
                    try:
                        amount_float = float(amount) if amount else 0.0
                    except (ValueError, TypeError):
                        amount_float = 0.0
                    
                    payment_id = payment.get('paymentId', 'N/A')
                    
                    # Data
                    date_str = payment.get('requestValueDate', 'N/A')
                    
                    logger.info(f"\n[{idx}] Payment ID: {payment_id}")
                    logger.info(f"    Pagador: {payer_name} (Doc: {payer_doc})")
                    logger.info(f"    Beneficiário: {payee_name} (Doc: {payee_doc})")
                    logger.info(f"    Valor: R$ {amount_float:,.2f}")
                    logger.info(f"    Data: {date_str}")
                
                logger.info(f"\n{'='*60}\n")
            
            return comprovantes_data
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"Erro HTTP ao listar comprovantes: {e}")
            if hasattr(e.response, 'text'):
                logger.error(f"Resposta: {e.response.text}")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro na requisição: {e}")
            raise
    
    def solicitar_geracao_pdf(self, payment_id: str) -> Dict[str, Any]:
        """
        Solicita a geração do PDF do comprovante
        
        Args:
            payment_id: ID do pagamento
        
        Returns:
            Dados da requisição incluindo request_id
        """
        endpoint = f"/consult_payment_receipts/v1/payment_receipts/{payment_id}/file_requests"
        url = f"{self.api_base}{endpoint}"
        
        headers = self._get_headers()
        cert_tuple = self.auth._get_cert_tuple()
        
        try:
            logger.info(f"Solicitando geração do PDF para payment_id: {payment_id}")
            
            response = requests.post(
                url,
                headers=headers,
                cert=cert_tuple,
                verify=True,
                timeout=35
            )
            
            # Status 202 = Accepted (requisição aceita)
            if response.status_code == 202:
                result = response.json()
                request_id = result.get('request', {}).get('requestId')
                status = result.get('file', {}).get('statusInfo', {}).get('statusCode')
                
                logger.info(f"✅ Requisição aceita - request_id: {request_id}, status: {status}")
                return result
            else:
                response.raise_for_status()
                return response.json()
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"Erro HTTP ao solicitar PDF: {e}")
            if hasattr(e.response, 'text'):
                logger.error(f"Resposta: {e.response.text}")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro na requisição: {e}")
            raise
    
    def consultar_status_pdf(self, payment_id: str, request_id: str) -> Dict[str, Any]:
        """
        Consulta o status da geração do PDF
        
        Args:
            payment_id: ID do pagamento
            request_id: ID da requisição de geração
        
        Returns:
            Dados do arquivo incluindo URL de download (se disponível)
        """
        endpoint = f"/consult_payment_receipts/v1/payment_receipts/{payment_id}/file_requests/{request_id}"
        url = f"{self.api_base}{endpoint}"
        
        headers = self._get_headers()
        cert_tuple = self.auth._get_cert_tuple()
        
        try:
            logger.info(f"Consultando status do PDF - payment_id: {payment_id}, request_id: {request_id}")
            
            response = requests.get(
                url,
                headers=headers,
                cert=cert_tuple,
                verify=True,
                timeout=35
            )
            
            response.raise_for_status()
            result = response.json()
            
            status = result.get('file', {}).get('statusInfo', {}).get('statusCode')
            location = result.get('file', {}).get('fileRepository', {}).get('location')
            
            logger.info(f"Status: {status}")
            if location:
                logger.info(f"✅ PDF disponível para download!")
            
            return result
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"Erro HTTP ao consultar status: {e}")
            if hasattr(e.response, 'text'):
                logger.error(f"Resposta: {e.response.text}")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro na requisição: {e}")
            raise
    
    def baixar_pdf(self, url_download: str, payment_id: str, save_path: Path = None) -> str:
        """
        Baixa o PDF do comprovante com múltiplas estratégias
        
        Args:
            url_download: URL temporária para download do PDF
            payment_id: ID do pagamento (usado para nome do arquivo)
            save_path: Caminho onde salvar (opcional)
        
        Returns:
            Caminho do arquivo salvo
        """
        try:
            logger.info(f"Baixando PDF do comprovante {payment_id}...")
            logger.info(f"URL: {url_download[:100]}...")  # Log parcial da URL
            
            # Define caminho para salvar
            if save_path is None:
                data_hoje = datetime.now().strftime("%Y%m%d")
                
                # Criar estrutura: Comprovantes/{fundo_id}/{data}/
                if self.auth.fundo_id:
                    dir_data = self.comprovantes_dir / self.auth.fundo_id / data_hoje
                else:
                    dir_data = self.comprovantes_dir / "sem_fundo" / data_hoje
                
                dir_data.mkdir(parents=True, exist_ok=True)
                
                # Limpar caracteres inválidos do payment_id para nome de arquivo
                payment_id_safe = payment_id.replace('/', '_').replace('\\', '_').replace(':', '_')
                save_path = dir_data / f"comprovante_{payment_id_safe}.pdf"
            
            logger.info(f"Salvando em: {save_path}")
            
            # ESTRATÉGIA 1: Download com streaming (chunk por chunk)
            # Mais eficiente para arquivos grandes e menos propenso a timeout
            # IMPORTANTE: URL do Azure NÃO precisa de certificado mTLS
            try:
                logger.info("Tentando download com streaming...")
                
                # Headers básicos para o Azure Storage
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                
                with requests.get(url_download, stream=True, timeout=(35, 305), 
                                 verify=True, headers=headers, allow_redirects=True) as response:
                    logger.info(f"Status: {response.status_code}")
                    
                    # Log de todos os headers de resposta para debug
                    logger.info(f"Headers da resposta:")
                    for key, value in response.headers.items():
                        logger.info(f"  {key}: {value}")
                    
                    if response.status_code == 403:
                        logger.error("❌ Acesso negado (403) - URL pode ter expirado")
                        logger.error(f"Response: {response.text[:500]}")
                        raise Exception("URL expirada ou sem permissão")
                    
                    response.raise_for_status()
                    
                    # Verificar Content-Type
                    content_type = response.headers.get('Content-Type', '')
                    logger.info(f"Content-Type: {content_type}")
                    
                    if 'html' in content_type.lower():
                        logger.error("❌ Resposta é HTML, não PDF")
                        logger.error(f"Conteúdo: {response.text[:500]}")
                        raise Exception("Resposta não é um PDF válido")
                    
                    # Baixa em chunks de 8KB
                    bytes_downloaded = 0
                    with open(save_path, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                                bytes_downloaded += len(chunk)
                    
                    logger.info(f"✅ PDF salvo: {bytes_downloaded} bytes em {save_path}")
                    
                    # Verificar se o arquivo foi salvo corretamente
                    if bytes_downloaded < 100:
                        logger.error(f"❌ Arquivo muito pequeno ({bytes_downloaded} bytes) - pode não ser um PDF válido")
                        with open(save_path, 'rb') as f:
                            content = f.read()
                            logger.error(f"Conteúdo: {content}")
                        raise Exception("Arquivo baixado é inválido")
                    
                    return str(save_path)
                
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                logger.warning(f"Streaming falhou: {e}")
                logger.warning(f"Tipo do erro: {type(e).__name__}")
                
                # ESTRATÉGIA 2: Download direto com timeout maior
                logger.info("Tentando download direto com timeout estendido...")
                try:
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                    }
                    
                    response = requests.get(url_download, timeout=305, verify=True, 
                                          headers=headers, allow_redirects=True)
                    logger.info(f"Status: {response.status_code}")
                    
                    if response.status_code == 403:
                        logger.error("❌ Acesso negado (403) - URL expirada")
                        raise Exception("URL expirada")
                    
                    response.raise_for_status()
                    
                    with open(save_path, 'wb') as f:
                        f.write(response.content)
                    
                    file_size = len(response.content)
                    logger.info(f"✅ PDF salvo: {file_size} bytes em {save_path}")
                    
                    if file_size < 100:
                        logger.error(f"❌ Arquivo muito pequeno - pode ser inválido")
                        raise Exception("Arquivo inválido")
                    
                    return str(save_path)
                except Exception as e2:
                    logger.error(f"Estratégia 2 também falhou: {e2}")
                    raise
            
        except requests.exceptions.Timeout:
            logger.error(f"Timeout ao baixar PDF após todas tentativas")
            # Salva a URL para download manual posterior
            url_file = save_path.parent / f"URL_{payment_id}.txt"
            with open(url_file, 'w') as f:
                f.write(f"Payment ID: {payment_id}\n")
                f.write(f"URL (válida por 5 minutos): {url_download}\n")
                f.write(f"Gerado em: {datetime.now()}\n")
            logger.info(f"💾 URL salva em: {url_file} (baixe manualmente)")
            raise
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro ao baixar PDF: {e}")
            raise
        except Exception as e:
            logger.error(f"Erro ao salvar arquivo: {e}")
            raise
    
    def aguardar_pdf_disponivel(self, payment_id: str, request_id: str, 
                                 max_tentativas: int = 15, intervalo: int = 1) -> Optional[str]:
        """
        Aguarda o PDF ficar disponível e retorna a URL de download
        
        Args:
            payment_id: ID do pagamento
            request_id: ID da requisição
            max_tentativas: Número máximo de tentativas (padrão 15)
            intervalo: Intervalo entre tentativas em segundos (padrão 1s)
        
        Returns:
            URL de download do PDF ou None se não ficou disponível
        """
        logger.info(f"Aguardando PDF ficar disponível (max {max_tentativas} tentativas, intervalo {intervalo}s)...")
        
        for tentativa in range(1, max_tentativas + 1):
            logger.info(f"Tentativa {tentativa}/{max_tentativas}...")
            
            try:
                result = self.consultar_status_pdf(payment_id, request_id)
                status = result.get('file', {}).get('statusInfo', {}).get('statusCode')
                
                logger.info(f"Status atual: {status}")
                
                if status == 'AVAILABLE':
                    url = result.get('file', {}).get('fileRepository', {}).get('location')
                    if url:
                        logger.info(f"✅ PDF disponível! URL obtida.")
                        logger.info(f"⏱️ Tempo total de espera: ~{(tentativa - 1) * intervalo}s")
                        return url
                    else:
                        logger.error("Status AVAILABLE mas URL não encontrada no response")
                        logger.error(f"Response completo: {json.dumps(result, indent=2)}")
                        return None
                elif status == 'REQUESTED':
                    logger.info(f"PDF ainda sendo processado... aguardando {intervalo}s")
                    time.sleep(intervalo)
                elif status == 'FAILED':
                    logger.error("Geração do PDF falhou no servidor")
                    return None
                else:
                    logger.warning(f"Status inesperado: {status}")
                    logger.warning(f"Response: {json.dumps(result, indent=2)}")
                    time.sleep(intervalo)
            except Exception as e:
                logger.error(f"Erro ao consultar status: {e}")
                if tentativa < max_tentativas:
                    time.sleep(intervalo)
                else:
                    raise
        
        logger.error(f"Timeout: PDF não ficou disponível em {max_tentativas * intervalo}s")
        return None
    
    def consultar_comprovantes_existentes(self, payment_id: str) -> Optional[Dict[str, Any]]:
        """
        Consulta se já existem comprovantes disponíveis para um payment_id
        SEM solicitar nova geração e SEM fazer download.
        
        Args:
            payment_id: ID do pagamento
            
        Returns:
            Dict com informações do comprovante se existir, None caso contrário
            Estrutura retornada:
            {
                'payment_id': str,
                'request_id': str,
                'status': str,
                'url_download': str,
                'disponivel': bool
            }
        """
        try:
            # Primeiro, tenta listar os file_requests existentes
            endpoint = f"/consult_payment_receipts/v1/payment_receipts/{payment_id}/file_requests"
            url = f"{self.api_base}{endpoint}"
            
            headers = self._get_headers()
            cert_tuple = self.auth._get_cert_tuple()
            
            logger.info(f"Consultando comprovantes existentes para payment_id: {payment_id}")
            
            # GET para listar requests existentes
            response = requests.get(
                url,
                headers=headers,
                cert=cert_tuple,
                verify=True,
                timeout=35
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # A API pode retornar uma lista ou objeto único
                requests_list = result.get('requests', [])
                
                if not requests_list:
                    logger.info(f"Nenhum comprovante existente encontrado para {payment_id}")
                    return None
                
                # Pegar o primeiro request (mais recente)
                first_request = requests_list[0] if isinstance(requests_list, list) else requests_list
                
                request_id = first_request.get('request', {}).get('requestId')
                status_info = first_request.get('file', {}).get('statusInfo', {})
                status_code = status_info.get('statusCode')
                file_repo = first_request.get('file', {}).get('fileRepository', {})
                url_download = file_repo.get('location')
                
                disponivel = status_code == 'AVAILABLE' and url_download is not None
                
                logger.info(f"✅ Comprovante encontrado - request_id: {request_id}, status: {status_code}, disponível: {disponivel}")
                
                return {
                    'payment_id': payment_id,
                    'request_id': request_id,
                    'status': status_code,
                    'url_download': url_download,
                    'disponivel': disponivel
                }
            
            elif response.status_code == 404:
                logger.info(f"Nenhum file_request encontrado para {payment_id}")
                return None
            
            else:
                logger.warning(f"Status inesperado ao consultar: {response.status_code}")
                logger.warning(f"Resposta: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Erro ao consultar comprovantes existentes: {type(e).__name__}: {e}")
            return None
    
    def buscar_e_baixar_comprovante(self, payment_id: str, 
                                     aguardar: bool = True,
                                     max_retries: int = 3,
                                     payment_info: dict = None) -> Optional[str]:
        """
        Fluxo completo: solicita, aguarda e baixa o comprovante com retry
        
        Args:
            payment_id: ID do pagamento
            aguardar: Se True, aguarda o PDF ficar disponível
            max_retries: Número máximo de tentativas de download
            payment_info: Informações adicionais do pagamento para logging (opcional)
        
        Returns:
            Caminho do arquivo salvo ou None se falhou
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"Iniciando busca e download do comprovante: {payment_id}")
        
        # Se tiver informações do pagamento, mostrar
        if payment_info:
            payer = payment_info.get('payer', {})
            payee = payment_info.get('payee', {})
            amount = payment_info.get('amount', 0)
            
            # Converter amount para float se for string
            try:
                amount_float = float(amount) if amount else 0.0
            except (ValueError, TypeError):
                amount_float = 0.0
            
            logger.info(f"Pagador: {payer.get('name', 'N/A')} (Doc: {payer.get('document', 'N/A')})")
            logger.info(f"Beneficiário: {payee.get('name', 'N/A')} (Doc: {payee.get('document', 'N/A')})")
            logger.info(f"Valor: R$ {amount_float:,.2f}")
        
        logger.info(f"{'='*60}")
        
        try:
            # ETAPA 0: Verificar se já existe comprovante disponível
            logger.info("Etapa 0/3: Verificando se já existe comprovante disponível...")
            comprovante_existente = self.consultar_comprovantes_existentes(payment_id)
            
            request_id = None
            url_download = None
            
            if comprovante_existente and comprovante_existente.get('disponivel'):
                # Comprovante já existe e está disponível
                logger.info(f"✅ Comprovante já existe e está disponível!")
                request_id = comprovante_existente.get('request_id')
                url_download = comprovante_existente.get('url_download')
                logger.info(f"✅ Request ID existente: {request_id}")
                logger.info("⏩ Pulando etapas 1 e 2 (solicitar e aguardar)")
                
            else:
                # Comprovante não existe ou não está disponível - precisa solicitar
                logger.info("📄 Nenhum comprovante disponível. Solicitando nova geração...")
                
                # 1. Solicita geração do PDF
                logger.info("Etapa 1/3: Solicitando geração do PDF...")
                result = self.solicitar_geracao_pdf(payment_id)
                request_id = result.get('request', {}).get('requestId')
                
                if not request_id:
                    logger.error("❌ Não foi possível obter request_id")
                    logger.error(f"Response: {json.dumps(result, indent=2)}")
                    return None
                
                logger.info(f"✅ Request ID obtido: {request_id}")
                
                # 2. Aguarda PDF ficar disponível (se solicitado)
                logger.info("Etapa 2/3: Aguardando PDF ficar disponível...")
                if aguardar:
                    url_download = self.aguardar_pdf_disponivel(payment_id, request_id)
                else:
                    # Consulta uma vez apenas
                    result = self.consultar_status_pdf(payment_id, request_id)
                    url_download = result.get('file', {}).get('fileRepository', {}).get('location')
                
                if not url_download:
                    logger.error("❌ URL de download não disponível")
                    return None
                
                logger.info(f"✅ URL de download obtida")
            
            # 3. Baixa o PDF com retry (seja comprovante novo ou existente)
            logger.info(f"Etapa 3/3: Baixando PDF (max {max_retries} tentativas)...")
            logger.info("⚠️ IMPORTANTE: Baixando imediatamente pois URL expira em 5 minutos!")
            
            for tentativa in range(1, max_retries + 1):
                try:
                    logger.info(f"Tentativa de download {tentativa}/{max_retries}")
                    arquivo_salvo = self.baixar_pdf(url_download, payment_id)
                    logger.info(f"✅✅✅ Comprovante salvo com sucesso: {arquivo_salvo}")
                    return arquivo_salvo
                except requests.exceptions.Timeout:
                    if tentativa < max_retries:
                        logger.warning(f"⏱️ Timeout na tentativa {tentativa}, tentando novamente em 1s...")
                        time.sleep(1)
                    else:
                        logger.error(f"❌ Falha após {max_retries} tentativas de timeout")
                        return None
                except requests.exceptions.RequestException as e:
                    logger.error(f"❌ Erro de requisição na tentativa {tentativa}: {e}")
                    if tentativa < max_retries:
                        logger.info("Tentando novamente em 1s...")
                        time.sleep(1)
                    else:
                        logger.error(f"❌ Falha após {max_retries} tentativas")
                        return None
                except Exception as e:
                    logger.error(f"❌ Erro inesperado na tentativa {tentativa}: {type(e).__name__}: {e}")
                    if tentativa >= max_retries:
                        return None
                    time.sleep(1)
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Erro no fluxo completo: {type(e).__name__}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def buscar_comprovantes_periodo(self, dias: int = 30, 
                                     auto_baixar: bool = True) -> Dict[str, str]:
        """
        Busca e baixa todos os comprovantes dos últimos N dias
        
        Args:
            dias: Número de dias para buscar
            auto_baixar: Se True, baixa automaticamente todos os PDFs
        
        Returns:
            Dicionário com payment_id -> caminho do arquivo
        """
        # Calcula período
        data_fim = date.today()
        data_inicio = data_fim - timedelta(days=dias)
        
        logger.info(f"\n{'='*80}")
        logger.info(f"Buscando comprovantes de {data_inicio} até {data_fim}")
        logger.info(f"{'='*80}\n")
        
        # Lista comprovantes
        comprovantes_data = self.listar_comprovantes(
            data_inicio.strftime("%Y-%m-%d"),
            data_fim.strftime("%Y-%m-%d")
        )
        
        receipts = comprovantes_data.get('paymentsReceipts', [])
        
        if not receipts:
            logger.info("Nenhum comprovante encontrado no período")
            return {}
        
        # Baixa cada comprovante (se solicitado)
        resultados = {}
        
        if auto_baixar:
            logger.info(f"\n🚀 Iniciando download de {len(receipts)} comprovante(s)...\n")
            
            for i, receipt in enumerate(receipts, 1):
                payment = receipt.get('payment', {})
                payment_id = payment.get('paymentId')
                
                if not payment_id:
                    logger.warning(f"Comprovante {i} sem payment_id")
                    continue
                
                logger.info(f"\n{'='*60}")
                logger.info(f"PROCESSANDO {i}/{len(receipts)}")
                logger.info(f"{'='*60}")
                
                # Preparar informações do pagamento para logging
                payer_info = payment.get('payer', {})
                payer_person = payer_info.get('person', {})
                payee_info = payment.get('payee', {})
                payee_person = payee_info.get('person', {})
                
                # Obter e converter amount para float
                amount_raw = payment.get('paymentAmountInfo', {}).get('direct', {}).get('amount', 0)
                try:
                    amount_float = float(amount_raw) if amount_raw else 0.0
                except (ValueError, TypeError):
                    amount_float = 0.0
                
                payment_info = {
                    'payer': {
                        'name': payer_info.get('name', 'N/A'),
                        'document': payer_person.get('document', {}).get('documentNumber', 'N/A')
                    },
                    'payee': {
                        'name': payee_info.get('name', 'N/A'),
                        'document': payee_person.get('document', {}).get('documentNumber', 'N/A')
                    },
                    'amount': amount_float  # Já convertido para float
                }
                
                # Baixa o comprovante com informações
                arquivo = self.buscar_e_baixar_comprovante(payment_id, payment_info=payment_info)
                resultados[payment_id] = arquivo if arquivo else "ERRO"
                
                if arquivo:
                    logger.info(f"✅ Comprovante {i}/{len(receipts)} baixado com sucesso!")
                else:
                    logger.error(f"❌ Erro ao baixar comprovante {i}/{len(receipts)}")
        else:
            # Apenas lista
            for receipt in receipts:
                payment_id = receipt.get('payment', {}).get('paymentId')
                if payment_id:
                    resultados[payment_id] = "LISTADO (não baixado)"
        
        return resultados


# Exemplo de uso
if __name__ == "__main__":
    print("\n" + "="*80)
    print("BUSCAR COMPROVANTES SANTANDER")
    print("="*80)
    
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
        
        # Inicializa cliente de comprovantes
        cliente_comprovantes = SantanderComprovantes(santander_auth)
        
        # ============================================================
        # EXEMPLO 1: BUSCAR COMPROVANTES DOS ÚLTIMOS 1 DIA (TESTE)
        # ============================================================
        
        print("\n" + "-"*80)
        print("BUSCAR COMPROVANTES DO ÚLTIMO DIA")
        print("-"*80)
        
        resultados = cliente_comprovantes.buscar_comprovantes_periodo(
            dias=1,
            auto_baixar=True
        )
        
        # Resumo
        print("\n" + "="*80)
        print("RESUMO")
        print("="*80)
        print(f"Total de comprovantes: {len(resultados)}")
        sucesso = sum(1 for v in resultados.values() if v and v != "ERRO")
        print(f"Baixados com sucesso: {sucesso}")
        print(f"Erros: {len(resultados) - sucesso}")
        
        print("\n✅ Processo concluído!")
        
    except Exception as e:
        print(f"\n❌ Erro: {e}")
        import traceback
        traceback.print_exc()
