"""
Wrapper de credenciais para Streamlit Cloud
============================================

Este módulo detecta automaticamente o ambiente (local ou cloud)
e carrega as credenciais da fonte apropriada.

- Local: Importa do credenciais_bancos.py real
- Cloud: Carrega do st.secrets

Os módulos que importam credenciais_bancos devem usar este arquivo no cloud.
"""

import streamlit as st
from typing import Dict, Any, Optional
import base64
import tempfile
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# Tentar importar do arquivo local primeiro
try:
    from credenciais_bancos import SANTANDER_FUNDOS as _LOCAL_FUNDOS
    from credenciais_bancos import SantanderAuth as _LocalSantanderAuth
    
    # Ambiente local - usar credenciais do arquivo
    SANTANDER_FUNDOS = _LOCAL_FUNDOS
    SantanderAuth = _LocalSantanderAuth
    CREDENTIALS_SOURCE = "local"
    
    logger.info("✅ Credenciais carregadas do arquivo local credenciais_bancos.py")
    
except ImportError:
    # Ambiente cloud - carregar do st.secrets
    logger.info("📡 Carregando credenciais do Streamlit Secrets...")
    
    CREDENTIALS_SOURCE = "secrets"
    
    # Converter secrets para dict no formato esperado
    SANTANDER_FUNDOS = {}
    
    if "santander_fundos" in st.secrets:
        for fundo_id in st.secrets["santander_fundos"].keys():
            fundo_secrets = st.secrets["santander_fundos"][fundo_id]
            
            SANTANDER_FUNDOS[fundo_id] = {
                "nome": fundo_secrets.get("nome", ""),
                "cnpj": fundo_secrets.get("cnpj", ""),
                "client_id": fundo_secrets.get("client_id", ""),
                "client_secret": fundo_secrets.get("client_secret", ""),
            }
            
            # No cloud, certificados estão em base64
            # Precisamos criar arquivos temporários
            if "cert_base64" in fundo_secrets and "key_base64" in fundo_secrets:
                # Criar arquivos temporários para certificados
                cert_data = base64.b64decode(fundo_secrets["cert_base64"])
                key_data = base64.b64decode(fundo_secrets["key_base64"])
                
                # Criar diretório temporário para certificados
                temp_dir = Path(tempfile.gettempdir()) / "streamlit_certs"
                temp_dir.mkdir(exist_ok=True)
                
                cert_path = temp_dir / f"{fundo_id}_cert.pem"
                key_path = temp_dir / f"{fundo_id}_key.pem"
                
                cert_path.write_bytes(cert_data)
                key_path.write_bytes(key_data)
                
                SANTANDER_FUNDOS[fundo_id]["cert_path"] = str(cert_path)
                SANTANDER_FUNDOS[fundo_id]["key_path"] = str(key_path)
                
                logger.info(f"✅ Certificados criados para {fundo_id}")
        
        logger.info(f"✅ {len(SANTANDER_FUNDOS)} fundos carregados do Streamlit Secrets")
    else:
        logger.warning("⚠️ Nenhuma credencial Santander configurada em secrets")
    
    # Implementação da classe SantanderAuth para cloud
    import requests
    import json
    from datetime import datetime, timedelta
    
    class SantanderAuth:
        """
        Versão simplificada de SantanderAuth para Streamlit Cloud
        Compatível com a versão local do credenciais_bancos.py
        """
        
        @classmethod
        def criar_por_fundo(cls, fundo_id: str, ambiente: str = "producao"):
            """Cria instância a partir do ID do fundo"""
            if fundo_id not in SANTANDER_FUNDOS:
                raise ValueError(f"Fundo '{fundo_id}' não encontrado")
            
            config = SANTANDER_FUNDOS[fundo_id]
            
            if not config.get("client_id") or not config.get("client_secret"):
                raise ValueError(f"Fundo '{fundo_id}' não tem credenciais configuradas")
            
            return cls(
                client_id=config["client_id"],
                client_secret=config["client_secret"],
                cert_path=config.get("cert_path"),
                key_path=config.get("key_path"),
                ambiente=ambiente,
                fundo_id=fundo_id,
                fundo_nome=config.get("nome"),
                fundo_cnpj=config.get("cnpj")
            )
        
        def __init__(self, client_id: str, client_secret: str,
                     cert_path: str, key_path: str = None, ambiente: str = "producao",
                     fundo_id: str = None, fundo_nome: str = None, fundo_cnpj: str = None):
            """Inicializa autenticação Santander"""
            self.client_id = client_id
            self.client_secret = client_secret
            self.ambiente = ambiente
            self.fundo_id = fundo_id
            self.fundo_nome = fundo_nome
            self.fundo_cnpj = fundo_cnpj
            
            self.cert_file = cert_path
            self.key_file = key_path
            
            if not cert_path:
                raise ValueError("Certificado é obrigatório")
            
            # URLs base
            self.base_urls = {
                "sandbox": {
                    "token": "https://trust-open.api.santander.com.br/auth/oauth/v2/token",
                    "api": "https://trust-open.api.santander.com.br"
                },
                "producao": {
                    "token": "https://trust-open.api.santander.com.br/auth/oauth/v2/token",
                    "api": "https://trust-open.api.santander.com.br"
                }
            }
            
            self.token_data = {
                "access_token": None,
                "token_type": None,
                "expires_in": None,
                "expires_at": None,
                "refresh_token": None
            }
            
            # Armazenar token em session_state do Streamlit (não em arquivo no cloud)
            self.token_cache_key = f"santander_token_{fundo_id or 'default'}"
            
            # Carregar token do cache se existir
            if self.token_cache_key in st.session_state:
                self.token_data = st.session_state[self.token_cache_key]
        
        def _get_cert_tuple(self):
            """Retorna tupla (cert, key) para requests"""
            if self.cert_file:
                if self.key_file:
                    return (self.cert_file, self.key_file)
                else:
                    return self.cert_file
            return None
        
        def _get_auth_header(self) -> str:
            """Header de autenticação Basic"""
            credentials = f"{self.client_id}:{self.client_secret}"
            encoded = base64.b64encode(credentials.encode()).decode()
            return f"Basic {encoded}"
        
        def _save_token(self):
            """Salva token no session_state"""
            st.session_state[self.token_cache_key] = self.token_data
        
        def _is_token_valid(self) -> bool:
            """Verifica se token está válido"""
            if not self.token_data.get("access_token"):
                return False
            
            if not self.token_data.get("expires_at"):
                return False
            
            expires_at = datetime.fromisoformat(self.token_data["expires_at"])
            return datetime.now() < expires_at - timedelta(minutes=5)
        
        def obter_token_acesso(self) -> Dict[str, Any]:
            """Obtém novo token de acesso"""
            url = self.base_urls[self.ambiente]["token"]
            
            headers = {
                "Authorization": self._get_auth_header(),
                "Content-Type": "application/x-www-form-urlencoded"
            }
            
            data = {"grant_type": "client_credentials"}
            
            cert_tuple = self._get_cert_tuple()
            
            response = requests.post(url, headers=headers, data=data, cert=cert_tuple)
            
            if response.status_code == 200:
                token_response = response.json()
                
                self.token_data = {
                    "access_token": token_response["access_token"],
                    "token_type": token_response.get("token_type", "Bearer"),
                    "expires_in": token_response.get("expires_in", 3600),
                    "expires_at": (datetime.now() + timedelta(seconds=token_response.get("expires_in", 3600))).isoformat(),
                    "refresh_token": token_response.get("refresh_token")
                }
                
                self._save_token()
                return self.token_data
            else:
                raise Exception(f"Erro ao obter token: {response.status_code} - {response.text}")

# Informações sobre a fonte das credenciais
def get_credentials_info() -> Dict[str, Any]:
    """Retorna informações sobre a fonte das credenciais"""
    return {
        "source": CREDENTIALS_SOURCE,
        "fundos_count": len(SANTANDER_FUNDOS),
        "fundos_ids": list(SANTANDER_FUNDOS.keys())
    }
