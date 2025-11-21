# 🚀 Setup Completo - GitHub Actions

## 📋 Passo a Passo para Configurar

### 1️⃣ Gerar Secret Completo

Execute o script que gera UM ÚNICO SECRET com todas as credenciais:

```powershell
py gerar_secret_completo.py
```

O script vai:
1. Ler os certificados Santander automaticamente
2. Pedir usuário e senha do Fromtis
3. Incluir todas as credenciais dos 60 fundos
4. Gerar o arquivo `github_secret_completo.json`

---

### 2️⃣ Configurar o Único Secret no GitHub

Acesse: https://github.com/promettigustavo/dashboard-pipefy-kanastra/settings/secrets/actions

Clique em **"New repository secret"** e adicione:

#### Secret: `KANASTRA_CREDENTIALS`

1. Abra o arquivo gerado:
   ```powershell
   notepad github_secret_completo.json
   ```

2. Copie **TODO** o conteúdo (Ctrl+A, Ctrl+C)

3. Cole no campo "Secret" do GitHub

4. Clique em "Add secret"

**✅ PRONTO! Apenas 1 secret ao invés de 5!**

Este secret único contém:
- ✅ Certificado Santander (cert_pem)
- ✅ Chave privada Santander (key_pem)
- ✅ Credenciais de todos os 60 fundos
- ✅ Usuário Fromtis
- ✅ Senha Fromtis

---

### 3️⃣ Fazer Commit dos Arquivos

```powershell
# Adicionar novos arquivos
git add gerar_secret_completo.py
git add .github/workflows/processar-fromtis.yml
git add .github/SETUP_GITHUB_ACTIONS.md

# Commit
git commit -m "feat: Simplificar para usar apenas 1 secret GitHub

- Criar gerar_secret_completo.py para gerar secret único
- Atualizar workflow para usar KANASTRA_CREDENTIALS
- Reduzir de 5 secrets para apenas 1
- Facilitar configuração inicial"

# Push
git push origin main
```

---

### 4️⃣ Testar a Primeira Execução

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

## 🔍 Verificar Secret Configurado

Acesse: https://github.com/promettigustavo/dashboard-pipefy-kanastra/settings/secrets/actions

Você deve ver:
- ✅ KANASTRA_CREDENTIALS

**Total: 1 secret (muito mais simples!)**

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
