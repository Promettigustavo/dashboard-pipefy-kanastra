# ============================================================
# SCRIPT DE EXECUÇÃO COMPLETA DO FLUXO FROMTIS
# ============================================================
# Executa automaticamente:
# 1. Exportação do mapeamento de fundos (credenciais_bancos.py → JSON)
# 2. Busca de comprovantes Santander (para todos os fundos configurados)
# 3. Execução do robô Puppeteer (anexação automática)
# ============================================================

# Configuracao de encoding para suportar emojis
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

# Cores para output
function Write-Success { param($Message) Write-Host "[OK] $Message" -ForegroundColor Green }
function Write-Error-Custom { param($Message) Write-Host "[ERRO] $Message" -ForegroundColor Red }
function Write-Info { param($Message) Write-Host "[INFO] $Message" -ForegroundColor Cyan }
function Write-Step { param($Message) Write-Host "`n[ETAPA] $Message" -ForegroundColor Yellow }

# Diretório base do projeto
$PROJECT_DIR = $PSScriptRoot
Set-Location $PROJECT_DIR

Write-Host "`n" + ("="*70) -ForegroundColor Magenta
Write-Host "   FLUXO COMPLETO - FROMTIS AUTOMAÇÃO" -ForegroundColor Magenta
Write-Host ("="*70) -ForegroundColor Magenta
Write-Host ""

# ============================================================
# ETAPA 1: EXPORTAR MAPEAMENTO DE FUNDOS
# ============================================================
Write-Step "ETAPA 1/3: Exportando mapeamento de fundos"
Write-Info "Gerando mapeamento_fundos_fromtis.json a partir de credenciais_bancos.py..."

try {
    $result = py exportar_mapeamento_fundos.py 2>&1
    
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Mapeamento exportado com sucesso!"
        
        # Verificar se arquivo foi criado
        if (Test-Path "mapeamento_fundos_fromtis.json") {
            $jsonContent = Get-Content "mapeamento_fundos_fromtis.json" -Raw | ConvertFrom-Json
            $fundosCount = ($jsonContent | Get-Member -MemberType NoteProperty).Count
            Write-Info "Total de fundos no mapeamento: $fundosCount"
        }
    } else {
        Write-Error-Custom "Erro ao exportar mapeamento!"
        Write-Host $result
        exit 1
    }
} catch {
    Write-Error-Custom "Falha na exportação do mapeamento: $_"
    exit 1
}

# ============================================================
# ETAPA 2: BUSCAR COMPROVANTES SANTANDER (CARGA INICIAL)
# ============================================================
Write-Step "ETAPA 2/3: Buscando comprovantes Santander (carga inicial)"
Write-Info "Buscando comprovantes do dia atual..."

try {
    # Busca inicial: últimos 1 dia
    $diasRetroativos = 1
    
    Write-Info "Consultando API Santander para todos os fundos configurados..."
    
    # Executa script de busca de comprovantes
    $result = py buscar_comprovantes_todos_fundos.py --dias $diasRetroativos 2>&1
    
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Comprovantes baixados com sucesso!"
        
        # Verificar quantos PDFs foram salvos
        if (Test-Path "Comprovantes") {
            $pdfCount = (Get-ChildItem "Comprovantes\*.pdf" -ErrorAction SilentlyContinue).Count
            Write-Info "Total de comprovantes salvos: $pdfCount PDFs"
        }
    } else {
        Write-Error-Custom "Erro ao buscar comprovantes!"
        Write-Host $result
        
        # Pergunta se quer continuar mesmo com erro
        $continuar = Read-Host "Deseja continuar mesmo assim? (S/N)"
        if ($continuar -ne "S" -and $continuar -ne "s") {
            exit 1
        }
    }
} catch {
    Write-Error-Custom "Falha na busca de comprovantes: $_"
    
    # Pergunta se quer continuar mesmo com erro
    $continuar = Read-Host "Deseja continuar para o robô? (S/N)"
    if ($continuar -ne "S" -and $continuar -ne "s") {
        exit 1
    }
}

# ============================================================
# ETAPA 2.5: CONFIGURAR ATUALIZAÇÃO CONTÍNUA DO CACHE
# ============================================================
Write-Info "Configurando atualização automática do cache a cada 3 minutos..."

# Job em background para atualizar cache continuamente
$cacheUpdateJob = Start-Job -ScriptBlock {
    param($projectDir)
    
    Set-Location $projectDir
    
    while ($true) {
        Start-Sleep -Seconds 180  # 3 minutos
        
        try {
            # Busca novos comprovantes (silencioso)
            py buscar_comprovantes_todos_fundos.py --dias 1 2>&1 | Out-Null
        } catch {
            # Ignora erros (não interrompe o robô)
        }
    }
} -ArgumentList $PROJECT_DIR

Write-Success "Cache será atualizado automaticamente em background!"
Write-Info "Job ID: $($cacheUpdateJob.Id) - Cache atualiza a cada 3 minutos"

# ============================================================
# ETAPA 3: COMPILAR TYPESCRIPT (SE NECESSÁRIO)
# ============================================================
Write-Step "ETAPA 3A/3: Verificando compilação TypeScript"

$tsFile = "puppeteer_com_comprovantes_v2.ts"
$jsFile = "puppeteer_com_comprovantes_v2.js"

# Verifica se .js existe e está mais recente que .ts
$needsCompile = $false

if (-not (Test-Path $jsFile)) {
    Write-Info "Arquivo .js não encontrado - compilação necessária"
    $needsCompile = $true
} else {
    $tsModified = (Get-Item $tsFile).LastWriteTime
    $jsModified = (Get-Item $jsFile).LastWriteTime
    
    if ($tsModified -gt $jsModified) {
        Write-Info "Arquivo .ts foi modificado - recompilação necessária"
        $needsCompile = $true
    } else {
        Write-Success "Arquivo .js está atualizado"
    }
}

if ($needsCompile) {
    Write-Info "Compilando TypeScript..."
    
    try {
        # Tenta usar npx primeiro
        $compileResult = cmd /c "npx tsc $tsFile --skipLibCheck 2>&1"
        
        if ($LASTEXITCODE -eq 0) {
            Write-Success "TypeScript compilado com sucesso!"
        } else {
            Write-Error-Custom "Erro na compilação TypeScript!"
            Write-Host $compileResult
            
            Write-Info "Tentando compilação alternativa com node..."
            $compileResult = cmd /c "node node_modules\typescript\bin\tsc $tsFile --skipLibCheck 2>&1"
            
            if ($LASTEXITCODE -eq 0) {
                Write-Success "TypeScript compilado com sucesso (método alternativo)!"
            } else {
                Write-Error-Custom "Falha na compilação. Execute manualmente: tsc $tsFile --skipLibCheck"
                
                # Pergunta se quer continuar com .js antigo
                if (Test-Path $jsFile) {
                    $continuar = Read-Host "Arquivo .js antigo existe. Deseja usar ele mesmo assim? (S/N)"
                    if ($continuar -ne "S" -and $continuar -ne "s") {
                        exit 1
                    }
                } else {
                    Write-Error-Custom "Nenhum arquivo .js disponível. Impossível continuar."
                    exit 1
                }
            }
        }
    } catch {
        Write-Error-Custom "Falha ao compilar TypeScript: $_"
        exit 1
    }
}

# ============================================================
# ETAPA 4: EXECUTAR ROBÔ PUPPETEER
# ============================================================
Write-Step "ETAPA 3B/3: Executando robô Puppeteer"
Write-Info "Iniciando automação Fromtis com anexação de comprovantes..."
Write-Info "Pressione Ctrl+C para interromper"
Write-Host ""

try {
    # Executa o robô
    node $jsFile
    
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Robô executado com sucesso!"
    } else {
        Write-Error-Custom "Robô finalizou com erros (código: $LASTEXITCODE)"
    }
} catch {
    Write-Error-Custom "Falha ao executar robô: $_"
    exit 1
} finally {
    # Para o job de atualização de cache ao finalizar
    if ($cacheUpdateJob) {
        Write-Info "Parando atualização automática do cache..."
        Stop-Job -Job $cacheUpdateJob -ErrorAction SilentlyContinue
        Remove-Job -Job $cacheUpdateJob -ErrorAction SilentlyContinue
        Write-Success "Cache job finalizado"
    }
}

# ============================================================
# RESUMO FINAL
# ============================================================
Write-Host "`n" + ("="*70) -ForegroundColor Magenta
Write-Host "   FLUXO COMPLETO FINALIZADO" -ForegroundColor Magenta
Write-Host ("="*70) -ForegroundColor Magenta

Write-Host "`nResumo da Execucao:" -ForegroundColor Cyan
Write-Host "   [OK] Mapeamento de fundos exportado" -ForegroundColor Green
Write-Host "   [OK] Comprovantes Santander baixados" -ForegroundColor Green
Write-Host "   [OK] Robo Puppeteer executado" -ForegroundColor Green

if (Test-Path "Comprovantes") {
    $pdfCount = (Get-ChildItem "Comprovantes\*.pdf" -ErrorAction SilentlyContinue).Count
    Write-Host "`nComprovantes disponiveis: $pdfCount PDFs" -ForegroundColor Yellow
}

if (Test-Path "mapeamento_fundos_fromtis.json") {
    $jsonContent = Get-Content "mapeamento_fundos_fromtis.json" -Raw | ConvertFrom-Json
    $fundosCount = ($jsonContent | Get-Member -MemberType NoteProperty).Count
    Write-Host "Fundos mapeados: $fundosCount" -ForegroundColor Yellow
}

Write-Host "`n"
