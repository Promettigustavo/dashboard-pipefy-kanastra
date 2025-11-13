import requests
import json
import os

def filtrar_cards_triagem():
    """
    Lista cards na fase 'Triagem' e identifica quais podem ser movidos
    Filtra: NÃO move cards com "Recolhimento de IOF" ou "Recolhimento de IRRF"
    """
    
    # Tentar pegar token do Streamlit secrets, senão usar hardcoded
    try:
        import streamlit as st
        api_token = st.secrets["pipefy"]["api_token"]
    except:
        # Fallback para execução local
        api_token = "eyJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJQaXBlZnkiLCJpYXQiOjE3NjExMzkxNDcsImp0aSI6ImM1NzhhYzM5LTUwZmUtNGI0NC1iMzYzLWE5ZjNhMzBmNjUwYyIsInN1YiI6MzA2ODY4NTY3LCJ1c2VyIjp7ImlkIjozMDY4Njg1NjcsImVtYWlsIjoiZ3VzdGF2by5wcm9tZXR0aUBrYW5hc3RyYS5jb20uYnIifSwidXNlcl90eXBlIjoiYXV0aGVudGljYXRlZCJ9.hjcPATGMMX1xBcRMHQ7gfjkvqB7Nq9w0Ou9tD33fIlmLoicU928x5sd_T_nmkL04DV37GtxFtF5mCFaFSa4fVQ"
    
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json"
    }
    
    print("🔍 FILTRANDO CARDS EM TRIAGEM")
    print("=" * 50)
    
    try:
        pipe_id = "303418384"  # ID do pipe "1 - A Liquidação"
        
        # Query para buscar informações do pipe e suas fases
        pipe_query = """
        query GetPipeInfo($pipeId: ID!) {
            pipe(id: $pipeId) {
                id
                name
                phases {
                    id
                    name
                    cards_count
                }
            }
        }
        """
        
        response = requests.post(
            "https://api.pipefy.com/graphql",
            headers=headers,
            json={
                "query": pipe_query,
                "variables": {"pipeId": pipe_id}
            }
        )
        
        if response.status_code != 200:
            print(f"❌ Erro HTTP: {response.status_code}")
            return
        
        result = response.json()
        
        if "errors" in result:
            print(f"❌ Erro GraphQL: {result['errors']}")
            return
        
        pipe_info = result["data"]["pipe"]
        print(f"📋 Pipe: {pipe_info['name']} (ID: {pipe_info['id']})")
        print("=" * 50)
        
        # Encontrar as fases "Triagem" e "Em Análise"
        triagem_phase = None
        analise_phase = None
        
        for phase in pipe_info['phases']:
            if phase['name'] == "Triagem":
                triagem_phase = phase
            elif phase['name'] == "Em Análise":
                analise_phase = phase
        
        if not triagem_phase:
            print("❌ Fase 'Triagem' não encontrada!")
            return
        
        if not analise_phase:
            print("❌ Fase 'Em Análise' não encontrada!")
            return
        
        print(f"\n✅ Fase origem: '{triagem_phase['name']}' (ID: {triagem_phase['id']}) - {triagem_phase['cards_count']} cards")
        print(f"✅ Fase destino: '{analise_phase['name']}' (ID: {analise_phase['id']}) - {analise_phase['cards_count']} cards")
        
        # Buscar cards na fase "Triagem" com paginação completa
        print(f"\n🔍 Buscando cards na fase '{triagem_phase['name']}'...")
        
        def buscar_todos_cards(phase_id):
            """Busca todos os cards de uma fase usando paginação"""
            all_cards = []
            has_next_page = True
            after_cursor = None
            page_count = 0
            
            cards_query = """
            query GetCardsInPhase($phaseId: ID!, $after: String) {
                phase(id: $phaseId) {
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
                                    name
                                }
                                created_at
                            }
                        }
                    }
                }
            }
            """
            
            while has_next_page:
                page_count += 1
                print(f"   � Buscando página {page_count}... (já encontrados: {len(all_cards)} cards)")
                
                response = requests.post(
                    "https://api.pipefy.com/graphql",
                    headers=headers,
                    json={
                        "query": cards_query,
                        "variables": {
                            "phaseId": phase_id,
                            "after": after_cursor
                        }
                    }
                )
                
                if response.status_code != 200:
                    print(f"❌ Erro HTTP ao buscar cards (página {page_count}): {response.status_code}")
                    break
                
                cards_result = response.json()
                
                if "errors" in cards_result:
                    print(f"❌ Erro GraphQL ao buscar cards (página {page_count}): {cards_result['errors']}")
                    break
                
                cards_data = cards_result["data"]["phase"]["cards"]
                
                # Adicionar cards da página atual
                if cards_data["edges"]:
                    for edge in cards_data["edges"]:
                        all_cards.append(edge["node"])
                
                # Verificar se há próxima página
                has_next_page = cards_data["pageInfo"]["hasNextPage"]
                after_cursor = cards_data["pageInfo"]["endCursor"]
            
            print(f"✅ Busca concluída: {len(all_cards)} cards encontrados em {page_count} página(s)")
            return all_cards
        
        # Buscar todos os cards da fase Triagem
        cards_list = buscar_todos_cards(triagem_phase['id'])
        
        if not cards_list:
            print("❌ Nenhum card encontrado na fase Triagem")
            return
        
        # Converter para formato compatível (edges format)
        cards_data = [{"node": card} for card in cards_list]
        
        # Filtros - cards que NÃO devem ser movidos
        filtros_bloqueados = [
            "Recolhimento de IOF",
            "Recolhimento de IRRF",
            "Recolhimento IOF",
            "Recolhimento IRRF"
        ]
        
        cards_movimentaveis = []
        cards_bloqueados = []
        
        print(f"\n🔍 Analisando {len(cards_data)} card(s) encontrado(s):")
        print("=" * 80)
        
        for i, edge in enumerate(cards_data, 1):
            card = edge["node"]
            card_title = card['title']
            
            # Verificar se o card está na lista de bloqueados
            bloqueado = any(filtro in card_title for filtro in filtros_bloqueados)
            
            if bloqueado:
                cards_bloqueados.append(card)
                status = "🚫 BLOQUEADO"
            else:
                cards_movimentaveis.append(card)
                status = "✅ PODE MOVER"
            
            print(f"{i}. {status}")
            print(f"   📋 {card_title}")
            print(f"   🆔 ID: {card['id']}")
            print(f"   📍 Fase: {card['current_phase']['name']}")
            print(f"   📅 Criado: {card['created_at']}")
            print("-" * 80)
        
        print(f"\n📊 RESUMO DA ANÁLISE:")
        print(f"   📋 Total de cards em 'Triagem': {len(cards_data)}")
        print(f"   ✅ Cards que PODEM ser movidos: {len(cards_movimentaveis)}")
        print(f"   🚫 Cards BLOQUEADOS: {len(cards_bloqueados)}")
        print(f"   📍 Destino: {analise_phase['name']} (ID: {analise_phase['id']})")
        
        if cards_bloqueados:
            print(f"\n🚫 CARDS BLOQUEADOS (não serão movidos):")
            for card in cards_bloqueados:
                print(f"   • {card['title']}")
        
        if cards_movimentaveis:
            print(f"\n✅ CARDS PRONTOS PARA MOVER:")
            for card in cards_movimentaveis:
                print(f"   • {card['title']}")
            
            # MOVIMENTAR OS CARDS
            print(f"\n🚀 INICIANDO MOVIMENTAÇÃO...")
            print("=" * 80)
            
            cards_movidos = []
            cards_com_erro = []
            
            for i, card in enumerate(cards_movimentaveis, 1):
                print(f"\n{i}/{len(cards_movimentaveis)} 🔄 Movendo: {card['title']} (ID: {card['id']})")
                
                # Mutation para mover o card
                move_mutation = """
                mutation MoveCardToPhase($cardId: ID!, $destinationPhaseId: ID!) {
                    moveCardToPhase(input: {
                        card_id: $cardId,
                        destination_phase_id: $destinationPhaseId
                    }) {
                        card {
                            id
                            title
                            current_phase {
                                id
                                name
                            }
                        }
                    }
                }
                """
                
                try:
                    response = requests.post(
                        "https://api.pipefy.com/graphql",
                        headers=headers,
                        json={
                            "query": move_mutation,
                            "variables": {
                                "cardId": card['id'],
                                "destinationPhaseId": analise_phase['id']
                            }
                        }
                    )
                    
                    if response.status_code != 200:
                        print(f"   ❌ Erro HTTP: {response.status_code}")
                        cards_com_erro.append(card)
                        continue
                    
                    result = response.json()
                    
                    if "errors" in result:
                        print(f"   ❌ Erro GraphQL: {result['errors']}")
                        cards_com_erro.append(card)
                        continue
                    
                    moved_card = result["data"]["moveCardToPhase"]["card"]
                    print(f"   ✅ MOVIDO! Agora está em: {moved_card['current_phase']['name']}")
                    cards_movidos.append(card)
                    
                except Exception as e:
                    print(f"   ❌ Erro inesperado: {e}")
                    cards_com_erro.append(card)
            
            # RESUMO FINAL
            print(f"\n🎉 MOVIMENTAÇÃO CONCLUÍDA!")
            print("=" * 80)
            print(f"✅ Cards movidos com sucesso: {len(cards_movidos)}")
            print(f"❌ Cards com erro: {len(cards_com_erro)}")
            print(f"🚫 Cards bloqueados (não movidos): {len(cards_bloqueados)}")
            print(f"📊 Total processado: {len(cards_data)}")
            
            if cards_movidos:
                print(f"\n✅ MOVIDOS COM SUCESSO:")
                for card in cards_movidos:
                    print(f"   • {card['title']} (ID: {card['id']})")
            
            if cards_com_erro:
                print(f"\n❌ CARDS COM ERRO:")
                for card in cards_com_erro:
                    print(f"   • {card['title']} (ID: {card['id']})")
        else:
            print(f"\nℹ️ Nenhum card para mover (todos foram bloqueados ou não há cards na triagem)")
        
        return {
            'fase_origem_id': triagem_phase['id'],
            'fase_destino_id': analise_phase['id'],
            'cards_movimentaveis': cards_movimentaveis,
            'cards_bloqueados': cards_bloqueados,
            'cards_movidos': cards_movidos if 'cards_movidos' in locals() else [],
            'cards_com_erro': cards_com_erro if 'cards_com_erro' in locals() else []
        }
        
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
        return None


def main():
    """Função principal para compatibilidade com app_streamlit.py"""
    return filtrar_cards_triagem()


if __name__ == "__main__":
    filtrar_cards_triagem()