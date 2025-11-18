"""
Gerador de secrets.toml completo para Streamlit Cloud
Gera arquivo com todos os 40 fundos Santander configurados
"""

import sys
import codecs

if sys.platform == 'win32':
    if hasattr(sys.stdout, 'buffer'):
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

from credenciais_bancos import SANTANDER_FUNDOS

# Token Pipefy (hardcoded para geração do secrets)
PIPEFY_API_TOKEN = "eyJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJQaXBlZnkiLCJpYXQiOjE3NjExMzkxNDcsImp0aSI6ImM1NzhhYzM5LTUwZmUtNGI0NC1iMzYzLWE5ZjNhMzBmNjUwYyIsInN1YiI6MzA2ODY4NTY3LCJ1c2VyIjp7ImlkIjozMDY4Njg1NjcsImVtYWlsIjoiZ3VzdGF2by5wcm9tZXR0aUBrYW5hc3RyYS5jb20uYnIifSwidXNlcl90eXBlIjoiYXV0aGVudGljYXRlZCJ9.hjcPATGMMX1xBcRMHQ7gfjkvqB7Nq9w0Ou9tD33fIlmLoicU928x5sd_T_nmkL04DV37GtxFtF5mCFaFSa4fVQ"

# Certificados em Base64 (gerados por converter_certificados.py)
CERT_BASE64 = "LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0tCk1JSUgyRENDQmNDZ0F3SUJBZ0lJR0NKM3M5MktsUVl3RFFZSktvWklodmNOQVFFTEJRQXdkREVMTUFrR0ExVUUKQmhNQ1FsSXhFekFSQmdOVkJBb1RDa2xEVUMxQ2NtRnphV3d4TmpBMEJnTlZCQXNUTFZObFkzSmxkR0Z5YVdFZwpaR0VnVW1WalpXbDBZU0JHWldSbGNtRnNJR1J2SUVKeVlYTnBiQ0F0SUZKR1FqRVlNQllHQTFVRUF4TVBRVU1nClZrRk1TVVFnVWtaQ0lIWTFNQjRYRFRJMU1URXdOVEUzTXpjd05Gb1hEVEkyTVRFd05URTNNemN3TkZvd2dnRVMKTVFzd0NRWURWUVFHRXdKQ1VqRVRNQkVHQTFVRUNoTUtTVU5RTFVKeVlYTnBiREUyTURRR0ExVUVDeE10VTJWagpjbVYwWVhKcFlTQmtZU0JTWldObGFYUmhJRVpsWkdWeVlXd2daRzhnUW5KaGMybHNJQzBnVWtaQ01SVXdFd1lEClZRUUxFd3hTUmtJZ1pTMURVRVlnUVRFeEdEQVdCZ05WQkFzVEQwRkRJRlpCVEVsRUlGSkdRaUJXTlRFaU1DQUcKQTFVRUN4TVpRVklnU2t3Z1EwVlNWRWxHU1VOQlJFOGdSRWxIU1ZSQlRERVpNQmNHQTFVRUN4TVFWbWxrWlc5agpiMjVtWlhKbGJtTnBZVEVYTUJVR0ExVUVDeE1PTWpZMU5EWTRNamd3TURBeE16TXhMVEFyQmdOVkJBTVRKRWRWClUxUkJWazhnVUZKUFRVVlVWRWtnVFVGVFExVk1TVG94TkRZMk16RTFNRFkzTlRDQ0FTSXdEUVlKS29aSWh2Y04KQVFFQkJRQURnZ0VQQURDQ0FRb0NnZ0VCQU5GRy9zZ0JTaE5ueW16ZzE3TVNxTFdsdXNra0pra1dlUmxtRUZRMgpFUEhTb1QvTWtMa2NYNFUwZ25DdWVRMTRhQXFoWFZYeVVwM3UxRXhtc21OY3BBKy9vL3VibkFIRzRjSzV0NE1DCmRNb2R3TzVpYkk5dlUvUmJXYmpwQ3VaVzI3ZnBOd3VhdUxsSkJFUGQzNXRVekNkOHFudHFLUmxPSzNpbnd4MzAKbWtZaHVzN2tZRzBuNFNzeG5ObjhTWDNaT0RCR2hMTGNlSHNQUU5VK0ZBWVBWNHVpWGFFTGVaZzQyRlVEUTlUQQorODR1NTl6TnFRSkx5dmlMaW5ZKzFTcnpVWUVkT3pkQ04zQUpOM25MWnQyVEtqNFNubFlPZXlVMHZ5VlZXaUZuCmdwZGFvZDlERFhGSmZnYlNaSHZtdUhSUDNSUlRQemhyajVPMDlkUzRtOW1KTXFNQ0F3RUFBYU9DQXN3d2dnTEkKTUlHY0JnZ3JCZ0VGQlFjQkFRU0JqekNCakRCVkJnZ3JCZ0VGQlFjd0FvWkphSFIwY0RvdkwybGpjQzFpY21GegphV3d1ZG1Gc2FXUmpaWEowYVdacFkyRmtiM0poTG1OdmJTNWljaTloWXkxMllXeHBaSEptWWk5aFl5MTJZV3hwClpISm1ZblkxTG5BM1lqQXpCZ2dyQmdFRkJRY3dBWVluYUhSMGNEb3ZMMjlqYzNCMk5TNTJZV3hwWkdObGNuUnAKWm1sallXUnZjbUV1WTI5dExtSnlNQWtHQTFVZEV3UUNNQUF3SHdZRFZSMGpCQmd3Rm9BVVU4dWw1SFZRbVVBcwp2bHNWUmNtK3l6Q3FpY1V3Y0FZRFZSMGdCR2t3WnpCbEJnWmdUQUVDQVNVd1d6QlpCZ2dyQmdFRkJRY0NBUlpOCmFIUjBjRG92TDJsamNDMWljbUZ6YVd3dWRtRnNhV1JqWlhKMGFXWnBZMkZrYjNKaExtTnZiUzVpY2k5aFl5MTIKWVd4cFpISm1ZaTlrY0dNdFlXTXRkbUZzYVdSeVptSldOUzV3WkdZd2diWUdBMVVkSHdTQnJqQ0JxekJUb0ZHZwpUNFpOYUhSMGNEb3ZMMmxqY0MxaWNtRnphV3d1ZG1Gc2FXUmpaWEowYVdacFkyRmtiM0poTG1OdmJTNWljaTloCll5MTJZV3hwWkhKbVlpOXNZM0l0WVdNdGRtRnNhV1J5Wm1KMk5TNWpjbXd3VktCU29GQ0dUbWgwZEhBNkx5OXAKWTNBdFluSmhjMmxzTWk1MllXeHBaR05sY25ScFptbGpZV1J2Y21FdVkyOXRMbUp5TDJGakxYWmhiR2xrY21aaQpMMnhqY2kxaFl5MTJZV3hwWkhKbVluWTFMbU55YkRBT0JnTlZIUThCQWY4RUJBTUNCZUF3SFFZRFZSMGZCQLL3CkZBWUlLd1lCQlFVSEF3SUdDQ3NHQVFVRkJ3TUVNSUdnQmdOVkhSRUVnWmd3Z1pXQklHZDFjM1JoZG04dWNISnYKYldWMGRHbEFhMkZ1WVhOMGNtRXVZMjl0TG1KeW9EZ0dCV0JNQVFNQm9DOEVMVEUwTURZeU1EQXdNVFEyTmpNeApOVEEyTnpVd01EQXdNREF3TURBd01EQXdNREF3TURBd01EQXdNREF3TUtBWEJnVmdUQUVEQnFBT0JBd3dNREF3Ck1EQXdNREF3TURDZ0hnWUZZRXdCQXdXZ0ZRUVRNREF3TURBd01EQXdNREF3TURBd01EQ3dNREFOQmdrcWhraUcKOXcwQkFRc0ZBQU9DQWdFQUh2UmVEYU1vMjJrbTUxQm90SGUrcW9wZXlQSzZvR1RNNDJMb0NhekpDWjNzWWIxTAo4SHg1R0lRRmVhdGxyR0paUENhVDZNVXFINnIzcVI2c2pKenpOT2d0OTNxRlFDN0FaR1NUS0hVUDFIMU9ya1piCnVZVVVMYTk0N013aXVzWSt1OWRUSDZQSFF5dEJncnp5YzNpODJxYWNoa3BydjJhUW4ySFkyVXpCamVBSHczVHYKUnFRMUJGNFd0M2Y0RjVTbmM0TDV3a0hNUnBGSUJXRkxyOEMvOGZXemNIZHNWcC9KMzM1VjZLRFhhZVRWUmFISwpmQS9ScEo3dmJsQ1p4QkdpMHUvRkMzdjV3MFVycllKa3RWcWJhaXVybHRrME9uZWxGQjNwVWc2dFZyNGlLTElWCjBRUW90NzVLTWwzS0dKVE42M0NIUHlLN3IyRzkxaGNBMVZEL3p3cUNpelpkbWhqOEVjNGJabzNJczhsVFJIVVcKV0RJUG03T3hFQit5QkNBVHFFT1lUQXh5dTJrcmZpUlFiWFN0L1dEOWhrT1BoUWxtRWc2MXluUjlla2k1STNJVQpLZzFIb2Y0T3ZiM01wWDltQS9jUHlUMXBoZEdSQzdmc3ZFVXpDajQvSEt4aFljU1dmRWx0RkdYd1Z2U0NjQ0dxCktWZVF6b0I0bWREd0o3Vk96S3FYOFJBQ1VBSWxaanhCUTZsNTV3Qm9MaVNMbVN1QzAzSW9IcCtJL1NVRllvZCsKOElibVpyQ3FHUVZKcllOMFVCOG5aalNmUFFCbjJxT3IwUjdydDNMOVMwVGZyMlk5TWg1YXdEdDVYNGplbW9PdgpYVTloSGZPOEcxT2QwNWJJc0l2RE5Ud0ovWTFUeFNaWTdocFhLNmhBSEY0YUwvcDRtazNUY29sTm15Zz0KLS0tLS1FTkQgQ0VSVElGSUNBVEUtLS0tLQo="

KEY_BASE64 = "LS0tLS1CRUdJTiBSU0EgUFJJVkFURSBLRVktLS0tLQpNSUlFcGdJQkFBS0NBUUVBMFViK3lBRktFMmZLYk9EWHN4S290YVc2eVNRbVNSWjVHV1lRVkRZUThkS2hQOHlRCnVSeGZoVFNDY0s1NURYaG9DcUZkVmZKU25lN1VUR2F5WTF5a0Q3K2orNXVjQWNiaHdybTNnd0oweWgzQTdtSnMKajI5VDlGdFp1T2tLNWxiYnQrazNDNXE0dVVrRVE5M2ZtMVRNSjN5cWUyb3BHVTRyZUtmREhmU2FSaUc2enVSZwpiU2ZoS3pHYzJmeEpmZGs0TUVhRXN0eDRldzlBMVQ0VUJnOVhpNkpkb1F0NW1EallWUU5EMU1EN3ppN24zTTJwCkFrdksrSXVLZGo3Vkt2TlJnUjA3TjBJM2NBazNlY3RtM1pNcVBoS2VWZzU3SlRTL0pWVmFJV2VDbDFxaDMwTU4KY1VsK0J0SmtlK2E0ZEUvZEZGTS9PR3VQazdUMTFMaWIyWWt5b3dJREFRQUJBb0lCQVFDUUEyWVM1bWcrWUY4NQplNlNUczFScjVBZGNvVWJEWnZhZzFzNkgxTWptVUlic2EyNXdKQ2xMZGk0Sk10ZFV3TFlBRXJrekN0VjFuME55CjYvejRTV2tRK1ZURDBHVW96SXRSNjl1aGsvRXk0UmE5ZG5GZU9nUkxxQmU4QlEwVmY2d2U2VUgrenVaNUN5dzluClVJaXUwTFRJdTQ1cDdVMG8vOVVFYTVYbXlFdGQxRnBtSkhVTHZNbHVTY0RicW5ZaUthYS9jamsvWk02cWh6K0MKdnh0THVhdXMzeVFMLy9iWHgwQ052N0R5QUd6bHNWUVYxQXpUZE5hbnQvYyswWTF1d0xVWm83R0I5dVBrbUlRMAo4UGdaZkJCVVgrVDRRTTdwVFpMTElvZ1NQclNhaXFsYnhlTWlFdzJUT1ViZkkzbHBSREJDam42c3JwVVd0cXd1Cmt5N0hWTVg1QW9HQkFOTjVlRHF4TTViNTl6WDNLdkw2aXJUZDVQY0JJYlZOSXlwM21YYmRjeXR3WEZPSFl5U1gKT0hzV1BLUU40ME1DSmFZK2FrU2tyc1R1WmVlZDFPM2xUTkhkNXgxL1JhNFZaVUNaNXVSenlQTFpQeU5NMEJrVQpWb05VQXBvWjJKS2lyOXY2TWxmQVFRY282ZnBtcnN3VHRVY0FEL0FtaWx3L1JLaTlRbFpLSVM3dEFvR0JBUDFYCR1FamlQMUFxTndoS2VFYXR6ZHc5ZEhZU2pDMnNGNGFHWFJhTFk2MVBTUElQUmlIdVBPcEZ6ZVdTTG1qVVRVYkd5Cnh2RHBGWjQ3YlE2S0RWZXo2MXFxU1EwOTl0eG5HUTEyekhddUxDNUdhcFdlSzhZZmVONmZ5Z1FMb1Mwc242QUoKVWEwNmJlWGVCYkZXSFdJUDNYQ2R5VmEzQndZUEVaaSt6TnVISENYUEFvR0JBTURNUEkyZDRqL2gwcnpUZzhlVQpIWU01emJaWHhNaUs4K1dTdGtvRktTdlFPNHczb1c3Sm8wZXNoVXE0RXBxVHlZbGYyL2lLLzM4eExaelZhendjClVrWC9mZWFKa3hoY0R6eXZVeTZ5Vk9ENnFUSmtGUkpFM3FWeysxOFpOT0RHTHR4Z2Ywa2hTWiszODd3RjcwCkZOQVBRWGliV29jeGMwSTNrZFFqcjA4ZEFvR0JBTDdwSXRGMEpGdHJwa04zWU9OdUdOdTRGT1YrSkwyYTZnUm0KeGJCSmZWVm1TZm9nTFpUSFE2Q1dmM1ZZaW5YU3dDNkVCYzFJS09WYjdQd1c1cVVmelkwK1k5eVp4RzBsT0VqZwpMSWpKeXp0NER4diszUWdackRGQUF2RjNmaGRYMkZhMmp4bFd2YmlLem9scjFxcXVQL1o4d1Z3YWd5MTZyNDBHCnc4UHZGalFiQW9HQkFNUTRCZkNWRFRwZmpVOG5kYytQUnVqUCtnMm9TeHdtN3FkbUt6djBYR2pSeHhiSFljbHAKV0FQZXdxcUtIczJJcXBBR0FBYjRINEFjdkVHSk9zdFNsOWhQWDMvUDJnM2Vnd1hEQU5WM0gwbERJZTZMSi9iUgp1ZENpNDJFTE5vclo4NE52SkJlR2hlaVhrZWsvUFJIcjZrcUNOY3VQTm1Oc3NhZitiUldZZnAzMwotLS0tLUVORCBSU0EgUFJJVkFURSBLRVktLS0tLQo="

def gerar_secrets_toml():
    """Gera arquivo secrets.toml completo"""
    
    print("\n" + "="*100)
    print("📝 GERANDO secrets.toml COMPLETO PARA STREAMLIT CLOUD")
    print("="*100)
    
    output = []
    
    # Header
    output.append("# Streamlit Secrets - Dashboard Pipefy Kanastra")
    output.append("# Gerado automaticamente - NÃO COMMITAR NO GIT!")
    output.append("")
    output.append("# Pipefy API Token")
    output.append(f'pipefy_token = "{PIPEFY_API_TOKEN}"')
    output.append("")
    
    # Fundos Santander
    output.append("[santander_fundos]")
    output.append("")
    
    for fundo_id, config in SANTANDER_FUNDOS.items():
        output.append(f"[santander_fundos.{fundo_id}]")
        output.append(f'nome = "{config["nome"]}"')
        
        # Adicionar nome_pipe_liq se existir
        if "nome_pipe_liq" in config:
            output.append(f'nome_pipe_liq = "{config["nome_pipe_liq"]}"')
        
        output.append(f'cnpj = "{config["cnpj"]}"')
        output.append(f'client_id = "{config["client_id"]}"')
        output.append(f'client_secret = "{config["client_secret"]}"')
        output.append(f'cert_base64 = "{CERT_BASE64}"')
        output.append(f'key_base64 = "{KEY_BASE64}"')
        output.append("")
    
    # Salvar arquivo
    arquivo_saida = "secrets.toml"
    with open(arquivo_saida, 'w', encoding='utf-8') as f:
        f.write('\n'.join(output))
    
    # Estatísticas
    total_fundos = len(SANTANDER_FUNDOS)
    fundos_com_nome_pipe = sum(1 for c in SANTANDER_FUNDOS.values() if "nome_pipe_liq" in c)
    
    print(f"\n✅ Arquivo gerado com sucesso!")
    print(f"\n📊 Estatísticas:")
    print(f"   📁 Total de fundos: {total_fundos}")
    print(f"   ✅ Fundos com nome_pipe_liq: {fundos_com_nome_pipe}/{total_fundos} ({fundos_com_nome_pipe/total_fundos*100:.1f}%)")
    print(f"   🔐 Certificados incluídos (Base64)")
    print(f"   🎫 Token Pipefy incluído")
    
    print(f"\n📝 Arquivo salvo: {arquivo_saida}")
    conteudo_completo = '\n'.join(output)
    print(f"   Tamanho: {len(conteudo_completo) / 1024:.1f} KB")
    
    print("\n" + "="*100)
    print("📋 PRÓXIMOS PASSOS:")
    print("="*100)
    print("\n1. Para Streamlit Cloud:")
    print("   - Acesse: https://share.streamlit.io/")
    print("   - Vá em: Settings > Secrets")
    print(f"   - Cole TODO o conteúdo de {arquivo_saida}")
    print("\n2. Para desenvolvimento local:")
    print("   - Copie secrets.toml para: .streamlit/secrets.toml")
    print("\n⚠️  ATENÇÃO:")
    print("   - NÃO faça commit de secrets.toml no git!")
    print("   - Arquivo já está no .gitignore")
    print("="*100)
    
    # Listar fundos configurados
    print("\n🏦 FUNDOS CONFIGURADOS:")
    print("-"*100)
    for idx, (fundo_id, config) in enumerate(SANTANDER_FUNDOS.items(), 1):
        nome_pipe = config.get('nome_pipe_liq', 'N/A')
        cnpj_status = "✅" if config.get('cnpj') else "❌"
        nome_pipe_status = "✅" if 'nome_pipe_liq' in config else "❌"
        print(f"{idx:2}. {fundo_id:20} | CNPJ: {cnpj_status} | nome_pipe_liq: {nome_pipe_status} | {nome_pipe}")
    
    print("\n" + "="*100)

if __name__ == "__main__":
    gerar_secrets_toml()
