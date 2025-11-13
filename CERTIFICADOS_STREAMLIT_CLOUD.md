# 🔐 CONFIGURAÇÃO DOS CERTIFICADOS SANTANDER NO STREAMLIT CLOUD

## ⚠️ PROBLEMA IDENTIFICADO

Os certificados `.pem` e `.key` estão no repositório, mas o Streamlit Cloud **não consegue usá-los diretamente** com `requests.post(cert=...)` devido a restrições de SSL.

## ✅ SOLUÇÃO: Adicionar certificados no secrets.toml

### Passo 1: Copiar conteúdo dos certificados

1. Abra `certificados/santander_cert.pem` e copie **TODO O CONTEÚDO** (incluindo as linhas BEGIN/END)
2. Abra `certificados/santander_key.pem` e copie **TODO O CONTEÚDO** (incluindo as linhas BEGIN/END)

### Passo 2: Adicionar no Streamlit Cloud Secrets

No painel do Streamlit Cloud:

1. Vá em **Settings > Secrets**
2. Adicione o seguinte (substituindo `<CONTEÚDO DO CERTIFICADO>` pelo conteúdo real):

```toml
[santander_fundos]

# Certificado compartilhado (todos os fundos usam o mesmo)
cert_pem = """
-----BEGIN CERTIFICATE-----
MIIH2DCCBcCgAwIBAgIIGCJ3s92KlQYwDQYJKoZIhvcNAQELBQAwdDELMAkGA1UE
... (COLE AQUI TODO O CONTEÚDO DO santander_cert.pem)
-----END CERTIFICATE-----
"""

# Chave privada compartilhada
key_pem = """
-----BEGIN RSA PRIVATE KEY-----
MIIEpgIBAAKCAQEA0Ub+yAFKE2fKbODXsxKotaW6ySQmSRZ5GWYQVDYQ8dKhP8yQ
... (COLE AQUI TODO O CONTEÚDO DO santander_key.pem)
-----END RSA PRIVATE KEY-----
"""

# Fundos Santander
[santander_fundos."911_BANK"]
nome = "911 BANK MULTI ESTRATEGIA FUNDO DE INVESTIMENTO EM DIREITOS CREDITORIOS"
cnpj = "50.790.524/0001-00"
client_id = "3ZYICW0BDAwihhCwP4Tx08EtKYHFb2JG"
client_secret = "dAsx4AFNd7gNe8Lt"

[santander_fundos.ALBATROZ]
nome = "ALBATROZ FUNDO DE INVESTIMENTO EM DIREITOS CREDITORIOS MULTISSETORIAL"
cnpj = "25.354.081/0001-59"
client_id = "tVgp6LU2OBZo62hXgBVt5AuMK3Z9sGSI"
client_secret = "KgMNdmARoqCfnMKC"

# ... adicione os outros fundos conforme necessário
```

### Passo 3: Modificar o código para usar os certificados do secrets

O código já está preparado! A função `criar_santander_auth_do_secrets()` vai:

1. Verificar se `cert_pem` e `key_pem` existem em `st.secrets["santander_fundos"]`
2. Criar arquivos temporários com o conteúdo
3. Usar esses arquivos temporários na requisição SSL

### ⚙️ ALTERNATIVA (se ainda não funcionar):

Se o problema persistir, podemos usar **arquivos temporários** ao invés de tentar ler do repositório.

O código precisa ser modificado para:

```python
# Ao invés de:
cert_path = Path(__file__).parent / "certificados" / "santander_cert.pem"

# Usar:
import tempfile
temp_dir = Path(tempfile.gettempdir()) / "santander_certs"
temp_dir.mkdir(exist_ok=True)

cert_path = temp_dir / "santander_cert.pem"
key_path = temp_dir / "santander_key.pem"

# Escrever conteúdo do secrets
with open(cert_path, 'w') as f:
    f.write(st.secrets["santander_fundos"]["cert_pem"])
    
with open(key_path, 'w') as f:
    f.write(st.secrets["santander_fundos"]["key_pem"])
```

## 🎯 CONCLUSÃO

O problema **NÃO É** com o código de autenticação (funciona perfeitamente localmente).

O problema É que o Streamlit Cloud tem **restrições específicas** ao usar certificados SSL do filesystem.

**A solução é passar os certificados via secrets e criar arquivos temporários**.
