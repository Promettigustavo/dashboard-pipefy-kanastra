"""
Módulo de Amortização - Versão Nova
Processa planilha Excel com duas abas e gera arquivo de pagamento formatado

ABA 1: Dados principais (a definir)
ABA 2: Dados de movimentação com colunas:
    - NomeCli: Nome do cliente
    - VlLiq: Valor líquido
    - CPFCNPJ: CPF/CNPJ do cliente
    - Outras colunas disponíveis conforme arquivo
"""

from pathlib import Path
import pandas as pd
from typing import Dict, List
import re


# ============================================================================
# COLUNAS DE SAÍDA (LAYOUT FINAL)
# ============================================================================

COLUNAS_SAIDA = [
    'Forma de iniciação',
    'Número do pagamento',
    'Chave Pix',
    'ISPB',
    'Banco',
    'Agência',
    'Conta',
    'Tipo de conta',
    'Nome do fornecedor',
    'Tipo documento',
    'Documento',
    'Valor a pagar',
    'Data de pagamento',
    'QR code (copia e cola)',
    'Informação ao recebedor'
]


# ============================================================================
# MAPEAMENTO DE COLUNAS ABA 2
# ============================================================================

# Colunas esperadas da aba 2 (podem não estar todas presentes)
COLUNAS_ABA2_ESPERADAS = {
    'nome': ['NomeCli', 'Cliente', 'Nome'],
    'documento': ['CPFCNPJ', 'CPF', 'CNPJ', 'Documento'],
    'valor': ['VlLiq', 'Valor', 'ValorLiq', 'TotValLiq']
}


# ============================================================================
# FUNÇÕES AUXILIARES
# ============================================================================

def _normalizar_coluna(col: str) -> str:
    """Normaliza nome de coluna para comparação"""
    return re.sub(r'[^a-z0-9]', '', str(col).lower().strip())


def _encontrar_coluna(df: pd.DataFrame, candidatos: List[str]) -> str:
    """
    Encontra coluna no DataFrame a partir de lista de candidatos
    Retorna nome da coluna encontrada ou None
    """
    colunas_df = {_normalizar_coluna(c): c for c in df.columns}
    
    for candidato in candidatos:
        candidato_norm = _normalizar_coluna(candidato)
        if candidato_norm in colunas_df:
            return colunas_df[candidato_norm]
    
    return None


def _apenas_digitos(texto: str) -> str:
    """Remove tudo que não é dígito"""
    return re.sub(r'\D', '', str(texto))


def _identificar_tipo_documento(documento: str) -> str:
    """
    Identifica tipo de documento (PF ou PJ) pelo tamanho
    CPF = 11 dígitos = PF
    CNPJ = 14 dígitos = PJ
    """
    doc_limpo = _apenas_digitos(documento)
    
    if len(doc_limpo) == 11:
        return 'PF'
    elif len(doc_limpo) == 14:
        return 'PJ'
    else:
        return ''


def _formatar_valor(valor) -> str:
    """
    Formata valor com ponto como separador decimal
    Exemplo: 1234.56
    Evita notação científica para valores grandes
    """
    try:
        # Converter para float evitando notação científica
        if isinstance(valor, str):
            # Remover formatação se houver
            valor = valor.replace('.', '').replace(',', '.')
        
        valor_float = float(valor)
        
        # Usar formato fixo para evitar notação científica
        # Para valores grandes, garantir precisão de 2 casas decimais
        return f"{valor_float:.2f}"
    except:
        return "0.00"


def _extrair_dados_aba1(df: pd.DataFrame) -> Dict[str, Dict]:
    """
    Extrai dados bancários da aba 1 (colunas F em diante)
    
    Estrutura esperada:
    - Coluna F, G, H... = cada cliente
    - Linha 3 (índice 2): Nome do cliente
    - Linha 4 (índice 3): CPF/CNPJ
    - Linha 5 (índice 4): Banco
    - Linha 6 (índice 5): Agência
    - Linha 7 (índice 6): Conta corrente
    - Linha 8 (índice 7): Chave PIX
    
    Returns:
        Dict onde a chave é o CPF/CNPJ limpo e o valor é um dict com banco, agencia, conta, pix
    """
    dados_bancarios = {}
    
    # Colunas da F em diante (índice 5 em diante, pois A=0, B=1, C=2, D=3, E=4, F=5)
    colunas_clientes = df.columns[5:]  # A partir da coluna F
    
    print(f"   📋 Processando {len(colunas_clientes)} colunas de clientes (F em diante)")
    
    for col in colunas_clientes:
        try:
            # Extrair dados das linhas específicas
            # Linha 3 = índice 2 (nome)
            # Linha 4 = índice 3 (CPF/CNPJ)
            # Linha 5 = índice 4 (Banco)
            # Linha 6 = índice 5 (Agência)
            # Linha 7 = índice 6 (Conta)
            # Linha 8 = índice 7 (Chave PIX)
            
            if len(df) < 8:  # Precisa ter pelo menos 8 linhas
                continue
            
            nome = str(df.iloc[2][col]).strip() if pd.notna(df.iloc[2][col]) else ''
            cpf_cnpj_raw = str(df.iloc[3][col]).strip() if pd.notna(df.iloc[3][col]) else ''
            banco_raw = str(df.iloc[4][col]).strip() if pd.notna(df.iloc[4][col]) else ''
            agencia_raw = str(df.iloc[5][col]).strip() if pd.notna(df.iloc[5][col]) else ''
            conta_raw = str(df.iloc[6][col]).strip() if pd.notna(df.iloc[6][col]) else ''
            chave_pix = str(df.iloc[7][col]).strip() if pd.notna(df.iloc[7][col]) else ''
            
            # Extrair apenas dígitos das linhas 4, 5, 6 e 7
            cpf_cnpj_limpo = _apenas_digitos(cpf_cnpj_raw)
            banco_limpo = _apenas_digitos(banco_raw)
            agencia_limpa = _apenas_digitos(agencia_raw)
            conta_limpa = _apenas_digitos(conta_raw)
            
            # Se tem documento válido, adicionar
            if cpf_cnpj_limpo and len(cpf_cnpj_limpo) in [11, 14]:
                dados_bancarios[cpf_cnpj_limpo] = {
                    'nome': nome,
                    'banco': banco_limpo,
                    'agencia': agencia_limpa,
                    'conta': conta_limpa,
                    'pix': chave_pix
                }
                pix_info = f", PIX={chave_pix[:20]}..." if chave_pix else ""
                print(f"      ✅ {cpf_cnpj_limpo}: Banco={banco_limpo}, Ag={agencia_limpa}, CC={conta_limpa}{pix_info}")
        
        except Exception as e:
            print(f"      ⚠️ Erro ao processar coluna {col}: {e}")
            continue
    
    print(f"   📊 Total: {len(dados_bancarios)} clientes com dados bancários")
    
    return dados_bancarios


def _extrair_dados_aba2(df: pd.DataFrame) -> pd.DataFrame:
    """
    Extrai dados relevantes da aba 2 e agrupa por CPF/CNPJ somando valores
    """
    dados = pd.DataFrame()
    
    # Encontrar colunas importantes
    col_nome = _encontrar_coluna(df, COLUNAS_ABA2_ESPERADAS['nome'])
    col_doc = _encontrar_coluna(df, COLUNAS_ABA2_ESPERADAS['documento'])
    col_valor = _encontrar_coluna(df, COLUNAS_ABA2_ESPERADAS['valor'])
    
    print(f"   📋 Colunas identificadas na Aba 2:")
    print(f"      Nome: {col_nome}")
    print(f"      Documento: {col_doc}")
    print(f"      Valor: {col_valor}")
    
    # Extrair dados
    if col_nome:
        dados['nome'] = df[col_nome]
    else:
        dados['nome'] = ''
    
    if col_doc:
        dados['documento'] = df[col_doc]
        # Limpar documento (apenas dígitos)
        dados['documento_limpo'] = dados['documento'].apply(_apenas_digitos)
    else:
        dados['documento'] = ''
        dados['documento_limpo'] = ''
    
    if col_valor:
        # Converter valor para numérico
        dados['valor'] = pd.to_numeric(df[col_valor], errors='coerce').fillna(0)
    else:
        dados['valor'] = 0
    
    # Remover linhas sem documento
    dados = dados[dados['documento_limpo'] != ''].copy()
    
    print(f"   📊 {len(dados)} registros com documento válido")
    
    # Agrupar por documento e somar valores
    dados_agrupados = dados.groupby('documento_limpo').agg({
        'nome': 'first',  # Pega o primeiro nome
        'documento': 'first',  # Pega o primeiro formato do documento
        'valor': 'sum'  # Soma os valores
    }).reset_index()
    
    print(f"   🔄 Agrupados em {len(dados_agrupados)} CPF/CNPJ únicos")
    
    # Verificar se houve agrupamento
    if len(dados_agrupados) < len(dados):
        qtd_agrupada = len(dados) - len(dados_agrupados)
        print(f"   ✅ {qtd_agrupada} registros duplicados foram somados")
    
    return dados_agrupados


# ============================================================================
# FUNÇÃO PRINCIPAL
# ============================================================================

def processar_amortizacao(
    input_file: str | Path,
    data_pagamento: str,
    saida_path: str | Path
) -> dict:
    """
    Processa arquivo Excel de amortização e gera CSV/XLSX
    
    Args:
        input_file: Caminho do arquivo Excel de entrada (com 2 abas)
        data_pagamento: Data de pagamento no formato dd/mm/yyyy
        saida_path: Caminho base para arquivos de saída (sem extensão)
    
    Returns:
        dict com: csv, xlsx, total_registros, mensagem
    """
    input_path = Path(input_file)
    saida_base = Path(saida_path)
    
    if not input_path.exists():
        raise FileNotFoundError(f'Arquivo não encontrado: {input_path}')
    
    print(f"📊 Processando arquivo: {input_path.name}")
    print(f"📅 Data de pagamento: {data_pagamento}")
    
    # Ler primeira aba do Excel
    print(f"\n📄 Lendo Aba 1...")
    df_aba1 = pd.read_excel(input_path, sheet_name=0, header=None)  # Sem cabeçalho
    print(f"✅ Aba 1 carregada: {len(df_aba1)} linhas, {len(df_aba1.columns)} colunas")
    
    # Extrair dados bancários da aba 1
    dados_bancarios = _extrair_dados_aba1(df_aba1)
    
    # Ler segunda aba do Excel
    print(f"\n📄 Lendo Aba 2...")
    df_aba2 = pd.read_excel(input_path, sheet_name=1)
    print(f"✅ Aba 2 carregada: {len(df_aba2)} linhas, {len(df_aba2.columns)} colunas")
    
    # Extrair dados da aba 2
    dados_aba2 = _extrair_dados_aba2(df_aba2)
    
    # Criar registros de saída
    registros = []
    
    for idx, row in dados_aba2.iterrows():
        documento_limpo = str(row.get('documento_limpo', '')).strip()
        documento_original = str(row.get('documento', '')).strip()
        tipo_doc = _identificar_tipo_documento(documento_limpo)
        valor_formatado = _formatar_valor(row.get('valor', 0))
        
        # Buscar dados bancários da aba 1
        dados_banco = dados_bancarios.get(documento_limpo, {})
        banco = dados_banco.get('banco', '')
        agencia = dados_banco.get('agencia', '')
        conta = dados_banco.get('conta', '')
        chave_pix = dados_banco.get('pix', '')
        
        registro = {
            'Forma de iniciação': '5',
            'Número do pagamento': '',
            'Chave Pix': chave_pix,
            'ISPB': '',
            'Banco': banco,
            'Agência': agencia,
            'Conta': conta,
            'Tipo de conta': 'CACC',
            'Nome do fornecedor': str(row.get('nome', '')).strip(),
            'Tipo documento': tipo_doc,
            'Documento': documento_limpo,
            'Valor a pagar': valor_formatado,
            'Data de pagamento': data_pagamento,
            'QR code (copia e cola)': '',
            'Informação ao recebedor': ''
        }
        registros.append(registro)
    
    # Criar DataFrame de saída
    df_saida = pd.DataFrame(registros, columns=COLUNAS_SAIDA)
    num_registros = len(df_saida)
    
    # Salvar CSV
    csv_path = saida_base.with_suffix('.csv')
    df_saida.to_csv(csv_path, sep=';', index=False, encoding='utf-8-sig')
    print(f"✅ CSV gerado: {csv_path}")
    
    # Salvar Excel com formatação de texto para colunas numéricas
    xlsx_path = saida_base.with_suffix('.xlsx')
    with pd.ExcelWriter(xlsx_path, engine='openpyxl') as writer:
        df_saida.to_excel(writer, index=False, sheet_name='Sheet1')
        
        # Aplicar formato de texto nas colunas que contêm números grandes
        worksheet = writer.sheets['Sheet1']
        from openpyxl.styles import numbers
        
        # Colunas que precisam ser texto: Chave Pix (C), Banco (E), Agência (F), Conta (G), Documento (K)
        colunas_texto = ['C', 'E', 'F', 'G', 'K']  # Índices das colunas
        
        for col in colunas_texto:
            for row in range(2, worksheet.max_row + 1):  # Começa da linha 2 (pula cabeçalho)
                cell = worksheet[f'{col}{row}']
                cell.number_format = '@'  # @ = formato de texto
                
    print(f"✅ Excel gerado: {xlsx_path}")
    
    return {
        'csv': str(csv_path),
        'xlsx': str(xlsx_path),
        'total_registros': num_registros,
        'mensagem': f'{num_registros} registros processados'
    }


# ============================================================================
# EXECUÇÃO DIRETA PARA TESTES
# ============================================================================

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 3:
        print("Uso: python Amortizacao_new.py <arquivo_entrada.xlsx> <data_pagamento>")
        print("Exemplo: python Amortizacao_new.py entrada.xlsx 05/11/2025")
        sys.exit(1)
    
    arquivo_entrada = sys.argv[1]
    data_pag = sys.argv[2]
    
    # Saída no mesmo diretório
    entrada_path = Path(arquivo_entrada)
    saida_path = entrada_path.parent / f"amortizacao_{entrada_path.stem}"
    
    try:
        resultado = processar_amortizacao(arquivo_entrada, data_pag, saida_path)
        print(f"\n✅ {resultado['mensagem']}")
    except Exception as e:
        print(f"\n❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
