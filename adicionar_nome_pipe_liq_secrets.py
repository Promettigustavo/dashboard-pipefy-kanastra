"""
Script para adicionar o campo nome_pipe_liq ao arquivo SECRETS - STREAMLIT.txt
baseado nas informações do credenciais_bancos.py
"""

# Mapeamento de nome_pipe_liq baseado em credenciais_bancos.py
NOME_PIPE_LIQ_MAP = {
    "911_BANK": "911 BANK",
    "ALBATROZ": "ALBATROZ FIDC MULTISSETORIAL",
    "AMPLIC": "AMPLIC FIDC",
    "CONDOLIVRE FIDC": "CONDOLIVRE FIDC",
    "AUTO X": "AUTO X FIDC",
    "AUTO XI FIDC": "AUTO XI FIDC",
    "TEMPUS III FIDC": "TEMPUS III FIDC",
    "INOVA": "INOVA CREDTECH III FIDC",
    "MAKENA": "MAKENA FIDC NP",
    "SEJA": "SEJA FIDC",
    "AKIREDE": "AKIREDE FIDC",
    "ATICCA": "ATTICA FIDC",
    "ALTLEGAL": "ALT LEGAL CLAIMS",
    "NETMONEY": "NETMONEY FIDC",
    "TCG": "TCG IRON FIDC",
    "DORO": "D'ORO CAPITAL FIDC MULTISSETORIAL",
    "ORION": "ORION JN FIM CP",
    "AGA": "AGA FIDC",
    "PRIME": "PRIME FIDC",
    "TESLA": "TESLA FIDC MULTISSETORIAL",
    "ALTINVEST": "ALTINVEST FIC FIDC",
    "ANTARES": "ANTARES FIDC",
    "AV_CAPITAL": "AV CAPITAL FIDC",
    "BAY": "BAY FIDC",
    "BLIPS": "BLIPS FIDC",
    "COINVEST": "COINVEST FIDC",
    "EXT_LOOMY": "LOOMY FIDC",
    "CONSORCIEI": "CONSORCIEI FIC FIDC",
    "IGAPORA": "IGAPORÃ FIC FIM",
    "LAVOURA": "LAVOURA FIAGRO",
    "MACAUBAS": "MACAÚBAS FIP",
    "MARCA I": "MARCA FIDC",
    "NX_BOATS": "NX BOATS",
    "OKLAHOMA": "OKLAHOMA FIDC",
    "ONCRED": "ONCRED FIDC",
    "ORIZ_JUS_CPS": "ORIZ JUS CPS",
    "SIM": "SIM FIDC",
    "SYMA": "SYMA FIF",
    "YUNUS": "YUNUS FIDC",
    # Novos fundos - precisam ser mapeados baseado no nome real no Pipefy
    "PRIMATO_FIDC": "PRIMATO FIDC",  # A confirmar
    "MOBILITAS_FIDC": "MOBILITAS FIDC",  # A confirmar
    "AMOVERI_FIDC": "AMOVERI FIDC",  # A confirmar
    "HURST_FIDC": "HURST FIC FIDC",  # A confirmar
}

def adicionar_nome_pipe_liq():
    """Adiciona o campo nome_pipe_liq a cada seção de fundo no arquivo SECRETS"""
    
    arquivo_entrada = "SECRETS - STREAMLIT.txt"
    arquivo_saida = "SECRETS - STREAMLIT_COM_NOME_PIPE.txt"
    
    with open(arquivo_entrada, 'r', encoding='utf-8') as f:
        linhas = f.readlines()
    
    novas_linhas = []
    fundo_atual = None
    nome_adicionado = False
    
    for linha in linhas:
        # Detecta início de uma seção de fundo
        if linha.startswith('[santander_fundos.') and linha.strip() != '[santander_fundos]':
            # Extrai o ID do fundo
            fundo_id = linha.split('.')[1].rstrip(']\n').strip('"')
            fundo_atual = fundo_id
            nome_adicionado = False
            novas_linhas.append(linha)
        
        # Adiciona nome_pipe_liq após a linha "nome = "
        elif fundo_atual and linha.startswith('nome = ') and not nome_adicionado:
            novas_linhas.append(linha)
            
            # Adiciona o nome_pipe_liq
            if fundo_atual in NOME_PIPE_LIQ_MAP:
                nome_pipe = NOME_PIPE_LIQ_MAP[fundo_atual]
                novas_linhas.append(f'nome_pipe_liq = "{nome_pipe}"\n')
                nome_adicionado = True
                print(f"✓ Adicionado nome_pipe_liq para {fundo_atual}: {nome_pipe}")
            else:
                print(f"⚠ Fundo {fundo_atual} não encontrado no mapeamento")
        
        else:
            novas_linhas.append(linha)
    
    # Salva o arquivo modificado
    with open(arquivo_saida, 'w', encoding='utf-8') as f:
        f.writelines(novas_linhas)
    
    print(f"\n✅ Arquivo salvo em: {arquivo_saida}")
    print(f"📊 Total de linhas: {len(novas_linhas)}")

if __name__ == "__main__":
    adicionar_nome_pipe_liq()
