"""
ProspectLocal - Sistema de Prospecção de Empresas Locais
Extração rica via Apify Google Maps Scraper
"""

from flask import Flask, jsonify, request, send_from_directory, Response
from apify_client import ApifyClient
import sqlite3, json, os, threading, csv, io, re, time
from datetime import datetime

# ── PDF ──────────────────────────────────────────────────────────
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                     Table, TableStyle, HRFlowable, KeepTogether)
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT
    REPORTLAB_OK = True
except ImportError:
    REPORTLAB_OK = False

app = Flask(__name__, static_folder='static')
DB_PATH = 'prospeccao.db'
CAMPAIGN_THREADS = {}
CAMPAIGN_THREAD_LOCK = threading.Lock()

DEFAULT_WA_QUICK_REPLY_CONFIG = {
    'footer': 'Toque em uma opcao abaixo',
    'buttons': [
        {'id': 'fu_responder', 'text': '✅ Quero ver'},
        {'id': 'fu_depois', 'text': '⏰ Depois'},
        {'id': 'fu_sair', 'text': '🚫 Não tenho interesse'},
    ]
}

# ─────────────────────────────────────────
# BANCO DE DADOS
# ─────────────────────────────────────────
def init_db():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.execute("PRAGMA journal_mode=WAL")
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS empresas (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            -- Identidade
            nome                TEXT,
            subtitulo           TEXT,
            descricao           TEXT,
            categoria           TEXT,
            categorias          TEXT,
            preco               TEXT,
            -- Localização
            endereco            TEXT,
            rua                 TEXT,
            bairro              TEXT,
            cidade              TEXT,
            estado              TEXT,
            cep                 TEXT,
            pais                TEXT,
            plus_code           TEXT,
            latitude            REAL,
            longitude           REAL,
            -- Contato
            telefone            TEXT,
            telefone_formatado  TEXT,
            website             TEXT,
            tem_website         INTEGER DEFAULT 0,
            menu_url            TEXT,
            -- Avaliação
            rating              REAL,
            reviews             INTEGER,
            dist_1estrela       INTEGER DEFAULT 0,
            dist_2estrelas      INTEGER DEFAULT 0,
            dist_3estrelas      INTEGER DEFAULT 0,
            dist_4estrelas      INTEGER DEFAULT 0,
            dist_5estrelas      INTEGER DEFAULT 0,
            -- Status
            fechado_permanente  INTEGER DEFAULT 0,
            fechado_temporario  INTEGER DEFAULT 0,
            reivindicado        INTEGER DEFAULT 0,
            -- Mídia
            qtd_fotos           INTEGER DEFAULT 0,
            -- Horários
            horario             TEXT,
            -- Google
            google_maps_url     TEXT,
            place_id            TEXT,
            -- Prospecção
            segmento            TEXT,
            grupo               TEXT,
            status_prospeccao   TEXT DEFAULT 'novo',
            notas               TEXT,
            -- Controle
            criado_em           TEXT DEFAULT CURRENT_TIMESTAMP,
            dados_extras        TEXT
        )
    ''')
    # Migração: adicionar colunas que possam não existir ainda
    colunas_novas = [
        ("subtitulo", "TEXT"), ("descricao", "TEXT"), ("categorias", "TEXT"),
        ("preco", "TEXT"), ("rua", "TEXT"), ("estado", "TEXT"), ("cep", "TEXT"),
        ("pais", "TEXT"), ("plus_code", "TEXT"), ("telefone_formatado", "TEXT"),
        ("menu_url", "TEXT"), ("dist_1estrela", "INTEGER DEFAULT 0"),
        ("dist_2estrelas", "INTEGER DEFAULT 0"), ("dist_3estrelas", "INTEGER DEFAULT 0"),
        ("dist_4estrelas", "INTEGER DEFAULT 0"), ("dist_5estrelas", "INTEGER DEFAULT 0"),
        ("fechado_permanente", "INTEGER DEFAULT 0"), ("fechado_temporario", "INTEGER DEFAULT 0"),
        ("reivindicado", "INTEGER DEFAULT 0"), ("qtd_fotos", "INTEGER DEFAULT 0"),
        ("place_id", "TEXT"), ("notas", "TEXT"), ("status_prospeccao", "TEXT DEFAULT 'novo'"),
    ]
    for col, tipo in colunas_novas:
        try:
            c.execute(f"ALTER TABLE empresas ADD COLUMN {col} {tipo}")
        except Exception:
            pass

    c.execute('''
        CREATE TABLE IF NOT EXISTS buscas (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            keyword          TEXT,
            segmento         TEXT,
            categoria        TEXT,
            localizacao      TEXT,
            total_encontrados INTEGER DEFAULT 0,
            novos            INTEGER DEFAULT 0,
            duplicatas       INTEGER DEFAULT 0,
            status           TEXT DEFAULT 'pendente',
            apify_run_id     TEXT,
            criado_em        TEXT DEFAULT CURRENT_TIMESTAMP,
            finalizado_em    TEXT
        )
    ''')
    # Migração: colunas novas na tabela buscas
    for col, tipo in [("novos", "INTEGER DEFAULT 0"), ("duplicatas", "INTEGER DEFAULT 0")]:
        try:
            c.execute(f"ALTER TABLE buscas ADD COLUMN {col} {tipo}")
        except Exception:
            pass
    # Índice único no place_id para evitar duplicatas (ignora vazios)
    c.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_place_id
        ON empresas(place_id)
        WHERE place_id IS NOT NULL AND place_id != ''
    """)
    # Tabela de reviews (depoimentos) — usada na geração de sites
    c.execute('''
        CREATE TABLE IF NOT EXISTS reviews (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id      INTEGER NOT NULL,
            place_id        TEXT,
            autor           TEXT,
            nota            INTEGER,
            texto           TEXT,
            data_review     TEXT,
            resposta_dono   TEXT,
            qtd_fotos_rev   INTEGER DEFAULT 0,
            idioma          TEXT,
            criado_em       TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(empresa_id) REFERENCES empresas(id) ON DELETE CASCADE
        )
    ''')
    # Índice para buscar reviews por empresa rapidamente
    c.execute("CREATE INDEX IF NOT EXISTS idx_reviews_empresa ON reviews(empresa_id)")

    # Tabela de templates Lovable por segmento
    c.execute('''
        CREATE TABLE IF NOT EXISTS template_segmentos (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            nome            TEXT NOT NULL,
            keywords        TEXT,
            prompt_template TEXT,
            ativo           INTEGER DEFAULT 1,
            criado_em       TEXT DEFAULT CURRENT_TIMESTAMP,
            atualizado_em   TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    # Semear templates iniciais apenas se a tabela estiver vazia
    count = c.execute("SELECT COUNT(*) FROM template_segmentos").fetchone()[0]
    if count == 0:
        _seed_templates(c)
    conn.commit()

    c.execute('''
        CREATE TABLE IF NOT EXISTS config (
            chave TEXT PRIMARY KEY,
            valor TEXT
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS apify_tokens (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            nome            TEXT NOT NULL,
            token           TEXT NOT NULL,
            ativo           INTEGER DEFAULT 0,
            criado_em       TEXT DEFAULT CURRENT_TIMESTAMP,
            atualizado_em   TEXT DEFAULT CURRENT_TIMESTAMP,
            ultimo_uso_em   TEXT
        )
    ''')
    c.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_apify_tokens_token ON apify_tokens(token)")
    conn.commit()

    # Migração legada: se havia apenas config.apify_token, promover para a tabela nova
    token_legado = c.execute("SELECT valor FROM config WHERE chave='apify_token'").fetchone()
    tem_tokens = c.execute("SELECT COUNT(*) FROM apify_tokens").fetchone()[0]
    if token_legado and token_legado[0] and tem_tokens == 0:
        c.execute(
            """INSERT INTO apify_tokens (nome, token, ativo, ultimo_uso_em)
               VALUES (?, ?, 1, CURRENT_TIMESTAMP)""",
            ("Token principal", token_legado[0])
        )
        conn.commit()

    # ── Tabelas WhatsApp / Kanban ─────────────────────────────────────────────
    c.execute('''
        CREATE TABLE IF NOT EXISTS wa_numeros (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            nome        TEXT NOT NULL,
            numero_id   TEXT UNIQUE NOT NULL,
            telefone    TEXT,
            status      TEXT DEFAULT 'disconnected',
            criado_em   TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS campanhas (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            nome             TEXT NOT NULL,
            estrategia       TEXT DEFAULT 'round_robin',
            total_empresas   INTEGER DEFAULT 0,
            total_numeros    INTEGER DEFAULT 0,
            template_id      INTEGER,
            template_nome    TEXT,
            template_texto   TEXT,
            intervalo_min_ms INTEGER DEFAULT 2200,
            intervalo_max_ms INTEGER DEFAULT 4200,
            usar_botoes      INTEGER DEFAULT 1,
            status           TEXT DEFAULT 'planejada',
            criado_em        TEXT DEFAULT CURRENT_TIMESTAMP,
            atualizado_em    TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    for col_sql in [
        "ALTER TABLE campanhas ADD COLUMN template_id INTEGER",
        "ALTER TABLE campanhas ADD COLUMN template_nome TEXT",
        "ALTER TABLE campanhas ADD COLUMN template_texto TEXT",
        "ALTER TABLE campanhas ADD COLUMN intervalo_min_ms INTEGER DEFAULT 2200",
        "ALTER TABLE campanhas ADD COLUMN intervalo_max_ms INTEGER DEFAULT 4200",
        "ALTER TABLE campanhas ADD COLUMN usar_botoes INTEGER DEFAULT 1",
    ]:
        try:
            c.execute(col_sql)
        except:
            pass

    c.execute('''
        CREATE TABLE IF NOT EXISTS campanha_itens (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            campanha_id   INTEGER NOT NULL,
            empresa_id    INTEGER NOT NULL,
            contato_id    INTEGER,
            numero_wa_id  TEXT,
            ordem         INTEGER DEFAULT 0,
            status        TEXT DEFAULT 'fila',
            tentativas    INTEGER DEFAULT 0,
            erro_msg      TEXT,
            enviado_em    TEXT,
            criado_em     TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(campanha_id) REFERENCES campanhas(id) ON DELETE CASCADE,
            FOREIGN KEY(empresa_id) REFERENCES empresas(id) ON DELETE CASCADE,
            FOREIGN KEY(contato_id) REFERENCES kanban_contatos(id) ON DELETE SET NULL
        )
    ''')
    for col_sql in [
        "ALTER TABLE campanha_itens ADD COLUMN tentativas INTEGER DEFAULT 0",
        "ALTER TABLE campanha_itens ADD COLUMN erro_msg TEXT",
        "ALTER TABLE campanha_itens ADD COLUMN enviado_em TEXT",
    ]:
        try:
            c.execute(col_sql)
        except:
            pass

    c.execute('''
        CREATE TABLE IF NOT EXISTS campanha_numeros (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            campanha_id    INTEGER NOT NULL,
            numero_wa_id   TEXT NOT NULL,
            total_previsto INTEGER DEFAULT 0,
            enviados       INTEGER DEFAULT 0,
            erros          INTEGER DEFAULT 0,
            status         TEXT DEFAULT 'fila',
            ultimo_erro    TEXT,
            ultima_acao_em TEXT,
            criado_em      TEXT DEFAULT CURRENT_TIMESTAMP,
            atualizado_em  TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(campanha_id) REFERENCES campanhas(id) ON DELETE CASCADE
        )
    ''')
    c.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_campanha_numeros_unique ON campanha_numeros(campanha_id, numero_wa_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_campanha_itens_campanha ON campanha_itens(campanha_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_campanha_itens_contato ON campanha_itens(contato_id)")

    c.execute('''
        CREATE TABLE IF NOT EXISTS kanban_contatos (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id        INTEGER NOT NULL,
            telefone_wa       TEXT,
            kanban_coluna     TEXT DEFAULT 'Fila',
            numero_wa_id      TEXT,
            mensagem_enviada  TEXT,
            ultima_msg        TEXT,
            ultima_msg_em     TEXT,
            notas_kanban      TEXT,
            lid_wa            TEXT,
            ordem             INTEGER DEFAULT 0,
            criado_em         TEXT DEFAULT CURRENT_TIMESTAMP,
            atualizado_em     TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(empresa_id) REFERENCES empresas(id) ON DELETE CASCADE
        )
    ''')

    # Garantir colunas extras (migrações)
    for col_sql in [
        "ALTER TABLE kanban_contatos ADD COLUMN lid_wa TEXT",
        "ALTER TABLE kanban_contatos ADD COLUMN followup_enviado_em TEXT",
        "ALTER TABLE kanban_contatos ADD COLUMN followup_etapa INTEGER DEFAULT 0",
        "ALTER TABLE kanban_contatos ADD COLUMN aguardando_nome INTEGER DEFAULT 0",
        "ALTER TABLE kanban_contatos ADD COLUMN nome_responsavel TEXT",
        "ALTER TABLE kanban_contatos ADD COLUMN resposta_classificacao TEXT",
        "ALTER TABLE kanban_contatos ADD COLUMN pending_pdf INTEGER DEFAULT 0",
        "ALTER TABLE kanban_contatos ADD COLUMN followup_pausado INTEGER DEFAULT 0",
        "ALTER TABLE kanban_contatos ADD COLUMN ja_respondeu INTEGER DEFAULT 0",
        "ALTER TABLE kanban_contatos ADD COLUMN optout_global INTEGER DEFAULT 0",
        "ALTER TABLE kanban_contatos ADD COLUMN optout_em TEXT",
        "ALTER TABLE kanban_contatos ADD COLUMN optout_motivo TEXT",
        "ALTER TABLE kanban_contatos ADD COLUMN is_teste INTEGER DEFAULT 0",
        "ALTER TABLE kanban_contatos ADD COLUMN followup_adiar_ate TEXT",
        "ALTER TABLE kanban_contatos ADD COLUMN template_origem TEXT",
        "ALTER TABLE kanban_contatos ADD COLUMN ultimo_template_nome TEXT",
        "ALTER TABLE kanban_contatos ADD COLUMN ultimo_contexto_envio TEXT",
        "ALTER TABLE kanban_contatos ADD COLUMN campanha_id INTEGER",
        "ALTER TABLE kanban_contatos ADD COLUMN campanha_item_id INTEGER",
        "ALTER TABLE kanban_contatos ADD COLUMN briefing_lead TEXT",
        "ALTER TABLE empresas ADD COLUMN nome_responsavel TEXT",
    ]:
        try:
            c.execute(col_sql)
        except:
            pass

    try:
        c.execute("""
            UPDATE kanban_contatos
               SET is_teste = 1
             WHERE COALESCE(is_teste, 0) = 0
               AND empresa_id IN (
                    SELECT id
                      FROM empresas
                     WHERE lower(COALESCE(categoria, '')) = 'teste'
                        OR lower(COALESCE(segmento, '')) = 'teste'
                        OR lower(COALESCE(grupo, '')) = 'manual'
                        OR lower(COALESCE(descricao, '')) LIKE '%teste%'
               )
        """)
    except:
        pass

    # Seed de mensagens de abordagem editáveis (só insere se não existir)
    old_msg_segunda_abordagem = (
        "Que bom que respondeu! 😊\n\n"
        "Estou entrando em contato porque notei que a *{nome}* ainda não tem um site profissional.\n\n"
        "Nós trabalhamos com criação e otimização de presença online para negócios como o seu, "
        "ajudando a alcançar mais credibilidade e atrair novos clientes.\n\n"
        "E olha só — nós já *criamos um modelo de site especialmente para a {nome}*! 🚀\n\n"
        "Gostaria de ver como ficou?\n\n"
        "Responda *Sim* ou *Não*"
    )
    old_msg_resposta_sim = (
        "Ótimo! Fico muito feliz com seu interesse! 🎉\n\n"
        "Vou preparar tudo certinho e te enviar o link do site da *{nome}* em breve.\n\n"
        "Enquanto isso, me diz: tem alguma preferência de cor, estilo ou algo que gostaria de destacar no site? "
        "Isso me ajuda a deixar tudo com a cara do seu negócio! 😉"
    )
    old_msg_followup = (
        "Oi {nome}! 👋 Passando para saber se você teve chance de ver minha mensagem anterior.\n\n"
        "Estamos criando sites profissionais para negócios como o seu aqui em {cidade}. "
        "Já temos um modelo pronto para a *{nome}*!\n\n"
        "Tem interesse em dar uma olhada? Responda *Sim* ou *Não* 😊"
    )
    old_msg_resposta_nao = (
        "Sem problemas! Agradeço muito pelo seu tempo e pela resposta. 🙏\n\n"
        "Caso mude de ideia no futuro, estamos à disposição.\n\n"
        "Desejo muito sucesso no seu negócio! 💪"
    )
    old_msg_pedir_nome = "Ótimo! 🎉 Só para personalizar tudo certinho — com quem tenho o prazer de falar? 😊"
    msgs_default = {
        'msg_segunda_abordagem': (
            "Perfeito, obrigado por responder.\n\n"
            "Falo com vocês porque a *{nome}* já tem presença no Google, mas ainda pode converter melhor no WhatsApp com uma página simples e profissional.\n\n"
            "Montei uma ideia inicial para *{categoria}* em *{cidade}* e posso te mostrar sem compromisso.\n\n"
            "Se fizer sentido, eu envio o exemplo aqui. Pode ser?"
        ),
        'msg_resposta_sim': (
            "Ótimo, {responsavel}.\n\n"
            "Vou separar a prévia da *{nome}* e te envio por aqui.\n\n"
            "Se quiser, já me diga também um ponto importante para destacar, como promoções, localização, serviços mais vendidos ou algo que traga mais clientes no WhatsApp."
        ),
        'msg_resposta_nao': (
            "Sem problema, agradeço pela sinceridade.\n\n"
            "Se em outro momento vocês quiserem melhorar a captação pelo WhatsApp e no Google, fico à disposição.\n\n"
            "Sucesso para a *{nome}*."
        ),
        'msg_followup': (
            "Oi, pessoal da *{nome}*.\n\n"
            "Passando só para confirmar se vale a pena eu te mostrar a ideia que montei para ajudar vocês a gerar mais contatos em {cidade}.\n\n"
            "Se fizer sentido, me responde com *posso ver* e eu envio por aqui."
        ),
        'followup_horas': '48',
        'followup_ativo': '1',
        'followup_so_warm_leads': '1',
        'followup_hora_inicio': '8',
        'followup_hora_fim': '20',
        'followup_max_etapas': '3',
        'followup_botoes_ativos': '1',
        'pedir_nome_ativo': '1',
        'wa_quick_reply_footer': DEFAULT_WA_QUICK_REPLY_CONFIG['footer'],
        'wa_quick_reply_buttons': json.dumps(DEFAULT_WA_QUICK_REPLY_CONFIG['buttons'], ensure_ascii=False),
        'msg_pedir_nome': (
            "Perfeito. Só para eu personalizar a prévia direitinho: com quem eu estou falando?"
        ),
    }
    for chave, valor in msgs_default.items():
        c.execute("INSERT OR IGNORE INTO config (chave, valor) VALUES (?,?)", (chave, valor))
    updates_default = {
        'msg_segunda_abordagem': (old_msg_segunda_abordagem, msgs_default['msg_segunda_abordagem']),
        'msg_resposta_sim': (old_msg_resposta_sim, msgs_default['msg_resposta_sim']),
        'msg_resposta_nao': (old_msg_resposta_nao, msgs_default['msg_resposta_nao']),
        'msg_followup': (old_msg_followup, msgs_default['msg_followup']),
        'msg_pedir_nome': (old_msg_pedir_nome, msgs_default['msg_pedir_nome']),
        'followup_horas': ('24', msgs_default['followup_horas']),
    }
    for chave, (old_val, new_val) in updates_default.items():
        row = c.execute("SELECT valor FROM config WHERE chave=?", (chave,)).fetchone()
        if row and (row[0] is None or row[0].strip() == '' or row[0] == old_val):
            c.execute("UPDATE config SET valor=? WHERE chave=?", (new_val, chave))
    row = c.execute("SELECT valor FROM config WHERE chave='msg_resposta_nao'").fetchone()
    if row and row[0] and 'Agradeço muito pelo seu tempo' in row[0]:
        c.execute("UPDATE config SET valor=? WHERE chave='msg_resposta_nao'", (msgs_default['msg_resposta_nao'],))
    row = c.execute("SELECT valor FROM config WHERE chave='msg_pedir_nome'").fetchone()
    if row and row[0] and 'com quem tenho o prazer de falar' in row[0].lower():
        c.execute("UPDATE config SET valor=? WHERE chave='msg_pedir_nome'", (msgs_default['msg_pedir_nome'],))
    c.connection.commit()

    c.execute('''
        CREATE TABLE IF NOT EXISTS wa_mensagens (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            contato_id    INTEGER,
            direcao       TEXT,
            texto         TEXT,
            numero_wa_id  TEXT,
            template_nome TEXT,
            contexto_envio TEXT,
            tipo_envio    TEXT DEFAULT 'text',
            criado_em     TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    for col_sql in [
        "ALTER TABLE wa_mensagens ADD COLUMN template_nome TEXT",
        "ALTER TABLE wa_mensagens ADD COLUMN contexto_envio TEXT",
        "ALTER TABLE wa_mensagens ADD COLUMN tipo_envio TEXT DEFAULT 'text'",
    ]:
        try:
            c.execute(col_sql)
        except:
            pass

    c.execute('''
        CREATE TABLE IF NOT EXISTS wa_msg_templates (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            nome        TEXT NOT NULL,
            categoria   TEXT DEFAULT 'abertura',
            texto       TEXT NOT NULL,
            ativo       INTEGER DEFAULT 1,
            criado_em   TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Semear templates de mensagem WA se vazio
    qt = c.execute("SELECT COUNT(*) FROM wa_msg_templates").fetchone()[0]
    if qt == 0:
        _seed_wa_templates(c)

    # Migração: inserir template de Indicação se ainda não existe
    has_ind = c.execute(
        "SELECT COUNT(*) FROM wa_msg_templates WHERE nome='Abertura - Indicação'"
    ).fetchone()[0]
    if not has_ind:
        c.execute(
            "INSERT INTO wa_msg_templates (nome, categoria, texto) VALUES (?, ?, ?)",
            ('Abertura - Indicação', 'abertura',
             'Olá! Quem me passou o contato de vocês foi *{nome_indicacao}*, que elogiou muito o atendimento do {nome}! 😊 Vocês continuam atendendo {categoria} em {cidade}?')
        )

    templates_upgrade = [
        ('Abertura - Diagnóstico Local', 'abertura',
         'Oi, pessoal da {nome}. Vi vocês no Google e notei uma chance de melhorar a captação de clientes em {cidade}, principalmente para quem procura {categoria}. Posso te explicar rapidinho por aqui?'),
        ('Abertura - Google Forte', 'abertura',
         'Olá! O {nome} aparece bem no Google, mas provavelmente ainda dá para transformar mais dessas buscas em conversas no WhatsApp. Posso te mostrar uma ideia rápida?'),
        ('Abertura - Sem Website', 'abertura',
         'Oi! Vi que a {nome} já está no Google, mas ainda sem um site enxuto para apresentar melhor o negócio e puxar contatos. Se fizer sentido, posso te mandar uma sugestão prática.'),
        ('Follow-up 4 horas', 'followup',
         'Oi, pessoal da {nome}. Passando só para confirmar se vale a pena eu te mostrar a ideia que montei para ajudar vocês a gerar mais contatos em {cidade}.'),
        ('Follow-up 24 horas', 'followup',
         'Voltei rapidinho porque negócios de {categoria} costumam perder cliente quando aparecem no Google, mas não apresentam bem o serviço logo de cara. Se quiser, eu te mostro uma ideia pronta para a {nome}.'),
    ]
    for nome_tpl, categoria_tpl, texto_tpl in templates_upgrade:
        exists = c.execute(
            "SELECT 1 FROM wa_msg_templates WHERE nome=? LIMIT 1",
            (nome_tpl,)
        ).fetchone()
        if not exists:
            c.execute(
                "INSERT INTO wa_msg_templates (nome, categoria, texto) VALUES (?, ?, ?)",
                (nome_tpl, categoria_tpl, texto_tpl)
            )

    v2_templates = [
        ('V2 | Auto | Diagnóstico', 'abertura',
         'Oi, pessoal da {nome}. Vi vocês no Google e percebi que dá para transformar mais buscas por {categoria} em conversas no WhatsApp. Posso te mostrar uma ideia rápida para isso?'),
        ('V2 | Auto | Prova Local', 'abertura',
         'Olá! A {nome} já aparece para quem procura serviço automotivo em {cidade}. O ponto é converter melhor esse interesse em orçamento. Se quiser, eu te mostro uma sugestão prática.'),
        ('V2 | Beleza | Agenda', 'abertura',
         'Oi! Vi a {nome} no Google e pensei numa forma simples de aumentar agendamentos direto no WhatsApp, sem complicar o atendimento. Posso te explicar em 30 segundos?'),
        ('V2 | Beleza | Credibilidade', 'abertura',
         'Olá! Negócios de beleza como a {nome} costumam ganhar muito quando as avaliações e os serviços ficam apresentados de forma mais profissional. Se quiser, eu te mando uma ideia pronta.'),
        ('V2 | Alimentação | Delivery', 'abertura',
         'Oi, pessoal da {nome}. Vi vocês no Google e pensei numa forma de facilitar pedidos e reservas pelo WhatsApp, principalmente para quem busca {categoria} em {cidade}. Posso te mostrar?'),
        ('V2 | Alimentação | Cardápio', 'abertura',
         'Olá! A {nome} já chama atenção no Google, mas ainda dá para converter melhor com uma apresentação rápida de cardápio, localização e botão direto para WhatsApp. Quer que eu te mostre uma ideia?'),
        ('V2 | Saúde | Confiança', 'abertura',
         'Oi! Vi a {nome} no Google e notei uma chance de transmitir mais confiança para quem está pesquisando {categoria} em {cidade}. Posso te mostrar uma sugestão simples e prática?'),
        ('V2 | Saúde | Agendamento', 'abertura',
         'Olá! Clínicas e consultórios ganham muito quando o paciente encontra logo as informações certas e chama no WhatsApp sem fricção. Se fizer sentido, eu te mostro uma ideia para a {nome}.'),
        ('V2 | Jurídico | Autoridade', 'abertura',
         'Oi, tudo bem? Vi a {nome} no Google e pensei numa forma de apresentar melhor autoridade, áreas atendidas e contato direto no WhatsApp. Posso te mostrar uma ideia enxuta?'),
        ('V2 | Serviços | Captação', 'abertura',
         'Olá! A {nome} já está no Google, mas ainda pode converter melhor visitantes em conversa. Se fizer sentido, eu te mostro uma ideia prática focada em gerar mais contatos em {cidade}.'),
        ('V2 | Proposta | Prévia', 'proposta',
         'Perfeito. Montei uma prévia para a {nome} com foco em apresentar melhor o negócio e gerar mais conversas no WhatsApp. Posso te enviar agora e você me diz se faz sentido?'),
        ('V2 | Proposta | Benefícios', 'proposta',
         'A ideia usa informações reais da {nome}, destaque dos serviços e um caminho mais rápido para orçamento ou agendamento. Se quiser, eu te mostro sem compromisso.'),
        ('V2 | Follow-up | 4h', 'followup',
         'Oi, pessoal da {nome}. Só confirmando se vale a pena eu te mostrar a ideia que montei para ajudar vocês a gerar mais contatos em {cidade}.'),
        ('V2 | Follow-up | 24h', 'followup',
         'Voltei rapidinho porque negócios como a {nome} costumam perder cliente quando aparecem no Google, mas não apresentam a oferta de forma clara logo de cara. Se quiser, eu te mando a prévia.'),
        ('V2 | Follow-up | 72h', 'followup',
         'Encerrando meu contato por aqui para não insistir. Se em algum momento vocês quiserem melhorar a entrada de clientes pelo Google e WhatsApp, me chama que eu envio a ideia da {nome}.'),
    ]
    for nome_tpl, categoria_tpl, texto_tpl in v2_templates:
        exists = c.execute(
            "SELECT 1 FROM wa_msg_templates WHERE nome=? LIMIT 1",
            (nome_tpl,)
        ).fetchone()
        if not exists:
            c.execute(
                "INSERT INTO wa_msg_templates (nome, categoria, texto) VALUES (?, ?, ?)",
                (nome_tpl, categoria_tpl, texto_tpl)
            )

    template_updates = [
        ('Abertura - Curiosidade',
         'Oi, pessoal da {nome}. Vi vocês no Google e notei uma chance de melhorar a captação de clientes em {cidade}, principalmente para quem procura {categoria}. Posso te explicar rapidinho por aqui?'),
        ('Abertura - Elogio',
         'Olá! O {nome} aparece bem no Google, mas provavelmente ainda dá para transformar mais dessas buscas em conversas no WhatsApp. Posso te mostrar uma ideia rápida?'),
        ('Abertura - Serviço',
         'Oi! Vi que a {nome} já está no Google, mas ainda sem um site enxuto para apresentar melhor o negócio e puxar contatos. Se fizer sentido, posso te mandar uma sugestão prática.'),
        ('Follow-up 1 dia',
         'Oi, pessoal da {nome}. Passando só para confirmar se vale a pena eu te mostrar a ideia que montei para ajudar vocês a gerar mais contatos em {cidade}.'),
        ('Follow-up 3 dias',
         'Voltei rapidinho porque negócios de {categoria} costumam perder cliente quando aparecem no Google, mas não apresentam bem o serviço logo de cara. Se quiser, eu te mostro uma ideia pronta para a {nome}.'),
    ]
    for nome_tpl, texto_tpl in template_updates:
        c.execute("UPDATE wa_msg_templates SET texto=? WHERE nome=?", (texto_tpl, nome_tpl))

    # Migração: mover cards de 'Proposta enviada' para 'Negociando' (coluna removida)
    c.execute("UPDATE kanban_contatos SET kanban_coluna='Negociando' WHERE kanban_coluna='Proposta enviada'")

    # Limpar mensagens órfãs (contato_id=0) de sessões anteriores com problemas de LID
    c.execute("DELETE FROM wa_mensagens WHERE contato_id = 0 OR contato_id IS NULL")

    conn.commit()

def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


AUTO_REPLY_PATTERNS = [
    'agradece seu contato',
    'agradecemos seu contato',
    'atendimento automático',
    'mensagem automática',
    'retornaremos em breve',
    'assim que possível',
    'deixe sua mensagem',
    'como podemos ajudar',
    'como posso ajudar',
    'em que posso ajudar',
    'fale conosco',
    'atendimento virtual',
]

OPEN_REPLY_PATTERNS = [
    'pode falar',
    'pode dizer',
    'claro',
    'diga',
    'pode mandar',
    'manda',
    'qual dúvida',
    'quais informações',
    'pois não',
    'pois nao',
    'sim',
    'boa tarde',
    'bom dia',
    'boa noite',
    'olá',
    'ola',
    'oi',
]

POSITIVE_REPLY_PATTERNS = [
    'sim', 'si', 'yes', 'quero', 'pode', 'bora', 'vamos',
    'claro', 'com certeza', 'manda', 'manda ai', 'manda aí',
    'quero ver', 'quero sim', 'pode mandar', 'show', 'top',
    'interessado', 'tenho interesse', 'gostaria', 'positivo',
    'pode sim', 'manda la', 'manda lá', 'opa', 'ok',
]

NEGATIVE_REPLY_PATTERNS = [
    'não', 'nao', 'no', 'n', 'nope', 'não quero',
    'nao quero', 'não preciso', 'nao preciso',
    'não obrigado', 'nao obrigado', 'sem interesse',
    'não tenho interesse', 'nao tenho interesse', 'dispenso',
    'não, obrigado', 'nao, obrigado',
    'bloquear contato', 'bloquear', 'me bloqueie',
    'sair da lista', 'remover da lista',
]

INTEREST_PATTERNS = [
    'quanto custa',
    'qual valor',
    'quanto fica',
    'como funciona',
    'pode enviar',
    'manda ai',
    'manda aí',
    'quero ver',
    'tenho interesse',
    'gostaria de ver',
    'me mostra',
    'posso ver',
]

NEGATIVE_PATTERNS = [
    'já temos site',
    'ja temos site',
    'não preciso',
    'nao preciso',
    'sem interesse',
    'não tenho interesse',
    'nao tenho interesse',
    'não quero',
    'nao quero',
    'bloquear contato',
    'sair da lista',
]


def _texto_normalizado(texto):
    return re.sub(r'\s+', ' ', (texto or '').strip().lower())


def _contains_any(texto, patterns):
    return any(p in texto for p in patterns)


def _detectar_resposta_curta(texto, patterns):
    texto_norm = _texto_normalizado(texto)
    for pattern in patterns:
        pattern_norm = _texto_normalizado(pattern)
        if (
            texto_norm == pattern_norm
            or texto_norm.startswith(pattern_norm + ' ')
            or texto_norm.startswith(pattern_norm + ',')
        ):
            return True
    for pattern in patterns:
        pattern_norm = _texto_normalizado(pattern)
        if len(pattern_norm) >= 3 and f' {pattern_norm} ' in f' {texto_norm} ':
            return True
    return False


def _classificar_primeira_resposta(texto):
    texto_norm = _texto_normalizado(texto)
    if not texto_norm:
        return 'vazio'
    if _contains_any(texto_norm, AUTO_REPLY_PATTERNS):
        return 'automatica'
    if _contains_any(texto_norm, OPEN_REPLY_PATTERNS) or '?' in texto_norm:
        return 'humana_aberta'
    return 'humana_generica'


def _classificar_resposta_negociacao(texto):
    texto_norm = _texto_normalizado(texto)
    if _contains_any(texto_norm, NEGATIVE_PATTERNS) or _detectar_resposta_curta(texto, NEGATIVE_REPLY_PATTERNS):
        return 'nao'
    if _contains_any(texto_norm, INTEREST_PATTERNS) or _detectar_resposta_curta(texto, POSITIVE_REPLY_PATTERNS):
        return 'sim'
    return 'indefinida'


def _empresa_em_lista_negra(conn, empresa_id):
    row = conn.execute(
        """SELECT 1
             FROM kanban_contatos
            WHERE empresa_id = ?
              AND COALESCE(optout_global, 0) = 1
            LIMIT 1""",
        (empresa_id,)
    ).fetchone()
    return bool(row)


def _formatar_template(texto, **kwargs):
    msg = texto or ''
    for chave, valor in kwargs.items():
        msg = msg.replace('{' + chave + '}', str(valor or ''))
    return msg


def _template_followup_por_etapa(etapa, nome, cidade, categoria, coluna='Enviado'):
    """Mensagens de follow-up por etapa. Suporta leads em Enviado, Respondeu e Negociando."""
    if coluna in ('Respondeu', 'Negociando'):
        # Follow-up para leads que já interagiram mas pararam de responder
        if etapa <= 1:
            return _formatar_template(
                "Oi, pessoal da *{nome}*! 😊\n\n"
                "Estou finalizando as previas desta semana e lembrei de voces.\n\n"
                "Ainda faz sentido dar uma olhada na ideia que preparei para a *{nome}*?",
                nome=nome, cidade=cidade, categoria=categoria,
            )
        if etapa == 2:
            return _formatar_template(
                "Oi! So passando para avisar que a previa que montei para a *{nome}* ainda esta disponivel.\n\n"
                "Se quiser dar uma olhada sem compromisso, e so me responder aqui. 👍",
                nome=nome, cidade=cidade, categoria=categoria,
            )
        return _formatar_template(
            "Encerrando meu contato por aqui para nao insistir.\n\n"
            "Se em algum momento a *{nome}* quiser melhorar a captacao de clientes pelo Google e WhatsApp, fico a disposicao! 🤝",
            nome=nome, cidade=cidade, categoria=categoria,
        )
    # Follow-up para leads em Enviado (nunca responderam)
    if etapa <= 1:
        return _formatar_template(
            "Oi, pessoal da *{nome}*.\n\n"
            "Passando so para confirmar se vale a pena eu te mostrar a ideia que montei para ajudar voces a gerar mais contatos em {cidade}.\n\n"
            "Se fizer sentido, me responde com *posso ver* e eu envio por aqui.",
            nome=nome, cidade=cidade, categoria=categoria,
        )
    if etapa == 2:
        return _formatar_template(
            "Oi, pessoal da *{nome}*.\n\n"
            "O motivo do meu contato e simples: negocios de *{categoria}* em {cidade} costumam perder oportunidade quando o cliente encontra no Google, mas nao ve uma apresentacao rapida e profissional.\n\n"
            "Se quiser, eu te mando uma ideia pronta e voce decide se vale continuar.",
            nome=nome, cidade=cidade, categoria=categoria,
        )
    return _formatar_template(
        "Encerrando meu contato por aqui para nao insistir.\n\n"
        "Se em algum momento a *{nome}* quiser melhorar a entrada de clientes pelo Google e WhatsApp, me chama que eu te envio a previa.",
        nome=nome, cidade=cidade, categoria=categoria,
    )

# ─────────────────────────────────────────
# TEMPLATES MENSAGENS WHATSAPP — SEED
# ─────────────────────────────────────────
def _seed_wa_templates(c):
    templates = [
        ('Abertura - Indicação', 'abertura',
         'Olá! Quem me passou o contato de vocês foi *{nome_indicacao}*, que elogiou muito o atendimento do {nome}! 😊 Vocês continuam atendendo {categoria} em {cidade}?'),
        ('Abertura - Diagnóstico Local', 'abertura',
         'Oi, pessoal da {nome}. Vi vocês no Google e notei uma chance de melhorar a captação de clientes em {cidade}, principalmente para quem procura {categoria}. Posso te explicar rapidinho por aqui?'),
        ('Abertura - Google Forte', 'abertura',
         'Olá! O {nome} aparece bem no Google, mas provavelmente ainda dá para transformar mais dessas buscas em conversas no WhatsApp. Posso te mostrar uma ideia rápida?'),
        ('Abertura - Sem Website', 'abertura',
         'Oi! Vi que a {nome} já está no Google, mas ainda sem um site enxuto para apresentar melhor o negócio e puxar contatos. Se fizer sentido, posso te mandar uma sugestão prática.'),
        ('Proposta - Site', 'proposta',
         'Perfeito. Montei uma prévia para a {nome} pensando em converter mais visitas do Google em conversas no WhatsApp. Posso te enviar agora e você me diz se faz sentido?'),
        ('Proposta - Detalhes', 'proposta',
         'A ideia usa as informações reais da {nome}, com foco em credibilidade, oferta clara e botão direto para WhatsApp. Se quiser, eu te mostro o exemplo antes de qualquer decisão.'),
        ('Follow-up 4 horas', 'followup',
         'Oi, pessoal da {nome}. Passando só para confirmar se vale a pena eu te mostrar a ideia que montei para ajudar vocês a gerar mais contatos em {cidade}.'),
        ('Follow-up 24 horas', 'followup',
         'Voltei rapidinho porque negócios de {categoria} costumam perder cliente quando aparecem no Google, mas não apresentam bem o serviço logo de cara. Se quiser, eu te mostro uma ideia pronta para a {nome}.'),
    ]
    for nome, cat, texto in templates:
        c.execute(
            "INSERT INTO wa_msg_templates (nome, categoria, texto) VALUES (?, ?, ?)",
            (nome, cat, texto)
        )

# ─────────────────────────────────────────
# TEMPLATES LOVABLE — SEED INICIAL
# ─────────────────────────────────────────
def _seed_templates(c):
    templates = [
        # ── 1. RESTAURANTE ──────────────────────────────────────────────────
        ("Restaurante / Lanchonete / Pizzaria",
         "restaurante,lanchonete,pizzaria,pizza,hamburguer,bar,comida,cozinha,churrascaria,sushi,japonês,italiano,self service,marmitaria,fast food,bistrô",
         """# {nome} | {categoria} em {cidade}

## CONTEXTO DO PROJETO
Crie um site gastronômico premium e apetitoso para **{nome}**, {categoria} em {cidade}. O site deve despertar fome e desejo nos visitantes, transmitir o ambiente e a identidade da casa, e converter em pedidos, reservas ou visitas.

## IDENTIDADE VISUAL
- **Estilo**: Warm & inviting — sofisticado mas acolhedor, como entrar no próprio restaurante
- **Paleta de cores**: Tons quentes — vermelho vinho (#8B1A1A) ou dourado (#C9A84C) como accent, fundo escuro carvão (#1A1A18) ou creme claro (#FAF7F0), texto branco ou marrom escuro
- **Tipografia**: Título: fonte serif elegante (Playfair Display ou Cormorant Garamond). Corpo: sans-serif limpa (Inter ou Lato)
- **Fotografia**: Espaços para fotos grandes e apetitosas de pratos, ambiente e equipe. Use placeholders cinematográficos com overlay escuro e texto branco contrastante
- **Tom**: Acolhedor, apetitoso, orgulhoso da tradição e qualidade

## DADOS REAIS DA EMPRESA
- **Nome**: {nome}
- **Tipo**: {categoria}
- **Descrição**: {descricao}
- **Endereço**: {endereco}, {cidade} — {estado}
- **Telefone / WhatsApp**: {telefone}
- **Avaliação Google**: ⭐ {rating}/5 ({reviews_count} avaliações)
- **Horário**: {horario_formatado}

## ESTRUTURA DO SITE (landing page única, scroll contínuo)

### SEÇÃO 1 — HERO (topo impactante)
- Background: foto full-screen do prato mais icônico ou ambiente do restaurante (placeholder cinemático)
- Overlay escuro semitransparente para legibilidade
- Título grande: "{nome}" em fonte serif
- Subtítulo: "{categoria} em {cidade}"
- Dois botões CTA lado a lado: "📞 Reservar Mesa" (WhatsApp: {telefone}) e "🍽️ Ver Cardápio" (scroll para seção cardápio)
- Badge flutuante de avaliação: "⭐ {rating} no Google"

### SEÇÃO 2 — SOBRE / HISTÓRIA
- Título: "Nossa História" ou "Quem Somos"
- Texto: {descricao} (expandir com tom cálido e pessoal se vazia)
- Ícones de diferenciais: ex. "Ingredientes Frescos", "Receitas Tradicionais", "Ambiente Familiar", "Atendimento Especial"
- Foto do ambiente ou da equipe ao lado (placeholder elegante)

### SEÇÃO 3 — ESPECIALIDADES / CARDÁPIO
- Título: "Nossas Especialidades"
- Grid de 3-4 cards de pratos com: placeholder de foto apetitosa, nome do prato, descrição curta, preço (se disponível)
- Botão: "Ver Cardápio Completo" → link para cardápio (placeholder por enquanto)
- Background: leve textura ou cor diferenciada para quebrar o layout

### SEÇÃO 4 — AVALIAÇÕES DO GOOGLE ⭐ {rating}/5
- Título: "O Que Nossos Clientes Dizem"
- Subtítulo: "{reviews_count} avaliações no Google"
- Cards de depoimentos com: nome do cliente, estrelas visuais, texto do review
- Reviews reais do cliente:
{reviews_texto}
- Botão: "Ver Todas no Google" → link Google Maps

### SEÇÃO 5 — HORÁRIO E CONTATO
- Horário de funcionamento: {horario_formatado}
- Telefone: {telefone}
- Endereço completo: {endereco}, {cidade}
- Mapa Google Maps embed (coordenadas de {cidade})
- Botão WhatsApp proeminente: "Falar no WhatsApp"

### SEÇÃO 6 — FOOTER
- Logo/nome do restaurante
- Links rápidos: Início, Cardápio, Avaliações, Contato
- Ícones de redes sociais (placeholders)
- Frase: "Feito com ❤️ em {cidade}"

## REQUISITOS TÉCNICOS OBRIGATÓRIOS
- React + TypeScript + Vite
- Tailwind CSS + shadcn/ui components
- Mobile-first: perfeito em celular (a maioria dos clientes acessa pelo celular)
- Animações: fade-in suave ao fazer scroll (Framer Motion)
- Botão WhatsApp flutuante fixo no canto inferior direito em todas as telas: "💬 Pedir / Reservar"
- SEO: meta title, description, Open Graph, schema markup LocalBusiness + Restaurant
- Performance: imagens lazy load, fontes otimizadas
- Seção de reviews com scroll horizontal (carousel) em mobile"""),

        # ── 2. BARBEARIA ────────────────────────────────────────────────────
        ("Barbearia / Salão de Beleza",
         "barbearia,salão,cabeleireiro,beleza,cabelo,barba,manicure,pedicure,estética,spa,nail,beauty,hair",
         """# {nome} | {categoria} em {cidade}

## CONTEXTO DO PROJETO
Crie um site premium com identidade forte para **{nome}**, {categoria} em {cidade}. O site deve transmitir estilo, confiança e profissionalismo, converter visitantes em agendamentos e destacar a equipe e os serviços.

## IDENTIDADE VISUAL
- **Estilo**: Masculino premium (barbearia) ou feminino sofisticado (salão) — escolha baseado no nome. Visual moderno com toque vintage ou luxury
- **Paleta (barbearia)**: Preto profundo (#0D0D0D) + Dourado (#D4AF37) + Branco puro + Couro/Marrom (#5C3317)
- **Paleta (salão feminino)**: Rosa nude (#F2D5CB) + Dourado rosé (#C9906A) + Branco + Cinza chumbo
- **Tipografia**: Título: fonte bold impactante (Bebas Neue, Oswald ou Montserrat Black). Corpo: limpa e moderna (Inter)
- **Estética**: Fotos grandes da equipe em ação, before/after de cortes, ambiente da loja
- **Tom**: Confiante, estiloso, "você vai sair diferente daqui"

## DADOS REAIS DA EMPRESA
- **Nome**: {nome}
- **Tipo**: {categoria}
- **Descrição**: {descricao}
- **Endereço**: {endereco}, {cidade} — {estado}
- **Telefone / WhatsApp**: {telefone}
- **Avaliação Google**: ⭐ {rating}/5 ({reviews_count} avaliações)
- **Horário**: {horario_formatado}

## ESTRUTURA DO SITE

### SEÇÃO 1 — HERO
- Foto full-screen do ambiente ou barbeiro em ação (placeholder estilizado escuro)
- Título bold: "{nome}"
- Tagline: "Seu estilo, nossa arte. Em {cidade}."
- CTA principal: "✂️ Agendar Horário" → WhatsApp {telefone}
- Badge: "⭐ {rating} no Google · {reviews_count} clientes satisfeitos"

### SEÇÃO 2 — SERVIÇOS E PREÇOS
- Título: "Nossos Serviços"
- Grid de cards elegantes com ícone, nome do serviço, descrição curta e preço (ex: Corte a partir de R$ XX, Barba, Combo, etc.)
- Serviços sugeridos: Corte Masculino, Barba, Combo Corte + Barba, Hidratação, Progressiva, Coloração (adaptar conforme tipo)
- CTA ao final: "Agendar pelo WhatsApp"

### SEÇÃO 3 — NOSSA EQUIPE
- Título: "Profissionais Especialistas"
- Cards de profissionais com foto placeholder, nome, especialidade
- Destaque para o proprietário/barbeiro principal

### SEÇÃO 4 — AVALIAÇÕES ⭐ {rating}/5
- Título: "O Que Nossos Clientes Falam"
- Reviews reais:
{reviews_texto}
- Grid de 3 colunas desktop, carousel mobile

### SEÇÃO 5 — AGENDAMENTO / CONTATO
- Título: "Agende Agora — É Rápido!"
- Botão grande WhatsApp: "💬 Agendar pelo WhatsApp"
- Horário: {horario_formatado}
- Endereço: {endereco}, {cidade}
- Mapa embed

### FOOTER
- Nome + tagline + links + redes sociais + copyright

## REQUISITOS TÉCNICOS
- React + TypeScript + Tailwind + shadcn/ui
- Mobile-first, animações scroll (Framer Motion)
- Botão WhatsApp fixo: "💬 Agendar"
- SEO LocalBusiness schema markup
- Paleta dark com accents dourados em todos os elementos interativos"""),

        # ── 3. OFICINA MECÂNICA ─────────────────────────────────────────────
        ("Oficina Mecânica / Automotivo",
         "oficina,mecânica,mecânico,auto,automóvel,carro,veículo,funilaria,pintura,elétrica automotiva,pneu,freio,suspensão,motor,troca de óleo",
         """# {nome} | {categoria} em {cidade}

## CONTEXTO DO PROJETO
Crie um site sólido e confiável para **{nome}**, {categoria} em {cidade}. O site deve transmitir competência técnica, transparência e agilidade. O cliente precisa sentir que pode confiar seu carro aqui.

## IDENTIDADE VISUAL
- **Estilo**: Industrial moderno — sólido, técnico, confiável. Sem frescura, direto ao ponto
- **Paleta**: Azul mecânico profundo (#1B2A4A) + Laranja/Amarelo energético (#F5821F ou #FFB800) + Cinza (#4A4A4A) + Branco
- **Tipografia**: Bold e legível — Roboto Condensed, Barlow ou Rajdhani para títulos; Inter para corpo
- **Elementos visuais**: Ícones técnicos de peças e serviços, linhas retas, layout sólido
- **Tom**: Direto, competente, sem enrolação — "trazemos seu carro de volta"

## DADOS REAIS DA EMPRESA
- **Nome**: {nome}
- **Tipo**: {categoria}
- **Descrição**: {descricao}
- **Endereço**: {endereco}, {cidade} — {estado}
- **Telefone / WhatsApp**: {telefone}
- **Avaliação Google**: ⭐ {rating}/5 ({reviews_count} avaliações)
- **Horário**: {horario_formatado}

## ESTRUTURA DO SITE

### SEÇÃO 1 — HERO (autoridade e urgência)
- Background: foto de mecânico trabalhando ou oficina equipada (placeholder)
- Overlay azul escuro semitransparente
- Título: "{nome}" | Subtítulo: "Sua oficina de confiança em {cidade}"
- Dois CTAs: "🔧 Solicitar Orçamento" + "📞 Ligar Agora ({telefone})"
- Badges: "⭐ {rating} no Google" | "Atendemos todos os modelos"

### SEÇÃO 2 — SERVIÇOS
- Título: "Nossos Serviços"
- Grid 2x3 ou 3x2 de cards com ícone técnico + nome + breve descrição
- Exemplos: Revisão Completa, Troca de Óleo, Suspensão e Freios, Elétrica, Funilaria e Pintura, Diagnóstico Computadorizado
- CTA: "Orçamento pelo WhatsApp"

### SEÇÃO 3 — POR QUE ESCOLHER A {nome}?
- 4-6 diferenciais com ícone + texto curto
- Exemplos: "Orçamento Sem Compromisso", "Garantia em Todos os Serviços", "Mecânicos Certificados", "Peças Originais", "Atendimento Transparente"

### SEÇÃO 4 — AVALIAÇÕES ⭐ {rating}/5
- Reviews reais:
{reviews_texto}

### SEÇÃO 5 — CONTATO E LOCALIZAÇÃO
- Horário: {horario_formatado}
- WhatsApp + Telefone: {telefone}
- Endereço: {endereco}, {cidade}
- Mapa embed

### FOOTER padrão

## REQUISITOS TÉCNICOS
- React + TypeScript + Tailwind + shadcn/ui
- Mobile-first (mecânico/cliente muitas vezes pesquisa pelo celular em pane)
- Botão WhatsApp fixo: "🔧 Orçamento"
- Schema markup: AutoRepair + LocalBusiness
- Cores escuras com accent laranja/amarelo em botões e destaques"""),

        # ── 4. ELETRICISTA ──────────────────────────────────────────────────
        ("Eletricista / Instalações",
         "eletricista,elétrica,instalação elétrica,eletrotécnico,quadro elétrico,SPDA,para-raios,ar condicionado,câmera,cftv,alarme,segurança eletrônica",
         """# {nome} | {categoria} em {cidade}

## CONTEXTO DO PROJETO
Crie um site profissional e confiável para **{nome}**, {categoria} em {cidade}. O cliente que busca eletricista geralmente está com urgência ou necessidade — o site deve inspirar confiança imediata e facilitar o contato em segundos.

## IDENTIDADE VISUAL
- **Estilo**: Profissional e confiável — limpo, sério, competente. Transmitir segurança (literalmente)
- **Paleta**: Amarelo elétrico (#FFD600) como accent forte + Azul escuro (#0A2342) como base + Branco + Cinza
- **Tipografia**: Firme e legível — Montserrat Bold ou Barlow Condensed para títulos; Source Sans Pro para corpo
- **Elementos**: Ícones elétricos, raios, plug, circuit. Layout limpo e direto
- **Tom**: Urgência + confiança + profissionalismo. "Problema resolvido, rápido e seguro"

## DADOS REAIS DA EMPRESA
- **Nome**: {nome}
- **Tipo**: {categoria}
- **Descrição**: {descricao}
- **Endereço**: {endereco}, {cidade} — {estado}
- **Telefone / WhatsApp**: {telefone}
- **Avaliação Google**: ⭐ {rating}/5 ({reviews_count} avaliações)
- **Horário**: {horario_formatado}

## ESTRUTURA DO SITE

### SEÇÃO 1 — HERO (urgência e confiança)
- Background: elétrico/profissional com accent amarelo e azul
- Título impactante: "{nome}" + "Eletricista Profissional em {cidade}"
- Destaque: "✅ Atendimento Residencial e Comercial"
- CTAs: "⚡ Solicitar Orçamento Grátis" + "📞 Emergência: {telefone}"
- Badge de avaliação: ⭐ {rating} | Badge: "Serviço Garantido"

### SEÇÃO 2 — SERVIÇOS
- Grid de serviços com ícone elétrico + nome + descrição
- Exemplos: Instalações Residenciais, Instalações Comerciais, Quadro Elétrico, SPDA/Para-raios, Ar Condicionado, CFTV e Câmeras, Alarmes, Diagnóstico Elétrico
- Destaque especial: "🚨 Atendimento de Emergência"

### SEÇÃO 3 — ÁREA DE ATENDIMENTO
- Mapa visual ou lista de bairros/cidades atendidas em {cidade}
- Destaque: "Atendemos toda {cidade} e região"

### SEÇÃO 4 — AVALIAÇÕES ⭐ {rating}/5
- Reviews reais:
{reviews_texto}

### SEÇÃO 5 — POR QUE NOS ESCOLHER?
- Cards: "NR10 e NR35 Certificado", "Garantia por Escrito", "Orçamento Grátis e Sem Compromisso", "Materiais de Qualidade", "Pontualidade Garantida"

### SEÇÃO 6 — CONTATO RÁPIDO
- Botão WhatsApp gigante central: "💬 Chamar no WhatsApp Agora"
- Telefone clicável, horário, endereço, mapa

### FOOTER padrão

## REQUISITOS TÉCNICOS
- React + TypeScript + Tailwind + shadcn/ui
- Cores: azul escuro base, amarelo elétrico em todos os CTAs e destaques
- Botão WhatsApp fixo vermelho piscante (urgência): "⚡ Emergência"
- Mobile-first — cliente em pane acessa pelo celular
- Schema: ElectricalContractor + LocalBusiness"""),

        # ── 5. CLÍNICA / SAÚDE ──────────────────────────────────────────────
        ("Clínica / Consultório / Saúde",
         "clínica,consultório,médico,medicina,saúde,dentista,odontologia,fisioterapia,psicologia,nutrição,oftalmologia,dermatologia,cardiologia,ortopedia,pediatria,ginecologia,urologia",
         """# {nome} | {categoria} em {cidade}

## CONTEXTO DO PROJETO
Crie um site clean, humanizado e profissional para **{nome}**, {categoria} em {cidade}. O paciente busca confiança, competência e acolhimento. O design deve transmitir higiene, cuidado e seriedade, mas sem ser frio.

## IDENTIDADE VISUAL
- **Estilo**: Clean healthcare — moderno, acolhedor, inspirador de confiança
- **Paleta**: Azul saúde (#2D6A9F ou #4A90D9) + Verde cuidado (#27AE60 ou #52B788) + Branco (#FFFFFF) + Cinza suave (#F5F7FA)
- **Tipografia**: Nunito ou Poppins (arredondado = acolhedor) para títulos; Source Sans Pro para corpo
- **Estética**: Fotos de profissionais com jaleco, ambiente clínico limpo, sorrisos
- **Tom**: Cuidadoso, técnico mas humano, acolhedor. "Sua saúde em boas mãos"

## DADOS REAIS DA EMPRESA
- **Nome**: {nome}
- **Tipo**: {categoria}
- **Descrição**: {descricao}
- **Endereço**: {endereco}, {cidade} — {estado}
- **Telefone / WhatsApp**: {telefone}
- **Avaliação Google**: ⭐ {rating}/5 ({reviews_count} avaliações)
- **Horário**: {horario_formatado}

## ESTRUTURA DO SITE

### SEÇÃO 1 — HERO
- Foto do profissional ou ambiente clínico (placeholder clean)
- Título: "{nome}" + Subtítulo: "{categoria} em {cidade}"
- CTA: "📅 Agendar Consulta" → WhatsApp {telefone}
- Badge: ⭐ {rating} no Google | "Atendimento Humanizado"

### SEÇÃO 2 — ESPECIALIDADES / SERVIÇOS
- Cards de especialidades com ícone de saúde, nome e descrição curta
- CTA individual: "Agendar"

### SEÇÃO 3 — SOBRE O PROFISSIONAL / A CLÍNICA
- Foto do Dr(a)/equipe, credenciais, formação, anos de experiência
- Texto humanizado: {descricao}
- Valores: "Cuidado", "Ética", "Comprometimento"

### SEÇÃO 4 — DEPOIMENTOS ⭐ {rating}/5
- Título: "Pacientes que Confiam em Nós"
- Reviews reais:
{reviews_texto}

### SEÇÃO 5 — AGENDAMENTO FÁCIL
- Destaque central: "Agende Sua Consulta Agora"
- WhatsApp + Telefone {telefone}
- Horário: {horario_formatado}
- Endereço: {endereco}, {cidade}
- Mapa embed

### FOOTER com links, redes sociais, Conselho Profissional (CFM/CRO etc)

## REQUISITOS TÉCNICOS
- React + TypeScript + Tailwind + shadcn/ui
- Paleta azul/verde saúde, layout extremamente limpo
- Botão WhatsApp fixo: "📅 Agendar Consulta"
- Schema: MedicalClinic ou Physician + LocalBusiness
- LGPD: rodapé com nota de privacidade simples"""),

        # ── 6. ACADEMIA / FITNESS ───────────────────────────────────────────
        ("Academia / Personal Trainer / Pilates",
         "academia,gym,fitness,personal,personal trainer,pilates,crossfit,musculação,natação,yoga,zumba,dança,artes marciais,muay thai,jiu-jitsu,funcional",
         """# {nome} | {categoria} em {cidade}

## CONTEXTO DO PROJETO
Crie um site energético e motivacional para **{nome}**, {categoria} em {cidade}. O site deve transmitir energia, transformação e comunidade. Converter visitantes em alunos matriculados.

## IDENTIDADE VISUAL
- **Estilo**: Energético, dinâmico, motivacional — "Bora treinar!"
- **Paleta opção A (clássico)**: Preto (#111) + Vermelho/Laranja energético (#E63946 ou #F4511E) + Branco
- **Paleta opção B (moderno)**: Azul escuro (#0D1B2A) + Verde neon/Lima (#7EE787) + Cinza + Branco
- **Tipografia**: Impactante — Bebas Neue, Barlow Condensed ou Oswald para títulos; Inter para corpo
- **Elementos visuais**: Silhuetas de atletas, pesos, antes/depois, equipe, ambiente da academia
- **Tom**: Motivacional, desafiador, inclusivo. "Transforme seu corpo, transforme sua vida"

## DADOS REAIS DA EMPRESA
- **Nome**: {nome}
- **Tipo**: {categoria}
- **Descrição**: {descricao}
- **Endereço**: {endereco}, {cidade} — {estado}
- **Telefone / WhatsApp**: {telefone}
- **Avaliação Google**: ⭐ {rating}/5 ({reviews_count} avaliações)
- **Horário**: {horario_formatado}

## ESTRUTURA DO SITE

### SEÇÃO 1 — HERO (impacto total)
- Background dark com imagem de alta energia (placeholder atlético)
- Título bold em maiúsculas: "TRANSFORME SEU CORPO"
- Subtítulo: "{nome} — {cidade}"
- CTAs: "🏋️ Aula Experimental Grátis" + "Ver Planos e Preços"
- Badge: ⭐ {rating} | Badge: "{reviews_count} alunos aprovam"

### SEÇÃO 2 — MODALIDADES / SERVIÇOS
- Grid de cards com ícone, nome da modalidade, horários disponíveis, breve descrição
- Exemplos: Musculação, Funcional, Pilates, Cardio, etc.

### SEÇÃO 3 — PLANOS E PREÇOS
- 3 cards de planos: Mensal / Trimestral / Anual (preços placeholder)
- Destaque para o plano mais popular
- CTA: "Matricule-se Agora"

### SEÇÃO 4 — TRANSFORMAÇÕES / DEPOIMENTOS ⭐ {rating}/5
- Reviews reais:
{reviews_texto}

### SEÇÃO 5 — EQUIPE / PROFESSORES
- Cards com foto placeholder, nome, especialidade, certificações

### SEÇÃO 6 — AULA EXPERIMENTAL + CONTATO
- CTA central: "Garanta Sua Aula Experimental GRÁTIS"
- Botão WhatsApp: "💬 Falar com um consultor"
- Horário: {horario_formatado} | Endereço + Mapa

### FOOTER dark com redes sociais

## REQUISITOS TÉCNICOS
- React + TypeScript + Tailwind + shadcn/ui
- Layout escuro e energético com accents coloridos
- Animações de entrada agressivas (Framer Motion)
- Botão WhatsApp fixo: "🏋️ Matricule-se"
- Schema: SportsActivityLocation + LocalBusiness
- Contador animado: "X alunos treinando" (número placeholder)"""),

        # ── 7. ADVOCACIA ────────────────────────────────────────────────────
        ("Advocacia / Escritório Jurídico",
         "advocacia,advogado,advogada,escritório jurídico,direito,law,jurídico,OAB,assessoria jurídica,consultoria jurídica",
         """# {nome} | {categoria} em {cidade}

## CONTEXTO DO PROJETO
Crie um site de autoridade e confiança para **{nome}**, {categoria} em {cidade}. O site deve transmitir expertise, seriedade e credibilidade. O cliente está em um momento delicado — ele precisa sentir que está nas mãos certas.

## IDENTIDADE VISUAL
- **Estilo**: Premium e sóbrio — elegante, autoritário, minimalista de luxo
- **Paleta**: Azul marinho profundo (#0A1628 ou #1B2A4A) + Dourado/Bronze (#C9A84C ou #B8860B) + Branco marfim (#FAFAFA) + Cinza escuro (#2D3748)
- **Tipografia**: Serif clássico para título (Cormorant Garamond, Libre Baskerville ou Playfair Display); Sans moderno para corpo (Inter ou Source Sans Pro)
- **Estética**: Escrivaninha, biblioteca jurídica, balança da justiça, advogado em escritório. Fotos formais e profissionais
- **Tom**: Sério, confiável, técnico mas acessível. "Seu problema jurídico tem solução"

## DADOS REAIS DA EMPRESA
- **Nome**: {nome}
- **Tipo**: {categoria}
- **Descrição**: {descricao}
- **Endereço**: {endereco}, {cidade} — {estado}
- **Telefone / WhatsApp**: {telefone}
- **Avaliação Google**: ⭐ {rating}/5 ({reviews_count} avaliações)
- **Horário**: {horario_formatado}

## ESTRUTURA DO SITE

### SEÇÃO 1 — HERO (autoridade)
- Background escuro elegante com textura sutil (couro, mármore ou gradiente)
- Título: "{nome}" em serif + "Advocacia em {cidade}"
- Subtítulo focado em resultado: "Defendemos seus direitos com excelência e comprometimento"
- CTA: "⚖️ Consulta Inicial" → WhatsApp {telefone}
- Badges: OAB/Número de inscrição (placeholder) | ⭐ {rating} no Google

### SEÇÃO 2 — ÁREAS DE ATUAÇÃO
- Grid elegante de cards com ícone jurídico e área: Direito Civil, Trabalhista, Família, Criminal, Empresarial, Previdenciário, Imobiliário, etc. (adaptar conforme {categoria})
- Cada card com descrição de 2 linhas e link "Saiba Mais"

### SEÇÃO 3 — SOBRE O DR.(A) / ESCRITÓRIO
- Foto profissional do advogado(a) (placeholder formal)
- Formação, especialização, anos de atuação, OAB
- Texto: {descricao}
- Valores do escritório: "Ética", "Confidencialidade", "Resultados"

### SEÇÃO 4 — DEPOIMENTOS ⭐ {rating}/5
- Título: "A Confiança dos Nossos Clientes"
- Reviews reais (preservar anonimato — exibir só nome + avaliação):
{reviews_texto}

### SEÇÃO 5 — CONTATO / CONSULTA
- Título: "Agende Sua Consulta"
- Subtítulo: "Primeira análise do caso sem compromisso"
- Botão WhatsApp: "💬 Consulta pelo WhatsApp"
- Telefone, horário ({horario_formatado}), endereço, mapa

### FOOTER com OAB, links, disclaimer legal obrigatório

## REQUISITOS TÉCNICOS
- React + TypeScript + Tailwind + shadcn/ui
- Design dark elegante com touches de dourado
- Sem animações exageradas — sutis e profissionais (fade in leve)
- Botão WhatsApp fixo discreto: "⚖️ Consulta"
- Schema: LegalService + Attorney + LocalBusiness
- Disclaimer no footer: "As informações aqui contidas não constituem consultoria jurídica"
- Certificação SSL e LGPD visíveis no footer"""),

        # ── 8. CONSTRUÇÃO / REFORMA ─────────────────────────────────────────
        ("Construção / Reforma / Arquitetura",
         "construção,reforma,construtora,empreiteira,obras,pedreiro,pintor,azulejista,gesseiro,arquitetura,engenharia,renovação,manutenção predial",
         """# {nome} | {categoria} em {cidade}

## CONTEXTO DO PROJETO
Crie um site sólido e profissional para **{nome}**, {categoria} em {cidade}. O cliente quer ver portfólio de obras, sentir confiança na execução e facilitar o pedido de orçamento. A palavra-chave é RESULTADO.

## IDENTIDADE VISUAL
- **Estilo**: Sólido e confiável — industrial moderno com toque de sofisticação
- **Paleta**: Amarelo construção (#FFB800) + Cinza cimento (#4A4A4A) + Branco + Laranja (#E8621A) como accent secundário
- **Tipografia**: Roboto Condensed Bold ou Barlow para títulos; Roboto Regular para corpo
- **Elementos**: Fotos de obras (antes/depois), materiais, equipe com EPI, plantas/projetos
- **Tom**: Direto, competente, focado em resultado. "Sua obra nas mãos certas"

## DADOS REAIS DA EMPRESA
- **Nome**: {nome}
- **Tipo**: {categoria}
- **Descrição**: {descricao}
- **Endereço**: {endereco}, {cidade} — {estado}
- **Telefone / WhatsApp**: {telefone}
- **Avaliação Google**: ⭐ {rating}/5 ({reviews_count} avaliações)
- **Horário**: {horario_formatado}

## ESTRUTURA DO SITE

### SEÇÃO 1 — HERO
- Foto impactante de obra concluída ou equipe em ação
- Título: "{nome}" + "Construção e Reforma em {cidade}"
- CTAs: "📋 Solicitar Orçamento Grátis" + "📞 {telefone}"
- Badges: ⭐ {rating} | "X anos de experiência" | "Obras entregues no prazo"

### SEÇÃO 2 — SERVIÇOS
- Grid de serviços: Construção do Zero, Reforma Completa, Pintura, Revestimentos, Hidráulica, Elétrica, Gesso/Drywall, etc.
- Cada card com ícone de ferramenta e descrição curta

### SEÇÃO 3 — PORTFÓLIO DE OBRAS
- Galeria grid com placeholders de antes/depois
- Filtros: "Residencial", "Comercial", "Reforma", "Novo"
- CTA: "Ver mais obras no WhatsApp"

### SEÇÃO 4 — POR QUE ESCOLHER A {nome}?
- Diferenciais: "Orçamento em 24h", "Equipe Própria (sem terceiros)", "Garantia por Escrito", "Materiais de 1ª Linha", "CREA/CAU Registrado"

### SEÇÃO 5 — AVALIAÇÕES ⭐ {rating}/5
{reviews_texto}

### SEÇÃO 6 — SOLICITAR ORÇAMENTO
- Formulário simples ou botão direto WhatsApp
- Horário, telefone, endereço, mapa

## REQUISITOS TÉCNICOS
- React + TypeScript + Tailwind + shadcn/ui
- Mobile-first
- Galeria com lightbox para fotos de obras
- Botão WhatsApp fixo: "📋 Orçamento Grátis"
- Schema: HomeAndConstructionBusiness + LocalBusiness
- Contador: "X obras entregues" animado"""),

        # ── 9. PET SHOP / VETERINÁRIO ────────────────────────────────────────
        ("Pet Shop / Clínica Veterinária",
         "pet shop,petshop,veterinário,veterinária,animal,banho,tosa,ração,aquário,pássaro,gato,cachorro,dog,cat,pet,animais",
         """# {nome} | {categoria} em {cidade}

## CONTEXTO DO PROJETO
Crie um site amigável, colorido e confiável para **{nome}**, {categoria} em {cidade}. O dono de pet é emocionalmente ligado ao animal — o site deve refletir amor, cuidado e profissionalismo.

## IDENTIDADE VISUAL
- **Estilo**: Amigável, caloroso, vibrante — "Seu pet merece o melhor"
- **Paleta**: Verde fresco (#27AE60 ou #4CAF50) + Azul céu (#4FC3F7) + Amarelo quente (#FFB300) + Branco. Sem cores escuras
- **Tipografia**: Rounded — Nunito, Poppins ou Quicksand para todo o site (transmite carinho)
- **Elementos**: Patas, corações, fotos fofas de pets felizes, equipe com os animais
- **Tom**: Carinhoso, especialista, tranquilizador. "Seus pets são nossa família"

## DADOS REAIS DA EMPRESA
- **Nome**: {nome}
- **Tipo**: {categoria}
- **Descrição**: {descricao}
- **Endereço**: {endereco}, {cidade} — {estado}
- **Telefone / WhatsApp**: {telefone}
- **Avaliação Google**: ⭐ {rating}/5 ({reviews_count} avaliações)
- **Horário**: {horario_formatado}

## ESTRUTURA DO SITE

### SEÇÃO 1 — HERO
- Fundo colorido e alegre com foto de pet fofo (placeholder)
- Título: "{nome}" + "Cuidamos do seu melhor amigo em {cidade}"
- CTAs: "🐾 Agendar Banho e Tosa" + "🏥 Emergência Veterinária"
- Badge: ⭐ {rating} | "Atendemos com amor"

### SEÇÃO 2 — SERVIÇOS
- Cards com ícone de pata/pet: Banho e Tosa, Consulta Veterinária, Vacinas, Castração, Pet Shop (produtos), Creche/Hotel, Adestramento
- Preços (placeholders)

### SEÇÃO 3 — POR QUE NOS ESCOLHER?
- "Profissionais que amam animais", "Ambiente Seguro e Higiênico", "Produtos de Qualidade", "Veterinário Sempre Presente"

### SEÇÃO 4 — NOSSOS PETS FELIZES (galeria)
- Grid de fotos de clientes satisfeitos (placeholders fofos)

### SEÇÃO 5 — DEPOIMENTOS ⭐ {rating}/5
{reviews_texto}

### SEÇÃO 6 — CONTATO E AGENDAMENTO
- Botão WhatsApp: "🐾 Agendar pelo WhatsApp"
- Horário: {horario_formatado} | Endereço + Mapa

## REQUISITOS TÉCNICOS
- React + TypeScript + Tailwind + shadcn/ui
- Paleta colorida e alegre, bordas arredondadas em tudo
- Microanimações suaves (patas pulando, coração pulsando)
- Botão WhatsApp fixo verde: "🐾 Agendar"
- Schema: VeterinaryCare + LocalBusiness"""),

        # ── 10. PADARIA / CONFEITARIA ────────────────────────────────────────
        ("Padaria / Confeitaria / Café",
         "padaria,confeitaria,café,bakery,bolo,pão,doce,salgado,lanche,cafeteria,pastelaria,torta,chocolate",
         """# {nome} | {categoria} em {cidade}

## CONTEXTO DO PROJETO
Crie um site artesanal, acolhedor e apetitoso para **{nome}**, {categoria} em {cidade}. O visual deve fazer o visitante sentir o cheiro de pão fresco. Transmitir tradição, carinho e qualidade artesanal.

## IDENTIDADE VISUAL
- **Estilo**: Artesanal premium — rústico moderno, aconchegante, apetitoso
- **Paleta**: Marrom caramelo (#8B5E3C ou #6F4E37) + Bege quente (#F5E6C8) + Branco + Dourado mel (#D4851A)
- **Tipografia**: Serif artesanal para títulos (Playfair Display, Lora); sans limpa para corpo (Inter)
- **Texturas**: Madeira clara, kraft paper, farinha. Fotografias quentes e apetitosas
- **Tom**: Artesanal, afetivo, tradição familiar. "Feito com amor, de geração em geração"

## DADOS REAIS DA EMPRESA
- **Nome**: {nome}
- **Tipo**: {categoria}
- **Descrição**: {descricao}
- **Endereço**: {endereco}, {cidade} — {estado}
- **Telefone / WhatsApp**: {telefone}
- **Avaliação Google**: ⭐ {rating}/5 ({reviews_count} avaliações)
- **Horário**: {horario_formatado}

## ESTRUTURA DO SITE

### SEÇÃO 1 — HERO apetitoso
- Foto quente de produtos (placeholder: bolo, pão, vitrine)
- Título: "{nome}" em serif
- Subtítulo: "Feito com amor em {cidade}"
- CTA: "🍞 Encomendar Agora" → WhatsApp {telefone}
- Badge: ⭐ {rating} | "Desde [ano — placeholder]"

### SEÇÃO 2 — NOSSOS PRODUTOS
- Grid de cards com foto do produto, nome, descrição, preço (placeholder)
- Categorias: Pães, Bolos, Salgados, Doces, Bebidas

### SEÇÃO 3 — ENCOMENDAS ESPECIAIS
- CTA de destaque para bolos personalizados/encomendas
- Botão: "Encomendar pelo WhatsApp"

### SEÇÃO 4 — NOSSA HISTÓRIA
- Texto: {descricao} + foto da padaria/equipe

### SEÇÃO 5 — DEPOIMENTOS ⭐ {rating}/5
{reviews_texto}

### SEÇÃO 6 — HORÁRIO E LOCALIZAÇÃO
- Horário: {horario_formatado} | Telefone | Endereço + Mapa

## REQUISITOS TÉCNICOS
- React + TypeScript + Tailwind + shadcn/ui
- Tons quentes e terrosos, tipografia serif, bordas arredondadas
- Botão WhatsApp fixo: "🍰 Encomendar"
- Schema: Bakery + FoodEstablishment + LocalBusiness"""),

        # ── 11. IMOBILIÁRIA ─────────────────────────────────────────────────
        ("Imobiliária / Corretor de Imóveis",
         "imobiliária,imóveis,corretor,venda,aluguel,apartamento,casa,terreno,lote,comercial,CRECI",
         """# {nome} | {categoria} em {cidade}

## CONTEXTO DO PROJETO
Crie um site premium e aspiracional para **{nome}**, {categoria} em {cidade}. O cliente está tomando a maior decisão financeira da vida — o site deve transmitir confiança, expertise e portfólio forte.

## IDENTIDADE VISUAL
- **Estilo**: Premium imobiliário — limpo, aspiracional, confiável
- **Paleta**: Azul marinho (#1B2A4A) + Dourado/Champagne (#C9A84C) + Branco (#FFFFFF) + Cinza claro (#F5F5F5)
- **Tipografia**: Título: Montserrat Bold ou Raleway; Corpo: Inter ou Source Sans Pro
- **Estética**: Fotos de interiores elegantes, fachadas, pôr do sol em condomínios
- **Tom**: Aspiracional, confiável, especialista local. "Seu sonho começa aqui"

## DADOS REAIS DA EMPRESA
- **Nome**: {nome}
- **Tipo**: {categoria}
- **Descrição**: {descricao}
- **Endereço**: {endereco}, {cidade} — {estado}
- **Telefone / WhatsApp**: {telefone}
- **Avaliação Google**: ⭐ {rating}/5 ({reviews_count} avaliações)
- **Horário**: {horario_formatado}

## ESTRUTURA DO SITE

### SEÇÃO 1 — HERO com busca
- Foto full-screen de imóvel premium (placeholder)
- Título: "Encontre o imóvel dos seus sonhos em {cidade}"
- Barra de busca: Tipo (Comprar/Alugar) + Tipo de imóvel + Valor
- Badges: ⭐ {rating} | CRECI placeholder | "X imóveis disponíveis"

### SEÇÃO 2 — IMÓVEIS EM DESTAQUE
- Grid de cards de imóveis: foto, tipo, localização, preço, metragem, dormitórios (todos placeholders)
- Filtros: Comprar / Alugar | Residencial / Comercial
- Botão: "Ver todos os imóveis"

### SEÇÃO 3 — POR QUE ESCOLHER A {nome}?
- Diferenciais: "CRECI Registrado", "Documentação Completa", "Financiamento Facilitado", "Atendimento Personalizado", "Conhecimento do Mercado Local"

### SEÇÃO 4 — SOBRE NÓS
- Foto do corretor/equipe, anos de experiência, número CRECI, especialidade
- {descricao}

### SEÇÃO 5 — DEPOIMENTOS ⭐ {rating}/5
{reviews_texto}

### SEÇÃO 6 — CONTATO / AVALIAÇÃO DE IMÓVEL
- CTA duplo: "Quero Comprar" + "Quero Vender / Alugar meu Imóvel"
- WhatsApp {telefone} | Horário | Endereço + Mapa

## REQUISITOS TÉCNICOS
- React + TypeScript + Tailwind + shadcn/ui
- Cards de imóveis com hover elegante e sombra suave
- Botão WhatsApp fixo: "🏠 Falar com Corretor"
- Schema: RealEstateAgent + LocalBusiness
- Filtros interativos nos cards de imóveis"""),

        # ── 12. ESCOLA / CURSO / ENSINO ──────────────────────────────────────
        ("Escola / Curso / Ensino",
         "escola,curso,ensino,educação,colégio,faculdade,curso livre,idioma,inglês,espanhol,música,reforço escolar,aula particular,treinamento",
         """# {nome} | {categoria} em {cidade}

## CONTEXTO DO PROJETO
Crie um site inspirador e moderno para **{nome}**, {categoria} em {cidade}. O site deve motivar a matrícula e transmitir a transformação que o aluno vai vivenciar — não apenas informar, mas inspirar.

## IDENTIDADE VISUAL
- **Estilo**: Moderno educacional — inspirador, jovem, energético mas profissional
- **Paleta**: Azul educação (#2196F3) + Amarelo/Laranja inspirador (#FF9800 ou #FFB300) + Branco + Verde sucesso (#4CAF50)
- **Tipografia**: Poppins ou Nunito (moderno e amigável) em títulos; Inter no corpo
- **Elementos**: Livros, certificados, estudantes felizes, tecnologia educacional
- **Tom**: Inspirador, transformador, acessível. "Seu futuro começa aqui"

## DADOS REAIS DA EMPRESA
- **Nome**: {nome}
- **Tipo**: {categoria}
- **Descrição**: {descricao}
- **Endereço**: {endereco}, {cidade} — {estado}
- **Telefone / WhatsApp**: {telefone}
- **Avaliação Google**: ⭐ {rating}/5 ({reviews_count} avaliações)
- **Horário**: {horario_formatado}

## ESTRUTURA DO SITE

### SEÇÃO 1 — HERO inspiracional
- Foto de alunos ou sala de aula moderna (placeholder)
- Título transformador: "Transforme Seu Futuro com {nome}"
- CTA: "📚 Garantir Minha Vaga" → WhatsApp {telefone}
- Badges: ⭐ {rating} | "X alunos formados" | "Certificado Reconhecido"

### SEÇÃO 2 — CURSOS / MODALIDADES
- Cards de cursos: nome, duração, modalidade (presencial/online/híbrido), carga horária, CTA matricular

### SEÇÃO 3 — METODOLOGIA / DIFERENCIAIS
- "Por que o {nome} é diferente?" — 4-6 pontos: Professores Especializados, Material Incluso, Certificação, Turmas Reduzidas, Aulas Práticas, Suporte Pós-Aula

### SEÇÃO 4 — DEPOIMENTOS ⭐ {rating}/5
{reviews_texto}

### SEÇÃO 5 — MATRÍCULA FÁCIL
- CTA central: "Reserve Sua Vaga — Turmas Limitadas!"
- WhatsApp, horário de atendimento, endereço, mapa

## REQUISITOS TÉCNICOS
- React + TypeScript + Tailwind + shadcn/ui
- Cores vibrantes e inspiradoras
- Animação de contador: "X alunos matriculados"
- Botão WhatsApp fixo: "📚 Matricular"
- Schema: EducationalOrganization + LocalBusiness"""),

        # ── 13. HOTEL / POUSADA ──────────────────────────────────────────────
        ("Hotel / Pousada / Turismo",
         "hotel,pousada,hospedagem,hostel,resort,turismo,turística,quarto,suite,acomodação,chalet,cabana",
         """# {nome} | {categoria} em {cidade}

## CONTEXTO DO PROJETO
Crie um site turístico premium e acolhedor para **{nome}**, {categoria} em {cidade}. O viajante quer ser seduzido pela experiência antes de reservar. Cada imagem e palavra deve fazer ele querer estar ali agora.

## IDENTIDADE VISUAL
- **Estilo**: Acolhedor premium — boutique, experiência, escapada perfeita
- **Paleta**: Bege areia (#F5E6C8) + Verde oliva (#6B7C4E) + Branco + Terracota (#C7654A) ou Azul oceano (#2E86AB)
- **Tipografia**: Serif elegante (Cormorant, Lora) para títulos; Inter limpa para corpo
- **Fotografia**: Quartos, vista, piscina, café da manhã — cinematográfico e quente
- **Tom**: Experiencial, acolhedor, escapismo. "Sua fuga perfeita"

## DADOS REAIS DA EMPRESA
- **Nome**: {nome}
- **Tipo**: {categoria}
- **Descrição**: {descricao}
- **Endereço**: {endereco}, {cidade} — {estado}
- **Telefone / WhatsApp**: {telefone}
- **Avaliação Google**: ⭐ {rating}/5 ({reviews_count} avaliações)
- **Horário**: Check-in {horario_formatado}

## ESTRUTURA DO SITE

### SEÇÃO 1 — HERO cinemático
- Slider ou vídeo do local (placeholder premium)
- Título: "{nome}" em serif + localização
- CTA: "🏨 Verificar Disponibilidade" → WhatsApp {telefone}
- Badge: ⭐ {rating} no Google

### SEÇÃO 2 — ACOMODAÇÕES
- Cards de quartos/suítes: foto, nome, capacidade, comodidades, preço/noite (placeholder)
- CTA: "Reservar pelo WhatsApp"

### SEÇÃO 3 — EXPERIÊNCIAS / COMODIDADES
- Ícones de comodidades: Wi-Fi, Café da manhã incluso, Piscina, Estacionamento, AC, etc.

### SEÇÃO 4 — SOBRE / LOCALIZAÇÃO
- {descricao} + pontos turísticos próximos (placeholder para {cidade})
- Mapa embed

### SEÇÃO 5 — DEPOIMENTOS ⭐ {rating}/5
{reviews_texto}

### SEÇÃO 6 — RESERVA / CONTATO
- CTA: "Consultar Disponibilidade pelo WhatsApp"
- Horário, telefone, mapa

## REQUISITOS TÉCNICOS
- React + TypeScript + Tailwind + shadcn/ui
- Slider de fotos cinematográfico no hero
- Galeria de acomodações com lightbox
- Botão WhatsApp fixo: "🏨 Reservar"
- Schema: LodgingBusiness + Hotel + LocalBusiness"""),

        # ── 14. CONTABILIDADE ───────────────────────────────────────────────
        ("Contabilidade / Financeiro",
         "contabilidade,contador,contábil,financeiro,fiscal,tributário,imposto,CNPJ,abertura de empresa,MEI,simples nacional,folha de pagamento,BPO",
         """# {nome} | {categoria} em {cidade}

## CONTEXTO DO PROJETO
Crie um site profissional e confiável para **{nome}**, {categoria} em {cidade}. O cliente quer segurança, expertise e um contador que fale a sua língua — sem dificuldades, sem surpresas.

## IDENTIDADE VISUAL
- **Estilo**: Profissional, confiável, moderno — sem ser frio
- **Paleta**: Azul corporativo (#1E3A5F ou #2D6A9F) + Verde prosperidade (#27AE60) + Branco + Cinza (#F8F9FA)
- **Tipografia**: Inter ou Source Sans Pro — limpa, legível, séria
- **Elementos**: Gráficos, documentos, calculadora, handshake, crescimento
- **Tom**: Parceiro de negócios, simplificador, especialista. "Sua empresa cresce, a gente cuida das contas"

## DADOS REAIS DA EMPRESA
- **Nome**: {nome}
- **Tipo**: {categoria}
- **Descrição**: {descricao}
- **Endereço**: {endereco}, {cidade} — {estado}
- **Telefone / WhatsApp**: {telefone}
- **Avaliação Google**: ⭐ {rating}/5 ({reviews_count} avaliações)
- **Horário**: {horario_formatado}

## ESTRUTURA DO SITE

### SEÇÃO 1 — HERO
- Background limpo, corporativo, com elemento gráfico (crescimento, gráfico ascendente)
- Título: "{nome}" + "Contabilidade Inteligente para o seu negócio em {cidade}"
- CTA: "📊 Falar com um Contador" → WhatsApp {telefone}
- Badge: ⭐ {rating} | CRC Registrado (placeholder)

### SEÇÃO 2 — SERVIÇOS
- Cards: Abertura de Empresa, MEI, Imposto de Renda, Folha de Pagamento, BPO Financeiro, Planejamento Tributário, Consultoria Empresarial

### SEÇÃO 3 — PARA QUEM ATENDEMOS?
- Ícones: MEI, Micro e Pequenas Empresas, Pessoas Físicas, Startups, Comércio, Serviços

### SEÇÃO 4 — POR QUE O {nome}?
- "CRC Ativo", "Atendimento Digital (sem precisar ir ao escritório)", "Relatórios Mensais Claros", "Especialistas em Simples Nacional", "X anos de experiência"

### SEÇÃO 5 — DEPOIMENTOS ⭐ {rating}/5
{reviews_texto}

### SEÇÃO 6 — CONTATO / PROPOSTA
- CTA: "Solicitar Proposta Gratuita"
- WhatsApp + Horário + Endereço + Mapa

## REQUISITOS TÉCNICOS
- React + TypeScript + Tailwind + shadcn/ui
- Layout clean e corporativo, muita whitespace
- Botão WhatsApp fixo: "📊 Falar com Contador"
- Schema: AccountingService + LocalBusiness"""),

        # ── 15. GENÉRICO (FALLBACK) ─────────────────────────────────────────
        ("Genérico / Serviços em Geral",
         "",
         """# {nome} | {categoria} em {cidade}

## CONTEXTO DO PROJETO
Crie um site profissional, moderno e completo para **{nome}**, {categoria} em {cidade}. O objetivo é apresentar o negócio de forma clara, transmitir credibilidade e converter visitantes em clientes pelo WhatsApp.

## IDENTIDADE VISUAL
- **Estilo**: Moderno e profissional — limpo, confiável, contemporâneo
- **Paleta**: Azul profissional (#2563EB) + Accent secundário (escolher tom que combine com o segmento) + Branco + Cinza claro (#F8FAFC)
- **Tipografia**: Inter ou Poppins para todo o site — moderna e altamente legível
- **Tom**: Profissional, confiável, direto. "O melhor serviço de {categoria} em {cidade}"

## DADOS REAIS DA EMPRESA
- **Nome**: {nome}
- **Tipo**: {categoria}
- **Descrição**: {descricao}
- **Endereço**: {endereco}, {cidade} — {estado}
- **Telefone / WhatsApp**: {telefone}
- **Avaliação Google**: ⭐ {rating}/5 ({reviews_count} avaliações)
- **Horário**: {horario_formatado}

## ESTRUTURA DO SITE (landing page completa)

### SEÇÃO 1 — HERO
- Background profissional (foto do negócio ou gradiente com pattern sutil)
- Título: "{nome}" + Subtítulo: "{categoria} em {cidade}"
- CTA principal: "💬 Falar pelo WhatsApp" → {telefone}
- Badge de avaliação: ⭐ {rating}/5 ({reviews_count} avaliações no Google)

### SEÇÃO 2 — SOBRE NÓS
- Apresentação do negócio: {descricao}
- 4 ícones de diferenciais (adaptar ao segmento)

### SEÇÃO 3 — NOSSOS SERVIÇOS / PRODUTOS
- Grid de 4-6 cards com ícone relevante, nome do serviço e breve descrição
- CTA em cada card: "Saber Mais"

### SEÇÃO 4 — AVALIAÇÕES DO GOOGLE ⭐ {rating}/5
- Título: "O Que Nossos Clientes Dizem"
- Reviews reais:
{reviews_texto}
- Botão: "Ver Todas as Avaliações no Google"

### SEÇÃO 5 — CONTATO E LOCALIZAÇÃO
- Botão WhatsApp em destaque: "💬 Entrar em Contato"
- Telefone, horário ({horario_formatado}), endereço completo ({endereco}, {cidade})
- Google Maps embed

### FOOTER
- Nome da empresa, links, redes sociais, copyright

## REQUISITOS TÉCNICOS OBRIGATÓRIOS
- React + TypeScript + Vite
- Tailwind CSS + shadcn/ui
- Mobile-first em todos os breakpoints
- Animações suaves ao scroll (Framer Motion — fade-in)
- Botão WhatsApp flutuante fixo no canto inferior direito: "💬 Falar Agora"
- SEO: meta tags, Open Graph, schema markup LocalBusiness
- Imagens com lazy loading
- Performance otimizada (Lighthouse score > 90)"""),
    ]
    c.executemany(
        "INSERT INTO template_segmentos (nome, keywords, prompt_template) VALUES (?,?,?)",
        templates
    )

init_db()

# ─────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────
def get_api_token():
    conn = get_db()
    row = conn.execute(
        "SELECT id, token, nome FROM apify_tokens WHERE ativo = 1 ORDER BY id DESC LIMIT 1"
    ).fetchone()
    if row:
        conn.execute(
            "UPDATE apify_tokens SET ultimo_uso_em=CURRENT_TIMESTAMP, atualizado_em=CURRENT_TIMESTAMP WHERE id=?",
            (row['id'],)
        )
        conn.commit()
        conn.close()
        return row['token']
    row = conn.execute("SELECT valor FROM config WHERE chave='apify_token'").fetchone()
    conn.close()
    return row['valor'] if row else None

def get_apify_tokens():
    conn = get_db()
    rows = conn.execute(
        "SELECT id, nome, token, ativo, criado_em, atualizado_em, ultimo_uso_em FROM apify_tokens ORDER BY ativo DESC, id ASC"
    ).fetchall()
    conn.close()
    resultado = []
    for r in rows:
        d = dict(r)
        token = d.get('token') or ''
        d['token_mascarado'] = token[:6] + '****' + token[-4:] if len(token) > 10 else '****'
        d.pop('token', None)
        resultado.append(d)
    return resultado

def get_apify_token_by_id(token_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM apify_tokens WHERE id=?", (token_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def ativar_apify_token(token_id):
    conn = get_db()
    conn.execute("UPDATE apify_tokens SET ativo = 0")
    conn.execute(
        "UPDATE apify_tokens SET ativo = 1, atualizado_em=CURRENT_TIMESTAMP WHERE id = ?",
        (token_id,)
    )
    conn.commit()
    # Compatibilidade com fluxos antigos que ainda consultem config
    row = conn.execute("SELECT token FROM apify_tokens WHERE id=?", (token_id,)).fetchone()
    if row:
        conn.execute("INSERT OR REPLACE INTO config (chave, valor) VALUES ('apify_token', ?)", (row['token'],))
        conn.commit()
    conn.close()

def testar_token_apify(token):
    client = ApifyClient(token)
    user  = client.user('me').get()
    plan  = user.get('plan', {})
    usage = user.get('usageCycle', {})
    return {
        'usuario': user.get('username'),
        'plano': plan.get('name', 'Free'),
        'credito_disponivel': usage.get('monthlyUsageUsd', 0),
        'limite_mensal': plan.get('monthlyUsageCreditsUsd', 5),
        'percentual_usado': round((usage.get('monthlyUsageUsd', 0) / max(plan.get('monthlyUsageCreditsUsd', 5), 0.01)) * 100, 1),
    }

def save_config(chave, valor):
    conn = get_db()
    conn.execute("INSERT OR REPLACE INTO config (chave, valor) VALUES (?,?)", (chave, valor))
    conn.commit()

def extrair_empresa(item, segmento, keyword, categoria, local, grupo):
    """Extrai todos os campos disponíveis do item do Apify."""
    dist = item.get('reviewsDistribution') or {}
    loc  = item.get('location') or {}
    website = (item.get('website') or '').strip()
    return {
        'nome':               item.get('title', ''),
        'subtitulo':          item.get('subTitle', '') or '',
        'descricao':          item.get('description', '') or '',
        'categoria':          item.get('categoryName', '') or categoria,
        'categorias':         json.dumps(item.get('categories', []), ensure_ascii=False),
        'preco':              item.get('price', '') or '',
        'endereco':           item.get('address', '') or '',
        'rua':                item.get('street', '') or '',
        'bairro':             item.get('neighborhood', '') or '',
        'cidade':             item.get('city', '') or local,
        'estado':             item.get('state', '') or '',
        'cep':                item.get('postalCode', '') or '',
        'pais':               item.get('countryCode', '') or '',
        'plus_code':          item.get('plusCode', '') or '',
        'latitude':           loc.get('lat'),
        'longitude':          loc.get('lng'),
        'telefone':           item.get('phone', '') or '',
        'telefone_formatado': item.get('phoneUnformatted', '') or '',
        'website':            website,
        'tem_website':        1 if website else 0,
        'menu_url':           item.get('menu', '') or '',
        'rating':             item.get('totalScore'),
        'reviews':            item.get('reviewsCount', 0) or 0,
        'dist_1estrela':      dist.get('oneStar', 0) or 0,
        'dist_2estrelas':     dist.get('twoStar', 0) or 0,
        'dist_3estrelas':     dist.get('threeStar', 0) or 0,
        'dist_4estrelas':     dist.get('fourStar', 0) or 0,
        'dist_5estrelas':     dist.get('fiveStar', 0) or 0,
        'fechado_permanente': 1 if item.get('permanentlyClosed') else 0,
        'fechado_temporario': 1 if item.get('temporarilyClosed') else 0,
        'reivindicado':       0 if item.get('claimThisBusiness') else 1,
        'qtd_fotos':          item.get('imagesCount', 0) or 0,
        'horario':            json.dumps(item.get('openingHours', []), ensure_ascii=False),
        'google_maps_url':    item.get('url', '') or '',
        'place_id':           item.get('placeId', '') or '',
        'segmento':           segmento or keyword,
        'grupo':              grupo,
        'dados_extras':       json.dumps(item, ensure_ascii=False),
    }

# ─────────────────────────────────────────
# ROTAS – CONFIGURAÇÃO
# ─────────────────────────────────────────
@app.route('/api/config', methods=['GET'])
def get_config_api():
    conn = get_db()
    rows = conn.execute("SELECT chave, valor FROM config").fetchall()
    conn.close()
    data = {r['chave']: r['valor'] for r in rows}
    tokens = get_apify_tokens()
    ativo = next((t for t in tokens if t.get('ativo')), None)
    data['apify_tokens'] = tokens
    data['token_configurado'] = bool(ativo)
    if ativo:
        data['apify_token_mascarado'] = ativo['token_mascarado']
        data['apify_token_ativo_nome'] = ativo['nome']
    return jsonify(data)

@app.route('/api/config', methods=['POST'])
def set_config_api():
    payload = request.json or {}
    if 'apify_token' in payload:
        token = (payload.get('apify_token') or '').strip()
        nome = (payload.get('apify_nome') or 'Token principal').strip()
        if token:
            conn = get_db()
            row = conn.execute("SELECT id FROM apify_tokens WHERE token=?", (token,)).fetchone()
            if row:
                conn.execute(
                    "UPDATE apify_tokens SET nome=?, ativo=1, atualizado_em=CURRENT_TIMESTAMP WHERE id=?",
                    (nome, row['id'])
                )
                token_id = row['id']
            else:
                conn.execute("UPDATE apify_tokens SET ativo = 0")
                cur = conn.execute(
                    """INSERT INTO apify_tokens (nome, token, ativo, ultimo_uso_em)
                       VALUES (?, ?, 1, CURRENT_TIMESTAMP)""",
                    (nome, token)
                )
                token_id = cur.lastrowid
            conn.execute("INSERT OR REPLACE INTO config (chave, valor) VALUES ('apify_token', ?)", (token,))
            conn.commit()
            conn.close()
            ativar_apify_token(token_id)
        payload = {k: v for k, v in payload.items() if k not in ('apify_token', 'apify_nome')}

    for chave, valor in payload.items():
        save_config(chave, valor)
    return jsonify({'ok': True})

@app.route('/api/apify-tokens', methods=['GET'])
def apify_tokens_listar():
    return jsonify(get_apify_tokens())

@app.route('/api/apify-tokens', methods=['POST'])
def apify_tokens_criar():
    d = request.json or {}
    nome = (d.get('nome') or '').strip()
    token = (d.get('token') or '').strip()
    ativar = bool(d.get('ativar', True))
    if not nome or not token:
        return jsonify({'erro': 'nome e token obrigatórios'}), 400

    conn = get_db()
    row = conn.execute("SELECT id FROM apify_tokens WHERE token=?", (token,)).fetchone()
    if row:
        token_id = row['id']
        if ativar:
            conn.execute("UPDATE apify_tokens SET ativo = 0")
        conn.execute(
            "UPDATE apify_tokens SET nome=?, ativo=?, atualizado_em=CURRENT_TIMESTAMP WHERE id=?",
            (nome, 1 if ativar else 0, token_id)
        )
    else:
        if ativar:
            conn.execute("UPDATE apify_tokens SET ativo = 0")
        cur = conn.execute(
            """INSERT INTO apify_tokens (nome, token, ativo, ultimo_uso_em)
               VALUES (?, ?, ?, CURRENT_TIMESTAMP)""",
            (nome, token, 1 if ativar else 0)
        )
        token_id = cur.lastrowid
    conn.commit()
    conn.close()
    if ativar:
        ativar_apify_token(token_id)
    return jsonify({'ok': True, 'tokens': get_apify_tokens()})

@app.route('/api/apify-tokens/<int:token_id>/ativar', methods=['PUT'])
def apify_tokens_ativar(token_id):
    token = get_apify_token_by_id(token_id)
    if not token:
        return jsonify({'erro': 'Token não encontrado'}), 404
    ativar_apify_token(token_id)
    return jsonify({'ok': True, 'tokens': get_apify_tokens()})

@app.route('/api/apify-tokens/<int:token_id>/testar', methods=['POST'])
def apify_tokens_testar(token_id):
    token = get_apify_token_by_id(token_id)
    if not token:
        return jsonify({'erro': 'Token não encontrado'}), 404
    try:
        return jsonify({'ok': True, 'apify': testar_token_apify(token['token'])})
    except Exception as e:
        return jsonify({'ok': False, 'erro': str(e)}), 400

@app.route('/api/apify-tokens/<int:token_id>', methods=['DELETE'])
def apify_tokens_deletar(token_id):
    token = get_apify_token_by_id(token_id)
    if not token:
        return jsonify({'erro': 'Token não encontrado'}), 404
    conn = get_db()
    conn.execute("DELETE FROM apify_tokens WHERE id=?", (token_id,))
    conn.commit()
    restante = conn.execute("SELECT id FROM apify_tokens ORDER BY id LIMIT 1").fetchone()
    conn.close()
    if token.get('ativo') and restante:
        ativar_apify_token(restante['id'])
    return jsonify({'ok': True, 'tokens': get_apify_tokens()})


def _percentual(valor, base):
    return round((float(valor) / float(base)) * 100, 1) if base else 0.0


def _coletar_metricas_comerciais(conn):
    enviados = conn.execute(
        """SELECT COUNT(*) AS n
             FROM wa_mensagens wm
             JOIN kanban_contatos kc ON kc.id = wm.contato_id
            WHERE wm.direcao = 'enviada'
              AND wm.contato_id > 0
              AND COALESCE(wm.contexto_envio, '') != 'auto_reply'
              AND COALESCE(kc.is_teste, 0) = 0"""
    ).fetchone()['n']

    entregues = conn.execute(
        """SELECT COUNT(DISTINCT wm.contato_id) AS n
             FROM wa_mensagens wm
             JOIN kanban_contatos kc ON kc.id = wm.contato_id
            WHERE wm.direcao = 'enviada'
              AND wm.contato_id > 0
              AND COALESCE(wm.contexto_envio, '') != 'auto_reply'
              AND COALESCE(kc.is_teste, 0) = 0"""
    ).fetchone()['n']

    responderam = conn.execute(
        """SELECT COUNT(*) AS n
             FROM kanban_contatos
            WHERE COALESCE(is_teste, 0) = 0
              AND COALESCE(ja_respondeu, 0) = 1"""
    ).fetchone()['n']

    interessados = conn.execute(
        """SELECT COUNT(*) AS n
             FROM kanban_contatos
            WHERE COALESCE(is_teste, 0) = 0
              AND (
                    kanban_coluna IN ('Negociando', 'Fechado')
                    OR COALESCE(resposta_classificacao, '') = 'interesse'
                  )"""
    ).fetchone()['n']

    blacklist = conn.execute(
        """SELECT COUNT(*) AS n
             FROM kanban_contatos
            WHERE COALESCE(is_teste, 0) = 0
              AND COALESCE(optout_global, 0) = 1"""
    ).fetchone()['n']

    templates_rows = conn.execute(
        """SELECT COALESCE(NULLIF(TRIM(kc.template_origem), ''), 'Manual / sem template') AS template_nome,
                  COUNT(*) AS enviados,
                  SUM(CASE WHEN COALESCE(kc.ja_respondeu, 0) = 1 THEN 1 ELSE 0 END) AS responderam,
                  SUM(CASE WHEN kc.kanban_coluna IN ('Negociando', 'Fechado')
                            OR COALESCE(kc.resposta_classificacao, '') = 'interesse'
                           THEN 1 ELSE 0 END) AS interessados,
                  SUM(CASE WHEN COALESCE(kc.optout_global, 0) = 1 THEN 1 ELSE 0 END) AS blacklist
             FROM kanban_contatos kc
            WHERE COALESCE(kc.is_teste, 0) = 0
              AND EXISTS (
                    SELECT 1
                     FROM wa_mensagens wm
                     WHERE wm.contato_id = kc.id
                       AND wm.direcao = 'enviada'
                       AND COALESCE(wm.contexto_envio, '') != 'auto_reply'
                  )
            GROUP BY 1
            ORDER BY enviados DESC, interessados DESC, responderam DESC
            LIMIT 8"""
    ).fetchall()

    nicho_rows = conn.execute(
        """SELECT COALESCE(NULLIF(TRIM(e.categoria), ''), 'Sem categoria') AS categoria,
                  COALESCE(NULLIF(TRIM(e.cidade), ''), 'Sem cidade') AS cidade,
                  COUNT(*) AS enviados,
                  SUM(CASE WHEN COALESCE(kc.ja_respondeu, 0) = 1 THEN 1 ELSE 0 END) AS responderam,
                  SUM(CASE WHEN kc.kanban_coluna IN ('Negociando', 'Fechado')
                            OR COALESCE(kc.resposta_classificacao, '') = 'interesse'
                           THEN 1 ELSE 0 END) AS interessados,
                  SUM(CASE WHEN COALESCE(kc.optout_global, 0) = 1 THEN 1 ELSE 0 END) AS blacklist
             FROM kanban_contatos kc
             JOIN empresas e ON e.id = kc.empresa_id
            WHERE COALESCE(kc.is_teste, 0) = 0
              AND EXISTS (
                    SELECT 1
                     FROM wa_mensagens wm
                     WHERE wm.contato_id = kc.id
                       AND wm.direcao = 'enviada'
                       AND COALESCE(wm.contexto_envio, '') != 'auto_reply'
                  )
            GROUP BY 1, 2
            ORDER BY interessados DESC, responderam DESC, enviados DESC
            LIMIT 10"""
    ).fetchall()

    templates = []
    for row in templates_rows:
        item = dict(row)
        item['taxa_resposta'] = _percentual(item['responderam'], item['enviados'])
        item['taxa_interesse'] = _percentual(item['interessados'], item['enviados'])
        templates.append(item)

    nichos_cidades = []
    for row in nicho_rows:
        item = dict(row)
        item['label'] = f"{item['categoria']} - {item['cidade']}"
        item['taxa_resposta'] = _percentual(item['responderam'], item['enviados'])
        item['taxa_interesse'] = _percentual(item['interessados'], item['enviados'])
        nichos_cidades.append(item)

    return {
        'enviados': enviados,
        'entregues': entregues,
        'responderam': responderam,
        'interessados': interessados,
        'blacklist': blacklist,
        'taxa_resposta_geral': _percentual(responderam, entregues),
        'taxa_interesse_geral': _percentual(interessados, entregues),
        'templates': templates,
        'nichos_cidades': nichos_cidades,
    }

# ─────────────────────────────────────────
# ROTAS – DASHBOARD
# ─────────────────────────────────────────
@app.route('/api/dashboard')
def dashboard():
    conn  = get_db()
    total_empresas = conn.execute("SELECT COUNT(*) as n FROM empresas").fetchone()['n']
    sem_site  = conn.execute("SELECT COUNT(*) as n FROM empresas WHERE tem_website=0").fetchone()['n']
    com_site  = conn.execute("SELECT COUNT(*) as n FROM empresas WHERE tem_website=1").fetchone()['n']
    total_buscas = conn.execute("SELECT COUNT(*) as n FROM buscas").fetchone()['n']
    grupos = conn.execute("SELECT grupo, COUNT(*) as n FROM empresas WHERE grupo IS NOT NULL AND grupo!='' GROUP BY grupo").fetchall()
    comercial = _coletar_metricas_comerciais(conn)
    conn.close()

    apify_info = {
        'usuario': '—',
        'plano': 'Sem token',
        'credito_disponivel': 0,
        'limite_mensal': 5,
    }
    erro = None

    try:
        token = get_api_token()
        if not token:
            erro = 'Token Apify não configurado'
        else:
            apify_info = testar_token_apify(token)
    except Exception as e:
        erro = str(e)

    return jsonify({
        'erro': erro,
        'apify': apify_info,
        'local': {
            'total_empresas': total_empresas,
            'sem_website': sem_site,
            'com_website': com_site,
            'total_buscas': total_buscas,
            'grupos': [{'grupo': g['grupo'], 'total': g['n']} for g in grupos]
        },
        'comercial': comercial,
    })

# ─────────────────────────────────────────
# ROTAS – BUSCA / SCRAPING
# ─────────────────────────────────────────
@app.route('/api/buscar', methods=['POST'])
def iniciar_busca():
    token = get_api_token()
    if not token:
        return jsonify({'erro': 'Token Apify não configurado'}), 400

    body      = request.json
    keyword   = body.get('keyword', '')
    segmento  = body.get('segmento', '')
    categoria = body.get('categoria', '')
    local     = body.get('localizacao', '')
    max_res   = int(body.get('max_resultados', 20))
    grupo     = body.get('grupo', '')
    # Filtros de prospecção
    filtro_site    = body.get('filtro_site', 'allPlaces')      # allPlaces | withoutWebsite | withWebsite
    so_com_tel     = body.get('so_com_telefone', False)        # filtro local pós-scraping
    pular_fechados = body.get('pular_fechados', True)
    # Reviews para geração de sites
    max_reviews    = int(body.get('max_reviews', 0))           # 0 = não coletar reviews

    conn = get_db()
    cur = conn.execute(
        "INSERT INTO buscas (keyword, segmento, categoria, localizacao, status) VALUES (?,?,?,?,?)",
        (keyword, segmento, categoria, local, 'rodando')
    )
    busca_id = cur.lastrowid
    conn.commit()
    conn.close()

    def rodar_apify():
        try:
            client = ApifyClient(token)
            run_input = {
                "searchStringsArray": [keyword or segmento],
                "locationQuery": local,
                "maxCrawledPlacesPerSearch": max_res,
                "language": "pt-BR",
                "countryCode": "br",
                "scrapePlaceDetailPage": True,
                "website": filtro_site,
                "skipClosedPlaces": bool(pular_fechados),
            }
            # Ativar coleta de reviews se solicitado
            if max_reviews > 0:
                run_input["maxReviews"] = max_reviews
                run_input["reviewsSort"] = "mostRelevant"
                run_input["reviewsTranslation"] = "originalAndTranslated"
            run        = client.actor("compass/crawler-google-places").call(run_input=run_input)
            run_id     = run.get('id', '')
            dataset_id = run.get('defaultDatasetId')

            conn2 = get_db()
            conn2.execute("UPDATE buscas SET apify_run_id=? WHERE id=?", (run_id, busca_id))
            conn2.commit()

            total = 0
            novos = 0
            duplicatas = 0
            for item in client.dataset(dataset_id).iterate_items():
                if not item.get('title'):
                    continue
                # Filtro local: só com telefone (para prospecto via WhatsApp)
                if so_com_tel and not (item.get('phone') or item.get('phoneUnformatted')):
                    continue
                e = extrair_empresa(item, segmento, keyword, categoria, local, grupo)
                cur2 = conn2.execute('''
                    INSERT OR IGNORE INTO empresas
                    (nome, subtitulo, descricao, categoria, categorias, preco,
                     endereco, rua, bairro, cidade, estado, cep, pais, plus_code,
                     latitude, longitude, telefone, telefone_formatado, website, tem_website,
                     menu_url, rating, reviews,
                     dist_1estrela, dist_2estrelas, dist_3estrelas, dist_4estrelas, dist_5estrelas,
                     fechado_permanente, fechado_temporario, reivindicado, qtd_fotos,
                     horario, google_maps_url, place_id, segmento, grupo, dados_extras)
                    VALUES
                    (:nome,:subtitulo,:descricao,:categoria,:categorias,:preco,
                     :endereco,:rua,:bairro,:cidade,:estado,:cep,:pais,:plus_code,
                     :latitude,:longitude,:telefone,:telefone_formatado,:website,:tem_website,
                     :menu_url,:rating,:reviews,
                     :dist_1estrela,:dist_2estrelas,:dist_3estrelas,:dist_4estrelas,:dist_5estrelas,
                     :fechado_permanente,:fechado_temporario,:reivindicado,:qtd_fotos,
                     :horario,:google_maps_url,:place_id,:segmento,:grupo,:dados_extras)
                ''', e)
                total += 1
                if cur2.rowcount > 0:
                    novos += 1       # empresa realmente inserida (nova)
                    empresa_id = cur2.lastrowid
                    # ── Salvar reviews se foram coletados ──
                    if max_reviews > 0:
                        reviews_raw = item.get('reviews', []) or []
                        for rv in reviews_raw[:max_reviews]:
                            conn2.execute('''
                                INSERT INTO reviews
                                (empresa_id, place_id, autor, nota, texto,
                                 data_review, resposta_dono, qtd_fotos_rev, idioma)
                                VALUES (?,?,?,?,?,?,?,?,?)
                            ''', (
                                empresa_id,
                                e.get('place_id', ''),
                                rv.get('name', '') or rv.get('reviewerName', ''),
                                rv.get('stars') or rv.get('rating'),
                                rv.get('text', '') or rv.get('reviewText', ''),
                                rv.get('publishedAtDate', '') or rv.get('date', ''),
                                (rv.get('responseFromOwnerText', '') or
                                 rv.get('ownerResponse', {}).get('text', '') if isinstance(rv.get('ownerResponse'), dict) else rv.get('ownerResponse', '')),
                                len(rv.get('reviewImageUrls', []) or []),
                                rv.get('reviewerLanguage', '') or rv.get('language', ''),
                            ))
                    # ── Opção 1: Auto-extrair nome do responsável ──
                    nome_resp = extrair_nome_responsavel(e.get('dados_extras', '{}'))
                    if nome_resp:
                        conn2.execute(
                            "UPDATE empresas SET nome_responsavel=? WHERE id=?",
                            (nome_resp, empresa_id)
                        )
                        print(f'[NomeResp] Extraído automaticamente: "{nome_resp}" para empresa {empresa_id}')
                else:
                    duplicatas += 1  # place_id já existia, ignorada

            conn2.execute(
                "UPDATE buscas SET status='concluido', total_encontrados=?, novos=?, duplicatas=?, finalizado_em=datetime('now') WHERE id=?",
                (total, novos, duplicatas, busca_id)
            )
            conn2.commit()
            conn2.close()

        except Exception as e:
            import traceback
            print(f"Erro Apify:\n{traceback.format_exc()}")
            conn3 = get_db()
            conn3.execute("UPDATE buscas SET status='erro' WHERE id=?", (busca_id,))
            conn3.commit()
            conn3.close()

    threading.Thread(target=rodar_apify, daemon=True).start()
    return jsonify({'ok': True, 'busca_id': busca_id, 'query': f"{keyword or segmento} em {local}"})

@app.route('/api/busca/<int:busca_id>/status')
def status_busca(busca_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM buscas WHERE id=?", (busca_id,)).fetchone()
    conn.close()
    if not row:
        return jsonify({'erro': 'Não encontrada'}), 404
    return jsonify(dict(row))

@app.route('/api/buscas')
def listar_buscas():
    conn = get_db()
    rows = conn.execute("SELECT * FROM buscas ORDER BY id DESC LIMIT 50").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

# ─────────────────────────────────────────
# ROTAS – EMPRESAS
# ─────────────────────────────────────────
@app.route('/api/empresas')
def listar_empresas():
    conn   = get_db()
    filtros, params = [], []
    filtros.append(
        """NOT EXISTS (
               SELECT 1
                 FROM kanban_contatos kc
                WHERE kc.empresa_id = empresas.id
                  AND COALESCE(kc.optout_global, 0) = 1
           )"""
    )
    if request.args.get('sem_site') == '1':
        filtros.append('tem_website = 0')
    if request.args.get('com_site') == '1':
        filtros.append('tem_website = 1')
    if request.args.get('grupo'):
        filtros.append('grupo = ?'); params.append(request.args.get('grupo'))
    if request.args.get('segmento'):
        filtros.append('segmento LIKE ?'); params.append(f"%{request.args.get('segmento')}%")
    if request.args.get('cidade'):
        filtros.append('cidade LIKE ?'); params.append(f"%{request.args.get('cidade')}%")
    if request.args.get('busca'):
        filtros.append('(nome LIKE ? OR endereco LIKE ? OR telefone LIKE ?)')
        t = f"%{request.args.get('busca')}%"; params += [t, t, t]
    if request.args.get('status'):
        filtros.append('status_prospeccao = ?'); params.append(request.args.get('status'))
    where = ('WHERE ' + ' AND '.join(filtros)) if filtros else ''
    rows = conn.execute(f"SELECT * FROM empresas {where} ORDER BY id DESC LIMIT 500", params).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/empresas/<int:emp_id>')
def detalhe_empresa(emp_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM empresas WHERE id=?", (emp_id,)).fetchone()
    conn.close()
    if not row: return jsonify({'erro': 'Não encontrada'}), 404
    return jsonify(dict(row))

@app.route('/api/empresas/<int:emp_id>', methods=['PATCH'])
def atualizar_empresa(emp_id):
    campos, params = [], []
    for k, v in request.json.items():
        campos.append(f"{k} = ?"); params.append(v)
    params.append(emp_id)
    conn = get_db()
    conn.execute(f"UPDATE empresas SET {', '.join(campos)} WHERE id=?", params)
    conn.commit(); conn.close()
    return jsonify({'ok': True})

@app.route('/api/empresas/<int:emp_id>', methods=['DELETE'])
def deletar_empresa(emp_id):
    conn = get_db()
    conn.execute("DELETE FROM empresas WHERE id=?", (emp_id,))
    conn.commit(); conn.close()
    return jsonify({'ok': True})

@app.route('/api/empresas/<int:emp_id>/reviews')
def listar_reviews(emp_id):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM reviews WHERE empresa_id=? ORDER BY nota DESC, id ASC",
        (emp_id,)
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

# ─────────────────────────────────────────
# ROTA – GERAR PDF DIAGNÓSTICO
# ─────────────────────────────────────────
@app.route('/api/empresas/<int:emp_id>/gerar-pdf')
def gerar_pdf_diagnostico(emp_id):
    if not REPORTLAB_OK:
        return jsonify({'erro': 'reportlab não instalado. Execute: pip install reportlab'}), 500

    conn = get_db()
    e = conn.execute("SELECT * FROM empresas WHERE id=?", (emp_id,)).fetchone()
    cfg_rows = conn.execute("SELECT chave, valor FROM config").fetchall()
    conn.close()
    if not e:
        return jsonify({'erro': 'Empresa não encontrada'}), 404

    e = dict(e)
    cfg = {r['chave']: r['valor'] for r in cfg_rows}

    # ── Monta dict de dados ──────────────────────────────────────
    dados = {
        'nome':              e.get('nome') or 'Empresa',
        'categoria':         e.get('categoria') or '',
        'telefone':          e.get('telefone_formatado') or e.get('telefone') or '',
        'endereco':          e.get('endereco') or '',
        'cidade':            ', '.join(filter(None, [e.get('cidade'), e.get('estado')])),
        'tem_website':       bool(e.get('tem_website')),
        'website_url':       e.get('website') or '',
        'avaliacao':         float(e.get('rating') or 0),
        'total_avaliacoes':  int(e.get('reviews') or 0),
        'total_fotos':       int(e.get('qtd_fotos') or 0),
        'distribuicao_estrelas': {
            5: int(e.get('dist_5estrelas') or 0),
            4: int(e.get('dist_4estrelas') or 0),
            3: int(e.get('dist_3estrelas') or 0),
            2: int(e.get('dist_2estrelas') or 0),
            1: int(e.get('dist_1estrela') or 0),
        },
        'seu_nome':      cfg.get('prospector_nome')    or 'ProspectLocal',
        'seu_whatsapp':  cfg.get('prospector_whatsapp') or '',
        'seu_servico':   cfg.get('prospector_servico')  or 'Criação de Sites Profissionais',
    }

    # ── Gera o PDF em memória ────────────────────────────────────
    buffer = io.BytesIO()
    _build_pdf(dados, buffer)
    buffer.seek(0)

    nome_arquivo = re.sub(r'[^\w\s-]', '', dados['nome']).strip().replace(' ', '_')
    nome_arquivo = f"diagnostico_{nome_arquivo}.pdf"

    return Response(
        buffer.read(),
        mimetype='application/pdf',
        headers={
            'Content-Disposition': f'attachment; filename="{nome_arquivo}"',
            'Content-Type': 'application/pdf'
        }
    )


# ─────────────────────────────────────────
# ROTA – ENVIAR ABERTURA "DIAGNÓSTICO" WA
# ─────────────────────────────────────────
@app.route('/api/empresas/<int:emp_id>/enviar-abertura-diagnostico', methods=['POST'])
def enviar_abertura_diagnostico(emp_id):
    """
    Envia mensagem de abertura pelo WhatsApp e marca o contato como
    aguardando confirmação para receber o PDF (pending_pdf=1).
    Body JSON: { numeroId, telefone, contatoId (opcional) }
    """
    payload = request.json or {}
    numero_id = payload.get('numeroId')
    telefone  = payload.get('telefone', '').replace('+', '').replace(' ', '').replace('-', '')

    if not numero_id or not telefone:
        return jsonify({'ok': False, 'erro': 'numeroId e telefone sao obrigatorios'}), 400

    conn = get_db()
    e = conn.execute("SELECT * FROM empresas WHERE id=?", (emp_id,)).fetchone()
    if not e:
        conn.close()
        return jsonify({'ok': False, 'erro': 'Empresa nao encontrada'}), 404
    e = dict(e)

    cfg = {r['chave']: r['valor'] for r in conn.execute("SELECT chave, valor FROM config").fetchall()}

    # Monta mensagem de abertura
    tpl = cfg.get('msg_abertura_diagnostico') or (
        "Oi! 👋\n\n"
        "Fiz uma analise rapida do perfil do *{nome}* no Google e montei um "
        "*Diagnostico Digital gratuito* sobre a presenca online de voces.\n\n"
        "Tem informacoes bem interessantes sobre avaliacoes, visibilidade e "
        "oportunidades que encontrei.\n\n"
        "Posso te enviar o relatorio? 📊"
    )
    nome_empresa = e.get('nome', 'sua empresa')
    mensagem = tpl.replace('{nome}', nome_empresa) \
                   .replace('{categoria}', e.get('categoria') or 'seu negocio') \
                   .replace('{cidade}', e.get('cidade') or '')

    # Envia mensagem via WA service
    wa_url = cfg.get('wa_service_url', 'http://localhost:3001')
    try:
        import urllib.request as _ur
        req_data = json.dumps({'numeroId': numero_id, 'telefone': telefone, 'mensagem': mensagem}).encode()
        req_obj  = _ur.Request(f'{wa_url}/api/enviar', data=req_data,
                               headers={'Content-Type': 'application/json'}, method='POST')
        with _ur.urlopen(req_obj, timeout=15) as resp:
            wa_result = json.loads(resp.read())
    except Exception as ex:
        conn.close()
        return jsonify({'ok': False, 'erro': f'Falha ao enviar WA: {str(ex)}'}), 500

    if not wa_result.get('ok'):
        conn.close()
        return jsonify({'ok': False, 'erro': wa_result.get('error', 'Erro WA')}), 500

    # Cria/atualiza contato no kanban com pending_pdf=1
    contato_id = payload.get('contatoId')
    if contato_id:
        conn.execute(
            """UPDATE kanban_contatos
               SET kanban_coluna='Enviado', pending_pdf=1,
                   numero_wa_id=?, atualizado_em=CURRENT_TIMESTAMP
               WHERE id=?""",
            (numero_id, contato_id)
        )
    else:
        existing = conn.execute(
            "SELECT id FROM kanban_contatos WHERE empresa_id=?", (emp_id,)
        ).fetchone()
        if existing:
            conn.execute(
                """UPDATE kanban_contatos
                   SET kanban_coluna='Enviado', pending_pdf=1,
                       numero_wa_id=?, telefone_wa=?, atualizado_em=CURRENT_TIMESTAMP
                   WHERE id=?""",
                (numero_id, telefone, existing['id'])
            )
            contato_id = existing['id']
        else:
            cur = conn.execute(
                """INSERT INTO kanban_contatos
                   (empresa_id, telefone_wa, kanban_coluna, numero_wa_id, pending_pdf)
                   VALUES (?,?,?,?,1)""",
                (emp_id, telefone, 'Enviado', numero_id)
            )
            contato_id = cur.lastrowid

    conn.commit()
    conn.close()
    return jsonify({'ok': True, 'contatoId': contato_id, 'mensagem': mensagem})



def _ensure_logo_assets():
    """Gera logos OtimizaAI se nao existirem."""
    import os as _os
    assets_dir = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), 'assets')
    logo_main = _os.path.join(assets_dir, 'logo_otimizaai.png')
    if _os.path.exists(logo_main):
        return  # ja existem
    try:
        from PIL import Image, ImageDraw, ImageFont
        import math
        _os.makedirs(assets_dir, exist_ok=True)

        def _make_logo(output, final_w, bg_color=None):
            SCALE = 4
            W = final_w * SCALE
            H = int(final_w * 0.48) * SCALE if bg_color is None else int(final_w * 0.22) * SCALE
            bg = (0,0,0,0) if bg_color is None else bg_color
            img = Image.new('RGBA', (W, H), bg)
            draw = ImageDraw.Draw(img)
            CYAN = (0,186,222); CYAN2 = (40,160,200); GOLD = (210,170,45); GOLD2 = (240,200,70)
            WHITE = (255,255,255); DBLUE = (15,35,90)

            if bg_color:
                # Header version: small globe left + text
                cx, cy = int(W*0.08), H//2
                R = int(H*0.35)
                draw.ellipse([cx-R,cy-R,cx+R,cy+R], outline=CYAN, width=SCALE*2)
                draw.ellipse([cx-int(R*0.5),cy-R,cx+int(R*0.5),cy+R], outline=(*CYAN,140), width=SCALE)
                draw.line([(cx-R,cy),(cx+R,cy)], fill=(*CYAN,140), width=SCALE)
                draw.line([(cx,cy-R),(cx,cy+R)], fill=(*CYAN,140), width=SCALE)
                def _star(d,x,y,r,c):
                    pts=[]
                    for i in range(10):
                        a=math.pi/5*i-math.pi/2; rad=r if i%2==0 else r*0.4
                        pts.append((x+rad*math.cos(a),y+rad*math.sin(a)))
                    d.polygon(pts,fill=c)
                for sx,sy in [(-R*0.8,-R*0.6),(R*0.3,-R*0.9),(R*1.0,-R*0.2)]:
                    _star(draw,int(cx+sx),int(cy+sy),int(R*0.2),GOLD2)
                try:
                    fb=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",int(H*0.38))
                    fl=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",int(H*0.18))
                except: fb=fl=ImageFont.load_default()
                tx=int(W*0.16); ty=int(H*0.15)
                t1,t2="Otimiza","AI"
                bb1=draw.textbbox((0,0),t1,font=fb); w1=bb1[2]-bb1[0]
                draw.text((tx,ty),t1,fill=WHITE,font=fb)
                draw.text((tx+w1,ty),t2,fill=GOLD,font=fb)
                draw.text((tx,ty+int(H*0.42)),"Presenca Digital",fill=CYAN,font=fl)
                fh = int(final_w*0.22)
            else:
                # Full logo version: globe center + stars + text
                cx,cy = W//2, int(H*0.38)
                R = int(W*0.14)
                draw.ellipse([cx-R,cy-R,cx+R,cy+R], outline=CYAN, width=SCALE*2)
                for frac in [-0.6,-0.3,0.0,0.3,0.6]:
                    dy=int(R*frac); dx=int(math.sqrt(max(0,R*R-dy*dy)))
                    draw.line([(cx-dx,cy+dy),(cx+dx,cy+dy)], fill=CYAN2, width=SCALE)
                for fw in [0.35,0.7]:
                    ew=int(R*fw)
                    draw.ellipse([cx-ew,cy-R,cx+ew,cy+R], outline=CYAN2, width=SCALE)
                draw.line([(cx,cy-R),(cx,cy+R)], fill=CYAN2, width=SCALE)
                ring_rx=int(R*1.55); ring_ry=int(R*0.45)
                for t in range(-3,4):
                    draw.ellipse([cx-ring_rx,cy-ring_ry+t,cx+ring_rx,cy+ring_ry+t],outline=(*CYAN,160),width=SCALE*2)
                def _star5(d,x,y,ro,ri,c):
                    pts=[]
                    for i in range(10):
                        a=math.pi/5*i-math.pi/2; rad=ro if i%2==0 else ri
                        pts.append((x+rad*math.cos(a),y+rad*math.sin(a)))
                    d.polygon(pts,fill=c)
                    pts2=[]
                    for i in range(10):
                        a=math.pi/5*i-math.pi/2; rad=(ro*0.7) if i%2==0 else (ri*0.7)
                        pts2.append((x+rad*math.cos(a)-ro*0.05,y+rad*math.sin(a)-ro*0.1))
                    d.polygon(pts2,fill=GOLD2)
                for sx,sy,sr in [(cx-R*1.3,cy-R*0.25,R*0.18),(cx-R*0.55,cy-R*0.78,R*0.15),
                                 (cx+R*0.25,cy-R*0.95,R*0.2),(cx+R*0.95,cy-R*0.6,R*0.17),(cx+R*1.4,cy+R*0.05,R*0.22)]:
                    _star5(draw,int(sx),int(sy),int(sr),int(sr*0.4),GOLD)
                try:
                    fb=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",int(W*0.072))
                    fl=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",int(W*0.035))
                except: fb=fl=ImageFont.load_default()
                ty=cy+R+int(H*0.06)
                t1,t2="Otimiza","AI"
                bb1=draw.textbbox((0,0),t1,font=fb); w1=bb1[2]-bb1[0]
                bb2=draw.textbbox((0,0),t2,font=fb); w2=bb2[2]-bb2[0]
                tx=(W-w1-w2)//2
                draw.text((tx+4,ty+4),t1,fill=(0,0,0,80),font=fb)
                draw.text((tx+w1+4,ty+4),t2,fill=(0,0,0,80),font=fb)
                draw.text((tx,ty),t1,fill=DBLUE,font=fb)
                draw.text((tx+w1,ty),t2,fill=GOLD,font=fb)
                sub="Presenca Digital"
                bbs=draw.textbbox((0,0),sub,font=fl); sw=bbs[2]-bbs[0]
                draw.text(((W-sw)//2,ty+int(H*0.08)),sub,fill=CYAN,font=fl)
                fh = int(final_w*0.48)
            final = img.resize((final_w, fh), Image.LANCZOS)
            final.save(output, 'PNG')

        _make_logo(logo_main, 600)
        _make_logo(_os.path.join(assets_dir, 'logo_otimizaai_header.png'), 500, bg_color=(11,29,78,255))
        _make_logo(_os.path.join(assets_dir, 'logo_otimizaai_cta.png'), 400)
        print('[Logo] Assets OtimizaAI gerados com sucesso')
    except Exception as e:
        print(f'[Logo] Aviso: nao foi possivel gerar logos: {e}')


def _draw_text_logo(c, center_x, baseline_y, brand='OtimizaAI', subtitle='Presenca Digital'):
    """Fallback simples em texto caso o arquivo de logo nao esteja disponivel."""
    from reportlab.lib import colors as _colors

    c.saveState()
    c.setFillColor(_colors.white)
    c.setFont('Helvetica-Bold', 24)
    c.drawCentredString(center_x, baseline_y, brand)
    c.setFillColor(_colors.HexColor('#93C5FD'))
    c.setFont('Helvetica', 9)
    c.drawCentredString(center_x, baseline_y - 14, subtitle)
    c.restoreState()


def _build_pdf_v4_legacy(d, output):
    """Gera PDF Diagnostico Digital v4 - OtimizaAI - Capa + Relatorio Moderno."""
    _ensure_logo_assets()
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas as _cm
    from reportlab.lib.utils import ImageReader
    from datetime import date as _date
    import os as _os

    W, H = A4
    data_str = _date.today().strftime('%d/%m/%Y')

    # ── Cores OtimizaAI ──────────────────────────────────────
    NAVY    = colors.HexColor('#0B1D4E')
    NAVY2   = colors.HexColor('#122A6B')
    NAVY3   = colors.HexColor('#0A1535')
    BLUE    = colors.HexColor('#1565C0')
    CYAN    = colors.HexColor('#00B4D8')
    GOLD    = colors.HexColor('#C9A227')
    GOLD_LT = colors.HexColor('#E8C94A')
    WHITE   = colors.white
    LIGHT   = colors.HexColor('#F4F7FF')
    CARD    = colors.HexColor('#FFFFFF')
    GRAY    = colors.HexColor('#8494A7')
    DARK    = colors.HexColor('#1E293B')
    GREEN   = colors.HexColor('#16A34A')
    RED     = colors.HexColor('#DC2626')
    ORANGE  = colors.HexColor('#EA580C')
    LGRAY   = colors.HexColor('#E2E8F0')

    # ── Dados ─────────────────────────────────────────────────
    nome      = d.get('nome', 'Empresa')
    categoria = d.get('categoria', '--')
    telefone  = d.get('telefone', '--')
    endereco  = d.get('endereco', '--')
    cidade    = d.get('cidade', '--')
    tem_web   = bool(d.get('tem_website'))
    web_url   = d.get('website_url', '')
    avaliacao = float(d.get('avaliacao', 0))
    n_rev     = int(d.get('total_avaliacoes', 0))
    n_fotos   = int(d.get('total_fotos', 0))
    dist      = d.get('distribuicao_estrelas', {})
    prosp     = d.get('seu_nome', 'OtimizaAI')
    wa_num    = re.sub(r'\D', '', d.get('seu_whatsapp', ''))

    # ── Scores ────────────────────────────────────────────────
    sc_pres = min(100, (40 if tem_web else 0) + round(min(n_fotos/20.0,1)*30)
                 + (10 if categoria!='--' else 0) + (10 if endereco!='--' else 0)
                 + (5 if telefone!='--' else 0))
    sc_rep  = min(100, (round((avaliacao/5.0)*60) if avaliacao>0 else 0)
                 + round(min(n_rev/100.0,1)*40))
    sc_eng  = min(100, round(min(n_fotos/30.0,1)*50) + round(min(n_rev/50.0,1)*50))
    sc_total = round(sc_pres*0.40 + sc_rep*0.35 + sc_eng*0.25)
    pot_pres = min(100, sc_pres + (40 if not tem_web else 0) + (15 if n_fotos<20 else 0))
    pot_rep  = min(100, sc_rep  + (10 if avaliacao<4.5 else 0) + (15 if n_rev<50 else 0))
    pot_eng  = min(100, sc_eng  + (20 if n_fotos<30 else 0) + (15 if n_rev<50 else 0))

    def sc_col(s):
        if s>=70: return GREEN
        if s>=40: return ORANGE
        return RED
    def sc_lbl(s):
        if s>=70: return 'Bom'
        if s>=40: return 'Regular'
        return 'Critico'

    # ── Recomendações ─────────────────────────────────────────
    recs = []
    if not tem_web:
        recs.append(('ALTA','Sem site profissional',
            '70% dos consumidores pesquisam no Google antes de contratar. Sem site, voce perde clientes para a concorrencia.'))
    if n_fotos<5:
        recs.append(('ALTA',f'Poucas fotos no perfil ({n_fotos})',
            'Negocios com +20 fotos recebem 35% mais cliques e transmitem muito mais confianca ao cliente.'))
    elif n_fotos<15:
        recs.append(('MEDIA',f'Fotos abaixo do ideal ({n_fotos})',
            'Ampliar para 20+ fotos aumenta visualizacoes e melhora posicionamento no Google Maps.'))
    if avaliacao>0 and avaliacao<4.0:
        recs.append(('ALTA',f'Avaliacao baixa ({avaliacao:.1f})',
            '70% dos consumidores evitam empresas com nota inferior a 4 estrelas no Google.'))
    if n_rev<10:
        recs.append(('MEDIA',f'Poucas avaliacoes ({n_rev})',
            'O Google prioriza perfis com mais avaliacoes. Peca para clientes avaliarem apos cada atendimento.'))
    elif n_rev<30:
        recs.append(('BAIXA',f'Ampliar avaliacoes ({n_rev})',
            'Incentivar mais avaliacoes pode dobrar sua visibilidade no Google Maps.'))
    neg = dist.get(1,0)+dist.get(2,0)
    if neg>=3 and n_rev>0 and (neg/n_rev)>0.15:
        recs.append(('ALTA',f'Avaliacoes negativas ({neg})',
            'Responder publicamente mostra profissionalismo e pode reverter percepcoes negativas.'))
    if not recs:
        recs.append(('BAIXA','Perfil bem configurado',
            'Continue pedindo avaliacoes para manter e ampliar sua visibilidade.'))

    wa_text = 'Gostaria de ver como ficou o meu site sem compromisso'
    wa_link = f'https://wa.me/55{wa_num}?text={wa_text.replace(" ","+")}' if wa_num else ''

    # ── Logos ─────────────────────────────────────────────────
    _here = _os.path.dirname(_os.path.abspath(__file__)) if '__file__' in dir() else ''
    def _find(n):
        for d2 in [_os.path.join(_here,'assets'), _os.path.join(_here,'..','assets'),
                   '/sessions/brave-adoring-hypatia/mnt/GOOGLE RASPAGEM AUTOMAÇÃO E PROPECÇÃO/ProspectLocal/assets']:
            p = _os.path.join(d2, n)
            if _os.path.exists(p): return p
        return None
    logo_main = _find('logo_otimizaai.png')
    logo_hdr  = _find('logo_otimizaai_header.png')
    logo_cta  = _find('logo_otimizaai_cta.png')

    # ── Helpers ───────────────────────────────────────────────
    def rrect(c, x, y, w, h, r, fill=None, stroke=None, sw=0.5):
        c.saveState()
        p = c.beginPath()
        p.moveTo(x+r,y); p.lineTo(x+w-r,y)
        p.arcTo(x+w-r,y,x+w,y+r,-90,90); p.lineTo(x+w,y+h-r)
        p.arcTo(x+w-r,y+h-r,x+w,y+h,0,90); p.lineTo(x+r,y+h)
        p.arcTo(x,y+h-r,x+r,y+h,90,90); p.lineTo(x,y+r)
        p.arcTo(x,y,x+r,y+r,180,90); p.close()
        if fill: c.setFillColor(fill)
        if stroke: c.setStrokeColor(stroke); c.setLineWidth(sw)
        c.drawPath(p, fill=1 if fill else 0, stroke=1 if stroke else 0)
        c.restoreState()

    def pbar(c, x, y, w, h, pct, col):
        rrect(c, x, y, w, h, h/2, fill=LGRAY)
        if pct > 0:
            rrect(c, x, y, max(h, pct/100.0*w), h, h/2, fill=col)

    def sec_title(c, x, y, txt, width):
        c.setFillColor(NAVY)
        c.setFont('Helvetica-Bold', 9)
        c.drawString(x, y, txt)
        c.setStrokeColor(CYAN)
        c.setLineWidth(1.5)
        c.line(x, y-3, x+width, y-3)
        return y - 8

    LM = 20*mm
    RM = W - 20*mm
    CW = RM - LM

    c = _cm.Canvas(output, pagesize=A4)

    # ==========================================================
    #  PÁGINA 1 — CAPA
    # ==========================================================
    # Full navy background
    c.setFillColor(NAVY3)
    c.rect(0, 0, W, H, fill=1, stroke=0)

    # Decorative gradient circles
    c.setFillColor(NAVY2)
    c.circle(W*0.8, H*0.85, 180, fill=1, stroke=0)
    c.circle(W*0.15, H*0.15, 120, fill=1, stroke=0)
    c.setFillColor(colors.HexColor('#0D2255'))
    c.circle(W*0.5, H*0.1, 90, fill=1, stroke=0)
    c.circle(W*0.9, H*0.4, 70, fill=1, stroke=0)

    # Gold accent line top
    c.setFillColor(GOLD)
    c.rect(0, H-6, W, 6, fill=1, stroke=0)

    # Cyan accent line bottom
    c.setFillColor(CYAN)
    c.rect(0, 0, W, 4, fill=1, stroke=0)

    # Vertical gold accent left
    c.setFillColor(GOLD)
    c.rect(LM - 4, H*0.25, 3, H*0.50, fill=1, stroke=0)

    # Logo grande centralizada
    if logo_main:
        try:
            lw, lh = 240, 115
            c.drawImage(ImageReader(logo_main), W/2-lw/2, H/2+30,
                       lw, lh, preserveAspectRatio=True, mask='auto')
        except:
            _draw_text_logo(c, W/2, H/2+80)
    else:
        c.setFillColor(WHITE)
        c.setFont('Helvetica-Bold', 36)
        c.drawCentredString(W/2, H/2+80, 'OtimizaAI')
        c.setFillColor(CYAN)
        c.setFont('Helvetica', 14)
        c.drawCentredString(W/2, H/2+60, 'Presenca Digital')

    # Divider line
    c.setStrokeColor(GOLD)
    c.setLineWidth(1.5)
    c.line(W/2-60, H/2+15, W/2+60, H/2+15)

    # "DIAGNÓSTICO DIGITAL"
    c.setFillColor(GOLD)
    c.setFont('Helvetica-Bold', 20)
    c.drawCentredString(W/2, H/2-15, 'DIAGNOSTICO DIGITAL')

    # "para [Empresa]"
    c.setFillColor(WHITE)
    c.setFont('Helvetica', 13)
    c.drawCentredString(W/2, H/2-38, 'para')

    c.setFillColor(WHITE)
    c.setFont('Helvetica-Bold', 16)
    nome_capa = nome[:45] + ('...' if len(nome)>45 else '')
    c.drawCentredString(W/2, H/2-58, nome_capa)

    # Info bottom area
    c.setFillColor(GRAY)
    c.setFont('Helvetica', 9)
    c.drawCentredString(W/2, H*0.18, f'{categoria}  |  {cidade}')
    c.drawCentredString(W/2, H*0.18 - 14, data_str)

    # Footer capa
    c.setFillColor(colors.HexColor('#3A4D7A'))
    c.setFont('Helvetica', 7)
    c.drawCentredString(W/2, 20, f'Preparado por {prosp}  |  Documento confidencial')

    # ==========================================================
    #  PÁGINA 2 — RELATÓRIO
    # ==========================================================
    c.showPage()
    c.setFillColor(LIGHT)
    c.rect(0, 0, W, H, fill=1, stroke=0)

    # Mini header bar
    rrect(c, LM, H-14*mm-24, CW, 24, 6, fill=NAVY)
    c.setFillColor(GOLD)
    c.rect(LM, H-14*mm-24, CW, 3, fill=1, stroke=0)
    if logo_hdr:
        try:
            c.drawImage(ImageReader(logo_hdr), LM+6, H-14*mm-22, 90, 20,
                       preserveAspectRatio=True, mask='auto')
        except: pass
    c.setFillColor(WHITE)
    c.setFont('Helvetica-Bold', 9)
    c.drawRightString(RM-8, H-14*mm-12, nome[:40])
    c.setFillColor(GRAY)
    c.setFont('Helvetica', 7)
    c.drawRightString(RM-8, H-14*mm-20, data_str)

    y = H - 14*mm - 38

    # ── INFO DA EMPRESA ───────────────────────────────────────
    y = sec_title(c, LM, y, 'INFORMACOES DA EMPRESA', CW)

    cell_w = CW / 3
    cell_h = 34
    info = [('Categoria', categoria), ('Cidade', cidade), ('Telefone', telefone),
            ('Website', web_url[:30] if tem_web else 'Nao possui'),
            ('Endereco', endereco[:30]),
            ('Avaliacao', f'{avaliacao:.1f} estrelas  |  {n_rev} reviews' if avaliacao else '--')]

    for idx, (label, val) in enumerate(info):
        col2 = idx % 3
        row = idx // 3
        cx2 = LM + col2*cell_w
        cy2 = y - row*cell_h - cell_h
        bg = CARD if row%2==0 else colors.HexColor('#F8FAFF')
        rrect(c, cx2+1, cy2+1, cell_w-2, cell_h-2, 4, fill=bg)
        c.setFillColor(GRAY)
        c.setFont('Helvetica', 7)
        c.drawString(cx2+8, cy2+cell_h-12, label)
        c.setFillColor(DARK)
        c.setFont('Helvetica-Bold', 8.5)
        c.drawString(cx2+8, cy2+8, str(val))

    y -= 2*cell_h + 12

    # ── PONTUAÇÃO POR CATEGORIA ───────────────────────────────
    y = sec_title(c, LM, y, 'PONTUACAO POR CATEGORIA', CW)

    card_w = (CW - 16) / 3
    card_h = 110
    cats = [
        ('Presenca Online', sc_pres, [('Website','Sim' if tem_web else 'Nao'),('Fotos',str(n_fotos))]),
        ('Reputacao', sc_rep, [('Avaliacao',f'{avaliacao:.1f}' if avaliacao else '--'),('Reviews',str(n_rev))]),
        ('Engajamento', sc_eng, [('Fotos',str(n_fotos)),('Reviews',str(n_rev))]),
    ]

    for i, (cat_name, cat_sc, subs) in enumerate(cats):
        cx2 = LM + i*(card_w+8)
        cy2 = y - card_h
        col2 = sc_col(cat_sc)

        # Card with shadow
        rrect(c, cx2+2, cy2-2, card_w, card_h, 8, fill=colors.HexColor('#D0D8E8'))
        rrect(c, cx2, cy2, card_w, card_h, 8, fill=CARD)

        # Color top bar
        c.setFillColor(col2)
        c.rect(cx2+8, cy2+card_h-5, card_w-16, 5, fill=1, stroke=0)

        # Score circle
        scx = cx2 + card_w/2
        scy = cy2 + card_h - 32
        # Outer ring
        c.setStrokeColor(col2)
        c.setLineWidth(3)
        c.circle(scx, scy, 22, fill=0, stroke=1)
        # Inner fill
        c.setFillColor(col2)
        c.circle(scx, scy, 18, fill=1, stroke=0)
        c.setFillColor(WHITE)
        c.setFont('Helvetica-Bold', 16)
        c.drawCentredString(scx, scy-6, str(cat_sc))

        # Name
        c.setFillColor(DARK)
        c.setFont('Helvetica-Bold', 8)
        c.drawCentredString(cx2+card_w/2, cy2+card_h-62, cat_name.upper())

        # Label
        c.setFillColor(col2)
        c.setFont('Helvetica-Bold', 7.5)
        c.drawCentredString(cx2+card_w/2, cy2+card_h-72, sc_lbl(cat_sc))

        # Progress bar
        pbar(c, cx2+12, cy2+25, card_w-24, 6, cat_sc, col2)

        # Sub-metrics
        for j, (sl, sv) in enumerate(subs):
            sx = cx2+12 + j*(card_w-24)/2
            c.setFillColor(GRAY)
            c.setFont('Helvetica', 6.5)
            c.drawString(sx, cy2+14, sl)
            c.setFillColor(DARK)
            c.setFont('Helvetica-Bold', 8)
            c.drawString(sx, cy2+5, sv)

    y -= card_h + 14

    # ── PONTUAÇÃO GERAL ───────────────────────────────────────
    ov_h = 48
    rrect(c, LM, y-ov_h, CW, ov_h, 10, fill=NAVY)
    c.setFillColor(GOLD)
    c.rect(LM, y-ov_h, CW, 3, fill=1, stroke=0)

    c.setFillColor(WHITE)
    c.setFont('Helvetica', 9)
    c.drawCentredString(W/2-5, y-ov_h+ov_h-14, 'PONTUACAO GERAL')

    c.setFillColor(GOLD)
    c.setFont('Helvetica-Bold', 30)
    c.drawCentredString(W/2-5, y-ov_h+10, str(sc_total))
    c.setFillColor(GRAY)
    c.setFont('Helvetica', 10)
    c.drawString(W/2+18, y-ov_h+14, '/ 100')

    lbl_c = sc_col(sc_total)
    rrect(c, RM-70, y-ov_h+(ov_h-20)/2, 60, 20, 10, fill=lbl_c)
    c.setFillColor(WHITE)
    c.setFont('Helvetica-Bold', 8)
    c.drawCentredString(RM-40, y-ov_h+(ov_h-20)/2+6, sc_lbl(sc_total).upper())

    y -= ov_h + 14

    # ── RECOMENDAÇÕES ─────────────────────────────────────────
    y = sec_title(c, LM, y, 'RECOMENDACOES', CW)

    pcolors = {'ALTA':RED, 'MEDIA':ORANGE, 'BAIXA':CYAN}
    pbgs = {'ALTA':colors.HexColor('#FFF5F5'),'MEDIA':colors.HexColor('#FFFBF0'),'BAIXA':colors.HexColor('#F0FAFF')}

    for prio, title, desc in recs[:3]:
        rec_h = 50
        if y - rec_h < 18*mm: break
        pcol = pcolors.get(prio, GRAY)
        pbg = pbgs.get(prio, CARD)

        # Shadow
        rrect(c, LM+2, y-rec_h-1, CW, rec_h, 6, fill=colors.HexColor('#E0E4EC'))
        rrect(c, LM, y-rec_h, CW, rec_h, 6, fill=pbg)
        rrect(c, LM, y-rec_h, CW, rec_h, 6, stroke=colors.HexColor('#E2E8F0'), sw=0.5)

        # Priority pill
        pill_w = 28
        rrect(c, LM+4, y-rec_h+rec_h/2-15, pill_w, 30, 6, fill=pcol)
        c.saveState()
        c.setFillColor(WHITE)
        c.setFont('Helvetica-Bold', 6.5)
        c.translate(LM+4+pill_w/2, y-rec_h+rec_h/2)
        c.rotate(90)
        c.drawCentredString(0, -3, prio)
        c.restoreState()

        # Title
        c.setFillColor(DARK)
        c.setFont('Helvetica-Bold', 9)
        c.drawString(LM+40, y-14, title[:50])

        # Desc
        c.setFillColor(GRAY)
        c.setFont('Helvetica', 7.5)
        words = desc.split()
        line = ''; ty = y-26; mw = CW-50
        for w2 in words:
            t = (line+' '+w2).strip()
            if c.stringWidth(t,'Helvetica',7.5) < mw:
                line = t
            else:
                c.drawString(LM+40, ty, line); ty -= 10; line = w2
        if line: c.drawString(LM+40, ty, line)

        # Impact tag
        tag = f'Impacto: {prio}'
        tw = c.stringWidth(tag,'Helvetica-Bold',7)+10
        rrect(c, RM-tw-4, y-rec_h+5, tw, 13, 4, fill=pcol)
        c.setFillColor(WHITE)
        c.setFont('Helvetica-Bold', 7)
        c.drawString(RM-tw+1, y-rec_h+8, tag)

        y -= rec_h + 6

    # Footer pag 2
    c.setFillColor(GRAY)
    c.setFont('Helvetica', 6.5)
    c.drawCentredString(W/2, 8*mm, f'{prosp}  |  Diagnostico Digital  |  {data_str}  |  Pagina 2')

    # ==========================================================
    #  PÁGINA 3 — EVOLUÇÃO + CTA
    # ==========================================================
    c.showPage()
    c.setFillColor(LIGHT)
    c.rect(0, 0, W, H, fill=1, stroke=0)

    # Mini header
    rrect(c, LM, H-14*mm-24, CW, 24, 6, fill=NAVY)
    c.setFillColor(GOLD)
    c.rect(LM, H-14*mm-24, CW, 3, fill=1, stroke=0)
    if logo_hdr:
        try:
            c.drawImage(ImageReader(logo_hdr), LM+6, H-14*mm-22, 90, 20,
                       preserveAspectRatio=True, mask='auto')
        except: pass
    c.setFillColor(WHITE)
    c.setFont('Helvetica-Bold', 9)
    c.drawRightString(RM-8, H-14*mm-12, nome[:40])
    c.setFillColor(GRAY)
    c.setFont('Helvetica', 7)
    c.drawRightString(RM-8, H-14*mm-20, data_str)

    y = H - 14*mm - 38

    # ── EVOLUÇÃO POTENCIAL ────────────────────────────────────
    y = sec_title(c, LM, y, 'EVOLUCAO POTENCIAL COM OTIMIZAAI', CW)

    ch_h = 165
    ch_y = y - ch_h
    # Chart bg with shadow
    rrect(c, LM+2, ch_y-2, CW, ch_h, 8, fill=colors.HexColor('#D8DFF0'))
    rrect(c, LM, ch_y, CW, ch_h, 8, fill=CARD)

    gx = LM + 35
    gy = ch_y + 28
    gw = CW - 50
    gh = ch_h - 52

    # Grid
    for i in range(5):
        gy2 = gy + (i/4.0)*gh
        c.setStrokeColor(colors.HexColor('#EDF0F7'))
        c.setLineWidth(0.4)
        c.line(gx, gy2, gx+gw, gy2)
        c.setFillColor(GRAY)
        c.setFont('Helvetica', 6.5)
        c.drawRightString(gx-4, gy2-2, str(i*25))

    # Legend
    lgx = gx+gw-100
    lgy = ch_y+ch_h-14
    rrect(c, lgx, lgy-2, 12, 8, 2, fill=BLUE)
    c.setFillColor(DARK)
    c.setFont('Helvetica', 7)
    c.drawString(lgx+14, lgy, 'Atual')
    rrect(c, lgx+48, lgy-2, 12, 8, 2, fill=GOLD)
    c.drawString(lgx+63, lgy, 'Com OtimizaAI')

    # Bars
    cats3 = [('Presenca\nOnline',sc_pres,pot_pres),('Reputacao',sc_rep,pot_rep),('Engajamento',sc_eng,pot_eng)]
    grp_w = gw / 3
    bw = grp_w * 0.22

    for i, (cn, cur, pot) in enumerate(cats3):
        bx = gx + i*grp_w + grp_w*0.2
        cur_h = max(3, (cur/100.0)*gh)
        pot_h = max(3, (pot/100.0)*gh)

        rrect(c, bx, gy, bw, cur_h, 3, fill=BLUE)
        c.setFillColor(WHITE)
        c.setFont('Helvetica-Bold', 7.5)
        if cur_h > 16:
            c.drawCentredString(bx+bw/2, gy+cur_h-10, str(cur))
        else:
            c.setFillColor(BLUE)
            c.drawCentredString(bx+bw/2, gy+cur_h+3, str(cur))

        rrect(c, bx+bw+4, gy, bw, pot_h, 3, fill=GOLD)
        c.setFillColor(DARK)
        c.setFont('Helvetica-Bold', 7.5)
        c.drawCentredString(bx+bw+4+bw/2, gy+pot_h+3, str(pot))

        delta = pot-cur
        if delta > 0:
            c.setFillColor(GREEN)
            c.setFont('Helvetica-Bold', 7)
            c.drawString(bx+bw*2+10, gy+cur_h+(pot_h-cur_h)/2, f'+{delta}')

        lines = cn.split('\n')
        for li, ln in enumerate(lines):
            c.setFillColor(DARK)
            c.setFont('Helvetica', 7)
            c.drawCentredString(bx+bw+2, gy-10-li*9, ln)

    y = ch_y - 20

    # ── CTA ───────────────────────────────────────────────────
    cta_h = 250
    cta_y = y - cta_h

    rrect(c, LM, cta_y, CW, cta_h, 12, fill=NAVY)

    # Decorative
    c.setFillColor(NAVY2)
    c.circle(RM-20, cta_y+cta_h-20, 40, fill=1, stroke=0)
    c.circle(LM+12, cta_y+25, 25, fill=1, stroke=0)

    c.setFillColor(CYAN)
    c.rect(LM, cta_y+cta_h-5, CW, 5, fill=1, stroke=0)
    c.setFillColor(GOLD)
    c.rect(LM, cta_y, CW, 4, fill=1, stroke=0)

    # Logo CTA
    _lp = logo_cta or logo_main
    if _lp:
        try:
            c.drawImage(ImageReader(_lp), W/2-65, cta_y+cta_h-75,
                       130, 62, preserveAspectRatio=True, mask='auto')
        except:
            c.setFillColor(WHITE)
            c.setFont('Helvetica-Bold', 20)
            c.drawCentredString(W/2, cta_y+cta_h-35, 'OtimizaAI')
    else:
        c.setFillColor(WHITE)
        c.setFont('Helvetica-Bold', 20)
        c.drawCentredString(W/2, cta_y+cta_h-35, 'OtimizaAI')

    # Gold divider
    c.setStrokeColor(GOLD)
    c.setLineWidth(1)
    dcy = cta_y + cta_h - 82
    c.line(W/2-35, dcy, W/2+35, dcy)

    # Headline
    c.setFillColor(GOLD)
    c.setFont('Helvetica-Bold', 12)
    nt = nome[:38]+('...' if len(nome)>38 else '')
    c.drawCentredString(W/2, dcy-16, f'Criamos um site para {nt}!')

    c.setFillColor(colors.HexColor('#93C5FD'))
    c.setFont('Helvetica', 9)
    c.drawCentredString(W/2, dcy-30, 'Gostaria de dar uma olhada? Sem compromisso algum.')

    # Benefits
    bens = [
        'Site profissional otimizado para aparecer no Google',
        'Pagina com botao direto para o WhatsApp do negocio',
        'Personalizado com as cores e nome da sua empresa',
    ]
    by2 = dcy - 50
    for b in bens:
        rrect(c, LM+45, by2-2, 14, 14, 3, fill=GREEN)
        c.setFillColor(WHITE)
        c.setFont('Helvetica-Bold', 9)
        c.drawCentredString(LM+52, by2, 'V')
        c.setFillColor(WHITE)
        c.setFont('Helvetica', 8.5)
        c.drawString(LM+66, by2+1, b)
        by2 -= 20

    # Button
    btn_w = 210
    btn_h = 32
    btn_x = W/2 - btn_w/2
    btn_y = by2 - 18
    rrect(c, btn_x+2, btn_y-2, btn_w, btn_h, 8, fill=colors.HexColor('#A88520'))
    rrect(c, btn_x, btn_y, btn_w, btn_h, 8, fill=GOLD)
    c.setFillColor(NAVY)
    c.setFont('Helvetica-Bold', 9.5)
    c.drawCentredString(W/2, btn_y+11, 'QUERO VER COMO FICOU MEU SITE')

    if wa_link:
        c.setFillColor(CYAN)
        c.setFont('Helvetica', 6.5)
        c.drawCentredString(W/2, btn_y-12, wa_link[:70])

    c.setFillColor(GRAY)
    c.setFont('Helvetica', 6)
    c.drawCentredString(W/2, cta_y+10, f'Preparado por {prosp}  |  Diagnostico gratuito, sem compromisso')

    # Page footer
    c.setFillColor(GRAY)
    c.setFont('Helvetica', 6.5)
    c.drawCentredString(W/2, 8*mm, f'{prosp}  |  Diagnostico Digital  |  {data_str}  |  Pagina 3')

    c.save()


def _build_pdf(d, output):
    try:
        from .diagnostic_pdf_html import build_diagnostic_pdf_html
    except ImportError:
        from diagnostic_pdf_html import build_diagnostic_pdf_html

    try:
        return build_diagnostic_pdf_html(
            d,
            output,
            ensure_logo_assets=_ensure_logo_assets,
            draw_text_logo=_draw_text_logo,
        )
    except Exception:
        try:
            from .pdf_builder_v5 import build_diagnostic_pdf
        except ImportError:
            from pdf_builder_v5 import build_diagnostic_pdf

        return build_diagnostic_pdf(
            d,
            output,
            ensure_logo_assets=_ensure_logo_assets,
            draw_text_logo=_draw_text_logo,
        )


@app.route('/api/templates')
def listar_templates():
    conn = get_db()
    rows = conn.execute("SELECT id, nome, keywords, ativo FROM template_segmentos ORDER BY nome").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/templates/<int:tid>')
def get_template(tid):
    conn = get_db()
    row = conn.execute("SELECT * FROM template_segmentos WHERE id=?", (tid,)).fetchone()
    conn.close()
    if not row: return jsonify({'erro': 'Não encontrado'}), 404
    return jsonify(dict(row))

@app.route('/api/templates', methods=['POST'])
def criar_template():
    d = request.json
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO template_segmentos (nome, keywords, prompt_template) VALUES (?,?,?)",
        (d.get('nome',''), d.get('keywords',''), d.get('prompt_template',''))
    )
    conn.commit(); conn.close()
    return jsonify({'ok': True, 'id': cur.lastrowid})

@app.route('/api/templates/<int:tid>', methods=['PUT'])
def atualizar_template(tid):
    d = request.json
    conn = get_db()
    conn.execute(
        "UPDATE template_segmentos SET nome=?, keywords=?, prompt_template=?, ativo=?, atualizado_em=datetime('now') WHERE id=?",
        (d.get('nome'), d.get('keywords'), d.get('prompt_template'), d.get('ativo', 1), tid)
    )
    conn.commit(); conn.close()
    return jsonify({'ok': True})

@app.route('/api/templates/<int:tid>', methods=['DELETE'])
def deletar_template(tid):
    conn = get_db()
    conn.execute("DELETE FROM template_segmentos WHERE id=?", (tid,))
    conn.commit(); conn.close()
    return jsonify({'ok': True})

# ─────────────────────────────────────────
# GERADOR DE PROMPT LOVABLE — baseado na skill lovable-site
# ─────────────────────────────────────────
_NICHOS_DB = {
    # SAÚDE & BELEZA
    'salao|beleza|cabeleireiro|cabelo': {
        'paleta': 'nude rosé (#F5E6E0), dourado (#D4AF37), preto fosco (#1C1917), branco gelo (#FAFAF9)',
        'estilo': 'luxuoso, elegante, clean — muito espaço em branco e tipografia refinada',
        'fontes': 'Playfair Display (serifada) para títulos, Inter para corpo',
        'icones': 'Scissors, Star, Heart, Calendar, MapPin, Sparkles',
        'imagens': 'ambiente iluminado e elegante de salão, cadeiras modernas, produtos premium, close de mãos ou cabelos, luz natural suave entrando pela janela',
        'pattern_break': 'seção de destaques com fundo preto ou grafite entre seções claras; borda dourada em cards de serviços',
        'cta': 'Agendar pelo WhatsApp',
        'secoes_extra': 'Galeria de resultados antes/depois',
    },
    'barbearia|barber': {
        'paleta': 'preto fosco (#1C1917), dourado (#D4AF37), branco gelo (#FAFAF9), cinza grafite (#44403C)',
        'estilo': 'masculino, elegante, bold — alto contraste com toques dourados',
        'fontes': 'Outfit Bold para títulos, Inter para corpo',
        'icones': 'Scissors, Star, Calendar, MapPin, Clock, Crown',
        'imagens': 'interior de barbearia moderna com cadeiras de couro, espelhos iluminados, barbeiro trabalhando com navalha, detalhes de ferramentas vintage, atmosfera masculina e sofisticada',
        'pattern_break': 'seção de serviços em fundo preto com detalhes dourados; galeria em grid escuro',
        'cta': 'Agendar Horário',
        'secoes_extra': 'Galeria de cortes realizados',
    },
    'academia|personal|fitness|crossfit': {
        'paleta': 'preto (#0A0A0A), vermelho (#DC2626), laranja (#EA580C), amarelo neon (#FACC15), branco',
        'estilo': 'energético, moderno, bold — fontes pesadas, contraste alto, impacto visual',
        'fontes': 'fontes condensadas e bold para títulos, clean sans-serif para corpo',
        'icones': 'Dumbbell, Flame, Trophy, Clock, Users, Zap',
        'imagens': 'pessoas treinando com energia e suor, equipamentos modernos, transformações corporais, ambiente amplo e iluminado com ferro e borracha',
        'pattern_break': 'seção com fundo preto e texto em amarelo/laranja neon; contador de alunos ou resultados com fundo vibrante',
        'cta': 'Começar Agora',
        'secoes_extra': 'Planos/modalidades, Transformações (antes/depois)',
    },
    # SAÚDE & CLÍNICAS
    'dentista|odonto|clinica odonto': {
        'paleta': 'azul claro (#60A5FA), verde menta (#34D399), branco (#FFFFFF), cinza suave (#F1F5F9)',
        'estilo': 'limpo, confiável, tranquilizador — transmite higiene e profissionalismo',
        'fontes': 'Plus Jakarta Sans para títulos, Inter para corpo',
        'icones': 'Smile, Star, Calendar, Shield, Award, Heart',
        'imagens': 'sorriso branco e saudável em close, ambiente clínico moderno e acolhedor, profissional com jaleco branco e luvas, equipamento dental moderno',
        'pattern_break': 'seção de especialidades com ícones grandes em fundo azul claro; depoimentos em carrossel com fundo branco e bordas arredondadas',
        'cta': 'Agende sua Consulta',
        'secoes_extra': 'Especialidades (implante, clareamento, ortodontia), Galeria de sorrisos',
    },
    'psicolog|terapeut': {
        'paleta': 'verde sálvia (#A3B18A), terracota suave (#C4A882), bege (#F5F0EB), branco, nude',
        'estilo': 'acolhedor, sereno, humano — minimalista com toque orgânico',
        'fontes': 'fontes suaves e humanistas para títulos, Inter Light para corpo',
        'icones': 'Heart, Brain, Shield, Calendar, Leaf, Sun',
        'imagens': 'ambiente aconchegante com plantas verdes, sofá confortável, luz natural difusa, profissional em postura acolhedora e atenta',
        'pattern_break': 'citação inspiradora em fundo verde sálvia suave; seção "Como funciona" com passos numerados em círculos',
        'cta': 'Agendar Consulta',
        'secoes_extra': 'Abordagem terapêutica, Especialidades',
    },
    'veterinar|pet shop|pet': {
        'paleta': 'verde (#16A34A), azul (#2563EB), amarelo (#FACC15), branco, laranja (#FB923C)',
        'estilo': 'alegre, acolhedor, transmite cuidado com animais',
        'fontes': 'Outfit para títulos, Inter para corpo',
        'icones': 'Heart, Star, Calendar, Shield, PawPrint, Stethoscope',
        'imagens': 'cachorro e gato felizes juntos, veterinário acariciando animal com carinho, ambiente limpo e colorido com brinquedos de pet',
        'pattern_break': 'seção de pets atendidos em grade colorida; ícones com patas estilizadas',
        'cta': 'Agendar Consulta',
        'secoes_extra': 'Serviços (consulta, vacinação, banho e tosa), Galeria de pets',
    },
    # ALIMENTAÇÃO
    'restaurante|pizzaria|hamburgueria|lanchonete|espetaria|churrascaria': {
        'paleta': 'vermelho (#DC2626), amarelo dourado (#D4AF37), preto (#0A0A0A), branco, creme (#FFFBEB)',
        'estilo': 'apetitoso, quente, convidativo — as fotos dos pratos devem dominar',
        'fontes': 'fontes bold e expressivas para títulos, clean para corpo',
        'icones': 'UtensilsCrossed, Star, MapPin, Clock, Phone, Flame, Truck',
        'imagens': 'foto close bem iluminada do prato principal com vapor subindo, ambiente do restaurante com mesas ocupadas e iluminação quente, ingredientes frescos em composição artística',
        'pattern_break': 'seção de cardápio em fundo escuro com fotos dos pratos; seção de depoimentos em fundo vermelho escuro; contador de clientes atendidos',
        'cta': 'Fazer Pedido',
        'secoes_extra': 'Cardápio (destaques com fotos), Delivery/reservas',
    },
    'padaria|confeitaria|bolo': {
        'paleta': 'marrom quente (#92400E), bege (#D4B896), dourado (#D4AF37), branco, creme (#FFFBEB)',
        'estilo': 'artesanal, acolhedor, apetitoso — tons quentes que lembram forno',
        'fontes': 'fontes com personalidade artesanal para títulos, Inter para corpo',
        'icones': 'CakeSlice, Coffee, Clock, MapPin, Star, Heart',
        'imagens': 'pão dourado saindo do forno com vapor, bolo decorado artisticamente, vitrine de doces coloridos e apetitosos, ambiente aconchegante de padaria com madeira e vidro',
        'pattern_break': 'seção de especialidades em fundo marrom escuro com texto claro; galeria de produtos em grid masonry',
        'cta': 'Fazer Encomenda',
        'secoes_extra': 'Vitrine de produtos, Encomendas',
    },
    # AUTOMOTIVO
    'insulfilm|pelicula|film': {
        'paleta': 'preto (#0A0A0A), cinza escuro (#27272A), prata (#A1A1AA), azul escuro (#1E3A5F), neon azul (#00B4D8)',
        'estilo': 'moderno, tecnológico, premium — alto contraste com toques de neon',
        'fontes': 'sans-serif bold e geométricas para títulos, Inter para corpo',
        'icones': 'Car, Shield, Sun, Thermometer, Star, Award, Eye',
        'imagens': 'carro de luxo com película escura brilhando sob a luz, profissional aplicando película com precisão, resultado antes e depois em split screen, prédio com película refletiva espelhando o céu',
        'pattern_break': 'seção de benefícios em fundo preto com ícones brilhantes neon; antes/depois em split screen interativo',
        'cta': 'Solicitar Orçamento',
        'secoes_extra': 'Tipos de película (residencial, automotiva, comercial), Galeria antes/depois',
    },
    'oficina|mecanica|mecanico|auto center|auto eletrica': {
        'paleta': 'vermelho (#DC2626), preto (#0A0A0A), cinza (#44403C), laranja (#EA580C), branco',
        'estilo': 'robusto, confiável, técnico — transmite competência e força',
        'fontes': 'fontes bold e condensadas para títulos',
        'icones': 'Wrench, Shield, Clock, Star, Truck, Settings, CheckCircle',
        'imagens': 'mecânico trabalhando concentrado em motor, ferramentas organizadas na oficina, carro sendo revisado em elevador, ambiente profissional e limpo',
        'pattern_break': 'seção de serviços com ícones em fundo vermelho escuro; diferenciais com números grandes em destaque',
        'cta': 'Orçamento Rápido',
        'secoes_extra': 'Serviços especializados, Galeria de trabalhos',
    },
    'lava rapido|lavagem|lava car|lava jato': {
        'paleta': 'azul (#2563EB), branco, verde (#10B981), amarelo (#FACC15)',
        'estilo': 'limpo, ágil, confiável — frescor e brilho',
        'fontes': 'Outfit para títulos, Inter para corpo',
        'icones': 'Droplets, Car, Star, Clock, Shield, Sparkles',
        'imagens': 'carro brilhando após lavagem com reflexo perfeito, jato de água em ação, equipe profissional trabalhando, resultado impecável de polimento',
        'pattern_break': 'seção de pacotes com fundo azul escuro; antes/depois em cards lado a lado',
        'cta': 'Agendar Lavagem',
        'secoes_extra': 'Pacotes de serviço, Tabela de preços',
    },
    # JURÍDICO & FINANCEIRO
    'advogad|advocacia|juridico|escritorio de direito': {
        'paleta': 'azul marinho (#1E3A5F), dourado (#D4AF37), branco (#FFFFFF), cinza escuro (#1F2937)',
        'estilo': 'formal, sério, autoridade e confiança — elegância clássica',
        'fontes': 'serifadas clássicas (Playfair Display) para títulos, Inter para corpo',
        'icones': 'Scale, Shield, BookOpen, Award, Phone, Gavel',
        'imagens': 'escritório elegante com estante de livros de direito, advogado em postura profissional e confiante, balança da justiça dourada, ambiente corporativo sofisticado',
        'pattern_break': 'seção de áreas de atuação em fundo azul marinho com texto claro e ícones dourados; citação jurídica em destaque',
        'cta': 'Agendar Consulta',
        'secoes_extra': 'Áreas de atuação, Equipe de advogados',
    },
    'contabil|contador|contabilidade': {
        'paleta': 'azul (#2563EB), verde (#10B981), branco, cinza (#64748B)',
        'estilo': 'profissional, organizado, confiável — números e gráficos',
        'fontes': 'Plus Jakarta Sans para títulos, Inter para corpo',
        'icones': 'Calculator, BarChart, Shield, FileText, Users, TrendingUp',
        'imagens': 'profissional analisando gráficos e planilhas, escritório organizado e moderno, reunião com cliente, dashboard financeiro',
        'pattern_break': 'seção de serviços com ícones em grid; diferenciais com números animados de destaque',
        'cta': 'Falar com Contador',
        'secoes_extra': 'Serviços (MEI, empresa, IRPF)',
    },
    # IMOBILIÁRIA
    'imobiliaria|imoveis|corretor de imoveis': {
        'paleta': 'azul marinho (#1E3A5F), dourado (#D4AF37), branco, cinza (#F1F5F9)',
        'estilo': 'confiável, elegante, profissional — transmite solidez',
        'fontes': 'Plus Jakarta Sans para títulos, Inter para corpo',
        'icones': 'Home, Key, MapPin, Star, Phone, Building, Search',
        'imagens': 'fachada de imóvel moderno e atraente, sala de estar ampla e iluminada, profissional entregando chaves sorrindo, vista aérea de bairro residencial',
        'pattern_break': 'seção de imóveis em destaque com cards grandes; diferenciais em fundo azul marinho',
        'cta': 'Falar com Corretor',
        'secoes_extra': 'Imóveis em destaque, Tipos de imóvel',
    },
    # FOTÓGRAFO
    'fotograf|foto|ensaio|studio foto': {
        'paleta': 'preto (#0A0A0A), branco (#FFFFFF), cinza (#71717A), dourado (#D4AF37) — minimalista para fotos',
        'estilo': 'portfólio visual, elegante — deixar as fotos falarem, mínimo de texto',
        'fontes': 'Plus Jakarta Sans Light para títulos, Inter para corpo',
        'icones': 'Camera, Image, Star, Heart, Award, Film',
        'imagens': 'câmera profissional em close, making of de ensaio fotográfico, galeria diversificada de fotos em parede, fotógrafo em ação',
        'pattern_break': 'galeria em grade masonry com hover effect zoom; seção de especialidades com fundo preto e fotos de alta qualidade',
        'cta': 'Solicitar Orçamento',
        'secoes_extra': 'Portfólio (casamento, newborn, corporativo, eventos)',
    },
    # DESIGNER / ARQUITETO
    'designer|design de interiores|arquiteto|arquitetura|decoracao': {
        'paleta': 'bege (#E8E0D5), cinza (#71717A), branco (#FFFFFF), preto (#1C1917), terracota (#C4A882)',
        'estilo': 'sofisticado, editorial, minimalista moderno — portfolio-driven',
        'fontes': 'Plus Jakarta Sans para títulos, Inter Light para corpo',
        'icones': 'Palette, Ruler, Home, Layers, Eye, Lightbulb, PenTool',
        'imagens': 'projeto residencial moderno com mobília clean, detalhe de materiais nobres como mármore e madeira, render 3D de ambiente com iluminação natural, mesa de trabalho com amostras de tecido e plantas',
        'pattern_break': 'portfólio em grid masonry com hover reveal de detalhes; seção de processo com timeline horizontal estilizada',
        'cta': 'Solicitar Projeto',
        'secoes_extra': 'Portfólio por categoria (residencial, comercial), Processo de trabalho (etapas)',
    },
    # EDUCAÇÃO
    'escola|curso|idioma|ingles': {
        'paleta': 'azul (#2563EB), amarelo (#FACC15), branco, verde (#10B981)',
        'estilo': 'moderno, dinâmico, acessível — inspira confiança e crescimento',
        'fontes': 'Outfit para títulos, Inter para corpo',
        'icones': 'BookOpen, GraduationCap, Users, Globe, Award, Lightbulb',
        'imagens': 'estudantes engajados em sala de aula moderna, professor interagindo com alunos, ambiente de aprendizado inspirador, livros e notebooks',
        'pattern_break': 'seção de metodologia com steps numerados; diferenciais com contadores animados',
        'cta': 'Agendar Aula Experimental',
        'secoes_extra': 'Cursos/Turmas, Metodologia',
    },
    # SERVIÇOS RESIDENCIAIS
    'eletricista|encanador|pintor|pedreiro|marceneiro|servicos gerais|manutencao': {
        'paleta': 'amarelo (#EAB308), laranja (#EA580C), azul (#2563EB), branco, cinza (#44403C)',
        'estilo': 'confiável, prático, acessível — transmite competência e disponibilidade',
        'fontes': 'Outfit Bold para títulos, Inter para corpo',
        'icones': 'Wrench, Zap, Droplets, PaintBucket, Hammer, Shield, Phone',
        'imagens': 'profissional com ferramentas em ação, trabalho sendo realizado com precisão, resultado final impecável, equipamento organizado',
        'pattern_break': 'seção de serviços em grade com ícones de ferramentas em fundo amarelo vibrante; destaques numéricos (500+ clientes atendidos)',
        'cta': 'Chamar no WhatsApp',
        'secoes_extra': 'Área de atendimento, Galeria de trabalhos realizados',
    },
    # DANÇA
    'danca|ballet|danza|dance': {
        'paleta': 'roxo (#7C3AED), dourado (#D4AF37), preto (#0A0A0A), branco, rosa (#EC4899)',
        'estilo': 'artístico, criativo, apaixonante — elegância em movimento',
        'fontes': 'Playfair Display para títulos, Inter para corpo',
        'icones': 'Music, Star, Heart, Users, Calendar, Award',
        'imagens': 'dançarina em posição elegante com iluminação dramática, sala de dança com espelhos e barra, grupo de alunos em apresentação, movimento capturado em long exposure',
        'pattern_break': 'galeria de apresentações em fundo escuro; seção de aulas com cards coloridos por modalidade',
        'cta': 'Matricular-se',
        'secoes_extra': 'Modalidades de dança, Galeria de apresentações',
    },
}

def _detectar_nicho(categoria, segmento='', nome=''):
    """Detecta o nicho baseado na categoria, segmento e nome da empresa."""
    alvo = f"{categoria} {segmento} {nome}".lower()
    melhor, melhor_score = None, 0
    for keys, info in _NICHOS_DB.items():
        kws = keys.split('|')
        score = sum(1 for k in kws if k in alvo)
        if score > melhor_score:
            melhor_score = score
            melhor = info
    return melhor

def _gerar_prompt_lovable_skill(empresa, reviews_list=None):
    """Gera prompt Lovable completo usando as boas práticas da skill lovable-site."""
    e = dict(empresa)
    nome       = e.get('nome') or 'Empresa'
    cat        = e.get('categoria') or e.get('segmento') or 'Servicos'
    descricao  = e.get('descricao') or ''
    cidade     = e.get('cidade') or ''
    estado     = e.get('estado') or ''
    endereco   = e.get('endereco') or ''
    bairro     = e.get('bairro') or ''
    telefone   = e.get('telefone_formatado') or e.get('telefone') or '[INSERIR TELEFONE]'
    rating     = float(e.get('rating') or 0)
    n_rev      = int(e.get('reviews') or 0)
    n_fotos    = int(e.get('qtd_fotos') or 0)

    tel_limpo  = re.sub(r'\D', '', telefone)
    wa_url     = f'https://wa.me/55{tel_limpo}' if tel_limpo and not tel_limpo.startswith('55') else f'https://wa.me/{tel_limpo}' if tel_limpo else '[INSERIR LINK WHATSAPP]'
    local      = ', '.join(filter(None, [bairro, cidade, estado]))

    # Horários
    horario_raw = e.get('horario') or '[]'
    try:
        horas = json.loads(horario_raw) if isinstance(horario_raw, str) else horario_raw
        horario_fmt = ' | '.join([f"{h.get('day','')}: {h.get('hours','')}" for h in horas if isinstance(h, dict) and h.get('hours')]) or '[INSERIR HORÁRIOS]'
    except:
        horario_fmt = '[INSERIR HORÁRIOS]'

    # Distribuição de estrelas
    d5 = int(e.get('dist_5estrelas') or 0)
    d4 = int(e.get('dist_4estrelas') or 0)
    d3 = int(e.get('dist_3estrelas') or 0)
    d2 = int(e.get('dist_2estrelas') or 0)
    d1 = int(e.get('dist_1estrela') or 0)

    # Detectar nicho e carregar design
    nicho = _detectar_nicho(cat, e.get('segmento',''), nome)
    if not nicho:
        nicho = {
            'paleta': 'azul moderno (#2563EB), branco (#FFFFFF), cinza claro (#F1F5F9), dourado (#D4AF37)',
            'estilo': 'profissional, moderno, confiável',
            'fontes': 'Plus Jakarta Sans para títulos, Inter para corpo',
            'icones': 'Star, MapPin, Phone, Clock, Shield, Award',
            'imagens': f'ambiente profissional representando {cat.lower()}, atendimento de qualidade, equipe trabalhando',
            'pattern_break': 'seção de diferenciais com fundo escuro; contadores animados',
            'cta': 'Falar pelo WhatsApp',
            'secoes_extra': '',
        }

    # Reviews formatadas
    reviews_section = ''
    if reviews_list:
        reviews_cards = []
        for i, r in enumerate(reviews_list[:8]):
            autor = r['autor'] or 'Cliente'
            nota = int(r.get('nota') or 5)
            texto = (r.get('texto') or '').strip()
            if not texto:
                continue
            stars = '★' * nota + '☆' * (5 - nota)
            tipo = 'Featured (col-span-2, bg cor primária, texto branco, quote decorativa 120px)' if i == 0 and len(texto) > 80 else 'Normal (bg branco, borda sutil)' if len(texto) > 40 else 'Tint (bg cor primária/5%)'
            reviews_cards.append(f'  - **{autor}** ({stars}): "{texto[:250]}"\n    Tipo de card: {tipo}')
        if reviews_cards:
            reviews_section = '\n'.join(reviews_cards)

    # ── GERAR PROMPT COMPLETO ──
    prompt = f"""## SITE: {nome} — {cat} em {local}

### 🎯 Objetivo do site
Criar um site profissional, moderno e visualmente impactante para **{nome}**, {cat} em {local}. O site deve transmitir credibilidade imediata, destacar os serviços oferecidos e converter visitantes em contatos pelo WhatsApp. Cada seção deve ter personalidade — NADA de template genérico.

### 🎨 Identidade visual
- **Paleta de cores**: {nicho['paleta']}
  - Background geral: off-white (#F8FAFC) — NUNCA branco puro
  - Alternar fundos entre seções para criar ritmo visual (claro → escuro → claro → cor de destaque)
- **Estilo visual**: {nicho['estilo']}
- **Tipografia**: {nicho.get('fontes', 'Plus Jakarta Sans para títulos (peso 700-800), Inter para corpo (peso 400, 17px, line-height 1.65)')}
  - Hero headline: 56px desktop / 36px mobile
  - Section title: 40px desktop / 28px mobile
  - NUNCA menor que 16px em mobile
- **Ícones**: Lucide Icons — {nicho['icones']}
- **Border-radius**: 16px em cards, 12px em botões, 24px na imagem hero, 9999px em badges/pills
- **Sombras**: `0 4px 6px -1px rgba(0,0,0,0.07)` padrão, `0 10px 25px -3px rgba(0,0,0,0.08)` hover
- **Container**: max-width 1200px, padding 24px mobile / 64px desktop
- **Espaço entre seções**: 96px desktop / 64px mobile (GENEROSO — sites premium respiram)

### 📐 Estrutura de páginas e seções

**SEÇÃO 1 — HERO (Split 55/45, alta conversão)**
- Badge no topo: "⭐ {cat} em {cidade}" (bg primária/10%, border-radius 9999px)
- Headline (56px, peso 800): Benefício principal do serviço — NÃO o nome da empresa
- Subheadline: "{descricao[:150] if descricao else f'{nome} — {cat} em {cidade}. Qualidade, experiência e atendimento personalizado.'}"
{f'- Prova social inline: "★★★★★ {n_rev} clientes satisfeitos" (badge com fundo dourado/10%)' if rating > 0 else ''}
- CTA primário: "{nicho['cta']}" → link: {wa_url}?text=Olá! Vim pelo site e gostaria de mais informações.
- CTA secundário: "Saiba Mais ↓" (ghost/outline, scroll suave para serviços)
- Imagem: {nicho['imagens'].split(',')[0]}, com border-radius 24px e sombra colorida sutil
- Layout: texto 55% à esquerda + imagem 45% à direita (mobile: imagem em cima)

**SEÇÃO 2 — NÚMEROS / CREDIBILIDADE (contadores animados)**
- Layout: 4 cards horizontais com números grandes animados (counter de 0 até valor)
- Sugestões: {f'"{rating:.1f}" (Nota Google)' if rating else '"100%"'} | {f'"{n_rev}+" (Avaliações)' if n_rev else '"Diversos"'} | "Anos de experiência" | "Garantia de qualidade"
- Cada número: 48px bold, label 14px muted abaixo
- Fundo: contraste com hero (se hero claro, usar fundo com cor primária escura e texto branco)

**SEÇÃO 3 — SERVIÇOS (Bento Grid assimétrico)**
Layout: bento grid responsivo — NÃO grid uniforme genérico.
- Desktop: grid de 12 colunas
  - Card A (serviço principal): col-span-7, row-span-2 — bg cor primária, texto branco, ícone 64px
  - Card B: col-span-5, row-span-1 — bg surface, border sutil
  - Card C: col-span-5, row-span-1 — bg cor de destaque/10%
  - Card D: col-span-12, row-span-1 — card horizontal com destaque central
- Mobile: empilhado em coluna única, Card A primeiro
- Todos: radius 16px, padding 28px, hover translate-y -4px, transition 300ms
- Cada card: ícone Lucide + título bold + descrição curta (1-2 linhas)
- Adaptar serviços reais ao tipo de negócio: {cat}
{f'- Seção extra: {nicho["secoes_extra"]}' if nicho.get('secoes_extra') else ''}

**SEÇÃO 4 — POR QUE NOS ESCOLHER (Diferenciais)**
- Layout alternado: texto à esquerda + imagem à direita (ou vice-versa)
- 3-4 diferenciais com ícone grande (48px), título bold, descrição
- Fundo: {nicho['pattern_break']}
- Imagem: {nicho['imagens'].split(',')[1] if ',' in nicho['imagens'] else nicho['imagens']}
- Números em destaque: tipografia 80px, semitransparente (opacity 5%) como decoração de fundo

**SEÇÃO 5 — COMO FUNCIONA (4 Steps com timeline)**
- Layout: timeline horizontal desktop / vertical mobile com linha SVG conectando os passos
- ① Contato → ② Avaliação → ③ Proposta → ④ Execução (adaptar ao negócio)
- Cada step: número grande em círculo com cor primária, título, breve descrição
- Animação: fade-in sequencial ao scroll (stagger 200ms)

**SEÇÃO 6 — SOBRE NÓS**
- Texto: apresentação de {nome}, história, missão e valores
- Imagem: {nicho['imagens'].split(',')[-1] if ',' in nicho['imagens'] else nicho['imagens']}
- Layout: texto à esquerda + imagem à direita com radius 24px
- Fundo: branco ou off-white para respirar"""

    # Seção de avaliações (a mais importante segundo a skill)
    if rating > 0:
        prompt += f"""

**SEÇÃO 7 — AVALIAÇÕES / PROVA SOCIAL** ⭐ SEÇÃO DE MAIOR IMPACTO NA CONVERSÃO

Esta é a seção que converte visitantes em clientes. Trate cada review como um ativo precioso.

BLOCO 1 — Header de credibilidade (centralizado):
- Logo Google SVG colorido + "Avaliações verificadas"
- Nota {rating:.1f} em 72px bold + ★★★★★ estrelas douradas 28px + "com base em {n_rev} avaliações" 14px muted
{f'''- Barra de distribuição de notas (mostra autenticidade):
  5★ {'█' * min(20, round(d5/max(n_rev,1)*20))}{'░' * (20 - min(20, round(d5/max(n_rev,1)*20)))} {round(d5/max(n_rev,1)*100)}%
  4★ {'█' * min(20, round(d4/max(n_rev,1)*20))}{'░' * (20 - min(20, round(d4/max(n_rev,1)*20)))} {round(d4/max(n_rev,1)*100)}%
  3★ {'█' * min(20, round(d3/max(n_rev,1)*20))}{'░' * (20 - min(20, round(d3/max(n_rev,1)*20)))} {round(d3/max(n_rev,1)*100)}%
  2★ {'█' * min(20, round(d2/max(n_rev,1)*20))}{'░' * (20 - min(20, round(d2/max(n_rev,1)*20)))} {round(d2/max(n_rev,1)*100)}%
  1★ {'█' * min(20, round(d1/max(n_rev,1)*20))}{'░' * (20 - min(20, round(d1/max(n_rev,1)*20)))} {round(d1/max(n_rev,1)*100)}%''' if n_rev >= 5 else ''}

BLOCO 2 — Wall of Reviews (masonry assimétrico):
{reviews_section if reviews_section else f'- Gerar 5-6 cards de avaliações representativas para {cat} em {cidade}'}
- Card Featured: col-span-2, bg cor primária, texto branco, quote decorativa 120px/8% opacity
- Cards normais: bg branco, borda 1px rgba(0,0,0,0.06), radius 16px, padding 24px
- Cards Tint: bg cor primária/5% para reviews curtas
- Hover: translate-y -3px + sombra suave, transition 250ms ease
- Entrada: fade-in scroll reveal com stagger 80ms entre cards
- Mobile: carrossel horizontal com scroll snap (1.2 cards visíveis)

Avatares com iniciais (NUNCA foto genérica):
- Círculos 44px com cores variadas: #D4AF37, #B45309, #78716C, #D97706, #92400E, #1C1917
- Iniciais: primeira letra nome + sobrenome, 15px bold

BLOCO 3 — Rodapé:
- Botão outline: "Ver todas as {n_rev} avaliações no Google ↗" (abre em nova aba)"""

    prompt += f"""

**SEÇÃO {'8' if rating > 0 else '7'} — CTA FINAL / CONTATO**
- Fundo: gradiente da cor primária → primária escura (diagonal)
- Título grande: chamada de ação forte e direta
- Botão principal: "{nicho['cta']}" → {wa_url}?text=Olá! Vim pelo site e gostaria de mais informações.
- Informações: {f'Endereço: {endereco}' if endereco else '[INSERIR ENDEREÇO]'}
- Telefone: {telefone}
- Horários: {horario_fmt}
- Card de localização clicável: "Ver no Google Maps" → link que abre Google Maps com endereço (NÃO usar iframe — Lovable quebra iframes)

**RODAPÉ**
- Logo/nome do negócio, links de navegação, redes sociais, "© {nome} — Todos os direitos reservados"

### 🖼️ Instruções para geração de imagens por IA
Para CADA imagem, descrever em detalhe para a IA do Lovable gerar com qualidade:
- **Hero**: {nicho['imagens']}
- **Sobre**: profissional em ação no ambiente de {cat.lower()}, expressão de dedicação e paixão pelo trabalho, iluminação natural
- **Galeria**: 4-6 imagens variadas mostrando diferentes aspectos do serviço

### 📱 Requisitos técnicos obrigatórios
- React + TypeScript + Tailwind CSS + shadcn/ui
- 100% responsivo (mobile-first): 375px, 768px, 1024px, 1440px
- Botão WhatsApp flutuante fixo: círculo verde (#25D366), ícone branco, 56x56px, sombra verde, hover scale 1.1
- SEO: meta title "{nome} | {cat} em {cidade}", meta description, og:image, schema LocalBusiness
- Lazy loading imagens, fontes otimizadas, target LCP < 2.5s
- Navbar fixa com backdrop-blur (bg white/80% + backdrop-blur-md)
- SEPARADORES entre seções: usar SVG wave ou clip-path polygon — NUNCA linha reta
- Cada seção adjacente DEVE variar em pelo menos 2 de: background / layout / alinhamento / decoração
- Animações: hover scale 1.03 em botões, hover translate-y -4px em cards, scroll reveal fade-in, contadores animados
- RESPEITAR prefers-reduced-motion

### 🔄 Prompts de ajuste para usar depois:
1. "Altere a paleta de cores: use [cor] como primária e [cor] como destaque"
2. "Atualize textos: título hero [novo], telefone [número], endereço [endereço]"
3. "Adicione seção de [nome] após [seção existente]"
4. "Atualize todos os botões WhatsApp para número [número]"
5. "Refine estilo: [descrição específica]"
"""
    return prompt


@app.route('/api/empresas/<int:emp_id>/gerar-prompt', methods=['POST'])
def gerar_prompt_lovable(emp_id):
    """Gera prompt Lovable completo usando a skill lovable-site."""
    conn = get_db()
    try:
        empresa = conn.execute("SELECT * FROM empresas WHERE id=?", (emp_id,)).fetchone()
        if not empresa:
            return jsonify({'erro': 'Empresa não encontrada'}), 404

        # Buscar reviews reais da empresa
        reviews = conn.execute(
            "SELECT autor, nota, texto FROM reviews WHERE empresa_id=? AND texto!='' ORDER BY nota DESC LIMIT 10",
            (emp_id,)
        ).fetchall()
        reviews_list = [dict(r) for r in reviews] if reviews else None

        prompt = _gerar_prompt_lovable_skill(empresa, reviews_list)

        return jsonify({
            'ok': True,
            'prompt': prompt,
            'nome': empresa['nome'],
            'template_nome': 'Skill Lovable (auto-detectado)',
        })
    except Exception as ex:
        return jsonify({'ok': False, 'erro': str(ex)})
    finally:
        conn.close()

@app.route('/api/kanban/contato/<int:contato_id>/prompt-lovable', methods=['POST'])
def kanban_prompt_lovable(contato_id):
    """Gera prompt Lovable para um contato do kanban, usando empresa_id associado."""
    conn = get_db()
    contato = conn.execute("SELECT empresa_id FROM kanban_contatos WHERE id=?", (contato_id,)).fetchone()
    if not contato or not contato['empresa_id']:
        conn.close()
        return jsonify({'erro': 'Contato ou empresa não encontrado'}), 404
    emp_id = contato['empresa_id']
    conn.close()
    # Chamar a rota existente diretamente
    return gerar_prompt_lovable(emp_id)

@app.route('/api/grupos')
def listar_grupos():
    conn = get_db()
    rows = conn.execute("SELECT DISTINCT grupo FROM empresas WHERE grupo IS NOT NULL AND grupo!='' ORDER BY grupo").fetchall()
    conn.close()
    return jsonify([r['grupo'] for r in rows])

@app.route('/api/exportar')
def exportar_csv():
    conn = get_db()
    rows = conn.execute("""
        SELECT nome, categoria, descricao, endereco, bairro, cidade, estado, cep,
               telefone, website, tem_website, rating, reviews,
               dist_1estrela, dist_2estrelas, dist_3estrelas, dist_4estrelas, dist_5estrelas,
               preco, qtd_fotos, fechado_permanente, reivindicado,
               plus_code, place_id, google_maps_url, menu_url,
               segmento, grupo, status_prospeccao, notas, criado_em
        FROM empresas ORDER BY id DESC
    """).fetchall()
    conn.close()
    output = io.StringIO()
    w = csv.writer(output)
    w.writerow(['Nome','Categoria','Descrição','Endereço','Bairro','Cidade','Estado','CEP',
                'Telefone','Website','Tem Site','Avaliação','Nº Reviews',
                '1★','2★','3★','4★','5★','Preço','Fotos','Fechado','Reivindicado',
                'Plus Code','Place ID','Google Maps','Menu URL',
                'Segmento','Grupo','Status Prospecção','Notas','Criado em'])
    for r in rows: w.writerow(list(r))
    return Response(output.getvalue(), mimetype='text/csv',
                    headers={"Content-Disposition":"attachment;filename=prospeccao.csv"})

# ═══════════════════════════════════════════════════════════════════════════════
# WHATSAPP — NÚMEROS
# ═══════════════════════════════════════════════════════════════════════════════

@app.route('/api/wa-numeros', methods=['GET'])
def wa_numeros_listar():
    conn = get_db()
    rows = conn.execute("SELECT * FROM wa_numeros ORDER BY id").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/wa-numeros', methods=['POST'])
def wa_numeros_criar():
    d = request.json or {}
    nome = (d.get('nome') or '').strip()
    if not nome:
        return jsonify({'erro': 'Nome obrigatório'}), 400
    # Gerar numero_id único (ex: numero_1, numero_2...)
    conn = get_db()
    count = conn.execute("SELECT COUNT(*) FROM wa_numeros").fetchone()[0]
    numero_id = f"numero_{count + 1}"
    # Garantir que não há colisão
    while conn.execute("SELECT id FROM wa_numeros WHERE numero_id = ?", (numero_id,)).fetchone():
        count += 1
        numero_id = f"numero_{count + 1}"
    conn.execute(
        "INSERT INTO wa_numeros (nome, numero_id) VALUES (?, ?)",
        (nome, numero_id)
    )
    conn.commit()
    row = conn.execute("SELECT * FROM wa_numeros WHERE numero_id = ?", (numero_id,)).fetchone()
    conn.close()
    return jsonify(dict(row))

@app.route('/api/wa-numeros/<int:id>', methods=['DELETE'])
def wa_numeros_deletar(id):
    conn = get_db()
    conn.execute("DELETE FROM wa_numeros WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})

@app.route('/api/wa-numeros/status', methods=['PUT'])
def wa_numeros_status():
    """Chamado pelo serviço Node.js para atualizar status de conexão"""
    d = request.json or {}
    numero_id = d.get('numero_id')
    status = d.get('status', 'disconnected')
    telefone = d.get('telefone', None)
    if not numero_id:
        return jsonify({'erro': 'numero_id obrigatorio'}), 400
    conn = get_db()
    if telefone is not None:
        conn.execute(
            "UPDATE wa_numeros SET status = ?, telefone = ? WHERE numero_id = ?",
            (status, telefone or None, numero_id)
        )
    else:
        conn.execute(
            "UPDATE wa_numeros SET status = ? WHERE numero_id = ?",
            (status, numero_id)
        )
    conn.commit()
    conn.close()
    return jsonify({'ok': True})


def _campanha_totais_para_status(conn, campanha_id):
    stats = conn.execute(
        """SELECT
               COUNT(*) AS total,
               SUM(CASE WHEN status='enviado' THEN 1 ELSE 0 END) AS enviados,
               SUM(CASE WHEN status='erro' THEN 1 ELSE 0 END) AS erros,
               SUM(CASE WHEN status='fila' THEN 1 ELSE 0 END) AS fila,
               SUM(CASE WHEN status='processando' THEN 1 ELSE 0 END) AS processando
           FROM campanha_itens
          WHERE campanha_id=?""",
        (campanha_id,)
    ).fetchone()
    stats = dict(stats or {})
    for chave in ('total', 'enviados', 'erros', 'fila', 'processando'):
        stats[chave] = int(stats.get(chave) or 0)
    return stats


def _recalcular_status_campanha(conn, campanha_id):
    numero_rows = conn.execute(
        "SELECT status FROM campanha_numeros WHERE campanha_id=?",
        (campanha_id,)
    ).fetchall()
    numero_status = [str(r['status'] or '') for r in numero_rows]
    totais = _campanha_totais_para_status(conn, campanha_id)

    if totais['total'] and totais['enviados'] + totais['erros'] >= totais['total'] and totais['fila'] == 0 and totais['processando'] == 0:
        novo_status = 'concluida'
    elif 'rodando' in numero_status:
        novo_status = 'rodando'
    elif 'pausado' in numero_status:
        novo_status = 'pausada'
    elif totais['enviados'] > 0:
        novo_status = 'parcial'
    else:
        novo_status = 'planejada'

    conn.execute(
        "UPDATE campanhas SET status=?, atualizado_em=CURRENT_TIMESTAMP WHERE id=?",
        (novo_status, campanha_id)
    )
    return novo_status


def _formatar_mensagem_campanha(conn, item_row, template_texto):
    nome_indicacao = get_nome_indicacao(item_row['empresa_id'], conn)
    return _formatar_template(
        template_texto,
        nome=item_row['nome'] or '',
        categoria=item_row['categoria'] or '',
        cidade=item_row['cidade'] or '',
        nome_indicacao=nome_indicacao or '',
        responsavel=item_row['nome_responsavel'] or '',
    )


def _campanha_worker(campanha_id, numero_wa_id):
    thread_key = (campanha_id, numero_wa_id)
    try:
        while True:
            conn = get_db()
            campanha = conn.execute("SELECT * FROM campanhas WHERE id=?", (campanha_id,)).fetchone()
            numero_cfg = conn.execute(
                "SELECT * FROM campanha_numeros WHERE campanha_id=? AND numero_wa_id=?",
                (campanha_id, numero_wa_id)
            ).fetchone()

            if not campanha or not numero_cfg:
                conn.close()
                break

            if numero_cfg['status'] != 'rodando':
                conn.close()
                break

            item = conn.execute(
                """SELECT ci.*, e.nome, e.categoria, e.cidade,
                          COALESCE(kc.nome_responsavel, e.nome_responsavel) AS nome_responsavel,
                          kc.telefone_wa
                     FROM campanha_itens ci
                     JOIN empresas e ON e.id = ci.empresa_id
                     JOIN kanban_contatos kc ON kc.id = ci.contato_id
                    WHERE ci.campanha_id=?
                      AND ci.numero_wa_id=?
                      AND ci.status IN ('fila', 'erro')
                    ORDER BY ci.ordem ASC
                    LIMIT 1""",
                (campanha_id, numero_wa_id)
            ).fetchone()

            if not item:
                conn.execute(
                    """UPDATE campanha_numeros
                          SET status='concluido', atualizado_em=CURRENT_TIMESTAMP
                        WHERE campanha_id=? AND numero_wa_id=?""",
                    (campanha_id, numero_wa_id)
                )
                _recalcular_status_campanha(conn, campanha_id)
                conn.commit()
                conn.close()
                break

            conn.execute(
                """UPDATE campanha_itens
                      SET status='processando'
                    WHERE id=?""",
                (item['id'],)
            )
            conn.execute(
                """UPDATE campanha_numeros
                      SET ultima_acao_em=CURRENT_TIMESTAMP, atualizado_em=CURRENT_TIMESTAMP
                    WHERE campanha_id=? AND numero_wa_id=?""",
                (campanha_id, numero_wa_id)
            )
            conn.commit()
            conn.close()

            try:
                conn_msg = get_db()
                try:
                    campanha_dict = dict(campanha)
                    item_dict = dict(item)
                    mensagem = _formatar_mensagem_campanha(conn_msg, item_dict, campanha_dict.get('template_texto') or '')
                    payload = {
                        'numeroId': numero_wa_id,
                        'telefone': item_dict['telefone_wa'],
                        'mensagem': mensagem,
                        'contatoId': item_dict['contato_id'],
                        'templateNome': campanha_dict.get('template_nome') or 'Campanha',
                        'contextoEnvio': 'campanha',
                        'tipoEnvio': 'buttons' if int(campanha_dict.get('usar_botoes') or 0) == 1 else 'text',
                    }
                    if int(campanha_dict.get('usar_botoes') or 0) == 1:
                        quick_cfg = _get_wa_quick_reply_config(conn_msg)
                        payload['footer'] = quick_cfg['footer']
                        payload['buttons'] = quick_cfg['buttons']
                    wa_url = _cfg(conn_msg, 'wa_service_url', 'http://localhost:3001')
                finally:
                    conn_msg.close()

                import urllib.request as _ur
                req_data = json.dumps(payload).encode()
                req_obj = _ur.Request(f'{wa_url}/api/enviar', data=req_data, headers={'Content-Type': 'application/json'}, method='POST')
                with _ur.urlopen(req_obj, timeout=45) as resp:
                    resp_json = json.loads(resp.read())
                if not resp_json.get('ok'):
                    raise RuntimeError(resp_json.get('error') or 'Falha ao enviar campanha')

                conn = get_db()
                conn.execute(
                    """UPDATE campanha_itens
                          SET status='enviado', tentativas=COALESCE(tentativas,0)+1,
                              erro_msg=NULL, enviado_em=CURRENT_TIMESTAMP
                        WHERE id=?""",
                    (item['id'],)
                )
                conn.execute(
                    """UPDATE campanha_numeros
                          SET enviados=COALESCE(enviados,0)+1, ultimo_erro=NULL,
                              ultima_acao_em=CURRENT_TIMESTAMP, atualizado_em=CURRENT_TIMESTAMP
                        WHERE campanha_id=? AND numero_wa_id=?""",
                    (campanha_id, numero_wa_id)
                )
                _recalcular_status_campanha(conn, campanha_id)
                conn.commit()
                conn.close()
            except Exception as ex:
                conn = get_db()
                conn.execute(
                    """UPDATE campanha_itens
                          SET status='erro', tentativas=COALESCE(tentativas,0)+1, erro_msg=?
                        WHERE id=?""",
                    (str(ex), item['id'])
                )
                conn.execute(
                    """UPDATE campanha_numeros
                          SET erros=COALESCE(erros,0)+1, ultimo_erro=?, status='pausado',
                              ultima_acao_em=CURRENT_TIMESTAMP, atualizado_em=CURRENT_TIMESTAMP
                        WHERE campanha_id=? AND numero_wa_id=?""",
                    (str(ex), campanha_id, numero_wa_id)
                )
                _recalcular_status_campanha(conn, campanha_id)
                conn.commit()
                conn.close()
                break

            espera_ms = max(int(campanha['intervalo_min_ms'] or 2200), 400)
            espera_max = max(int(campanha['intervalo_max_ms'] or espera_ms), espera_ms)
            time.sleep((espera_ms + (espera_max - espera_ms) * 0.5) / 1000.0)
    finally:
        with CAMPAIGN_THREAD_LOCK:
            CAMPAIGN_THREADS.pop(thread_key, None)


def _iniciar_worker_campanha(campanha_id, numero_wa_id):
    thread_key = (campanha_id, numero_wa_id)
    with CAMPAIGN_THREAD_LOCK:
        th = CAMPAIGN_THREADS.get(thread_key)
        if th and th.is_alive():
            return False
        th = threading.Thread(target=_campanha_worker, args=(campanha_id, numero_wa_id), daemon=True)
        CAMPAIGN_THREADS[thread_key] = th
        th.start()
        return True


def _campanha_payload(conn, campanha_row):
    if not campanha_row:
        return None
    campanha = dict(campanha_row)
    campanha_id = campanha['id']
    totais = _campanha_totais_para_status(conn, campanha_id)
    item_rows = conn.execute(
        """SELECT numero_wa_id,
                  COUNT(*) AS total,
                  SUM(CASE WHEN status='fila' THEN 1 ELSE 0 END) AS fila,
                  SUM(CASE WHEN status='processando' THEN 1 ELSE 0 END) AS processando,
                  SUM(CASE WHEN status='enviado' THEN 1 ELSE 0 END) AS enviados,
                  SUM(CASE WHEN status='erro' THEN 1 ELSE 0 END) AS erros
             FROM campanha_itens
            WHERE campanha_id=?
            GROUP BY numero_wa_id""",
        (campanha_id,)
    ).fetchall()
    item_stats = {r['numero_wa_id']: dict(r) for r in item_rows}
    numero_rows = conn.execute(
        """SELECT cn.*, wn.nome AS numero_nome, wn.telefone AS numero_telefone, wn.status AS numero_status
             FROM campanha_numeros cn
        LEFT JOIN wa_numeros wn ON wn.numero_id = cn.numero_wa_id
            WHERE cn.campanha_id=?
            ORDER BY cn.id""",
        (campanha_id,)
    ).fetchall()
    numeros = []
    for row in numero_rows:
        numero = dict(row)
        stats = item_stats.get(numero['numero_wa_id'], {})
        total = int(stats.get('total') or numero.get('total_previsto') or 0)
        enviados = int(stats.get('enviados') or numero.get('enviados') or 0)
        erros = int(stats.get('erros') or numero.get('erros') or 0)
        fila = int(stats.get('fila') or 0)
        processando = int(stats.get('processando') or 0)
        numero.update({
            'total_previsto': int(numero.get('total_previsto') or total),
            'enviados': int(numero.get('enviados') or 0),
            'erros': int(numero.get('erros') or 0),
            'fila': fila,
            'processando': processando,
            'pendentes': max(total - enviados - erros, 0),
            'progresso_pct': round(((enviados + erros) / total) * 100, 1) if total else 100.0,
        })
        numeros.append(numero)
    campanha.update({
        'totais': totais,
        'progresso_pct': round(((totais['enviados'] + totais['erros']) / totais['total']) * 100, 1) if totais['total'] else 0.0,
        'numeros': numeros,
    })
    return campanha


def _campanha_por_id(conn, campanha_id):
    row = conn.execute("SELECT * FROM campanhas WHERE id=?", (campanha_id,)).fetchone()
    return _campanha_payload(conn, row) if row else None


@app.route('/api/campanhas', methods=['GET'])
def campanhas_listar():
    conn = get_db()
    q = (request.args.get('q') or '').strip()
    status = (request.args.get('status') or '').strip().lower()
    data_inicio = (request.args.get('data_inicio') or '').strip()
    data_fim = (request.args.get('data_fim') or '').strip()
    wheres = []
    params = []
    if q:
        wheres.append("nome LIKE ?")
        params.append(f"%{q}%")
    if status:
        wheres.append("LOWER(status)=?")
        params.append(status)
    if data_inicio:
        wheres.append("date(criado_em) >= date(?)")
        params.append(data_inicio)
    if data_fim:
        wheres.append("date(criado_em) <= date(?)")
        params.append(data_fim)
    sql = "SELECT * FROM campanhas"
    if wheres:
        sql += " WHERE " + " AND ".join(wheres)
    sql += " ORDER BY id DESC LIMIT 80"
    rows = conn.execute(sql, tuple(params)).fetchall()
    data = [_campanha_payload(conn, row) for row in rows]
    conn.close()
    return jsonify(data)


@app.route('/api/campanhas', methods=['POST'])
def campanhas_criar():
    d = request.json or {}
    empresa_ids = [int(i) for i in (d.get('empresa_ids') or []) if str(i).isdigit()]
    numero_ids = [str(i).strip() for i in (d.get('numero_ids') or []) if str(i).strip()]
    estrategia = str(d.get('estrategia') or 'round_robin').strip() or 'round_robin'
    nome = str(d.get('nome') or '').strip()

    if not empresa_ids:
        return jsonify({'ok': False, 'erro': 'Selecione pelo menos uma empresa'}), 400
    if not numero_ids:
        return jsonify({'ok': False, 'erro': 'Selecione pelo menos um numero de WhatsApp'}), 400

    if not nome:
        nome = f"Campanha {datetime.now().strftime('%d/%m %H:%M')}"

    conn = get_db()
    numeros = conn.execute(
        f"SELECT numero_id, nome, status FROM wa_numeros WHERE numero_id IN ({','.join(['?'] * len(numero_ids))})",
        tuple(numero_ids)
    ).fetchall()
    mapa_numeros = {r['numero_id']: dict(r) for r in numeros}
    numero_ids_validos = [n for n in numero_ids if n in mapa_numeros]
    if not numero_ids_validos:
        conn.close()
        return jsonify({'ok': False, 'erro': 'Nenhum numero valido encontrado'}), 400

    cur = conn.execute(
        """INSERT INTO campanhas (nome, estrategia, total_empresas, total_numeros, status, atualizado_em)
           VALUES (?, ?, ?, ?, 'planejada', CURRENT_TIMESTAMP)""",
        (nome, estrategia, len(empresa_ids), len(numero_ids_validos))
    )
    campanha_id = cur.lastrowid

    adicionados = []
    atualizados = []
    ja_existiam = []
    bloqueados = []
    sem_telefone = []
    erros = []
    distribuicao = {numero_id: 0 for numero_id in numero_ids_validos}

    for idx, empresa_id in enumerate(empresa_ids):
        numero_destino = numero_ids_validos[idx % len(numero_ids_validos)]
        try:
            emp = conn.execute(
                "SELECT id, nome, telefone, telefone_formatado FROM empresas WHERE id = ?",
                (empresa_id,)
            ).fetchone()
            if not emp:
                erros.append(empresa_id)
                continue
            if _empresa_em_lista_negra(conn, empresa_id):
                bloqueados.append({'id': empresa_id, 'nome': emp['nome']})
                continue

            tel_raw = emp['telefone_formatado'] or emp['telefone'] or ''
            tel_limpo = re.sub(r'\D', '', tel_raw)
            if not tel_limpo:
                sem_telefone.append({'id': empresa_id, 'nome': emp['nome']})
                continue

            contato = conn.execute(
                "SELECT id, kanban_coluna FROM kanban_contatos WHERE empresa_id = ?",
                (empresa_id,)
            ).fetchone()

            if contato and contato['kanban_coluna'] not in ('Fila',):
                ja_existiam.append({'id': empresa_id, 'nome': emp['nome'], 'coluna': contato['kanban_coluna']})
                continue

            if contato:
                conn.execute(
                    """UPDATE kanban_contatos
                          SET telefone_wa=?,
                              numero_wa_id=?,
                              campanha_id=?,
                              atualizado_em=CURRENT_TIMESTAMP
                        WHERE id=?""",
                    (tel_limpo, numero_destino, campanha_id, contato['id'])
                )
                contato_id = contato['id']
                atualizados.append({'id': empresa_id, 'nome': emp['nome'], 'numero_id': numero_destino})
            else:
                cur_contato = conn.execute(
                    """INSERT INTO kanban_contatos (empresa_id, telefone_wa, kanban_coluna, numero_wa_id, campanha_id)
                       VALUES (?, ?, 'Fila', ?, ?)""",
                    (empresa_id, tel_limpo, numero_destino, campanha_id)
                )
                contato_id = cur_contato.lastrowid
                adicionados.append({'id': empresa_id, 'nome': emp['nome'], 'numero_id': numero_destino})

            cur_item = conn.execute(
                """INSERT INTO campanha_itens (campanha_id, empresa_id, contato_id, numero_wa_id, ordem, status)
                   VALUES (?, ?, ?, ?, ?, 'fila')""",
                (campanha_id, empresa_id, contato_id, numero_destino, idx + 1)
            )
            campanha_item_id = cur_item.lastrowid
            conn.execute(
                "UPDATE kanban_contatos SET campanha_item_id=? WHERE id=?",
                (campanha_item_id, contato_id)
            )
            distribuicao[numero_destino] += 1
        except Exception:
            erros.append(empresa_id)

    total_validos = len(adicionados) + len(atualizados)
    status_final = 'planejada' if total_validos else 'vazia'
    for numero_id in numero_ids_validos:
        conn.execute(
            """INSERT OR REPLACE INTO campanha_numeros
                  (campanha_id, numero_wa_id, total_previsto, enviados, erros, status, atualizado_em)
               VALUES (?, ?, ?, 0, 0, ?, CURRENT_TIMESTAMP)""",
            (
                campanha_id,
                numero_id,
                int(distribuicao.get(numero_id, 0) or 0),
                'fila' if int(distribuicao.get(numero_id, 0) or 0) > 0 else 'concluido',
            )
        )
    conn.execute(
        """UPDATE campanhas
              SET total_empresas=?,
                  total_numeros=?,
                  status=?,
                  atualizado_em=CURRENT_TIMESTAMP
            WHERE id=?""",
        (total_validos, len(numero_ids_validos), status_final, campanha_id)
    )
    conn.commit()
    conn.close()

    distribuicao_detalhada = []
    for numero_id in numero_ids_validos:
        meta = mapa_numeros.get(numero_id) or {}
        distribuicao_detalhada.append({
            'numero_id': numero_id,
            'nome': meta.get('nome') or numero_id,
            'status': meta.get('status') or 'desconhecido',
            'total': distribuicao.get(numero_id, 0),
        })

    return jsonify({
        'ok': True,
        'campanha_id': campanha_id,
        'nome': nome,
        'estrategia': estrategia,
        'adicionados': len(adicionados),
        'atualizados': len(atualizados),
        'ja_existiam': len(ja_existiam),
        'bloqueados': len(bloqueados),
        'sem_telefone': len(sem_telefone),
        'erros': len(erros),
        'distribuicao': distribuicao_detalhada,
        'detalhes': {
            'adicionados': adicionados,
            'atualizados': atualizados,
            'ja_existiam': ja_existiam,
            'bloqueados': bloqueados,
            'sem_telefone': sem_telefone,
        }
    })


@app.route('/api/campanhas/<int:campanha_id>', methods=['GET'])
def campanhas_detalhe(campanha_id):
    conn = get_db()
    payload = _campanha_por_id(conn, campanha_id)
    conn.close()
    if not payload:
        return jsonify({'ok': False, 'erro': 'Campanha nao encontrada'}), 404
    return jsonify(payload)


@app.route('/api/campanhas/<int:campanha_id>/disparar', methods=['POST'])
def campanhas_disparar(campanha_id):
    d = request.json or {}
    template_id = d.get('template_id')
    try:
        template_id = int(template_id)
    except Exception:
        template_id = 0
    intervalo_min_ms = max(int(d.get('intervalo_min_ms') or 2200), 400)
    intervalo_max_ms = max(int(d.get('intervalo_max_ms') or intervalo_min_ms), intervalo_min_ms)
    usar_botoes = 1 if str(d.get('usar_botoes', 1)).lower() not in ('0', 'false', 'off', '') else 0

    conn = get_db()
    campanha = conn.execute("SELECT * FROM campanhas WHERE id=?", (campanha_id,)).fetchone()
    if not campanha:
        conn.close()
        return jsonify({'ok': False, 'erro': 'Campanha nao encontrada'}), 404

    template = None
    if template_id:
        template = conn.execute(
            "SELECT id, nome, texto, ativo FROM wa_msg_templates WHERE id=?",
            (template_id,)
        ).fetchone()
        if not template:
            conn.close()
            return jsonify({'ok': False, 'erro': 'Template nao encontrado'}), 404
    elif campanha['template_texto']:
        template = {
            'id': campanha['template_id'],
            'nome': campanha['template_nome'] or 'Campanha',
            'texto': campanha['template_texto'],
            'ativo': 1,
        }
    else:
        conn.close()
        return jsonify({'ok': False, 'erro': 'Selecione um template para disparar a campanha'}), 400

    numero_rows = conn.execute(
        "SELECT numero_wa_id, total_previsto, status FROM campanha_numeros WHERE campanha_id=? ORDER BY id",
        (campanha_id,)
    ).fetchall()
    if not numero_rows:
        conn.close()
        return jsonify({'ok': False, 'erro': 'Campanha sem numeros vinculados'}), 400

    numeros_rodando = []
    for row in numero_rows:
        pendentes = conn.execute(
            """SELECT COUNT(*)
                 FROM campanha_itens
                WHERE campanha_id=? AND numero_wa_id=? AND status IN ('fila', 'erro', 'processando')""",
            (campanha_id, row['numero_wa_id'])
        ).fetchone()[0]
        novo_status = 'rodando' if pendentes > 0 else 'concluido'
        conn.execute(
            """UPDATE campanha_numeros
                  SET status=?, ultimo_erro=NULL, atualizado_em=CURRENT_TIMESTAMP
                WHERE campanha_id=? AND numero_wa_id=?""",
            (novo_status, campanha_id, row['numero_wa_id'])
        )
        if pendentes > 0:
            conn.execute(
                """UPDATE campanha_itens
                      SET status='fila'
                    WHERE campanha_id=? AND numero_wa_id=? AND status='processando'""",
                (campanha_id, row['numero_wa_id'])
            )
            numeros_rodando.append(row['numero_wa_id'])

    conn.execute(
        """UPDATE campanhas
              SET template_id=?, template_nome=?, template_texto=?,
                  intervalo_min_ms=?, intervalo_max_ms=?, usar_botoes=?,
                  status='rodando', atualizado_em=CURRENT_TIMESTAMP
            WHERE id=?""",
        (
            int(template['id'] or 0) if isinstance(template, sqlite3.Row) else int(template.get('id') or 0),
            template['nome'] if isinstance(template, sqlite3.Row) else template.get('nome'),
            template['texto'] if isinstance(template, sqlite3.Row) else template.get('texto'),
            intervalo_min_ms,
            intervalo_max_ms,
            usar_botoes,
            campanha_id,
        )
    )
    _recalcular_status_campanha(conn, campanha_id)
    payload = _campanha_por_id(conn, campanha_id)
    conn.commit()
    conn.close()

    for numero_id in numeros_rodando:
        _iniciar_worker_campanha(campanha_id, numero_id)

    return jsonify({
        'ok': True,
        'campanha': payload,
        'numeros_rodando': numeros_rodando,
    })


@app.route('/api/campanhas/<int:campanha_id>/status', methods=['POST'])
def campanhas_alterar_status(campanha_id):
    d = request.json or {}
    novo_status = str(d.get('status') or '').strip().lower()
    if novo_status not in ('rodando', 'pausada'):
        return jsonify({'ok': False, 'erro': 'Status invalido'}), 400

    conn = get_db()
    campanha = conn.execute("SELECT * FROM campanhas WHERE id=?", (campanha_id,)).fetchone()
    if not campanha:
        conn.close()
        return jsonify({'ok': False, 'erro': 'Campanha nao encontrada'}), 404
    if novo_status == 'rodando' and not campanha['template_texto']:
        conn.close()
        return jsonify({'ok': False, 'erro': 'Essa campanha ainda nao tem template configurado. Use Disparar campanha primeiro.'}), 400

    numero_rows = conn.execute(
        "SELECT numero_wa_id FROM campanha_numeros WHERE campanha_id=? ORDER BY id",
        (campanha_id,)
    ).fetchall()
    numeros_rodando = []
    for row in numero_rows:
        numero_wa_id = row['numero_wa_id']
        pendentes = conn.execute(
            """SELECT COUNT(*)
                 FROM campanha_itens
                WHERE campanha_id=? AND numero_wa_id=? AND status IN ('fila', 'erro', 'processando')""",
            (campanha_id, numero_wa_id)
        ).fetchone()[0]
        if novo_status == 'pausada':
            if pendentes > 0:
                conn.execute(
                    """UPDATE campanha_numeros
                          SET status='pausado', atualizado_em=CURRENT_TIMESTAMP
                        WHERE campanha_id=? AND numero_wa_id=?""",
                    (campanha_id, numero_wa_id)
                )
        else:
            if pendentes > 0:
                conn.execute(
                    """UPDATE campanha_itens
                          SET status='fila'
                        WHERE campanha_id=? AND numero_wa_id=? AND status='processando'""",
                    (campanha_id, numero_wa_id)
                )
                conn.execute(
                    """UPDATE campanha_numeros
                          SET status='rodando', ultimo_erro=NULL, atualizado_em=CURRENT_TIMESTAMP
                        WHERE campanha_id=? AND numero_wa_id=?""",
                    (campanha_id, numero_wa_id)
                )
                numeros_rodando.append(numero_wa_id)
            else:
                conn.execute(
                    """UPDATE campanha_numeros
                          SET status='concluido', atualizado_em=CURRENT_TIMESTAMP
                        WHERE campanha_id=? AND numero_wa_id=?""",
                    (campanha_id, numero_wa_id)
                )

    if novo_status == 'pausada':
        conn.execute(
            "UPDATE campanhas SET status='pausada', atualizado_em=CURRENT_TIMESTAMP WHERE id=?",
            (campanha_id,)
        )
    _recalcular_status_campanha(conn, campanha_id)
    payload = _campanha_por_id(conn, campanha_id)
    conn.commit()
    conn.close()

    if novo_status == 'rodando':
        for numero_wa_id in numeros_rodando:
            _iniciar_worker_campanha(campanha_id, numero_wa_id)

    return jsonify({'ok': True, 'campanha': payload, 'numeros_rodando': numeros_rodando})


@app.route('/api/campanhas/<int:campanha_id>/numeros/<numero_wa_id>/status', methods=['POST'])
def campanhas_alterar_status_numero(campanha_id, numero_wa_id):
    d = request.json or {}
    novo_status = str(d.get('status') or '').strip().lower()
    if novo_status not in ('rodando', 'pausado'):
        return jsonify({'ok': False, 'erro': 'Status invalido'}), 400

    conn = get_db()
    row = conn.execute(
        "SELECT * FROM campanha_numeros WHERE campanha_id=? AND numero_wa_id=?",
        (campanha_id, numero_wa_id)
    ).fetchone()
    if not row:
        conn.close()
        return jsonify({'ok': False, 'erro': 'Numero da campanha nao encontrado'}), 404

    if novo_status == 'rodando':
        pendentes = conn.execute(
            """SELECT COUNT(*)
                 FROM campanha_itens
                WHERE campanha_id=? AND numero_wa_id=? AND status IN ('fila', 'erro', 'processando')""",
            (campanha_id, numero_wa_id)
        ).fetchone()[0]
        if pendentes <= 0:
            conn.execute(
                """UPDATE campanha_numeros
                      SET status='concluido', atualizado_em=CURRENT_TIMESTAMP
                    WHERE campanha_id=? AND numero_wa_id=?""",
                (campanha_id, numero_wa_id)
            )
        else:
            conn.execute(
                """UPDATE campanha_itens
                      SET status='fila'
                    WHERE campanha_id=? AND numero_wa_id=? AND status='processando'""",
                (campanha_id, numero_wa_id)
            )
            conn.execute(
                """UPDATE campanha_numeros
                      SET status='rodando', ultimo_erro=NULL, atualizado_em=CURRENT_TIMESTAMP
                    WHERE campanha_id=? AND numero_wa_id=?""",
                (campanha_id, numero_wa_id)
            )
    else:
        conn.execute(
            """UPDATE campanha_numeros
                  SET status='pausado', atualizado_em=CURRENT_TIMESTAMP
                WHERE campanha_id=? AND numero_wa_id=?""",
            (campanha_id, numero_wa_id)
        )

    _recalcular_status_campanha(conn, campanha_id)
    payload = _campanha_por_id(conn, campanha_id)
    conn.commit()
    conn.close()

    if novo_status == 'rodando':
        _iniciar_worker_campanha(campanha_id, numero_wa_id)

    return jsonify({'ok': True, 'campanha': payload})

# ═══════════════════════════════════════════════════════════════════════════════
# WHATSAPP — TEMPLATES DE MENSAGEM
# ═══════════════════════════════════════════════════════════════════════════════

@app.route('/api/wa-msg-templates', methods=['GET'])
def wa_tpl_listar():
    conn = get_db()
    rows = conn.execute("SELECT * FROM wa_msg_templates ORDER BY categoria, id").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/wa-msg-templates', methods=['POST'])
def wa_tpl_criar():
    d = request.json or {}
    if not d.get('nome') or not d.get('texto'):
        return jsonify({'erro': 'nome e texto obrigatórios'}), 400
    conn = get_db()
    conn.execute(
        "INSERT INTO wa_msg_templates (nome, categoria, texto) VALUES (?, ?, ?)",
        (d['nome'], d.get('categoria', 'abertura'), d['texto'])
    )
    conn.commit()
    row = conn.execute("SELECT * FROM wa_msg_templates WHERE id = last_insert_rowid()").fetchone()
    conn.close()
    return jsonify(dict(row))

@app.route('/api/wa-msg-templates/<int:id>', methods=['PUT'])
def wa_tpl_atualizar(id):
    d = request.json or {}
    conn = get_db()
    conn.execute(
        "UPDATE wa_msg_templates SET nome=?, categoria=?, texto=?, ativo=? WHERE id=?",
        (d.get('nome'), d.get('categoria', 'abertura'), d.get('texto'), d.get('ativo', 1), id)
    )
    conn.commit()
    row = conn.execute("SELECT * FROM wa_msg_templates WHERE id = ?", (id,)).fetchone()
    conn.close()
    return jsonify(dict(row) if row else {'erro': 'Não encontrado'})

@app.route('/api/wa-msg-templates/<int:id>', methods=['DELETE'])
def wa_tpl_deletar(id):
    conn = get_db()
    conn.execute("DELETE FROM wa_msg_templates WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})

def get_nome_indicacao(empresa_id, conn):
    """
    Retorna primeiro+sobrenome do cliente mais recente com melhor avaliação.
    Prefere 5★ > 4★ > 3★. Filtra handles/apelidos sem nome real.
    Retorna None se não encontrar review adequado.
    """
    import unicodedata as _ud

    def nome_valido(texto):
        """Verifica se parece um nome real (letras, mínimo 3 chars por parte)."""
        partes = texto.strip().split()
        validas = []
        for p in partes:
            # Remover acentos para checar se é só letras
            normalizado = _ud.normalize('NFKD', p).encode('ascii', 'ignore').decode()
            if normalizado.isalpha() and len(p) >= 3:
                validas.append(p.capitalize())
        return validas

    for nota_min in [5, 4, 3]:
        rows = conn.execute(
            """SELECT autor FROM reviews
               WHERE empresa_id=? AND nota>=? AND autor IS NOT NULL AND autor!=''
               ORDER BY nota DESC, data_review DESC
               LIMIT 10""",
            (empresa_id, nota_min)
        ).fetchall()
        for row in rows:
            partes = nome_valido(row['autor'])
            if len(partes) >= 2:
                return f"{partes[0]} {partes[1]}"  # Primeiro + Sobrenome
            elif len(partes) == 1:
                return partes[0]  # Só primeiro nome
    return None

# ═══════════════════════════════════════════════════════════════════════════════
# KANBAN — CONTATOS
# ═══════════════════════════════════════════════════════════════════════════════

KANBAN_COLUNAS = ['Fila', 'Enviado', 'Respondeu', 'Negociando', 'Fechado', 'Descartado']
KANBAN_BRIEFING_FIELDS = (
    'logo',
    'fotos',
    'cores_marca',
    'contatos',
    'principais_servicos',
    'observacoes',
)


def _briefing_lead_vazio():
    return {campo: '' for campo in KANBAN_BRIEFING_FIELDS}


def _parse_briefing_lead(raw_briefing, notas_legado=''):
    briefing = _briefing_lead_vazio()
    bruto = raw_briefing

    if isinstance(bruto, str):
        bruto = bruto.strip()
        if bruto:
            try:
                bruto = json.loads(bruto)
            except Exception:
                bruto = {'observacoes': bruto}
        else:
            bruto = {}

    if isinstance(bruto, dict):
        for campo in KANBAN_BRIEFING_FIELDS:
            valor = bruto.get(campo, '')
            briefing[campo] = str(valor or '').strip()

    notas_legado = str(notas_legado or '').strip()
    if notas_legado and not briefing['observacoes']:
        briefing['observacoes'] = notas_legado

    return briefing


def _briefing_lead_tem_conteudo(briefing):
    return any(str((briefing or {}).get(campo, '') or '').strip() for campo in KANBAN_BRIEFING_FIELDS)


def _resumir_texto_briefing(valor, limite=90):
    texto = ' '.join(str(valor or '').split())
    if len(texto) <= limite:
        return texto
    return texto[: limite - 3].rstrip() + '...'


def _resumo_briefing_lead(briefing):
    briefing = _parse_briefing_lead(briefing)
    if not _briefing_lead_tem_conteudo(briefing):
        return ''

    partes = []
    if briefing['logo']:
        partes.append(f"Logo: {_resumir_texto_briefing(briefing['logo'], 60)}")
    if briefing['fotos']:
        qtd_fotos = len([item for item in re.split(r'[\n,;]+', briefing['fotos']) if item.strip()])
        if qtd_fotos > 0:
            partes.append(f"Fotos: {qtd_fotos} item(ns)")
    if briefing['cores_marca']:
        partes.append(f"Cores: {_resumir_texto_briefing(briefing['cores_marca'], 60)}")
    if briefing['contatos']:
        partes.append(f"Contatos: {_resumir_texto_briefing(briefing['contatos'], 70)}")
    if briefing['principais_servicos']:
        partes.append(f"Servicos: {_resumir_texto_briefing(briefing['principais_servicos'], 70)}")
    if briefing['observacoes']:
        partes.append(f"Obs: {_resumir_texto_briefing(briefing['observacoes'], 90)}")

    return '\n'.join(partes[:6])


def _kanban_filter_clause():
    campanha_id = (request.args.get('campanha_id') or '').strip()
    if campanha_id.isdigit():
        return " WHERE kc.campanha_id = ? ", [int(campanha_id)]
    return "", []

def extrair_nome_responsavel(dados_extras_str):
    """
    Opção 1 — Tenta extrair o nome do responsável a partir dos dados do Google Maps.
    Busca em: respostas do dono nos reviews, descrição, e padrões de assinatura.
    Retorna o nome encontrado ou None.
    """
    try:
        import re as _re
        d = json.loads(dados_extras_str or '{}')

        # 1) Verificar nas respostas do dono aos reviews
        reviews = d.get('reviews', [])
        for rv in reviews:
            resp = (rv.get('responseFromOwnerText') or '').strip()
            if not resp:
                continue
            # Padrões comuns: "Att, João Silva", "Abraços, Maria", "Sou o Carlos", "Aqui é a Ana"
            padroes = [
                r'[Aa]tt[,.]?\s+([A-ZÁÉÍÓÚÀÂÊÔÃÕÜÇ][a-záéíóúàâêôãõüç]+(?:\s+[A-ZÁÉÍÓÚÀÂÊÔÃÕÜÇ][a-záéíóúàâêôãõüç]+)?)',
                r'[Aa]bra[çc]os[,.]?\s+([A-ZÁÉÍÓÚÀÂÊÔÃÕÜÇ][a-záéíóúàâêôãõüç]+(?:\s+[A-ZÁÉÍÓÚÀÂÊÔÃÕÜÇ][a-záéíóúàâêôãõüç]+)?)',
                r'[Gg]rato[,.]?\s+([A-ZÁÉÍÓÚÀÂÊÔÃÕÜÇ][a-záéíóúàâêôãõüç]+(?:\s+[A-ZÁÉÍÓÚÀÂÊÔÃÕÜÇ][a-záéíóúàâêôãõüç]+)?)',
                r'[Ss]ou\s+[oa]?\s*([A-ZÁÉÍÓÚÀÂÊÔÃÕÜÇ][a-záéíóúàâêôãõüç]+(?:\s+[A-ZÁÉÍÓÚÀÂÊÔÃÕÜÇ][a-záéíóúàâêôãõüç]+)?)',
                r'[Aa]qui\s+[eé]\s+[oa]?\s*([A-ZÁÉÍÓÚÀÂÊÔÃÕÜÇ][a-záéíóúàâêôãõüç]+(?:\s+[A-ZÁÉÍÓÚÀÂÊÔÃÕÜÇ][a-záéíóúàâêôãõüç]+)?)',
                r'[Mm]eu\s+nome\s+[eé]\s+([A-ZÁÉÍÓÚÀÂÊÔÃÕÜÇ][a-záéíóúàâêôãõüç]+(?:\s+[A-ZÁÉÍÓÚÀÂÊÔÃÕÜÇ][a-záéíóúàâêôãõüç]+)?)',
                r'[-–]\s*([A-ZÁÉÍÓÚÀÂÊÔÃÕÜÇ][a-záéíóúàâêôãõüç]+(?:\s+[A-ZÁÉÍÓÚÀÂÊÔÃÕÜÇ][a-záéíóúàâêôãõüç]+)?)\s*$',
            ]
            for pat in padroes:
                m = _re.search(pat, resp)
                if m:
                    nome = m.group(1).strip()
                    # Filtrar palavras genéricas
                    ignorar = {'Equipe', 'Time', 'Empresa', 'Loja', 'Atenciosamente', 'Gerência', 'Gerencia'}
                    if nome not in ignorar and len(nome) >= 3:
                        return nome

        # 2) Verificar em questionsAndAnswers
        qas = d.get('questionsAndAnswers', [])
        for qa in qas:
            ans = qa.get('answer', {})
            autor = ans.get('authorName', '') or ans.get('author', '')
            texto_resp = (ans.get('text') or '').strip()
            if autor and autor not in ('Proprietário', 'Owner', 'Dono'):
                return autor
            if texto_resp:
                for pat in [r'[-–]\s*([A-ZÁÉÍÓÚÀÂÊÔÃÕÜÇ][a-záéíóúàâêôãõüç]+)']:
                    m = _re.search(pat, texto_resp)
                    if m:
                        return m.group(1).strip()

        return None
    except Exception as e:
        print(f'[extrair_nome_responsavel] Erro: {e}')
        return None

@app.route('/api/kanban', methods=['GET'])
def kanban_listar():
    conn = get_db()
    where_sql, params = _kanban_filter_clause()
    rows = conn.execute(f"""
        SELECT
            kc.*,
            e.nome, e.categoria, e.cidade, e.rating, e.reviews,
            e.telefone, e.telefone_formatado, e.website, e.google_maps_url,
            e.endereco, e.estado, e.segmento,
            COALESCE(kc.nome_responsavel, e.nome_responsavel) AS nome_responsavel
        FROM kanban_contatos kc
        JOIN empresas e ON e.id = kc.empresa_id
        {where_sql}
        ORDER BY kc.kanban_coluna, kc.atualizado_em DESC
    """, tuple(params)).fetchall()
    conn.close()

    # Agrupar por coluna e injetar nome_indicacao
    conn2 = get_db()
    resultado = {col: [] for col in KANBAN_COLUNAS}
    for r in rows:
        d = dict(r)
        col = d.get('kanban_coluna', 'Fila')
        if col not in resultado:
            resultado[col] = []
        # Adicionar nome de indicação via review
        d['nome_indicacao'] = get_nome_indicacao(d.get('empresa_id'), conn2)
        resultado[col].append(d)
    conn2.close()

    return jsonify(resultado)

@app.route('/api/kanban/lista', methods=['GET'])
def kanban_lista_flat():
    """Retorna lista plana de todos os contatos (para tabelas)"""
    conn = get_db()
    where_sql, params = _kanban_filter_clause()
    rows = conn.execute(f"""
        SELECT
            kc.*,
            e.nome, e.categoria, e.cidade, e.rating,
            e.telefone, e.telefone_formatado, e.website, e.segmento
        FROM kanban_contatos kc
        JOIN empresas e ON e.id = kc.empresa_id
        {where_sql}
        ORDER BY kc.atualizado_em DESC
    """, tuple(params)).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/empresas-manual', methods=['POST'])
def empresa_manual_criar():
    """Cria uma empresa manualmente (para testes ou leads offline)"""
    d = request.json or {}
    nome = (d.get('nome') or '').strip()
    if not nome:
        return jsonify({'erro': 'Nome obrigatório'}), 400

    if _empresa_em_lista_negra(conn, empresa_id):
        conn.close()
        return jsonify({'erro': 'Empresa na lista negra e bloqueada para novo envio'}), 409

    import re as _re
    tel_raw = d.get('telefone', '')
    tel_limpo = _re.sub(r'\D', '', tel_raw)

    conn = get_db()
    conn.execute("""
        INSERT INTO empresas
            (nome, categoria, cidade, estado, telefone, telefone_formatado,
             endereco, descricao, segmento, grupo, tem_website, status_prospeccao)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 'novo')
    """, (
        nome,
        d.get('categoria', 'Teste'),
        d.get('cidade', ''),
        d.get('estado', ''),
        tel_limpo,
        tel_raw,
        d.get('endereco', ''),
        d.get('descricao', 'Empresa criada manualmente para teste'),
        d.get('segmento', 'Teste'),
        d.get('grupo', 'Manual'),
    ))
    conn.commit()
    emp_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    # Já jogar no Kanban se tiver telefone
    if tel_limpo:
        conn.execute("""
            INSERT INTO kanban_contatos (empresa_id, telefone_wa, kanban_coluna, is_teste)
            VALUES (?, ?, 'Fila', 1)
        """, (emp_id, tel_limpo))
        conn.commit()

    conn.close()
    return jsonify({'ok': True, 'empresa_id': emp_id})

@app.route('/api/kanban', methods=['POST'])
def kanban_adicionar():
    d = request.json or {}
    empresa_id = d.get('empresa_id')
    if not empresa_id:
        return jsonify({'erro': 'empresa_id obrigatório'}), 400

    conn = get_db()

    # Verificar se já está no kanban
    existente = conn.execute(
        "SELECT id FROM kanban_contatos WHERE empresa_id = ?", (empresa_id,)
    ).fetchone()
    if existente:
        conn.close()
        return jsonify({'erro': 'Empresa já está no Kanban', 'id': existente['id']}), 409

    # Buscar telefone da empresa
    emp = conn.execute(
        "SELECT telefone, telefone_formatado FROM empresas WHERE id = ?", (empresa_id,)
    ).fetchone()
    if not emp:
        conn.close()
        return jsonify({'erro': 'Empresa não encontrada'}), 404

    import re as _re
    tel_raw = emp['telefone_formatado'] or emp['telefone'] or ''
    tel_limpo = _re.sub(r'\D', '', tel_raw)

    conn.execute("""
        INSERT INTO kanban_contatos (empresa_id, telefone_wa, kanban_coluna)
        VALUES (?, ?, 'Fila')
    """, (empresa_id, tel_limpo))
    conn.commit()
    row_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.close()
    return jsonify({'ok': True, 'id': row_id})

@app.route('/api/kanban/lote', methods=['POST'])
def kanban_adicionar_lote():
    """Adiciona múltiplas empresas ao Kanban de uma vez."""
    d = request.json or {}
    ids = d.get('empresa_ids', [])
    if not ids or not isinstance(ids, list):
        return jsonify({'erro': 'empresa_ids deve ser uma lista'}), 400

    import re as _re
    conn = get_db()
    adicionados = []
    ja_existiam = []
    bloqueados = []
    erros = []

    for empresa_id in ids:
        try:
            existente = conn.execute(
                "SELECT id FROM kanban_contatos WHERE empresa_id = ?", (empresa_id,)
            ).fetchone()
            if existente:
                ja_existiam.append(empresa_id)
                continue

            emp = conn.execute(
                "SELECT nome, telefone, telefone_formatado FROM empresas WHERE id = ?", (empresa_id,)
            ).fetchone()
            if not emp:
                erros.append(empresa_id)
                continue
            if _empresa_em_lista_negra(conn, empresa_id):
                bloqueados.append({'id': empresa_id, 'nome': emp['nome']})
                continue

            tel_raw = emp['telefone_formatado'] or emp['telefone'] or ''
            tel_limpo = _re.sub(r'\D', '', tel_raw)

            conn.execute("""
                INSERT INTO kanban_contatos (empresa_id, telefone_wa, kanban_coluna)
                VALUES (?, ?, 'Fila')
            """, (empresa_id, tel_limpo))
            adicionados.append({'id': empresa_id, 'nome': emp['nome']})
        except Exception as ex:
            erros.append(empresa_id)

    conn.commit()
    conn.close()
    return jsonify({
        'ok': True,
        'adicionados': len(adicionados),
        'ja_existiam': len(ja_existiam),
        'bloqueados': len(bloqueados),
        'erros': len(erros),
        'detalhes': {
            'adicionados': adicionados,
            'bloqueados': bloqueados,
        }
    })


@app.route('/api/kanban/<int:id>/coluna', methods=['PUT'])
def kanban_mover_coluna(id):
    d = request.json or {}
    nova_coluna = d.get('coluna', '')
    if nova_coluna not in KANBAN_COLUNAS:
        return jsonify({'erro': f'Coluna inválida: {nova_coluna}'}), 400
    conn = get_db()
    conn.execute(
        "UPDATE kanban_contatos SET kanban_coluna = ?, atualizado_em = CURRENT_TIMESTAMP WHERE id = ?",
        (nova_coluna, id)
    )
    conn.commit()
    conn.close()
    return jsonify({'ok': True})

@app.route('/api/kanban/<int:id>', methods=['PUT'])
def kanban_atualizar(id):
    d = request.json or {}
    conn = get_db()
    campos = []
    valores = []
    for campo in ['notas_kanban', 'kanban_coluna', 'telefone_wa', 'mensagem_enviada']:
        if campo in d:
            campos.append(f"{campo} = ?")
            valores.append(d[campo])
    if campos:
        campos.append("atualizado_em = CURRENT_TIMESTAMP")
        valores.append(id)
        conn.execute(f"UPDATE kanban_contatos SET {', '.join(campos)} WHERE id = ?", valores)
        conn.commit()
    row = conn.execute("""
        SELECT kc.*, e.nome, e.categoria, e.cidade
        FROM kanban_contatos kc
        JOIN empresas e ON e.id = kc.empresa_id
        WHERE kc.id = ?
    """, (id,)).fetchone()
    conn.close()
    return jsonify(dict(row) if row else {'erro': 'Não encontrado'})

@app.route('/api/kanban/<int:id>', methods=['DELETE'])
def kanban_remover(id):
    conn = get_db()
    conn.execute("DELETE FROM kanban_contatos WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})

@app.route('/api/kanban/contato/<int:contato_id>', methods=['GET'])
def kanban_contato_info(contato_id):
    """Retorna info atualizada de um contato (usado pelo chat para detectar mudanças de coluna)."""
    conn = get_db()
    row = conn.execute(
        """SELECT kc.*, e.nome, e.categoria, e.cidade,
                  COALESCE(kc.nome_responsavel, e.nome_responsavel) AS nome_responsavel
           FROM kanban_contatos kc
           JOIN empresas e ON e.id = kc.empresa_id
           WHERE kc.id = ?""",
        (contato_id,)
    ).fetchone()
    if not row:
        conn.close()
        return jsonify({'erro': 'Contato não encontrado'}), 404
    contato = dict(row)
    contato['nome_indicacao'] = get_nome_indicacao(contato.get('empresa_id'), conn)
    contato['bloqueado_envio'] = _contato_bloqueado_envio(contato)
    conn.close()
    return jsonify(contato)

@app.route('/api/kanban/contato/<int:contato_id>/envio-status', methods=['GET'])
def kanban_contato_envio_status(contato_id):
    conn = get_db()
    row = conn.execute(
        "SELECT id, kanban_coluna, optout_global, is_teste FROM kanban_contatos WHERE id=?",
        (contato_id,)
    ).fetchone()
    conn.close()
    if not row:
        return jsonify({'ok': False, 'erro': 'Contato nÃ£o encontrado'}), 404

    contato = dict(row)
    bloqueado = _contato_bloqueado_envio(contato)
    return jsonify({
        'ok': True,
        'pode_enviar': not bloqueado,
        'bloqueado': bloqueado,
        'is_teste': bool(contato['is_teste']),
        'motivo': 'Contato em lista negra' if bloqueado else '',
    })


@app.route('/api/kanban/lista-negra', methods=['GET'])
def kanban_lista_negra():
    conn = get_db()
    rows = conn.execute(
        """SELECT kc.id, kc.telefone_wa, kc.kanban_coluna, kc.optout_em, kc.optout_motivo,
                  kc.is_teste, e.nome, e.categoria, e.cidade
             FROM kanban_contatos kc
             JOIN empresas e ON e.id = kc.empresa_id
            WHERE COALESCE(kc.optout_global, 0) = 1
            ORDER BY COALESCE(kc.optout_em, kc.atualizado_em) DESC"""
    ).fetchall()
    conn.close()
    return jsonify({
        'ok': True,
        'total': len(rows),
        'itens': [dict(r) for r in rows],
    })


@app.route('/api/kanban/<int:contato_id>/lista-negra', methods=['POST'])
def kanban_toggle_lista_negra(contato_id):
    d = request.json or {}
    ativo = bool(d.get('ativo', True))
    conn = get_db()
    row = conn.execute(
        "SELECT id, is_teste FROM kanban_contatos WHERE id=?",
        (contato_id,)
    ).fetchone()
    if not row:
        conn.close()
        return jsonify({'ok': False, 'erro': 'Contato não encontrado'}), 404

    if ativo:
        conn.execute(
            """UPDATE kanban_contatos
                  SET kanban_coluna='Descartado',
                      followup_pausado=1,
                      resposta_classificacao='recusou',
                      optout_global=1,
                      optout_em=CURRENT_TIMESTAMP,
                      optout_motivo='manual',
                      atualizado_em=CURRENT_TIMESTAMP
                WHERE id=?""",
            (contato_id,)
        )
    else:
        conn.execute(
            """UPDATE kanban_contatos
                  SET optout_global=0,
                      optout_em=NULL,
                      optout_motivo='liberado_manual',
                      atualizado_em=CURRENT_TIMESTAMP
                WHERE id=?""",
            (contato_id,)
        )

    conn.commit()
    conn.close()
    return jsonify({'ok': True, 'ativo': ativo})

@app.route('/api/kanban/mensagens/<int:contato_id>', methods=['GET'])
def kanban_mensagens(contato_id):
    conn = get_db()
    msgs = conn.execute(
        "SELECT * FROM wa_mensagens WHERE contato_id = ? ORDER BY criado_em ASC",
        (contato_id,)
    ).fetchall()
    conn.close()
    return jsonify([dict(m) for m in msgs])

def _normalizar_fones(telefone):
    """Gera variações do número para lidar com o 9 extra do Brasil."""
    import re as _re
    tel = _re.sub(r'\D', '', telefone)
    variações = {tel}
    # Se tem 13 dígitos (55 + 2 área + 9 + 8 número), tenta sem o 9
    if len(tel) == 13 and tel.startswith('55'):
        sem9 = tel[:4] + tel[5:]   # remove o 9 (pos 4)
        variações.add(sem9)
    # Se tem 12 dígitos, tenta com o 9
    if len(tel) == 12 and tel.startswith('55'):
        com9 = tel[:4] + '9' + tel[4:]
        variações.add(com9)
    # Também tenta sem código do país
    if tel.startswith('55') and len(tel) >= 10:
        variações.add(tel[2:])
    return list(variações)

@app.route('/api/kanban/mensagem-recebida', methods=['POST'])
def kanban_mensagem_recebida():
    """Chamado pelo Node.js quando chega mensagem do WhatsApp."""
    try:
        return _mensagem_recebida_impl()
    except Exception as e:
        print(f'[mensagem-recebida] ERRO: {e}')
        import traceback; traceback.print_exc()
        return jsonify({'ok': False, 'erro': str(e)})

def _mensagem_recebida_impl():
    d = request.json or {}
    telefone = (d.get('telefone') or '').replace('+', '')
    texto = d.get('texto', '')
    numero_wa_id = d.get('numero_wa_id', '')

    conn = get_db()

    # Proteção anti-eco: ignorar se nós mesmos enviamos essa mensagem nos últimos 30s
    eco = conn.execute(
        """SELECT id FROM wa_mensagens
           WHERE direcao='enviada' AND texto=? AND numero_wa_id=?
             AND criado_em >= datetime('now', '-30 seconds')
           LIMIT 1""",
        (texto, numero_wa_id)
    ).fetchone()
    if eco:
        conn.close()
        print(f'[anti-eco] Ignorando eco: {texto[:40]}')
        return jsonify({'ok': True, 'eco': True})

    # === ETAPA 1: Tentar encontrar contato pelo telefone (número normal) ===
    # Prioridade: 1) Enviado+pending_pdf (diagnóstico aguardando confirmação)
    #             2) Enviado (prospecção ativa)
    #             3) Respondeu (conversa em andamento)
    #             4) Qualquer outro (pelo mais recente)
    _PRIO_SQL = """
        SELECT * FROM kanban_contatos
        WHERE telefone_wa = ?
        ORDER BY
            CASE
                WHEN kanban_coluna='Enviado'   AND pending_pdf=1 THEN 0
                WHEN kanban_coluna='Enviado'                     THEN 1
                WHEN kanban_coluna='Respondeu'                   THEN 2
                ELSE 3
            END,
            atualizado_em DESC
        LIMIT 1
    """
    variações = _normalizar_fones(telefone)
    contato = None
    for tel_var in variações:
        contato = conn.execute(_PRIO_SQL, (tel_var,)).fetchone()
        if contato:
            break

    # === ETAPA 2: Se não encontrou por telefone, tentar pelo LID salvo ===
    tel_limpo = re.sub(r'\D', '', telefone)
    if not contato:
        contato = conn.execute(
            "SELECT * FROM kanban_contatos WHERE lid_wa = ? LIMIT 1", (tel_limpo,)
        ).fetchone()
        if contato:
            print(f'[LID] Contato encontrado via lid_wa: id={contato["id"]}')

    # === ETAPA 3: Se ainda não encontrou (LID desconhecido), buscar um único candidato recente ===
    if not contato:
        candidatos = conn.execute(
            """SELECT * FROM kanban_contatos
               WHERE kanban_coluna = 'Enviado'
                 AND numero_wa_id = ?
                 AND (lid_wa IS NULL OR lid_wa = '')
                 AND datetime(atualizado_em) >= datetime('now', '-15 minutes')
               ORDER BY atualizado_em DESC
               LIMIT 2""",
            (numero_wa_id,)
        ).fetchall()
        if len(candidatos) == 1:
            contato = candidatos[0]
            conn.execute("UPDATE kanban_contatos SET lid_wa = ? WHERE id = ?", (tel_limpo, contato['id']))
            print(f'[LID] Novo mapeamento: LID {tel_limpo} => contato id={contato["id"]} (tel: {contato["telefone_wa"]})')
        elif len(candidatos) > 1:
            print(f'[LID] Mapeamento ignorado por ambiguidade: {len(candidatos)} candidatos recentes para {numero_wa_id}')

    # === Processar a mensagem ===
    contato_id = None
    auto_reply = None  # mensagem automática para enviar de volta
    nova_coluna = None

    if contato:
        contato_id = contato['id']
        coluna_atual = contato['kanban_coluna']
        eh_teste = bool(contato['is_teste']) if 'is_teste' in contato.keys() else False

        # ── OPT-OUT: Detectar clique em botão "Sair" ou texto SAIR ───────────
        # Se o lead clicar no botão 🚫 Sair ou responder SAIR/PARAR/etc,
        # marcamos como descartado e paramos todos os follow-ups.
        # Isso é ESSENCIAL para evitar denúncias de spam.
        _txt_optout = texto.strip().lower()
        _optout_palavras = [
            'sair', 'parar', 'para', 'stop', 'cancelar', 'descadastrar',
            'não quero mais', 'nao quero mais', 'remover', 'remove me',
            'não me mande mais', 'nao me mande mais', 'chega', 'pare',
            'bloquear contato', 'bloquear', 'me bloqueie',
            'sair da lista', 'remover da lista',
            '🚫 sair',  # botão baileys vira texto displayText
            'fu_sair',  # buttonId caso chegue como ID
        ]
        _is_optout = any(
            _txt_optout == p or _txt_optout.startswith(p + ' ') or _txt_optout.endswith(' ' + p)
            for p in _optout_palavras
        )
        if _is_optout and eh_teste:
            conn.execute(
                """UPDATE kanban_contatos
                   SET kanban_coluna='Descartado', followup_pausado=0,
                       resposta_classificacao='recusou',
                       optout_global=0, optout_em=NULL, optout_motivo='teste_validacao',
                       ultima_msg=?, ultima_msg_em=CURRENT_TIMESTAMP,
                       atualizado_em=CURRENT_TIMESTAMP
                   WHERE id=?""",
                (texto, contato_id)
            )
            conn.commit()
            nova_coluna = 'Descartado'
            auto_reply = "Teste registrado. Como este numero esta marcado como teste, ele continua liberado para novas validacoes."
            print(f'[OptOutTeste] Contato {contato_id} marcou sair, mas segue liberado para testes')
            conn.close()
            return jsonify({'ok': True, 'auto_reply': auto_reply, 'telefone': telefone,
                            'contato_id': contato_id, 'nova_coluna': nova_coluna})
        if _is_optout:
            conn.execute(
                """UPDATE kanban_contatos
                   SET kanban_coluna='Descartado', followup_pausado=1,
                       resposta_classificacao='recusou',
                       optout_global=1, optout_em=CURRENT_TIMESTAMP, optout_motivo='optout',
                       ultima_msg=?, ultima_msg_em=CURRENT_TIMESTAMP,
                       atualizado_em=CURRENT_TIMESTAMP
                   WHERE id=?""",
                (texto, contato_id)
            )
            conn.commit()
            nova_coluna = 'Descartado'
            auto_reply = "Tudo bem! Removi você da lista. Não enviarei mais mensagens. 🙏 Boa sorte no seu negócio!"
            print(f'[OptOut] Contato {contato_id} saiu da lista voluntariamente')
            conn.close()
            return jsonify({'ok': True, 'auto_reply': auto_reply, 'telefone': telefone,
                            'contato_id': contato_id, 'nova_coluna': nova_coluna})

        # ── BOTÃO "Depois": adia próximo follow-up em 48h ────────────────────
        _txt_depois = texto.strip().lower()
        _depois_palavras = ['⏰ depois (48h)', 'depois', 'fu_depois', 'mais tarde']
        _is_depois = any(_txt_depois == p for p in _depois_palavras)
        if _is_depois:
            nova_coluna = 'Respondeu' if coluna_atual == 'Enviado' else coluna_atual
            conn.execute(
                """UPDATE kanban_contatos
                   SET kanban_coluna=?,
                       ja_respondeu=1,
                       followup_pausado=0,
                       resposta_classificacao='depois',
                       followup_adiar_ate=datetime('now', '+48 hours'),
                       atualizado_em=CURRENT_TIMESTAMP,
                       ultima_msg=?, ultima_msg_em=CURRENT_TIMESTAMP
                   WHERE id=?""",
                (nova_coluna, texto, contato_id)
            )
            conn.commit()
            auto_reply = "Perfeito. Vou retomar o contato daqui a cerca de 48 horas."
            print(f'[BotaoDepois] Contato {contato_id} adiou follow-up por 48h')
            conn.close()
            return jsonify({
                'ok': True,
                'telefone': telefone,
                'contato_id': contato_id,
                'auto_reply': auto_reply,
                'nova_coluna': nova_coluna,
            })

        # ── FLUXO 1: Enviado → Respondeu (primeira resposta do lead) ──
        if coluna_atual == 'Enviado':
            # Verificar se este contato está aguardando confirmação para receber PDF
            _contato_keys = list(contato.keys())
            _pending_pdf = contato['pending_pdf'] if 'pending_pdf' in _contato_keys else 0

            if _pending_pdf == 1:
                # ── FLUXO DIAGNÓSTICO: lead respondeu à abertura do diagnóstico ──
                _tl = texto.strip().lower()
                _sim_pats = ['sim', 'si', 'yes', 'quero', 'pode', 'bora', 'vamos',
                             'claro', 'com certeza', 'manda', 'manda ai', 'manda aí',
                             'quero ver', 'quero sim', 'pode mandar', 'show', 'top',
                             'pode sim', 'manda la', 'manda lá', 'opa', 'ok', 's']
                _respondeu_sim_diag = any(
                    r == _tl or _tl.startswith(r + ' ') or _tl.startswith(r + ',')
                    or f' {r} ' in f' {_tl} '
                    for r in _sim_pats
                )
                if _respondeu_sim_diag:
                    conn.execute(
                        """UPDATE kanban_contatos
                           SET kanban_coluna='Negociando', ja_respondeu=1, ultima_msg=?, ultima_msg_em=CURRENT_TIMESTAMP,
                               resposta_classificacao='interesse', ja_respondeu=1, atualizado_em=CURRENT_TIMESTAMP
                           WHERE id=?""",
                        (texto, contato_id)
                    )
                    nova_coluna = 'Negociando'
                    print(f'[DiagPDF] Contato {contato_id} confirmou → gerando e enviando PDF')
                    _emp_pdf = conn.execute("SELECT * FROM empresas WHERE id=?", (contato['empresa_id'],)).fetchone()
                    if _emp_pdf:
                        try:
                            import base64 as _b64
                            _cfg2 = {r['chave']: r['valor'] for r in
                                     conn.execute("SELECT chave, valor FROM config").fetchall()}
                            _ed = dict(_emp_pdf)
                            _dados_pdf = {
                                'nome':             _ed.get('nome') or 'Empresa',
                                'categoria':        _ed.get('categoria') or '',
                                'telefone':         _ed.get('telefone_formatado') or _ed.get('telefone') or '',
                                'endereco':         _ed.get('endereco') or '',
                                'cidade':           ', '.join(filter(None, [_ed.get('cidade'), _ed.get('estado')])),
                                'tem_website':      bool(_ed.get('tem_website')),
                                'website_url':      _ed.get('website') or '',
                                'avaliacao':        float(_ed.get('rating') or 0),
                                'total_avaliacoes': int(_ed.get('reviews') or 0),
                                'total_fotos':      int(_ed.get('qtd_fotos') or 0),
                                'distribuicao_estrelas': {
                                    5: int(_ed.get('dist_5estrelas') or 0),
                                    4: int(_ed.get('dist_4estrelas') or 0),
                                    3: int(_ed.get('dist_3estrelas') or 0),
                                    2: int(_ed.get('dist_2estrelas') or 0),
                                    1: int(_ed.get('dist_1estrela') or 0),
                                },
                                'seu_nome':     _cfg2.get('prospector_nome')     or 'ProspectLocal',
                                'seu_whatsapp': _cfg2.get('prospector_whatsapp') or '',
                                'seu_servico':  _cfg2.get('prospector_servico')  or 'Criacao de Sites Profissionais',
                            }
                            _buf2 = io.BytesIO()
                            _build_pdf(_dados_pdf, _buf2)
                            _pdf_b64 = _b64.b64encode(_buf2.getvalue()).decode()
                            _fname2 = re.sub(r'[^\w\s-]', '', _ed.get('nome', 'empresa')).strip().replace(' ', '_')
                            _fname2 = f"diagnostico_{_fname2}.pdf"
                            _wa_url2 = _cfg2.get('wa_service_url', 'http://localhost:3001')
                            _num_id2 = contato['numero_wa_id']
                            _tel2    = contato['telefone_wa']
                            _msg_ap2 = _cfg2.get('msg_apos_pdf') or (
                                "Aqui esta o Diagnostico Digital de vocês! 📊\n\n"
                                "Qualquer duvida, pode me chamar. Fico a disposicao!"
                            )
                            import urllib.request as _ur2
                            _rdata2 = json.dumps({
                                'numeroId': _num_id2, 'telefone': _tel2,
                                'pdfBase64': _pdf_b64, 'fileName': _fname2,
                                'mensagemApos': _msg_ap2,
                            }).encode()
                            _req2 = _ur2.Request(
                                f'{_wa_url2}/api/enviar-documento', data=_rdata2,
                                headers={'Content-Type': 'application/json'}, method='POST'
                            )
                            with _ur2.urlopen(_req2, timeout=20) as _resp2:
                                _wa_res2 = json.loads(_resp2.read())
                            if _wa_res2.get('ok'):
                                print(f'[DiagPDF] PDF enviado com sucesso para contato {contato_id}')
                                conn.execute("UPDATE kanban_contatos SET pending_pdf=0 WHERE id=?", (contato_id,))
                            else:
                                print(f'[DiagPDF] Falha WA ao enviar PDF: {_wa_res2.get("error")}')
                        except Exception as _ep:
                            print(f'[DiagPDF] ERRO ao gerar/enviar PDF (Enviado→Negociando): {_ep}')
                    auto_reply = None  # mensagem após o PDF já está no payload
                else:
                    # Respondeu algo diferente de SIM (ex: pergunta, não)
                    conn.execute(
                        """UPDATE kanban_contatos
                           SET kanban_coluna='Respondeu', ja_respondeu=1, ultima_msg=?, ultima_msg_em=CURRENT_TIMESTAMP,
                               resposta_classificacao='neutro', atualizado_em=CURRENT_TIMESTAMP
                           WHERE id=?""",
                        (texto, contato_id)
                    )
                    nova_coluna = 'Respondeu'
                    auto_reply = None
                    print(f'[DiagPDF] Contato {contato_id} respondeu mas não confirmou PDF → Respondeu')

            else:
                # ── Fluxo normal: primeira resposta ao script de prospecção ──
                empresa = conn.execute(
                    "SELECT nome, categoria, cidade FROM empresas WHERE id = ?",
                    (contato['empresa_id'],)
                ).fetchone()
                nome_empresa = empresa['nome'] if empresa else 'sua empresa'
                categoria = empresa['categoria'] if empresa else 'seu negócio'
                cidade = empresa['cidade'] if empresa else ''
                classificacao_negociacao = _classificar_resposta_negociacao(texto)
                primeira_classificacao = _classificar_primeira_resposta(texto)

                if classificacao_negociacao == 'sim':
                    conn.execute(
                        """UPDATE kanban_contatos
                           SET kanban_coluna='Negociando', ja_respondeu=1, ultima_msg=?, ultima_msg_em=CURRENT_TIMESTAMP,
                               resposta_classificacao='interesse', atualizado_em=CURRENT_TIMESTAMP
                           WHERE id=?""",
                        (texto, contato_id)
                    )
                    nova_coluna = 'Negociando'
                    cfg_pedir = conn.execute("SELECT valor FROM config WHERE chave='pedir_nome_ativo'").fetchone()
                    row_nome = conn.execute(
                        "SELECT nome_responsavel FROM empresas WHERE id=?",
                        (contato['empresa_id'],)
                    ).fetchone()
                    nome_resp_ja_salvo = contato['nome_responsavel'] or (row_nome['nome_responsavel'] if row_nome else '')
                    if cfg_pedir and cfg_pedir['valor'] == '1' and not nome_resp_ja_salvo:
                        tpl_nome = conn.execute("SELECT valor FROM config WHERE chave='msg_pedir_nome'").fetchone()
                        auto_reply = tpl_nome['valor'] if tpl_nome else "Otimo! Com quem tenho o prazer de falar?"
                        conn.execute("UPDATE kanban_contatos SET aguardando_nome=1 WHERE id=?", (contato_id,))
                    else:
                        tpl_sim = conn.execute("SELECT valor FROM config WHERE chave='msg_resposta_sim'").fetchone()
                        tpl_sim_txt = tpl_sim['valor'] if tpl_sim else "Otimo! Vou te enviar o link do site da *{nome}* em breve!"
                        resp_nome = nome_resp_ja_salvo or nome_empresa
                        auto_reply = _formatar_template(tpl_sim_txt, nome=nome_empresa, responsavel=resp_nome)
                    print(f'[Kanban] Card {contato_id} movido direto para Negociando (interesse na primeira resposta)')
                elif classificacao_negociacao == 'nao':
                    conn.execute(
                        """UPDATE kanban_contatos
                           SET kanban_coluna='Descartado',
                               followup_pausado=?,
                               resposta_classificacao='sem_interesse',
                               optout_global=?,
                               optout_em=CASE WHEN ? = 1 THEN NULL ELSE CURRENT_TIMESTAMP END,
                               optout_motivo=?,
                               ultima_msg=?, ultima_msg_em=CURRENT_TIMESTAMP, atualizado_em=CURRENT_TIMESTAMP
                           WHERE id=?""",
                        (
                            0 if eh_teste else 1,
                            0 if eh_teste else 1,
                            1 if eh_teste else 0,
                            'teste_validacao' if eh_teste else 'nao_interesse',
                            texto,
                            contato_id,
                        )
                    )
                    nova_coluna = 'Descartado'
                    tpl_nao = conn.execute("SELECT valor FROM config WHERE chave='msg_resposta_nao'").fetchone()
                    auto_reply = tpl_nao['valor'] if tpl_nao else "Sem problemas! Obrigado pelo seu tempo."
                    print(f'[Kanban] Card {contato_id} descartado ja na primeira resposta (sem interesse)')
                elif primeira_classificacao == 'automatica':
                    conn.execute(
                        """UPDATE kanban_contatos
                           SET ultima_msg=?, ultima_msg_em=CURRENT_TIMESTAMP,
                               resposta_classificacao=?, atualizado_em=CURRENT_TIMESTAMP
                           WHERE id=?""",
                        (texto, primeira_classificacao, contato_id)
                    )
                    tpl_2a = conn.execute("SELECT valor FROM config WHERE chave='msg_segunda_abordagem'").fetchone()
                    tpl_2a_txt = tpl_2a['valor'] if tpl_2a else (
                        "Perfeito, obrigado por responder.\n\n"
                        "Montei uma ideia inicial para *{categoria}* em *{cidade}* e posso te mostrar sem compromisso.\n\n"
                        "Se fizer sentido, eu envio o exemplo aqui. Pode ser?"
                    )
                    auto_reply = _formatar_template(
                        tpl_2a_txt,
                        nome=nome_empresa,
                        categoria=categoria,
                        cidade=cidade,
                    )
                    print(f'[Kanban] Card {contato_id} permaneceu em Enviado (resposta automática)')
                else:
                    conn.execute(
                        """UPDATE kanban_contatos
                           SET kanban_coluna='Respondeu', ja_respondeu=1, ultima_msg=?, ultima_msg_em=CURRENT_TIMESTAMP,
                               resposta_classificacao=?, atualizado_em=CURRENT_TIMESTAMP
                           WHERE id=?""",
                        (texto, primeira_classificacao, contato_id)
                    )
                    nova_coluna = 'Respondeu'
                    print(f'[Kanban] Card {contato_id} movido para Respondeu ({primeira_classificacao})')

                    tpl_2a = conn.execute("SELECT valor FROM config WHERE chave='msg_segunda_abordagem'").fetchone()
                    tpl_2a_txt = tpl_2a['valor'] if tpl_2a else (
                        "Perfeito, obrigado por responder.\n\n"
                        "Montei uma ideia inicial para *{categoria}* em *{cidade}* e posso te mostrar sem compromisso.\n\n"
                        "Se fizer sentido, eu envio o exemplo aqui. Pode ser?"
                    )
                    auto_reply = _formatar_template(
                        tpl_2a_txt,
                        nome=nome_empresa,
                        categoria=categoria,
                        cidade=cidade,
                    )
                    print(f'[AutoReply] Segunda abordagem preparada para contato {contato_id}')

        # ── FLUXO 2: Respondeu → Negociando/Descartado (resposta Sim/Não) ──
        elif coluna_atual == 'Respondeu':
            classificacao_negociacao = _classificar_resposta_negociacao(texto)
            respondeu_sim = classificacao_negociacao == 'sim'
            respondeu_nao = classificacao_negociacao == 'nao'
            texto_lower = _texto_normalizado(texto)

            # Detectar SIM (aceita variações)
            respostas_sim = ['sim', 'si', 'yes', 'quero', 'pode', 'bora', 'vamos',
                             'claro', 'com certeza', 'manda', 'manda ai', 'manda aí',
                             'quero ver', 'quero sim', 'pode mandar', 'show', 'top',
                             'interessado', 'tenho interesse', 'gostaria', 'positivo', 's',
                             'pode sim', 'manda la', 'manda lá', 'opa', 'ok']
            # Detectar NÃO
            respostas_nao = ['não', 'nao', 'no', 'n', 'nope', 'não quero',
                             'nao quero', 'não preciso', 'nao preciso',
                             'não obrigado', 'nao obrigado', 'sem interesse',
                             'não tenho interesse', 'nao tenho interesse', 'dispenso',
                             'não, obrigado']

            # Busca flexível: palavra exata OU contida na frase (ex: "eu já disse sim")
            def detectar_resposta(texto_lower, lista):
                # 1) Match exato ou começa com a resposta
                for r in lista:
                    if r == texto_lower or texto_lower.startswith(r + ' ') or texto_lower.startswith(r + ','):
                        return True
                # 2) Contém a palavra-chave dentro da frase (para frases maiores)
                palavras_chave = [r for r in lista if len(r) >= 3]  # só palavras com 3+ chars para evitar falsos positivos
                for r in palavras_chave:
                    if f' {r} ' in f' {texto_lower} ':  # word boundary simples
                        return True
                return False

            respondeu_sim = detectar_resposta(texto_lower, respostas_sim)
            respondeu_nao = detectar_resposta(texto_lower, respostas_nao)
            classificacao_negociacao = _classificar_resposta_negociacao(texto)

            if classificacao_negociacao == 'sim':
                respondeu_sim = True
            elif classificacao_negociacao == 'nao':
                respondeu_nao = True

            if respondeu_sim:
                # Mover para Negociando
                conn.execute(
                    """UPDATE kanban_contatos
                       SET kanban_coluna='Negociando', ja_respondeu=1, ultima_msg=?, ultima_msg_em=CURRENT_TIMESTAMP,
                           resposta_classificacao='interesse', atualizado_em=CURRENT_TIMESTAMP
                       WHERE id=?""",
                    (texto, contato_id)
                )
                nova_coluna = 'Negociando'
                print(f'[Kanban] Card {contato_id} → Negociando (respondeu SIM)')

                # Buscar dados da empresa
                empresa = conn.execute(
                    "SELECT * FROM empresas WHERE id = ?",
                    (contato['empresa_id'],)
                ).fetchone()
                nome_empresa = empresa['nome'] if empresa else 'sua empresa'

                # ── FLUXO DIAGNÓSTICO: se pending_pdf=1, enviar o PDF automaticamente ──
                _cpk2 = list(contato.keys())
                _pend2 = contato['pending_pdf'] if 'pending_pdf' in _cpk2 else 0
                if _pend2 == 1 and empresa:
                    print(f'[DiagPDF] Contato {contato_id} tem pending_pdf=1 → enviando PDF')
                    try:
                        cfg_pdf = {r['chave']: r['valor'] for r in
                                   conn.execute("SELECT chave, valor FROM config").fetchall()}
                        import base64 as _b64
                        emp_dict = dict(empresa)
                        dados_pdf = {
                            'nome':              emp_dict.get('nome') or 'Empresa',
                            'categoria':         emp_dict.get('categoria') or '',
                            'telefone':          emp_dict.get('telefone_formatado') or emp_dict.get('telefone') or '',
                            'endereco':          emp_dict.get('endereco') or '',
                            'cidade':            ', '.join(filter(None, [emp_dict.get('cidade'), emp_dict.get('estado')])),
                            'tem_website':       bool(emp_dict.get('tem_website')),
                            'website_url':       emp_dict.get('website') or '',
                            'avaliacao':         float(emp_dict.get('rating') or 0),
                            'total_avaliacoes':  int(emp_dict.get('reviews') or 0),
                            'total_fotos':       int(emp_dict.get('qtd_fotos') or 0),
                            'distribuicao_estrelas': {
                                5: int(emp_dict.get('dist_5estrelas') or 0),
                                4: int(emp_dict.get('dist_4estrelas') or 0),
                                3: int(emp_dict.get('dist_3estrelas') or 0),
                                2: int(emp_dict.get('dist_2estrelas') or 0),
                                1: int(emp_dict.get('dist_1estrela') or 0),
                            },
                            'seu_nome':      cfg_pdf.get('prospector_nome')     or 'ProspectLocal',
                            'seu_whatsapp':  cfg_pdf.get('prospector_whatsapp') or '',
                            'seu_servico':   cfg_pdf.get('prospector_servico')  or 'Criacao de Sites Profissionais',
                        }
                        buf_pdf = io.BytesIO()
                        _build_pdf(dados_pdf, buf_pdf)
                        pdf_b64 = _b64.b64encode(buf_pdf.getvalue()).decode()
                        file_name = re.sub(r'[^\w\s-]', '', emp_dict.get('nome', 'empresa')).strip().replace(' ', '_')
                        file_name = f"diagnostico_{file_name}.pdf"

                        wa_url = cfg_pdf.get('wa_service_url', 'http://localhost:3001')
                        numero_id = contato['numero_wa_id'] or ''
                        tel_lead  = contato['telefone_wa'] or ''

                        msg_apos = cfg_pdf.get('msg_apos_pdf') or (
                            "Aqui esta o Diagnostico Digital de vocês! 📊\n\n"
                            "Qualquer duvida, pode me chamar. Fico a disposicao!"
                        )

                        import urllib.request as _ur
                        req_data = json.dumps({
                            'numeroId':    numero_id,
                            'telefone':    tel_lead,
                            'pdfBase64':   pdf_b64,
                            'fileName':    file_name,
                            'mensagemApos': msg_apos,
                        }).encode()
                        req_obj = _ur.Request(
                            f'{wa_url}/api/enviar-documento',
                            data=req_data,
                            headers={'Content-Type': 'application/json'},
                            method='POST'
                        )
                        with _ur.urlopen(req_obj, timeout=20) as resp:
                            wa_pdf_result = json.loads(resp.read())

                        if wa_pdf_result.get('ok'):
                            print(f'[DiagPDF] PDF enviado com sucesso para contato {contato_id}')
                            conn.execute("UPDATE kanban_contatos SET pending_pdf=0 WHERE id=?", (contato_id,))
                        else:
                            print(f'[DiagPDF] Falha ao enviar PDF: {wa_pdf_result.get("error")}')
                    except Exception as pdf_err:
                        print(f'[DiagPDF] ERRO ao gerar/enviar PDF: {pdf_err}')
                    # Não envia auto_reply de texto — a mensagem após o PDF já serve
                    auto_reply = None
                else:
                    # Fluxo normal (sem pending_pdf)
                    cfg_pedir = conn.execute("SELECT valor FROM config WHERE chave='pedir_nome_ativo'").fetchone()
                    nome_resp_ja_salvo = contato['nome_responsavel'] or conn.execute(
                        "SELECT nome_responsavel FROM empresas WHERE id=?", (contato['empresa_id'],)
                    ).fetchone()['nome_responsavel']

                    if cfg_pedir and cfg_pedir['valor'] == '1' and not nome_resp_ja_salvo:
                        tpl_nome = conn.execute("SELECT valor FROM config WHERE chave='msg_pedir_nome'").fetchone()
                        auto_reply = tpl_nome['valor'] if tpl_nome else "Otimo! Com quem tenho o prazer de falar?"
                        conn.execute("UPDATE kanban_contatos SET aguardando_nome=1 WHERE id=?", (contato_id,))
                        print(f'[AutoReply] Perguntando nome para contato {contato_id}')
                    else:
                        tpl_sim = conn.execute("SELECT valor FROM config WHERE chave='msg_resposta_sim'").fetchone()
                        tpl_sim_txt = tpl_sim['valor'] if tpl_sim else "Otimo! Vou te enviar o link do site da *{nome}* em breve!"
                        resp_nome = nome_resp_ja_salvo or nome_empresa
                        auto_reply = _formatar_template(tpl_sim_txt, nome=nome_empresa, responsavel=resp_nome)

                print(f'[AutoReply] Resposta SIM preparada para contato {contato_id}')

            elif respondeu_nao:
                # Mover para Descartado
                conn.execute(
                    """UPDATE kanban_contatos
                       SET kanban_coluna='Descartado',
                           followup_pausado=?,
                           resposta_classificacao='sem_interesse',
                           optout_global=?,
                           optout_em=CASE WHEN ? = 1 THEN NULL ELSE CURRENT_TIMESTAMP END,
                           optout_motivo=?,
                           ultima_msg=?, ultima_msg_em=CURRENT_TIMESTAMP, atualizado_em=CURRENT_TIMESTAMP
                       WHERE id=?""",
                    (
                        0 if eh_teste else 1,
                        0 if eh_teste else 1,
                        1 if eh_teste else 0,
                        'teste_validacao' if eh_teste else 'nao_interesse',
                        texto,
                        contato_id,
                    )
                )
                nova_coluna = 'Descartado'
                print(f'[Kanban] Card {contato_id} → Descartado (respondeu NÃO)')

                tpl_nao = conn.execute("SELECT valor FROM config WHERE chave='msg_resposta_nao'").fetchone()
                auto_reply = tpl_nao['valor'] if tpl_nao else "Sem problemas! Obrigado pelo seu tempo. 🙏 Sucesso no seu negócio! 💪"
                print(f'[AutoReply] Resposta NÃO preparada para contato {contato_id}')

            else:
                # Resposta indefinida — não move, apenas registra
                conn.execute(
                    """UPDATE kanban_contatos
                       SET ultima_msg=?, ultima_msg_em=CURRENT_TIMESTAMP, atualizado_em=CURRENT_TIMESTAMP
                       WHERE id=?""",
                    (texto, contato_id)
                )
                print(f'[Kanban] Card {contato_id} respondeu em "Respondeu" mas texto indefinido: "{texto[:50]}"')

        # ── FLUXO 3: Negociando — capturar nome do responsável se aguardando ──
        elif coluna_atual == 'Negociando' and contato['aguardando_nome']:
            nome_capturado = texto.strip()
            # Salvar o nome e desativar flag
            conn.execute(
                """UPDATE kanban_contatos
                   SET nome_responsavel=?, aguardando_nome=0,
                       ultima_msg=?, ultima_msg_em=CURRENT_TIMESTAMP, atualizado_em=CURRENT_TIMESTAMP
                   WHERE id=?""",
                (nome_capturado, texto, contato_id)
            )
            print(f'[NomeResp] Nome capturado via conversa: "{nome_capturado}" para contato {contato_id}')

            # Agora enviar a mensagem de confirmação com o nome personalizado
            empresa = conn.execute(
                "SELECT nome FROM empresas WHERE id = ?", (contato['empresa_id'],)
            ).fetchone()
            nome_empresa = empresa['nome'] if empresa else 'sua empresa'
            tpl_sim = conn.execute("SELECT valor FROM config WHERE chave='msg_resposta_sim'").fetchone()
            tpl_sim_txt = tpl_sim['valor'] if tpl_sim else "Ótimo {responsavel}! 🎉 Vou te enviar o link do site da *{nome}* em breve!"
            auto_reply = _formatar_template(tpl_sim_txt, nome=nome_empresa, responsavel=nome_capturado)
            print(f'[AutoReply] Confirmação pós-nome para {nome_capturado}')

        # ── OUTROS ESTADOS: apenas registra a mensagem ──
        else:
            conn.execute(
                """UPDATE kanban_contatos
                   SET ultima_msg=?, ultima_msg_em=CURRENT_TIMESTAMP, atualizado_em=CURRENT_TIMESTAMP
                   WHERE id=?""",
                (texto, contato_id)
            )

    try:
        conn.execute(
            "INSERT INTO wa_mensagens (contato_id, direcao, texto, numero_wa_id) VALUES (?, 'recebida', ?, ?)",
            (contato_id or 0, texto, numero_wa_id)
        )
        conn.commit()
    except Exception as e:
        print(f'[mensagem-recebida] Erro DB: {e}')
    finally:
        conn.close()

    resultado = {'ok': True, 'contato_id': contato_id}
    if auto_reply:
        resultado['auto_reply'] = auto_reply
        resultado['telefone'] = telefone
    if nova_coluna:
        resultado['nova_coluna'] = nova_coluna
    return jsonify(resultado)

@app.route('/api/kanban/mensagem-enviada', methods=['POST'])
def kanban_mensagem_enviada():
    """Chamado pelo Node.js quando envia mensagem"""
    d = request.json or {}
    contato_id = d.get('contato_id', 0)
    texto = d.get('texto', '')
    numero_wa_id = d.get('numero_wa_id', '')
    template_nome = str(d.get('template_nome') or d.get('templateNome') or '').strip()
    contexto_envio = str(d.get('contexto_envio') or d.get('contextoEnvio') or '').strip()
    tipo_envio = str(d.get('tipo_envio') or d.get('tipoEnvio') or 'text').strip() or 'text'
    if not template_nome and contexto_envio == 'chat_kanban':
        template_nome = 'Manual - Chat Kanban'
    elif not template_nome and contexto_envio == 'lote_abertura':
        template_nome = 'Manual - Lote'
    elif not template_nome and contexto_envio == 'followup':
        template_nome = 'Follow-up automatico'
    conn = get_db()
    conn.execute(
        """INSERT INTO wa_mensagens (contato_id, direcao, texto, numero_wa_id, template_nome, contexto_envio, tipo_envio)
           VALUES (?, 'enviada', ?, ?, ?, ?, ?)""",
        (contato_id, texto, numero_wa_id, template_nome, contexto_envio, tipo_envio)
    )
    if contato_id:
        # Verificar coluna atual — só mover para "Enviado" se estiver na Fila (primeiro envio)
        # Para auto-replies (quando já está em Respondeu, Negociando, etc), NÃO resetar a coluna
        row = conn.execute("SELECT kanban_coluna FROM kanban_contatos WHERE id=?", (contato_id,)).fetchone()
        coluna_atual = row['kanban_coluna'] if row else 'Fila'

        if coluna_atual == 'Fila':
            # Primeiro envio: mover para Enviado
            conn.execute(
                """UPDATE kanban_contatos
                   SET kanban_coluna='Enviado', mensagem_enviada=?, numero_wa_id=?,
                       followup_etapa=0, followup_enviado_em=NULL, followup_adiar_ate=NULL, resposta_classificacao=NULL,
                       template_origem=CASE WHEN COALESCE(template_origem, '') = '' THEN ? ELSE template_origem END,
                       ultimo_template_nome=CASE WHEN ? != '' THEN ? ELSE ultimo_template_nome END,
                       ultimo_contexto_envio=CASE WHEN ? != '' THEN ? ELSE ultimo_contexto_envio END,
                       atualizado_em=CURRENT_TIMESTAMP
                   WHERE id=?""",
                (
                    texto, numero_wa_id,
                    template_nome,
                    template_nome, template_nome,
                    contexto_envio, contexto_envio,
                    contato_id,
                )
            )
            print(f'[mensagem-enviada] Card {contato_id} movido para Enviado (primeiro envio)')
        else:
            # Auto-reply ou mensagem manual posterior: apenas atualizar timestamp, NÃO mudar coluna
            conn.execute(
                """UPDATE kanban_contatos
                   SET ultimo_template_nome=CASE WHEN ? != '' THEN ? ELSE ultimo_template_nome END,
                       ultimo_contexto_envio=CASE WHEN ? != '' THEN ? ELSE ultimo_contexto_envio END,
                       atualizado_em=CURRENT_TIMESTAMP
                   WHERE id=?""",
                (template_nome, template_nome, contexto_envio, contexto_envio, contato_id)
            )
            print(f'[mensagem-enviada] Card {contato_id} permanece em "{coluna_atual}" (auto-reply/manual)')
    conn.commit()
    conn.close()
    return jsonify({'ok': True})

def _cfg(conn, chave, default=''):
    """Helper: lê config do banco com fallback."""
    r = conn.execute("SELECT valor FROM config WHERE chave=?", (chave,)).fetchone()
    return r['valor'] if r else default


def _normalizar_principal_quick_reply_config(raw_buttons=None, footer=''):
    base = DEFAULT_WA_QUICK_REPLY_CONFIG['buttons']
    try:
        dados = json.loads(raw_buttons) if isinstance(raw_buttons, str) else raw_buttons
    except Exception:
        dados = None
    dados = dados if isinstance(dados, list) else []

    botoes = []
    for idx, default_btn in enumerate(base):
        item = dados[idx] if idx < len(dados) and isinstance(dados[idx], dict) else {}
        texto = str(item.get('text') or item.get('label') or default_btn['text']).strip()
        botoes.append({
            'id': default_btn['id'],
            'text': texto or default_btn['text'],
        })

    footer_final = str(footer or DEFAULT_WA_QUICK_REPLY_CONFIG['footer']).strip()
    return {
        'footer': footer_final or DEFAULT_WA_QUICK_REPLY_CONFIG['footer'],
        'buttons': botoes,
    }


def _get_wa_quick_reply_config(conn):
    footer = _cfg(conn, 'wa_quick_reply_footer', DEFAULT_WA_QUICK_REPLY_CONFIG['footer'])
    buttons_raw = _cfg(
        conn,
        'wa_quick_reply_buttons',
        json.dumps(DEFAULT_WA_QUICK_REPLY_CONFIG['buttons'], ensure_ascii=False)
    )
    return _normalizar_principal_quick_reply_config(buttons_raw, footer)


def _contato_bloqueado_envio(contato):
    if not contato:
        return False
    return bool(contato['optout_global']) and not bool(contato['is_teste'])


@app.route('/api/kanban/check-followup', methods=['POST'])
def kanban_check_followup():
    """Verifica leads parados e retorna lista para follow-up — com todas as proteções anti-bloqueio."""
    from datetime import datetime as _dt
    conn = get_db()
    try:
        # ── Proteção 1: sistema desativado ──
        if _cfg(conn, 'followup_ativo', '1') != '1':
            return jsonify({'ok': True, 'followups': [], 'msg': 'Follow-up desativado'})

        # ── Proteção 2: horário seguro (não enviar de madrugada) ──
        hora_inicio = int(_cfg(conn, 'followup_hora_inicio', '8'))
        hora_fim    = int(_cfg(conn, 'followup_hora_fim', '20'))
        hora_atual  = _dt.now().hour
        if not (hora_inicio <= hora_atual < hora_fim):
            return jsonify({'ok': True, 'followups': [],
                            'msg': f'Fora do horário permitido ({hora_inicio}h–{hora_fim}h). Agora: {hora_atual}h'})

        horas        = int(_cfg(conn, 'followup_horas', '48'))
        max_etapas   = int(_cfg(conn, 'followup_max_etapas', '3'))
        so_warm      = _cfg(conn, 'followup_so_warm_leads', '1') == '1'
        tpl          = _cfg(conn, 'msg_followup',
            "Oi, pessoal da *{nome}*.\n\n"
            "Passando só para confirmar se vale a pena eu te mostrar a ideia que montei para ajudar vocês a gerar mais contatos em {cidade}.\n\n"
            "Se fizer sentido, me responde com *posso ver* e eu envio por aqui.")

        # ── Busca leads candidatos ──
        # Proteção 3: respeitar followup_pausado por contato
        # Proteção 4: só warm leads (ja_respondeu=1) se ativado
        warm_filter = "AND COALESCE(kc.ja_respondeu, 0) = 1" if so_warm else ""

        pendentes = conn.execute(f"""
            SELECT kc.id, kc.telefone_wa, kc.numero_wa_id,
                   COALESCE(kc.followup_etapa, 0) AS followup_etapa,
                   kc.kanban_coluna, kc.atualizado_em, kc.followup_adiar_ate,
                   COALESCE(kc.ja_respondeu, 0) AS ja_respondeu,
                   e.nome, e.cidade, e.categoria
            FROM kanban_contatos kc
            JOIN empresas e ON e.id = kc.empresa_id
            WHERE kc.kanban_coluna IN ('Enviado', 'Respondeu', 'Negociando')
              AND COALESCE(kc.resposta_classificacao, '') NOT IN ('automatica', 'nao', 'recusou')
              AND COALESCE(kc.followup_etapa, 0) < ?
              AND COALESCE(kc.pending_pdf, 0) = 0
              AND COALESCE(kc.followup_pausado, 0) = 0
              AND COALESCE(kc.optout_global, 0) = 0
              {warm_filter}
        """, (max_etapas,)).fetchall()

        followups = []
        for p in pendentes:
            etapa_atual  = p['followup_etapa']
            coluna       = p['kanban_coluna']
            nome_emp     = p['nome'] or 'sua empresa'
            cidade       = p['cidade'] or ''
            categoria    = p['categoria'] or 'seu segmento'

            # Tempos de espera por etapa
            if coluna == 'Enviado':
                horas_espera = [horas, 120, 240][min(etapa_atual, 2)]
            else:
                horas_espera = [48, 120, 240][min(etapa_atual, 2)]

            pronto = conn.execute(
                "SELECT 1 FROM kanban_contatos WHERE id=? AND datetime(atualizado_em) <= datetime('now', ? || ' hours')",
                (p['id'], f'-{horas_espera}')
            ).fetchone()
            if not pronto:
                continue

            if p['followup_adiar_ate']:
                ainda_adiado = conn.execute(
                    "SELECT CASE WHEN datetime(?) > datetime('now') THEN 1 ELSE 0 END AS ativo",
                    (p['followup_adiar_ate'],)
                ).fetchone()['ativo']
                if ainda_adiado:
                    continue

            if etapa_atual == 0 and coluna == 'Enviado':
                msg = _formatar_template(tpl, nome=nome_emp, cidade=cidade, categoria=categoria)
            else:
                msg = _template_followup_por_etapa(etapa_atual + 1, nome_emp, cidade, categoria, coluna=coluna)

            conn.execute(
                "UPDATE kanban_contatos SET followup_enviado_em=CURRENT_TIMESTAMP, followup_etapa=followup_etapa+1, followup_adiar_ate=NULL WHERE id=?",
                (p['id'],)
            )
            followups.append({
                'contato_id':  p['id'],
                'telefone':    p['telefone_wa'],
                'numero_wa_id':p['numero_wa_id'],
                'mensagem':    msg,
                'coluna':      coluna,
                'etapa':       etapa_atual + 1,
                'nome':        nome_emp,
            })

        conn.commit()
        print(f'[FollowUp] {len(followups)} follow-up(s) | warm_only={so_warm} | hora={hora_atual}h')
        return jsonify({'ok': True, 'followups': followups})
    except Exception as e:
        print(f'[FollowUp] Erro: {e}')
        return jsonify({'ok': False, 'erro': str(e)})
    finally:
        conn.close()


@app.route('/api/followup/fila')
def followup_fila():
    """Retorna a fila de follow-ups pendentes com previsão de envio."""
    from datetime import datetime as _dt, timedelta as _td
    conn = get_db()
    try:
        cfg_so_warm  = _cfg(conn, 'followup_so_warm_leads', '1') == '1'
        horas_cfg    = int(_cfg(conn, 'followup_horas', '48'))
        max_etapas   = int(_cfg(conn, 'followup_max_etapas', '3'))
        hora_inicio  = int(_cfg(conn, 'followup_hora_inicio', '8'))
        hora_fim     = int(_cfg(conn, 'followup_hora_fim', '20'))
        ativo        = _cfg(conn, 'followup_ativo', '1') == '1'
        warm_filter  = "AND COALESCE(kc.ja_respondeu, 0) = 1" if cfg_so_warm else ""

        todos = conn.execute(f"""
            SELECT kc.id, kc.telefone_wa,
                   COALESCE(kc.followup_etapa, 0) AS followup_etapa,
                   kc.kanban_coluna, kc.atualizado_em, kc.followup_adiar_ate,
                   COALESCE(kc.followup_pausado, 0) AS followup_pausado,
                   COALESCE(kc.ja_respondeu, 0) AS ja_respondeu,
                   e.nome, e.cidade, e.categoria
            FROM kanban_contatos kc
            JOIN empresas e ON e.id = kc.empresa_id
            WHERE kc.kanban_coluna IN ('Enviado', 'Respondeu', 'Negociando')
              AND COALESCE(kc.resposta_classificacao, '') NOT IN ('automatica', 'nao', 'recusou')
              AND COALESCE(kc.followup_etapa, 0) < ?
              AND COALESCE(kc.pending_pdf, 0) = 0
              AND COALESCE(kc.optout_global, 0) = 0
              {warm_filter}
            ORDER BY kc.atualizado_em ASC
            LIMIT 50
        """, (max_etapas,)).fetchall()

        agora = _dt.now()
        itens = []
        for p in todos:
            etapa = p['followup_etapa']
            coluna = p['kanban_coluna']
            if coluna == 'Enviado':
                h = [horas_cfg, 120, 240][min(etapa, 2)]
            else:
                h = [48, 120, 240][min(etapa, 2)]

            try:
                atualizado = _dt.fromisoformat(p['atualizado_em'].replace('Z',''))
            except:
                atualizado = agora

            previsto = atualizado + _td(hours=h)
            if p['followup_adiar_ate']:
                try:
                    adiado_ate = _dt.fromisoformat(str(p['followup_adiar_ate']).replace('Z', ''))
                    if adiado_ate > previsto:
                        previsto = adiado_ate
                except:
                    pass
            pronto   = previsto <= agora
            pausado  = bool(p['followup_pausado'])
            bloqueado_horario = not (hora_inicio <= agora.hour < hora_fim)

            status = 'pausado' if pausado else ('pronto' if pronto else 'aguardando')
            if not pausado and not pronto and p['followup_adiar_ate']:
                status = 'adiado'
            if status == 'pronto' and (bloqueado_horario or not ativo):
                status = 'aguardando_horario' if bloqueado_horario else 'sistema_pausado'

            itens.append({
                'contato_id':   p['id'],
                'nome':         p['nome'],
                'telefone':     p['telefone_wa'],
                'coluna':       coluna,
                'etapa':        etapa + 1,
                'max_etapas':   max_etapas,
                'ja_respondeu': bool(p['ja_respondeu']),
                'pausado':      pausado,
                'status':       status,
                'previsto_em':  previsto.strftime('%d/%m/%Y %H:%M'),
                'horas_restantes': max(0, round((previsto - agora).total_seconds() / 3600, 1)) if not pronto else 0,
            })

        return jsonify({
            'ok': True,
            'sistema_ativo':    ativo,
            'so_warm_leads':    cfg_so_warm,
            'horario_permitido':f'{hora_inicio}h–{hora_fim}h',
            'total':            len(itens),
                'prontos':      sum(1 for i in itens if i['status'] == 'pronto'),
                'aguardando':   sum(1 for i in itens if i['status'] in ('aguardando', 'adiado', 'aguardando_horario', 'sistema_pausado')),
                'pausados':     sum(1 for i in itens if i['status'] == 'pausado'),
            'itens':            itens,
        })
    except Exception as ex:
        return jsonify({'ok': False, 'erro': str(ex)})
    finally:
        conn.close()


@app.route('/api/followup/config', methods=['GET'])
def followup_config_get():
    """Retorna configurações de follow-up."""
    conn = get_db()
    chaves = ['followup_ativo', 'followup_horas', 'followup_max_etapas',
              'followup_so_warm_leads', 'followup_hora_inicio', 'followup_hora_fim',
              'msg_followup', 'msg_followup_etapa2', 'msg_followup_etapa3',
              'followup_botoes_ativos']
    result = {c: _cfg(conn, c, '') for c in chaves}
    conn.close()
    return jsonify(result)


@app.route('/api/followup/config', methods=['POST'])
def followup_config_set():
    """Salva configurações de follow-up."""
    d = request.json or {}
    conn = get_db()
    chaves_permitidas = ['followup_ativo', 'followup_horas', 'followup_max_etapas',
                         'followup_so_warm_leads', 'followup_hora_inicio', 'followup_hora_fim',
                         'msg_followup', 'msg_followup_etapa2', 'msg_followup_etapa3',
                         'followup_botoes_ativos']
    for chave in chaves_permitidas:
        if chave in d:
            conn.execute("INSERT OR REPLACE INTO config (chave, valor) VALUES (?,?)", (chave, str(d[chave])))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})


@app.route('/api/followup/pausar/<int:contato_id>', methods=['POST'])
def followup_pausar_contato(contato_id):
    """Pausa ou retoma follow-up de um contato específico."""
    d = request.json or {}
    pausar = d.get('pausar', True)
    conn = get_db()
    conn.execute("UPDATE kanban_contatos SET followup_pausado=? WHERE id=?", (1 if pausar else 0, contato_id))
    conn.commit()
    conn.close()
    return jsonify({'ok': True, 'pausado': pausar})


@app.route('/api/wa-quick-reply-config', methods=['GET'])
def wa_quick_reply_config_get():
    conn = get_db()
    cfg = _get_wa_quick_reply_config(conn)
    conn.close()
    return jsonify(cfg)


@app.route('/api/wa-quick-reply-config', methods=['POST'])
def wa_quick_reply_config_set():
    d = request.json or {}
    cfg = _normalizar_principal_quick_reply_config(d.get('buttons'), d.get('footer'))
    conn = get_db()
    conn.execute(
        "INSERT OR REPLACE INTO config (chave, valor) VALUES (?, ?)",
        ('wa_quick_reply_footer', cfg['footer'])
    )
    conn.execute(
        "INSERT OR REPLACE INTO config (chave, valor) VALUES (?, ?)",
        ('wa_quick_reply_buttons', json.dumps(cfg['buttons'], ensure_ascii=False))
    )
    conn.commit()
    conn.close()
    return jsonify({'ok': True, **cfg})

@app.route('/api/kanban/mensagens-config', methods=['GET'])
def get_mensagens_config():
    """Retorna as mensagens de abordagem editáveis."""
    conn = get_db()
    chaves = ['msg_segunda_abordagem', 'msg_resposta_sim', 'msg_resposta_nao', 'msg_followup', 'followup_horas', 'followup_ativo', 'pedir_nome_ativo', 'msg_pedir_nome']
    result = {}
    for chave in chaves:
        row = conn.execute("SELECT valor FROM config WHERE chave=?", (chave,)).fetchone()
        result[chave] = row['valor'] if row else ''
    conn.close()
    return jsonify(result)

@app.route('/api/kanban/mensagens-config', methods=['POST'])
def set_mensagens_config():
    """Salva as mensagens de abordagem editáveis."""
    d = request.json or {}
    conn = get_db()
    chaves_permitidas = ['msg_segunda_abordagem', 'msg_resposta_sim', 'msg_resposta_nao', 'msg_followup', 'followup_horas', 'followup_ativo', 'pedir_nome_ativo', 'msg_pedir_nome']
    for chave in chaves_permitidas:
        if chave in d:
            conn.execute("INSERT OR REPLACE INTO config (chave, valor) VALUES (?,?)", (chave, str(d[chave])))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})

@app.route('/api/kanban/<int:cid>/responsavel', methods=['PUT'])
def kanban_salvar_responsavel(cid):
    """Salva nome do responsável manualmente no contato (Opção 2)."""
    d = request.json or {}
    nome = d.get('nome_responsavel', '').strip()
    conn = get_db()
    conn.execute(
        "UPDATE kanban_contatos SET nome_responsavel=?, atualizado_em=CURRENT_TIMESTAMP WHERE id=?",
        (nome or None, cid)
    )
    conn.commit()
    conn.close()
    return jsonify({'ok': True})

@app.route('/api/kanban/<int:cid>/notas', methods=['PUT'])
def kanban_salvar_notas(cid):
    """Salva notas ou briefing estruturado de um card."""
    d = request.json or {}
    briefing = _parse_briefing_lead(d.get('briefing'), d.get('notas', ''))
    briefing_json = json.dumps(briefing, ensure_ascii=False) if _briefing_lead_tem_conteudo(briefing) else None
    notas_resumo = _resumo_briefing_lead(briefing) if briefing_json else str(d.get('notas', '') or '').strip()
    conn = get_db()
    conn.execute(
        """UPDATE kanban_contatos
              SET notas_kanban=?,
                  briefing_lead=?,
                  atualizado_em=CURRENT_TIMESTAMP
            WHERE id=?""",
        (notas_resumo or None, briefing_json, cid)
    )
    conn.commit()
    row = conn.execute(
        "SELECT id, notas_kanban, briefing_lead FROM kanban_contatos WHERE id=?",
        (cid,)
    ).fetchone()
    conn.close()
    return jsonify({
        'ok': True,
        'notas_kanban': row['notas_kanban'] if row else notas_resumo,
        'briefing_lead': json.loads(row['briefing_lead']) if row and row['briefing_lead'] else briefing,
    })

@app.route('/api/kanban/mapear-lid', methods=['POST'])
def kanban_mapear_lid():
    """Recebe mapeamento LID->telefone do Node.js e corrige mensagens órfãs (contato_id=0)"""
    try:
        return _mapear_lid_impl()
    except Exception as e:
        print(f'[mapear-lid] Erro: {e}')
        return jsonify({'ok': False, 'erro': str(e)})

def _mapear_lid_impl():
    d = request.json or {}
    lid_num = re.sub(r'\D', '', d.get('lid', ''))      # ex: "220503939801186"
    telefone = re.sub(r'\D', '', d.get('telefone', '')) # ex: "558393015765"

    if not lid_num or not telefone:
        return jsonify({'ok': False, 'erro': 'lid e telefone sao obrigatorios'})

    conn = get_db()
    variações = _normalizar_fones(telefone)

    # Buscar contato pelo telefone
    contato = None
    for tel_var in variações:
        contato = conn.execute(
            "SELECT * FROM kanban_contatos WHERE telefone_wa = ? LIMIT 1", (tel_var,)
        ).fetchone()
        if contato:
            break

    if not contato:
        conn.close()
        return jsonify({'ok': True, 'mapeado': False, 'msg': 'Contato nao encontrado para ' + telefone})

    contato_id = contato['id']

    # Salvar LID no contato para futuras consultas
    conn.execute("UPDATE kanban_contatos SET lid_wa = ? WHERE id = ? AND (lid_wa IS NULL OR lid_wa = '')", (lid_num, contato_id))

    # Corrigir mensagens órfãs que vieram do LID antes de ter o mapeamento
    orfas = conn.execute(
        "SELECT id FROM wa_mensagens WHERE contato_id = 0 OR contato_id IS NULL LIMIT 50"
    ).fetchall()

    corrigidas = 0
    for m in orfas:
        conn.execute("UPDATE wa_mensagens SET contato_id = ? WHERE id = ?", (contato_id, m['id']))
        corrigidas += 1

    # Se o contato está em "Enviado" e tem mensagens recebidas, mover para Respondeu
    if contato['kanban_coluna'] == 'Enviado' and corrigidas > 0:
        ultima = conn.execute(
            "SELECT texto FROM wa_mensagens WHERE contato_id = ? AND direcao = 'recebida' ORDER BY id DESC LIMIT 1",
            (contato_id,)
        ).fetchone()
        if ultima:
            conn.execute(
                """UPDATE kanban_contatos
                   SET kanban_coluna='Respondeu', ja_respondeu=1, ultima_msg=?, ultima_msg_em=CURRENT_TIMESTAMP,
                       atualizado_em=CURRENT_TIMESTAMP
                   WHERE id=?""",
                (ultima['texto'], contato_id)
            )

    conn.commit()
    conn.close()
    return jsonify({'ok': True, 'mapeado': True, 'contato_id': contato_id, 'mensagens_corrigidas': corrigidas})


@app.route('/api/kanban/stats', methods=['GET'])
def kanban_stats():
    conn = get_db()
    campanha_id = (request.args.get('campanha_id') or '').strip()
    if campanha_id.isdigit():
        rows = conn.execute("""
        SELECT kanban_coluna, COUNT(*) as total
        FROM kanban_contatos
        WHERE campanha_id = ?
        GROUP BY kanban_coluna
    """, (int(campanha_id),)).fetchall()
    else:
        rows = conn.execute("""
        SELECT kanban_coluna, COUNT(*) as total
        FROM kanban_contatos
        GROUP BY kanban_coluna
    """).fetchall()
    conn.close()
    stats = {col: 0 for col in KANBAN_COLUNAS}
    for r in rows:
        stats[r['kanban_coluna']] = r['total']
    return jsonify(stats)


@app.route('/api/kanban/limpar', methods=['POST'])
def kanban_limpar_tudo():
    conn = get_db()
    campanhas = conn.execute("SELECT COUNT(*) FROM campanhas").fetchone()[0]
    contatos = conn.execute("SELECT COUNT(*) FROM kanban_contatos").fetchone()[0]
    conn.execute("DELETE FROM campanha_itens")
    conn.execute("DELETE FROM campanha_numeros")
    conn.execute("DELETE FROM campanhas")
    conn.execute("DELETE FROM wa_mensagens")
    conn.execute("DELETE FROM kanban_contatos")
    conn.commit()
    conn.close()
    return jsonify({
        'ok': True,
        'campanhas_removidas': int(campanhas or 0),
        'contatos_removidos': int(contatos or 0),
    })

# ─────────────────────────────────────────
# FRONTEND
# ─────────────────────────────────────────
@app.route('/')
def index(): return send_from_directory('static', 'index.html')

@app.route('/<path:path>')
def static_files(path): return send_from_directory('static', path)

if __name__ == '__main__':
    init_db()
    print("=" * 55)
    print("  ProspectLocal iniciado!")
    print("  Acesse: http://localhost:5000")
    print("  Para parar: feche esta janela ou CTRL+C")
    print("=" * 55)
    app.run(debug=False, host='127.0.0.1', port=5000)
