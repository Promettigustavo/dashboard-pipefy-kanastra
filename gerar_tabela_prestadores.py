import json
import pandas as pd
from datetime import datetime

def gerar_tabela_prestadores(arquivo_json):
    """
    Gera uma tabela Excel com informações dos prestadores de serviço
    
    Args:
        arquivo_json: Caminho para o arquivo JSON com os cards
    """
    
    print("📊 GERANDO TABELA DE PRESTADORES")
    print("=" * 80)
    
    # Carregar o JSON
    try:
        with open(arquivo_json, 'r', encoding='utf-8') as f:
            cards = json.load(f)
        print(f"✅ Arquivo carregado: {len(cards)} cards encontrados")
    except Exception as e:
        print(f"❌ Erro ao carregar arquivo: {e}")
        return
    
    # Lista para armazenar os dados
    dados = []
    
    print(f"\n🔍 Extraindo informações dos cards...")
    
    for i, card in enumerate(cards, 1):
        if i % 100 == 0:
            print(f"   Processando card {i}/{len(cards)}...")
        
        # Dicionário para armazenar os campos do card
        campos = {}
        for field in card.get('fields', []):
            campos[field['name']] = field.get('value', '')
        
        # Extrair as informações desejadas
        registro = {
            'Nome do Fundo': campos.get('Nome do Fundo', ''),
            'Prestador': campos.get('Razão Social do Beneficiário', ''),
            'CNPJ': campos.get('CNPJ', ''),
            'Email': campos.get('Seu email', ''),
            'Email Creditas': campos.get('E-mail Creditas(liquidação)', ''),
            'Valor': campos.get('Valor', ''),
            'Data Pagamento': campos.get('Prazo para pagamento', ''),
            'Forma Pagamento': campos.get('Forma de Pagamento', ''),
            'Card ID': card.get('id', ''),
            'Criado em': card.get('created_at', ''),
            'Finalizado em': card.get('finished_at', '')
        }
        
        dados.append(registro)
    
    # Criar DataFrame
    df = pd.DataFrame(dados)
    
    print(f"\n✅ {len(df)} registros processados")
    print("\n📋 Colunas da tabela:")
    for col in df.columns:
        print(f"   • {col}")
    
    # Exibir estatísticas
    print("\n📊 ESTATÍSTICAS:")
    print(f"   • Total de registros: {len(df)}")
    print(f"   • Fundos únicos: {df['Nome do Fundo'].nunique()}")
    print(f"   • Prestadores únicos: {df['Prestador'].nunique()}")
    
    # Mostrar top 5 fundos com mais prestadores
    print("\n🏆 TOP 5 FUNDOS COM MAIS PRESTADORES:")
    top_fundos = df['Nome do Fundo'].value_counts().head(5)
    for fundo, count in top_fundos.items():
        print(f"   {count:3d} - {fundo}")
    
    # Mostrar top 5 prestadores mais frequentes
    print("\n🏆 TOP 5 PRESTADORES MAIS FREQUENTES:")
    top_prestadores = df['Prestador'].value_counts().head(5)
    for prestador, count in top_prestadores.items():
        print(f"   {count:3d} - {prestador}")
    
    # Salvar em Excel
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    arquivo_excel = f"tabela_prestadores_{timestamp}.xlsx"
    
    try:
        # Criar Excel com formatação
        with pd.ExcelWriter(arquivo_excel, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Prestadores', index=False)
            
            # Ajustar largura das colunas
            worksheet = writer.sheets['Prestadores']
            for idx, col in enumerate(df.columns):
                max_length = max(
                    df[col].astype(str).apply(len).max(),
                    len(col)
                ) + 2
                worksheet.column_dimensions[chr(65 + idx)].width = min(max_length, 50)
        
        print(f"\n💾 Tabela salva em: {arquivo_excel}")
        
        # Salvar também em CSV para facilitar visualização
        arquivo_csv = f"tabela_prestadores_{timestamp}.csv"
        df.to_csv(arquivo_csv, index=False, encoding='utf-8-sig', sep=';')
        print(f"💾 Tabela CSV salva em: {arquivo_csv}")
        
    except Exception as e:
        print(f"\n❌ Erro ao salvar arquivo: {e}")
        return
    
    print("\n" + "=" * 80)
    print("✅ PROCESSO CONCLUÍDO!")
    print("=" * 80)
    
    return df


if __name__ == "__main__":
    # Nome do arquivo JSON gerado anteriormente
    arquivo_json = "cards_concluido_prestadores_20251111_110029.json"
    
    df = gerar_tabela_prestadores(arquivo_json)
    
    if df is not None:
        print("\n📊 Primeiras 5 linhas da tabela:")
        print(df.head().to_string())
