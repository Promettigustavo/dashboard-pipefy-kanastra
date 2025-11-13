"""
Move cards da fase "2ª Aprovação" para "Aguardando Comprovante"
Com configuração automática de banco por fundo
Pipe: 1 - A Liquidação (ID: 303418384)
"""

import requests
import json
from datetime import datetime

# Token de autenticação
API_TOKEN = "eyJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJQaXBlZnkiLCJpYXQiOjE3NjExMzkxNDcsImp0aSI6ImM1NzhhYzM5LTUwZmUtNGI0NC1iMzYzLWE5ZjNhMzBmNjUwYyIsInN1YiI6MzA2ODY4NTY3LCJ1c2VyIjp7ImlkIjozMDY4Njg1NjcsImVtYWlsIjoiZ3VzdGF2by5wcm9tZXR0aUBrYW5hc3RyYS5jb20uYnIifSwidXNlcl90eXBlIjoiYXV0aGVudGljYXRlZCJ9.hjcPATGMMX1xBcRMHQ7gfjkvqB7Nq9w0Ou9tD33fIlmLoicU928x5sd_T_nmkL04DV37GtxFtF5mCFaFSa4fVQ"

HEADERS = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type": "application/json"
}

PIPE_ID = "303418384"  # 1 - A Liquidação

# =============================================================================
# MAPEAMENTO DE FUNDOS PARA BANCOS
# =============================================================================
# Formato: "NOME DO FUNDO (PARCIAL OU COMPLETO)": {"nome": "Nome", "codigo": "XXX", "record_id": "ID"}
# O nome do fundo será buscado usando "in" (case insensitive), então pode ser parcial
# 
# ANÁLISE COMPLETA: 6853 cards analisados, 142 fundos encontrados
# Data da análise: 31/10/2025 14:34:18
#
FUNDO_BANCO_MAP = {
    # Fundos com Santander (record_id: 1115747762)
    "911 BANK": {"nome": "Santander", "codigo": "033", "record_id": "1115747762"},
    "AGROCANA": {"nome": "Santander", "codigo": "033", "record_id": "1115747762"},
    "AID BANK": {"nome": "Santander", "codigo": "033", "record_id": "1115747762"},
    "ALBATROZ": {"nome": "Santander", "codigo": "033", "record_id": "1115747762"},
    "ALTINVEST FIC": {"nome": "Santander", "codigo": "033", "record_id": "1115747762"},
    "AMOVERI": {"nome": "Santander", "codigo": "033", "record_id": "1115747762"},
    "AMPLIC": {"nome": "Santander", "codigo": "033", "record_id": "1115747762"},
    "ANTARES": {"nome": "Santander", "codigo": "033", "record_id": "1115747762"},
    "ARACUA": {"nome": "Santander", "codigo": "033", "record_id": "1115747762"},
    "ARCO": {"nome": "Santander", "codigo": "033", "record_id": "1115747762"},
    "AUTO GWM": {"nome": "Santander", "codigo": "033", "record_id": "1115747762"},
    "AUTO X": {"nome": "Santander", "codigo": "033", "record_id": "1115747762"},
    "AUTO XI": {"nome": "Santander", "codigo": "033", "record_id": "1115747762"},
    "BLIPS": {"nome": "Santander", "codigo": "033", "record_id": "1115747762"},
    "BOLSA DE CRÉDITO": {"nome": "Santander", "codigo": "033", "record_id": "1115747762"},
    "CAPIA": {"nome": "Santander", "codigo": "033", "record_id": "1115747762"},
    "CITRINO": {"nome": "Santander", "codigo": "033", "record_id": "1115747762"},
    "CITRINO II": {"nome": "Santander", "codigo": "033", "record_id": "1115747762"},
    "CLM": {"nome": "Santander", "codigo": "033", "record_id": "1115747762"},
    "COHAB MINAS": {"nome": "Santander", "codigo": "033", "record_id": "1115747762"},
    "COINVEST FIC": {"nome": "Santander", "codigo": "033", "record_id": "1115747762"},
    "COINVEST": {"nome": "Santander", "codigo": "033", "record_id": "1115747762"},
    "CONDOLIVRE": {"nome": "Santander", "codigo": "033", "record_id": "1115747762"},
    "CONSORCIEI FIC": {"nome": "Santander", "codigo": "033", "record_id": "1115747762"},
    "CPV": {"nome": "Santander", "codigo": "033", "record_id": "1115747762"},
    "CREDALUGA": {"nome": "Santander", "codigo": "033", "record_id": "1115747762"},
    "CREDITAS AUTO X": {"nome": "Santander", "codigo": "033", "record_id": "1115747762"},
    "D'ORO CAPITAL": {"nome": "Santander", "codigo": "033", "record_id": "1115747762"},
    "DC1": {"nome": "Santander", "codigo": "033", "record_id": "1115747762"},
    "DUCATO": {"nome": "Santander", "codigo": "033", "record_id": "1115747762"},
    "EOS": {"nome": "Santander", "codigo": "033", "record_id": "1115747762"},
    "FACTIA": {"nome": "Santander", "codigo": "033", "record_id": "1115747762"},
    "FATURE": {"nome": "Santander", "codigo": "033", "record_id": "1115747762"},
    "FRAGATA": {"nome": "Santander", "codigo": "033", "record_id": "1115747762"},
    "GAMA": {"nome": "Santander", "codigo": "033", "record_id": "1115747762"},
    "GRANA TECH": {"nome": "Santander", "codigo": "033", "record_id": "1115747762"},
    "HB CAPITAL": {"nome": "Santander", "codigo": "033", "record_id": "1115747762"},
    "HEALTH MERCANTIL": {"nome": "Santander", "codigo": "033", "record_id": "1115747762"},
    "HURST": {"nome": "Santander", "codigo": "033", "record_id": "1115747762"},
    "INDIE MERX RAIZ": {"nome": "Santander", "codigo": "033", "record_id": "1115747762"},
    "JUSINVEST": {"nome": "Santander", "codigo": "033", "record_id": "1115747762"},
    "LAVOURA FIAGRO": {"nome": "Santander", "codigo": "033", "record_id": "1115747762"},
    "MAKENA": {"nome": "Santander", "codigo": "033", "record_id": "1115747762"},
    "MARCA": {"nome": "Santander", "codigo": "033", "record_id": "1115747762"},
    "MULTIBANK": {"nome": "Santander", "codigo": "033", "record_id": "1115747762"},
    "NETMONEY": {"nome": "Santander", "codigo": "033", "record_id": "1115747762"},
    "NOBEL II": {"nome": "Santander", "codigo": "033", "record_id": "1115747762"},
    "NORDE": {"nome": "Santander", "codigo": "033", "record_id": "1115747762"},
    "NX BOATS": {"nome": "Santander", "codigo": "033", "record_id": "1115747762"},
    "ORION JN FIM CP": {"nome": "Santander", "codigo": "033", "record_id": "1115747762"},
    "ORIZ JUS CPS": {"nome": "Santander", "codigo": "033", "record_id": "1115747762"},
    "PBG SUPPLIERS": {"nome": "Santander", "codigo": "033", "record_id": "1115747762"},
    "PIC PAY": {"nome": "Santander", "codigo": "033", "record_id": "1115747762"},
    "PRECATORIOS BR": {"nome": "Santander", "codigo": "033", "record_id": "1115747762"},
    "PRIME": {"nome": "Santander", "codigo": "033", "record_id": "1115747762"},
    "PRIMEPAG": {"nome": "Santander", "codigo": "033", "record_id": "1115747762"},
    "QUASAR CHILLI BEANS": {"nome": "Santander", "codigo": "033", "record_id": "1115747762"},
    "RECOVERY LEX": {"nome": "Santander", "codigo": "033", "record_id": "1115747762"},
    "SETTORE": {"nome": "Santander", "codigo": "033", "record_id": "1115747762"},
    "SEVEN SUMMITS": {"nome": "Santander", "codigo": "033", "record_id": "1115747762"},
    "SOLFACIL VI": {"nome": "Santander", "codigo": "033", "record_id": "1115747762"},
    "TCG IRON": {"nome": "Santander", "codigo": "033", "record_id": "1115747762"},
    "TEMPUS III": {"nome": "Santander", "codigo": "033", "record_id": "1115747762"},
    "TESLA": {"nome": "Santander", "codigo": "033", "record_id": "1115747762"},
    "TRADEMASTER": {"nome": "Santander", "codigo": "033", "record_id": "1115747762"},
    "TRUST": {"nome": "Santander", "codigo": "033", "record_id": "1115747762"},
    "URBANO": {"nome": "Santander", "codigo": "033", "record_id": "1115747762"},
    "VIRTUS": {"nome": "Santander", "codigo": "033", "record_id": "1115747762"},
    "ZERMATT": {"nome": "Santander", "codigo": "033", "record_id": "1115747762"},
    
    # Fundos com Banco Santander Brasil S.A. (record_id: 1177387374)
    "AGA": {"nome": "Banco Santander Brasil S.A.", "codigo": "033", "record_id": "1177387374"},
    "AKIREDE": {"nome": "Banco Santander Brasil S.A.", "codigo": "033", "record_id": "1177387374"},
    "ALPS BANK": {"nome": "Banco Santander Brasil S.A.", "codigo": "033", "record_id": "1177387374"},
    "ALT LEGAL CLAIMS": {"nome": "Banco Santander Brasil S.A.", "codigo": "033", "record_id": "1177387374"},
    "AMG INVESTMENT FUND": {"nome": "Banco Santander Brasil S.A.", "codigo": "033", "record_id": "1177387374"},
    "ANTALLI": {"nome": "Banco Santander Brasil S.A.", "codigo": "033", "record_id": "1177387374"},
    "ATIVA": {"nome": "Banco Santander Brasil S.A.", "codigo": "033", "record_id": "1177387374"},
    "AV CAPITAL": {"nome": "Banco Santander Brasil S.A.", "codigo": "033", "record_id": "1177387374"},
    "BANCOR": {"nome": "Banco Santander Brasil S.A.", "codigo": "033", "record_id": "1177387374"},
    "BAY": {"nome": "Banco Santander Brasil S.A.", "codigo": "033", "record_id": "1177387374"},
    "BEM FACIL DIGITAL": {"nome": "Banco Santander Brasil S.A.", "codigo": "033", "record_id": "1177387374"},
    "BRAEVO": {"nome": "Banco Santander Brasil S.A.", "codigo": "033", "record_id": "1177387374"},
    "CLM II": {"nome": "Banco Santander Brasil S.A.", "codigo": "033", "record_id": "1177387374"},
    "CUB": {"nome": "Banco Santander Brasil S.A.", "codigo": "033", "record_id": "1177387374"},
    "FACIO": {"nome": "Banco Santander Brasil S.A.", "codigo": "033", "record_id": "1177387374"},
    "FINZA": {"nome": "Banco Santander Brasil S.A.", "codigo": "033", "record_id": "1177387374"},
    "GHI CAPITAL": {"nome": "Banco Santander Brasil S.A.", "codigo": "033", "record_id": "1177387374"},
    "HCAM": {"nome": "Banco Santander Brasil S.A.", "codigo": "033", "record_id": "1177387374"},
    "IGAPORÃ": {"nome": "Banco Santander Brasil S.A.", "codigo": "033", "record_id": "1177387374"},
    "INOVA CREDTECH III": {"nome": "Banco Santander Brasil S.A.", "codigo": "033", "record_id": "1177387374"},
    "KYR": {"nome": "Banco Santander Brasil S.A.", "codigo": "033", "record_id": "1177387374"},
    "LOOMY": {"nome": "Banco Santander Brasil S.A.", "codigo": "033", "record_id": "1177387374"},
    "MACAÚBAS": {"nome": "Banco Santander Brasil S.A.", "codigo": "033", "record_id": "1177387374"},
    "MOBILITAS": {"nome": "Banco Santander Brasil S.A.", "codigo": "033", "record_id": "1177387374"},
    "OKLAHOMA": {"nome": "Banco Santander Brasil S.A.", "codigo": "033", "record_id": "1177387374"},
    "ONCRED": {"nome": "Banco Santander Brasil S.A.", "codigo": "033", "record_id": "1177387374"},
    "OPI GOOROO": {"nome": "Banco Santander Brasil S.A.", "codigo": "033", "record_id": "1177387374"},
    "ORIZ": {"nome": "Banco Santander Brasil S.A.", "codigo": "033", "record_id": "1177387374"},
    "ORIZ JUS V": {"nome": "Banco Santander Brasil S.A.", "codigo": "033", "record_id": "1177387374"},
    "PAGALEVE": {"nome": "Banco Santander Brasil S.A.", "codigo": "033", "record_id": "1177387374"},
    "PJ BANC": {"nome": "Banco Santander Brasil S.A.", "codigo": "033", "record_id": "1177387374"},
    "PLETORA": {"nome": "Banco Santander Brasil S.A.", "codigo": "033", "record_id": "1177387374"},
    "SALVADOR CAPITAL": {"nome": "Banco Santander Brasil S.A.", "codigo": "033", "record_id": "1177387374"},
    "SEJA": {"nome": "Banco Santander Brasil S.A.", "codigo": "033", "record_id": "1177387374"},
    "SIM": {"nome": "Banco Santander Brasil S.A.", "codigo": "033", "record_id": "1177387374"},
    "SIMPLIC": {"nome": "Banco Santander Brasil S.A.", "codigo": "033", "record_id": "1177387374"},
    "SIRIUS": {"nome": "Banco Santander Brasil S.A.", "codigo": "033", "record_id": "1177387374"},
    "SOLFARMA": {"nome": "Banco Santander Brasil S.A.", "codigo": "033", "record_id": "1177387374"},
    "WALL": {"nome": "Banco Santander Brasil S.A.", "codigo": "033", "record_id": "1177387374"},
    "YELLOW": {"nome": "Banco Santander Brasil S.A.", "codigo": "033", "record_id": "1177387374"},
    "YUNUS": {"nome": "Banco Santander Brasil S.A.", "codigo": "033", "record_id": "1177387374"},
    
    # Fundos com Itaú Unibanco (record_id: 1188722029)
    "ALBAUGH": {"nome": "Banco Itaú Unibanco S.A", "codigo": "341", "record_id": "1188722029"},
    "ASAAS": {"nome": "Banco Itaú Unibanco S.A", "codigo": "341", "record_id": "1188722029"},
    "B4 TRUST": {"nome": "Banco Itaú Unibanco S.A", "codigo": "341", "record_id": "1188722029"},
    "BRASPRESS URBANO": {"nome": "Banco Itaú Unibanco S.A", "codigo": "341", "record_id": "1188722029"},
    "CEDRO PROPERTIES": {"nome": "Banco Itaú Unibanco S.A", "codigo": "341", "record_id": "1188722029"},
    "FORCE CAPITAL": {"nome": "Banco Itaú Unibanco S.A", "codigo": "341", "record_id": "1188722029"},
    "KANOA": {"nome": "Banco Itaú Unibanco S.A", "codigo": "341", "record_id": "1188722029"},
    "KVIV VENTURES II": {"nome": "Banco Itaú Unibanco S.A", "codigo": "341", "record_id": "1188722029"},
    "MDR II HIGH": {"nome": "Banco Itaú Unibanco S.A", "codigo": "341", "record_id": "1188722029"},
    "METROPOLITANA ATIVOS": {"nome": "Banco Itaú Unibanco S.A", "codigo": "341", "record_id": "1188722029"},
    "NC 2025": {"nome": "Banco Itaú Unibanco S.A", "codigo": "341", "record_id": "1188722029"},
    "SILVER STONE": {"nome": "Banco Itaú Unibanco S.A", "codigo": "341", "record_id": "1188722029"},
    "TOP 2025": {"nome": "Banco Itaú Unibanco S.A", "codigo": "341", "record_id": "1188722029"},
    "TOP 2025 A": {"nome": "Banco Itaú Unibanco S.A", "codigo": "341", "record_id": "1188722029"},
    "TOP 2025 B": {"nome": "Banco Itaú Unibanco S.A", "codigo": "341", "record_id": "1188722029"},
    "WCAPITAL": {"nome": "Banco Itaú Unibanco S.A", "codigo": "341", "record_id": "1188722029"},
    
    # Fundos com BCO Arbi (record_id: 1115748180)
    "BERILO": {"nome": "BCO Arbi S.A", "codigo": "213", "record_id": "1115748180"},
    "COLIBRI": {"nome": "BCO Arbi S.A", "codigo": "213", "record_id": "1115748180"},
    "FAISCA": {"nome": "BCO Arbi S.A", "codigo": "213", "record_id": "1115748180"},
    "JADE": {"nome": "BCO Arbi S.A", "codigo": "213", "record_id": "1115748180"},
    "JASPE": {"nome": "BCO Arbi S.A", "codigo": "213", "record_id": "1115748180"},
    "ONIX": {"nome": "BCO Arbi S.A", "codigo": "213", "record_id": "1115748180"},
    "QUARTZO": {"nome": "BCO Arbi S.A", "codigo": "213", "record_id": "1115748180"},
    "RUBI": {"nome": "BCO Arbi S.A", "codigo": "213", "record_id": "1115748180"},
    "TURQUESA": {"nome": "BCO Arbi S.A", "codigo": "213", "record_id": "1115748180"},
    
    # Outros bancos
    "CL & AM CAPITAL BANK": {"nome": "Bradesco S.A", "codigo": "237", "record_id": "1115748193"},
    "FIDC GOLDENTREE": {"nome": "Santander", "codigo": "033", "record_id": "1115748336"},
    "GUAJUVIRA": {"nome": "Banco do Brasil S.A", "codigo": "001", "record_id": "1115747718"},
    "J17 CONSIG": {"nome": "Santander", "codigo": "033", "record_id": "1115748336"},
    "JADE FIM CP": {"nome": "Santander", "codigo": "033", "record_id": "1115748336"},
    "SDA": {"nome": "Santander", "codigo": "033", "record_id": "1115748336"},
    "UNAVANTI": {"nome": "Unavanti Sociedade de Crédito Direto S.A", "codigo": "340", "record_id": "1115748456"},
}


def buscar_cards_fase(phase_id):
    """Busca todos os cards de uma fase com paginação"""
    all_cards = []
    has_next_page = True
    after_cursor = None
    
    while has_next_page:
        query = """
        query GetCardsInPhase($phaseId: ID!, $after: String) {
            phase(id: $phaseId) {
                id
                name
                cards(first: 50, after: $after) {
                    pageInfo {
                        hasNextPage
                        endCursor
                    }
                    edges {
                        node {
                            id
                            title
                            fields {
                                name
                                value
                            }
                        }
                    }
                }
            }
        }
        """
        
        response = requests.post(
            "https://api.pipefy.com/graphql",
            headers=HEADERS,
            json={
                "query": query,
                "variables": {
                    "phaseId": phase_id,
                    "after": after_cursor
                }
            }
        )
        
        if response.status_code != 200:
            print(f"❌ Erro HTTP: {response.status_code}")
            break
        
        data = response.json()
        if "errors" in data:
            print(f"❌ Erro GraphQL: {data['errors']}")
            break
        
        cards_data = data["data"]["phase"]["cards"]
        
        if cards_data["edges"]:
            for edge in cards_data["edges"]:
                all_cards.append(edge["node"])
        
        has_next_page = cards_data["pageInfo"]["hasNextPage"]
        after_cursor = cards_data["pageInfo"]["endCursor"]
        
        if has_next_page:
            print(f"   📄 Buscando mais cards... (já encontrados: {len(all_cards)})")
    
    return all_cards


def buscar_campo_banco():
    """Busca o ID do campo banco_2 (connector)"""
    query = """
    query GetPipeFields($pipeId: ID!) {
        pipe(id: $pipeId) {
            id
            name
            phases {
                id
                name
                fields {
                    id
                    label
                    internal_id
                    type
                }
            }
        }
    }
    """
    
    response = requests.post(
        "https://api.pipefy.com/graphql",
        headers=HEADERS,
        json={
            "query": query,
            "variables": {"pipeId": PIPE_ID}
        }
    )
    
    if response.status_code != 200:
        print(f"❌ Erro HTTP: {response.status_code}")
        return None
    
    data = response.json()
    if "errors" in data:
        print(f"❌ Erro GraphQL: {data['errors']}")
        return None
    
    pipe_data = data["data"]["pipe"]
    
    # Procurar campo Banco (connector) com internal_id 413196803
    for phase in pipe_data.get("phases", []):
        for field in phase.get("fields", []):
            if field.get("internal_id") == "413196803" and field.get("type") == "connector":
                campo_banco_id = field["id"]
                print(f"✅ Campo Banco encontrado: {field['label']} (ID: {campo_banco_id})")
                return campo_banco_id
    
    return None


def atualizar_banco_card(card_id, campo_banco_id, record_id):
    """Conecta um registro de banco ao card"""
    mutation = """
    mutation UpdateCardField($input: UpdateCardFieldInput!) {
        updateCardField(input: $input) {
            card {
                id
            }
            success
        }
    }
    """
    
    response = requests.post(
        "https://api.pipefy.com/graphql",
        headers=HEADERS,
        json={
            "query": mutation,
            "variables": {
                "input": {
                    "card_id": card_id,
                    "field_id": campo_banco_id,
                    "new_value": [record_id]  # Array com o ID do registro
                }
            }
        }
    )
    
    if response.status_code != 200:
        return False, f"Erro HTTP: {response.status_code}"
    
    data = response.json()
    if "errors" in data:
        return False, str(data['errors'])
    
    return True, "Banco conectado"


def mover_card(card_id, destination_phase_id):
    """Move um card para uma fase de destino"""
    mutation = """
    mutation MoveCard($cardId: ID!, $destinationPhaseId: ID!) {
        moveCardToPhase(input: {
            card_id: $cardId
            destination_phase_id: $destinationPhaseId
        }) {
            card {
                id
            }
        }
    }
    """
    
    response = requests.post(
        "https://api.pipefy.com/graphql",
        headers=HEADERS,
        json={
            "query": mutation,
            "variables": {
                "cardId": card_id,
                "destinationPhaseId": destination_phase_id
            }
        }
    )
    
    if response.status_code != 200:
        return False, f"Erro HTTP: {response.status_code}"
    
    data = response.json()
    if "errors" in data:
        return False, str(data['errors'])
    
    return True, "Movido"


def obter_valor_campo(card, nome_campo):
    """Obtém o valor de um campo específico do card"""
    for field in card.get("fields", []):
        if field["name"].lower() == nome_campo.lower():
            return field.get("value")
    return None


def identificar_banco_fundo(nome_fundo):
    """
    Identifica qual banco usar baseado no nome do fundo
    Retorna: (banco_info dict, chave_fundo) ou (None, None) se não encontrar
    """
    if not nome_fundo:
        return None, None
    
    nome_fundo_upper = nome_fundo.upper()
    
    for chave_fundo, banco_info in FUNDO_BANCO_MAP.items():
        if chave_fundo.upper() in nome_fundo_upper:
            return banco_info, chave_fundo
    
    return None, None


def main():
    print("=" * 80)
    print("🔄 MOVER CARDS: 2ª APROVAÇÃO → AGUARDANDO COMPROVANTE")
    print("=" * 80)
    print(f"📋 Pipe: 1 - A Liquidação (ID: {PIPE_ID})")
    print(f"🕐 Início: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print()
    print("📊 Fundos configurados:")
    for fundo, banco in FUNDO_BANCO_MAP.items():
        print(f"   • {fundo} → {banco['nome']} ({banco['codigo']})")
    print()
    
    # 1. Buscar ID do campo banco
    print("🔍 Buscando campo banco...")
    campo_banco_id = buscar_campo_banco()
    
    if not campo_banco_id:
        print("❌ Não foi possível encontrar o campo banco")
        return {'movidos': 0, 'erros': 1, 'ignorados': 0, 'total': 0}
    
    print()
    
    # IDs das fases
    FASE_ORIGEM_ID = "326914583"  # 2a Aprovação [Liquidação]
    FASE_DESTINO_ID = "325983455"  # Aguardando comprovante
    
    print("🔍 Buscando cards na fase '2a Aprovação [Liquidação]'...")
    cards = buscar_cards_fase(FASE_ORIGEM_ID)
    
    if not cards:
        print("❌ Nenhum card encontrado")
        return {'movidos': 0, 'erros': 0, 'ignorados': 0, 'total': 0}
    
    print(f"✅ {len(cards)} card(s) encontrado(s)")
    print()
    
    # Filtrar cards que têm banco configurado
    cards_com_banco = []
    cards_sem_banco = []
    
    for card in cards:
        nome_fundo = obter_valor_campo(card, "nome do fundo")
        banco_info, chave_fundo = identificar_banco_fundo(nome_fundo)
        
        if banco_info:
            cards_com_banco.append({
                "card": card,
                "nome_fundo": nome_fundo,
                "banco_info": banco_info,
                "chave_fundo": chave_fundo
            })
        else:
            cards_sem_banco.append({
                "card": card,
                "nome_fundo": nome_fundo
            })
    
    print(f"✅ {len(cards_com_banco)} card(s) com banco configurado")
    print(f"⚠️  {len(cards_sem_banco)} card(s) sem banco configurado (serão ignorados)")
    
    if cards_sem_banco:
        print("\n   Cards sem banco:")
        for item in cards_sem_banco[:5]:  # Mostrar apenas os 5 primeiros
            print(f"   - {item['card']['title']} (Fundo: {item['nome_fundo'] or 'N/A'})")
        if len(cards_sem_banco) > 5:
            print(f"   ... e mais {len(cards_sem_banco) - 5} cards")
    
    if not cards_com_banco:
        print("\nℹ️  Nenhum card para processar")
        return {'movidos': 0, 'erros': 0, 'ignorados': len(cards_sem_banco), 'total': len(cards)}
    
    print()
    print("🔄 PROCESSANDO CARDS:")
    print("=" * 80)
    
    movidos = 0
    erros = 0
    stats_por_fundo = {}
    
    for i, item in enumerate(cards_com_banco, 1):
        card = item["card"]
        nome_fundo = item["nome_fundo"]
        banco_info = item["banco_info"]
        chave_fundo = item["chave_fundo"]
        
        print(f"\n[{i}/{len(cards_com_banco)}] Card: {card['title']} (ID: {card['id']})")
        print(f"   📂 Fundo: {nome_fundo}")
        print(f"   🏦 Banco: {banco_info['nome']} ({banco_info['codigo']})")
        
        # Inicializar stats
        if chave_fundo not in stats_por_fundo:
            stats_por_fundo[chave_fundo] = {"movidos": 0, "erros": 0}
        
        # Passo 1: Conectar registro do banco ao card
        print(f"   🔗 Conectando banco ao card...")
        sucesso_banco, msg_banco = atualizar_banco_card(
            card["id"], 
            campo_banco_id, 
            banco_info["record_id"]
        )
        
        if not sucesso_banco:
            print(f"   ❌ Erro ao conectar banco: {msg_banco}")
            erros += 1
            stats_por_fundo[chave_fundo]["erros"] += 1
            continue
        
        print(f"   ✅ Banco conectado")
        
        # Passo 2: Mover card
        print(f"   📤 Movendo card...")
        sucesso_mover, msg_mover = mover_card(card["id"], FASE_DESTINO_ID)
        
        if sucesso_mover:
            print(f"   ✅ Card movido para 'Aguardando comprovante'")
            movidos += 1
            stats_por_fundo[chave_fundo]["movidos"] += 1
        else:
            print(f"   ❌ Erro ao mover: {msg_mover}")
            erros += 1
            stats_por_fundo[chave_fundo]["erros"] += 1
    
    # Resumo
    print()
    print("=" * 80)
    print("📊 RESUMO DA OPERAÇÃO:")
    print(f"   📋 Total de cards encontrados: {len(cards)}")
    print(f"   ✅ Cards movidos com sucesso: {movidos}")
    print(f"   ❌ Erros: {erros}")
    print(f"   ⚠️  Cards sem banco configurado: {len(cards_sem_banco)}")
    print()
    print("📈 Estatísticas por fundo:")
    for fundo, stats in stats_por_fundo.items():
        banco = FUNDO_BANCO_MAP[fundo]
        print(f"   • {fundo} ({banco['nome']}):")
        print(f"     ✅ Movidos: {stats['movidos']}")
        if stats['erros'] > 0:
            print(f"     ❌ Erros: {stats['erros']}")
    print(f"\n🕐 Término: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("=" * 80)
    
    # Retornar resultados para integração com launcher
    return {
        'movidos': movidos,
        'erros': erros,
        'ignorados': len(cards_sem_banco),
        'total': len(cards),
        'stats_por_fundo': stats_por_fundo
    }


if __name__ == "__main__":
    main()
