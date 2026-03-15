/**
 * ProspectLocal — Servico WhatsApp (v2 - Estavel)
 * Usa Baileys para conectar numeros WA
 * Porta 3001 | Flask fica na 5000
 *
 * Melhorias v2:
 *  - Backoff exponencial na reconexao (evita loop 428)
 *  - Deduplicacao de mensagens recebidas
 *  - Tratamento de Bad MAC (sessao corrompida)
 *  - Retry automatico no envio
 *  - Logs organizados com timestamp
 */

const {
  default: makeWASocket,
  useMultiFileAuthState,
  DisconnectReason,
  fetchLatestBaileysVersion,
  fetchLatestWaWebVersion,
  Browsers,
} = require('baileys');

const express = require('express');
const cors = require('cors');
const path = require('path');
const fs = require('fs');
const QRCode = require('qrcode');
const P = require('pino');
const fetch = require('node-fetch');

const app = express();
app.use(cors());
app.use(express.json({ limit: '50mb' }));

const SESSIONS_DIR = path.join(__dirname, 'sessions');
const FLASK_URL = 'http://localhost:5000';

if (!fs.existsSync(SESSIONS_DIR)) {
  fs.mkdirSync(SESSIONS_DIR, { recursive: true });
}

// ─────────────────────────────────────────────────────────────────────────────
// ESTADO GLOBAL
// ─────────────────────────────────────────────────────────────────────────────
const connections = {};

// ─────────────────────────────────────────────────────────────────────────────
// LOGGER com timestamp
// ─────────────────────────────────────────────────────────────────────────────
function log(numId, msg) {
  const ts = new Date().toLocaleTimeString('pt-BR');
  console.log('[' + ts + '][' + numId + '] ' + msg);
}
function logErr(numId, msg) {
  const ts = new Date().toLocaleTimeString('pt-BR');
  console.error('[' + ts + '][' + numId + '] ERRO: ' + msg);
}

// ─────────────────────────────────────────────────────────────────────────────
// HELPERS — chamar Flask API (com retry)
// ─────────────────────────────────────────────────────────────────────────────
async function flaskGet(urlPath) {
  try {
    const r = await fetch(FLASK_URL + urlPath, { timeout: 8000 });
    if (!r.ok) return null;
    return await r.json();
  } catch (e) {
    console.error('[Flask] GET ' + urlPath + ': ' + e.message);
    return null;
  }
}

async function flaskPost(urlPath, body, retries = 1) {
  for (let i = 0; i <= retries; i++) {
    try {
      const r = await fetch(FLASK_URL + urlPath, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
        timeout: 8000,
      });
      const text = await r.text();
      try { return JSON.parse(text); } catch (_) {
        console.error('[Flask] POST ' + urlPath + ' retornou HTML (erro Flask). Status: ' + r.status);
        return null;
      }
    } catch (e) {
      if (i < retries) { await sleep(1000); continue; }
      console.error('[Flask] POST ' + urlPath + ': ' + e.message);
      return null;
    }
  }
}

async function flaskPut(urlPath, body) {
  try {
    const r = await fetch(FLASK_URL + urlPath, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      timeout: 8000,
    });
    const text = await r.text();
    try { return JSON.parse(text); } catch (_) { return null; }
  } catch (e) {
    console.error('[Flask] PUT ' + urlPath + ': ' + e.message);
    return null;
  }
}

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

function preferirNonoDigitoPorDdd(numero55) {
  if (!numero55 || !numero55.startsWith('55') || numero55.length < 12) return numero55;
  const ddd = parseInt(numero55.slice(2, 4), 10);
  if (!Number.isFinite(ddd)) return numero55;

  // Heuristica inicial: DDDs 11-28 tendem a operar com 9 no identificador.
  if (ddd >= 11 && ddd <= 28) {
    if (numero55.length === 12) return numero55.slice(0, 4) + '9' + numero55.slice(4);
    return numero55;
  }

  // Demais DDDs: priorizar sem 9, mas mantendo fallback dinamico.
  if (numero55.length === 13) return numero55.slice(0, 4) + numero55.slice(5);
  return numero55;
}

function normalizarTelefonesBR(telefone) {
  const tel = String(telefone || '').replace(/\D/g, '');
  if (!tel) return [];

  const com55Base = tel.startsWith('55') ? tel : ('55' + tel);
  const prioritario = preferirNonoDigitoPorDdd(com55Base);
  const variacoes = new Set([prioritario, com55Base, tel]);

  // 55 + DDD + 9 + numero(8) => tenta sem o 9
  if (com55Base.length === 13 && com55Base.startsWith('55')) {
    variacoes.add(com55Base.slice(0, 4) + com55Base.slice(5));
  }

  // 55 + DDD + numero(8) => tenta com o 9
  if (com55Base.length === 12 && com55Base.startsWith('55')) {
    variacoes.add(com55Base.slice(0, 4) + '9' + com55Base.slice(4));
  }

  for (const n of [...variacoes]) {
    if (n.startsWith('55')) variacoes.add(n.slice(2));
  }

  return [...variacoes].filter(Boolean);
}

async function resolverJidsWhatsApp(sock, telefone) {
  const candidatos = normalizarTelefonesBR(telefone);
  const jids = new Set();
  const detalhes = [];

  for (const numero of candidatos) {
    try {
      const consultas = await sock.onWhatsApp(numero) || [];
      for (const item of consultas) {
        if (item?.jid) {
          jids.add(item.jid);
          detalhes.push({ numero, jid: item.jid, fonte: 'onWhatsApp' });
        }
      }
    } catch (_) {}

    if (numero.startsWith('55')) {
      const jid = numero + '@s.whatsapp.net';
      jids.add(jid);
      detalhes.push({ numero, jid, fonte: 'fallback55' });
    } else {
      const jid55 = '55' + numero + '@s.whatsapp.net';
      const jidDireto = numero + '@s.whatsapp.net';
      jids.add(jid55);
      jids.add(jidDireto);
      detalhes.push({ numero, jid: jid55, fonte: 'fallback55' });
      detalhes.push({ numero, jid: jidDireto, fonte: 'fallbackDireto' });
    }
  }

  return {
    candidatos,
    jids: [...jids],
    detalhes,
    prioritario: candidatos[0] || null,
  };
}

async function enviarTextoComFallback(sock, telefone, texto) {
  const resolucao = await resolverJidsWhatsApp(sock, telefone);
  const jids = resolucao.jids;
  let ultimoErro = null;

  for (const jid of jids) {
    try {
      const resultado = await sock.sendMessage(jid, { text: texto });
      const detalhe = resolucao.detalhes.find(d => d.jid === jid) || null;
      return { resultado, jid, detalhe, candidatos: resolucao.candidatos, prioritario: resolucao.prioritario };
    } catch (e) {
      ultimoErro = e;
    }
  }

  if (ultimoErro) throw ultimoErro;
  throw new Error('Nenhum JID valido encontrado para envio');
}

async function enviarQuickReplyComFallback(sock, telefone, texto, footer, buttons) {
  const resolucao = await resolverJidsWhatsApp(sock, telefone);
  const jids = resolucao.jids;
  let ultimoErro = null;

  const botoesNormalizados = (Array.isArray(buttons) ? buttons : [])
    .map((btn, idx) => ({
      type: 'reply',
      id: String(btn?.id || `btn_${idx + 1}`).trim(),
      text: String(btn?.text || '').trim(),
    }))
    .filter(btn => btn.id && btn.text)
    .slice(0, 3);

  if (!texto || !botoesNormalizados.length) {
    throw new Error('Texto e pelo menos um botao sao obrigatorios');
  }

  for (const jid of jids) {
    try {
      const resultado = await sock.sendMessage(jid, {
        text: String(texto).trim(),
        footer: footer ? String(footer).trim() : undefined,
        nativeButtons: botoesNormalizados,
      });
      const detalhe = resolucao.detalhes.find(d => d.jid === jid) || null;
      return { resultado, jid, detalhe, candidatos: resolucao.candidatos, prioritario: resolucao.prioritario };
    } catch (e) {
      ultimoErro = e;
    }
  }

  if (ultimoErro) throw ultimoErro;
  throw new Error('Nenhum JID valido encontrado para envio de quick reply');
}

function extrairTextoInterativo(message) {
  const paramsJson = message?.interactiveResponseMessage?.nativeFlowResponseMessage?.paramsJson;
  if (!paramsJson) return '';

  try {
    const params = JSON.parse(paramsJson);
    const buttonId = String(
      params?.id ||
      params?.button_id ||
      params?.buttonId ||
      ''
    ).trim();
    const displayText = String(
      params?.display_text ||
      params?.displayText ||
      params?.title ||
      params?.text ||
      ''
    ).trim();

    if (buttonId === 'fu_sair' || buttonId === 'fu_depois') {
      return buttonId;
    }

    return displayText || buttonId;
  } catch (_) {
    return '';
  }
}

async function obterPrincipalQuickReplyConfig() {
  const padrao = {
    footer: 'Toque em uma opcao abaixo',
    buttons: [
      { id: 'fu_responder', text: '✅ Quero ver' },
      { id: 'fu_depois', text: '⏰ Depois' },
      { id: 'fu_sair', text: '🚫 Nao tenho interesse' },
    ],
  };

  try {
    const cfg = await flaskGet('/api/wa-quick-reply-config');
    const buttons = Array.isArray(cfg?.buttons) ? cfg.buttons : [];
    return {
      footer: String(cfg?.footer || padrao.footer).trim() || padrao.footer,
      buttons: padrao.buttons.map((btn, idx) => ({
        id: btn.id,
        text: String(buttons[idx]?.text || btn.text).trim() || btn.text,
      })),
    };
  } catch (_) {
    return padrao;
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// CONEXAO BAILEYS
// ─────────────────────────────────────────────────────────────────────────────
async function enviarTesteInterativo(socket, tel, mensagemFallback) {
  const info = await enviarQuickReplyComFallback(
    socket,
    tel,
    mensagemFallback,
    'Clique em uma opcao abaixo',
    [
      { id: 'teste_ok', text: '✅ Recebi' },
      { id: 'teste_depois', text: '⏰ Depois' },
      { id: 'teste_sair', text: '🚫 Sair' },
    ]
  );
  console.log('[Teste Botoes] ✅ nativeFlow quick_reply enviado para ' + tel + ' | jid=' + info.jid);
  return { ...info, comBotoes: true, tipo: 'buttons' };
}

async function conectar(numeroId) {
  // Limpar timer anterior
  if (connections[numeroId]?.reconnectTimer) {
    clearTimeout(connections[numeroId].reconnectTimer);
  }

  const sessionDir = path.join(SESSIONS_DIR, numeroId);
  if (!fs.existsSync(sessionDir)) {
    fs.mkdirSync(sessionDir, { recursive: true });
  }

  const { state, saveCreds } = await useMultiFileAuthState(sessionDir);
  // Igual ao projeto exemplo: fetchLatestWaWebVersion busca a versão real do WA Web
  // Isso é fundamental para que mensagens interativas (botões, listas) sejam aceitas
  let version;
  try {
    ({ version } = await fetchLatestWaWebVersion());
    log(numeroId, 'Versão WA Web obtida: ' + version.join('.'));
  } catch (_) {
    try {
      ({ version } = await fetchLatestBaileysVersion());
    } catch (__) {
      version = [2, 3000, 1032884366]; // fallback estático
    }
  }
  const logger = P({ level: 'silent' });

  const sock = makeWASocket({
    version,
    auth: state,
    printQRInTerminal: false,
    logger,
    browser: Browsers.windows('Chrome'), // igual ao exemplo — Windows + Chrome reconhecido pelo WA
    generateHighQualityLinkPreview: false,
    syncFullHistory: false,
    getMessage: async (key) => ({ conversation: '' }),
  });

  // Preservar lidMap de conexao anterior
  const lidMap = connections[numeroId]?.lidMap || {};
  const badMacCount = connections[numeroId]?.badMacCount || 0;

  connections[numeroId] = {
    socket: sock,
    status: 'connecting',
    qr: null,
    phone: null,
    reconnectTimer: null,
    reconnectAttempt: 0,     // backoff exponencial
    sentIds: new Set(),       // IDs de msgs enviadas (anti-eco)
    processedIds: new Set(),  // IDs de msgs ja processadas (anti-duplicata)
    lidMap,                   // LID -> telefone
    badMacCount,              // contador de erros Bad MAC
  };

  // ── EVENTO: Conexao ──
  sock.ev.on('connection.update', async (update) => {
    const { connection, lastDisconnect, qr } = update;
    const conn = connections[numeroId];
    if (!conn) return;

    if (qr) {
      try {
        conn.qr = await QRCode.toDataURL(qr, { width: 280 });
        conn.status = 'qr_code';
        conn.reconnectAttempt = 0; // resetar backoff
        log(numeroId, 'QR gerado — escaneie com o WhatsApp!');
        await flaskPut('/api/wa-numeros/status', { numero_id: numeroId, status: 'qr_code' });
      } catch (e) {
        logErr(numeroId, 'Erro QR: ' + e.message);
      }
    }

    if (connection === 'close') {
      const code = lastDisconnect?.error?.output?.statusCode;
      const loggedOut = code === DisconnectReason.loggedOut;

      if (loggedOut) {
        log(numeroId, 'Deslogado — removendo sessao.');
        if (fs.existsSync(sessionDir)) fs.rmSync(sessionDir, { recursive: true, force: true });
        conn.status = 'disconnected';
        conn.qr = null;
        await flaskPut('/api/wa-numeros/status', { numero_id: numeroId, status: 'disconnected' });
        delete connections[numeroId];
        return;
      }

      // Backoff exponencial: 3s, 6s, 12s, 24s, max 60s
      conn.reconnectAttempt = Math.min((conn.reconnectAttempt || 0) + 1, 6);
      const delay = Math.min(3000 * Math.pow(2, conn.reconnectAttempt - 1), 60000);
      conn.status = 'reconnecting';
      conn.qr = null;
      log(numeroId, 'Desconectado (codigo: ' + code + '). Reconectando em ' + (delay / 1000) + 's... (tentativa ' + conn.reconnectAttempt + ')');
      await flaskPut('/api/wa-numeros/status', { numero_id: numeroId, status: 'reconnecting' });
      conn.reconnectTimer = setTimeout(() => conectar(numeroId), delay);
    }

    if (connection === 'open') {
      conn.status = 'connected';
      conn.qr = null;
      conn.reconnectAttempt = 0; // resetar backoff
      conn.badMacCount = 0;       // resetar Bad MAC
      const phone = sock.user?.id?.split(':')[0] || sock.user?.id?.split('@')[0] || '';
      conn.phone = phone;
      log(numeroId, 'Conectado! Telefone: ' + phone);
      await flaskPut('/api/wa-numeros/status', { numero_id: numeroId, status: 'connected', telefone: phone });
    }
  });

  sock.ev.on('creds.update', saveCreds);

  // ── EVENTO: Contatos (mapeamento LID) ──
  sock.ev.on('contacts.upsert', (contacts) => {
    const conn = connections[numeroId];
    if (!conn) return;
    for (const c of contacts) {
      if (c.lid && c.id) {
        conn.lidMap[c.lid] = c.id;
        log(numeroId, 'Contato mapeado: ' + c.lid + ' => ' + c.id);
      }
    }
  });

  sock.ev.on('contacts.update', (updates) => {
    const conn = connections[numeroId];
    if (!conn) return;
    for (const c of updates) {
      if (c.lid && c.id) conn.lidMap[c.lid] = c.id;
    }
  });

  // ── EVENTO: Mensagens recebidas ──
  sock.ev.on('messages.upsert', async ({ messages, type }) => {
    for (const msg of messages) {
      const jid = msg.key.remoteJid || '';
      const fromMe = msg.key.fromMe;
      const msgId = msg.key.id || '';
      const conn = connections[numeroId];
      if (!conn) continue;

      // === FILTRO 1: Ignorar proprias ===
      if (fromMe) continue;

      // === FILTRO 2: Anti-eco (msgs que nós enviamos) ===
      if (conn.sentIds.has(msgId)) {
        conn.sentIds.delete(msgId);
        continue;
      }

      // === FILTRO 3: Anti-duplicata (msg ja processada) ===
      if (conn.processedIds.has(msgId)) continue;

      // === FILTRO 4: Apenas chats individuais (@s.whatsapp.net ou @lid) ===
      const isPhoneJid = jid.endsWith('@s.whatsapp.net');
      const isLidJid = jid.endsWith('@lid');
      if (!isPhoneJid && !isLidJid) continue;

      // === FILTRO 5: Sem conteudo = Bad MAC ===
      if (!msg.message) {
        conn.badMacCount = (conn.badMacCount || 0) + 1;
        if (conn.badMacCount <= 3) {
          log(numeroId, 'Msg sem conteudo (Bad MAC #' + conn.badMacCount + ') de ' + jid);
        }
        if (conn.badMacCount === 10) {
          log(numeroId, '⚠ Muitos erros Bad MAC! Recomendado: execute RESETAR SESSAO WA.bat');
        }
        continue;
      }

      // Marcar como processada (evita duplicatas)
      conn.processedIds.add(msgId);
      // Limpar IDs antigos (manter max 200)
      if (conn.processedIds.size > 200) {
        const arr = [...conn.processedIds];
        conn.processedIds = new Set(arr.slice(-100));
      }

      // === Resolver LID ===
      let resolvedJid = jid;
      if (isLidJid) {
        if (conn.lidMap[jid]) {
          resolvedJid = conn.lidMap[jid];
          log(numeroId, 'LID resolvido: ' + jid + ' => ' + resolvedJid);
          flaskPost('/api/kanban/mapear-lid', { lid: jid, telefone: resolvedJid.replace(/@s\.whatsapp\.net$/, '') });
        } else {
          log(numeroId, 'LID novo (Flask vai resolver): ' + jid);
        }
      }

      // === Extrair texto ===
      const text =
        msg.message?.conversation ||
        msg.message?.extendedTextMessage?.text ||
        msg.message?.imageMessage?.caption ||
        msg.message?.videoMessage?.caption ||
        msg.message?.buttonsResponseMessage?.selectedDisplayText ||
        msg.message?.listResponseMessage?.title ||
        msg.message?.templateButtonReplyMessage?.selectedDisplayText ||
        extrairTextoInterativo(msg.message) ||
        '[midia]';

      const from = resolvedJid.replace(/@s\.whatsapp\.net$|@lid$/, '');
      log(numeroId, '<< Recebido de ' + from + ': ' + text.substring(0, 80));

      // Marcar como lida
      try { await sock.readMessages([msg.key]); } catch (_) {}

      // Enviar para Flask
      const resultado = await flaskPost('/api/kanban/mensagem-recebida', {
        telefone: from,
        texto: text,
        numero_wa_id: numeroId,
      }, 2); // 2 retries
      log(numeroId, 'Flask: ' + JSON.stringify(resultado));

      // ── AUTO-REPLY: Se Flask retornou mensagem automática, enviar ──
      if (resultado && resultado.auto_reply && resultado.telefone) {
        const delayMs = 3000 + Math.random() * 4000; // 3-7s delay humano
        log(numeroId, '[AutoReply] Aguardando ' + Math.round(delayMs/1000) + 's antes de enviar...');

        setTimeout(async () => {
          try {
            const tel = resultado.telefone.replace(/\D/g, '');
            const envioInfo = await enviarTextoComFallback(sock, tel, resultado.auto_reply);
            const { resultado: envio, jid, detalhe, prioritario } = envioInfo;

            // Registrar ID para anti-eco
            if (envio?.key?.id) {
              conn.sentIds.add(envio.key.id);
              setTimeout(() => conn.sentIds.delete(envio.key.id), 60000);
            }

            log(
              numeroId,
              '[AutoReply] >> Enviado para ' + tel +
              ' | prioritario=' + (prioritario || '-') +
              ' | usado=' + (detalhe?.numero || '-') +
              ' | jid=' + jid +
              (resultado.nova_coluna ? ' (coluna: ' + resultado.nova_coluna + ')' : '')
            );

            // Registrar no Flask como mensagem enviada
            await flaskPost('/api/kanban/mensagem-enviada', {
              contato_id: resultado.contato_id,
              texto: resultado.auto_reply,
              numero_wa_id: numeroId,
              template_nome: 'Auto-reply',
              contexto_envio: 'auto_reply',
              tipo_envio: 'text',
            });
          } catch (e) {
            logErr(numeroId, '[AutoReply] Falha ao enviar auto-reply: ' + e.message);
          }
        }, delayMs);
      }
    }
  });

  return sock;
}

// ─────────────────────────────────────────────────────────────────────────────
// AUTO-RECONEXAO NA INICIALIZACAO
// ─────────────────────────────────────────────────────────────────────────────
async function autoConnect() {
  let flaskOk = false;
  for (let i = 0; i < 10; i++) {
    try {
      const r = await fetch(FLASK_URL + '/api/wa-numeros', { timeout: 3000 });
      if (r.ok) { flaskOk = true; break; }
    } catch (_) {}
    console.log('[autoconnect] Aguardando Flask... (' + (i + 1) + '/10)');
    await sleep(2000);
  }

  if (!flaskOk) {
    console.log('[autoconnect] Flask nao encontrado. Inicie INICIAR AQUI.bat tambem.');
    return;
  }

  const numeros = await flaskGet('/api/wa-numeros');
  if (!numeros || !numeros.length) return;

  for (const num of numeros) {
    const sessionDir = path.join(SESSIONS_DIR, num.numero_id);
    if (fs.existsSync(path.join(sessionDir, 'creds.json'))) {
      log(num.numero_id, 'Reconectando: ' + num.nome);
      await conectar(num.numero_id);
      await sleep(2000);
    }
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// API ROUTES
// ─────────────────────────────────────────────────────────────────────────────

app.get('/api/ping', (req, res) => {
  res.json({ ok: true, servico: 'ProspectLocal WhatsApp v2', connections: Object.keys(connections).length });
});

app.get('/api/status', (req, res) => {
  const statuses = {};
  for (const [id, conn] of Object.entries(connections)) {
    statuses[id] = {
      status: conn.status,
      phone: conn.phone,
      hasQr: !!conn.qr,
      reconnectAttempt: conn.reconnectAttempt,
      badMacCount: conn.badMacCount,
      lidMapSize: Object.keys(conn.lidMap || {}).length,
    };
  }
  res.json(statuses);
});

app.get('/api/qr/:numeroId', (req, res) => {
  const conn = connections[req.params.numeroId];
  if (!conn) return res.json({ ok: false, status: 'not_started', qr: null });
  res.json({ ok: true, status: conn.status, qr: conn.qr, phone: conn.phone });
});

app.post('/api/conectar/:numeroId', async (req, res) => {
  const { numeroId } = req.params;
  if (connections[numeroId]?.status === 'connected') {
    return res.json({ ok: true, status: 'connected', message: 'Ja conectado!' });
  }
  try {
    await conectar(numeroId);
    await sleep(2500);
    const conn = connections[numeroId];
    res.json({ ok: true, status: conn?.status || 'connecting', qr: conn?.qr || null });
  } catch (e) {
    res.json({ ok: false, error: e.message });
  }
});

app.post('/api/desconectar/:numeroId', async (req, res) => {
  const { numeroId } = req.params;
  const conn = connections[numeroId];
  if (conn?.socket) {
    try { await conn.socket.logout(); } catch (_) {}
  }
  if (conn?.reconnectTimer) clearTimeout(conn.reconnectTimer);
  const sessionDir = path.join(SESSIONS_DIR, numeroId);
  if (fs.existsSync(sessionDir)) fs.rmSync(sessionDir, { recursive: true, force: true });
  delete connections[numeroId];
  await flaskPut('/api/wa-numeros/status', { numero_id: numeroId, status: 'disconnected', telefone: '' });
  res.json({ ok: true });
});

app.post('/api/enviar', async (req, res) => {
  const {
    numeroId, telefone, mensagem, mensagens, contatoId, intervaloMin, intervaloMax,
    footer, buttons, templateNome, contextoEnvio, tipoEnvio
  } = req.body;
  const blocos = Array.isArray(mensagens)
    ? mensagens.map(m => String(m || '').trim()).filter(Boolean)
    : [String(mensagem || '').trim()].filter(Boolean);
  const usarBotoes = Array.isArray(buttons)
    && buttons.some(btn => String(btn?.id || '').trim() && String(btn?.text || '').trim());

  if (!numeroId || !telefone || !blocos.length) {
    return res.status(400).json({ ok: false, error: 'Faltam: numeroId, telefone, mensagem' });
  }

  const conn = connections[numeroId];
  if (!conn || conn.status !== 'connected') {
    return res.json({ ok: false, error: 'Numero "' + numeroId + '" nao conectado' });
  }

  if (contatoId) {
    const envioStatus = await flaskGet('/api/kanban/contato/' + contatoId + '/envio-status');
    if (envioStatus && envioStatus.bloqueado) {
      return res.json({ ok: false, error: envioStatus.motivo || 'Contato em lista negra' });
    }
  }

  const tel = telefone.replace(/\D/g, '');

  // Pre-mapear LID
  try {
    for (const numero of normalizarTelefonesBR(tel)) {
      const consultas = await conn.socket.onWhatsApp(numero) || [];
      for (const waInfo of consultas) {
        if (waInfo?.lid && waInfo?.jid) {
          conn.lidMap[waInfo.lid] = waInfo.jid;
          log(numeroId, 'Pre-mapeado LID: ' + waInfo.lid + ' => ' + waInfo.jid);
          flaskPost('/api/kanban/mapear-lid', { lid: waInfo.lid, telefone: waInfo.jid.replace('@s.whatsapp.net', '') });
        }
      }
    }
  } catch (_) {}

  const intervaloSeguroMin = Number.isFinite(Number(intervaloMin)) ? Math.max(400, Number(intervaloMin)) : 2200;
  const intervaloSeguroMax = Number.isFinite(Number(intervaloMax)) ? Math.max(intervaloSeguroMin, Number(intervaloMax)) : 4200;

  let ultimoResultado = null;
  for (let idx = 0; idx < blocos.length; idx++) {
    const textoBloco = blocos[idx];
    const enviarComoQuickReply = usarBotoes && idx === blocos.length - 1;
    let resultado = null;

    for (let tentativa = 0; tentativa < 2; tentativa++) {
      try {
        const envioInfo = enviarComoQuickReply
          ? await enviarQuickReplyComFallback(conn.socket, tel, textoBloco, footer, buttons)
          : await enviarTextoComFallback(conn.socket, tel, textoBloco);
        resultado = envioInfo.resultado;
        resultado.__jidUsado = envioInfo.jid;
        resultado.__numeroUsado = envioInfo.detalhe?.numero || null;
        resultado.__numeroPrioritario = envioInfo.prioritario || null;
        resultado.__tipoEnvio = enviarComoQuickReply ? 'buttons' : 'text';
        break; // sucesso
      } catch (e) {
        if (tentativa === 0 && e.message?.includes('Connection Closed')) {
          log(numeroId, 'Conexao fechou ao enviar. Aguardando reconexao...');
          await sleep(5000);
          const c = connections[numeroId];
          if (!c || c.status !== 'connected') {
            return res.json({ ok: false, error: 'Conexao perdida. Tente novamente em alguns segundos.' });
          }
          continue;
        }
        logErr(numeroId, 'Falha ao enviar bloco ' + (idx + 1) + ': ' + e.message);
        return res.json({ ok: false, error: e.message, bloco: idx + 1 });
      }
    }

    if (!resultado) {
      return res.json({ ok: false, error: 'Falha ao enviar apos retries', bloco: idx + 1 });
    }

    const msgId = resultado?.key?.id;
    if (msgId) {
      conn.sentIds.add(msgId);
      setTimeout(() => conn.sentIds.delete(msgId), 60000);
      log(
        numeroId,
        '>> Enviado bloco ' + (idx + 1) + '/' + blocos.length +
        ' [' + (resultado.__tipoEnvio || 'text') + ']' +
        ' para ' + tel +
        ' | prioritario=' + (resultado.__numeroPrioritario || '-') +
        ' | usado=' + (resultado.__numeroUsado || '-') +
        ' | jid=' + (resultado.__jidUsado || '-') +
        ' (ID: ' + msgId + ')'
      );
    }

    ultimoResultado = resultado;

    if (idx < blocos.length - 1) {
      const espera = intervaloSeguroMin + Math.random() * (intervaloSeguroMax - intervaloSeguroMin);
      await sleep(Math.round(espera));
    }
  }

  // Registrar no Flask
  await flaskPost('/api/kanban/mensagem-enviada', {
    contato_id: contatoId || 0,
    texto: blocos.join('\n\n'),
    numero_wa_id: numeroId,
    template_nome: templateNome || '',
    contexto_envio: contextoEnvio || '',
    tipo_envio: tipoEnvio || (usarBotoes ? 'buttons' : 'text'),
  });

  res.json({ ok: true, message: 'Mensagem enviada!', sentCount: blocos.length, messageId: ultimoResultado?.key?.id || null });
});

// ── Enviar documento (PDF) via WhatsApp ──────────────────────────────────────
app.post('/api/enviar-botoes-lote', async (req, res) => {
  let { numeroId, telefones, intervaloMin, intervaloMax, texto, footer, buttons } = req.body || {};

  if (!numeroId) {
    const conectado = Object.entries(connections).find(([, c]) => c.status === 'connected');
    if (!conectado) return res.json({ ok: false, error: 'Nenhum numero conectado' });
    numeroId = conectado[0];
  }

  const conn = connections[numeroId];
  if (!conn || conn.status !== 'connected') {
    return res.json({ ok: false, error: 'Numero "' + numeroId + '" nao conectado' });
  }

  const listaTelefones = Array.isArray(telefones)
    ? telefones
    : String(telefones || '')
        .split(/\r?\n/)
        .map(t => t.trim())
        .filter(Boolean);

  const telefonesNormalizados = listaTelefones
    .map(t => String(t || '').replace(/\D/g, ''))
    .filter(Boolean);

  const botoesValidos = (Array.isArray(buttons) ? buttons : [])
    .map((btn, idx) => ({
      id: String(btn?.id || `btn_${idx + 1}`).trim(),
      text: String(btn?.text || '').trim(),
    }))
    .filter(btn => btn.id && btn.text)
    .slice(0, 3);

  if (!telefonesNormalizados.length || !texto || !botoesValidos.length) {
    return res.status(400).json({ ok: false, error: 'Informe numero, texto e pelo menos um botao' });
  }

  const intervaloMinMs = Math.max(0, Math.round((Number(intervaloMin) || 2) * 1000));
  const intervaloMaxMs = Math.max(intervaloMinMs, Math.round((Number(intervaloMax) || 5) * 1000));

  const resultados = [];
  let enviados = 0;
  let erros = 0;

  for (let idx = 0; idx < telefonesNormalizados.length; idx++) {
    const tel = telefonesNormalizados[idx];
    try {
      const envioInfo = await enviarQuickReplyComFallback(conn.socket, tel, texto, footer, botoesValidos);
      const msgId = envioInfo.resultado?.key?.id || null;
      if (msgId) {
        conn.sentIds.add(msgId);
        setTimeout(() => conn.sentIds.delete(msgId), 60000);
      }
      enviados++;
      resultados.push({
        telefone: tel,
        ok: true,
        jid: envioInfo.jid,
        messageId: msgId,
      });
      log(numeroId, '[Painel Botoes] Enviado para ' + tel + ' | jid=' + (envioInfo.jid || '-') + ' | id=' + (msgId || '-'));
    } catch (e) {
      erros++;
      resultados.push({
        telefone: tel,
        ok: false,
        error: e.message,
      });
      logErr(numeroId, '[Painel Botoes] Falha para ' + tel + ': ' + e.message);
    }

    if (idx < telefonesNormalizados.length - 1) {
      const espera = intervaloMinMs + Math.random() * (intervaloMaxMs - intervaloMinMs);
      await sleep(Math.round(espera));
    }
  }

  res.json({
    ok: erros === 0,
    numeroId,
    enviados,
    erros,
    resultados,
  });
});

app.post('/api/enviar-documento', async (req, res) => {
  const { numeroId, telefone, pdfBase64, fileName, mensagemApos } = req.body;

  if (!numeroId || !telefone || !pdfBase64) {
    return res.status(400).json({ ok: false, error: 'Faltam: numeroId, telefone, pdfBase64' });
  }

  const conn = connections[numeroId];
  if (!conn || conn.status !== 'connected') {
    return res.json({ ok: false, error: 'Numero nao conectado: ' + numeroId });
  }

  const tel = telefone.replace(/\D/g, '');

  try {
    // Descobre JID correto (55xx ou +55xx)
    let jid = null;
    for (const numero of normalizarTelefonesBR(tel)) {
      try {
        const resultados = await conn.socket.onWhatsApp(numero) || [];
        const encontrado = resultados.find(r => r.exists);
        if (encontrado) { jid = encontrado.jid; break; }
      } catch (_) {}
    }
    if (!jid) jid = tel.length === 13 ? tel + '@s.whatsapp.net' : '55' + tel + '@s.whatsapp.net';

    // Envia o PDF como documento
    const buffer = Buffer.from(pdfBase64, 'base64');
    const resultado = await conn.socket.sendMessage(jid, {
      document: buffer,
      mimetype: 'application/pdf',
      fileName: fileName || 'diagnostico.pdf',
    });

    log(numeroId, `PDF enviado para ${tel}: ${fileName || 'diagnostico.pdf'}`);

    // Envia mensagem de texto após o PDF (opcional)
    if (mensagemApos) {
      await sleep(1500);
      await enviarTextoComFallback(conn.socket, tel, mensagemApos);
    }

    res.json({ ok: true, messageId: resultado?.key?.id || null });
  } catch (e) {
    logErr(numeroId, 'Erro ao enviar documento: ' + e.message);
    res.json({ ok: false, error: e.message });
  }
});

app.get('/api/mensagens/:contatoId', async (req, res) => {
  const data = await flaskGet('/api/kanban/mensagens/' + req.params.contatoId);
  res.json(data || []);
});

// ── Teste de botões interativos ──────────────────────────────────────────────
app.post('/api/testar-botoes', async (req, res) => {
  const { telefone, numero_wa_id } = req.body || {};
  if (!telefone) return res.json({ ok: false, error: 'Informe o telefone' });

  // Usa o primeiro número conectado se não informado
  let numeroId = numero_wa_id;
  if (!numeroId) {
    const conectado = Object.entries(connections).find(([, c]) => c.status === 'connected');
    if (!conectado) return res.json({ ok: false, error: 'Nenhum número conectado' });
    numeroId = conectado[0];
  }

  const conn = connections[numeroId];
  if (!conn || conn.status !== 'connected') {
    return res.json({ ok: false, error: 'Número ' + numeroId + ' não está conectado' });
  }

  const tel = telefone.replace(/\D/g, '');
  const mensagemTeste = `🧪 *Teste de Follow-up — ProspectLocal*

Olá! Esta é uma mensagem de *teste* para verificar se os botões interativos estão funcionando.

Clique em um dos botões abaixo para testar cada ação:`;

  // Timeout global de 15s para não travar o frontend
  const timeoutId = setTimeout(() => {
    if (!res.headersSent) res.json({ ok: false, error: 'Timeout (15s) — verifique o terminal do WhatsApp service' });
  }, 15000);

  try {
    const info = await enviarTesteInterativo(conn.socket, tel, mensagemTeste);
    clearTimeout(timeoutId);
    if (res.headersSent) return;
    log(numeroId, '[Teste Botões] Enviado para ' + tel + ' | tipo=' + info.tipo);
    res.json({ ok: true, comBotoes: info.comBotoes, tipo: info.tipo, jid: info.jid });
  } catch (e) {
    clearTimeout(timeoutId);
    if (res.headersSent) return;
    logErr(numeroId, '[Teste Botões] Erro: ' + e.message);
    res.json({ ok: false, error: e.message });
  }
});

// ── Health check detalhado ──
app.get('/api/health', (req, res) => {
  const health = {
    servico: 'ProspectLocal WhatsApp v2',
    uptime: Math.floor(process.uptime()) + 's',
    memoria: Math.round(process.memoryUsage().heapUsed / 1024 / 1024) + 'MB',
    conexoes: {},
  };
  for (const [id, conn] of Object.entries(connections)) {
    health.conexoes[id] = {
      status: conn.status,
      phone: conn.phone,
      reconnects: conn.reconnectAttempt,
      badMac: conn.badMacCount,
      msgsProcessadas: conn.processedIds?.size || 0,
      lidMapeados: Object.keys(conn.lidMap || {}).length,
    };
  }
  res.json(health);
});

// ── Formatar JID direto (sem onWhatsApp para evitar timeout) ────────────────
function formatarJID(tel) {
  const n = tel.replace(/\D/g, '');
  // Garante prefixo 55 + DDD + número
  const com55 = n.startsWith('55') ? n : '55' + n;
  return com55 + '@s.whatsapp.net';
}

// ── Resolver JIDs com timeout para evitar hang do onWhatsApp ─────────────────
async function resolverJidsComTimeout(sock, telefone, timeoutMs) {
  const timeoutP = new Promise(resolve => setTimeout(() => resolve(null), timeoutMs));
  const resolveP = resolverJidsWhatsApp(sock, telefone);
  const resultado = await Promise.race([resolveP, timeoutP]);
  if (resultado) return resultado.jids || [];
  // Timeout: retornar candidatos diretos sem onWhatsApp
  const candidatos = normalizarTelefonesBR(telefone);
  const jids = new Set();
  for (const n of candidatos) {
    if (n.startsWith('55')) jids.add(n + '@s.whatsapp.net');
    else { jids.add('55' + n + '@s.whatsapp.net'); jids.add(n + '@s.whatsapp.net'); }
  }
  return [...jids];
}

// ── Enviar follow-up com botões interativos — InfiniteAPI (nativeList) ───
// IMPORTANTE: nativeButtons com type:'reply' usa formato buttonsMessage LEGADO
// que o WhatsApp parou de entregar aos destinatários. Por isso, usamos
// nativeList (listMessage) como tentativa 1 — mais confiável.
// Usa onWhatsApp para verificar o JID correto antes de enviar (evita enviar
// para JID errado sem/com 9° dígito — o Baileys nunca lança erro nesses casos).
async function enviarFollowUpComBotoesLegacy(socket, tel, mensagem) {
  // ── Passo 1: verificar JID real via onWhatsApp (evita JID errado silencioso) ──
  let jidVerificado = null;
  const candidatos = normalizarTelefonesBR(tel);
  console.log('[FollowUp] Verificando JID para ' + tel + ' | candidatos: ' + candidatos.slice(0, 4).join(', '));
  for (const numero of candidatos) {
    try {
      const resultados = await Promise.race([
        socket.onWhatsApp(numero).catch(() => []),
        new Promise(resolve => setTimeout(() => resolve([]), 3000)),
      ]);
      const encontrado = (resultados || []).find(r => r?.exists && r?.jid);
      if (encontrado) {
        jidVerificado = encontrado.jid;
        console.log('[FollowUp] JID verificado para ' + tel + ': ' + jidVerificado);
        break;
      }
    } catch (_) {}
  }

  // ── Passo 2: montar lista de JIDs — verificado primeiro, fallback depois ──
  const jidDireto = formatarJID(tel);
  let jidsParaTentar;
  if (jidVerificado) {
    // Usar só o JID verificado (mais confiável)
    jidsParaTentar = jidVerificado !== jidDireto ? [jidVerificado, jidDireto] : [jidVerificado];
  } else {
    // Nenhum JID verificado — usar fallback com prioridade para 13 dígitos (com 9°)
    const fallbackSet = new Set();
    for (const n of candidatos) {
      if (n.startsWith('55')) fallbackSet.add(n + '@s.whatsapp.net');
      else { fallbackSet.add('55' + n + '@s.whatsapp.net'); fallbackSet.add(n + '@s.whatsapp.net'); }
    }
    // Ordenar: 13 dígitos (com 9°) antes de 12 dígitos (sem 9°)
    jidsParaTentar = [...fallbackSet].sort((a, b) => {
      const dA = a.replace(/@.*/, '').length;
      const dB = b.replace(/@.*/, '').length;
      return dB - dA; // mais longo (com 9°) primeiro
    });
    if (!jidsParaTentar.includes(jidDireto)) jidsParaTentar.push(jidDireto);
    console.log('[FollowUp] JID não verificado — fallback ordenado para ' + tel + ': ' + jidsParaTentar.join(', '));
  }

  // ── Tentativa 1: nativeList — menu dropdown (listMessage) ───────────────────
  for (const jid of jidsParaTentar) {
    try {
      const result = await socket.sendMessage(jid, {
        text: mensagem,
        footer: 'Escolha uma opção abaixo',
        nativeList: {
          buttonText: '📋 Ver opções',
          sections: [{
            title: 'Escolha uma ação',
            rows: [
              { id: 'fu_responder', title: '✅ Responder agora', description: 'Envie sua resposta aqui' },
              { id: 'fu_depois',    title: '⏰ Depois (48h)',    description: 'Avisarei em 2 dias'     },
              { id: 'fu_sair',      title: '🚫 Sair da lista',  description: 'Não receber mais mensagens' },
            ],
          }],
        },
      });
      console.log('[FollowUp] ✅ nativeList enviado para ' + tel + ' | jid=' + jid);
      return { resultado: result, jid, comBotoes: true, tipo: 'list' };
    } catch (errList) {
      console.log('[FollowUp] nativeList falhou para ' + jid + ': ' + errList.message);
    }
  }

  // ── Tentativa 2: nativeButtons ────────────────────────────────────────────
  for (const jid of jidsParaTentar) {
    try {
      const result = await socket.sendMessage(jid, {
        text: mensagem,
        footer: 'Clique em uma opção ou responda livremente',
        nativeButtons: [
          { type: 'reply', id: 'fu_responder', text: '✅ Responder agora' },
          { type: 'reply', id: 'fu_depois',    text: '⏰ Depois (48h)'    },
          { type: 'reply', id: 'fu_sair',      text: '🚫 Sair'            },
        ],
      });
      console.log('[FollowUp] ✅ nativeButtons enviado para ' + tel + ' | jid=' + jid);
      return { resultado: result, jid, comBotoes: true, tipo: 'buttons' };
    } catch (errBtn) {
      console.log('[FollowUp] nativeButtons falhou para ' + jid + ': ' + errBtn.message);
    }
  }

  // ── Fallback: texto formatado com opções numeradas ─────────────────────────
  console.log('[FollowUp] Botões falharam → usando texto formatado');
  const textoFinal = mensagem +
    '\n\n*Responda com uma opção:*\n' +
    '*1.* ✅ Tenho interesse\n' +
    '*2.* ⏰ Me contate depois\n' +
    '*3.* 🚫 Não tenho interesse';
  const info = await enviarTextoComFallback(socket, tel, textoFinal);
  return { ...info, comBotoes: false, tipo: 'texto' };
}

// ── Follow-up automático: checa a cada 30 minutos ──────────────────────────
async function enviarFollowUpComBotoes(socket, tel, mensagem) {
  try {
    const cfg = await obterPrincipalQuickReplyConfig();
    const info = await enviarQuickReplyComFallback(
      socket,
      tel,
      mensagem,
      cfg.footer,
      cfg.buttons
    );
    console.log('[FollowUp] ✅ quick reply enviado para ' + tel + ' | jid=' + info.jid);
    return { ...info, comBotoes: true, tipo: 'buttons' };
  } catch (errBtn) {
    console.log('[FollowUp] quick reply falhou para ' + tel + ': ' + errBtn.message);
  }

  const textoFinal = mensagem +
    '\n\n*Responda com uma opcao:*\n' +
    '*1.* ✅ Quero ver\n' +
    '*2.* ⏰ Depois\n' +
    '*3.* 🚫 Nao tenho interesse';
  const info = await enviarTextoComFallback(socket, tel, textoFinal);
  return { ...info, comBotoes: false, tipo: 'texto' };
}

async function runFollowUp() {
  try {
    const resultado = await flaskPost('/api/kanban/check-followup', {});
    if (!resultado || !resultado.followups || resultado.followups.length === 0) return;

    console.log('[FollowUp] ' + resultado.followups.length + ' follow-up(s) para enviar');

    // Verificar se botões estão ativos
    let botoesAtivos = false;
    try {
      const cfg = await flaskGet('/api/followup/config');
      botoesAtivos = cfg && cfg.followup_botoes_ativos === '1';
    } catch (_) {}

    for (const fu of resultado.followups) {
      if (!fu.telefone || !fu.numero_wa_id) continue;

      // Verificar se o número está conectado
      const conn = connections[fu.numero_wa_id];
      if (!conn || !conn.socket || conn.status !== 'connected') {
        console.log('[FollowUp] Número ' + fu.numero_wa_id + ' não conectado, pulando');
        continue;
      }

      // ── Delay dinâmico humano ──────────────────────────────────────────
      // Essencial para evitar detecção de automação pelo WhatsApp.
      // Cada mensagem é enviada com um intervalo diferente (10s a 45s),
      // simulando o comportamento humano de digitação e envio manual.
      const delayMs = 10000 + Math.random() * 35000;
      console.log('[FollowUp] Aguardando ' + Math.round(delayMs / 1000) + 's (delay anti-ban)...');
      await new Promise(r => setTimeout(r, delayMs));

      try {
        const tel = fu.telefone.replace(/\D/g, '');
        let envio, jid, detalhe, prioritario;

        if (botoesAtivos) {
          // Enviar com botões + fallback automático
          const info = await enviarFollowUpComBotoes(conn.socket, tel, fu.mensagem);
          envio = info.resultado; jid = info.jid; detalhe = info.detalhe; prioritario = info.prioritario;
        } else {
          // Texto puro com instrução de saída discreta no rodapé
          const textoFinal = fu.mensagem + '\n\n_Para não receber mais mensagens, responda:_ *SAIR*';
          const info = await enviarTextoComFallback(conn.socket, tel, textoFinal);
          envio = info.resultado; jid = info.jid; detalhe = info.detalhe; prioritario = info.prioritario;
        }

        if (envio?.key?.id) {
          conn.sentIds.add(envio.key.id);
          setTimeout(() => conn.sentIds.delete(envio.key.id), 60000);
        }
        console.log('[FollowUp] >> Enviado para ' + tel + ' | jid=' + jid);

        await flaskPost('/api/kanban/mensagem-enviada', {
          contato_id: fu.contato_id,
          texto: fu.mensagem,
          numero_wa_id: fu.numero_wa_id,
          template_nome: 'Follow-up automatico - etapa ' + fu.etapa,
          contexto_envio: 'followup',
          tipo_envio: botoesAtivos ? 'buttons' : 'text',
        });
      } catch (e) {
        console.error('[FollowUp] Erro ao enviar para ' + fu.telefone + ': ' + e.message);
      }
    }
  } catch (e) {
    console.error('[FollowUp] Erro geral: ' + e.message);
  }
}

// ─────────────────────────────────────────────────────────────────────────────
const PORT = 3001;
app.listen(PORT, async () => {
  console.log('');
  console.log('==============================================');
  console.log('  ProspectLocal - Servico WhatsApp v2');
  console.log('  Rodando em: http://localhost:' + PORT);
  console.log('  Health:     http://localhost:' + PORT + '/api/health');
  console.log('==============================================');
  console.log('');
  await autoConnect();

  // Iniciar loop de follow-up (checa a cada 30 minutos)
  setInterval(runFollowUp, 30 * 60 * 1000);
  console.log('[FollowUp] Agendado para checar a cada 30 minutos');
});
