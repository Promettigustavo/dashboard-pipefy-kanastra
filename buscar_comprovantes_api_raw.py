"""
Busca Comprovantes Santander - Versão Simples
Retorna a resposta da API sem tratamento
"""

import requests
from datetime import datetime, timedelta
import json

# Importar credenciais
try:
    from credenciais_bancos import SANTANDER_FUNDOS
except ImportError:
    print("❌ Erro: arquivo credenciais_bancos.py não encontrado")
    exit(1)


def obter_token_oauth2(client_id, client_secret, cert_path, key_path):
    """
    Obtém token OAuth2 da API Santander
    """
    url = "https://trust-open.api.santander.com.br/auth/oauth/v2/token"
    
    headers = {
        "X-Application-Key": client_id,
        "Content-Type": "application/x-www-form-urlencoded"
    }
    
    data = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret
    }
    
    try:
        response = requests.post(
            url,
            headers=headers,
            data=data,
            cert=(cert_path, key_path),
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"❌ Erro ao obter token: {e}")
        return None


def buscar_comprovantes(token, client_id, cert_path, key_path, data_inicial, data_final):
    """
    Busca comprovantes na API Santander
    
    Args:
        token: Token OAuth2
        client_id: Client ID da aplicação
        cert_path: Caminho do certificado
        key_path: Caminho da chave privada
        data_inicial: Data inicial (datetime)
        data_final: Data final (datetime)
    
    Returns:
        dict: Resposta da API sem tratamento
    """
    url = "https://trust-open.api.santander.com.br/consult_payment_receipts/v1/payment_receipts"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Application-Key": client_id,
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    params = {
        "start_date": data_inicial.strftime("%Y-%m-%d"),
        "end_date": data_final.strftime("%Y-%m-%d")
    }
    
    try:
        response = requests.get(
            url,
            headers=headers,
            params=params,
            cert=(cert_path, key_path),
            verify=True,
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"❌ Erro ao buscar comprovantes: {e}")
        return None


def main():
    """
    Função principal
    """
    print("=" * 80)
    print("BUSCA DE COMPROVANTES SANTANDER - VERSÃO SIMPLES")
    print("=" * 80)
    
    # Selecionar fundo
    print("\n📋 Fundos disponíveis:")
    fundos_lista = list(SANTANDER_FUNDOS.keys())
    for i, fundo in enumerate(fundos_lista, 1):
        print(f"   {i}. {fundo}")
    
    escolha = int(input("\nEscolha o número do fundo: ")) - 1
    fundo_id = fundos_lista[escolha]
    fundo = SANTANDER_FUNDOS[fundo_id]
    
    print(f"\n✅ Fundo selecionado: {fundo_id}")
    print(f"   Nome: {fundo['nome']}")
    print(f"   CNPJ: {fundo['cnpj']}")
    
    # Definir período (últimos 7 dias por padrão)
    data_final = datetime.now()
    data_inicial = data_final - timedelta(days=7)
    
    print(f"\n📅 Período: {data_inicial.strftime('%d/%m/%Y')} a {data_final.strftime('%d/%m/%Y')}")
    
    # Obter token
    print("\n🔑 Obtendo token OAuth2...")
    token_data = obter_token_oauth2(
        client_id=fundo['client_id'],
        client_secret=fundo['client_secret'],
        cert_path=fundo['cert_path'],
        key_path=fundo['key_path']
    )
    
    if not token_data:
        print("❌ Falha ao obter token")
        return
    
    token = token_data['access_token']
    print(f"✅ Token obtido (expira em {token_data.get('expires_in', 'N/A')}s)")
    
    # Buscar comprovantes
    print("\n📊 Buscando comprovantes...")
    resposta_api = buscar_comprovantes(
        token, 
        fundo['client_id'],
        fundo['cert_path'],
        fundo['key_path'],
        data_inicial, 
        data_final
    )
    
    if not resposta_api:
        print("❌ Falha ao buscar comprovantes")
        return
    
    # Extrair e analisar dados dos pagamentos
    payments_receipts = resposta_api.get('paymentsReceipts', [])
    
    print("\n" + "=" * 80)
    print(f"ANÁLISE DOS COMPROVANTES - {len(payments_receipts)} PAGAMENTO(S) ENCONTRADO(S)")
    print("=" * 80)
    
    for idx, receipt in enumerate(payments_receipts, 1):
        payment = receipt.get('payment', {})
        
        print(f"\n{'─' * 80}")
        print(f"PAGAMENTO #{idx}")
        print(f"{'─' * 80}")
        
        # Dados principais
        print(f"\n📋 IDENTIFICAÇÃO:")
        print(f"   Payment ID: {payment.get('paymentId', 'N/A')}")
        print(f"   Commitment Number: {payment.get('commitmentNumber', 'N/A')}")
        print(f"   Data/Hora: {payment.get('requestValueDate', 'N/A')}")
        
        # Pagador (Payer)
        payer = payment.get('payer', {})
        payer_person = payer.get('person', {})
        payer_doc = payer_person.get('document', {})
        print(f"\n💰 PAGADOR:")
        print(f"   Tipo Documento: {payer_doc.get('documentTypeCode', 'N/A')}")
        print(f"   CNPJ/CPF: {payer_doc.get('documentNumber', 'N/A')}")
        
        # Beneficiário (Payee)
        payee = payment.get('payee', {})
        print(f"\n👤 BENEFICIÁRIO:")
        print(f"   Nome: {payee.get('name', 'N/A')}")
        
        # Valor
        amount_info = payment.get('paymentAmountInfo', {})
        direct = amount_info.get('direct', {})
        print(f"\n💵 VALOR:")
        print(f"   Valor Direto: R$ {direct.get('amount', 'N/A')}")
        
        # Categoria e Canal
        category = receipt.get('category', {})
        channel = receipt.get('channel', {})
        print(f"\n🏷️ CLASSIFICAÇÃO:")
        print(f"   Categoria: {category.get('code', 'N/A')}")
        print(f"   Canal: {channel.get('code', 'N/A')}")
        
        # Dados completos (JSON)
        print(f"\n📄 DADOS COMPLETOS (JSON):")
        print(json.dumps(receipt, indent=2, ensure_ascii=False))
    
    # Mostrar resposta completa da API
    print("\n" + "=" * 80)
    print("RESPOSTA COMPLETA DA API (RAW)")
    print("=" * 80)
    print(json.dumps(resposta_api, indent=2, ensure_ascii=False))
    
    # Salvar em arquivo
    filename = f"comprovantes_api_raw_{fundo_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(resposta_api, f, indent=2, ensure_ascii=False)
    
    print("\n" + "=" * 80)
    print(f"✅ Resposta salva em: {filename}")
    print("=" * 80)


if __name__ == "__main__":
    main()
