"""
Script para buscar comprovantes do fundo AUTO XI FIDC no Santander
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
import json

# Importar o módulo de credenciais
from credenciais_bancos import SantanderAuth
from buscar_comprovantes_santander import SantanderComprovantes

def listar_comprovantes_auto_xi():
    """
    Lista os comprovantes disponíveis do fundo AUTO XI FIDC
    """
    
    print("=" * 80)
    print("LISTAGEM DE COMPROVANTES - AUTO XI FIDC")
    print("=" * 80)
    
    fundo_id = "AUTO XI FIDC"
    
    try:
        # Criar instância de autenticação para o fundo específico
        print(f"\n🔐 Autenticando fundo: {fundo_id}")
        auth = SantanderAuth.criar_por_fundo(fundo_id, ambiente="producao")
        
        # Verificar se o token é válido, senão obter novo
        if not auth._is_token_valid():
            print("⏳ Token expirado, obtendo novo token...")
            auth.obter_token_acesso()
        else:
            print("✅ Token válido encontrado")
        
        # Criar instância do buscador de comprovantes
        print("\n🔍 Buscando comprovantes disponíveis...")
        comprovantes = SantanderComprovantes(auth)
        
        # Definir período de busca (últimos 30 dias - limite da API Santander)
        data_fim = datetime.now()
        data_inicio = data_fim - timedelta(days=30)
        
        print(f"\n📅 Período: {data_inicio.strftime('%d/%m/%Y')} até {data_fim.strftime('%d/%m/%Y')}")
        print(f"🏦 Fundo: {auth.fundo_nome}")
        print(f"📋 CNPJ: {auth.fundo_cnpj}")
        print("\n" + "=" * 80)
        
        # Buscar comprovantes
        resultado = comprovantes.listar_comprovantes(
            data_inicio=data_inicio.strftime("%Y-%m-%d"),
            data_fim=data_fim.strftime("%Y-%m-%d")
        )
        
        if not resultado:
            print("\n❌ Nenhum comprovante encontrado no período")
            return
        
        # Exibir resumo
        print(f"\n✅ Comprovantes disponíveis!")
        print("\n" + "=" * 80)
        print(f"📊 RESUMO: API retornou dados dos comprovantes")
        print("=" * 80)
        
        # Salvar em arquivo JSON
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        arquivo_json = f"comprovantes_auto_xi_{timestamp}.json"
        
        try:
            with open(arquivo_json, 'w', encoding='utf-8') as f:
                json.dump(resultado, f, indent=2, ensure_ascii=False)
            print(f"\n💾 Comprovantes salvos em: {arquivo_json}")
            print(f"📝 Verifique o arquivo JSON para ver os detalhes completos")
        except Exception as e:
            print(f"\n⚠️ Erro ao salvar JSON: {e}")
        
        print("\n" + "=" * 80)
        print(f"✅ PROCESSO CONCLUÍDO")
        print(f"📄 Arquivo salvo: {arquivo_json}")
        print("=" * 80)
        
        return resultado
        
    except ValueError as e:
        print(f"\n❌ Erro de configuração: {e}")
        print("\nVerifique se o fundo 'AUTO XI FIDC' está configurado com credenciais válidas")
        return None
        
    except Exception as e:
        print(f"\n❌ Erro ao buscar comprovantes: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    comprovantes = listar_comprovantes_auto_xi()
    
    if comprovantes:
        print(f"\n✅ Comprovantes disponíveis do fundo AUTO XI FIDC")
    else:
        print("\n⚠️ Nenhum comprovante foi retornado")
