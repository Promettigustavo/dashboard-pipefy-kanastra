import requests
import json
from datetime import datetime

def buscar_cards_concluido(filtrar_prestadores=False):
    """
    Busca cards na fase 'Concluído' do pipe de Liquidação
    Pipe ID: 303418384
    Fase ID: 327310320
    
    Args:
        filtrar_prestadores (bool): Se True, retorna apenas cards de prestadores de serviço
    """
    
    # Token de autenticação
    api_token = "eyJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJQaXBlZnkiLCJpYXQiOjE3NjExMzkxNDcsImp0aSI6ImM1NzhhYzM5LTUwZmUtNGI0NC1iMzYzLWE5ZjNhMzBmNjUwYyIsInN1YiI6MzA2ODY4NTY3LCJ1c2VyIjp7ImlkIjozMDY4Njg1NjcsImVtYWlsIjoiZ3VzdGF2by5wcm9tZXR0aUBrYW5hc3RyYS5jb20uYnIifSwidXNlcl90eXBlIjoiYXV0aGVudGljYXRlZCJ9.hjcPATGMMX1xBcRMHQ7gfjkvqB7Nq9w0Ou9tD33fIlmLoicU928x5sd_T_nmkL04DV37GtxFtF5mCFaFSa4fVQ"
    
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json"
    }
    
    pipe_id = "303418439"  # Pipe Liquidação
    phase_id = "327310320"  # Fase Concluído
    
    print("🔍 BUSCANDO CARDS NA FASE CONCLUÍDO")
    print("=" * 80)
    print(f"📋 Pipe ID: {pipe_id}")
    print(f"📍 Fase ID: {phase_id}")
    if filtrar_prestadores:
        print(f"🔧 Filtro: APENAS PRESTADORES DE SERVIÇO")
    print("=" * 80)
    
    def buscar_todos_cards(phase_id):
        """Busca todos os cards de uma fase usando paginação"""
        all_cards = []
        has_next_page = True
        after_cursor = None
        page_count = 0
        
        cards_query = """
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
                            current_phase {
                                id
                                name
                            }
                            created_at
                            updated_at
                            finished_at
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
        
        while has_next_page:
            page_count += 1
            print(f"\n📄 Buscando página {page_count}... (total encontrado: {len(all_cards)} cards)")
            
            try:
                response = requests.post(
                    "https://api.pipefy.com/graphql",
                    headers=headers,
                    json={
                        "query": cards_query,
                        "variables": {
                            "phaseId": phase_id,
                            "after": after_cursor
                        }
                    },
                    timeout=30
                )
                
                if response.status_code != 200:
                    print(f"❌ Erro HTTP ao buscar cards (página {page_count}): {response.status_code}")
                    print(f"   Resposta: {response.text}")
                    break
                
                cards_result = response.json()
                
                if "errors" in cards_result:
                    print(f"❌ Erro GraphQL ao buscar cards (página {page_count}):")
                    print(f"   {json.dumps(cards_result['errors'], indent=2)}")
                    break
                
                cards_data = cards_result["data"]["phase"]["cards"]
                
                # Adicionar cards da página atual
                if cards_data["edges"]:
                    for edge in cards_data["edges"]:
                        all_cards.append(edge["node"])
                
                # Verificar se há próxima página
                has_next_page = cards_data["pageInfo"]["hasNextPage"]
                after_cursor = cards_data["pageInfo"]["endCursor"]
                
            except requests.exceptions.RequestException as e:
                print(f"❌ Erro de conexão ao buscar cards (página {page_count}): {e}")
                break
            except Exception as e:
                print(f"❌ Erro inesperado ao buscar cards (página {page_count}): {e}")
                break
        
        print(f"\n✅ Busca concluída: {len(all_cards)} cards encontrados em {page_count} página(s)")
        return all_cards
    
    # Buscar todos os cards da fase Concluído
    cards_list = buscar_todos_cards(phase_id)
    
    if not cards_list:
        print("\n❌ Nenhum card encontrado na fase Concluído")
        return []
    
    # Filtrar prestadores de serviço se solicitado
    if filtrar_prestadores:
        print("\n🔧 Aplicando filtro de prestadores de serviço...")
        cards_filtrados = []
        
        for card in cards_list:
            # Buscar campo "Tipo de Pagamento" nos fields
            tipo_pagamento = None
            for field in card.get('fields', []):
                if field['name'] and 'tipo' in field['name'].lower() and 'pagamento' in field['name'].lower():
                    tipo_pagamento = field.get('value', '')
                    break
            
            # Verificar se é prestador de serviço
            # Possíveis valores: "Prestador de Serviço", "Prestadores", etc.
            if tipo_pagamento and 'prestador' in str(tipo_pagamento).lower():
                cards_filtrados.append(card)
        
        print(f"✅ Filtrados: {len(cards_filtrados)} de {len(cards_list)} cards são prestadores de serviço")
        cards_list = cards_filtrados
    
    if not cards_list:
        print("\n❌ Nenhum card de prestador de serviço encontrado")
        return []
    
    # Exibir resumo dos cards
    print("\n" + "=" * 80)
    print(f"📊 RESUMO: {len(cards_list)} CARDS ENCONTRADOS")
    print("=" * 80)
    
    # Exibir os primeiros 10 cards como exemplo
    print("\n📋 Primeiros cards encontrados:")
    print("-" * 80)
    
    for i, card in enumerate(cards_list[:10], 1):
        print(f"\n{i}. {card['title']}")
        print(f"   🆔 ID: {card['id']}")
        print(f"   📍 Fase: {card['current_phase']['name']}")
        print(f"   📅 Criado: {card['created_at']}")
        print(f"   📅 Atualizado: {card['updated_at']}")
        if card.get('finished_at'):
            print(f"   ✅ Finalizado: {card['finished_at']}")
        print("-" * 80)
    
    if len(cards_list) > 10:
        print(f"\n... e mais {len(cards_list) - 10} cards")
    
    # Salvar em arquivo JSON
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if filtrar_prestadores:
        filename = f"cards_concluido_prestadores_{timestamp}.json"
    else:
        filename = f"cards_concluido_{timestamp}.json"
    
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(cards_list, f, indent=2, ensure_ascii=False)
        print(f"\n💾 Cards salvos em: {filename}")
    except Exception as e:
        print(f"\n❌ Erro ao salvar arquivo: {e}")
    
    return cards_list


if __name__ == "__main__":
    # Para buscar todos os cards:
    # cards = buscar_cards_concluido()
    
    # Para buscar apenas prestadores de serviço:
    cards = buscar_cards_concluido(filtrar_prestadores=True)
    
    print("\n" + "=" * 80)
    print(f"✅ PROCESSO CONCLUÍDO - Total: {len(cards)} cards")
    print("=" * 80)
