#!/usr/bin/env python3
"""
Gera um único secret JSON com TODAS as credenciais necessárias
para o GitHub Actions
"""

import json
from pathlib import Path
from credenciais_bancos import SANTANDER_FUNDOS

def ler_arquivo(caminho):
    """Lê arquivo e retorna conteúdo"""
    try:
        with open(caminho, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"⚠️  Erro ao ler {caminho}: {e}")
        return None

def main():
    print("="*80)
    print("GERADOR DE SECRET ÚNICO PARA GITHUB ACTIONS")
    print("="*80)
    print()
    
    # Paths dos certificados
    cert_path = r"C:\Users\GustavoPrometti\Cert\santander_cert.pem"
    key_path = r"C:\Users\GustavoPrometti\Cert\santander_key.pem"
    
    # Ler certificados
    print("📄 Lendo certificados Santander...")
    cert_content = ler_arquivo(cert_path)
    key_content = ler_arquivo(key_path)
    
    if not cert_content or not key_content:
        print("❌ Erro: Certificados não encontrados!")
        print(f"   Verifique se existem em:")
        print(f"   - {cert_path}")
        print(f"   - {key_path}")
        return
    
    print(f"✅ Certificado: {len(cert_content)} caracteres")
    print(f"✅ Chave privada: {len(key_content)} caracteres")
    
    # Solicitar credenciais Fromtis
    print()
    print("🔑 Digite as credenciais do Fromtis:")
    fromtis_username = input("   Usuário Fromtis: ").strip()
    fromtis_password = input("   Senha Fromtis: ").strip()
    
    if not fromtis_username or not fromtis_password:
        print("❌ Erro: Usuário e senha do Fromtis são obrigatórios!")
        return
    
    # Montar o secret completo
    print()
    print("🔨 Montando secret completo...")
    
    secret_completo = {
        "santander": {
            "cert_pem": cert_content,
            "key_pem": key_content,
            "fundos": SANTANDER_FUNDOS
        },
        "fromtis": {
            "username": fromtis_username,
            "password": fromtis_password
        }
    }
    
    # Salvar em arquivo
    output_file = "github_secret_completo.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(secret_completo, f, indent=2, ensure_ascii=False)
    
    file_size = Path(output_file).stat().st_size / 1024  # KB
    
    print(f"✅ Secret gerado: {output_file} ({file_size:.1f} KB)")
    print()
    print("="*80)
    print("📋 PRÓXIMOS PASSOS")
    print("="*80)
    print()
    print("1. Abra o arquivo gerado:")
    print(f"   notepad {output_file}")
    print()
    print("2. Copie TODO o conteúdo (Ctrl+A, Ctrl+C)")
    print()
    print("3. Acesse GitHub Secrets:")
    print("   https://github.com/Promettigustavo/dashboard-pipefy-kanastra/settings/secrets/actions")
    print()
    print("4. Clique em 'New repository secret'")
    print()
    print("5. Nome do secret:")
    print("   KANASTRA_CREDENTIALS")
    print()
    print("6. Cole o conteúdo copiado")
    print()
    print("7. Clique em 'Add secret'")
    print()
    print("="*80)
    print()
    print("⚠️  IMPORTANTE:")
    print("   - Apenas 1 secret ao invés de 5!")
    print("   - Arquivo local sensível - NÃO commitar!")
    print("   - Deletar após configurar no GitHub")
    print()
    print("="*80)

if __name__ == "__main__":
    main()
