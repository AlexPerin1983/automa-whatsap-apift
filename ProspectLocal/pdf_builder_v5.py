import os
import re
from datetime import date

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader, simpleSplit
from reportlab.pdfgen import canvas as _cm


def _find_logo(base_dir, name):
    for folder in (os.path.join(base_dir, 'assets'), os.path.join(base_dir, '..', 'assets')):
        path = os.path.join(folder, name)
        if os.path.exists(path):
            return path
    return None


def build_diagnostic_pdf(d, output, ensure_logo_assets=None, draw_text_logo=None):
    if ensure_logo_assets:
        ensure_logo_assets()

    W, H = A4
    data_str = date.today().strftime('%d/%m/%Y')

    NAVY = colors.HexColor('#0F172A')
    NAVY_DEEP = colors.HexColor('#111C32')
    NAVY_SOFT = colors.HexColor('#EEF4FF')
    BLUE = colors.HexColor('#2D6BFF')
    CYAN = colors.HexColor('#8AB8FF')
    GOLD = colors.HexColor('#C19143')
    GOLD_SOFT = colors.HexColor('#F3E7D2')
    WHITE = colors.white
    PAPER = colors.HexColor('#FBFCFE')
    PAPER_ALT = colors.HexColor('#F4F7FB')
    CARD = colors.HexColor('#FFFFFF')
    INK = colors.HexColor('#17253E')
    MUTED = colors.HexColor('#6B7A90')
    GREEN = colors.HexColor('#16A34A')
    RED = colors.HexColor('#DC2626')
    ORANGE = colors.HexColor('#F97316')
    BORDER = colors.HexColor('#DCE5F0')
    SHADOW = colors.HexColor('#E7EDF5')
    TRACK = colors.HexColor('#E9EEF6')

    nome = str(d.get('nome') or 'Empresa')
    categoria = str(d.get('categoria') or 'Categoria nao informada')
    telefone = str(d.get('telefone') or 'Nao informado')
    endereco = str(d.get('endereco') or 'Endereco nao informado')
    cidade = str(d.get('cidade') or 'Cidade nao informada')
    tem_web = bool(d.get('tem_website'))
    web_url = str(d.get('website_url') or '').strip()
    avaliacao = float(d.get('avaliacao') or 0)
    n_rev = int(d.get('total_avaliacoes') or 0)
    n_fotos = int(d.get('total_fotos') or 0)
    dist = {}
    for k, v in (d.get('distribuicao_estrelas', {}) or {}).items():
        try:
            dist[int(k)] = int(v)
        except Exception:
            continue
    prosp = str(d.get('seu_nome') or 'OtimizaAI')
    wa_display = str(d.get('seu_whatsapp') or '').strip()
    wa_num = re.sub(r'\D', '', wa_display)
    if wa_num and not wa_num.startswith('55'):
        wa_num = f'55{wa_num}'

    sc_pres = min(
        100,
        (40 if tem_web else 0)
        + round(min(n_fotos / 20.0, 1) * 30)
        + (10 if categoria != 'Categoria nao informada' else 0)
        + (10 if endereco != 'Endereco nao informado' else 0)
        + (5 if telefone != 'Nao informado' else 0),
    )
    sc_rep = min(
        100,
        (round((avaliacao / 5.0) * 60) if avaliacao > 0 else 0)
        + round(min(n_rev / 100.0, 1) * 40),
    )
    sc_eng = min(100, round(min(n_fotos / 30.0, 1) * 50) + round(min(n_rev / 50.0, 1) * 50))
    sc_total = round(sc_pres * 0.40 + sc_rep * 0.35 + sc_eng * 0.25)
    pot_pres = min(100, sc_pres + (40 if not tem_web else 0) + (15 if n_fotos < 20 else 0))
    pot_rep = min(100, sc_rep + (10 if avaliacao < 4.5 else 0) + (15 if n_rev < 50 else 0))
    pot_eng = min(100, sc_eng + (20 if n_fotos < 30 else 0) + (15 if n_rev < 50 else 0))

    def sc_col(score):
        if score >= 70:
            return GREEN
        if score >= 40:
            return ORANGE
        return RED

    def sc_lbl(score):
        if score >= 70:
            return 'Bom'
        if score >= 40:
            return 'Regular'
        return 'Critico'

    def score_phrase(score):
        if score >= 75:
            return 'A empresa ja tem uma base digital consistente e pode focar em conversao.'
        if score >= 55:
            return 'Existe uma base relevante, mas ainda ha ajustes claros para captar mais contatos.'
        if score >= 35:
            return 'A presenca atual funciona, porem ainda esta abaixo do potencial comercial do negocio.'
        return 'A presenca digital esta fragil e ha espaco imediato para elevar confianca e visibilidade.'

    recs = []
    if not tem_web:
        recs.append(('ALTA', 'Criar um site profissional', 'Sem um site proprio, a empresa perde autoridade e deixa escapar clientes que pesquisam antes de contratar.'))
    if n_fotos < 5:
        recs.append(('ALTA', f'Ampliar a galeria do perfil ({n_fotos} fotos)', 'Mais fotos aumentam cliques, melhoram percepcao de qualidade e ajudam o cliente a confiar mais rapido.'))
    elif n_fotos < 15:
        recs.append(('MEDIA', f'Reforcar o acervo visual ({n_fotos} fotos)', 'Chegar a 20+ fotos deixa o perfil mais competitivo e mais persuasivo na busca local.'))
    if avaliacao > 0 and avaliacao < 4.0:
        recs.append(('ALTA', f'Elevar a nota media ({avaliacao:.1f})', 'Uma reputacao abaixo de 4 estrelas reduz conversao e cria inseguranca logo no primeiro contato.'))
    if n_rev < 10:
        recs.append(('MEDIA', f'Gerar mais avaliacoes ({n_rev})', 'Aumentar a prova social melhora a posicao no Google e fortalece a decisao de compra.'))
    elif n_rev < 30:
        recs.append(('BAIXA', f'Estruturar rotina de avaliacoes ({n_rev})', 'A empresa ja tem base, mas pode crescer mais rapido com um processo simples de pedido de feedback.'))
    neg = dist.get(1, 0) + dist.get(2, 0)
    if neg >= 3 and n_rev > 0 and (neg / n_rev) > 0.15:
        recs.append(('ALTA', f'Responder feedbacks negativos ({neg})', 'Responder comentarios publicamente transmite seriedade e ajuda a reduzir desgaste de reputacao.'))
    if not recs:
        recs.append(('BAIXA', 'Consolidar a operacao digital', 'O perfil esta em bom nivel. O proximo passo e escalar reputacao, visibilidade e conversao de forma previsivel.'))

    gaps = []
    if not tem_web:
        gaps.append('ausencia de site profissional')
    if n_fotos < 20:
        gaps.append('acervo visual abaixo do ideal')
    if n_rev < 30:
        gaps.append('volume de avaliacoes ainda baixo')
    if avaliacao and avaliacao < 4.5:
        gaps.append('nota de reputacao abaixo do ideal')
    main_gap = gaps[0] if gaps else 'conversao e recorrencia comercial'
    wa_text = 'Quero ver uma demonstracao do meu site'
    wa_link = f'https://wa.me/{wa_num}?text={wa_text.replace(" ", "%20")}' if wa_num else ''

    def normalize_url(url):
        url = (url or '').strip()
        if not url:
            return ''
        return url if url.startswith(('http://', 'https://')) else f'https://{url}'

    web_link = normalize_url(web_url)
    base_dir = os.path.dirname(os.path.abspath(__file__))
    logo_main = _find_logo(base_dir, 'logo_otimizaai.png')
    logo_hdr = _find_logo(base_dir, 'logo_otimizaai_header.png')
    logo_cta = _find_logo(base_dir, 'logo_otimizaai_cta.png')

    def rrect(c, x, y, w, h, r, fill=None, stroke=None, sw=0.5):
        c.saveState()
        p = c.beginPath()
        p.moveTo(x + r, y)
        p.lineTo(x + w - r, y)
        p.arcTo(x + w - r, y, x + w, y + r, -90, 90)
        p.lineTo(x + w, y + h - r)
        p.arcTo(x + w - r, y + h - r, x + w, y + h, 0, 90)
        p.lineTo(x + r, y + h)
        p.arcTo(x, y + h - r, x + r, y + h, 90, 90)
        p.lineTo(x, y + r)
        p.arcTo(x, y, x + r, y + r, 180, 90)
        p.close()
        if fill:
            c.setFillColor(fill)
        if stroke:
            c.setStrokeColor(stroke)
            c.setLineWidth(sw)
        c.drawPath(p, fill=1 if fill else 0, stroke=1 if stroke else 0)
        c.restoreState()

    def shadow(c, x, y, w, h, r, dx=1.5, dy=-1.5):
        rrect(c, x + dx, y + dy, w, h, r, fill=SHADOW)

    def pbar(c, x, y, w, h, pct, col):
        rrect(c, x, y, w, h, h / 2, fill=TRACK)
        if pct > 0:
            rrect(c, x, y, max(h, pct / 100.0 * w), h, h / 2, fill=col)

    def draw_wrapped(c, x, y, text, max_width, font_name, font_size, color, leading=None, max_lines=None, align='left'):
        lines = simpleSplit(str(text or ''), font_name, font_size, max_width)
        if max_lines and len(lines) > max_lines:
            lines = lines[:max_lines]
            tail = lines[-1].rstrip('. ')
            while tail and c.stringWidth(f'{tail}...', font_name, font_size) > max_width:
                tail = tail[:-1]
            lines[-1] = f'{tail.rstrip()}...'
        c.saveState()
        c.setFillColor(color)
        c.setFont(font_name, font_size)
        leading = leading or font_size * 1.3
        cy = y
        for line in lines:
            if align == 'center':
                c.drawCentredString(x, cy, line)
            elif align == 'right':
                c.drawRightString(x, cy, line)
            else:
                c.drawString(x, cy, line)
            cy -= leading
        c.restoreState()
        return cy

    def pill(c, x, y, w, h, text, fill, text_color=WHITE):
        rrect(c, x, y, w, h, h / 2, fill=fill)
        c.setFillColor(text_color)
        c.setFont('Helvetica-Bold', 6.9)
        c.drawCentredString(x + w / 2, y + h / 2 - 2.4, str(text).upper())

    def metric_card(c, x, y, w, h, label, value, note, accent=BLUE, dark=False, value_font=16, note_lines=1):
        shadow(c, x, y, w, h, 10)
        bg = CARD if not dark else NAVY_SOFT
        border = BORDER if not dark else colors.HexColor('#2E4E86')
        rrect(c, x, y, w, h, 10, fill=bg, stroke=border, sw=0.8)
        c.setFillColor(accent)
        c.rect(x + 12, y + h - 6, w - 24, 3.5, fill=1, stroke=0)
        c.setFillColor(MUTED if not dark else GOLD_SOFT)
        c.setFont('Helvetica-Bold', 6.9)
        c.drawString(x + 14, y + h - 17, label.upper())
        c.setFillColor(INK if not dark else WHITE)
        c.setFont('Helvetica-Bold', value_font)
        c.drawString(x + 14, y + h - max(35, value_font + 19), str(value))
        draw_wrapped(
            c,
            x + 14,
            y + 10,
            note,
            w - 28,
            'Helvetica',
            6.7,
            MUTED if not dark else colors.HexColor('#D8E3FF'),
            leading=8.1,
            max_lines=note_lines,
        )

    def detail_box(c, x, y, w, h, label, value):
        rrect(c, x, y, w, h, 8, fill=colors.HexColor('#F7F9FC'))
        c.setFillColor(CYAN)
        c.rect(x + 8, y + 8, 3, h - 16, fill=1, stroke=0)
        c.setFillColor(MUTED)
        c.setFont('Helvetica-Bold', 6.7)
        c.drawString(x + 16, y + h - 12, label.upper())
        draw_wrapped(c, x + 16, y + h - 24, value, w - 24, 'Helvetica-Bold', 8.2, INK, leading=8.8, max_lines=2)

    def section_label(c, x1, x2, y, title, subtitle=''):
        c.setFillColor(GOLD)
        c.rect(x1, y + 3.5, 14, 1.6, fill=1, stroke=0)
        c.setFillColor(INK)
        c.setFont('Helvetica-Bold', 10.2)
        c.drawString(x1, y, title.upper())
        if subtitle:
            c.setFillColor(MUTED)
            c.setFont('Helvetica', 7.2)
            c.drawRightString(x2, y, subtitle)
        c.setStrokeColor(CYAN)
        c.setLineWidth(0.9)
        c.line(x1, y - 4, x2, y - 4)
        return y - 18

    def page_header(c, x1, x2, width, page_no, title, subtitle):
        c.setFillColor(PAPER)
        c.rect(0, 0, W, H, fill=1, stroke=0)
        hh = 22 * mm
        hy = H - 24 * mm - hh
        shadow(c, x1, hy, width, hh, 14)
        rrect(c, x1, hy, width, hh, 14, fill=CARD, stroke=BORDER, sw=0.8)
        c.setFillColor(NAVY)
        c.rect(x1, hy + hh - 5, width, 5, fill=1, stroke=0)
        rrect(c, x1 + 10, hy + 7, 52, hh - 14, 6, fill=NAVY_DEEP)
        if logo_hdr:
            try:
                c.drawImage(ImageReader(logo_hdr), x1 + 13, hy + 10, 46, hh - 20, preserveAspectRatio=True, mask='auto')
            except Exception:
                c.setFillColor(NAVY)
                c.setFont('Helvetica-Bold', 11)
                c.drawString(x1 + 18, hy + hh / 2 - 4, 'OtimizaAI')
        else:
            c.setFillColor(NAVY)
            c.setFont('Helvetica-Bold', 11)
            c.drawString(x1 + 18, hy + hh / 2 - 4, 'OtimizaAI')
        c.setFillColor(INK)
        c.setFont('Helvetica-Bold', 13.4)
        c.drawString(x1 + 70, hy + hh - 19, title)
        c.setFillColor(MUTED)
        c.setFont('Helvetica', 7.5)
        c.drawString(x1 + 70, hy + 9, subtitle)
        pill(c, x2 - 19, hy + 7.5, 19, hh - 15, f'{page_no:02d}', NAVY)
        return hy - 16

    def page_footer(c, x1, x2, page_no):
        c.setStrokeColor(BORDER)
        c.setLineWidth(0.6)
        c.line(x1, 14 * mm, x2, 14 * mm)
        c.setFillColor(MUTED)
        c.setFont('Helvetica', 6.6)
        c.drawString(x1, 10 * mm, f'Preparado por {prosp}')
        c.drawRightString(x2, 10 * mm, f'Pagina {page_no}  |  {data_str}')

    def category_card(c, x, y, w, h, title, current, potential):
        accent = sc_col(current)
        shadow(c, x, y, w, h, 12)
        rrect(c, x, y, w, h, 12, fill=CARD, stroke=BORDER, sw=0.8)
        c.setFillColor(accent)
        c.rect(x + 10, y + h - 6, w - 20, 4, fill=1, stroke=0)
        delta = max(0, potential - current)
        if delta:
            pill(c, x + w - 42, y + h - 24, 28, 12, f'+{delta}', accent)
        scx = x + w / 2
        scy = y + h - 34
        c.setStrokeColor(accent)
        c.setLineWidth(2.2)
        c.circle(scx, scy, 20, fill=0, stroke=1)
        c.setFillColor(CARD)
        c.circle(scx, scy, 16, fill=1, stroke=0)
        c.setFillColor(accent)
        c.setFont('Helvetica-Bold', 14)
        c.drawCentredString(scx, scy - 5, str(current))
        draw_wrapped(c, scx, y + h - 62, title, w - 26, 'Helvetica-Bold', 8.1, INK, leading=10, max_lines=2, align='center')
        pill(c, x + w / 2 - 20, y + h - 86, 40, 13, sc_lbl(current), accent)
        c.setFillColor(MUTED)
        c.setFont('Helvetica', 6.7)
        c.drawString(x + 14, y + 30, 'Atual')
        c.drawRightString(x + w - 14, y + 30, str(current))
        pbar(c, x + 14, y + 21, w - 28, 6, current, accent)
        c.drawString(x + 14, y + 13, 'Potencial')
        c.drawRightString(x + w - 14, y + 13, str(potential))
        pbar(c, x + 14, y + 4, w - 28, 6, potential, BLUE)

    def signal_row(c, x, y, w, h, label, value, accent=BLUE, fill=PAPER_ALT, value_color=INK, value_size=8.1, max_lines=2):
        rrect(c, x, y, w, h, 8, fill=fill)
        c.setFillColor(accent)
        c.rect(x + 10, y + 8, 4, h - 16, fill=1, stroke=0)
        c.setFillColor(MUTED if fill != NAVY else colors.HexColor('#BED0F0'))
        c.setFont('Helvetica-Bold', 6.6)
        c.drawString(x + 20, y + h - 12, label.upper())
        draw_wrapped(c, x + 20, y + h - 23, value, w - 30, 'Helvetica-Bold', value_size, value_color, leading=value_size * 1.12, max_lines=max_lines)

    def priority_card(c, x, y, w, h, idx, prio, title, desc):
        prio_colors = {'ALTA': RED, 'MEDIA': ORANGE, 'BAIXA': CYAN}
        prio_bg = {
            'ALTA': colors.HexColor('#FFF5F5'),
            'MEDIA': colors.HexColor('#FFF8ED'),
            'BAIXA': colors.HexColor('#F0F9FF'),
        }
        accent = prio_colors.get(prio, BLUE)
        shadow(c, x, y, w, h, 10)
        rrect(c, x, y, w, h, 10, fill=prio_bg.get(prio, CARD), stroke=BORDER, sw=0.7)
        c.setFillColor(accent)
        c.rect(x + 10, y + h - 5, w - 20, 3, fill=1, stroke=0)
        pill(c, x + 12, y + h - 22, 34, 14, prio, accent)
        c.setFillColor(accent)
        c.setFont('Helvetica-Bold', 10.5)
        c.drawRightString(x + w - 12, y + h - 14, f'{idx:02d}')
        c.setFillColor(INK)
        c.setFont('Helvetica-Bold', 8.8)
        title_bottom = draw_wrapped(c, x + 12, y + h - 34, title, w - 24, 'Helvetica-Bold', 8.8, INK, leading=10, max_lines=2)
        draw_wrapped(c, x + 12, title_bottom - 3, desc, w - 24, 'Helvetica', 7.5, MUTED, leading=9.2, max_lines=3)

    def roadmap_card(c, x, y, w, h, step, title, desc, result, accent=BLUE):
        shadow(c, x, y, w, h, 12)
        rrect(c, x, y, w, h, 12, fill=CARD, stroke=BORDER, sw=0.8)
        pill(c, x + 12, y + h - 22, 28, 13, step, NAVY)
        c.setFillColor(accent)
        c.rect(x + 12, y + h - 34, w - 24, 3, fill=1, stroke=0)
        c.setFillColor(INK)
        c.setFont('Helvetica-Bold', 9.2)
        title_bottom = draw_wrapped(c, x + 12, y + h - 46, title, w - 24, 'Helvetica-Bold', 9.2, INK, leading=10.5, max_lines=2)
        draw_wrapped(c, x + 12, title_bottom - 3, desc, w - 24, 'Helvetica', 7.5, MUTED, leading=9.2, max_lines=3)
        signal_row(c, x + 12, y + 12, w - 24, 24, 'Resultado esperado', result, accent=accent, fill=PAPER_ALT, value_color=INK, value_size=7.4, max_lines=2)

    def trunc(text, limit):
        text = str(text or '').strip()
        if len(text) <= limit:
            return text
        return f'{text[:limit - 3].rstrip()}...'

    LM = 18 * mm
    RM = W - 18 * mm
    CW = RM - LM

    c = _cm.Canvas(output, pagesize=A4)
    c.setTitle(f'Diagnostico Digital - {nome[:60]}')
    c.setAuthor(prosp)

    strengths = []
    if tem_web:
        strengths.append('Ja existe um ponto proprio de conversao para receber demanda.')
    if avaliacao >= 4.5 and n_rev >= 10:
        strengths.append('A reputacao local passa confianca logo no primeiro contato.')
    if n_fotos >= 20:
        strengths.append('O volume de fotos ajuda a valorizar a percepcao do negocio.')
    if n_rev >= 30:
        strengths.append('A prova social ja comeca a reduzir objecoes comerciais.')
    if not strengths:
        strengths.append('Existe um bom espaco para evoluir rapido com ajustes simples.')

    opportunities = []
    if not tem_web:
        opportunities.append('Criar um site ou pagina de alta conversao para capturar demanda fora do Google.')
    if n_fotos < 20:
        opportunities.append('Ampliar o acervo visual para reforcar autoridade e cliques no perfil.')
    if n_rev < 30:
        opportunities.append('Estruturar uma rotina de pedido de avaliacao para ganhar prova social.')
    if avaliacao and avaliacao < 4.5:
        opportunities.append('Tratar reputacao e respostas publicas para proteger a conversao.')
    if not opportunities:
        opportunities.append('Focar o proximo ciclo em conversao, velocidade de resposta e recorrencia.')

    potential_total = round(pot_pres * 0.40 + pot_rep * 0.35 + pot_eng * 0.25)
    score_gain = max(0, potential_total - sc_total)
    stars_filled = max(0, min(5, int(round(avaliacao))))
    stars_visual = ('*' * stars_filled) + ('-' * (5 - stars_filled)) if avaliacao else 'Sem nota'
    negative_share = round((neg / n_rev) * 100) if n_rev else 0

    c.setFillColor(PAPER)
    c.rect(0, 0, W, H, fill=1, stroke=0)
    c.setFillColor(NAVY)
    c.rect(0, H - 23 * mm, W, 23 * mm, fill=1, stroke=0)
    c.setFillColor(BLUE)
    c.rect(0, H - 23 * mm, W, 3 * mm, fill=1, stroke=0)
    c.setFillColor(colors.HexColor('#EAF2FF'))
    c.circle(RM + 14, H - 58 * mm, 34, fill=1, stroke=0)
    c.setFillColor(colors.HexColor('#F3F7FF'))
    c.circle(RM - 10, H - 124 * mm, 52, fill=1, stroke=0)

    meta_y = 18 * mm
    meta_h = 24 * mm
    summary_w = 74 * mm
    summary_h = 166 * mm
    summary_x = RM - summary_w
    summary_y = meta_y + meta_h + 14
    hero_w = summary_x - LM - 9 * mm

    if logo_main:
        try:
            c.drawImage(ImageReader(logo_main), LM, H - 35 * mm, 112, 34, preserveAspectRatio=True, mask='auto')
        except Exception:
            c.setFillColor(NAVY)
            c.setFont('Helvetica-Bold', 22)
            c.drawString(LM, H - 26 * mm, 'OtimizaAI')
    else:
        c.setFillColor(NAVY)
        c.setFont('Helvetica-Bold', 22)
        c.drawString(LM, H - 26 * mm, 'OtimizaAI')

    pill(c, LM, H - 48 * mm, 42 * mm, 6.5 * mm, 'ANALISE CONSULTIVA', NAVY)
    hero_y = draw_wrapped(c, LM, H - 64 * mm, 'Diagnostico digital com leitura executiva', hero_w, 'Helvetica-Bold', 23.5, INK, leading=25.5, max_lines=3)
    hero_y = draw_wrapped(c, LM, hero_y - 6, 'Uma leitura organizada da presenca online, da reputacao local e do potencial comercial da empresa.', hero_w - 10, 'Helvetica', 10.7, MUTED, leading=13.8, max_lines=3)
    c.setFillColor(GOLD)
    c.rect(LM, hero_y - 2, 28 * mm, 1.6, fill=1, stroke=0)

    chip_y = hero_y - 6
    pill(c, LM, chip_y - 2, 30 * mm, 6 * mm, trunc(categoria, 18), colors.HexColor('#EEF3FB'), INK)
    pill(c, LM + 32 * mm, chip_y - 2, 28 * mm, 6 * mm, trunc(cidade, 16), colors.HexColor('#EEF3FB'), INK)
    pill(c, LM + 62 * mm, chip_y - 2, 22 * mm, 6 * mm, data_str, CARD, BLUE)

    company_h = 32 * mm
    company_y = chip_y - 11 * mm - company_h
    shadow(c, LM, company_y, hero_w, company_h, 14)
    rrect(c, LM, company_y, hero_w, company_h, 14, fill=CARD, stroke=BORDER, sw=0.8)
    c.setFillColor(GOLD)
    c.rect(LM, company_y + company_h - 6, hero_w, 6, fill=1, stroke=0)
    c.setFillColor(MUTED)
    c.setFont('Helvetica-Bold', 7.2)
    c.drawString(LM + 14, company_y + company_h - 18, 'EMPRESA ANALISADA')
    draw_wrapped(c, LM + 14, company_y + company_h - 34, nome, hero_w - 28, 'Helvetica-Bold', 13.5, INK, leading=15.5, max_lines=2)
    c.setFillColor(MUTED)
    c.setFont('Helvetica', 8)
    c.drawString(LM + 14, company_y + 10, f'{categoria}  |  {cidade}')

    gap_h = 24 * mm
    gap_y = company_y - 6 * mm - gap_h
    shadow(c, LM, gap_y, hero_w, gap_h, 12)
    rrect(c, LM, gap_y, hero_w, gap_h, 12, fill=colors.HexColor('#EEF5FF'), stroke=colors.HexColor('#CFE0FF'), sw=0.8)
    pill(c, LM + 14, gap_y + gap_h - 19, 34 * mm, 5.5 * mm, 'PRINCIPAL ALAVANCA', BLUE)
    c.setFillColor(INK)
    c.setFont('Helvetica-Bold', 10.2)
    draw_wrapped(c, LM + 14, gap_y + gap_h - 31, main_gap.capitalize(), hero_w - 28, 'Helvetica-Bold', 10.2, INK, leading=11.5, max_lines=2)
    draw_wrapped(c, LM + 14, gap_y + 10, opportunities[0], hero_w - 28, 'Helvetica', 7.7, MUTED, leading=9.4, max_lines=2)

    stat_gap = 6
    stat_w = (hero_w - stat_gap * 2) / 3
    stat_h = 18 * mm
    stat_y = gap_y - 6 * mm - stat_h
    metric_card(c, LM, stat_y, stat_w, stat_h, 'Score atual', f'{sc_total}/100', 'Leitura executiva atual', accent=sc_col(sc_total), value_font=15)
    metric_card(c, LM + stat_w + stat_gap, stat_y, stat_w, stat_h, 'Avaliacoes', str(n_rev), 'Volume de prova social', accent=CYAN, value_font=15)
    metric_card(c, LM + (stat_w + stat_gap) * 2, stat_y, stat_w, stat_h, 'Fotos', str(n_fotos), 'Percepcao visual do perfil', accent=GOLD, value_font=15)

    c.setFillColor(MUTED)
    c.setFont('Helvetica-Bold', 7.2)
    c.drawString(LM, stat_y - 18, 'ESCOPO DO DIAGNOSTICO')
    draw_wrapped(c, LM, stat_y - 31, 'Perfil do Google, presenca web, reputacao percebida e sinais de capacidade atual para transformar busca local em contato comercial.', hero_w - 8, 'Helvetica', 8.7, MUTED, leading=11, max_lines=4)

    shadow(c, summary_x, summary_y, summary_w, summary_h, 16)
    rrect(c, summary_x, summary_y, summary_w, summary_h, 16, fill=NAVY, stroke=colors.HexColor('#1D3A6B'), sw=0.9)
    c.setFillColor(GOLD)
    c.rect(summary_x, summary_y + summary_h - 6, summary_w, 6, fill=1, stroke=0)
    c.setFillColor(WHITE)
    c.setFont('Helvetica-Bold', 12.5)
    c.drawString(summary_x + 16, summary_y + summary_h - 24, 'Resumo executivo')
    if score_gain:
        pill(c, summary_x + summary_w - 62, summary_y + summary_h - 28, 46, 15, f'+{score_gain} pts', GREEN)
    c.setFillColor(WHITE)
    c.setFont('Helvetica-Bold', 34)
    c.drawString(summary_x + 16, summary_y + summary_h - 62, str(sc_total))
    c.setFillColor(colors.HexColor('#D8E3FF'))
    c.setFont('Helvetica', 10)
    c.drawString(summary_x + 50, summary_y + summary_h - 56, '/ 100')
    pill(c, summary_x + 16, summary_y + summary_h - 82, 44, 14, sc_lbl(sc_total), sc_col(sc_total))
    draw_wrapped(c, summary_x + 16, summary_y + summary_h - 100, score_phrase(sc_total), summary_w - 32, 'Helvetica', 8.4, colors.HexColor('#D8E3FF'), leading=10.5, max_lines=3)

    bar_y = summary_y + summary_h - 132
    for label, score, col in (('Presenca online', sc_pres, CYAN), ('Reputacao local', sc_rep, GOLD_SOFT), ('Engajamento', sc_eng, GREEN)):
        c.setFillColor(colors.HexColor('#D8E3FF'))
        c.setFont('Helvetica-Bold', 7.1)
        c.drawString(summary_x + 16, bar_y, label)
        c.drawRightString(summary_x + summary_w - 16, bar_y, str(score))
        pbar(c, summary_x + 16, bar_y - 10, summary_w - 32, 7, score, col)
        bar_y -= 22

    signal_top = summary_y + 26
    signal_row(c, summary_x + 16, signal_top + 26, summary_w - 32, 24, 'Website', 'Ativo e pronto para conversao' if tem_web else 'Ausente e com alto impacto comercial', accent=GREEN if tem_web else RED, fill=colors.HexColor('#162A47'), value_color=WHITE, value_size=7.3)
    signal_row(c, summary_x + 16, signal_top, summary_w - 32, 24, 'Maior gap', main_gap.capitalize(), accent=CYAN, fill=colors.HexColor('#162A47'), value_color=WHITE, value_size=7.4)
    c.setFillColor(colors.HexColor('#BED0F0'))
    c.setFont('Helvetica', 7)
    c.drawString(summary_x + 16, summary_y + 12, f'Potencial estimado: {potential_total}/100')

    shadow(c, LM, meta_y, CW, meta_h, 12)
    rrect(c, LM, meta_y, CW, meta_h, 12, fill=CARD, stroke=BORDER, sw=0.8)
    cols = [('Empresa', trunc(nome, 24)), ('Nicho', trunc(categoria, 20)), ('Local', trunc(cidade, 20)), ('Potencial', f'{sc_total} para {potential_total}')]
    col_w = CW / 4
    for i, (label, value) in enumerate(cols):
        x0 = LM + i * col_w
        if i:
            c.setStrokeColor(BORDER)
            c.setLineWidth(0.8)
            c.line(x0, meta_y + 10, x0, meta_y + meta_h - 10)
        c.setFillColor(MUTED)
        c.setFont('Helvetica-Bold', 6.8)
        c.drawString(x0 + 12, meta_y + meta_h - 18, label.upper())
        c.setFillColor(INK)
        c.setFont('Helvetica-Bold', 8.3)
        draw_wrapped(c, x0 + 12, meta_y + meta_h - 31, value, col_w - 24, 'Helvetica-Bold', 8.3, INK, leading=10, max_lines=2)
    c.setFillColor(MUTED)
    c.setFont('Helvetica', 6.7)
    c.drawCentredString(W / 2, 10, f'Preparado por {prosp}  |  Documento comercial consultivo')

    c.showPage()
    y = page_header(c, LM, RM, CW, 2, 'Diagnostico da presenca digital', 'Leitura estruturada do contexto atual')
    summary_card_w = (CW - 18) / 4
    summary_card_h = 48
    summary_cards = [
        ('Website', 'Ativo' if tem_web else 'Ausente', trunc(web_url, 24) if tem_web and web_url else 'Maior alavanca do diagnostico', GREEN if tem_web else RED),
        ('Nota media', f'{avaliacao:.1f}' if avaliacao else '--', stars_visual, sc_col(round(avaliacao * 20)) if avaliacao else ORANGE),
        ('Avaliacoes', str(n_rev), 'Volume de prova social', CYAN),
        ('Fotos', str(n_fotos), 'Competitividade visual', GOLD),
    ]
    website_rect = None
    for idx, (label, value, note, accent) in enumerate(summary_cards):
        cx = LM + idx * (summary_card_w + 6)
        metric_card(c, cx, y - summary_card_h, summary_card_w, summary_card_h, label, value, note, accent=accent, value_font=14)
        if idx == 0 and web_link:
            website_rect = (cx, y - summary_card_h, cx + summary_card_w, y)
    if website_rect:
        c.linkURL(web_link, website_rect, relative=0, thickness=0)
    y -= summary_card_h + 18

    y = section_label(c, LM, RM, y, 'Diagnostico atual', 'Empresa e sinais principais')
    col_gap = 8
    left_w = (CW - col_gap) / 2
    right_w = left_w
    left_x = LM
    right_x = LM + left_w + col_gap
    top_h = 108
    top_y = y - top_h

    shadow(c, left_x, top_y, left_w, top_h, 12)
    rrect(c, left_x, top_y, left_w, top_h, 12, fill=CARD, stroke=BORDER, sw=0.8)
    c.setFillColor(INK)
    c.setFont('Helvetica-Bold', 12.5)
    draw_wrapped(c, left_x + 16, top_y + top_h - 20, nome, left_w - 32, 'Helvetica-Bold', 12.5, INK, leading=14, max_lines=2)
    c.setFillColor(MUTED)
    c.setFont('Helvetica', 8)
    c.drawString(left_x + 16, top_y + top_h - 40, f'{categoria}  |  {cidade}')
    c.setStrokeColor(BORDER)
    c.setLineWidth(0.7)
    c.line(left_x + 16, top_y + top_h - 48, left_x + left_w - 16, top_y + top_h - 48)
    detail_w = (left_w - 42) / 2
    detail_box(c, left_x + 16, top_y + 46, detail_w, 28, 'Telefone', telefone)
    detail_box(c, left_x + 26 + detail_w, top_y + 46, detail_w, 28, 'Website', web_url if tem_web and web_url else 'Nao possui website')
    detail_box(c, left_x + 16, top_y + 12, left_w - 32, 30, 'Endereco', endereco)

    shadow(c, right_x, top_y, right_w, top_h, 12)
    rrect(c, right_x, top_y, right_w, top_h, 12, fill=CARD, stroke=BORDER, sw=0.8)
    c.setFillColor(INK)
    c.setFont('Helvetica-Bold', 10.8)
    c.drawString(right_x + 14, top_y + top_h - 18, 'Reputacao no Google')
    c.setFillColor(MUTED)
    c.setFont('Helvetica', 7.6)
    c.drawString(right_x + 14, top_y + top_h - 31, 'Como a empresa aparece para quem esta pesquisando agora')
    c.setFillColor(sc_col(round(avaliacao * 20)) if avaliacao else ORANGE)
    c.setFont('Helvetica-Bold', 26)
    c.drawString(right_x + 14, top_y + top_h - 58, f'{avaliacao:.1f}' if avaliacao else '--')
    c.setFillColor(MUTED)
    c.setFont('Helvetica', 8)
    c.drawString(right_x + 52, top_y + top_h - 52, f'/ 5.0  |  {n_rev} avaliacoes')
    c.setFillColor(INK)
    c.setFont('Helvetica-Bold', 8.5)
    c.drawString(right_x + 14, top_y + top_h - 76, stars_visual)
    signal_row(c, right_x + 14, top_y + 42, right_w - 28, 24, 'Sinal comercial', 'Perfil com boa base' if sc_rep >= 70 else 'Confianca moderada' if sc_rep >= 40 else 'Confianca fragil', accent=sc_col(sc_rep), value_size=7.3)
    feedback_msg = f'{neg} avaliacoes baixas ({negative_share}%)' if neg else 'Sem concentracao relevante de notas baixas'
    signal_row(c, right_x + 14, top_y + 14, right_w - 28, 24, 'Feedbacks criticos', feedback_msg, accent=RED if neg else GREEN, value_size=7.2)

    consult_h = 104
    consult_y = top_y - 14 - consult_h
    shadow(c, LM, consult_y, CW, consult_h, 12)
    rrect(c, LM, consult_y, CW, consult_h, 12, fill=NAVY, stroke=colors.HexColor('#1F4180'), sw=0.8)
    c.setFillColor(CYAN)
    c.rect(LM, consult_y + consult_h - 5, CW, 5, fill=1, stroke=0)
    c.setFillColor(WHITE)
    c.setFont('Helvetica-Bold', 11)
    c.drawString(LM + 16, consult_y + consult_h - 18, 'Leitura consultiva')
    draw_wrapped(c, LM + 16, consult_y + consult_h - 34, score_phrase(sc_total), CW - 32, 'Helvetica', 8.4, colors.HexColor('#D8E3FF'), leading=10.5, max_lines=3)
    half_w = (CW - 42) / 2
    c.setFillColor(colors.HexColor('#BED0F0'))
    c.setFont('Helvetica-Bold', 7)
    c.drawString(LM + 16, consult_y + 38, 'FORCAS IDENTIFICADAS')
    draw_wrapped(c, LM + 16, consult_y + 26, f'1. {strengths[0]}', half_w, 'Helvetica', 7.5, WHITE, leading=9.2, max_lines=2)
    draw_wrapped(c, LM + 16, consult_y + 10, f'2. {strengths[1] if len(strengths) > 1 else strengths[0]}', half_w, 'Helvetica', 7.5, WHITE, leading=9.2, max_lines=2)
    signal_row(c, LM + 26 + half_w, consult_y + 28, half_w, 32, 'Principal alavanca', main_gap.capitalize(), accent=sc_col(sc_total), fill=colors.HexColor('#162A47'), value_color=WHITE, value_size=7.5)
    draw_wrapped(c, LM + 26 + half_w, consult_y + 14, opportunities[0], half_w, 'Helvetica', 7.2, colors.HexColor('#D8E3FF'), leading=8.8, max_lines=2)
    page_footer(c, LM, RM, 2)

    c.showPage()
    y = page_header(c, LM, RM, CW, 3, 'Analise de desempenho', 'Pontuacao, potencial e prioridades')
    y = section_label(c, LM, RM, y, 'Pontuacao por categoria', 'Atual e potencial')
    cat_w = (CW - 14) / 3
    cat_h = 122
    category_card(c, LM, y - cat_h, cat_w, cat_h, 'Presenca online', sc_pres, pot_pres)
    category_card(c, LM + cat_w + 7, y - cat_h, cat_w, cat_h, 'Reputacao local', sc_rep, pot_rep)
    category_card(c, LM + (cat_w + 7) * 2, y - cat_h, cat_w, cat_h, 'Engajamento', sc_eng, pot_eng)
    y -= cat_h + 18

    y = section_label(c, LM, RM, y, 'Cenario potencial', 'Atual x potencial')
    chart_h = 182
    chart_y = y - chart_h
    shadow(c, LM, chart_y, CW, chart_h, 12)
    rrect(c, LM, chart_y, CW, chart_h, 12, fill=CARD, stroke=BORDER, sw=0.8)
    c.setFillColor(INK)
    c.setFont('Helvetica-Bold', 10.2)
    c.drawString(LM + 16, chart_y + chart_h - 20, 'Onde a empresa pode chegar com uma estrutura mais profissional')
    c.setFillColor(MUTED)
    c.setFont('Helvetica', 7.8)
    c.drawString(LM + 16, chart_y + chart_h - 33, 'A estimativa considera presenca web, reputacao local e melhoria de sinais de confianca.')
    pill(c, RM - 95, chart_y + chart_h - 28, 28, 14, str(sc_total), sc_col(sc_total))
    pill(c, RM - 62, chart_y + chart_h - 28, 28, 14, str(potential_total), GREEN if potential_total >= 70 else BLUE)
    if score_gain:
        pill(c, RM - 28, chart_y + chart_h - 28, 22, 14, f'+{score_gain}', BLUE)

    gx = LM + 36
    gy = chart_y + 34
    gw = CW - 56
    gh = 102
    for i in range(5):
        gy_line = gy + (i / 4.0) * gh
        c.setStrokeColor(colors.HexColor('#ECF0F7'))
        c.setLineWidth(0.5)
        c.line(gx, gy_line, gx + gw, gy_line)
        c.setFillColor(MUTED)
        c.setFont('Helvetica', 6.4)
        c.drawRightString(gx - 4, gy_line - 2, str(i * 25))
    c.setFillColor(BLUE)
    c.rect(gx + gw - 108, chart_y + chart_h - 32, 12, 8, fill=1, stroke=0)
    c.setFillColor(INK)
    c.setFont('Helvetica', 7)
    c.drawString(gx + gw - 92, chart_y + chart_h - 30, 'Atual')
    c.setFillColor(GOLD)
    c.rect(gx + gw - 54, chart_y + chart_h - 32, 12, 8, fill=1, stroke=0)
    c.setFillColor(INK)
    c.drawString(gx + gw - 38, chart_y + chart_h - 30, 'Potencial')

    grp_w = gw / 3
    bw = grp_w * 0.22
    for i, (label, cur, pot) in enumerate((('Presenca\nonline', sc_pres, pot_pres), ('Reputacao', sc_rep, pot_rep), ('Engajamento', sc_eng, pot_eng))):
        bx = gx + i * grp_w + grp_w * 0.2
        cur_h = max(3, (cur / 100.0) * gh)
        pot_h = max(3, (pot / 100.0) * gh)
        rrect(c, bx, gy, bw, cur_h, 3, fill=BLUE)
        rrect(c, bx + bw + 5, gy, bw, pot_h, 3, fill=GOLD)
        c.setFillColor(BLUE if cur_h < 16 else WHITE)
        c.setFont('Helvetica-Bold', 7)
        c.drawCentredString(bx + bw / 2, gy + (cur_h + 3 if cur_h < 16 else cur_h - 9), str(cur))
        c.setFillColor(INK)
        c.drawCentredString(bx + bw + 5 + bw / 2, gy + pot_h + 4, str(pot))
        delta = max(0, pot - cur)
        if delta:
            c.setFillColor(GREEN)
            c.setFont('Helvetica-Bold', 7.1)
            c.drawString(bx + bw * 2 + 12, gy + max(cur_h, pot_h) - 2, f'+{delta}')
        for li, line in enumerate(label.split('\n')):
            c.setFillColor(INK)
            c.setFont('Helvetica', 7.1)
            c.drawCentredString(bx + bw + 2, gy - 11 - li * 9, line)

    signal_row(c, LM + 16, chart_y + 12, 48 * mm, 24, 'Maior ganho esperado', f'{score_gain} pontos no score geral' if score_gain else 'Consolidacao de performance', accent=GREEN if score_gain else BLUE, value_size=7.4)
    signal_row(c, LM + 67 * mm, chart_y + 12, 46 * mm, 24, 'Prioridade central', trunc(recs[0][1], 32), accent=sc_col(sc_total), value_size=7.4)
    signal_row(c, RM - 50 * mm, chart_y + 12, 46 * mm, 24, 'Objetivo', 'Mais confianca e mais contato comercial', accent=CYAN, value_size=7.4)
    y = chart_y - 18

    y = section_label(c, LM, RM, y, 'Prioridades recomendadas', 'Impacto e velocidade')
    priorities = recs[:3]
    prio_count = len(priorities)
    if prio_count == 1:
        prio_w = CW * 0.62
        prio_gap = 0
        start_x = LM + (CW - prio_w) / 2
    elif prio_count == 2:
        prio_gap = 10
        prio_w = (CW - prio_gap) / 2
        start_x = LM
    else:
        prio_gap = 8
        prio_w = (CW - prio_gap * 2) / 3
        start_x = LM
    prio_h = 84
    for idx, (prio, title, desc) in enumerate(priorities, start=1):
        px = start_x + (idx - 1) * (prio_w + prio_gap)
        priority_card(c, px, y - prio_h, prio_w, prio_h, idx, prio, title, desc)
    page_footer(c, LM, RM, 3)

    c.showPage()
    y = page_header(c, LM, RM, CW, 4, 'Plano de acao sugerido', 'Roteiro pratico e proximo passo recomendado')
    y = section_label(c, LM, RM, y, 'Roteiro sugerido', 'Plano em 3 frentes')
    step_w = (CW - 12) / 3
    step_h = 112
    roadmap_card(c, LM, y - step_h, step_w, step_h, '01', 'Base web e conversao', 'Criar ou refinar uma pagina com proposta clara, prova social e CTA direto para WhatsApp.', 'Mais clareza comercial e menos perda de interessados', accent=BLUE)
    roadmap_card(c, LM + step_w + 6, y - step_h, step_w, step_h, '02', 'Perfil Google e reputacao', 'Atualizar fotos, reforcar o perfil e estruturar uma rotina simples para novas avaliacoes.', 'Mais confianca na busca local e maior taxa de clique', accent=GOLD)
    roadmap_card(c, LM + (step_w + 6) * 2, y - step_h, step_w, step_h, '03', 'Fluxo comercial', 'Diminuir atrito no atendimento e transformar pesquisa local em conversa mais qualificada.', 'Mais respostas e mais oportunidades reais de venda', accent=GREEN)
    y -= step_h + 20

    y = section_label(c, LM, RM, y, 'Proximo passo recomendado', 'Apresentacao e contato')
    cta_h = 174
    cta_y = y - cta_h
    shadow(c, LM, cta_y, CW, cta_h, 14)
    rrect(c, LM, cta_y, CW, cta_h, 14, fill=CARD, stroke=BORDER, sw=0.8)
    c.setFillColor(BLUE)
    c.rect(LM, cta_y + cta_h - 6, CW, 6, fill=1, stroke=0)

    right_w = 63 * mm
    right_x = RM - right_w - 16
    left_x = LM + 18
    pill(c, left_x, cta_y + cta_h - 22, 34 * mm, 6 * mm, 'PROPOSTA VISUAL', NAVY, WHITE)
    c.setFillColor(INK)
    c.setFont('Helvetica-Bold', 13)
    c.drawString(left_x, cta_y + cta_h - 38, 'Proximo passo recomendado')
    body_end = draw_wrapped(c, left_x, cta_y + cta_h - 56, 'Se fizer sentido, eu posso montar uma demonstracao visual mais sofisticada da presenca digital da empresa e mostrar como o novo site pode elevar confianca, percepcao de valor e contato comercial.', right_x - left_x - 20, 'Helvetica', 8.6, MUTED, leading=10.8, max_lines=5)
    bullet_y = body_end - 6
    for bullet in (
        'Layout com hierarquia mais elegante e apresentacao mais premium',
        'Estrutura pensada para transformar visita em conversa no WhatsApp',
        'Apresentacao mais profissional para elevar confianca e percepcao de valor',
    ):
        rrect(c, left_x, bullet_y - 1, 12, 12, 3, fill=BLUE)
        c.setFillColor(WHITE)
        c.setFont('Helvetica-Bold', 8)
        c.drawCentredString(left_x + 6, bullet_y + 2, 'V')
        bullet_end = draw_wrapped(c, left_x + 18, bullet_y + 2, bullet, right_x - left_x - 28, 'Helvetica', 8.0, INK, leading=10, max_lines=2)
        bullet_y = bullet_end - 8
    c.setFillColor(MUTED)
    c.setFont('Helvetica', 7.3)
    c.drawString(left_x, cta_y + 18, f'Diagnostico preparado por {prosp}')

    shadow(c, right_x, cta_y + 26, right_w, 112, 12)
    rrect(c, right_x, cta_y + 26, right_w, 112, 12, fill=PAPER_ALT, stroke=BORDER, sw=0.8)
    logo_card = logo_cta or logo_main
    if logo_card:
        try:
            c.drawImage(ImageReader(logo_card), right_x + 12, cta_y + 92, right_w - 24, 22, preserveAspectRatio=True, mask='auto')
        except Exception:
            c.setFillColor(NAVY)
            c.setFont('Helvetica-Bold', 13)
            c.drawCentredString(right_x + right_w / 2, cta_y + 104, 'OtimizaAI')
    else:
        c.setFillColor(NAVY)
        c.setFont('Helvetica-Bold', 13)
        c.drawCentredString(right_x + right_w / 2, cta_y + 104, 'OtimizaAI')
    c.setFillColor(MUTED)
    c.setFont('Helvetica-Bold', 7.1)
    c.drawCentredString(right_x + right_w / 2, cta_y + 76, 'CONTATO DIRETO')
    c.setFillColor(INK)
    c.setFont('Helvetica-Bold', 10.8)
    c.drawCentredString(right_x + right_w / 2, cta_y + 62, wa_display or 'WhatsApp nao informado')
    draw_wrapped(c, right_x + right_w / 2, cta_y + 48, 'Solicite uma demonstracao sem compromisso para visualizar a nova apresentacao da empresa.', right_w - 24, 'Helvetica', 7.3, MUTED, leading=9.2, max_lines=3, align='center')
    btn_x = right_x + 14
    btn_y = cta_y + 28
    btn_w = right_w - 28
    rrect(c, btn_x, btn_y, btn_w, 26, 8, fill=BLUE if wa_link else colors.HexColor('#CBD5E1'))
    c.setFillColor(WHITE if wa_link else NAVY)
    c.setFont('Helvetica-Bold', 8.1)
    c.drawCentredString(btn_x + btn_w / 2, btn_y + 9.2, 'AGENDAR DEMONSTRACAO')
    if wa_link:
        c.linkURL(wa_link, (btn_x, btn_y, btn_x + btn_w, btn_y + 26), relative=0, thickness=0)

    page_footer(c, LM, RM, 4)
    c.save()
    return output
