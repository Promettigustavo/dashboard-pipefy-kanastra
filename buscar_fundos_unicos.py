import requests
import json
import pandas as pd
from datetime import datetime

def buscar_fundos_unicos_concluido():
    """
    Busca cards na fase 'Concluído' do pipe 303418439 e 
    gera tabela Excel com nomes de fundos únicos
    """
    
    # Token de autenticação
    api_token = "eyJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJQaXBlZnkiLCJpYXQiOjE3NjExMzkxNDcsImp0aSI6ImM1NzhhYzM5LTUwZmUtNGI0NC1iMzYzLWE5ZjNhMzBmNjUwYyIsInN1YiI6MzA2ODY4NTY3LCJ1c2VyIjp7ImlkIjozMDY4Njg1NjcsImVtYWlsIjoiZ3VzdGF2by5wcm9tZXR0aUBrYW5hc3RyYS5jb20uYnIifSwidXNlcl90eXBlIjoiYXV0aGVudGljYXRlZCJ9.hjcPATGMMX1xBcRMHQ7gfjkvqB7Nq9w0Ou9tD33fIlmLoicU928x5sd_T_nmkL04DV37GtxFtF5mCFaFSa4fVQ"
    
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json"
    }
    
    pipe_id = "303418439"
    
    print("🔍 BUSCANDO FASES DO PIPE")
    print("=" * 80)
    print(f"📋 Pipe ID: {pipe_id}")
    print("=" * 80)
    
    # Primeiro, buscar as fases do pipe
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
    
    try:
        response = requests.post(
            "https://api.pipefy.com/graphql",
            headers=headers,
            json={
                "query": pipe_query,
                "variables": {"pipeId": pipe_id}
            },
            timeout=30
        )
        
        if response.status_code != 200:
            print(f"❌ Erro HTTP: {response.status_code}")
            return
        
        result = response.json()
        
        if "errors" in result:
            print(f"❌ Erro GraphQL: {result['errors']}")
            return
        
        pipe_info = result["data"]["pipe"]
        print(f"\n✅ Pipe: {pipe_info['name']} (ID: {pipe_info['id']})")
        print("\n📋 Fases disponíveis:")
        
        phase_id_concluido = None
        for phase in pipe_info['phases']:
            print(f"   • {phase['name']} (ID: {phase['id']}) - {phase['cards_count']} cards")
            if 'conclu' in phase['name'].lower():
                phase_id_concluido = phase['id']
        
        if not phase_id_concluido:
            print("\n❌ Fase 'Concluído' não encontrada!")
            return
        
        print(f"\n✅ Fase Concluído encontrada: {phase_id_concluido}")
        
    except Exception as e:
        print(f"❌ Erro ao buscar fases: {e}")
        return
    
    # Agora buscar os cards
    print("\n" + "=" * 80)
    print("🔍 BUSCANDO CARDS DA FASE CONCLUÍDO")
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
            print(f"📄 Buscando página {page_count}... (total: {len(all_cards)} cards)")
            
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
                    print(f"❌ Erro HTTP: {response.status_code}")
                    break
                
                cards_result = response.json()
                
                if "errors" in cards_result:
                    print(f"❌ Erro GraphQL: {cards_result['errors']}")
                    break
                
                cards_data = cards_result["data"]["phase"]["cards"]
                
                if cards_data["edges"]:
                    for edge in cards_data["edges"]:
                        all_cards.append(edge["node"])
                
                has_next_page = cards_data["pageInfo"]["hasNextPage"]
                after_cursor = cards_data["pageInfo"]["endCursor"]
                
            except Exception as e:
                print(f"❌ Erro: {e}")
                break
        
        print(f"\n✅ Busca concluída: {len(all_cards)} cards encontrados")
        return all_cards
    
    # Buscar todos os cards
    cards_list = buscar_todos_cards(phase_id_concluido)
    
    if not cards_list:
        print("\n❌ Nenhum card encontrado")
        return
    
    # Extrair nomes dos fundos
    print("\n" + "=" * 80)
    print("🔍 EXTRAINDO NOMES DOS FUNDOS")
    print("=" * 80)
    
    fundos_info = []
    fundos_set = set()
    
    for card in cards_list:
        # Buscar campo "Nome do Fundo"
        nome_fundo = None
        for field in card.get('fields', []):
            if field.get('name') and 'nome' in field['name'].lower() and 'fundo' in field['name'].lower():
                nome_fundo = field.get('value', '').strip()
                break
        
        # Se não encontrou nos campos, usar o título do card
        if not nome_fundo:
            nome_fundo = card.get('title', '').strip()
        
        if nome_fundo and nome_fundo not in fundos_set:
            fundos_set.add(nome_fundo)
            fundos_info.append({
                'Nome do Fundo': nome_fundo,
                'Primeiro Card ID': card.get('id', ''),
                'Data Criação': card.get('created_at', '')
            })
    
    # Criar DataFrame
    df = pd.DataFrame(fundos_info)
    df = df.sort_values('Nome do Fundo')
    
    print(f"\n✅ {len(df)} fundos únicos encontrados")
    
    # Exibir primeiros fundos
    print("\n📋 Primeiros 10 fundos:")
    for i, row in df.head(10).iterrows():
        print(f"   {i+1}. {row['Nome do Fundo']}")
    
    if len(df) > 10:
        print(f"   ... e mais {len(df) - 10} fundos")
    
    # Salvar em Excel
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    arquivo_excel = f"fundos_unicos_concluido_{timestamp}.xlsx"
    
    try:
        with pd.ExcelWriter(arquivo_excel, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Fundos Únicos', index=False)
            
            worksheet = writer.sheets['Fundos Únicos']
            for idx, col in enumerate(df.columns):
                max_length = max(
                    df[col].astype(str).apply(len).max(),
                    len(col)
                ) + 2
                worksheet.column_dimensions[chr(65 + idx)].width = min(max_length, 60)
        
        print(f"\n💾 Arquivo Excel salvo: {arquivo_excel}")
        
    except Exception as e:
        print(f"\n❌ Erro ao salvar Excel: {e}")
    
    print("\n" + "=" * 80)
    print(f"✅ PROCESSO CONCLUÍDO - {len(df)} fundos únicos")
    print("=" * 80)
    
    return df


if __name__ == "__main__":
    df = buscar_fundos_unicos_concluido()
