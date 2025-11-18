"""
Busca Cards Pipefy - Versão Simples
Retorna os cards do pipe de liquidação sem tratamento
"""

import requests
import json
from datetime import datetime


PIPEFY_API_TOKEN = "eyJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJQaXBlZnkiLCJpYXQiOjE3NjExMzkxNDcsImp0aSI6ImM1NzhhYzM5LTUwZmUtNGI0NC1iMzYzLWE5ZjNhMzBmNjUwYyIsInN1YiI6MzA2ODY4NTY3LCJ1c2VyIjp7ImlkIjozMDY4Njg1NjcsImVtYWlsIjoiZ3VzdGF2by5wcm9tZXR0aUBrYW5hc3RyYS5jb20uYnIifSwidXNlcl90eXBlIjoiYXV0aGVudGljYXRlZCJ9.hjcPATGMMX1xBcRMHQ7gfjkvqB7Nq9w0Ou9tD33fIlmLoicU928x5sd_T_nmkL04DV37GtxFtF5mCFaFSa4fVQ"

# IDs do Pipe de Liquidação
PIPE_LIQUIDACAO_ID = "303418384"
FASE_AGUARDANDO_COMPROVANTE = "325983455"
FASE_SOLICITACAO_PAGA = "321352632"


def buscar_cards_fase(fase_id, pipe_id=PIPE_LIQUIDACAO_ID):
    """
    Busca cards de uma fase específica do Pipefy
    
    Args:
        fase_id: ID da fase
        pipe_id: ID do pipe
    
    Returns:
        list: Lista de cards sem tratamento
    """
    url = "https://api.pipefy.com/graphql"
    
    headers = {
        "Authorization": f"Bearer {PIPEFY_API_TOKEN}",
        "Content-Type": "application/json"
    }
    
    query = """
    query($phaseId: ID!) {
        phase(id: $phaseId) {
            name
            cards_count
            cards {
                edges {
                    node {
                        id
                        title
                        created_at
                        updated_at
                        due_date
                        assignees {
                            id
                            name
                        }
                        fields {
                            name
                            value
                            filled_at
                            field {
                                id
                                type
                            }
                        }
                        comments {
                            id
                            text
                            author {
                                name
                            }
                        }
                        labels {
                            name
                        }
                    }
                }
            }
        }
    }
    """
    
    variables = {
        "phaseId": fase_id
    }
    
    try:
        response = requests.post(
            url,
            headers=headers,
            json={"query": query, "variables": variables},
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        
        if 'errors' in data:
            print(f"❌ Erro GraphQL: {data['errors']}")
            return None
        
        return data.get('data', {}).get('phase', {})
    except Exception as e:
        print(f"❌ Erro ao buscar cards: {e}")
        return None


def main():
    """
    Função principal
    """
    print("=" * 80)
    print("BUSCA DE CARDS PIPEFY - LIQUIDAÇÃO")
    print("=" * 80)
    
    # Selecionar fase
    print("\n📋 Fases disponíveis:")
    print("   1. Aguardando Comprovante")
    print("   2. Solicitação Paga")
    
    escolha = int(input("\nEscolha o número da fase: "))
    
    if escolha == 1:
        fase_id = FASE_AGUARDANDO_COMPROVANTE
        fase_nome = "Aguardando Comprovante"
    elif escolha == 2:
        fase_id = FASE_SOLICITACAO_PAGA
        fase_nome = "Solicitação Paga"
    else:
        print("❌ Opção inválida")
        return
    
    print(f"\n✅ Fase selecionada: {fase_nome}")
    print(f"   ID: {fase_id}")
    
    # Buscar cards
    print("\n📊 Buscando cards...")
    resposta_api = buscar_cards_fase(fase_id)
    
    if not resposta_api:
        print("❌ Falha ao buscar cards")
        return
    
    # Extrair e analisar cards
    cards_edges = resposta_api.get('cards', {}).get('edges', [])
    cards_count = resposta_api.get('cards_count', 0)
    
    print("\n" + "=" * 80)
    print(f"ANÁLISE DOS CARDS - {cards_count} CARD(S) ENCONTRADO(S)")
    print("=" * 80)
    
    for idx, edge in enumerate(cards_edges, 1):
        card = edge.get('node', {})
        
        print(f"\n{'─' * 80}")
        print(f"CARD #{idx}")
        print(f"{'─' * 80}")
        
        # Dados principais
        print(f"\n📋 IDENTIFICAÇÃO:")
        print(f"   ID: {card.get('id', 'N/A')}")
        print(f"   Título: {card.get('title', 'N/A')}")
        print(f"   Criado em: {card.get('created_at', 'N/A')}")
        print(f"   Atualizado em: {card.get('updated_at', 'N/A')}")
        print(f"   Vencimento: {card.get('due_date', 'N/A')}")
        
        # Responsáveis
        assignees = card.get('assignees', [])
        if assignees:
            print(f"\n👥 RESPONSÁVEIS:")
            for assignee in assignees:
                print(f"   - {assignee.get('name', 'N/A')} (ID: {assignee.get('id', 'N/A')})")
        
        # Labels
        labels = card.get('labels', [])
        if labels:
            print(f"\n🏷️ LABELS:")
            for label in labels:
                print(f"   - {label.get('name', 'N/A')}")
        
        # Campos
        fields = card.get('fields', [])
        if fields:
            print(f"\n📝 CAMPOS ({len(fields)}):")
            for field in fields:
                nome = field.get('name', 'N/A')
                valor = field.get('value', 'N/A')
                tipo = field.get('field', {}).get('type', 'N/A')
                print(f"   • {nome}: {valor}")
                print(f"     Tipo: {tipo}")
        
        # Comentários
        comments = card.get('comments', [])
        if comments:
            print(f"\n💬 COMENTÁRIOS ({len(comments)}):")
            for comment in comments:
                autor = comment.get('author', {}).get('name', 'N/A')
                texto = comment.get('text', 'N/A')
                print(f"   • {autor}: {texto[:100]}...")
        
        # Dados completos (JSON)
        print(f"\n📄 DADOS COMPLETOS (JSON):")
        print(json.dumps(card, indent=2, ensure_ascii=False))
    
    # Mostrar resposta completa da API
    print("\n" + "=" * 80)
    print("RESPOSTA COMPLETA DA API (RAW)")
    print("=" * 80)
    print(json.dumps(resposta_api, indent=2, ensure_ascii=False))
    
    # Salvar em arquivo
    filename = f"cards_pipefy_raw_{fase_nome.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(resposta_api, f, indent=2, ensure_ascii=False)
    
    print("\n" + "=" * 80)
    print(f"✅ Resposta salva em: {filename}")
    print("=" * 80)


if __name__ == "__main__":
    main()
