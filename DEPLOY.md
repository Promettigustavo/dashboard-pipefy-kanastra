# 🚀 Guia de Deploy - Streamlit Cloud

## Pré-requisitos

1. ✅ Código commitado no Git (FEITO)
2. ⏳ Repositório criado no GitHub
3. ⏳ Conta no Streamlit Cloud (https://share.streamlit.io)

## Passo 1: Criar Repositório no GitHub

1. Acesse: https://github.com/new
2. Preencha:
   - **Repository name**: `dashboard-pipefy-kanastra`
   - **Description**: Dashboard Streamlit para integração Pipefy - Kanastra
   - **Visibilidade**: Private (recomendado para código interno)
   - ⚠️ **NÃO** marque "Add a README file"
   - ⚠️ **NÃO** marque "Add .gitignore"
3. Clique em **"Create repository"**

## Passo 2: Conectar Repositório Local ao GitHub

Após criar o repo no GitHub, execute no terminal:

```powershell
# Substitua SEU_USUARIO pelo seu usuário GitHub
git remote add origin https://github.com/SEU_USUARIO/dashboard-pipefy-kanastra.git
git branch -M main
git push -u origin main
```

## Passo 3: Deploy no Streamlit Cloud

1. Acesse: https://share.streamlit.io
2. Faça login com sua conta GitHub
3. Clique em **"New app"**
4. Preencha:
   - **Repository**: `SEU_USUARIO/dashboard-pipefy-kanastra`
   - **Branch**: `main`
   - **Main file path**: `app_streamlit.py`
   - **App URL**: `dashboard-pipefy-kanastra` (ou personalizado)
5. Clique em **"Deploy!"**

## Passo 4: Configurar Secrets

⚠️ **IMPORTANTE**: Configure os secrets ANTES de usar o app

1. No Streamlit Cloud, abra seu app
2. Clique em **"⚙️ Settings"** → **"Secrets"**
3. Cole o conteúdo abaixo (ajuste conforme necessário):

```toml
[github]
repo = "SEU_USUARIO/dashboard-pipefy-kanastra"
branch = "main"

[pipefy]
api_token = "SEU_TOKEN_PIPEFY"

# Adicione outras configurações conforme necessário
```

4. Clique em **"Save"**

## Passo 5: Arquivos Sensíveis

Os seguintes arquivos NÃO devem ser commitados (já estão no .gitignore):

- ❌ `config_streamlit.py` (credenciais)
- ❌ `credenciais_bancos.py` (tokens Santander)
- ❌ `*.pem` (certificados)
- ❌ `config/` (diretório de configurações)
- ❌ `kanastra-live-*.json` (chaves Google)

**Solução**: Configure todas as credenciais via **Secrets** do Streamlit Cloud

## Passo 6: Verificar Deploy

1. Aguarde o build (pode levar 2-5 minutos)
2. Acesse a URL do seu app
3. Verifique se todas as funcionalidades estão operacionais

## 🔧 Troubleshooting

### Erro: Module not found
- Verifique se o módulo está em `requirements.txt`
- Faça commit e push novamente

### Erro: Secrets not configured
- Configure os secrets no painel do Streamlit Cloud
- Reinicie o app

### App não carrega
- Verifique os logs no Streamlit Cloud
- Certifique-se que `app_streamlit.py` está na raiz do repo

## 📝 Atualizações Futuras

Para atualizar o app:

```powershell
git add .
git commit -m "Descrição da atualização"
git push
```

O Streamlit Cloud irá fazer o redeploy automaticamente!

## 🎨 Personalização

- O tema está configurado em `.streamlit/config.toml`
- Cores da Kanastra: #00B37E (verde)

## 📞 Suporte

Em caso de dúvidas:
- Streamlit Docs: https://docs.streamlit.io
- Streamlit Community: https://discuss.streamlit.io
