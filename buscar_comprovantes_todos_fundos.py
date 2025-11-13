"""
Script para buscar comprovantes de todos os fundos Santander configurados
"""

import logging
from datetime import date, timedelta
from credenciais_bancos import criar_auth_para_todos_fundos, listar_fundos_configurados
from buscar_comprovantes_santander import SantanderComprovantes

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def buscar_comprovantes_todos_fundos(dias: int = 1):
    """
    Busca comprovantes de todos os fundos configurados
    
    Args:
        dias: Número de dias retroativos para buscar (padrão: 1 - apenas hoje)
    """
    logger.info("="*80)
    logger.info("BUSCA DE COMPROVANTES - TODOS OS FUNDOS SANTANDER")
    logger.info("="*80)
    
    # Listar fundos disponíveis
    fundos = listar_fundos_configurados()
    
    logger.info(f"\nTotal de fundos cadastrados: {len(fundos)}")
    fundos_configurados = [f for f in fundos if f["configurado"]]
    logger.info(f"Fundos com credenciais: {len(fundos_configurados)}")
    
    if not fundos_configurados:
        logger.error("❌ Nenhum fundo configurado com credenciais!")
        logger.info("\nEdite o arquivo credenciais_bancos.py e adicione:")
        logger.info("  - client_id")
        logger.info("  - client_secret")
        logger.info("para cada fundo")
        return
    
    logger.info("\n" + "="*80)
    logger.info("FUNDOS CONFIGURADOS:")
    for f in fundos_configurados:
        logger.info(f"  ✅ {f['id']}: {f['nome']}")
    logger.info("="*80)
    
    # Criar clientes de autenticação para todos os fundos
    logger.info("\n🔐 Criando clientes de autenticação...")
    auth_clients = criar_auth_para_todos_fundos()
    
    if not auth_clients:
        logger.error("❌ Não foi possível criar nenhum cliente de autenticação")
        return
    
    # Processar cada fundo
    resultados_geral = {}
    
    for fundo_id, auth in auth_clients.items():
        logger.info("\n" + "="*80)
        logger.info(f"PROCESSANDO FUNDO: {fundo_id}")
        logger.info(f"Nome: {auth.fundo_nome}")
        logger.info(f"CNPJ: {auth.fundo_cnpj}")
        logger.info("="*80)
        
        try:
            # Criar cliente de comprovantes
            cliente = SantanderComprovantes(auth)
            
            # Buscar comprovantes do período
            resultados = cliente.buscar_comprovantes_periodo(
                dias=dias,
                auto_baixar=True
            )
            
            resultados_geral[fundo_id] = {
                "sucesso": True,
                "total": len(resultados),
                "comprovantes": resultados
            }
            
            logger.info(f"\n✅ {fundo_id}: {len(resultados)} comprovante(s) processado(s)")
            
        except Exception as e:
            logger.error(f"\n❌ Erro ao processar {fundo_id}: {e}")
            resultados_geral[fundo_id] = {
                "sucesso": False,
                "erro": str(e),
                "total": 0
            }
    
    # Resumo final
    logger.info("\n" + "="*80)
    logger.info("RESUMO FINAL")
    logger.info("="*80)
    
    total_comprovantes = 0
    fundos_sucesso = 0
    fundos_erro = 0
    
    for fundo_id, resultado in resultados_geral.items():
        if resultado["sucesso"]:
            fundos_sucesso += 1
            total_comprovantes += resultado["total"]
            logger.info(f"✅ {fundo_id}: {resultado['total']} comprovante(s)")
        else:
            fundos_erro += 1
            logger.error(f"❌ {fundo_id}: {resultado.get('erro', 'Erro desconhecido')}")
    
    logger.info("\n" + "="*80)
    logger.info(f"Total de comprovantes baixados: {total_comprovantes}")
    logger.info(f"Fundos processados com sucesso: {fundos_sucesso}/{len(auth_clients)}")
    if fundos_erro > 0:
        logger.info(f"Fundos com erro: {fundos_erro}")
    logger.info("="*80)
    
    return resultados_geral


if __name__ == "__main__":
    import sys
    
    # Número de dias para buscar (padrão: 1 dia = hoje)
    dias = 1
    if len(sys.argv) > 1:
        try:
            dias = int(sys.argv[1])
        except ValueError:
            logger.error("Uso: python buscar_comprovantes_todos_fundos.py [dias]")
            logger.error("Exemplo: python buscar_comprovantes_todos_fundos.py 7")
            sys.exit(1)
    
    logger.info(f"Buscando comprovantes dos últimos {dias} dia(s)")
    buscar_comprovantes_todos_fundos(dias)
