# Instruções para Agentes de IA - Dashboard Pipefy Kanastra

## 🎯 Visão Geral do Sistema

Sistema integrado Python para automação de processos financeiros no Pipefy, processamento CETIP e anexação automática de comprovantes bancários via API Santander. Possui três interfaces: Desktop (Tkinter), Web (Streamlit) e módulos CLI standalone.

**Fluxo principal:** Cards do Pipefy → Exportação via GraphQL → Processamento local → Geração de arquivos bancários → Anexação de comprovantes via API Santander → Movimentação de cards entre fases.

## 🏗️ Arquitetura de Componentes

### Pipes Pipefy (IDs Hardcoded)
- **Liquidação**: `PIPE_LIQUIDACAO_ID = "303418384"`
  - Fases: `FASE_LIQUIDACAO_AGUARDANDO_COMPROVANTE = "325983455"`, `FASE_LIQUIDACAO_SOLICITACAO_PAGA = "321352632"`
- **Taxas**: `PIPE_TAXAS_ID = "303667924"`
  - Fases: `FASE_TAXAS_AGUARDANDO_COMPROVANTE = "322673487"`, `FASE_TAXAS_SOLICITACAO_PAGA = "322618269"`
- **Taxas ANBIMA**: `303808557`

### Módulos Core de Processamento
- `pipeliquidacao.py`: Normaliza dados de liquidação, adiciona sufixo `4444` aos valores (`parse_valor_to_string_with_4444`), sanitiza texto (`sanitize_text_out`), valida datas futuras
- `PipeTaxas.py`: Processamento de taxas, normaliza agências (lógica especial para 5 dígitos), valores com `money_with_4444`
- `Amortizacao.py`: Processamento de amortizações
- `funcoes.py`: Utilitários Selenium para automações web (scroll inteligente, esperar e clicar/escrever)

### Automações Completas (API Pipefy + Processamento)
Padrão de 3 etapas: `descobrir_report_id()` → `iniciar_exportacao()` → `aguardar_arquivo()`

- `auto_pipeliquidacao.py`: Inclui `filtrar_e_mover_cards()` periódico em thread daemon
- `auto_pipetaxas.py`: Gera Excel via GraphQL, executa PipeTaxas
- `auto_taxasanbima.py`: Automação específica para Taxas ANBIMA
- `auto_amortizacao.py`: Automação de amortizações

### Anexação de Comprovantes Santander
- `Anexarcomprovantespipe.py` / `Anexarcomprovantespipetaxas.py`: Match inteligente por CNPJ fundo + valor (±1 centavo) + nome beneficiário (desempate)
- `buscar_comprovantes_santander.py`: Classe `SantanderComprovantes` com autenticação mTLS + OAuth2
- **Diretório:** `Comprovantes/` (criado automaticamente ao lado dos scripts)

### Integração CETIP
Importação dinâmica de módulos do diretório irmão `"Projeto CETIP"` via `_import_local_module()` em `app_streamlit.py`:
- `integrador.py`: Emissão NC, Depósito/Venda (MDA), Compra/Venda, CCI
- Contagem de registros via `_count_registros_em_arquivo()` com prefixos específicos (`"NC   1"`, `"MDA  1"`, `"CCI  1"`)

## 🔐 Sistema de Credenciais Híbrido

**Local:** `credenciais_bancos.py` (39 fundos Santander, token Pipefy, paths para PEM)  
**Cloud:** Streamlit secrets via `get_santander_credentials()` → retorna `(fundos_dict, "local"|"secrets")`

### Certificados Santander (mTLS)
- **Local:** `C:\Users\GustavoPrometti\Cert\santander_cert.pem` + `santander_key.pem`
- **Cloud:** Base64 em secrets via `criar_santander_auth_do_secrets()` → arquivos temp em `tempfile.gettempdir()/santander_certs/`

### Classes de Autenticação
- `SantanderAuth` (local): Factory method `criar_por_fundo(fundo_id)`, cache de token, métodos `obter_token_acesso()`, `_is_token_valid()`, `_get_cert_tuple()`
- `SantanderAuthFromSecrets` (cloud): Compatível com a local, sem persistência de token em disco
- `SantanderComprovantes`: Wrapper sobre auth, endpoint `/consult_payment_receipts/v1/payment_receipts`, parâmetros `start_date`/`end_date` (max 30 dias)

## 🔧 Padrões de Desenvolvimento

### Importação Condicional de Credenciais
```python
try:
    from credenciais_bancos import PIPEFY_API_TOKEN, SantanderAuth
    HAS_CREDENCIAIS = True
except ImportError:
    HAS_CREDENCIAIS = False
    # Não falhar - permitir import no Streamlit Cloud
```

### Normalização de Texto
Use sempre `strip_accents()` + `.upper()` antes de comparações. Valores monetários sempre com 2 casas decimais + sufixo `"4444"` para match único.

### GraphQL Pipefy
Padrão:
```python
headers = {"Authorization": f"Bearer {PIPEFY_API_TOKEN}", "Content-Type": "application/json"}
response = requests.post("https://api.pipefy.com/graphql", json={"query": query, "variables": vars}, headers=headers)
```

### Bases de Dados
- `Basedadosfundos.xlsx` / `Basedadosfundos_Arbi.xlsx`: Lookup de fundos, validados via `validar_presenca_bancos()`
- Download automático do GitHub via `baixar_base_github()` em `app_streamlit.py` se não existirem localmente

## 🖥️ Interfaces

### Tkinter (`Integracao.py`)
Classe `IntegracaoUnificada` com tabs: Pipefy (processamento), CETIP (integração), Comprovantes (busca/anexação). Padrão de execução: thread separada + `TextRedirector` para stdout → widget de log.

### Streamlit (`app_streamlit.py`)
- **Sidebar:** Upload bases, auto-download GitHub, validação de presença
- **Tabs:** "📋 Pipefy", "🏦 CETIP", "📎 Comprovantes"
- Import lazy de módulos via `import_module_lazy()` para performance
- Custom CSS inline com classes `.main-header`, `.sub-header`, `.success-box`

## ⚡ Comandos Críticos

### Executar Dashboard
```powershell
streamlit run app_streamlit.py
```

### Testar Credenciais
```python
from credenciais_bancos import SANTANDER_FUNDOS, PIPEFY_API_TOKEN
print(f"Fundos: {len(SANTANDER_FUNDOS)}, Token: {PIPEFY_API_TOKEN[:20]}...")
```

### Converter Certificados para Cloud
```powershell
python converter_certificados.py
```

## 📝 Notas Importantes

- **IDs de Pipes/Fases são hardcoded** - consultar constantes no topo de cada módulo
- **Sufixo 4444** é essencial para matching único de valores entre Pipefy e Santander
- **Limite API Santander:** 30 dias por consulta, requer mTLS + OAuth2 Client Credentials
- **Selenium (`funcoes.py`)** usa scroll inteligente para garantir elementos visíveis antes de interação
- **Thread daemon em `auto_pipeliquidacao.py`** move cards periodicamente durante execução
- **CETIP** espera módulos em diretório irmão `"Projeto CETIP"`, fallback para mesmo diretório
- **Encoding Windows:** UTF-8 via `codecs.getwriter()` no início de scripts para suportar emojis nos logs

## 🚨 Armadilhas Comuns

1. **Não committar `credenciais_bancos.py`** - está no `.gitignore`
2. **Certificados PEM devem ter `\n` reais** - converter `\\n` literais em secrets
3. **Match de comprovantes:** CNPJ do fundo é obrigatório, nome beneficiário só para desempate
4. **Datas de pagamento:** Validação impede datas passadas (`valida_data_pagamento`)
5. **Bases de dados:** Verificar presença via `verificar_bases_dados()` antes de processamento
6. **GraphQL timeout:** Exportações grandes podem demorar, usar `aguardar_arquivo(timeout_segundos=300)`
7. **Módulos de automação:** Sempre passar `data_pagamento` e `pasta_saida` para `main()` - ex: `module.main(data_pagamento="14/11/2025", pasta_saida=os.getcwd())`
8. **Busca de arquivos gerados:** Procurar por múltiplos padrões (ex: `PipeTaxas_Final`, `PipeTaxas_`) e usar `max()` por timestamp

## 🗂️ Estrutura de Saída

Arquivos gerados seguem padrão: `{Tipo}_{timestamp}.xlsx` (ex: `PipeLiquidacao_20241114_153045.xlsx`)  
Comprovantes salvos em: `Comprovantes/{fundo_id}_{payment_id}.pdf`
