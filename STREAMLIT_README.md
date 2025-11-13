# 🚀 Como Executar o Dashboard Streamlit

## 📋 Pré-requisitos

```bash
pip install -r requirements.txt
```

## ⚙️ Configuração Inicial

### 1. Configurar GitHub (para download automático de bases)

Edite `config_streamlit.py`:

```python
GITHUB_REPO = "seu-usuario/nome-do-repo"  # Seu repositório
GITHUB_BRANCH = "main"
```

Ou use secrets do Streamlit (`.streamlit/secrets.toml`):

```toml
[github]
repo = "seu-usuario/nome-do-repo"
branch = "main"
```

Com isso, as bases `Basedadosfundos.xlsx` e `Basedadosfundos_Arbi.xlsx` serão baixadas automaticamente do GitHub quando não existirem localmente.

## ▶️ Executar Dashboard

```bash
streamlit run app_streamlit.py
```

O dashboard abrirá automaticamente em: http://localhost:8501

## � Bases de Dados

### Opção 1: Auto-download do GitHub (Recomendado)
- Configure `config_streamlit.py` com seu repositório
- As bases serão baixadas automaticamente
- Ative "Auto-download do GitHub" na sidebar

### Opção 2: Upload Manual
- Use a sidebar para fazer upload
- Aceita arquivos `.xlsx`

### Opção 3: Local
- Coloque os arquivos na mesma pasta do `app_streamlit.py`:
  - `Basedadosfundos.xlsx`
  - `Basedadosfundos_Arbi.xlsx`

## 🔐 Credenciais

Certifique-se de ter:
- `credenciais_bancos.py` configurado com tokens Pipefy e Santander
- Certificado Santander em `C:\Users\<usuario>\Cert\santander_cert.pem`

## 🎯 Funcionalidades

### 🔄 Aba Pipefy
- **Processamento Manual**: Liquidação, Taxas ARBI, Pipe Taxas, Amortização
- **Auto Liquidação**: Automação completa do fluxo
- **Auto Taxas**: Pipe Taxas + ANBIMA
- **Auto Amortização**: Processamento automático
- **Mover Cards**: Triagem e 2ª Aprovação

### 🏦 Aba CETIP
- Integração com módulo integrador.py
- Emissão NC
- Depósitos

### 📎 Aba Comprovantes
- Buscar comprovantes Santander (múltiplos fundos)
- Anexar automaticamente ao Pipefy
- Match inteligente: CNPJ + Valor + Beneficiário

## 🌐 Deploy Online

### Streamlit Cloud (Grátis)

1. Faça push do código para GitHub
2. Acesse https://streamlit.io/cloud
3. Conecte seu repositório
4. Configure secrets (credenciais) no dashboard
5. Deploy!

### Secrets no Streamlit Cloud

Crie `.streamlit/secrets.toml`:

```toml
[santander]
cert_path = "/path/to/cert.pem"

[pipefy]
api_token = "seu_token"
```

## ⚙️ Configurações Avançadas

### Porta customizada
```bash
streamlit run app_streamlit.py --server.port 8080
```

### Modo de desenvolvimento
```bash
streamlit run app_streamlit.py --server.runOnSave true
```

## 🔧 Troubleshooting

### Módulo não encontrado
- Verifique se todos os arquivos .py estão na mesma pasta
- Confirme que requirements.txt foi instalado

### Erro de bases de dados
- Faça upload pela sidebar
- Ou coloque na mesma pasta do app_streamlit.py

### Erro de credenciais
- Verifique credenciais_bancos.py
- Confirme caminho do certificado Santander

## 📊 Performance

Para melhor performance:
- Use `@st.cache_data` para dados que não mudam
- Use `@st.cache_resource` para conexões
- Limite tamanho de uploads (max 200MB padrão)
