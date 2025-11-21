"use strict";
var __awaiter = (this && this.__awaiter) || function (thisArg, _arguments, P, generator) {
    function adopt(value) { return value instanceof P ? value : new P(function (resolve) { resolve(value); }); }
    return new (P || (P = Promise))(function (resolve, reject) {
        function fulfilled(value) { try { step(generator.next(value)); } catch (e) { reject(e); } }
        function rejected(value) { try { step(generator["throw"](value)); } catch (e) { reject(e); } }
        function step(result) { result.done ? resolve(result.value) : adopt(result.value).then(fulfilled, rejected); }
        step((generator = generator.apply(thisArg, _arguments || [])).next());
    });
};
var __generator = (this && this.__generator) || function (thisArg, body) {
    var _ = { label: 0, sent: function() { if (t[0] & 1) throw t[1]; return t[1]; }, trys: [], ops: [] }, f, y, t, g = Object.create((typeof Iterator === "function" ? Iterator : Object).prototype);
    return g.next = verb(0), g["throw"] = verb(1), g["return"] = verb(2), typeof Symbol === "function" && (g[Symbol.iterator] = function() { return this; }), g;
    function verb(n) { return function (v) { return step([n, v]); }; }
    function step(op) {
        if (f) throw new TypeError("Generator is already executing.");
        while (g && (g = 0, op[0] && (_ = 0)), _) try {
            if (f = 1, y && (t = op[0] & 2 ? y["return"] : op[0] ? y["throw"] || ((t = y["return"]) && t.call(y), 0) : y.next) && !(t = t.call(y, op[1])).done) return t;
            if (y = 0, t) op = [op[0] & 2, t.value];
            switch (op[0]) {
                case 0: case 1: t = op; break;
                case 4: _.label++; return { value: op[1], done: false };
                case 5: _.label++; y = op[1]; op = [0]; continue;
                case 7: op = _.ops.pop(); _.trys.pop(); continue;
                default:
                    if (!(t = _.trys, t = t.length > 0 && t[t.length - 1]) && (op[0] === 6 || op[0] === 2)) { _ = 0; continue; }
                    if (op[0] === 3 && (!t || (op[1] > t[0] && op[1] < t[3]))) { _.label = op[1]; break; }
                    if (op[0] === 6 && _.label < t[1]) { _.label = t[1]; t = op; break; }
                    if (t && _.label < t[2]) { _.label = t[2]; _.ops.push(op); break; }
                    if (t[2]) _.ops.pop();
                    _.trys.pop(); continue;
            }
            op = body.call(thisArg, _);
        } catch (e) { op = [6, e]; y = 0; } finally { f = t = 0; }
        if (op[0] & 5) throw op[1]; return { value: op[0] ? op[1] : void 0, done: true };
    }
};
Object.defineProperty(exports, "__esModule", { value: true });
var puppeteer_1 = require("puppeteer");
var fs = require("fs");
var child_process_1 = require("child_process");
var delay = function (ms) { return new Promise(function (resolve) { return setTimeout(resolve, ms); }); };
// ============================================================
// CARREGAMENTO DE MAPEAMENTO DE FUNDOS
// ============================================================
var MAPEAMENTO_FUNDOS_LIMINE = {};
function carregarMapeamentoFundos() {
    try {
        var conteudo = fs.readFileSync('mapeamento_fundos_fromtis.json', 'utf-8');
        MAPEAMENTO_FUNDOS_LIMINE = JSON.parse(conteudo);
        log("\u2705 Mapeamento de fundos carregado: ".concat(Object.keys(MAPEAMENTO_FUNDOS_LIMINE).length, " fundos"));
    }
    catch (erro) {
        log("\u274C Erro ao carregar mapeamento de fundos: ".concat(erro));
        MAPEAMENTO_FUNDOS_LIMINE = {};
    }
}
// ============================================================
// FUNÇÕES DE NORMALIZAÇÃO E BUSCA
// ============================================================
/**
 * Normaliza nome do banco removendo acentos e convertendo para uppercase
 */
function normalizarNomeBanco(nome) {
    return nome
        .normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '')
        .toUpperCase()
        .trim();
}
/**
 * Normaliza CNPJ removendo pontuação
 */
function normalizarCNPJ(cnpj) {
    return cnpj.replace(/[^\d]/g, '');
}
/**
 * Normaliza valor monetário para número
 * Aceita formatos: "R$ 1.234,56", "1234.56", "1.234,56"
 */
function normalizarValor(valor) {
    // Remove "R$" e espaços
    var valorLimpo = valor.replace(/R\$\s*/g, '').trim();
    // Se tem vírgula, assume formato brasileiro (1.234,56)
    if (valorLimpo.includes(',')) {
        valorLimpo = valorLimpo.replace(/\./g, '').replace(',', '.');
    }
    return parseFloat(valorLimpo) || 0;
}
/**
 * Normaliza nome de pessoa/empresa para comparação
 */
function normalizarNome(nome) {
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
function obterCNPJPorNomeFundo(nomeFundo) {
    var nomeNormalizado = normalizarNomeBanco(nomeFundo);
    // Busca exata primeiro
    for (var _i = 0, _a = Object.entries(MAPEAMENTO_FUNDOS_LIMINE); _i < _a.length; _i++) {
        var _b = _a[_i], key = _b[0], cnpj = _b[1];
        if (normalizarNomeBanco(key) === nomeNormalizado) {
            return cnpj;
        }
    }
    // Busca parcial (contém)
    for (var _c = 0, _d = Object.entries(MAPEAMENTO_FUNDOS_LIMINE); _c < _d.length; _c++) {
        var _e = _d[_c], key = _e[0], cnpj = _e[1];
        var keyNormalizado = normalizarNomeBanco(key);
        if (keyNormalizado.includes(nomeNormalizado) || nomeNormalizado.includes(keyNormalizado)) {
            return cnpj;
        }
    }
    return null;
}
/**
 * Busca comprovante por CNPJ e valor (sem validação de beneficiário)
 */
function buscarComprovantePorValorEBeneficiario(comprovantes, cnpj, valor, beneficiario) {
    var cnpjNormalizado = normalizarCNPJ(cnpj);
    var toleranciaValor = 0.02;
    var candidato = comprovantes.find(function (comp) {
        var cnpjCompNormalizado = normalizarCNPJ(comp.cnpj_fundo);
        var diferencaValor = Math.abs(comp.valor - valor);
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
function buscarComprovanteTempoReal(cnpj) {
    return __awaiter(this, void 0, void 0, function () {
        var comprovantesBuscados, erro_1;
        return __generator(this, function (_a) {
            switch (_a.label) {
                case 0:
                    _a.trys.push([0, 2, , 3]);
                    log("\uD83D\uDD0D Buscando comprovante em tempo real para CNPJ ".concat(cnpj, "..."));
                    return [4 /*yield*/, new Promise(function (resolve, reject) {
                            var processo = (0, child_process_1.spawn)('python', [
                                'buscar_comprovante_fundo_especifico.py',
                                cnpj
                            ]);
                            var saida = '';
                            var erro = '';
                            processo.stdout.on('data', function (dados) {
                                saida += dados.toString();
                            });
                            processo.stderr.on('data', function (dados) {
                                erro += dados.toString();
                            });
                            processo.on('close', function (codigo) {
                                if (codigo !== 0) {
                                    log("\u26A0\uFE0F Erro ao buscar comprovante (c\u00F3digo ".concat(codigo, "): ").concat(erro));
                                    resolve([]);
                                    return;
                                }
                                try {
                                    // Espera JSON com lista de comprovantes
                                    var resultado = JSON.parse(saida);
                                    resolve(resultado.comprovantes || []);
                                }
                                catch (e) {
                                    log("\u26A0\uFE0F Erro ao parsear resposta da busca: ".concat(e));
                                    resolve([]);
                                }
                            });
                        })];
                case 1:
                    comprovantesBuscados = _a.sent();
                    if (comprovantesBuscados.length > 0) {
                        log("\u2705 Encontrados ".concat(comprovantesBuscados.length, " comprovante(s) em tempo real para CNPJ ").concat(cnpj));
                    }
                    else {
                        log("\u23ED\uFE0F Nenhum comprovante encontrado em tempo real para CNPJ ".concat(cnpj));
                    }
                    return [2 /*return*/, comprovantesBuscados];
                case 2:
                    erro_1 = _a.sent();
                    log("\u274C Erro na busca em tempo real: ".concat(erro_1));
                    return [2 /*return*/, []];
                case 3: return [2 /*return*/];
            }
        });
    });
}
/**
 * Busca comprovante com sistema de retry (até 3 tentativas com intervalo de 30s)
 * Atualiza o cache global de comprovantes quando encontra
 */
function buscarComprovanteComRetry(cnpj, valor, beneficiario, comprovantesRef) {
    return __awaiter(this, void 0, void 0, function () {
        var maxTentativas, intervaloRetry, tentativa, novosComprovantes, _loop_1, _i, novosComprovantes_1, novo, comprovante;
        return __generator(this, function (_a) {
            switch (_a.label) {
                case 0:
                    maxTentativas = 3;
                    intervaloRetry = 30000;
                    tentativa = 1;
                    _a.label = 1;
                case 1:
                    if (!(tentativa <= maxTentativas)) return [3 /*break*/, 5];
                    log("\uD83D\uDD04 Tentativa ".concat(tentativa, "/").concat(maxTentativas, " - Buscando comprovante para CNPJ ").concat(cnpj, ", valor R$ ").concat(valor.toFixed(2)));
                    return [4 /*yield*/, buscarComprovanteTempoReal(cnpj)];
                case 2:
                    novosComprovantes = _a.sent();
                    _loop_1 = function (novo) {
                        var jaExiste = comprovantesRef.lista.some(function (existente) {
                            return normalizarCNPJ(existente.cnpj_fundo) === normalizarCNPJ(novo.cnpj_fundo) &&
                                Math.abs(existente.valor - novo.valor) < 0.01;
                        });
                        if (!jaExiste) {
                            comprovantesRef.lista.push(novo);
                            log("\u2795 Novo comprovante adicionado ao cache: CNPJ ".concat(novo.cnpj_fundo, ", Valor R$ ").concat(novo.valor.toFixed(2)));
                        }
                    };
                    // Adiciona novos comprovantes ao cache (evita duplicatas)
                    for (_i = 0, novosComprovantes_1 = novosComprovantes; _i < novosComprovantes_1.length; _i++) {
                        novo = novosComprovantes_1[_i];
                        _loop_1(novo);
                    }
                    comprovante = buscarComprovantePorValorEBeneficiario(comprovantesRef.lista, cnpj, valor, beneficiario);
                    if (comprovante) {
                        log("\u2705 Comprovante encontrado na tentativa ".concat(tentativa, "!"));
                        return [2 /*return*/, comprovante];
                    }
                    if (!(tentativa < maxTentativas)) return [3 /*break*/, 4];
                    log("\u23F3 Comprovante n\u00E3o encontrado. Aguardando ".concat(intervaloRetry / 1000, "s antes da pr\u00F3xima tentativa..."));
                    return [4 /*yield*/, delay(intervaloRetry)];
                case 3:
                    _a.sent();
                    _a.label = 4;
                case 4:
                    tentativa++;
                    return [3 /*break*/, 1];
                case 5:
                    log("\u23ED\uFE0F Comprovante n\u00E3o encontrado ap\u00F3s ".concat(maxTentativas, " tentativas - Pulando item"));
                    return [2 /*return*/, null];
            }
        });
    });
}
// Intervalo de atualização de comprovantes (5 minutos)
var INTERVALO_ATUALIZACAO_COMPROVANTES = 5 * 60 * 1000; // 5 minutos em ms
// Sistema de logging em arquivo
var logBuffer = '';
var logFile = "execution_log_".concat(new Date().toISOString().replace(/[:.]/g, '-'), ".txt");
var originalConsoleLog = console.log; // Salvar referência original
function log(message) {
    var timestamp = new Date().toLocaleTimeString('pt-BR');
    var logMessage = "[".concat(timestamp, "] ").concat(message);
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
process.on('SIGINT', function () {
    saveLog();
    process.exit();
});
process.on('uncaughtException', function (err) {
    log("\u274C ERRO N\u00C3O CAPTURADO: ".concat(err.message));
    log("Stack: ".concat(err.stack));
    saveLog();
    process.exit(1);
});
// Bancos que rodam direto sem verificar comprovante (aprovação direta)
var allowedBanks = [
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
function carregarComprovantes() {
    try {
        // Busca o arquivo mais recente de listagem
        var files = fs.readdirSync('.')
            .filter(function (f) { return f.startsWith('listagem_comprovantes_') && f.endsWith('.json'); })
            .sort()
            .reverse();
        if (files.length === 0) {
            log('⚠️  Nenhum arquivo de comprovantes encontrado');
            return [];
        }
        var arquivoMaisRecente = files[0];
        log("\uD83D\uDCC2 Carregando comprovantes de: ".concat(arquivoMaisRecente));
        var conteudo = fs.readFileSync(arquivoMaisRecente, 'utf-8');
        var comprovantes = JSON.parse(conteudo);
        log("\u2705 ".concat(comprovantes.length, " comprovantes carregados"));
        return comprovantes;
    }
    catch (error) {
        console.error('❌ Erro ao carregar comprovantes:', error);
        return [];
    }
}
/**
 * Executa busca de comprovantes via Python em background
 * Retorna uma Promise que resolve quando o processo terminar
 */
function buscarComprovantesBackground() {
    return new Promise(function (resolve, reject) {
        var _a, _b;
        log('🔄 Iniciando busca de comprovantes em background...');
        var processo = (0, child_process_1.spawn)('py', ['listar_comprovantes_santander.py'], {
            stdio: 'pipe', // Captura output
            shell: true
        });
        var output = '';
        var errorOutput = '';
        (_a = processo.stdout) === null || _a === void 0 ? void 0 : _a.on('data', function (data) {
            output += data.toString();
        });
        (_b = processo.stderr) === null || _b === void 0 ? void 0 : _b.on('data', function (data) {
            errorOutput += data.toString();
        });
        processo.on('close', function (code) {
            if (code === 0) {
                log('✅ Comprovantes atualizados com sucesso');
                resolve();
            }
            else {
                log("\u274C Erro ao buscar comprovantes (c\u00F3digo ".concat(code, ")"));
                if (errorOutput)
                    log("Erro: ".concat(errorOutput));
                reject(new Error("Processo terminou com c\u00F3digo ".concat(code)));
            }
        });
        processo.on('error', function (err) {
            log("\u274C Erro ao executar busca de comprovantes: ".concat(err.message));
            reject(err);
        });
    });
}
/**
 * Inicia loop de atualização automática de comprovantes
 * Atualiza a cada 5 minutos em background
 */
function iniciarAtualizacaoAutomatica(comprovantesRef) {
    var _this = this;
    log("\u23F0 Atualiza\u00E7\u00E3o autom\u00E1tica configurada a cada ".concat(INTERVALO_ATUALIZACAO_COMPROVANTES / 60000, " minutos"));
    setInterval(function () { return __awaiter(_this, void 0, void 0, function () {
        var novosComprovantes, error_1;
        return __generator(this, function (_a) {
            switch (_a.label) {
                case 0:
                    _a.trys.push([0, 2, , 3]);
                    log('');
                    log('🔄 ========== ATUALIZAÇÃO AUTOMÁTICA DE COMPROVANTES ==========');
                    return [4 /*yield*/, buscarComprovantesBackground()];
                case 1:
                    _a.sent();
                    novosComprovantes = carregarComprovantes();
                    comprovantesRef.lista = novosComprovantes;
                    log("\u2705 Lista atualizada: ".concat(novosComprovantes.length, " comprovantes dispon\u00EDveis"));
                    log('============================================================');
                    log('');
                    return [3 /*break*/, 3];
                case 2:
                    error_1 = _a.sent();
                    log("\u274C Erro na atualiza\u00E7\u00E3o autom\u00E1tica: ".concat(error_1));
                    return [3 /*break*/, 3];
                case 3: return [2 /*return*/];
            }
        });
    }); }, INTERVALO_ATUALIZACAO_COMPROVANTES);
}
/**
 * Verifica se deve processar a operação (COM BUSCA EM TEMPO REAL)
 */
function deveProcessar(bankText, valorNumerico, beneficiario, comprovantesRef) {
    return __awaiter(this, void 0, void 0, function () {
        var cnpj, comprovante;
        return __generator(this, function (_a) {
            // 1. Verifica se é banco com aprovação direta
            if (allowedBanks.includes(bankText)) {
                return [2 /*return*/, { processar: true, motivo: 'Banco na lista de aprovação direta' }];
            }
            // 2. Verifica se é valor zero (aprovação direta)
            if (valorNumerico === 0) {
                return [2 /*return*/, { processar: true, motivo: 'Valor zero' }];
            }
            cnpj = obterCNPJPorNomeFundo(bankText);
            if (!cnpj) {
                return [2 /*return*/, { processar: false, motivo: 'Fundo não mapeado para CNPJ Santander' }];
            }
            comprovante = buscarComprovantePorValorEBeneficiario(comprovantesRef.lista, cnpj, valorNumerico, beneficiario);
            if (!comprovante) {
                return [2 /*return*/, { processar: false, motivo: "Sem comprovante para CNPJ ".concat(cnpj, " e valor R$ ").concat(valorNumerico.toFixed(2)) }];
            }
            return [2 /*return*/, { processar: true, motivo: "Comprovante encontrado (CNPJ: ".concat(cnpj, ", Valor: R$ ").concat(comprovante.valor.toFixed(2), ")") }];
        });
    });
}
/**
 * Obtém o número da página atual lendo o estado da paginação
 */
function obterPaginaAtual(page) {
    return __awaiter(this, void 0, void 0, function () {
        var activePage, pageNumber, numero, error_2;
        return __generator(this, function (_a) {
            switch (_a.label) {
                case 0:
                    _a.trys.push([0, 4, , 5]);
                    return [4 /*yield*/, page.$('span.rf-ds-nmb-btn.rf-ds-act')];
                case 1:
                    activePage = _a.sent();
                    if (!activePage) return [3 /*break*/, 3];
                    return [4 /*yield*/, page.evaluate(function (el) { var _a; return (_a = el.textContent) === null || _a === void 0 ? void 0 : _a.trim(); }, activePage)];
                case 2:
                    pageNumber = _a.sent();
                    numero = parseInt(pageNumber || '1');
                    log("\uD83D\uDCCD P\u00E1gina atual detectada: ".concat(numero));
                    return [2 /*return*/, numero];
                case 3:
                    log("\u26A0\uFE0F N\u00E3o foi poss\u00EDvel detectar p\u00E1gina atual, assumindo p\u00E1gina 1");
                    return [2 /*return*/, 1];
                case 4:
                    error_2 = _a.sent();
                    log("\u274C Erro ao detectar p\u00E1gina atual: ".concat(error_2));
                    return [2 /*return*/, 1];
                case 5: return [2 /*return*/];
            }
        });
    });
}
/**
 * Navega para uma página específica da tabela
 * Usa clique direto no link da página (ID: form:pagedDataTable:j_idt283_ds_N)
 */
function navegarParaPagina(page, paginaDestino, paginaAtual) {
    return __awaiter(this, void 0, void 0, function () {
        var pageId, pageLink, pageLinks, _i, pageLinks_1, link, linkText, navegado, navegarPraFrente, passos, i, btnSelector, btn, isDisabled, error_3;
        return __generator(this, function (_a) {
            switch (_a.label) {
                case 0:
                    if (paginaDestino === paginaAtual) {
                        log("\u2705 J\u00E1 est\u00E1 na p\u00E1gina ".concat(paginaDestino));
                        return [2 /*return*/];
                    }
                    log("\uD83D\uDD04 Navegando da p\u00E1gina ".concat(paginaAtual, " para p\u00E1gina ").concat(paginaDestino, "..."));
                    _a.label = 1;
                case 1:
                    _a.trys.push([1, 27, , 28]);
                    pageId = "form\\:pagedDataTable\\:j_idt283_ds_".concat(paginaDestino);
                    return [4 /*yield*/, page.$("a#".concat(pageId))];
                case 2:
                    pageLink = _a.sent();
                    if (!pageLink) return [3 /*break*/, 6];
                    log("\uD83D\uDC46 Clicando direto no link da p\u00E1gina ".concat(paginaDestino, " (").concat(pageId, ")"));
                    return [4 /*yield*/, pageLink.click()];
                case 3:
                    _a.sent();
                    return [4 /*yield*/, delay(2000)];
                case 4:
                    _a.sent();
                    return [4 /*yield*/, page.waitForSelector('#form\\:pagedDataTable\\:tb')];
                case 5:
                    _a.sent();
                    log("\u2705 Navega\u00E7\u00E3o direta bem-sucedida");
                    return [2 /*return*/];
                case 6:
                    log("\u26A0\uFE0F Link da p\u00E1gina ".concat(paginaDestino, " n\u00E3o encontrado, tentando via texto..."));
                    return [4 /*yield*/, page.$$('a.rf-ds-nmb-btn')];
                case 7:
                    pageLinks = _a.sent();
                    _i = 0, pageLinks_1 = pageLinks;
                    _a.label = 8;
                case 8:
                    if (!(_i < pageLinks_1.length)) return [3 /*break*/, 14];
                    link = pageLinks_1[_i];
                    return [4 /*yield*/, page.evaluate(function (el) { var _a; return (_a = el.textContent) === null || _a === void 0 ? void 0 : _a.trim(); }, link)];
                case 9:
                    linkText = _a.sent();
                    if (!(linkText === paginaDestino.toString())) return [3 /*break*/, 13];
                    log("\uD83D\uDC46 Clicando no link com texto \"".concat(paginaDestino, "\""));
                    return [4 /*yield*/, link.click()];
                case 10:
                    _a.sent();
                    return [4 /*yield*/, delay(2000)];
                case 11:
                    _a.sent();
                    return [4 /*yield*/, page.waitForSelector('#form\\:pagedDataTable\\:tb')];
                case 12:
                    _a.sent();
                    log("\u2705 Navega\u00E7\u00E3o por texto bem-sucedida");
                    return [2 /*return*/];
                case 13:
                    _i++;
                    return [3 /*break*/, 8];
                case 14:
                    // Método 3: Usar JavaScript para clicar (funciona mesmo se não visível)
                    log("\uD83D\uDE80 Tentando navega\u00E7\u00E3o via JavaScript...");
                    return [4 /*yield*/, page.evaluate(function (destino) {
                            // Tenta pelo ID padrão
                            var linkById = document.getElementById("form:pagedDataTable:j_idt283_ds_".concat(destino));
                            if (linkById) {
                                linkById.click();
                                return true;
                            }
                            // Tenta procurar pelo texto
                            var links = Array.from(document.querySelectorAll('a.rf-ds-nmb-btn'));
                            var targetLink = links.find(function (link) { var _a; return ((_a = link.textContent) === null || _a === void 0 ? void 0 : _a.trim()) === destino.toString(); });
                            if (targetLink) {
                                targetLink.click();
                                return true;
                            }
                            return false;
                        }, paginaDestino)];
                case 15:
                    navegado = _a.sent();
                    if (!navegado) return [3 /*break*/, 18];
                    return [4 /*yield*/, delay(2000)];
                case 16:
                    _a.sent();
                    return [4 /*yield*/, page.waitForSelector('#form\\:pagedDataTable\\:tb')];
                case 17:
                    _a.sent();
                    log("\u2705 Navega\u00E7\u00E3o via JavaScript bem-sucedida");
                    return [2 /*return*/];
                case 18:
                    // Método 4: Último recurso - navegação incremental
                    log("\u26A0\uFE0F Navega\u00E7\u00E3o direta falhou, usando navega\u00E7\u00E3o incremental...");
                    navegarPraFrente = paginaDestino > paginaAtual;
                    passos = Math.abs(paginaDestino - paginaAtual);
                    log("".concat(navegarPraFrente ? '▶️' : '◀️', " Navegando incrementalmente (").concat(passos, " p\u00E1ginas)..."));
                    i = 0;
                    _a.label = 19;
                case 19:
                    if (!(i < passos)) return [3 /*break*/, 25];
                    btnSelector = navegarPraFrente ? '.rf-ds-btn.rf-ds-btn-next' : '.rf-ds-btn.rf-ds-btn-prev';
                    return [4 /*yield*/, page.$(btnSelector)];
                case 20:
                    btn = _a.sent();
                    if (!btn) return [3 /*break*/, 24];
                    return [4 /*yield*/, page.evaluate(function (b) {
                            var el = b;
                            return el.disabled || el.classList.contains('rf-ds-btn-dis');
                        }, btn)];
                case 21:
                    isDisabled = _a.sent();
                    if (!!isDisabled) return [3 /*break*/, 24];
                    return [4 /*yield*/, btn.click()];
                case 22:
                    _a.sent();
                    return [4 /*yield*/, delay(1000)];
                case 23:
                    _a.sent();
                    _a.label = 24;
                case 24:
                    i++;
                    return [3 /*break*/, 19];
                case 25: return [4 /*yield*/, page.waitForSelector('#form\\:pagedDataTable\\:tb')];
                case 26:
                    _a.sent();
                    log("\u2705 Navega\u00E7\u00E3o incremental conclu\u00EDda");
                    return [3 /*break*/, 28];
                case 27:
                    error_3 = _a.sent();
                    log("\u274C Erro na navega\u00E7\u00E3o: ".concat(error_3));
                    log("\u26A0\uFE0F Tentando continuar mesmo com erro...");
                    return [3 /*break*/, 28];
                case 28: return [2 /*return*/];
            }
        });
    });
}
function changeStatus() {
    return __awaiter(this, void 0, void 0, function () {
        var browser, page, comprovantesRef, currentPage, globalItemIndex, processadosComComprovante, processadosAprovacaoDireta, pulados, ciclosCompletos, itensNaoEncontradosNaPagina, totalItensProcessados, ITENS_PARA_RECARREGAR_CACHE, pageRowIndex, bankSelector, bankElement, bankText, valueSelector, valueElement, valorNumerico, valueText, beneficiarioSelector, beneficiarioElement, beneficiario, resultado, paginaSalva, indiceSalvo, cacheSizeAntes, cacheSizeDepois, detailsSelector, paginaAtualAposProcessamento, error_4, paginaVazia, firstPageButton, nextPageEnabled, nextPageButton, firstPageButton, error_5;
        return __generator(this, function (_a) {
            switch (_a.label) {
                case 0: return [4 /*yield*/, puppeteer_1.default.launch({
                        headless: false,
                        devtools: false,
                    })];
                case 1:
                    browser = _a.sent();
                    return [4 /*yield*/, browser.pages().then(function (pages) { return pages[0]; })];
                case 2:
                    page = _a.sent();
                    // Carregar mapeamento de fundos do JSON
                    carregarMapeamentoFundos();
                    comprovantesRef = { lista: carregarComprovantes() };
                    log("\n".concat('='.repeat(80)));
                    log("COMPROVANTES CARREGADOS: ".concat(comprovantesRef.lista.length));
                    log("".concat('='.repeat(80), "\n"));
                    // Iniciar atualização automática em background
                    iniciarAtualizacaoAutomatica(comprovantesRef);
                    return [4 /*yield*/, page.goto("https://limine-custodia.fromtis.com/login.xhtml")];
                case 3:
                    _a.sent();
                    return [4 /*yield*/, page.setViewport({ width: 1366, height: 768 })];
                case 4:
                    _a.sent();
                    return [4 /*yield*/, page.type('input[name="j_username"]', 'gustavop.kanastra')];
                case 5:
                    _a.sent();
                    return [4 /*yield*/, page.type('input[name="j_password"]', 'limine25')];
                case 6:
                    _a.sent();
                    return [4 /*yield*/, page.click('button')];
                case 7:
                    _a.sent();
                    return [4 /*yield*/, page.waitForNavigation()];
                case 8:
                    _a.sent();
                    return [4 /*yield*/, page.waitForSelector('#menuForm\\:j_idt128_itm')];
                case 9:
                    _a.sent();
                    return [4 /*yield*/, page.hover('#menuForm\\:j_idt128_itm')];
                case 10:
                    _a.sent();
                    return [4 /*yield*/, page.waitForSelector('#menuForm\\:j_idt131', { visible: true })];
                case 11:
                    _a.sent();
                    return [4 /*yield*/, page.click('#menuForm\\:j_idt131')];
                case 12:
                    _a.sent();
                    return [4 /*yield*/, page.waitForNavigation()];
                case 13:
                    _a.sent();
                    return [4 /*yield*/, page.waitForSelector('select[id="form:situacao"]')];
                case 14:
                    _a.sent();
                    return [4 /*yield*/, page.click('select[id="form:situacao"]')];
                case 15:
                    _a.sent();
                    return [4 /*yield*/, page.click('option[value="AB"]')];
                case 16:
                    _a.sent();
                    return [4 /*yield*/, page.click('.buscar')];
                case 17:
                    _a.sent();
                    return [4 /*yield*/, page.waitForSelector('#form\\:pagedDataTable\\:tb')];
                case 18:
                    _a.sent();
                    log('🔄 Iniciando processamento contínuo das páginas...');
                    log('🔄 Cache será recarregado automaticamente a cada 15 itens processados');
                    log('⚠️  Pressione Ctrl+C para parar a automação\n');
                    currentPage = 1;
                    globalItemIndex = 0;
                    processadosComComprovante = 0;
                    processadosAprovacaoDireta = 0;
                    pulados = 0;
                    ciclosCompletos = 0;
                    itensNaoEncontradosNaPagina = 0;
                    totalItensProcessados = 0;
                    ITENS_PARA_RECARREGAR_CACHE = 15;
                    _a.label = 19;
                case 19:
                    if (!true) return [3 /*break*/, 82];
                    log("\n\uD83D\uDCC4 Processando p\u00E1gina ".concat(currentPage, "..."));
                    return [4 /*yield*/, page.waitForSelector('#form\\:pagedDataTable\\:tb')];
                case 20:
                    _a.sent();
                    itensNaoEncontradosNaPagina = 0; // Resetar contador no início de cada página
                    pageRowIndex = 0;
                    _a.label = 21;
                case 21:
                    if (!(pageRowIndex <= 9)) return [3 /*break*/, 56];
                    log("\n\uD83D\uDCCB Processando item global ".concat(globalItemIndex, " (linha ").concat(pageRowIndex, " da p\u00E1gina ").concat(currentPage, ")..."));
                    _a.label = 22;
                case 22:
                    _a.trys.push([22, 54, , 55]);
                    bankSelector = "#form\\:pagedDataTable\\:".concat(globalItemIndex, "\\:j_idt261");
                    return [4 /*yield*/, page.$(bankSelector)];
                case 23:
                    bankElement = _a.sent();
                    if (!bankElement) {
                        log("\u23ED\uFE0F Elemento n\u00E3o encontrado na linha ".concat(globalItemIndex, " - fim das linhas desta p\u00E1gina"));
                        itensNaoEncontradosNaPagina++;
                        return [3 /*break*/, 56];
                    }
                    return [4 /*yield*/, page.evaluate(function (el) { var _a; return (_a = el === null || el === void 0 ? void 0 : el.textContent) === null || _a === void 0 ? void 0 : _a.trim(); }, bankElement)];
                case 24:
                    bankText = _a.sent();
                    log("\uD83C\uDFE6 Banco encontrado: \"".concat(bankText, "\""));
                    valueSelector = "#form\\:pagedDataTable\\:".concat(globalItemIndex, "\\:j_idt270");
                    return [4 /*yield*/, page.$(valueSelector)];
                case 25:
                    valueElement = _a.sent();
                    valorNumerico = 0;
                    if (!valueElement) return [3 /*break*/, 27];
                    return [4 /*yield*/, page.evaluate(function (el) { var _a; return (_a = el === null || el === void 0 ? void 0 : el.textContent) === null || _a === void 0 ? void 0 : _a.trim(); }, valueElement)];
                case 26:
                    valueText = _a.sent();
                    log("\uD83D\uDCB0 Valor encontrado: \"".concat(valueText, "\""));
                    valorNumerico = normalizarValor(valueText || '0');
                    return [3 /*break*/, 28];
                case 27:
                    log("\u274C Elemento de valor n\u00E3o encontrado");
                    _a.label = 28;
                case 28:
                    beneficiarioSelector = "#form\\:pagedDataTable\\:".concat(globalItemIndex, "\\:j_idt267");
                    return [4 /*yield*/, page.$(beneficiarioSelector)];
                case 29:
                    beneficiarioElement = _a.sent();
                    beneficiario = '';
                    if (!beneficiarioElement) return [3 /*break*/, 31];
                    return [4 /*yield*/, page.evaluate(function (el) { var _a; return ((_a = el === null || el === void 0 ? void 0 : el.textContent) === null || _a === void 0 ? void 0 : _a.trim()) || ''; }, beneficiarioElement)];
                case 30:
                    beneficiario = _a.sent();
                    log("\uD83D\uDC64 Benefici\u00E1rio encontrado: \"".concat(beneficiario, "\""));
                    return [3 /*break*/, 32];
                case 31:
                    log("\u26A0\uFE0F  Elemento de benefici\u00E1rio n\u00E3o encontrado");
                    _a.label = 32;
                case 32: return [4 /*yield*/, deveProcessar(bankText || '', valorNumerico, beneficiario, comprovantesRef)];
                case 33:
                    resultado = _a.sent();
                    if (!resultado.processar) return [3 /*break*/, 52];
                    log("\u2705 ".concat(resultado.motivo, " - Processando..."));
                    paginaSalva = currentPage;
                    indiceSalvo = globalItemIndex;
                    log("\uD83D\uDCBE Salvando posi\u00E7\u00E3o: P\u00E1gina ".concat(paginaSalva, ", \u00CDndice global ").concat(indiceSalvo));
                    // Rastrear tipo de processamento
                    if (resultado.motivo.includes('Comprovante encontrado')) {
                        processadosComComprovante++;
                    }
                    else {
                        processadosAprovacaoDireta++;
                    }
                    totalItensProcessados++; // NOVO: Incrementa contador de itens processados
                    // NOVO: Verifica se deve recarregar cache
                    if (totalItensProcessados % ITENS_PARA_RECARREGAR_CACHE === 0) {
                        log("\n\uD83D\uDD04 Recarregando cache (".concat(totalItensProcessados, " itens processados)..."));
                        cacheSizeAntes = comprovantesRef.lista.length;
                        comprovantesRef.lista = carregarComprovantes();
                        cacheSizeDepois = comprovantesRef.lista.length;
                        log("\u2705 Cache atualizado: ".concat(cacheSizeAntes, " \u2192 ").concat(cacheSizeDepois, " comprovantes (+").concat(cacheSizeDepois - cacheSizeAntes, ")\n"));
                    }
                    return [4 /*yield*/, delay(200)];
                case 34:
                    _a.sent();
                    detailsSelector = "td[id=\"form:pagedDataTable:".concat(globalItemIndex, ":j_idt279\"]");
                    log('🔍 Aguardando botão de detalhes...');
                    return [4 /*yield*/, page.waitForSelector(detailsSelector)];
                case 35:
                    _a.sent();
                    log('👆 Clicando no botão de detalhes...');
                    return [4 /*yield*/, page.click(detailsSelector)];
                case 36:
                    _a.sent();
                    log('🔧 Alterando situação para PAGO_PELO_BANCO_COBRADOR...');
                    return [4 /*yield*/, page.waitForSelector('select[id="form:situacaoAlterar"]')];
                case 37:
                    _a.sent();
                    return [4 /*yield*/, page.select('select[id="form:situacaoAlterar"]', 'PAGO_PELO_BANCO_COBRADOR')];
                case 38:
                    _a.sent();
                    log('📝 Preenchendo justificativa...');
                    return [4 /*yield*/, page.waitForSelector('textarea[id="form:justificativa"]')];
                case 39:
                    _a.sent();
                    return [4 /*yield*/, page.type('textarea[id="form:justificativa"]', 'P')];
                case 40:
                    _a.sent();
                    return [4 /*yield*/, page.waitForSelector('#form\\:j_idt298')];
                case 41:
                    _a.sent();
                    return [4 /*yield*/, page.click('#form\\:j_idt298')];
                case 42:
                    _a.sent();
                    log('⏳ Aguardando navegação...');
                    return [4 /*yield*/, page.waitForNavigation()];
                case 43:
                    _a.sent();
                    log('🔙 Voltando para a lista...');
                    return [4 /*yield*/, delay(200)];
                case 44:
                    _a.sent();
                    return [4 /*yield*/, page.click('.fechar')];
                case 45:
                    _a.sent();
                    log('🔍 Procurando elemento de controle do popup...');
                    return [4 /*yield*/, page.waitForSelector('div[id="form:popupAlteracaoStatus_header_controls"]')];
                case 46:
                    _a.sent();
                    log('✅ Elemento de controle do popup encontrado!');
                    log('👆 Clicando no elemento de controle do popup...');
                    return [4 /*yield*/, page.click('div[id="form:popupAlteracaoStatus_header_controls"]')];
                case 47:
                    _a.sent();
                    log('⏳ Aguardando fechamento completo do popup...');
                    return [4 /*yield*/, delay(5000)];
                case 48:
                    _a.sent();
                    return [4 /*yield*/, page.waitForSelector('div[id="form:popupAlteracaoStatus_header_controls"]', { hidden: true })];
                case 49:
                    _a.sent();
                    // APÓS PROCESSAR: Volta para página 1 e depois retorna para a página salva
                    log("\uD83D\uDD04 Item processado! Sistema voltou para p\u00E1gina 1");
                    log("\uD83D\uDCCD Retornando para p\u00E1gina ".concat(paginaSalva, " para continuar de onde parou..."));
                    return [4 /*yield*/, obterPaginaAtual(page)];
                case 50:
                    paginaAtualAposProcessamento = _a.sent();
                    return [4 /*yield*/, navegarParaPagina(page, paginaSalva, paginaAtualAposProcessamento)];
                case 51:
                    _a.sent();
                    currentPage = paginaSalva;
                    globalItemIndex = indiceSalvo; // Continua do mesmo item
                    pageRowIndex = (indiceSalvo % 10) - 1; // Ajusta pageRowIndex para continuar na linha correta
                    log("\u2705 Continuando da p\u00E1gina ".concat(currentPage, ", \u00EDndice ").concat(globalItemIndex));
                    return [3 /*break*/, 53];
                case 52:
                    log("\u23ED\uFE0F  ".concat(resultado.motivo, " - Pulando"));
                    pulados++;
                    _a.label = 53;
                case 53:
                    globalItemIndex++;
                    return [3 /*break*/, 55];
                case 54:
                    error_4 = _a.sent();
                    log("\u274C Erro no item global ".concat(globalItemIndex, " (linha ").concat(pageRowIndex, " da p\u00E1gina ").concat(currentPage, "):"));
                    log("   Mensagem: ".concat((error_4 === null || error_4 === void 0 ? void 0 : error_4.message) || 'Erro desconhecido'));
                    log("   Stack: ".concat((error_4 === null || error_4 === void 0 ? void 0 : error_4.stack) || 'Sem stack trace'));
                    saveLog(); // Salvar imediatamente em caso de erro
                    globalItemIndex++;
                    return [3 /*break*/, 55];
                case 55:
                    pageRowIndex++;
                    return [3 /*break*/, 21];
                case 56:
                    _a.trys.push([56, 79, , 81]);
                    paginaVazia = itensNaoEncontradosNaPagina > 0;
                    if (!paginaVazia) return [3 /*break*/, 64];
                    // Página vazia detectada - significa que chegamos ao fim
                    ciclosCompletos++;
                    log("\n".concat('='.repeat(80)));
                    log("\u2705 FIM DAS P\u00C1GINAS DETECTADO (p\u00E1gina ".concat(currentPage, " est\u00E1 vazia)"));
                    log("\uD83D\uDD04 CICLO ".concat(ciclosCompletos, " COMPLETO - Voltando para p\u00E1gina 1..."));
                    log("\uD83D\uDCCA Estat\u00EDsticas deste ciclo:");
                    log("   \u2705 Processados com comprovante: ".concat(processadosComComprovante));
                    log("   \u2705 Processados por aprova\u00E7\u00E3o direta: ".concat(processadosAprovacaoDireta));
                    log("   \u23ED\uFE0F  Pulados: ".concat(pulados));
                    log("   \uD83D\uDCC2 Comprovantes em cache: ".concat(comprovantesRef.lista.length));
                    log("".concat('='.repeat(80), "\n"));
                    return [4 /*yield*/, page.$('.rf-ds-btn.rf-ds-btn-first:not(.rf-ds-btn-dis)')];
                case 57:
                    firstPageButton = _a.sent();
                    if (!firstPageButton) return [3 /*break*/, 61];
                    return [4 /*yield*/, firstPageButton.click()];
                case 58:
                    _a.sent();
                    return [4 /*yield*/, new Promise(function (resolve) { return setTimeout(resolve, 2000); })];
                case 59:
                    _a.sent();
                    return [4 /*yield*/, page.waitForSelector('#form\\:pagedDataTable\\:tb')];
                case 60:
                    _a.sent();
                    currentPage = 1;
                    globalItemIndex = 0;
                    return [3 /*break*/, 63];
                case 61:
                    log("\u23F8\uFE0F Aguardando 3 segundos antes de tentar novamente...");
                    return [4 /*yield*/, new Promise(function (resolve) { return setTimeout(resolve, 3000); })];
                case 62:
                    _a.sent();
                    _a.label = 63;
                case 63: return [3 /*break*/, 19]; // Reinicia o loop do while
                case 64:
                    log("\n\uD83D\uDD0D Verificando se existe pr\u00F3xima p\u00E1gina...");
                    return [4 /*yield*/, page.evaluate(function () {
                            var nextBtn = document.querySelector('.rf-ds-btn.rf-ds-btn-next');
                            if (!nextBtn)
                                return false;
                            // Verificar múltiplas formas de desabilitação
                            var hasDisabledClass = nextBtn.classList.contains('rf-ds-btn-dis') ||
                                nextBtn.classList.contains('disabled');
                            var hasDisabledAttr = nextBtn.disabled;
                            var hasAriaDisabled = nextBtn.getAttribute('aria-disabled') === 'true';
                            var hasOpacity = window.getComputedStyle(nextBtn).opacity === '0.5';
                            var hasPointerEvents = window.getComputedStyle(nextBtn).pointerEvents === 'none';
                            return !hasDisabledClass && !hasDisabledAttr && !hasAriaDisabled && !hasOpacity && !hasPointerEvents;
                        })];
                case 65:
                    nextPageEnabled = _a.sent();
                    if (!nextPageEnabled) return [3 /*break*/, 71];
                    log("\uD83D\uDCC4 Bot\u00E3o \"pr\u00F3xima p\u00E1gina\" encontrado e habilitado - avan\u00E7ando para p\u00E1gina ".concat(currentPage + 1, "..."));
                    return [4 /*yield*/, page.$('.rf-ds-btn.rf-ds-btn-next')];
                case 66:
                    nextPageButton = _a.sent();
                    if (!nextPageButton) return [3 /*break*/, 70];
                    return [4 /*yield*/, nextPageButton.click()];
                case 67:
                    _a.sent();
                    return [4 /*yield*/, new Promise(function (resolve) { return setTimeout(resolve, 2000); })];
                case 68:
                    _a.sent();
                    return [4 /*yield*/, page.waitForSelector('#form\\:pagedDataTable\\:tb')];
                case 69:
                    _a.sent();
                    currentPage++;
                    _a.label = 70;
                case 70: return [3 /*break*/, 78];
                case 71:
                    // Última página - voltar para a primeira
                    ciclosCompletos++;
                    log("\n".concat('='.repeat(80)));
                    log("\uD83D\uDD04 CICLO ".concat(ciclosCompletos, " COMPLETO - Voltando para p\u00E1gina 1..."));
                    log("\uD83D\uDCCA Estat\u00EDsticas deste ciclo:");
                    log("   \u2705 Processados com comprovante: ".concat(processadosComComprovante));
                    log("   \u2705 Processados por aprova\u00E7\u00E3o direta: ".concat(processadosAprovacaoDireta));
                    log("   \u23ED\uFE0F  Pulados: ".concat(pulados));
                    log("   \uD83D\uDCC2 Comprovantes em cache: ".concat(comprovantesRef.lista.length));
                    log("".concat('='.repeat(80), "\n"));
                    return [4 /*yield*/, page.$('.rf-ds-btn.rf-ds-btn-first:not(.rf-ds-btn-dis)')];
                case 72:
                    firstPageButton = _a.sent();
                    if (!firstPageButton) return [3 /*break*/, 76];
                    return [4 /*yield*/, firstPageButton.click()];
                case 73:
                    _a.sent();
                    return [4 /*yield*/, new Promise(function (resolve) { return setTimeout(resolve, 2000); })];
                case 74:
                    _a.sent();
                    return [4 /*yield*/, page.waitForSelector('#form\\:pagedDataTable\\:tb')];
                case 75:
                    _a.sent();
                    currentPage = 1;
                    globalItemIndex = 0;
                    return [3 /*break*/, 78];
                case 76:
                    log("\u23F8\uFE0F Aguardando 3 segundos antes de tentar novamente...");
                    return [4 /*yield*/, new Promise(function (resolve) { return setTimeout(resolve, 3000); })];
                case 77:
                    _a.sent();
                    _a.label = 78;
                case 78: return [3 /*break*/, 81];
                case 79:
                    error_5 = _a.sent();
                    log("\u26A0\uFE0F Erro ao navegar p\u00E1ginas: ".concat((error_5 === null || error_5 === void 0 ? void 0 : error_5.message) || 'Erro desconhecido', " - aguardando 3 segundos..."));
                    return [4 /*yield*/, new Promise(function (resolve) { return setTimeout(resolve, 3000); })];
                case 80:
                    _a.sent();
                    return [3 /*break*/, 81];
                case 81: return [3 /*break*/, 19];
                case 82: 
                // Este código nunca será executado pois o loop é infinito
                // A automação só para com Ctrl+C do usuário
                return [4 /*yield*/, browser.close()];
                case 83:
                    // Este código nunca será executado pois o loop é infinito
                    // A automação só para com Ctrl+C do usuário
                    _a.sent();
                    log("\uD83D\uDD12 Browser fechado com sucesso");
                    return [2 /*return*/];
            }
        });
    });
}
changeStatus()
    .then(function () {
    log('✅ Automação finalizada com sucesso');
    saveLog();
    process.exit(0);
})
    .catch(function (error) {
    log("\u274C ERRO FATAL na automa\u00E7\u00E3o: ".concat(error.message));
    log("Stack trace: ".concat(error.stack));
    saveLog();
    process.exit(1);
});
