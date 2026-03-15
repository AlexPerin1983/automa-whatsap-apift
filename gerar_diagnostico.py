"""
ProspectLocal — Gerador de PDF de Diagnóstico Digital
Uso: python gerar_diagnostico.py
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import KeepTogether
import os

# ─── PALETA DE CORES ────────────────────────────────────────────
AZUL_ESCURO   = colors.HexColor("#0F172A")   # fundo principal
AZUL_MEDIO    = colors.HexColor("#1E293B")   # cards
AZUL_BORDA    = colors.HexColor("#334155")   # bordas
VERDE         = colors.HexColor("#22C55E")   # positivo
VERMELHO      = colors.HexColor("#EF4444")   # alerta / sem site
AMARELO       = colors.HexColor("#F59E0B")   # estrela / aviso
AZUL_DESTAQUE = colors.HexColor("#3B82F6")   # links / destaque
BRANCO        = colors.white
CINZA_CLARO   = colors.HexColor("#CBD5E1")
CINZA_MEDIO   = colors.HexColor("#94A3B8")

# ─── FUNÇÃO PRINCIPAL ───────────────────────────────────────────
def gerar_pdf(dados_empresa: dict, caminho_saida: str = "diagnostico.pdf"):
    """
    Gera o PDF de Diagnóstico Digital para uma empresa.

    Parâmetros de dados_empresa:
        nome            str  — nome da empresa
        categoria       str  — categoria/nicho
        telefone        str  — telefone (ou None)
        endereco        str  — endereço completo
        cidade          str  — cidade / estado
        tem_website     bool — True se tem site
        website_url     str  — URL do site (ou None)
        avaliacao       float— nota Google (0-5)
        total_avaliacoes int  — quantidade de avaliações
        total_fotos     int  — fotos no Google
        seu_nome        str  — seu nome (prospector)
        seu_whatsapp    str  — seu WhatsApp
        seu_servico     str  — nome do serviço oferecido
    """

    doc = SimpleDocTemplate(
        caminho_saida,
        pagesize=A4,
        rightMargin=1.8*cm,
        leftMargin=1.8*cm,
        topMargin=1.5*cm,
        bottomMargin=1.5*cm,
    )

    largura, altura = A4
    story = []

    # ── ESTILOS ─────────────────────────────────────────────────
    def estilo(nome, **kw):
        base = kw.pop("base", "Normal")
        s = getSampleStyleSheet()[base].clone(nome)
        for k, v in kw.items():
            setattr(s, k, v)
        return s

    s_titulo_capa     = estilo("TituloCapa",     fontSize=26, leading=32, textColor=BRANCO,        alignment=TA_CENTER, fontName="Helvetica-Bold")
    s_subtitulo_capa  = estilo("SubtituloCapa",  fontSize=13, leading=18, textColor=AZUL_DESTAQUE, alignment=TA_CENTER, fontName="Helvetica-Bold")
    s_empresa_capa    = estilo("EmpresaCapa",     fontSize=18, leading=24, textColor=VERDE,         alignment=TA_CENTER, fontName="Helvetica-Bold")
    s_cat_capa        = estilo("CatCapa",         fontSize=11, leading=14, textColor=CINZA_CLARO,   alignment=TA_CENTER, fontName="Helvetica")
    s_secao           = estilo("Secao",           fontSize=12, leading=16, textColor=AZUL_DESTAQUE, fontName="Helvetica-Bold", spaceBefore=14, spaceAfter=4)
    s_label           = estilo("Label",           fontSize=8,  leading=11, textColor=CINZA_MEDIO,   fontName="Helvetica-Bold")
    s_valor           = estilo("Valor",           fontSize=10, leading=14, textColor=BRANCO,        fontName="Helvetica")
    s_valor_destaque  = estilo("ValorDestaque",   fontSize=12, leading=16, textColor=VERDE,         fontName="Helvetica-Bold")
    s_alerta          = estilo("Alerta",          fontSize=12, leading=16, textColor=VERMELHO,      fontName="Helvetica-Bold")
    s_body            = estilo("Body",            fontSize=9,  leading=13, textColor=CINZA_CLARO,   fontName="Helvetica")
    s_rodape          = estilo("Rodape",          fontSize=8,  leading=11, textColor=CINZA_MEDIO,   fontName="Helvetica", alignment=TA_CENTER)
    s_cta_titulo      = estilo("CTATitulo",       fontSize=15, leading=20, textColor=BRANCO,        fontName="Helvetica-Bold", alignment=TA_CENTER)
    s_cta_body        = estilo("CTABody",         fontSize=10, leading=14, textColor=CINZA_CLARO,   fontName="Helvetica",      alignment=TA_CENTER)
    s_cta_contato     = estilo("CTAContato",      fontSize=12, leading=16, textColor=VERDE,         fontName="Helvetica-Bold", alignment=TA_CENTER)
    s_badge_sem       = estilo("BadgeSem",        fontSize=13, leading=18, textColor=VERMELHO,      fontName="Helvetica-Bold", alignment=TA_CENTER)
    s_badge_com       = estilo("BadgeCom",        fontSize=13, leading=18, textColor=VERDE,         fontName="Helvetica-Bold", alignment=TA_CENTER)
    s_score_num       = estilo("ScoreNum",        fontSize=36, leading=44, textColor=VERMELHO,      fontName="Helvetica-Bold", alignment=TA_CENTER)
    s_score_max       = estilo("ScoreMax",        fontSize=14, leading=20, textColor=CINZA_MEDIO,   fontName="Helvetica",      alignment=TA_CENTER)

    # helper: célula escura com label + valor
    def celula(label_txt, valor_txt, cor_valor=None):
        cor = cor_valor or BRANCO
        s_v = s_valor_destaque if cor_valor == VERDE else (s_alerta if cor_valor == VERMELHO else s_valor)
        return [Paragraph(label_txt.upper(), s_label), Paragraph(valor_txt, s_v)]

    def card_tabela(linhas, col_widths=None, bg=AZUL_MEDIO):
        """Cria um card escuro com tabela interna."""
        cw = col_widths or [(largura - 3.6*cm) / len(linhas[0])] * len(linhas[0])
        t = Table(linhas, colWidths=cw)
        t.setStyle(TableStyle([
            ("BACKGROUND",  (0, 0), (-1, -1), bg),
            ("ROWBACKGROUNDS", (0,0), (-1,-1), [bg]),
            ("BOX",         (0, 0), (-1, -1), 0.5, AZUL_BORDA),
            ("INNERGRID",   (0, 0), (-1, -1), 0.3, AZUL_BORDA),
            ("TOPPADDING",  (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING",(0,0), (-1, -1), 8),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING",(0, 0), (-1, -1), 10),
            ("VALIGN",      (0, 0), (-1, -1), "TOP"),
        ]))
        return t

    # ════════════════════════════════════════════════════════════
    # CABEÇALHO / CAPA
    # ════════════════════════════════════════════════════════════
    w = largura - 3.6*cm

    capa = Table([
        [Paragraph("📊 DIAGNÓSTICO DIGITAL GRATUITO", s_titulo_capa)],
        [Paragraph("Análise da presença online do seu negócio", s_subtitulo_capa)],
        [Spacer(1, 8)],
        [HRFlowable(width=w*0.6, thickness=1, color=AZUL_DESTAQUE, hAlign="CENTER")],
        [Spacer(1, 8)],
        [Paragraph(dados_empresa["nome"], s_empresa_capa)],
        [Paragraph(dados_empresa["categoria"], s_cat_capa)],
        [Spacer(1, 4)],
    ], colWidths=[w])
    capa.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), AZUL_ESCURO),
        ("BOX",           (0,0), (-1,-1), 1.5, AZUL_DESTAQUE),
        ("TOPPADDING",    (0,0), (-1,-1), 14),
        ("BOTTOMPADDING", (0,0), (-1,-1), 14),
        ("LEFTPADDING",   (0,0), (-1,-1), 20),
        ("RIGHTPADDING",  (0,0), (-1,-1), 20),
        ("ALIGN",         (0,0), (-1,-1), "CENTER"),
    ]))
    story.append(capa)
    story.append(Spacer(1, 14))

    # ════════════════════════════════════════════════════════════
    # INFORMAÇÕES DA EMPRESA
    # ════════════════════════════════════════════════════════════
    story.append(Paragraph("📋  Informações da Empresa", s_secao))

    half = (w - 6) / 2
    info_rows = [
        [celula("📞 Telefone", dados_empresa.get("telefone") or "Não informado"),
         celula("📍 Cidade / Estado", dados_empresa.get("cidade") or "—")],
        [celula("🗺  Endereço", dados_empresa.get("endereco") or "Não informado"),
         celula("🏷  Categoria", dados_empresa.get("categoria") or "—")],
    ]
    story.append(card_tabela(info_rows, col_widths=[half, half]))
    story.append(Spacer(1, 14))

    # ════════════════════════════════════════════════════════════
    # PRESENÇA DIGITAL — STATUS DO SITE
    # ════════════════════════════════════════════════════════════
    story.append(Paragraph("🌐  Presença Digital", s_secao))

    tem_site = dados_empresa.get("tem_website", False)
    url      = dados_empresa.get("website_url") or ""
    badge_txt = "✅  POSSUI WEBSITE" if tem_site else "🚫  SEM WEBSITE — OPORTUNIDADE!"
    badge_sty = s_badge_com if tem_site else s_badge_sem
    badge_bg  = colors.HexColor("#14532D") if tem_site else colors.HexColor("#450A0A")

    site_rows = [
        [Paragraph(badge_txt, badge_sty)],
        [Paragraph(url if tem_site else "Este negócio ainda não tem um site profissional na internet.", s_body)],
    ]
    site_tab = Table(site_rows, colWidths=[w])
    site_tab.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), badge_bg),
        ("BOX",           (0,0), (-1,-1), 1, VERMELHO if not tem_site else VERDE),
        ("TOPPADDING",    (0,0), (-1,-1), 12),
        ("BOTTOMPADDING", (0,0), (-1,-1), 12),
        ("LEFTPADDING",   (0,0), (-1,-1), 16),
        ("RIGHTPADDING",  (0,0), (-1,-1), 16),
        ("ALIGN",         (0,0), (-1,-1), "CENTER"),
    ]))
    story.append(site_tab)
    story.append(Spacer(1, 14))

    # ════════════════════════════════════════════════════════════
    # AVALIAÇÕES GOOGLE
    # ════════════════════════════════════════════════════════════
    story.append(Paragraph("⭐  Avaliações no Google", s_secao))

    av     = dados_empresa.get("avaliacao", 0)
    total  = dados_empresa.get("total_avaliacoes", 0)
    fotos  = dados_empresa.get("total_fotos", 0)

    estrelas = int(round(av))
    estrelas_str = "★" * estrelas + "☆" * (5 - estrelas)

    cor_av = VERDE if av >= 4.0 else (AMARELO if av >= 3.0 else VERMELHO)
    s_av_num = estilo("AvNum", fontSize=28, leading=34, textColor=cor_av, fontName="Helvetica-Bold", alignment=TA_CENTER)
    s_av_str = estilo("AvStr", fontSize=14, leading=18, textColor=AMARELO, fontName="Helvetica-Bold", alignment=TA_CENTER)
    s_av_tot = estilo("AvTot", fontSize=9,  leading=12, textColor=CINZA_MEDIO, fontName="Helvetica", alignment=TA_CENTER)

    av_col1 = [
        [Paragraph(f"{av:.1f}", s_av_num)],
        [Paragraph(estrelas_str, s_av_str)],
        [Paragraph(f"{total} avaliações", s_av_tot)],
    ]
    col1 = Table(av_col1, colWidths=[w * 0.33])
    col1.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), AZUL_MEDIO),
        ("TOPPADDING",    (0,0), (-1,-1), 8),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
        ("ALIGN",         (0,0), (-1,-1), "CENTER"),
    ]))

    # Distribuição de estrelas
    dist = dados_empresa.get("distribuicao_estrelas", {5: 0, 4: 0, 3: 0, 2: 0, 1: 0})
    s_star_label = estilo("StarL", fontSize=9, leading=12, textColor=AMARELO,     fontName="Helvetica-Bold")
    s_star_val   = estilo("StarV", fontSize=9, leading=12, textColor=CINZA_CLARO, fontName="Helvetica")

    dist_rows = [[Paragraph(f"{'★'*i}", s_star_label), Paragraph(str(dist.get(i, 0)), s_star_val)]
                 for i in range(5, 0, -1)]
    col2 = Table(dist_rows, colWidths=[w * 0.20, w * 0.15])
    col2.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), AZUL_MEDIO),
        ("TOPPADDING",    (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ("LEFTPADDING",   (0,0), (-1,-1), 14),
        ("RIGHTPADDING",  (0,0), (-1,-1), 8),
        ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
    ]))

    s_fotos_num = estilo("FotosN", fontSize=24, leading=30, textColor=AZUL_DESTAQUE, fontName="Helvetica-Bold", alignment=TA_CENTER)
    s_fotos_lbl = estilo("FotosL", fontSize=9,  leading=12, textColor=CINZA_MEDIO,   fontName="Helvetica",      alignment=TA_CENTER)
    col3_rows = [
        [Paragraph(str(fotos), s_fotos_num)],
        [Paragraph("fotos no\nGoogle", s_fotos_lbl)],
    ]
    col3 = Table(col3_rows, colWidths=[w * 0.32])
    col3.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), AZUL_MEDIO),
        ("TOPPADDING",    (0,0), (-1,-1), 8),
        ("BOTTOMPADDING", (0,0), (-1,-1), 8),
        ("ALIGN",         (0,0), (-1,-1), "CENTER"),
    ]))

    av_outer = Table([[col1, col2, col3]], colWidths=[w*0.33, w*0.35, w*0.32])
    av_outer.setStyle(TableStyle([
        ("BACKGROUND",  (0,0),(-1,-1), AZUL_MEDIO),
        ("BOX",         (0,0),(-1,-1), 0.5, AZUL_BORDA),
        ("INNERGRID",   (0,0),(-1,-1), 0.3, AZUL_BORDA),
        ("VALIGN",      (0,0),(-1,-1), "MIDDLE"),
        ("TOPPADDING",  (0,0),(-1,-1), 0),
        ("BOTTOMPADDING",(0,0),(-1,-1), 0),
        ("LEFTPADDING", (0,0),(-1,-1), 0),
        ("RIGHTPADDING",(0,0),(-1,-1), 0),
    ]))
    story.append(av_outer)
    story.append(Spacer(1, 14))

    # ════════════════════════════════════════════════════════════
    # SCORE DE PRESENÇA DIGITAL (calculado)
    # ════════════════════════════════════════════════════════════
    story.append(Paragraph("📊  Score de Presença Digital", s_secao))

    score = 0
    pontos = []

    if tem_site:
        score += 30
        pontos.append(("✅ Site profissional", "+30 pts", VERDE))
    else:
        pontos.append(("❌ Sem site profissional", "0 pts", VERMELHO))

    if av >= 4.0:
        score += 25
        pontos.append(("✅ Boa avaliação Google (≥ 4.0)", "+25 pts", VERDE))
    elif av >= 3.0:
        score += 15
        pontos.append(("⚠️  Avaliação razoável (3.0–3.9)", "+15 pts", AMARELO))
    else:
        pontos.append(("❌ Avaliação baixa (< 3.0)", "0 pts", VERMELHO))

    if total >= 50:
        score += 20
        pontos.append(("✅ Muitas avaliações (≥ 50)", "+20 pts", VERDE))
    elif total >= 10:
        score += 10
        pontos.append(("⚠️  Poucas avaliações (10–49)", "+10 pts", AMARELO))
    else:
        pontos.append(("❌ Muito poucas avaliações (< 10)", "0 pts", VERMELHO))

    if fotos >= 20:
        score += 15
        pontos.append(("✅ Muitas fotos no Google (≥ 20)", "+15 pts", VERDE))
    elif fotos >= 5:
        score += 8
        pontos.append(("⚠️  Poucas fotos (5–19)", "+8 pts", AMARELO))
    else:
        pontos.append(("❌ Quase sem fotos (< 5)", "0 pts", VERMELHO))

    if dados_empresa.get("telefone"):
        score += 10
        pontos.append(("✅ Telefone cadastrado", "+10 pts", VERDE))
    else:
        pontos.append(("❌ Sem telefone no Google", "0 pts", VERMELHO))

    cor_score = VERDE if score >= 70 else (AMARELO if score >= 40 else VERMELHO)
    s_score_n = estilo("ScN", fontSize=42, leading=50, textColor=cor_score, fontName="Helvetica-Bold", alignment=TA_CENTER)
    s_score_m = estilo("ScM", fontSize=13, leading=18, textColor=CINZA_MEDIO, fontName="Helvetica", alignment=TA_CENTER)
    s_score_c = estilo("ScC", fontSize=10, leading=14, textColor=CINZA_CLARO, fontName="Helvetica", alignment=TA_CENTER)

    classificacao = "FORTE" if score >= 70 else ("MÉDIO" if score >= 40 else "FRACO")
    cor_class = VERDE if score >= 70 else (AMARELO if score >= 40 else VERMELHO)
    s_class = estilo("Cls", fontSize=11, leading=16, textColor=cor_class, fontName="Helvetica-Bold", alignment=TA_CENTER)

    score_col = Table([
        [Paragraph(str(score), s_score_n)],
        [Paragraph("/ 100 pontos", s_score_m)],
        [Spacer(1, 4)],
        [Paragraph(classificacao, s_class)],
    ], colWidths=[w * 0.30])
    score_col.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), AZUL_MEDIO),
        ("TOPPADDING",    (0,0),(-1,-1), 8),
        ("BOTTOMPADDING", (0,0),(-1,-1), 8),
        ("ALIGN",         (0,0),(-1,-1), "CENTER"),
    ]))

    s_item_ok = estilo("IOk", fontSize=9, leading=13, textColor=CINZA_CLARO, fontName="Helvetica")
    s_pts      = estilo("Pts", fontSize=9, leading=13, textColor=CINZA_MEDIO, fontName="Helvetica", alignment=TA_RIGHT)
    pontos_rows = [[Paragraph(txt, s_item_ok), Paragraph(pts, s_pts)] for txt, pts, _ in pontos]
    pontos_tab = Table(pontos_rows, colWidths=[w * 0.47, w * 0.18])
    pontos_tab.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), AZUL_MEDIO),
        ("TOPPADDING",    (0,0),(-1,-1), 5),
        ("BOTTOMPADDING", (0,0),(-1,-1), 5),
        ("LEFTPADDING",   (0,0),(-1,-1), 12),
        ("RIGHTPADDING",  (0,0),(-1,-1), 12),
    ]))

    score_outer = Table([[score_col, pontos_tab]], colWidths=[w*0.30, w*0.70])
    score_outer.setStyle(TableStyle([
        ("BACKGROUND",  (0,0),(-1,-1), AZUL_MEDIO),
        ("BOX",         (0,0),(-1,-1), 0.5, AZUL_BORDA),
        ("INNERGRID",   (0,0),(-1,-1), 0.3, AZUL_BORDA),
        ("VALIGN",      (0,0),(-1,-1), "MIDDLE"),
        ("TOPPADDING",  (0,0),(-1,-1), 0),
        ("BOTTOMPADDING",(0,0),(-1,-1), 0),
        ("LEFTPADDING", (0,0),(-1,-1), 0),
        ("RIGHTPADDING",(0,0),(-1,-1), 0),
    ]))
    story.append(score_outer)
    story.append(Spacer(1, 16))

    # ════════════════════════════════════════════════════════════
    # O QUE ESTÁ FALTANDO (só se não tem site)
    # ════════════════════════════════════════════════════════════
    if not tem_site:
        story.append(Paragraph("💡  O que está faltando", s_secao))

        s_miss_title = estilo("MT", fontSize=10, leading=14, textColor=AMARELO, fontName="Helvetica-Bold")
        s_miss_desc  = estilo("MD", fontSize=9,  leading=13, textColor=CINZA_CLARO, fontName="Helvetica")

        itens_faltando = [
            ("🌐  Site Profissional",
             "Um site bem feito transmite credibilidade, aparece no Google e funciona como vendedor 24h por dia."),
            ("📅  Agendamento Online",
             "Clientes modernos preferem marcar pelo celular, sem precisar ligar. Você perde vendas sem isso."),
            ("📸  Galeria de Trabalhos",
             "Mostrar o seu trabalho online convence clientes antes mesmo de você falar com eles."),
            ("⭐  Gestão de Avaliações",
             "Pedir avaliações dos clientes satisfeitos aumenta sua reputação e aparência no Google Maps."),
        ]

        for titulo, desc in itens_faltando:
            r = Table([
                [Paragraph(titulo, s_miss_title)],
                [Paragraph(desc, s_miss_desc)],
            ], colWidths=[w - 24])
            r.setStyle(TableStyle([
                ("BACKGROUND",    (0,0),(-1,-1), colors.HexColor("#1C2A3A")),
                ("BOX",           (0,0),(-1,-1), 0.5, colors.HexColor("#F59E0B")),
                ("TOPPADDING",    (0,0),(-1,-1), 8),
                ("BOTTOMPADDING", (0,0),(-1,-1), 8),
                ("LEFTPADDING",   (0,0),(-1,-1), 14),
                ("RIGHTPADDING",  (0,0),(-1,-1), 14),
            ]))
            story.append(r)
            story.append(Spacer(1, 5))

        story.append(Spacer(1, 10))

    # ════════════════════════════════════════════════════════════
    # CALL TO ACTION
    # ════════════════════════════════════════════════════════════
    nome_serv = dados_empresa.get("seu_servico", "Criação de Sites Profissionais")
    nome_pros = dados_empresa.get("seu_nome", "ProspectLocal")
    wpp       = dados_empresa.get("seu_whatsapp", "")

    cta = Table([
        [Paragraph(f"🚀  Posso resolver isso para você!", s_cta_titulo)],
        [Spacer(1, 4)],
        [Paragraph(f"Ofereço o serviço de <b>{nome_serv}</b> para negócios como o seu.\n"
                   f"Site profissional, rápido, bonito e que aparece no Google — "
                   f"sem complicação, com resultado.", s_cta_body)],
        [Spacer(1, 8)],
        [Paragraph(f"📲  Fale comigo no WhatsApp:", s_cta_body)],
        [Paragraph(wpp, s_cta_contato)],
        [Spacer(1, 4)],
        [Paragraph(nome_pros, s_rodape)],
    ], colWidths=[w])
    cta.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), colors.HexColor("#0D2137")),
        ("BOX",           (0,0),(-1,-1), 1.5, AZUL_DESTAQUE),
        ("TOPPADDING",    (0,0),(-1,-1), 14),
        ("BOTTOMPADDING", (0,0),(-1,-1), 14),
        ("LEFTPADDING",   (0,0),(-1,-1), 20),
        ("RIGHTPADDING",  (0,0),(-1,-1), 20),
        ("ALIGN",         (0,0),(-1,-1), "CENTER"),
    ]))
    story.append(KeepTogether(cta))

    # ─── GERA ────────────────────────────────────────────────────
    doc.build(story)
    print(f"✅  PDF gerado: {caminho_saida}")
    return caminho_saida


# ─── DADOS DE EXEMPLO ────────────────────────────────────────────
if __name__ == "__main__":
    empresa_exemplo = {
        "nome":              "Barbearia do Zé Premium",
        "categoria":         "Barbearia",
        "telefone":          "+55 83 99999-1234",
        "endereco":          "Rua das Flores, 142 — Centro",
        "cidade":            "João Pessoa, PB",
        "tem_website":       False,
        "website_url":       None,
        "avaliacao":         4.2,
        "total_avaliacoes":  27,
        "total_fotos":       8,
        "distribuicao_estrelas": {5: 18, 4: 5, 3: 2, 2: 1, 1: 1},
        # seus dados
        "seu_nome":          "Alex Perin — ProspectLocal",
        "seu_whatsapp":      "(83) 9 9999-0000",
        "seu_servico":       "Criação de Sites Profissionais para Negócios Locais",
    }

    saida = "/sessions/brave-adoring-hypatia/diagnostico_exemplo.pdf"
    gerar_pdf(empresa_exemplo, saida)
