"""
Script para listar comprovantes disponíveis no Santander
Baseado em buscar_comprovantes_santander.py, mas apenas lista sem gerar PDFs
"""

import json
import sys
import codecs
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any
import logging

# Configurar encoding UTF-8 para Windows
if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

from buscar_comprovantes_santander import SantanderComprovantes
from credenciais_bancos import SantanderAuth, SANTANDER_FUNDOS

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def formatar_cnpj(cnpj: str) -> str:
    """Formata CNPJ para exibição"""
    cnpj_numeros = ''.join(filter(str.isdigit, cnpj))
    if len(cnpj_numeros) == 14:
        return f"{cnpj_numeros[:2]}.{cnpj_numeros[2:5]}.{cnpj_numeros[5:8]}/{cnpj_numeros[8:12]}-{cnpj_numeros[12:]}"
    return cnpj


def listar_comprovantes_fundo(fundo_id: str) -> List[Dict[str, Any]]:
    """
    Lista comprovantes de um fundo específico do dia atual
    
    Args:
        fundo_id: ID do fundo no dicionário SANTANDER_FUNDOS
    
    Returns:
        Lista de comprovantes com CNPJ do fundo e valor
    """
    try:
        # Criar autenticação para o fundo
        auth = SantanderAuth.criar_por_fundo(fundo_id)
        
        # Criar cliente de comprovantes
        cliente = SantanderComprovantes(auth)
        
        # Data de hoje
        hoje = datetime.now().date().strftime("%Y-%m-%d")
        
        # Listar comprovantes
        logger.info(f"\n{'='*80}")
        logger.info(f"FUNDO: {auth.fundo_nome}")
        logger.info(f"CNPJ: {formatar_cnpj(auth.fundo_cnpj)}")
        logger.info(f"Data: {hoje}")
        logger.info(f"{'='*80}")
        
        resultado = cliente.listar_comprovantes(hoje, hoje)
        comprovantes = resultado.get('paymentsReceipts', [])
        
        # Processar e formatar comprovantes - apenas CNPJ e valor
        comprovantes_formatados = []
        for comprovante in comprovantes:
            payment = comprovante.get('payment', {})
            
            # Valor
            amount_info = payment.get('paymentAmountInfo', {})
            amount = amount_info.get('direct', {}).get('amount', 0)
            try:
                amount_float = float(amount) if amount else 0.0
            except (ValueError, TypeError):
                amount_float = 0.0
            
            # Beneficiário
            beneficiario = payment.get('payee', {}).get('name', '')
            
            comprovante_formatado = {
                'cnpj_fundo': auth.fundo_cnpj,
                'valor': amount_float,
                'beneficiario': beneficiario
            }
            
            comprovantes_formatados.append(comprovante_formatado)
        
        logger.info(f"✅ {len(comprovantes_formatados)} comprovante(s) encontrado(s)")
        
        return comprovantes_formatados
        
    except Exception as e:
        logger.error(f"❌ Erro ao listar comprovantes do fundo {fundo_id}: {e}")
        return []


def listar_comprovantes_todos_fundos(fundos_especificos: List[str] = None) -> List[Dict[str, Any]]:
    """
    Lista comprovantes de todos os fundos configurados (do dia atual)
    
    Args:
        fundos_especificos: Lista opcional de IDs de fundos específicos para consultar
    
    Returns:
        Lista de comprovantes com CNPJ e valor
    """
    comprovantes_todos = []
    
    # Determinar quais fundos processar
    fundos_para_processar = fundos_especificos if fundos_especificos else list(SANTANDER_FUNDOS.keys())
    
    hoje = datetime.now().date().strftime("%Y-%m-%d")
    logger.info(f"\n🔍 Iniciando listagem de comprovantes para {len(fundos_para_processar)} fundo(s)")
    logger.info(f"📅 Data: {hoje}\n")
    
    for fundo_id in fundos_para_processar:
        if fundo_id not in SANTANDER_FUNDOS:
            logger.warning(f"⚠️  Fundo {fundo_id} não encontrado na configuração")
            continue
        
        comprovantes = listar_comprovantes_fundo(fundo_id)
        comprovantes_todos.extend(comprovantes)
    
    # Resumo final
    logger.info(f"\n{'='*80}")
    logger.info(f"📊 RESUMO DA LISTAGEM")
    logger.info(f"{'='*80}")
    logger.info(f"Fundos consultados: {len(fundos_para_processar)}")
    logger.info(f"Total de comprovantes: {len(comprovantes_todos)}")
    logger.info(f"{'='*80}\n")
    
    return comprovantes_todos


def salvar_listagem_json(comprovantes: List[Dict[str, Any]], arquivo: str = None):
    """
    Salva a listagem de comprovantes em arquivo JSON
    
    Args:
        comprovantes: Lista de comprovantes
        arquivo: Nome do arquivo (opcional, gera automático se não informado)
    """
    if arquivo is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        arquivo = f"listagem_comprovantes_{timestamp}.json"
    
    arquivo_path = Path(__file__).parent / arquivo
    
    with open(arquivo_path, 'w', encoding='utf-8') as f:
        json.dump(comprovantes, f, ensure_ascii=False, indent=2)
    
    logger.info(f"💾 Listagem salva em: {arquivo_path.absolute()}")


def exibir_resumo(comprovantes: List[Dict[str, Any]]):
    """
    Exibe resumo dos comprovantes
    
    Args:
        comprovantes: Lista de comprovantes
    """
    print("\n" + "="*80)
    print("📋 LISTAGEM DE COMPROVANTES DO DIA")
    print("="*80)
    
    if not comprovantes:
        print("\n⚠️  Nenhum comprovante encontrado")
        print("\n" + "="*80 + "\n")
        return
    
    # Agrupar por CNPJ
    por_cnpj = {}
    for comp in comprovantes:
        cnpj = comp['cnpj_fundo']
        if cnpj not in por_cnpj:
            por_cnpj[cnpj] = []
        por_cnpj[cnpj].append(comp)
    
    # Exibir
    for cnpj, lista in por_cnpj.items():
        total_valor = sum(c['valor'] for c in lista)
        
        print(f"\n💼 CNPJ: {formatar_cnpj(cnpj)}")
        print(f"   Comprovantes: {len(lista)}")
        print(f"   Valor total: R$ {total_valor:,.2f}")
        
        # Lista os valores
        for idx, comp in enumerate(lista, 1):
            print(f"   [{idx}] R$ {comp['valor']:,.2f}")
    
    print("\n" + "="*80 + "\n")


def main():
    """Função principal"""
    # Parser de argumentos
    parser = argparse.ArgumentParser(description='Listar comprovantes Santander')
    parser.add_argument(
        '--dias',
        type=int,
        default=1,
        help='Dias retroativos para buscar (padrão: 1)'
    )
    
    args = parser.parse_args()
    
    # Buscar apenas o dia atual (não retroativo)
    data_fim = datetime.now().date()
    data_inicio = data_fim  # Mesmo dia - apenas hoje
    
    logger.info(f"Buscando comprovantes de {data_inicio} até {data_fim} (somente dia atual)")
    
    # Listar comprovantes de TODOS os fundos
    comprovantes = listar_comprovantes_todos_fundos()
    
    # Exibir resumo
    exibir_resumo(comprovantes)
    
    # Salvar em JSON
    salvar_listagem_json(comprovantes)


if __name__ == "__main__":
    main()
