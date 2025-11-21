# 🤖 GitHub Actions - Robô Fromtis

## Como Usar

### 🚀 Execução Manual

1. Acesse: https://github.com/promettigustavo/dashboard-pipefy-kanastra/actions
2. Clique em "🤖 Processar Fromtis com Comprovantes"
3. Clique em "Run workflow"
4. Configure:
   - **Dias retroativos**: Quantos dias buscar comprovantes (1, 3, 7, 15 ou 30)
   - **Modo debug**: Ativar logs detalhados (true/false)
5. Clique em "Run workflow" (verde)
6. Aguarde a execução (~5-15 minutos)
7. Baixe os resultados em "Artifacts"

### ⏰ Execução Automática

O robô roda automaticamente **segunda a sexta às 6h (horário de Brasília)**.

Você pode ver o histórico em:
https://github.com/promettigustavo/dashboard-pipefy-kanastra/actions

---

## 📋 O Que o Robô Faz

1. **Busca comprovantes** da API Santander (todos os fundos configurados)
2. **Gera mapeamento** Fromtis → CNPJ
3. **Processa Fromtis** automaticamente com Puppeteer
4. **Salva resultados** como artifacts (disponíveis por 30 dias)

---

## 🔐 Configurar Secrets (Primeira Vez)

Acesse: https://github.com/promettigustavo/dashboard-pipefy-kanastra/settings/secrets/actions

### Secrets Necessários:

#### 1. Certificados Santander
```
SANTANDER_CERT_PEM
```
Cole o conteúdo do arquivo `santander_cert.pem` (com -----BEGIN CERTIFICATE-----, etc)

```
SANTANDER_KEY_PEM
```
Cole o conteúdo do arquivo `santander_key.pem` (com -----BEGIN RSA PRIVATE KEY-----, etc)

#### 2. Credenciais Fromtis
```
FROMTIS_USERNAME
```
Seu usuário do Fromtis

```
FROMTIS_PASSWORD
```
Sua senha do Fromtis

#### 3. Fundos Santander
```
SANTANDER_FUNDOS
```
Cole o conteúdo do dicionário SANTANDER_FUNDOS do arquivo `credenciais_bancos.py`:

```python
{
  "911_BANK": {
    "nome": "911 BANK MULTI ESTRATEGIA...",
    "cnpj": "50.790.524/0001-00",
    "client_id": "...",
    "client_secret": "..."
  },
  ...
}
```

**IMPORTANTE:** Converta o dicionário Python para JSON válido:
- Aspas simples `'` → aspas duplas `"`
- `True` → `true`
- `False` → `false`
- `None` → `null`

---

## 📥 Baixar Resultados

Após cada execução:

1. Vá em: https://github.com/promettigustavo/dashboard-pipefy-kanastra/actions
2. Clique na execução desejada
3. Role até "Artifacts"
4. Baixe: `fromtis-resultados-XXX.zip`

O arquivo contém:
- `execution_log_XXXXX.txt` - Log completo da execução
- `listagem_comprovantes_XXXXX.json` - Comprovantes encontrados
- `mapeamento_fundos_fromtis.json` - Mapeamento de fundos
- `relatorio_execucao.txt` - Resumo da execução

---

## 🐛 Debug e Logs

### Ver Logs em Tempo Real

1. Clique na execução em andamento
2. Clique no job "Processar Fromtis"
3. Acompanhe cada etapa expandindo os steps

### Executar com Debug

Ao rodar manualmente, marque:
- **Modo debug**: `true`

Isso ativará logs detalhados do Puppeteer.

---

## ⚙️ Limites do GitHub Actions

- **2000 minutos/mês** (grátis)
- **Timeout**: 60 minutos por execução
- **Storage**: Artifacts mantidos por 30 dias
- **Execuções simultâneas**: Até 20

---

## 🔄 Atualizar o Robô

Sempre que você fizer commit de mudanças no código, o GitHub Actions usará a versão mais recente automaticamente.

Arquivos monitorados:
- `puppeteer_com_comprovantes_v2.ts`
- `listar_comprovantes_santander.py`
- `exportar_mapeamento_fundos.py`
- `credenciais_bancos.py`

---

## ❓ Troubleshooting

### Erro: "No artifacts found"
- O robô não gerou arquivos de resultado
- Verifique os logs da etapa "Executar robô Fromtis"

### Erro: "Invalid credentials"
- Verifique se os secrets `FROMTIS_USERNAME` e `FROMTIS_PASSWORD` estão corretos

### Erro: "Certificate not found"
- Verifique se `SANTANDER_CERT_PEM` e `SANTANDER_KEY_PEM` foram configurados corretamente
- Certifique-se de incluir as linhas `-----BEGIN CERTIFICATE-----` e `-----END CERTIFICATE-----`

### Timeout após 60 minutos
- Reduza o número de dias de comprovantes
- Verifique se há algum travamento no Fromtis

---

## 👥 Compartilhar com a Equipe

Qualquer pessoa com acesso ao repositório pode:
1. Ver execuções: **Read** permission
2. Rodar workflow: **Write** permission
3. Configurar secrets: **Admin** permission

Para adicionar pessoas:
1. Settings → Collaborators
2. Add people
3. Escolha permission level

---

## 💡 Dicas

- **Primeira execução**: Teste com 1 dia de comprovantes
- **Produção**: Use 3-7 dias para garantir cobertura
- **Troubleshooting**: Ative modo debug
- **Agendamento**: Edite o cron em `.github/workflows/processar-fromtis.yml`

---

## 📞 Suporte

Dúvidas? Abra uma Issue:
https://github.com/promettigustavo/dashboard-pipefy-kanastra/issues
