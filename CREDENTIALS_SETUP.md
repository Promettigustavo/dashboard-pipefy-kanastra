# 🔐 Guia de Configuração de Credenciais

Este documento explica como configurar as credenciais necessárias para o Dashboard Pipefy Kanastra funcionar corretamente tanto em ambiente local quanto no Streamlit Cloud.

## 📋 Índice

1. [Visão Geral](#visão-geral)
2. [Configuração Local](#configuração-local)
3. [Configuração Streamlit Cloud](#configuração-streamlit-cloud)
4. [Credenciais Necessárias](#credenciais-necessárias)
5. [Segurança](#segurança)

---

## 🎯 Visão Geral

O sistema utiliza uma **abordagem híbrida** para gerenciar credenciais:

- **Desenvolvimento Local**: Arquivo `credenciais_bancos.py` (não versionado no git)
- **Produção (Streamlit Cloud)**: Arquivo `.streamlit/secrets.toml` via interface do Streamlit

A aplicação detecta automaticamente qual fonte usar através da função `get_santander_credentials()`.

---

## 💻 Configuração Local

### 1. Arquivo credenciais_bancos.py

Este arquivo já existe localmente e contém:
- 39 fundos Santander com client_id e client_secret
- Caminhos para certificados PEM
- Token da API Pipefy

**⚠️ IMPORTANTE**: Este arquivo está no `.gitignore` e **NUNCA** deve ser commitado!

### 2. Certificados Santander

Os certificados devem estar em:
```
C:\Users\GustavoPrometti\Cert\santander_cert.pem
C:\Users\GustavoPrometti\Cert\santander_key.pem
```

Para verificar se os certificados existem:
```powershell
Test-Path "C:\Users\GustavoPrometti\Cert\santander_cert.pem"
Test-Path "C:\Users\GustavoPrometti\Cert\santander_key.pem"
```

---

## ☁️ Configuração Streamlit Cloud

### Passo 1: Converter Certificados

Os certificados PEM precisam ser convertidos para base64 antes de serem adicionados aos secrets:

```bash
python converter_certificados.py
```

Este script irá:
1. ✅ Verificar se os certificados existem
2. ✅ Converter para base64
3. ✅ Exibir as strings para copiar
4. ✅ Salvar backup em `certificados_base64_BACKUP.txt`

### Passo 2: Configurar Secrets no Streamlit Cloud

1. Acesse seu app no Streamlit Cloud
2. Vá em **Settings** > **Secrets**
3. Copie o conteúdo do arquivo `.streamlit/secrets.toml.example`
4. Cole no editor de secrets
5. **SUBSTITUA** os valores de exemplo pelos valores reais:
   - `cert_base64` e `key_base64`: Use a saída do `converter_certificados.py`
   - Token Pipefy: Copie do arquivo `credenciais_bancos.py` local
   - Mantenha os `client_id` e `client_secret` que já estão preenchidos

### Exemplo de Estrutura:

```toml
[pipefy]
api_token = "SEU_TOKEN_REAL_AQUI"

[santander_fundos.AUTO_XI_FIDC]
nome = "FUNDO DE INVESTIMENTO EM DIREITOS CREDITORIOS CREDITAS AUTO XI"
cnpj = "58.035.124/0001-92"
client_id = "Ts21bGPsosCjh0SVeZrLDXefd0Tkn12Z"
client_secret = "JwLavIQKYQlJDAeo"
cert_base64 = "LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0t..."  # Saída do converter_certificados.py
key_base64 = "LS0tLS1CRUdJTiBQUklWQVRFIEtFWS0tLS0t..."   # Saída do converter_certificados.py
```

---

## 🔑 Credenciais Necessárias

### 1. Token Pipefy
- **Onde usar**: Todas as operações com Pipefy API
- **Formato**: JWT token
- **Exemplo**: `eyJhbGciOiJIUzUxMiJ9...`
- **Onde encontrar**: Pipefy > Settings > Personal Access Tokens

### 2. Fundos Santander (39 fundos)

Cada fundo requer:
- `nome`: Nome completo do fundo
- `cnpj`: CNPJ do fundo (XX.XXX.XXX/0001-XX)
- `client_id`: Client ID da API Santander
- `client_secret`: Client Secret da API Santander
- `cert_base64`: Certificado em base64 (cloud) ou `cert_path` (local)
- `key_base64`: Chave privada em base64 (cloud) ou `key_path` (local)

**Fundos incluídos:**
- 911_BANK, AMPLIC, CONDOLIVRE FIDC, AUTO X, AUTO XI FIDC
- TEMPUS III FIDC, INOVA, MAKENA, SEJA, AKIREDE
- ATICCA, ALTLEGAL, NETMONEY, TCG, DORO
- ORION, AGA, PRIME, ALBATROZ, TESLA
- ALTINVEST, ANTARES, AV_CAPITAL, BAY, BLIPS
- COINVEST, EXT_LOOMY, CONSORCIEI, IGAPORA, LAVOURA
- MACAUBAS, MARCA I, NX_BOATS, OKLAHOMA, ONCRED
- ORIZ_JUS_CPS, SIM, SYMA, YUNUS

---

## 🔒 Segurança

### ⚠️ NUNCA FAÇA:

❌ Commit de arquivos com credenciais para o git  
❌ Compartilhe certificados ou tokens com terceiros  
❌ Exponha secrets em logs ou outputs públicos  
❌ Use credenciais de produção em ambientes de teste  

### ✅ SEMPRE FAÇA:

✅ Mantenha `credenciais_bancos.py` apenas localmente  
✅ Use `.gitignore` para proteger arquivos sensíveis  
✅ Armazene backups de certificados em local seguro  
✅ Renove tokens periodicamente conforme política de segurança  
✅ Use secrets.toml apenas no Streamlit Cloud (nunca commitar)  
✅ Delete `certificados_base64_BACKUP.txt` após configurar o cloud  

### Arquivos Protegidos pelo .gitignore:

```
credenciais_bancos.py
*.pem
*.key
*.crt
.streamlit/secrets.toml
certificados_base64_BACKUP.txt
converter_certificados.py
kanastra-live-*.json
```

---

## 🧪 Testando a Configuração

### Local:
```python
# No terminal Python ou em um script de teste
from credenciais_bancos import SANTANDER_FUNDOS, PIPEFY_API_TOKEN

print(f"Fundos configurados: {len(SANTANDER_FUNDOS)}")
print(f"Token Pipefy: {PIPEFY_API_TOKEN[:20]}...")
```

### Streamlit Cloud:
Execute o app e verifique no log:
```
✅ Credenciais carregadas: secrets (39 fundos)
```

Se aparecer erro, verifique:
1. Formato TOML está correto
2. Certificados base64 estão completos
3. Todas as chaves estão presentes

---

## 📞 Suporte

Em caso de dúvidas sobre credenciais:
1. Verifique se os arquivos estão nos caminhos corretos
2. Confirme que os certificados não estão corrompidos
3. Valide o formato TOML no Streamlit Cloud
4. Consulte os logs da aplicação para erros específicos

---

**Última atualização**: 2024  
**Versão do Dashboard**: 2.0  
**Ambiente**: Kanastra - Projeto Pipe
