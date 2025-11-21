# 🚀 Setup Completo - GitHub Actions

## 📋 Passo a Passo para Configurar

### 1️⃣ Preparar Secrets

Execute o script auxiliar para gerar os secrets em formato correto:

```powershell
python preparar_secrets_github.py
```

Isso criará o arquivo `santander_fundos_secret.json` que você usará no passo 3.

---

### 2️⃣ Obter Certificados Santander

Os certificados já devem estar em:
```
C:\Users\GustavoPrometti\Cert\santander_cert.pem
C:\Users\GustavoPrometti\Cert\santander_key.pem
```

Você vai precisar do **conteúdo completo** desses arquivos (incluindo as linhas BEGIN/END).

---

### 3️⃣ Configurar Secrets no GitHub

Acesse: https://github.com/promettigustavo/dashboard-pipefy-kanastra/settings/secrets/actions

Clique em **"New repository secret"** e adicione cada um:

#### Secret 1: `SANTANDER_CERT_PEM`
```
Valor: Cole TODO o conteúdo de santander_cert.pem
```
Exemplo:
```
-----BEGIN CERTIFICATE-----
MIIH2DCCBcCgAwIBAgIIGCJ3s92KlQYwDQYJKoZIhvcNAQELBQAwdDELMAkGA1UE
...
-----END CERTIFICATE-----
```

#### Secret 2: `SANTANDER_KEY_PEM`
```
Valor: Cole TODO o conteúdo de santander_key.pem
```
Exemplo:
```
-----BEGIN RSA PRIVATE KEY-----
MIIEpgIBAAKCAQEA0Ub+yAFKE2fKbODXsxKotaW6ySQmSRZ5GWYQVDYQ8dKhP8yQ
...
-----END RSA PRIVATE KEY-----
```

#### Secret 3: `SANTANDER_FUNDOS`
```
Valor: Cole o conteúdo de santander_fundos_secret.json (gerado no passo 1)
```

#### Secret 4: `FROMTIS_USERNAME`
```
Valor: Seu usuário do Fromtis
```

#### Secret 5: `FROMTIS_PASSWORD`
```
Valor: Sua senha do Fromtis
```

---

### 4️⃣ Fazer Commit dos Arquivos

```powershell
# Adicionar arquivos do GitHub Actions
git add .github/

# Adicionar scripts auxiliares
git add preparar_secrets_github.py
git add listar_comprovantes_santander.py
git add exportar_mapeamento_fundos.py

# Adicionar código do robô
git add puppeteer_com_comprovantes_v2.ts
git add tsconfig.json
git add package.json

# Commit
git commit -m "feat: Adicionar GitHub Actions para processamento Fromtis

- Workflow automático: segunda a sexta às 6h
- Execução manual via interface GitHub
- Busca automática de comprovantes Santander
- Processamento Fromtis com Puppeteer
- Upload de resultados como artifacts"

# Push
git push origin main
```

---

### 5️⃣ Testar a Primeira Execução

1. Acesse: https://github.com/promettigustavo/dashboard-pipefy-kanastra/actions

2. Clique em **"🤖 Processar Fromtis com Comprovantes"**

3. Clique em **"Run workflow"** (botão verde à direita)

4. Configure:
   - **branch**: main
   - **Dias retroativos**: 1
   - **Modo debug**: true (para primeira execução)

5. Clique em **"Run workflow"**

6. Aguarde ~5-15 minutos

7. Se der sucesso ✅:
   - Role até "Artifacts"
   - Baixe `fromtis-resultados-XXX.zip`
   - Extraia e veja os resultados

8. Se der erro ❌:
   - Clique no job que falhou
   - Veja qual step deu erro
   - Leia os logs para identificar o problema

---

## 🔍 Verificar Secrets Configurados

Acesse: https://github.com/promettigustavo/dashboard-pipefy-kanastra/settings/secrets/actions

Você deve ver:
- ✅ FROMTIS_PASSWORD
- ✅ FROMTIS_USERNAME  
- ✅ SANTANDER_CERT_PEM
- ✅ SANTANDER_FUNDOS
- ✅ SANTANDER_KEY_PEM

**Total: 5 secrets**

---

## 📊 Estrutura dos Arquivos

```
.github/
├── workflows/
│   └── processar-fromtis.yml          ← Workflow principal
└── GITHUB_ACTIONS_MANUAL.md           ← Manual do usuário

preparar_secrets_github.py             ← Gera JSON dos fundos
listar_comprovantes_santander.py       ← Busca comprovantes (com --dias)
exportar_mapeamento_fundos.py          ← Gera mapeamento Fromtis
puppeteer_com_comprovantes_v2.ts       ← Robô Puppeteer
tsconfig.json                          ← Config TypeScript
package.json                           ← Dependências Node
```

---

## ⚠️ Troubleshooting

### Erro: "secret not found"
→ Volte ao passo 3 e configure todos os 5 secrets

### Erro: "Invalid certificate"
→ Certifique-se de copiar TODO o arquivo .pem, incluindo:
- `-----BEGIN CERTIFICATE-----`
- Conteúdo
- `-----END CERTIFICATE-----`

### Erro: "SANTANDER_FUNDOS parse error"
→ O JSON deve ser válido. Execute novamente `preparar_secrets_github.py` e copie exatamente o conteúdo gerado

### Erro: "python command not found"
→ GitHub Actions usa Python 3.11 - não deve dar esse erro. Verifique o workflow.

### Erro: "node command not found"  
→ GitHub Actions usa Node 20 - não deve dar esse erro. Verifique o workflow.

---

## 🎉 Pronto!

Após configurar, qualquer pessoa com acesso ao repo pode:

1. **Rodar manualmente**: Actions → Run workflow
2. **Ver execuções**: Actions → histórico
3. **Baixar resultados**: Artifacts de cada run

**Execução automática**: Segunda a sexta, 6h da manhã (Brasília)

---

## 📚 Documentação Adicional

- [Manual do Usuário](.github/GITHUB_ACTIONS_MANUAL.md)
- [GitHub Actions Docs](https://docs.github.com/en/actions)
- [Workflow Syntax](https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions)
