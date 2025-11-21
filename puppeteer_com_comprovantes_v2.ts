import puppeteer from 'puppeteer';
import * as fs from 'fs';
import { spawn } from 'child_process';

const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

// ============================================================
// INTERFACES E TIPOS
// ============================================================
interface Comprovante {
    cnpj_fundo: string;
    valor: number;
    beneficiario: string;
}

// ============================================================
// CARREGAMENTO DE MAPEAMENTO DE FUNDOS
// ============================================================
let MAPEAMENTO_FUNDOS_LIMINE: Record<string, string> = {};

function carregarMapeamentoFundos(): void {
    try {
        const conteudo = fs.readFileSync('mapeamento_fundos_fromtis.json', 'utf-8');
        MAPEAMENTO_FUNDOS_LIMINE = JSON.parse(conteudo);
        log(`✅ Mapeamento de fundos carregado: ${Object.keys(MAPEAMENTO_FUNDOS_LIMINE).length} fundos`);
    } catch (erro) {
        log(`❌ Erro ao carregar mapeamento de fundos: ${erro}`);
        MAPEAMENTO_FUNDOS_LIMINE = {};
    }
}

// ============================================================
// FUNÇÕES DE NORMALIZAÇÃO E BUSCA
// ============================================================

/**
 * Normaliza nome do banco removendo acentos e convertendo para uppercase
 */
function normalizarNomeBanco(nome: string): string {
    return nome
        .normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '')
        .toUpperCase()
        .trim();
}

/**
 * Normaliza CNPJ removendo pontuação
 */
function normalizarCNPJ(cnpj: string): string {
    return cnpj.replace(/[^\d]/g, '');
}

/**
 * Normaliza valor monetário para número
 * Aceita formatos: "R$ 1.234,56", "1234.56", "1.234,56"
 */
function normalizarValor(valor: string): number {
    // Remove "R$" e espaços
    let valorLimpo = valor.replace(/R\$\s*/g, '').trim();
    
    // Se tem vírgula, assume formato brasileiro (1.234,56)
    if (valorLimpo.includes(',')) {
        valorLimpo = valorLimpo.replace(/\./g, '').replace(',', '.');
    }
    
    return parseFloat(valorLimpo) || 0;
}

/**
 * Normaliza nome de pessoa/empresa para comparação
 */
function normalizarNome(nome: string): string {
    return nome
        .normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '')
        .replace(/[^A-Z0-9\s]/gi, '')
        .replace(/\s+/g, ' ')
        .toUpperCase()
        .trim();
}

/**
 * Obtém CNPJ Santander a partir do nome do fundo no Limine
 */
function obterCNPJPorNomeFundo(nomeFundo: string): string | null {
    const nomeNormalizado = normalizarNomeBanco(nomeFundo);
    
    // Busca exata primeiro
    for (const [key, cnpj] of Object.entries(MAPEAMENTO_FUNDOS_LIMINE)) {
        if (normalizarNomeBanco(key) === nomeNormalizado) {
            return cnpj;
        }
    }
    
    // Busca parcial (contém)
    for (const [key, cnpj] of Object.entries(MAPEAMENTO_FUNDOS_LIMINE)) {
        const keyNormalizado = normalizarNomeBanco(key);
        if (keyNormalizado.includes(nomeNormalizado) || nomeNormalizado.includes(keyNormalizado)) {
            return cnpj;
        }
    }
    
    return null;
}

/**
 * Busca comprovante por CNPJ e valor (sem validação de beneficiário)
 */
function buscarComprovantePorValorEBeneficiario(
    comprovantes: Comprovante[],
    cnpj: string,
    valor: number,
    beneficiario: string
): Comprovante | null {
    const cnpjNormalizado = normalizarCNPJ(cnpj);
    const toleranciaValor = 0.02;
    
    const candidato = comprovantes.find(comp => {
        const cnpjCompNormalizado = normalizarCNPJ(comp.cnpj_fundo);
        const diferencaValor = Math.abs(comp.valor - valor);
        
        return cnpjCompNormalizado === cnpjNormalizado && diferencaValor <= toleranciaValor;
    });
    
    return candidato || null;
}

// ============================================================
// BUSCA EM TEMPO REAL DE COMPROVANTES (COM RETRY)
// ============================================================

/**
 * Busca comprovante em tempo real na API Santander para um CNPJ específico
 * Retorna lista de comprovantes encontrados para aquele fundo
 */
async function buscarComprovanteTempoReal(cnpj: string): Promise<Comprovante[]> {
    try {
        log(`🔍 Buscando comprovante em tempo real para CNPJ ${cnpj}...`);
        
        // Executa script Python para buscar comprovantes de um fundo específico
        const comprovantesBuscados = await new Promise<Comprovante[]>((resolve, reject) => {
            const processo = spawn('python', [
                'buscar_comprovante_fundo_especifico.py',
                cnpj
            ]);
            
            let saida = '';
            let erro = '';
            
            processo.stdout.on('data', (dados) => {
                saida += dados.toString();
            });
            
            processo.stderr.on('data', (dados) => {
                erro += dados.toString();
            });
            
            processo.on('close', (codigo) => {
                if (codigo !== 0) {
                    log(`⚠️ Erro ao buscar comprovante (código ${codigo}): ${erro}`);
                    resolve([]);
                    return;
                }
                
                try {
                    // Espera JSON com lista de comprovantes
                    const resultado = JSON.parse(saida);
                    resolve(resultado.comprovantes || []);
                } catch (e) {
                    log(`⚠️ Erro ao parsear resposta da busca: ${e}`);
                    resolve([]);
                }
            });
        });
        
        if (comprovantesBuscados.length > 0) {
            log(`✅ Encontrados ${comprovantesBuscados.length} comprovante(s) em tempo real para CNPJ ${cnpj}`);
        } else {
            log(`⏭️ Nenhum comprovante encontrado em tempo real para CNPJ ${cnpj}`);
        }
        
        return comprovantesBuscados;
    } catch (erro) {
        log(`❌ Erro na busca em tempo real: ${erro}`);
        return [];
    }
}

/**
 * Busca comprovante com sistema de retry (até 3 tentativas com intervalo de 30s)
 * Atualiza o cache global de comprovantes quando encontra
 */
async function buscarComprovanteComRetry(
    cnpj: string,
    valor: number,
    beneficiario: string,
    comprovantesRef: { lista: Comprovante[] }
): Promise<Comprovante | null> {
    const maxTentativas = 3;
    const intervaloRetry = 30000; // 30 segundos
    
    for (let tentativa = 1; tentativa <= maxTentativas; tentativa++) {
        log(`🔄 Tentativa ${tentativa}/${maxTentativas} - Buscando comprovante para CNPJ ${cnpj}, valor R$ ${valor.toFixed(2)}`);
        
        // Busca novos comprovantes na API
        const novosComprovantes = await buscarComprovanteTempoReal(cnpj);
        
        // Adiciona novos comprovantes ao cache (evita duplicatas)
        for (const novo of novosComprovantes) {
            const jaExiste = comprovantesRef.lista.some(existente => 
                normalizarCNPJ(existente.cnpj_fundo) === normalizarCNPJ(novo.cnpj_fundo) &&
                Math.abs(existente.valor - novo.valor) < 0.01
            );
            
            if (!jaExiste) {
                comprovantesRef.lista.push(novo);
                log(`➕ Novo comprovante adicionado ao cache: CNPJ ${novo.cnpj_fundo}, Valor R$ ${novo.valor.toFixed(2)}`);
            }
        }
        
        // Verifica se agora encontra o comprovante necessário
        const comprovante = buscarComprovantePorValorEBeneficiario(
            comprovantesRef.lista,
            cnpj,
            valor,
            beneficiario
        );
        
        if (comprovante) {
            log(`✅ Comprovante encontrado na tentativa ${tentativa}!`);
            return comprovante;
        }
        
        // Se não é a última tentativa, aguarda antes de tentar novamente
        if (tentativa < maxTentativas) {
            log(`⏳ Comprovante não encontrado. Aguardando ${intervaloRetry / 1000}s antes da próxima tentativa...`);
            await delay(intervaloRetry);
        }
    }
    
    log(`⏭️ Comprovante não encontrado após ${maxTentativas} tentativas - Pulando item`);
    return null;
}

// Intervalo de atualização de comprovantes (5 minutos)
const INTERVALO_ATUALIZACAO_COMPROVANTES = 5 * 60 * 1000; // 5 minutos em ms

// Sistema de logging em arquivo
let logBuffer = '';
const logFile = `execution_log_${new Date().toISOString().replace(/[:.]/g, '-')}.txt`;
const originalConsoleLog = console.log; // Salvar referência original

function log(message: string) {
    const timestamp = new Date().toLocaleTimeString('pt-BR');
    const logMessage = `[${timestamp}] ${message}`;
    originalConsoleLog(message); // Usar console.log original
    logBuffer += logMessage + '\n';
    
    // Salvar incrementalmente a cada 10 linhas
    if (logBuffer.split('\n').length % 10 === 0) {
        fs.appendFileSync(logFile, logBuffer);
        logBuffer = '';
    }
}

function saveLog() {
    if (logBuffer) {
        fs.appendFileSync(logFile, logBuffer);
        logBuffer = '';
    }
}

// Garantir salvamento ao finalizar
process.on('exit', saveLog);
process.on('SIGINT', () => {
    saveLog();
    process.exit();
});
process.on('uncaughtException', (err) => {
    log(`❌ ERRO NÃO CAPTURADO: ${err.message}`);
    log(`Stack: ${err.stack}`);
    saveLog();
    process.exit(1);
});

// Bancos que rodam direto sem verificar comprovante (aprovação direta)
const allowedBanks = [
    'UNAVANTI FIDC',
    'VIRTUS FIDC',
    'METROPOLITANA ATIVOS FIDC NP MULTISSETORIAL',
    'LU INVEST FIDC',
    'METROPOLITANO',
    'B4 TRUST',
    'J17',
    'WCAPITAL',
    'SILVER',
    'SDA',
    'FORCE',
    'FORCE CAPITAL FIDC',
    'B4 TRUST MULTISSETORIAL FIDC',
    'CL&AM CAPITAL BANK FIDC',
    'SILVER STONE FIDC MULTISSETORIAL'
];

/**
 * Carrega comprovantes do JSON gerado pelo Python
 */
function carregarComprovantes(): Comprovante[] {
    try {
        // Busca o arquivo mais recente de listagem
        const files = fs.readdirSync('.')
            .filter(f => f.startsWith('listagem_comprovantes_') && f.endsWith('.json'))
            .sort()
            .reverse();
        
        if (files.length === 0) {
            log('⚠️  Nenhum arquivo de comprovantes encontrado');
            return [];
        }
        
        const arquivoMaisRecente = files[0];
        log(`📂 Carregando comprovantes de: ${arquivoMaisRecente}`);
        
        const conteudo = fs.readFileSync(arquivoMaisRecente, 'utf-8');
        const comprovantes = JSON.parse(conteudo) as Comprovante[];
        
        log(`✅ ${comprovantes.length} comprovantes carregados`);
        return comprovantes;
    } catch (error) {
        console.error('❌ Erro ao carregar comprovantes:', error);
        return [];
    }
}

/**
 * Executa busca de comprovantes via Python em background
 * Retorna uma Promise que resolve quando o processo terminar
 */
function buscarComprovantesBackground(): Promise<void> {
    return new Promise((resolve, reject) => {
        log('🔄 Iniciando busca de comprovantes em background...');
        
        const processo = spawn('py', ['listar_comprovantes_santander.py'], {
            stdio: 'pipe', // Captura output
            shell: true
        });
        
        let output = '';
        let errorOutput = '';
        
        processo.stdout?.on('data', (data) => {
            output += data.toString();
        });
        
        processo.stderr?.on('data', (data) => {
            errorOutput += data.toString();
        });
        
        processo.on('close', (code) => {
            if (code === 0) {
                log('✅ Comprovantes atualizados com sucesso');
                resolve();
            } else {
                log(`❌ Erro ao buscar comprovantes (código ${code})`);
                if (errorOutput) log(`Erro: ${errorOutput}`);
                reject(new Error(`Processo terminou com código ${code}`));
            }
        });
        
        processo.on('error', (err) => {
            log(`❌ Erro ao executar busca de comprovantes: ${err.message}`);
            reject(err);
        });
    });
}

/**
 * Inicia loop de atualização automática de comprovantes
 * Atualiza a cada 5 minutos em background
 */
function iniciarAtualizacaoAutomatica(comprovantesRef: { lista: Comprovante[] }) {
    log(`⏰ Atualização automática configurada a cada ${INTERVALO_ATUALIZACAO_COMPROVANTES / 60000} minutos`);
    
    setInterval(async () => {
        try {
            log('');
            log('🔄 ========== ATUALIZAÇÃO AUTOMÁTICA DE COMPROVANTES ==========');
            await buscarComprovantesBackground();
            
            // Recarrega os comprovantes do arquivo atualizado
            const novosComprovantes = carregarComprovantes();
            comprovantesRef.lista = novosComprovantes;
            
            log(`✅ Lista atualizada: ${novosComprovantes.length} comprovantes disponíveis`);
            log('============================================================');
            log('');
        } catch (error) {
            log(`❌ Erro na atualização automática: ${error}`);
        }
    }, INTERVALO_ATUALIZACAO_COMPROVANTES);
}

/**
 * Verifica se deve processar a operação (COM BUSCA EM TEMPO REAL)
 */
async function deveProcessar(
    bankText: string,
    valorNumerico: number,
    beneficiario: string,
    comprovantesRef: { lista: Comprovante[] }
): Promise<{ processar: boolean; motivo: string }> {
    // 1. Verifica se é banco com aprovação direta
    if (allowedBanks.includes(bankText)) {
        return { processar: true, motivo: 'Banco na lista de aprovação direta' };
    }
    
    // 2. Verifica se é valor zero (aprovação direta)
    if (valorNumerico === 0) {
        return { processar: true, motivo: 'Valor zero' };
    }
    
    // 3. Verifica se tem comprovante Santander (apenas CNPJ + valor)
    const cnpj = obterCNPJPorNomeFundo(bankText);
    if (!cnpj) {
        return { processar: false, motivo: 'Fundo não mapeado para CNPJ Santander' };
    }
    
    // 4. Busca comprovante no cache (SEM retry em tempo real - comportamento original rápido)
    const comprovante = buscarComprovantePorValorEBeneficiario(comprovantesRef.lista, cnpj, valorNumerico, beneficiario);
    
    if (!comprovante) {
        return { processar: false, motivo: `Sem comprovante para CNPJ ${cnpj} e valor R$ ${valorNumerico.toFixed(2)}` };
    }
    
    return { processar: true, motivo: `Comprovante encontrado (CNPJ: ${cnpj}, Valor: R$ ${comprovante.valor.toFixed(2)})` };
}

/**
 * Obtém o número da página atual lendo o estado da paginação
 */
async function obterPaginaAtual(page: any): Promise<number> {
    try {
        // Procura pelo elemento span com classe 'rf-ds-act' (página ativa)
        const activePage = await page.$('span.rf-ds-nmb-btn.rf-ds-act');
        if (activePage) {
            const pageNumber = await page.evaluate(el => el.textContent?.trim(), activePage);
            const numero = parseInt(pageNumber || '1');
            log(`📍 Página atual detectada: ${numero}`);
            return numero;
        }
        
        log(`⚠️ Não foi possível detectar página atual, assumindo página 1`);
        return 1;
    } catch (error) {
        log(`❌ Erro ao detectar página atual: ${error}`);
        return 1;
    }
}

/**
 * Navega para uma página específica da tabela
 * Usa clique direto no link da página (ID: form:pagedDataTable:j_idt283_ds_N)
 */
async function navegarParaPagina(page: any, paginaDestino: number, paginaAtual: number) {
    if (paginaDestino === paginaAtual) {
        log(`✅ Já está na página ${paginaDestino}`);
        return;
    }

    log(`🔄 Navegando da página ${paginaAtual} para página ${paginaDestino}...`);

    try {
        // Método 1: Clicar no link direto da página usando o ID padrão
        // Padrão: form:pagedDataTable:j_idt283_ds_{numero}
        const pageId = `form\\:pagedDataTable\\:j_idt283_ds_${paginaDestino}`;
        const pageLink = await page.$(`a#${pageId}`);
        
        if (pageLink) {
            log(`👆 Clicando direto no link da página ${paginaDestino} (${pageId})`);
            await pageLink.click();
            await delay(2000);
            await page.waitForSelector('#form\\:pagedDataTable\\:tb');
            log(`✅ Navegação direta bem-sucedida`);
            return;
        }
        
        log(`⚠️ Link da página ${paginaDestino} não encontrado, tentando via texto...`);

        // Método 2: Procurar pelo texto do link (fallback)
        const pageLinks = await page.$$('a.rf-ds-nmb-btn');
        for (const link of pageLinks) {
            const linkText = await page.evaluate(el => el.textContent?.trim(), link);
            if (linkText === paginaDestino.toString()) {
                log(`👆 Clicando no link com texto "${paginaDestino}"`);
                await link.click();
                await delay(2000);
                await page.waitForSelector('#form\\:pagedDataTable\\:tb');
                log(`✅ Navegação por texto bem-sucedida`);
                return;
            }
        }

        // Método 3: Usar JavaScript para clicar (funciona mesmo se não visível)
        log(`🚀 Tentando navegação via JavaScript...`);
        const navegado = await page.evaluate((destino) => {
            // Tenta pelo ID padrão
            const linkById = document.getElementById(`form:pagedDataTable:j_idt283_ds_${destino}`) as any;
            if (linkById) {
                linkById.click();
                return true;
            }
            
            // Tenta procurar pelo texto
            const links = Array.from(document.querySelectorAll('a.rf-ds-nmb-btn'));
            const targetLink = links.find(link => link.textContent?.trim() === destino.toString()) as any;
            if (targetLink) {
                targetLink.click();
                return true;
            }
            
            return false;
        }, paginaDestino);

        if (navegado) {
            await delay(2000);
            await page.waitForSelector('#form\\:pagedDataTable\\:tb');
            log(`✅ Navegação via JavaScript bem-sucedida`);
            return;
        }

        // Método 4: Último recurso - navegação incremental
        log(`⚠️ Navegação direta falhou, usando navegação incremental...`);
        const navegarPraFrente = paginaDestino > paginaAtual;
        const passos = Math.abs(paginaDestino - paginaAtual);
        
        log(`${navegarPraFrente ? '▶️' : '◀️'} Navegando incrementalmente (${passos} páginas)...`);
        
        for (let i = 0; i < passos; i++) {
            const btnSelector = navegarPraFrente ? '.rf-ds-btn.rf-ds-btn-next' : '.rf-ds-btn.rf-ds-btn-prev';
            const btn = await page.$(btnSelector);
            
            if (btn) {
                const isDisabled = await page.evaluate(b => {
                    const el = b as any;
                    return el.disabled || el.classList.contains('rf-ds-btn-dis');
                }, btn);
                
                if (!isDisabled) {
                    await btn.click();
                    await delay(1000);
                }
            }
        }
        
        await page.waitForSelector('#form\\:pagedDataTable\\:tb');
        log(`✅ Navegação incremental concluída`);
        
    } catch (error) {
        log(`❌ Erro na navegação: ${error}`);
        log(`⚠️ Tentando continuar mesmo com erro...`);
    }
}

async function changeStatus() {
    const browser = await puppeteer.launch({ 
        headless: false,
        devtools: false, 
    });
    const page = await browser.pages().then(pages => pages[0]);

    // Carregar mapeamento de fundos do JSON
    carregarMapeamentoFundos();

    // Carregar comprovantes antes de começar
    const comprovantesRef = { lista: carregarComprovantes() };
    log(`\n${'='.repeat(80)}`);
    log(`COMPROVANTES CARREGADOS: ${comprovantesRef.lista.length}`);
    log(`${'='.repeat(80)}\n`);

    // Iniciar atualização automática em background
    iniciarAtualizacaoAutomatica(comprovantesRef);

    await page.goto("https://limine-custodia.fromtis.com/login.xhtml");
    await page.setViewport({width:1366, height: 768});
    await page.type('input[name="j_username"]', 'gustavop.kanastra');
    await page.type('input[name="j_password"]', 'limine25');
    await page.click('button');

    await page.waitForNavigation();
    
    await page.waitForSelector('#menuForm\\:j_idt128_itm');
    await page.hover('#menuForm\\:j_idt128_itm');
    
    await page.waitForSelector('#menuForm\\:j_idt131', { visible: true });
    await page.click('#menuForm\\:j_idt131');

    await page.waitForNavigation();

    await page.waitForSelector('select[id="form:situacao"]');
    
    await page.click('select[id="form:situacao"]');
    await page.click('option[value="AB"]');
    await page.click('.buscar');
 
    await page.waitForSelector('#form\\:pagedDataTable\\:tb');

    log('🔄 Iniciando processamento contínuo das páginas...');
    log('🔄 Cache será recarregado automaticamente a cada 15 itens processados');
    log('⚠️  Pressione Ctrl+C para parar a automação\n');
    
    let currentPage = 1;
    let globalItemIndex = 0;
    let processadosComComprovante = 0;
    let processadosAprovacaoDireta = 0;
    let pulados = 0;
    let ciclosCompletos = 0;
    let itensNaoEncontradosNaPagina = 0;
    let totalItensProcessados = 0; // NOVO: Contador de itens processados (com sucesso)
    const ITENS_PARA_RECARREGAR_CACHE = 15; // Recarrega cache a cada 15 itens processados
    
    // Loop infinito - apenas o usuário pode parar (Ctrl+C)
    while (true) {
        log(`\n📄 Processando página ${currentPage}...`);
        
        await page.waitForSelector('#form\\:pagedDataTable\\:tb');
        itensNaoEncontradosNaPagina = 0; // Resetar contador no início de cada página
        
        for (let pageRowIndex = 0; pageRowIndex <= 9; pageRowIndex++) {
            log(`\n📋 Processando item global ${globalItemIndex} (linha ${pageRowIndex} da página ${currentPage})...`);
            
            try {
                const bankSelector = `#form\\:pagedDataTable\\:${globalItemIndex}\\:j_idt261`;
                const bankElement = await page.$(bankSelector);
                if (!bankElement) {
                    log(`⏭️ Elemento não encontrado na linha ${globalItemIndex} - fim das linhas desta página`);
                    itensNaoEncontradosNaPagina++;
                    break;
                }
                
                const bankText = await page.evaluate(el => el?.textContent?.trim(), bankElement);
                log(`🏦 Banco encontrado: "${bankText}"`);
                
                const valueSelector = `#form\\:pagedDataTable\\:${globalItemIndex}\\:j_idt270`;
                const valueElement = await page.$(valueSelector);
                
                let valorNumerico = 0;
                if (valueElement) {
                    const valueText = await page.evaluate(el => el?.textContent?.trim(), valueElement);
                    log(`💰 Valor encontrado: "${valueText}"`);
                    valorNumerico = normalizarValor(valueText || '0');
                } else {
                    log(`❌ Elemento de valor não encontrado`);
                }
                
                // Extrair beneficiário (coluna j_idt267)
                const beneficiarioSelector = `#form\\:pagedDataTable\\:${globalItemIndex}\\:j_idt267`;
                const beneficiarioElement = await page.$(beneficiarioSelector);
                let beneficiario = '';
                if (beneficiarioElement) {
                    beneficiario = await page.evaluate(el => el?.textContent?.trim() || '', beneficiarioElement);
                    log(`👤 Beneficiário encontrado: "${beneficiario}"`);
                } else {
                    log(`⚠️  Elemento de beneficiário não encontrado`);
                }
                
                // Verifica se deve processar (COM BUSCA EM TEMPO REAL - usando await)
                const resultado = await deveProcessar(bankText || '', valorNumerico, beneficiario, comprovantesRef);
                
                if (resultado.processar) {
                    log(`✅ ${resultado.motivo} - Processando...`);
                    
                    // SALVAR página e índice antes de processar
                    const paginaSalva = currentPage;
                    const indiceSalvo = globalItemIndex;
                    
                    log(`💾 Salvando posição: Página ${paginaSalva}, Índice global ${indiceSalvo}`);
                    
                    // Rastrear tipo de processamento
                    if (resultado.motivo.includes('Comprovante encontrado')) {
                        processadosComComprovante++;
                    } else {
                        processadosAprovacaoDireta++;
                    }
                    
                    totalItensProcessados++; // NOVO: Incrementa contador de itens processados
                    
                    // NOVO: Verifica se deve recarregar cache
                    if (totalItensProcessados % ITENS_PARA_RECARREGAR_CACHE === 0) {
                        log(`\n🔄 Recarregando cache (${totalItensProcessados} itens processados)...`);
                        const cacheSizeAntes = comprovantesRef.lista.length;
                        comprovantesRef.lista = carregarComprovantes();
                        const cacheSizeDepois = comprovantesRef.lista.length;
                        log(`✅ Cache atualizado: ${cacheSizeAntes} → ${cacheSizeDepois} comprovantes (+${cacheSizeDepois - cacheSizeAntes})\n`);
                    }
                    
                    await delay(200);
                    
                    const detailsSelector = `td[id="form:pagedDataTable:${globalItemIndex}:j_idt279"]`;
                    log('🔍 Aguardando botão de detalhes...');
                    await page.waitForSelector(detailsSelector);
                    
                    log('👆 Clicando no botão de detalhes...');
                    await page.click(detailsSelector);
                    
                    log('🔧 Alterando situação para PAGO_PELO_BANCO_COBRADOR...');
                    await page.waitForSelector('select[id="form:situacaoAlterar"]');
                    await page.select('select[id="form:situacaoAlterar"]', 'PAGO_PELO_BANCO_COBRADOR');
                    
                    log('📝 Preenchendo justificativa...');
                    await page.waitForSelector('textarea[id="form:justificativa"]');
                    await page.type('textarea[id="form:justificativa"]', 'P');
                    
                    await page.waitForSelector('#form\\:j_idt298');
                    await page.click('#form\\:j_idt298');
                    
                    log('⏳ Aguardando navegação...');
                    await page.waitForNavigation();
                    
                    log('🔙 Voltando para a lista...');
                    await delay(200);
                    await page.click('.fechar');
                    log('🔍 Procurando elemento de controle do popup...');
                    await page.waitForSelector('div[id="form:popupAlteracaoStatus_header_controls"]');
                    log('✅ Elemento de controle do popup encontrado!');
                    log('👆 Clicando no elemento de controle do popup...');
                    await page.click('div[id="form:popupAlteracaoStatus_header_controls"]');
                    
                    log('⏳ Aguardando fechamento completo do popup...');
                    await delay(5000);
                    await page.waitForSelector('div[id="form:popupAlteracaoStatus_header_controls"]', { hidden: true });

                    // APÓS PROCESSAR: Volta para página 1 e depois retorna para a página salva
                    log(`🔄 Item processado! Sistema voltou para página 1`);
                    log(`📍 Retornando para página ${paginaSalva} para continuar de onde parou...`);
                    
                    // Detectar página atual após processamento (sempre será 1)
                    const paginaAtualAposProcessamento = await obterPaginaAtual(page);
                    await navegarParaPagina(page, paginaSalva, paginaAtualAposProcessamento);
                    
                    currentPage = paginaSalva;
                    globalItemIndex = indiceSalvo; // Continua do mesmo item
                    pageRowIndex = (indiceSalvo % 10) - 1; // Ajusta pageRowIndex para continuar na linha correta
                    
                    log(`✅ Continuando da página ${currentPage}, índice ${globalItemIndex}`);
                } else {
                    log(`⏭️  ${resultado.motivo} - Pulando`);
                    pulados++;
                }
                
                globalItemIndex++;
                
            } catch (error: any) {
                log(`❌ Erro no item global ${globalItemIndex} (linha ${pageRowIndex} da página ${currentPage}):`);
                log(`   Mensagem: ${error?.message || 'Erro desconhecido'}`);
                log(`   Stack: ${error?.stack || 'Sem stack trace'}`);
                saveLog(); // Salvar imediatamente em caso de erro
                globalItemIndex++;
            }
        }
        
        // Verificar próxima página ou voltar ao início
        try {
            // NOVO: Verificar se a página atual está vazia (primeiro item não encontrado significa página vazia)
            const paginaVazia = itensNaoEncontradosNaPagina > 0;
            
            if (paginaVazia) {
                // Página vazia detectada - significa que chegamos ao fim
                ciclosCompletos++;
                log(`\n${'='.repeat(80)}`);
                log(`✅ FIM DAS PÁGINAS DETECTADO (página ${currentPage} está vazia)`);
                log(`🔄 CICLO ${ciclosCompletos} COMPLETO - Voltando para página 1...`);
                log(`📊 Estatísticas deste ciclo:`);
                log(`   ✅ Processados com comprovante: ${processadosComComprovante}`);
                log(`   ✅ Processados por aprovação direta: ${processadosAprovacaoDireta}`);
                log(`   ⏭️  Pulados: ${pulados}`);
                log(`   📂 Comprovantes em cache: ${comprovantesRef.lista.length}`);
                log(`${'='.repeat(80)}\n`);
                
                const firstPageButton = await page.$('.rf-ds-btn.rf-ds-btn-first:not(.rf-ds-btn-dis)');
                if (firstPageButton) {
                    await firstPageButton.click();
                    await new Promise(resolve => setTimeout(resolve, 2000));
                    await page.waitForSelector('#form\\:pagedDataTable\\:tb');
                    currentPage = 1;
                    globalItemIndex = 0;
                } else {
                    log(`⏸️ Aguardando 3 segundos antes de tentar novamente...`);
                    await new Promise(resolve => setTimeout(resolve, 3000));
                }
                continue; // Reinicia o loop do while
            }
            
            log(`\n🔍 Verificando se existe próxima página...`);
            
            // Verificar se o botão próxima página está habilitado
            const nextPageEnabled = await page.evaluate(() => {
                const nextBtn = document.querySelector('.rf-ds-btn.rf-ds-btn-next');
                if (!nextBtn) return false;
                
                // Verificar múltiplas formas de desabilitação
                const hasDisabledClass = nextBtn.classList.contains('rf-ds-btn-dis') || 
                                        nextBtn.classList.contains('disabled');
                const hasDisabledAttr = (nextBtn as HTMLButtonElement).disabled;
                const hasAriaDisabled = nextBtn.getAttribute('aria-disabled') === 'true';
                const hasOpacity = window.getComputedStyle(nextBtn).opacity === '0.5';
                const hasPointerEvents = window.getComputedStyle(nextBtn).pointerEvents === 'none';
                
                return !hasDisabledClass && !hasDisabledAttr && !hasAriaDisabled && !hasOpacity && !hasPointerEvents;
            });
            
            if (nextPageEnabled) {
                log(`📄 Botão "próxima página" encontrado e habilitado - avançando para página ${currentPage + 1}...`);
                const nextPageButton = await page.$('.rf-ds-btn.rf-ds-btn-next');
                if (nextPageButton) {
                    await nextPageButton.click();
                    
                    await new Promise(resolve => setTimeout(resolve, 2000));
                    await page.waitForSelector('#form\\:pagedDataTable\\:tb');
                    
                    currentPage++;
                }
            } else {
                // Última página - voltar para a primeira
                ciclosCompletos++;
                log(`\n${'='.repeat(80)}`);
                log(`🔄 CICLO ${ciclosCompletos} COMPLETO - Voltando para página 1...`);
                log(`📊 Estatísticas deste ciclo:`);
                log(`   ✅ Processados com comprovante: ${processadosComComprovante}`);
                log(`   ✅ Processados por aprovação direta: ${processadosAprovacaoDireta}`);
                log(`   ⏭️  Pulados: ${pulados}`);
                log(`   📂 Comprovantes em cache: ${comprovantesRef.lista.length}`);
                log(`${'='.repeat(80)}\n`);
                
                const firstPageButton = await page.$('.rf-ds-btn.rf-ds-btn-first:not(.rf-ds-btn-dis)');
                if (firstPageButton) {
                    await firstPageButton.click();
                    await new Promise(resolve => setTimeout(resolve, 2000));
                    await page.waitForSelector('#form\\:pagedDataTable\\:tb');
                    currentPage = 1;
                    globalItemIndex = 0;
                } else {
                    log(`⏸️ Aguardando 3 segundos antes de tentar novamente...`);
                    await new Promise(resolve => setTimeout(resolve, 3000));
                }
            }
        } catch (error: any) {
            log(`⚠️ Erro ao navegar páginas: ${error?.message || 'Erro desconhecido'} - aguardando 3 segundos...`);
            await new Promise(resolve => setTimeout(resolve, 3000));
        }
    }
    
    // Este código nunca será executado pois o loop é infinito
    // A automação só para com Ctrl+C do usuário
    await browser.close();
    log(`🔒 Browser fechado com sucesso`);
}

changeStatus()
    .then(() => {
        log('✅ Automação finalizada com sucesso');
        saveLog();
        process.exit(0);
    })
    .catch((error) => {
        log(`❌ ERRO FATAL na automação: ${error.message}`);
        log(`Stack trace: ${error.stack}`);
        saveLog();
        process.exit(1);
    });
