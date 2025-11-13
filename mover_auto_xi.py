"""
Move cards do AUTO XI da fase "2ª Aprovação" para "Aguardando Comprovante"
Cria registro de banco (Santander - 033) automaticamente
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


def buscar_table_id_banco():
    """Busca o ID da tabela de banco no pipe através dos campos nas fases"""
    # Primeira query: buscar o campo banco_2
    query1 = """
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
            "query": query1,
            "variables": {"pipeId": PIPE_ID}
        }
    )
    
    if response.status_code != 200:
        print(f"❌ Erro HTTP: {response.status_code}")
        return None, None
    
    data = response.json()
    if "errors" in data:
        print(f"❌ Erro GraphQL: {data['errors']}")
        return None, None
    
    pipe_data = data["data"]["pipe"]
    
    # Procurar campo Banco (connector) com internal_id 413196803
    campo_banco_id = None
    
    for phase in pipe_data.get("phases", []):
        for field in phase.get("fields", []):
            if field.get("internal_id") == "413196803" and field.get("type") == "connector":
                campo_banco_id = field["id"]
                print(f"✅ Campo Banco encontrado: {field['label']} (ID: {campo_banco_id})")
                break
        if campo_banco_id:
            break
    
    if not campo_banco_id:
        return None, None
    
    # Segunda query: buscar as opções (registros) do campo connector
    query2 = """
    query GetFieldOptions($repoId: ID!) {
        phase(id: "326914583") {
            fields {
                id
                options
            }
        }
    }
    """
    
    # Por enquanto, vamos retornar apenas o campo_id e buscar o table_id de outra forma
    # O table_id pode ser obtido através da API de table_records diretamente
    return campo_banco_id, "banco_2"  # Retorna o internal_id como placeholder


def buscar_registro_santander(campo_banco_id):
    """
    Retorna o ID do registro Santander da database "Lista de Bancos"
    ID descoberto através de cards já preenchidos: 1115747762
    """
    santander_record_id = "1115747762"
    print(f"✅ Usando registro Santander (ID: {santander_record_id})")
    return santander_record_id


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


def main():
    print("=" * 80)
    print("🔄 MOVER CARDS AUTO XI: 2ª APROVAÇÃO → AGUARDANDO COMPROVANTE")
    print("=" * 80)
    print(f"📋 Pipe: 1 - A Liquidação (ID: {PIPE_ID})")
    print(f"🏦 Banco: Santander (033)")
    print(f"🕐 Início: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print()
    
    # 1. Buscar ID do campo banco e tabela
    print("🔍 Buscando informações do campo banco...")
    campo_banco_id, table_id = buscar_table_id_banco()
    
    if not campo_banco_id or not table_id:
        print("❌ Não foi possível encontrar o campo de banco ou tabela")
        return
    
    print()
    
    # 2. Buscar registro do Santander
    print("🔍 Buscando registro do Santander (033)...")
    santander_record_id = buscar_registro_santander(campo_banco_id)
    
    if not santander_record_id:
        print("❌ Não foi possível encontrar o registro do Santander")
        return
    
    print()
    
    # IDs das fases
    FASE_ORIGEM_ID = "326914583"  # 2a Aprovação [Liquidação]
    FASE_DESTINO_ID = "325983455"  # Aguardando comprovante
    
    print("🔍 Buscando cards na fase '2a Aprovação [Liquidação]'...")
    cards = buscar_cards_fase(FASE_ORIGEM_ID)
    
    if not cards:
        print("❌ Nenhum card encontrado")
        return
    
    print(f"✅ {len(cards)} card(s) encontrado(s)")
    print()
    
    # Filtrar apenas cards do AUTO XI
    cards_auto_xi = []
    for card in cards:
        nome_fundo = obter_valor_campo(card, "nome do fundo")
        if nome_fundo and "AUTO XI" in nome_fundo.upper():
            cards_auto_xi.append(card)
    
    print(f"✅ {len(cards_auto_xi)} card(s) do AUTO XI encontrado(s)")
    
    if not cards_auto_xi:
        print("ℹ️  Nenhum card do AUTO XI para processar")
        return
    
    print()
    print("🔄 PROCESSANDO CARDS:")
    print("=" * 80)
    
    movidos = 0
    erros = 0
    
    for i, card in enumerate(cards_auto_xi, 1):
        print(f"\n[{i}/{len(cards_auto_xi)}] Card: {card['title']} (ID: {card['id']})")
        nome_fundo = obter_valor_campo(card, "nome do fundo")
        print(f"   📂 Fundo: {nome_fundo}")
        
        # Passo 1: Conectar registro do Santander ao card
        print(f"   🏦 Conectando banco Santander ao card...")
        sucesso_banco, msg_banco = atualizar_banco_card(card["id"], campo_banco_id, santander_record_id)
        
        if not sucesso_banco:
            print(f"   ❌ Erro ao conectar banco: {msg_banco}")
            erros += 1
            continue
        
        print(f"   ✅ Banco conectado")
        
        # Passo 2: Mover card
        print(f"   📤 Movendo card...")
        sucesso_mover, msg_mover = mover_card(card["id"], FASE_DESTINO_ID)
        
        if sucesso_mover:
            print(f"   ✅ Card movido para 'Aguardando comprovante'")
            movidos += 1
        else:
            print(f"   ❌ Erro ao mover: {msg_mover}")
            erros += 1
    
    # Resumo
    print()
    print("=" * 80)
    print("📊 RESUMO DA OPERAÇÃO:")
    print(f"   📋 Total de cards AUTO XI: {len(cards_auto_xi)}")
    print(f"   ✅ Cards movidos com sucesso: {movidos}")
    print(f"   ❌ Erros: {erros}")
    print(f"   🏦 Banco configurado: Santander (033)")
    print(f"🕐 Término: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("=" * 80)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Operação interrompida")
    except Exception as e:
        print(f"\n\n❌ Erro: {e}")
        import traceback
        traceback.print_exc()
