# Script para atualizar processamento CETIP no dashboard

# Ler o arquivo
with open('app_streamlit.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Encontrar e substituir linha por linha
for i in range(len(lines)):
    # Substituir linha do NC
    if '📄 [NC] Iniciando Emissão de NC...' in lines[i] or '� [NC] Iniciando Emissão de NC...' in lines[i]:
        # Encontrou o início do bloco NC - vamos refazer esse bloco
        # Primeira linha: adicionar conversão Path
        if i > 0 and 'tmp_path_obj = Path(tmp_path)' not in lines[i-2]:
            lines.insert(i, '                    # Converter string de tmp_path para Path object\n')
            lines.insert(i+1, '                    tmp_path_obj = Path(tmp_path)\n')
            lines.insert(i+2, '                    \n')
        
        # Substituir a linha do NC
        lines[i+3] = '                        log_cetip.append("📄 EMISSÃO NC")\n'
        
        # Procurar e remover linhas de simulação
        j = i + 4
        while j < len(lines) and 'contadores["NC"]' not in lines[j]:
            j += 1
        
        # Substituir bloco entre o título e o contador
        if j < len(lines):
            # Remover linhas entre i+4 e j
            del lines[i+4:j]
            # Adicionar nova linha de processamento
            lines.insert(i+4, '                        qtd_nc = run_emissao_nc(log_cetip, tmp_path_obj, pasta_saida_cetip)\n')
            lines.insert(i+5, '                        contadores["NC"] = qtd_nc\n')
        
        break

# Salvar
with open('app_streamlit.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print('✅ Processamento NC atualizado!')
