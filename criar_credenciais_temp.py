"""
Script para criar credenciais_bancos.py temporário a partir do JSON do GitHub Actions
"""
import json
import os
import sys
import codecs

# Configurar encoding UTF-8 para Windows
if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

def criar_credenciais_temp():
    """
    Cria credenciais_bancos.py temporário a partir de santander_fundos.json
    Usado no GitHub Actions
    """
    fundos_json_path = "santander_fundos.json"
    
    if not os.path.exists(fundos_json_path):
        print(f"❌ Erro: {fundos_json_path} não encontrado")
        print("Este script deve ser executado após a extração das credenciais do secret")
        sys.exit(1)
    
    # Carregar fundos do JSON
    with open(fundos_json_path, 'r', encoding='utf-8') as f:
        fundos = json.load(f)
    
    # Pegar paths dos certificados das variáveis de ambiente
    cert_path = os.environ.get('SANTANDER_CERT_PATH', '')
    key_path = os.environ.get('SANTANDER_KEY_PATH', '')
    
    if not cert_path or not key_path:
        print("❌ Erro: Variáveis SANTANDER_CERT_PATH e SANTANDER_KEY_PATH não definidas")
        sys.exit(1)
    
    # Criar conteúdo do credenciais_bancos.py
    conteudo = f'''"""
Credenciais temporárias geradas pelo GitHub Actions
NÃO COMMITAR ESTE ARQUIVO!
"""

# Paths dos certificados (do GitHub Actions)
SANTANDER_CERT_PEM = r"{cert_path}"
SANTANDER_KEY_PEM = r"{key_path}"

# Token Pipefy (não usado no workflow Fromtis)
PIPEFY_API_TOKEN = ""

# Fundos Santander (do secret KANASTRA_CREDENTIALS)
SANTANDER_FUNDOS = {json.dumps(fundos, indent=4, ensure_ascii=False)}

# Classe SantanderAuth simplificada para GitHub Actions
class SantanderAuth:
    def __init__(self, fundo_id, client_id, client_secret, cnpj, nome="", cert_path=None, key_path=None):
        self.fundo_id = fundo_id
        self.client_id = client_id
        self.client_secret = client_secret
        self.fundo_cnpj = cnpj
        self.fundo_nome = nome
        self._cert_path = cert_path or SANTANDER_CERT_PEM
        self._key_path = key_path or SANTANDER_KEY_PEM
        self._token_cache = None
    
    @classmethod
    def criar_por_fundo(cls, fundo_id):
        config = SANTANDER_FUNDOS.get(fundo_id)
        if not config:
            raise ValueError(f"Fundo {{fundo_id}} não encontrado")
        
        return cls(
            fundo_id=fundo_id,
            client_id=config["client_id"],
            client_secret=config["client_secret"],
            cnpj=config["cnpj"],
            nome=config.get("nome", fundo_id)
        )
    
    def _get_cert_tuple(self):
        return (self._cert_path, self._key_path)
    
    def obter_token_acesso(self):
        # Implementação simplificada - o buscar_comprovantes_santander.py faz o real
        if self._token_cache:
            return self._token_cache
        
        import requests
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry
        
        session = requests.Session()
        retry = Retry(total=3, backoff_factor=1)
        session.mount('https://', HTTPAdapter(max_retries=retry))
        
        url = "https://trust-open.api.santander.com.br/auth/oauth/v2/token"
        headers = {{"Content-Type": "application/x-www-form-urlencoded"}}
        data = {{
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }}
        
        response = session.post(url, headers=headers, data=data, cert=self._get_cert_tuple(), timeout=30)
        response.raise_for_status()
        
        token_data = response.json()
        self._token_cache = token_data.get("access_token")
        return self._token_cache
'''
    
    # Salvar arquivo
    with open('credenciais_bancos.py', 'w', encoding='utf-8') as f:
        f.write(conteudo)
    
    print("✅ credenciais_bancos.py temporário criado com sucesso!")
    print(f"   - {len(fundos)} fundos configurados")
    print(f"   - Certificado: {cert_path}")
    print(f"   - Chave: {key_path}")

if __name__ == "__main__":
    criar_credenciais_temp()
