"""
Script para listar todas as fases dos Pipes (Liquidação e Taxas)
Mostra ID e nome de cada fase para uso direto no código
"""

import requests
import json

# Configurações da API
PIPEFY_API_URL = "https://api.pipefy.com/graphql"
PIPEFY_API_TOKEN = "eyJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJQaXBlZnkiLCJpYXQiOjE3NjExMzkxNDcsImp0aSI6ImM1NzhhYzM5LTUwZmUtNGI0NC1iMzYzLWE5ZjNhMzBmNjUwYyIsInN1YiI6MzA2ODY4NTY3LCJ1c2VyIjp7ImlkIjozMDY4Njg1NjcsImVtYWlsIjoiZ3VzdGF2by5wcm9tZXR0aUBrYW5hc3RyYS5jb20uYnIifSwidXNlcl90eXBlIjoiYXV0aGVudGljYXRlZCJ9.hjcPATGMMX1xBcRMHQ7gfjkvqB7Nq9w0Ou9tD33fIlmLoicU928x5sd_T_nmkL04DV37GtxFtF5mCFaFSa4fVQ"

# IDs dos Pipes
PIPE_LIQUIDACAO_ID = "303418384"
PIPE_TAXAS_ID = "303667924"


def listar_fases_pipe(pipe_id, nome_pipe):
    """
    Lista todas as fases de um pipe
    
    Args:
        pipe_id: ID do pipe
        nome_pipe: Nome do pipe (para exibição)
    """
    print(f"\n{'='*80}")
    print(f"📋 PIPE: {nome_pipe}")
    print(f"🆔 ID: {pipe_id}")
    print(f"{'='*80}\n")
    
    query = """
    query GetPipePhases($pipeId: ID!) {
        pipe(id: $pipeId) {
            name
            phases {
                id
                name
                cards_count
            }
        }
    }
    """
    
    variables = {
        "pipeId": str(pipe_id)
    }
    
    headers = {
        "Authorization": f"Bearer {PIPEFY_API_TOKEN}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(
            PIPEFY_API_URL,
            headers=headers,
            json={
                "query": query,
                "variables": variables
            },
            timeout=10
        )
        
        if response.status_code != 200:
            print(f"❌ Erro HTTP: {response.status_code}")
            print(f"Resposta: {response.text}")
            return None
        
        data = response.json()
        
        if 'errors' in data:
            print(f"❌ Erro GraphQL: {data['errors']}")
            return None
        
        pipe_data = data.get('data', {}).get('pipe', {})
        phases = pipe_data.get('phases', [])
        
        print(f"Total de fases: {len(phases)}\n")
        
        for i, phase in enumerate(phases, 1):
            phase_id = phase.get('id')
            phase_name = phase.get('name')
            cards_count = phase.get('cards_count', 0)
            
            print(f"{i}. {phase_name}")
            print(f"   ID: {phase_id}")
            print(f"   Cards: {cards_count}")
            print()
        
        return phases
        
    except Exception as e:
        print(f"❌ Exceção: {type(e).__name__}: {e}")
        return None


def gerar_codigo_constantes(phases_liquidacao, phases_taxas):
    """
    Gera código Python com constantes dos IDs das fases
    """
    print(f"\n{'='*80}")
    print("📝 CÓDIGO PARA ADICIONAR NOS ARQUIVOS")
    print(f"{'='*80}\n")
    
    print("# ==================== IDs DAS FASES ====================")
    print()
    
    if phases_liquidacao:
        print("# Pipe Liquidação")
        for phase in phases_liquidacao:
            phase_name = phase.get('name', '').upper().replace(' ', '_').replace('Ã', 'A').replace('Ç', 'C')
            phase_id = phase.get('id')
            print(f'FASE_LIQUIDACAO_{phase_name} = "{phase_id}"  # {phase.get("name")}')
    
    print()
    
    if phases_taxas:
        print("# Pipe Taxas")
        for phase in phases_taxas:
            phase_name = phase.get('name', '').upper().replace(' ', '_').replace('Ã', 'A').replace('Ç', 'C')
            phase_id = phase.get('id')
            print(f'FASE_TAXAS_{phase_name} = "{phase_id}"  # {phase.get("name")}')
    
    print()
    print("# ========================================================")


def main():
    """
    Função principal
    """
    print("\n" + "="*80)
    print("🔍 LISTANDO FASES DOS PIPES PIPEFY")
    print("="*80)
    
    # Listar fases do Pipe Liquidação
    phases_liquidacao = listar_fases_pipe(PIPE_LIQUIDACAO_ID, "Pipe Liquidação")
    
    # Listar fases do Pipe Taxas
    phases_taxas = listar_fases_pipe(PIPE_TAXAS_ID, "Pipe Taxas")
    
    # Gerar código com constantes
    if phases_liquidacao or phases_taxas:
        gerar_codigo_constantes(phases_liquidacao, phases_taxas)
    
    print("\n" + "="*80)
    print("✅ CONCLUÍDO!")
    print("="*80 + "\n")
    
    # Salvar em arquivo JSON para referência
    dados = {
        "pipe_liquidacao": {
            "id": PIPE_LIQUIDACAO_ID,
            "phases": phases_liquidacao or []
        },
        "pipe_taxas": {
            "id": PIPE_TAXAS_ID,
            "phases": phases_taxas or []
        }
    }
    
    with open("fases_pipes.json", "w", encoding="utf-8") as f:
        json.dump(dados, f, indent=2, ensure_ascii=False)
    
    print("📄 Dados salvos em: fases_pipes.json\n")


if __name__ == "__main__":
    main()
