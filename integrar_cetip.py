"""
Script para integrar a nova aba CETIP no app_streamlit.py
"""

# Ler o arquivo novo
with open('aba_cetip_novo.py', 'r', encoding='utf-8') as f:
    conteudo_novo = f.read()

# Extrair apenas o código entre === INÍCIO === e === FIM ===
inicio = conteudo_novo.find('# === INÍCIO ===')
fim = conteudo_novo.find('# === FIM ===')

if inicio == -1 or fim == -1:
    print("❌ Marcadores não encontrados!")
    exit(1)

# Pegar o código (pulando a linha do marcador)
codigo_novo = conteudo_novo[inicio:fim].split('\n', 2)[2]  # Pula "# === INÍCIO ===" e linha vazia

# Ler o app_streamlit.py
with open('app_streamlit.py', 'r', encoding='utf-8') as f:
    linhas = f.readlines()

# Encontrar as linhas de início e fim da seção CETIP
linha_inicio = None
linha_fim = None

for i, linha in enumerate(linhas):
    if '# ===== ABA CETIP =====' in linha:
        linha_inicio = i
    if linha_inicio is not None and '# ===== ABA COMPROVANTES =====' in linha:
        linha_fim = i
        break

if linha_inicio is None or linha_fim is None:
    print(f"❌ Não foi possível encontrar as seções!")
    print(f"Linha início: {linha_inicio}, Linha fim: {linha_fim}")
    exit(1)

print(f"✅ Seção CETIP encontrada: linhas {linha_inicio + 1} a {linha_fim}")

# Substituir a seção
novas_linhas = (
    linhas[:linha_inicio] +  # Antes da seção CETIP
    [codigo_novo + '\n'] +  # Novo código
    linhas[linha_fim:]  # A partir de ABA COMPROVANTES
)

# Salvar o arquivo
with open('app_streamlit.py', 'w', encoding='utf-8') as f:
    f.writelines(novas_linhas)

print(f"✅ Arquivo app_streamlit.py atualizado!")
print(f"   Linhas removidas: {linha_fim - linha_inicio}")
print(f"   Código novo inserido")
print("\n🎯 Próximo passo: Verificar erros e fazer commit")
