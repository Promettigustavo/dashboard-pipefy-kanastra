import os
import json
import requests
from datetime import datetime
import re

# Configurações
PIPEFY_API_URL = "https://api.pipefy.com/graphql"
PIPEFY_API_TOKEN = "eyJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJQaXBlZnkiLCJpYXQiOjE3NjExMzkxNDcsImp0aSI6ImM1NzhhYzM5LTUwZmUtNGI0NC1iMzYzLWE5ZjNhMzBmNjUwYyIsInN1YiI6MzA2ODY4NTY3LCJ1c2VyIjp7ImlkIjozMDY4Njg1NjcsImVtYWlsIjoiZ3VzdGF2by5wcm9tZXR0aUBrYW5hc3RyYS5jb20uYnIifSwidXNlcl90eXBlIjoiYXV0aGVudGljYXRlZCJ9.hjcPATGMMX1xBcRMHQ7gfjkvqB7Nq9w0Ou9tD33fIlmLoicU928x5sd_T_nmkL04DV37GtxFtF5mCFaFSa4fVQ"

# IDs corretos do pipe de taxas
PIPE_TAXAS_ID = "303667924"
FASE_AGUARDANDO_COMPROVANTES_ID = "322673487"

headers = {
    "Authorization": f"Bearer {PIPEFY_API_TOKEN}",
    "Content-Type": "application/json"
}

def buscar_cards_aguardando():
    """Busca todos os cards na fase 'Aguardando Comprovante'"""
    print("🔍 Buscando cards na fase 'Aguardando Comprovante'...")
    
    query = """
    query($phaseId: ID!, $after: String) {
        phase(id: $phaseId) {
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
    
    all_cards = []
    has_next_page = True
    after_cursor = None
    
    while has_next_page:
        variables = {
            "phaseId": FASE_AGUARDANDO_COMPROVANTES_ID,
            "after": after_cursor
        }
        
        response = requests.post(
            PIPEFY_API_URL,
            headers=headers,
            json={"query": query, "variables": variables}
        )
        
        if response.status_code == 200:
            data = response.json()
            if 'data' in data and data['data']['phase']:
                phase_data = data['data']['phase']
                cards_data = phase_data['cards']
                
                for edge in cards_data['edges']:
                    all_cards.append(edge['node'])
                
                has_next_page = cards_data['pageInfo']['hasNextPage']
                after_cursor = cards_data['pageInfo']['endCursor']
            else:
                print(f"❌ Erro na resposta: {data}")
                break
        else:
            print(f"❌ Erro HTTP {response.status_code}: {response.text}")
            break
    
    print(f"✅ Encontrados {len(all_cards)} cards")
    return all_cards

def extrair_dados_card(card):
    """Extrai dados importantes do card"""
    card_data = {
        "id": card["id"],
        "title": card["title"],
        "valor": None,
        "data_pagamento": None,
        "fundo": None,
        "favorecido": None,
        "anexo_atual": None
    }
    
    for field in card["fields"]:
        field_id = field["field"]["id"]
        field_name = field["name"].lower()
        value = field["value"]
        
        # Mapear campos importantes
        if "valor" in field_name and "favorecido" in field_name:
            card_data["valor"] = value
        elif "data" in field_name and "pagamento" in field_name:
            card_data["data_pagamento"] = value
        elif field_name == "fundo" or "fundo" in field_name:
            card_data["fundo"] = value
        elif "favorecido" in field_name and "nome" in field_name:
            card_data["favorecido"] = value
        elif field["field"]["type"] == "attachment" and value:
            card_data["anexo_atual"] = value
    
    return card_data

def normalizar_valor(valor_str):
    """Normaliza valor para comparação"""
    if not valor_str:
        return None
    
    # Remove espaços e caracteres especiais, mantém números, vírgulas e pontos
    valor_limpo = re.sub(r'[^\d,.]', '', str(valor_str))
    
    if not valor_limpo:
        return None
    
    try:
        # Se tem vírgula, considera formato brasileiro (1.234,56)
        if ',' in valor_limpo:
            # Remove pontos (separador de milhar) e troca vírgula por ponto
            valor_limpo = valor_limpo.replace('.', '').replace(',', '.')
        # Se só tem ponto, pode ser formato americano ou separador de milhar
        elif '.' in valor_limpo:
            # Se tem mais de um ponto ou o último ponto tem 3 dígitos depois, é separador de milhar
            partes = valor_limpo.split('.')
            if len(partes) > 2 or (len(partes) == 2 and len(partes[-1]) == 3):
                valor_limpo = valor_limpo.replace('.', '')
        
        return float(valor_limpo)
    except (ValueError, TypeError):
        print(f"⚠️ Erro ao converter valor: '{valor_str}' -> '{valor_limpo}'")
        return None

def listar_comprovantes_baixados():
    """Lista todos os comprovantes já baixados"""
    print("📁 Listando comprovantes baixados...")
    
    comprovantes_path = "Comprovantes"
    comprovantes = []
    
    if not os.path.exists(comprovantes_path):
        print(f"❌ Pasta {comprovantes_path} não encontrada")
        return []
    
    # Percorre todas as subpastas (fundos/datas)
    pdfs_processados = set()  # Para evitar processar o mesmo PDF duas vezes
    
    for root, dirs, files in os.walk(comprovantes_path):
        # Primeiro, processa arquivos TXT para extrair Payment IDs reais
        for file in files:
            if file.endswith('.txt') and 'URL_' in file:
                txt_path = os.path.join(root, file)
                payment_id_nome_arquivo = file.replace('URL_', '').replace('.txt', '')
                pdf_correspondente = os.path.join(root, f"comprovante_{payment_id_nome_arquivo}.pdf")
                
                # Se não existe PDF correspondente, pula
                if not os.path.exists(pdf_correspondente):
                    print(f"   ⚠️ PDF não encontrado para {payment_id_nome_arquivo}, pulando...")
                    continue
                
                # Extrai Payment ID real do arquivo TXT
                try:
                    with open(txt_path, 'r', encoding='utf-8') as f:
                        conteudo = f.read()
                        match = re.search(r'Payment ID:\s*([A-F0-9]+)', conteudo)
                        if match:
                            payment_id_real = match.group(1)
                            
                            file_info = {
                                "path": pdf_correspondente,
                                "filename": f"comprovante_{payment_id_nome_arquivo}.pdf",
                                "folder": root,
                                "valor": payment_id_real,  # Payment ID real como valor
                                "data": extrair_data_do_comprovante(pdf_correspondente),
                                "fonte": "txt_com_pdf"
                            }
                            
                            comprovantes.append(file_info)
                            pdfs_processados.add(pdf_correspondente)
                            print(f"   ✅ Payment ID extraído do TXT: {payment_id_real} -> {file_info['filename']}")
                except Exception as e:
                    print(f"   ❌ Erro ao ler {txt_path}: {e}")
        
        # Depois, processa PDFs órfãos (sem TXT correspondente)
        for file in files:
            if file.endswith('.pdf') and file.startswith('comprovante_'):
                pdf_path = os.path.join(root, file)
                
                # Pula se já foi processado via TXT
                if pdf_path in pdfs_processados:
                    continue
                
                # Extrai Payment ID do nome do arquivo PDF
                nome_base = os.path.splitext(file)[0]
                if 'comprovante_' in nome_base:
                    payment_id_do_nome = nome_base.replace('comprovante_', '')
                    
                    # Verifica se o Payment ID parece válido (hexadecimal, pelo menos 15 caracteres)
                    if len(payment_id_do_nome) >= 15 and re.match(r'^[A-F0-9&]+$', payment_id_do_nome):
                        file_info = {
                            "path": pdf_path,
                            "filename": file,
                            "folder": root,
                            "valor": payment_id_do_nome,  # Payment ID do nome do arquivo
                            "data": extrair_data_do_comprovante(pdf_path),
                            "fonte": "pdf_orfao"
                        }
                        
                        comprovantes.append(file_info)
                        print(f"   ✅ Payment ID extraído do nome: {payment_id_do_nome} -> {file}")
                    else:
                        print(f"   ⚠️ Payment ID inválido no arquivo: {file}")
    
    print(f"✅ Encontrados {len(comprovantes)} comprovantes com valor identificado")
    return comprovantes

def extrair_valor_do_comprovante(file_path):
    """Extrai valor do nome do arquivo, arquivo TXT correspondente ou do conteúdo do PDF"""
    filename = os.path.basename(file_path)
    diretorio = os.path.dirname(file_path)
    
    # Se for PDF, procura arquivo TXT correspondente com Payment ID
    if file_path.lower().endswith('.pdf'):
        # Extrai ID do nome do arquivo PDF
        nome_base = os.path.splitext(filename)[0]
        if 'comprovante_' in nome_base:
            payment_id = nome_base.replace('comprovante_', '')
            
            # Procura arquivo TXT com o Payment ID
            arquivo_txt = os.path.join(diretorio, f"URL_{payment_id}.txt")
            if os.path.exists(arquivo_txt):
                try:
                    with open(arquivo_txt, 'r', encoding='utf-8') as f:
                        conteudo = f.read()
                        # Extrai o Payment ID do arquivo TXT
                        match = re.search(r'Payment ID:\s*([A-F0-9]+)', conteudo)
                        if match:
                            payment_id_extraido = match.group(1)
                            print(f"   📄 {filename} -> Payment ID: {payment_id_extraido}")
                            return payment_id_extraido  # Retorna o Payment ID como string para matching
                except Exception as e:
                    print(f"   ❌ Erro ao ler {arquivo_txt}: {e}")
    
    # Padrões para extrair valor numérico do nome do arquivo
    patterns = [
        r'comprovante_[A-Z0-9]+_(\d+[.,]\d+)',  # comprovante_ID_VALOR
        r'comprovante_(\d+[.,]\d+)',  # comprovante_VALOR
        r'(\d+[.,]\d{2})\.pdf',  # VALOR.pdf
        r'(\d{1,3}(?:[.,]\d{3})*[.,]\d{2})',  # Formato monetário brasileiro
    ]
    
    for pattern in patterns:
        match = re.search(pattern, filename)
        if match:
            valor_str = match.group(1)
            valor_normalizado = normalizar_valor(valor_str)
            if valor_normalizado:
                print(f"   📄 {filename} -> R$ {valor_normalizado}")
                return valor_normalizado
    
    print(f"   ⚠️ Valor não identificado em: {filename}")
    return None

def extrair_data_do_comprovante(file_path):
    """Extrai data do nome do arquivo ou pasta"""
    # Procura data no caminho do arquivo
    patterns = [
        r'(\d{8})',  # YYYYMMDD
        r'(\d{4}-\d{2}-\d{2})',  # YYYY-MM-DD
        r'(\d{2}-\d{2}-\d{4})',  # DD-MM-YYYY
    ]
    
    full_path = file_path.replace('\\', '/')
    
    for pattern in patterns:
        match = re.search(pattern, full_path)
        if match:
            return match.group(1)
    
    return None

def fazer_match_comprovante_card(cards, comprovantes):
    """Faz o match entre comprovantes e cards baseado no valor ou Payment ID"""
    print("🔗 Fazendo match entre comprovantes e cards...")
    
    matches = []
    cards_sem_anexo = []
    
    # Processar TODOS os cards (mesmo com anexo da nota fiscal)
    # Objetivo: adicionar comprovante de pagamento junto com a nota fiscal
    for card in cards:
        card_data = extrair_dados_card(card)
        
        # Não pula mais cards com anexo - precisa anexar comprovante
        cards_sem_anexo.append(card_data)
        print(f"   📝 Processando card {card_data['id']} - {card_data['title']} (pode ter nota fiscal)")
            
    print(f"📊 Cards para processar: {len(cards_sem_anexo)}")
    
    print(f"📊 Cards para processar: {len(cards_sem_anexo)}")
    
    # Fazer matching por Payment ID
    for card_data in cards_sem_anexo:
        card_valor = normalizar_valor(card_data["valor"])
        card_titulo = str(card_data["title"]) if card_data["title"] else ""
        
        # Procura Payment ID no título do card
        payment_id_card = None
        match_payment = re.search(r'([A-F0-9]{23,})', card_titulo)
        if match_payment:
            payment_id_card = match_payment.group(1)
        
        print(f"   🔍 Card {card_data['id']}: Valor={card_valor}, Payment_ID={payment_id_card}, Título={card_titulo[:50]}...")
        
        # Procura comprovante correspondente
        melhor_match = None
        menor_diferenca = float('inf')
        
        for comprovante in comprovantes:
            comp_valor = comprovante["valor"]
            
            # Se o comprovante tem Payment ID e o card também, prioriza match por ID
            if isinstance(comp_valor, str) and payment_id_card and comp_valor == payment_id_card:
                melhor_match = comprovante
                menor_diferenca = 0
                print(f"   🎯 Match por Payment ID: {comp_valor}")
                break
            
            # Se ambos são valores numéricos, faz match por valor
            elif isinstance(comp_valor, (int, float)) and card_valor:
                diferenca = abs(card_valor - comp_valor)
                
                if diferenca < 0.01:  # Tolerância de 1 centavo
                    if diferenca < menor_diferenca:
                        menor_diferenca = diferenca
                        melhor_match = comprovante
        
        if melhor_match:
            match_info = {
                "card": card_data,
                "comprovante": melhor_match,
                "diferenca": menor_diferenca
            }
            
            if isinstance(melhor_match["valor"], str):
                match_info["tipo_match"] = "payment_id"
                match_info["payment_id"] = melhor_match["valor"]
                print(f"✅ Match por ID: Card {card_data['id']} - {card_data['title'][:30]}... ↔ {melhor_match['filename']} (ID: {melhor_match['valor']})")
            else:
                match_info["tipo_match"] = "valor"
                match_info["valor_card"] = card_valor
                match_info["valor_comprovante"] = melhor_match["valor"]
                print(f"✅ Match por valor: Card {card_data['id']} - {card_data['title'][:30]}... - R$ {card_valor} ↔ {melhor_match['filename']}")
            
            matches.append(match_info)
            
            # Remove comprovante da lista para evitar duplicatas
            comprovantes.remove(melhor_match)
        else:
            print(f"   ❌ Sem match: Card {card_data['id']} - R$ {card_valor} - ID: {payment_id_card}")
    
    print(f"🎯 Total de matches encontrados: {len(matches)}")
    return matches

def fazer_upload_arquivo_pipefy(file_path):
    """Faz upload do arquivo para o Pipefy"""
    print(f"📤 Fazendo upload de {os.path.basename(file_path)}...")
    
    try:
        with open(file_path, 'rb') as file:
            files = {
                'query': (None, 'mutation { createPresignedUrl(input: {fileName: "' + os.path.basename(file_path) + '", organizationId: "300376769"}) { url } }'),
                'file': (os.path.basename(file_path), file, 'application/pdf')
            }
            
            response = requests.post(
                PIPEFY_API_URL,
                files=files,
                headers={'Authorization': f'Bearer {PIPEFY_API_TOKEN}'}
            )
            
            if response.status_code == 200:
                data = response.json()
                if 'data' in data and 'createPresignedUrl' in data['data']:
                    url = data['data']['createPresignedUrl']['url']
                    print(f"   ✅ Upload realizado: {url}")
                    return url
                else:
                    print(f"   ❌ Erro na resposta: {data}")
                    return None
            else:
                print(f"   ❌ Erro HTTP {response.status_code}: {response.text}")
                return None
                
    except Exception as e:
        print(f"   ❌ Erro no upload: {e}")
        return None

def anexar_ao_card(card_id, file_url):
    """Anexa o comprovante ao campo ESPECÍFICO de comprovante (não substitui nota fiscal)"""
    print(f"📎 Anexando COMPROVANTE ao card {card_id}...")
    
    try:
        # 1. Buscar ID do campo de anexo
        query_fields = """
        query GetCard($cardId: ID!) {
            card(id: $cardId) {
                current_phase {
                    fields {
                        id
                        label
                        type
                    }
                }
            }
        }
        """
        
        response = requests.post(
            PIPEFY_API_URL,
            headers=headers,
            json={"query": query_fields, "variables": {"cardId": card_id}}
        )
        
        if response.status_code != 200:
            print(f"   ❌ Erro ao buscar campos: {response.text}")
            return False
        
        data = response.json()
        fields = data['data']['card']['current_phase']['fields']
        
        # Encontrar campo específico do COMPROVANTE (não nota fiscal)
        field_anexo_comprovante_id = None
        field_sim_nao_id = None
        
        for field in fields:
            label = field['label'].lower()
            if field['type'] == 'attachment' and ('comprovante' in label or 'pagamento' in label):
                field_anexo_comprovante_id = field['id']
                print(f"   📎 Campo COMPROVANTE encontrado: {field['label']} (ID: {field_anexo_comprovante_id})")
            elif 'comprovante anexado corretamente' in label:
                field_sim_nao_id = field['id']
                print(f"   ✅ Campo sim/não encontrado: {field['label']} (ID: {field_sim_nao_id})")
        
        if not field_anexo_comprovante_id:
            print("   ❌ Campo específico de comprovante não encontrado")
            return False
        
        # 2. Anexar arquivo
        from urllib.parse import urlparse
        parsed_url = urlparse(file_url)
        caminho_relativo = parsed_url.path.lstrip('/')
        
        mutation_anexo = """
        mutation UpdateCardField($cardId: ID!, $fieldId: ID!, $value: [UndefinedInput]) {
            updateCardField(
                input: {
                    card_id: $cardId
                    field_id: $fieldId
                    new_value: $value
                }
            ) {
                success
            }
        }
        """
        
        variables_anexo = {
            "cardId": card_id,
            "fieldId": field_anexo_id,
            "value": [caminho_relativo]
        }
        
        response_anexo = requests.post(
            PIPEFY_API_URL,
            headers=headers,
            json={"query": mutation_anexo, "variables": variables_anexo}
        )
        
        if response_anexo.status_code != 200:
            print(f"   ❌ Erro ao anexar: {response_anexo.text}")
            return False
        
        result_anexo = response_anexo.json()
        if 'errors' in result_anexo:
            print(f"   ❌ Erro GraphQL anexo: {result_anexo['errors']}")
            return False
        
        if result_anexo.get('data', {}).get('updateCardField', {}).get('success'):
            print("   ✅ Arquivo anexado com sucesso")
            
            # 3. Marcar como 'Sim' se campo existe
            if field_sim_nao_id:
                variables_sim = {
                    "cardId": card_id,
                    "fieldId": field_sim_nao_id,
                    "value": ["Sim"]
                }
                
                response_sim = requests.post(
                    PIPEFY_API_URL,
                    headers=headers,
                    json={"query": mutation_anexo, "variables": variables_sim}
                )
                
                if response_sim.status_code == 200:
                    result_sim = response_sim.json()
                    if not 'errors' in result_sim and result_sim.get('data', {}).get('updateCardField', {}).get('success'):
                        print("   ✅ Campo 'Sim' marcado com sucesso")
                    else:
                        print(f"   ⚠️ Erro ao marcar 'Sim': {result_sim}")
                else:
                    print(f"   ⚠️ Erro HTTP ao marcar 'Sim': {response_sim.text}")
            else:
                print("   ⚠️ Campo 'Sim/Não' não encontrado")
            
            # COMENTADO: Mover para fase "Solicitação Paga"
            # print("   🔄 Movendo para fase 'Solicitação Paga'...")
            # mover_para_solicitacao_paga(card_id)
            
            return True
        else:
            print(f"   ❌ Falha ao anexar arquivo")
            return False
            
    except Exception as e:
        print(f"   ❌ Erro ao anexar ao card: {e}")
        return False

def processar_matches(matches):
    """Processa todos os matches encontrados"""
    print(f"\n🚀 Processando {len(matches)} matches...")
    
    sucessos = 0
    erros = 0
    
    for i, match in enumerate(matches, 1):
        print(f"\n--- Match {i}/{len(matches)} ---")
        card = match["card"]
        comprovante = match["comprovante"]
        
        print(f"Card: {card['id']} - {card['title']}")
        print(f"Valor Card: R$ {match['valor_card']}")
        print(f"Valor Comprovante: R$ {match['valor_comprovante']}")
        print(f"Arquivo: {comprovante['filename']}")
        print(f"Path: {comprovante['path']}")
        
        # Upload do arquivo
        file_url = fazer_upload_arquivo_pipefy(comprovante["path"])
        
        if file_url:
            # Anexar ao card
            if anexar_ao_card(card["id"], file_url):
                sucessos += 1
                print("✅ Processado com sucesso!")
            else:
                erros += 1
                print("❌ Erro ao anexar ao card")
        else:
            erros += 1
            print("❌ Erro no upload")
        
        # Pequena pausa para não sobrecarregar a API
        import time
        time.sleep(1)
    
    print(f"\n📊 RESUMO FINAL:")
    print(f"✅ Sucessos: {sucessos}")
    print(f"❌ Erros: {erros}")
    print(f"📈 Total processado: {sucessos + erros}")

def main():
    """Função principal"""
    print("🎯 Iniciando processo de anexar comprovantes existentes aos cards...")
    print("⚠️  IMPORTANTE: Não irá mover cards de fase (movimentação comentada)")
    print("="*80)
    
    # 1. Buscar cards
    cards = buscar_cards_aguardando()
    if not cards:
        print("❌ Nenhum card encontrado")
        return
    
    # 2. Listar comprovantes
    comprovantes = listar_comprovantes_baixados()
    if not comprovantes:
        print("❌ Nenhum comprovante encontrado")
        return
    
    # 3. Fazer matches
    matches = fazer_match_comprovante_card(cards, comprovantes)
    if not matches:
        print("❌ Nenhum match encontrado")
        return
    
    # 4. Mostrar resumo e confirmar
    print(f"\n📋 RESUMO:")
    print(f"   🔍 Cards encontrados: {len(cards)}")
    print(f"   📄 Comprovantes encontrados: {len(comprovantes)}")
    print(f"   🎯 Matches encontrados: {len(matches)}")
    print(f"\n⚠️  Serão processados {len(matches)} anexações.")
    print(f"⚠️  MOVIMENTO DE FASE ESTÁ DESABILITADO")
    
    continuar = input("\nDeseja continuar? (s/N): ").lower().strip()
    
    if continuar == 's' or continuar == 'sim':
        processar_matches(matches)
    else:
        print("❌ Operação cancelada pelo usuário")

if __name__ == "__main__":
    main()