# Sistema de Integração Pipefy - Kanastra

Sistema integrado para automação de processos no Pipefy, incluindo liquidação, taxas ARBI, amortização e anexação automática de comprovantes bancários via API Santander.

## 📋 Funcionalidades

### 🔄 Pipes Principais
- **Pipe Liquidação** - Processamento de liquidações financeiras
- **Pipe Taxas** - Gerenciamento de taxas e tarifas
- **Taxas ARBI** - Processamento específico de taxas ARBI
- **Amortização** - Controle de amortizações

### 🤖 Automações
- **Auto Pipe Liquidação** - Automação completa do fluxo de liquidação
- **Auto Pipe Taxas** - Automação completa do fluxo de taxas
- **Auto Taxas ANBIMA** - Automação de taxas ANBIMA
- **Auto Amortização** - Automação de amortizações

### 📎 Comprovantes Bancários
- **Anexar Comprovantes (Liquidação)** - Busca e anexa comprovantes via API Santander
- **Anexar Comprovantes (Taxas)** - Busca e anexa comprovantes para taxas
- Match inteligente por:
  - CNPJ do fundo
  - Valor do pagamento
  - Nome do beneficiário (desempate)

### 🔀 Movimentação de Cards
- **Move Cards** - Triagem → Em Análise
- **Mover 2ª Aprovação** - 2ª Aprovação → Aguardando Comprovante

## 🚀 Instalação

### Pré-requisitos
- Python 3.8+
- Pip

### Instalar dependências
```bash
pip install -r requirements.txt
```

## ⚙️ Configuração

### 1. Credenciais Pipefy
Crie o arquivo `credenciais_bancos.py` (não versionado):

```python
PIPEFY_API_TOKEN = "seu_token_aqui"

SANTANDER_FUNDOS = {
    "NOME_FUNDO": {
        "cnpj": "XX.XXX.XXX/XXXX-XX",
        "client_id": "seu_client_id",
        "client_secret": "seu_client_secret"
    },
    # ... outros fundos
}
```

### 2. Certificado Santander (mTLS)
Coloque o certificado em:
```
C:\Users\<seu_usuario>\Cert\santander_cert.pem
```

### 3. Google Sheets (opcional)
Se usar integração com Google Sheets:
- Baixe as credenciais JSON da Google Cloud Console
- Salve como `kanastra-live-XXXXXXX.json`

## 📦 Estrutura do Projeto

```
Projeto pipe/
├── Integracao.py              # Interface principal (Tkinter)
├── pipeliquidacao.py          # Core - Pipe Liquidação
├── PipeTaxas.py               # Core - Pipe Taxas
├── taxasarbi.py               # Core - Taxas ARBI
├── Amortizacao.py             # Core - Amortização
├── auto_pipeliquidacao.py     # Automação Liquidação
├── auto_pipetaxas.py          # Automação Taxas
├── auto_taxasanbima.py        # Automação Taxas ANBIMA
├── auto_amortizacao.py        # Automação Amortização
├── Anexarcomprovantespipe.py  # Anexar comprovantes (Liquidação)
├── Anexarcomprovantespipetaxas.py # Anexar comprovantes (Taxas)
├── movecards.py               # Mover cards (Triagem)
├── mover_2a_aprovacao.py      # Mover cards (2ª Aprovação)
├── credenciais_bancos.py      # ⚠️ NÃO VERSIONADO - Credenciais
├── requirements.txt           # Dependências Python
└── README.md                  # Este arquivo
```

## 🎯 Como Usar

### Interface Desktop (Tkinter)
```bash
python Integracao.py
```

### Executar módulos individuais
```bash
# Pipe Liquidação
python pipeliquidacao.py

# Anexar comprovantes
python Anexarcomprovantespipe.py

# Auto Amortização
python auto_amortizacao.py
```

## 🔐 Segurança

### ⚠️ NUNCA COMMITAR:
- `credenciais_bancos.py` - Tokens Pipefy e credenciais Santander
- `*.pem`, `*.key`, `*.crt` - Certificados
- `kanastra-live-*.json` - Credenciais Google
- Arquivos de output (`.csv`, `.xlsx`, `.json`)

### ✅ Boas práticas:
- Use variáveis de ambiente para credenciais em produção
- Mantenha certificados fora do repositório
- Atualize `.gitignore` se adicionar novos tipos de arquivo sensível

## 📊 APIs Utilizadas

- **Pipefy GraphQL API** - Gestão de cards e pipes
- **Santander Open Banking API** - Busca de comprovantes de pagamento (mTLS)
- **Google Sheets API** - Integração com planilhas (opcional)

## 🛠️ Tecnologias

- Python 3.8+
- Pandas - Manipulação de dados
- Requests - HTTP client
- Tkinter - Interface desktop
- OpenPyXL - Manipulação de Excel
- GSpread - Google Sheets (opcional)

## 📝 Notas

### Match de Comprovantes
O sistema faz match de comprovantes Santander com cards Pipefy usando:
1. **CNPJ do fundo** (obrigatório - match por nome desabilitado)
2. **Valor** (tolerância de 1 centavo)
3. **Nome do beneficiário** (usado apenas como desempate quando há múltiplos valores iguais)

### Limitações API Santander
- Intervalo máximo de consulta: **30 dias**
- Autenticação: **mTLS** + OAuth2 Client Credentials

## 👥 Contribuindo

1. Crie uma branch para sua feature (`git checkout -b feature/MinhaFeature`)
2. Commit suas mudanças (`git commit -m 'Adiciona MinhaFeature'`)
3. Push para a branch (`git push origin feature/MinhaFeature`)
4. Abra um Pull Request

## 📄 Licença

Uso interno - Kanastra

## 🆘 Suporte

Para dúvidas ou problemas, contate a equipe de desenvolvimento Kanastra.
