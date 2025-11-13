import requests
import json

# Configurações
PIPEFY_API_URL = "https://api.pipefy.com/graphql"
PIPEFY_TOKEN = "eyJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJQaXBlZnkiLCJpYXQiOjE3NjExMzkxNDcsImp0aSI6ImM1NzhhYzM5LTUwZmUtNGI0NC1iMzYzLWE5ZjNhMzBmNjUwYyIsInN1YiI6MzA2ODY4NTY3LCJ1c2VyIjp7ImlkIjozMDY4Njg1NjcsImVtYWlsIjoiZ3VzdGF2by5wcm9tZXR0aUBrYW5hc3RyYS5jb20uYnIifSwidXNlcl90eXBlIjoiYXV0aGVudGljYXRlZCJ9.hjcPATGMMX1xBcRMHQ7gfjkvqB7Nq9w0Ou9tD33fIlmLoicU928x5sd_T_nmkL04DV37GtxFtF5mCFaFSa4fVQ"

FASE_AGUARDANDO_COMPROVANTES_ID = "322673487"

def buscar_card_com_comprovante():
    """Busca cards que têm o comprovante anexado"""
    print(f"\n{'='*80}")
    print(f"BUSCANDO CARDS COM COMPROVANTE ANEXADO")
    print(f"{'='*80}\n")
    
    query = """
    query($phaseId: ID!) {
        phase(id: $phaseId) {
            cards(first: 50) {
                edges {
                    node {
                        id
                        title
                        fields {
                            name
                            value
                            field {
                                id
                                type
                            }
                        }
                    }
                }
            }
        }
    }
    """
    
    headers = {
        "Authorization": f"Bearer {PIPEFY_TOKEN}",
        "Content-Type": "application/json"
    }
    
    response = requests.post(
        PIPEFY_API_URL,
        headers=headers,
        json={
            "query": query,
            "variables": {"phaseId": FASE_AGUARDANDO_COMPROVANTES_ID}
        }
    )
    
    if response.status_code != 200:
        print(f"❌ Erro: {response.status_code}")
        return
    
    data = response.json()
    cards = data['data']['phase']['cards']['edges']
    
    print(f"Total de cards: {len(cards)}\n")
    
    for edge in cards:
        card = edge['node']
        
        # Verificar se tem o campo de anexo preenchido
        tem_anexo = False
        valor_anexo = None
        valor_sim_nao = None
        
        for field in card['fields']:
            field_name = field['name'].lower()
            field_value = field['value']
            field_type = field['field']['type']
            
            if field_type == 'attachment' and field_value:
                tem_anexo = True
                valor_anexo = field_value
            
            if 'comprovante anexado corretamente' in field_name:
                valor_sim_nao = field_value
        
        if tem_anexo:
            print(f"{'='*80}")
            print(f"Card ID: {card['id']}")
            print(f"Título: {card['title']}")
            print(f"Anexo: {valor_anexo}")
            print(f"Marcado como Sim?: {valor_sim_nao}")
            print()

if __name__ == "__main__":
    buscar_card_com_comprovante()
